"""
CRMill Background Worker for TariffMill
Handles folder monitoring and background PDF processing.
"""

import time
from pathlib import Path
from typing import List, Dict, Optional
from PyQt5.QtCore import QThread, pyqtSignal, QMutex


class CRMillWorker(QThread):
    """
    Background worker for CRMill folder monitoring and PDF processing.

    Signals:
        log_message: Emitted with log messages for display
        processing_started: Emitted when processing begins
        processing_finished: Emitted when processing completes with item count
        pdf_processed: Emitted after each PDF is processed with (filename, success, item_count)
        error: Emitted on errors with error message
        items_extracted: Emitted with extracted items for UI display
    """

    log_message = pyqtSignal(str)
    processing_started = pyqtSignal()
    processing_finished = pyqtSignal(int)  # total items processed
    pdf_processed = pyqtSignal(str, bool, int)  # filename, success, item_count
    error = pyqtSignal(str)
    items_extracted = pyqtSignal(list)  # list of item dicts

    def __init__(self, processor, parent=None):
        """
        Initialize the worker.

        Args:
            processor: ProcessorEngine instance
            parent: Parent QObject
        """
        super().__init__(parent)
        self.processor = processor
        self._running = False
        self._monitoring = False
        self._poll_interval = 60  # seconds
        self._mutex = QMutex()

        # Connect processor logging to our signal
        self.processor.log_callback = self._log

    def _log(self, message: str):
        """Log callback that emits signal."""
        self.log_message.emit(message)

    def set_poll_interval(self, seconds: int):
        """Set the polling interval for folder monitoring."""
        self._mutex.lock()
        self._poll_interval = max(10, min(300, seconds))  # clamp to 10-300 seconds
        self._mutex.unlock()

    def start_monitoring(self):
        """Start folder monitoring mode."""
        self._mutex.lock()
        self._monitoring = True
        self._mutex.unlock()
        if not self.isRunning():
            self.start()

    def stop_monitoring(self):
        """Stop folder monitoring mode."""
        self._mutex.lock()
        self._monitoring = False
        self._mutex.unlock()

    def is_monitoring(self) -> bool:
        """Check if currently monitoring."""
        self._mutex.lock()
        result = self._monitoring
        self._mutex.unlock()
        return result

    def stop(self):
        """Stop the worker thread."""
        self._mutex.lock()
        self._running = False
        self._monitoring = False
        self._mutex.unlock()
        self.wait(5000)  # Wait up to 5 seconds for thread to finish

    def run(self):
        """Main thread loop for folder monitoring."""
        self._running = True

        while self._running:
            self._mutex.lock()
            monitoring = self._monitoring
            poll_interval = self._poll_interval
            self._mutex.unlock()

            if monitoring:
                try:
                    self._process_folder()
                except Exception as e:
                    self.error.emit(f"Monitoring error: {str(e)}")

                # Sleep in small increments to allow for stopping
                for _ in range(poll_interval):
                    if not self._running or not self._monitoring:
                        break
                    time.sleep(1)
            else:
                # Not monitoring, just sleep briefly
                time.sleep(1)

    def _process_folder(self):
        """Process PDFs in the input folder."""
        input_folder = Path(self.processor.config.input_folder)
        output_folder = Path(self.processor.config.output_folder)

        if not input_folder.exists():
            return

        pdf_files = list(input_folder.glob("*.pdf"))
        if not pdf_files:
            return

        self.processing_started.emit()
        total_items = 0

        for pdf_path in pdf_files:
            if not self._running or not self._monitoring:
                break

            try:
                items = self.processor.process_pdf(pdf_path)
                if items:
                    self.processor.save_to_csv(items, output_folder, pdf_name=pdf_path.name)
                    processed_folder = input_folder / "Processed"
                    self.processor.move_to_processed(pdf_path, processed_folder)
                    self.pdf_processed.emit(pdf_path.name, True, len(items))
                    self.items_extracted.emit(items)
                    total_items += len(items)
                else:
                    failed_folder = input_folder / "Failed"
                    self.processor.move_to_failed(pdf_path, failed_folder, "No items extracted")
                    self.pdf_processed.emit(pdf_path.name, False, 0)

            except Exception as e:
                self.error.emit(f"Error processing {pdf_path.name}: {str(e)}")
                failed_folder = input_folder / "Failed"
                self.processor.move_to_failed(pdf_path, failed_folder, str(e)[:50])
                self.pdf_processed.emit(pdf_path.name, False, 0)

        self.processing_finished.emit(total_items)

    def process_single_file(self, pdf_path: Path, output_folder: Path = None) -> List[Dict]:
        """
        Process a single PDF file (not in background thread).

        This method should be called from a separate worker thread
        or using processEvents() for responsiveness.

        Args:
            pdf_path: Path to PDF file
            output_folder: Output folder path

        Returns:
            List of extracted items
        """
        self.processing_started.emit()

        try:
            items = self.processor.process_pdf(pdf_path)
            if items:
                output = output_folder or Path(self.processor.config.output_folder)
                self.processor.save_to_csv(items, output, pdf_name=pdf_path.name)
                self.pdf_processed.emit(pdf_path.name, True, len(items))
                self.items_extracted.emit(items)
            else:
                self.pdf_processed.emit(pdf_path.name, False, 0)

            self.processing_finished.emit(len(items) if items else 0)
            return items or []

        except Exception as e:
            self.error.emit(f"Error processing {pdf_path.name}: {str(e)}")
            self.processing_finished.emit(0)
            return []


class SingleFileWorker(QThread):
    """
    Worker for processing a single PDF file without blocking the UI.
    """

    log_message = pyqtSignal(str)
    finished = pyqtSignal(list)  # list of extracted items
    error = pyqtSignal(str)

    def __init__(self, processor, pdf_path: Path, output_folder: Path = None, parent=None):
        super().__init__(parent)
        self.processor = processor
        self.pdf_path = pdf_path
        self.output_folder = output_folder
        self._original_callback = processor.log_callback

    def run(self):
        """Process the PDF file."""
        # Temporarily redirect logging
        self.processor.log_callback = lambda msg: self.log_message.emit(msg)

        try:
            items = self.processor.process_pdf(self.pdf_path)
            if items:
                output = self.output_folder or Path(self.processor.config.output_folder)
                self.processor.save_to_csv(items, output, pdf_name=self.pdf_path.name)
            self.finished.emit(items or [])

        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit([])

        finally:
            # Restore original callback
            self.processor.log_callback = self._original_callback
