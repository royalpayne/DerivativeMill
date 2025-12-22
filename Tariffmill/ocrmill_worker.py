"""
OCRMill Background Worker for TariffMill
Handles folder monitoring and background PDF processing.
"""

import time
import os
from pathlib import Path
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt5.QtCore import QThread, pyqtSignal, QMutex


class OCRMillWorker(QThread):
    """
    Background worker for OCRMill folder monitoring and PDF processing.

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


class MultiFileWorker(QThread):
    """
    Worker for processing multiple PDF files in parallel using ThreadPoolExecutor.

    This significantly speeds up processing when multiple PDFs are dropped at once.
    """

    log_message = pyqtSignal(str)
    file_started = pyqtSignal(str)  # filename
    file_finished = pyqtSignal(str, bool, int)  # filename, success, item_count
    all_finished = pyqtSignal(list)  # all items combined
    progress = pyqtSignal(int, int)  # completed, total
    error = pyqtSignal(str)

    def __init__(self, processor, file_paths: List[Path], output_folder: Path = None,
                 max_workers: int = None, parent=None):
        """
        Initialize the multi-file worker.

        Args:
            processor: ProcessorEngine instance
            file_paths: List of PDF file paths to process
            output_folder: Output folder for CSV files
            max_workers: Maximum parallel workers (default: CPU count or 4, whichever is smaller)
            parent: Parent QObject
        """
        super().__init__(parent)
        self.processor = processor
        self.file_paths = [Path(p) for p in file_paths]
        self.output_folder = output_folder or Path(processor.config.output_folder)
        # Limit workers to prevent overwhelming the system
        # PDF processing is I/O and CPU intensive, so don't use too many threads
        self.max_workers = max_workers or min(os.cpu_count() or 4, 4)
        self._cancelled = False
        self._mutex = QMutex()

    def cancel(self):
        """Cancel the processing."""
        self._mutex.lock()
        self._cancelled = True
        self._mutex.unlock()

    def is_cancelled(self) -> bool:
        """Check if processing was cancelled."""
        self._mutex.lock()
        result = self._cancelled
        self._mutex.unlock()
        return result

    def _process_single_pdf(self, pdf_path: Path) -> tuple:
        """
        Process a single PDF file (called from thread pool).

        Args:
            pdf_path: Path to PDF file

        Returns:
            Tuple of (pdf_path, items, error_message)
        """
        if self.is_cancelled():
            return (pdf_path, [], "Cancelled")

        try:
            # Note: We create a simple log collector instead of emitting signals
            # because signals can't be emitted from non-Qt threads safely
            items = self.processor.process_pdf(pdf_path)
            if items:
                self.processor.save_to_csv(items, self.output_folder, pdf_name=pdf_path.name)
            return (pdf_path, items or [], None)
        except Exception as e:
            return (pdf_path, [], str(e))

    def run(self):
        """Process all PDF files in parallel."""
        total = len(self.file_paths)
        if total == 0:
            self.all_finished.emit([])
            return

        self.log_message.emit(f"Starting parallel processing of {total} PDF(s) with {self.max_workers} workers...")

        all_items = []
        completed = 0

        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(self._process_single_pdf, path): path
                for path in self.file_paths
            }

            # Process results as they complete
            for future in as_completed(future_to_path):
                if self.is_cancelled():
                    self.log_message.emit("Processing cancelled")
                    break

                pdf_path = future_to_path[future]

                try:
                    path, items, error = future.result()

                    if error:
                        self.log_message.emit(f"  ✗ {path.name}: {error}")
                        self.file_finished.emit(path.name, False, 0)
                    elif items:
                        self.log_message.emit(f"  ✓ {path.name}: {len(items)} items")
                        self.file_finished.emit(path.name, True, len(items))
                        all_items.extend(items)
                    else:
                        self.log_message.emit(f"  - {path.name}: No items extracted")
                        self.file_finished.emit(path.name, False, 0)

                except Exception as e:
                    self.log_message.emit(f"  ✗ {pdf_path.name}: Unexpected error - {e}")
                    self.file_finished.emit(pdf_path.name, False, 0)

                completed += 1
                self.progress.emit(completed, total)

        if not self.is_cancelled():
            self.log_message.emit(f"Completed: {len(all_items)} total items from {completed} file(s)")

        self.all_finished.emit(all_items)


class ParallelFolderWorker(QThread):
    """
    Worker for processing all PDFs in a folder in parallel.
    """

    log_message = pyqtSignal(str)
    file_finished = pyqtSignal(str, bool, int)  # filename, success, item_count
    all_finished = pyqtSignal(int)  # total items processed
    progress = pyqtSignal(int, int)  # completed, total
    error = pyqtSignal(str)

    def __init__(self, processor, input_folder: Path, output_folder: Path = None,
                 max_workers: int = None, parent=None):
        super().__init__(parent)
        self.processor = processor
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder) if output_folder else Path(processor.config.output_folder)
        self.max_workers = max_workers or min(os.cpu_count() or 4, 4)
        self._cancelled = False
        self._mutex = QMutex()

    def cancel(self):
        """Cancel the processing."""
        self._mutex.lock()
        self._cancelled = True
        self._mutex.unlock()

    def is_cancelled(self) -> bool:
        self._mutex.lock()
        result = self._cancelled
        self._mutex.unlock()
        return result

    def _process_single_pdf(self, pdf_path: Path) -> tuple:
        """Process a single PDF (called from thread pool)."""
        if self.is_cancelled():
            return (pdf_path, [], "Cancelled")

        try:
            items = self.processor.process_pdf(pdf_path)
            if items:
                self.processor.save_to_csv(items, self.output_folder, pdf_name=pdf_path.name)
            return (pdf_path, items or [], None)
        except Exception as e:
            return (pdf_path, [], str(e))

    def run(self):
        """Process all PDFs in the folder in parallel."""
        # Create folders
        self.input_folder.mkdir(parents=True, exist_ok=True)
        self.output_folder.mkdir(parents=True, exist_ok=True)
        processed_folder = self.input_folder / "Processed"
        failed_folder = self.input_folder / "Failed"

        # Find PDFs
        pdf_files = list(self.input_folder.glob("*.pdf"))
        total = len(pdf_files)

        if total == 0:
            self.log_message.emit("No PDF files found in input folder")
            self.all_finished.emit(0)
            return

        self.log_message.emit(f"Found {total} PDF(s), processing with {self.max_workers} workers...")

        total_items = 0
        completed = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_path = {
                executor.submit(self._process_single_pdf, path): path
                for path in pdf_files
            }

            for future in as_completed(future_to_path):
                if self.is_cancelled():
                    self.log_message.emit("Processing cancelled")
                    break

                pdf_path = future_to_path[future]

                try:
                    path, items, error = future.result()

                    if error:
                        self.log_message.emit(f"  ✗ {path.name}: {error}")
                        self.file_finished.emit(path.name, False, 0)
                        self.processor.move_to_failed(path, failed_folder, error[:50])
                    elif items:
                        self.log_message.emit(f"  ✓ {path.name}: {len(items)} items")
                        self.file_finished.emit(path.name, True, len(items))
                        self.processor.move_to_processed(path, processed_folder)
                        total_items += len(items)
                    else:
                        self.log_message.emit(f"  - {path.name}: No items extracted")
                        self.file_finished.emit(path.name, False, 0)
                        self.processor.move_to_failed(path, failed_folder, "No items extracted")

                except Exception as e:
                    self.log_message.emit(f"  ✗ {pdf_path.name}: {e}")
                    self.file_finished.emit(pdf_path.name, False, 0)
                    try:
                        self.processor.move_to_failed(pdf_path, failed_folder, str(e)[:50])
                    except:
                        pass

                completed += 1
                self.progress.emit(completed, total)

        self.log_message.emit(f"Folder processing complete: {total_items} items from {completed} file(s)")
        self.all_finished.emit(total_items)
