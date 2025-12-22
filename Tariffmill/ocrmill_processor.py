"""
OCRMill Processing Engine for TariffMill
PDF invoice processing using OCR templates.
"""

import csv
import re
from pathlib import Path
from typing import List, Dict, Callable, Optional
from datetime import datetime

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from templates import get_all_templates
from templates.bill_of_lading import BillOfLadingTemplate


class OCRMillConfig:
    """Configuration holder for OCRMill processing."""

    def __init__(self):
        self.input_folder = Path("Input/OCRMill")
        self.output_folder = Path("Output/OCRMill")
        self.consolidate_multi_invoice = False
        self.poll_interval = 60
        self.auto_start = False
        self.template_settings = {}  # template_name -> enabled

    def get_template_enabled(self, template_name: str) -> bool:
        """Check if a template is enabled."""
        return self.template_settings.get(template_name, True)

    def set_template_enabled(self, template_name: str, enabled: bool):
        """Set template enabled state."""
        self.template_settings[template_name] = enabled


class ProcessorEngine:
    """Core processing engine using templates for PDF invoice extraction."""

    def __init__(self, db, config: OCRMillConfig = None, log_callback: Callable[[str], None] = None):
        """
        Initialize the processor engine.

        Args:
            db: OCRMillDatabase instance for parts tracking
            config: OCRMillConfig with processing settings
            log_callback: Function to call with log messages
        """
        self.config = config or OCRMillConfig()
        self.log_callback = log_callback or print
        self.templates = {}
        self.parts_db = db
        self._load_templates()

    def _load_templates(self):
        """Load all available templates."""
        self.templates = get_all_templates()

    def reload_templates(self):
        """Reload templates from disk. Call after adding/removing template files."""
        self._load_templates()
        self.log(f"Reloaded {len(self.templates)} templates")

    def log(self, message: str):
        """Log a message."""
        self.log_callback(message)

    def get_best_template(self, text: str):
        """Find the best template for the given text."""
        best_template = None
        best_score = 0.0

        self.log(f"  Evaluating {len(self.templates)} templates...")

        for name, template in self.templates.items():
            if not self.config.get_template_enabled(name):
                self.log(f"    - {name}: Disabled in config")
                continue
            if not template.enabled:
                self.log(f"    - {name}: Disabled in template")
                continue

            score = template.get_confidence_score(text)
            self.log(f"    - {name}: Confidence score {score:.2f}")

            if score > best_score:
                best_score = score
                best_template = template

        if best_template:
            self.log(f"  Selected template: {best_template.name} (score: {best_score:.2f})")
        else:
            self.log(f"  No matching template found")

        return best_template

    def process_pdf(self, pdf_path: Path) -> List[Dict]:
        """
        Process a single PDF file, handling multiple invoices per PDF.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of extracted line items as dictionaries
        """
        if pdfplumber is None:
            self.log("Error: pdfplumber is not installed. Run: pip install pdfplumber")
            return []

        self.log(f"Processing: {pdf_path.name}")

        try:
            with pdfplumber.open(pdf_path) as pdf:
                # First pass: extract all text to detect template
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"

                if not full_text.strip():
                    self.log(f"  No text extracted from {pdf_path.name}")
                    return []

                # Scan for Bill of Lading and extract gross weight
                bol_weight = None
                bol_template = BillOfLadingTemplate()

                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text and bol_template.can_process(page_text):
                        self.log(f"  Found Bill of Lading on a page")
                        bol_weight = bol_template.extract_gross_weight(page_text)
                        if bol_weight:
                            self.log(f"  Extracted BOL gross weight: {bol_weight} kg")
                            break

                # Find the best template
                template = self.get_best_template(full_text)
                if not template:
                    self.log(f"  No matching template for {pdf_path.name}")
                    return []

                self.log(f"  Using template: {template.name}")

                # Check if packing list only
                if template.is_packing_list(full_text):
                    self.log(f"  Skipping packing list: {pdf_path.name}")
                    return []

                # Second pass: process page-by-page to handle multiple invoices
                all_items = []
                current_invoice = None
                current_project = None
                page_buffer = []

                for page in pdf.pages:
                    page_text = page.extract_text()
                    if not page_text:
                        continue

                    # Skip packing list and BOL pages
                    if 'packing list' in page_text.lower() and 'invoice' not in page_text.lower():
                        continue
                    if 'bill of lading' in page_text.lower():
                        continue

                    # Check for new invoice on this page
                    inv_match = re.search(r'(?:Proforma\s+)?[Ii]nvoice\s+(?:number|n)\.?\s*:?\s*(\d+(?:/\d+)?)', page_text)
                    proj_match = re.search(r'(?:\d+\.\s*)?[Pp]roject\s*(?:n\.?)?\s*:?\s*(US\d+[A-Z]\d+)', page_text, re.IGNORECASE)

                    # If we found a new invoice number, process the buffer first
                    new_invoice = inv_match.group(1) if inv_match else None
                    if new_invoice and current_invoice and new_invoice != current_invoice:
                        # Process accumulated pages for previous invoice
                        if page_buffer:
                            buffer_text = "\n".join(page_buffer)
                            _, _, items = template.extract_all(buffer_text)
                            for item in items:
                                item['invoice_number'] = current_invoice
                                item['project_number'] = current_project
                                if bol_weight:
                                    item['bol_gross_weight'] = bol_weight
                                if bol_weight and ('net_weight' not in item or not item.get('net_weight')):
                                    item['net_weight'] = bol_weight
                            all_items.extend(items)
                            page_buffer = []

                    # Update current invoice/project if found
                    if inv_match:
                        current_invoice = inv_match.group(1)
                    if proj_match:
                        current_project = proj_match.group(1).upper()

                    # Add page to buffer
                    page_buffer.append(page_text)

                # Process remaining pages in buffer
                if page_buffer and current_invoice:
                    buffer_text = "\n".join(page_buffer)
                    _, _, items = template.extract_all(buffer_text)
                    for item in items:
                        item['invoice_number'] = current_invoice
                        item['project_number'] = current_project
                        if bol_weight:
                            item['bol_gross_weight'] = bol_weight
                        if bol_weight and ('net_weight' not in item or not item.get('net_weight')):
                            item['net_weight'] = bol_weight
                    all_items.extend(items)

                # Count unique invoices and calculate grand total
                unique_invoices = set(item.get('invoice_number', 'UNKNOWN') for item in all_items)
                grand_total = sum(float(item.get('total_price', 0) or 0) for item in all_items)
                self.log(f"  Found {len(unique_invoices)} invoice(s), {len(all_items)} total items, Grand Total: ${grand_total:,.2f}")

                for inv in sorted(unique_invoices):
                    inv_items = [item for item in all_items if item.get('invoice_number') == inv]
                    proj = inv_items[0].get('project_number', 'UNKNOWN') if inv_items else 'UNKNOWN'
                    total_value = sum(float(item.get('total_price', 0) or 0) for item in inv_items)
                    self.log(f"    - Invoice {inv} (Project {proj}): {len(inv_items)} items, ${total_value:,.2f}")

                return all_items

        except Exception as e:
            self.log(f"  Error processing {pdf_path.name}: {e}")
            return []

    def save_to_csv(self, items: List[Dict], output_folder: Path, pdf_name: str = None) -> List[Path]:
        """
        Save items to CSV files and add to parts database.

        Args:
            items: List of extracted line items
            output_folder: Output folder for CSV files
            pdf_name: Original PDF filename for reference

        Returns:
            List of paths to created CSV files
        """
        if not items:
            return []

        output_folder.mkdir(exist_ok=True, parents=True)
        created_files = []

        # Add items to parts database and enrich with descriptions, HTS codes, MID
        for item in items:
            # Look up MID and country_origin from manufacturer name
            if ('mid' not in item or not item['mid']) or ('country_origin' not in item or not item['country_origin']):
                manufacturer_name = item.get('manufacturer_name', '')
                if manufacturer_name:
                    manufacturer = self.parts_db.get_manufacturer_by_name(manufacturer_name)
                    if manufacturer:
                        if 'mid' not in item or not item['mid']:
                            if manufacturer.get('mid'):
                                item['mid'] = manufacturer.get('mid', '')
                        if 'country_origin' not in item or not item['country_origin']:
                            if manufacturer.get('country'):
                                item['country_origin'] = manufacturer.get('country', '')

            # If country_origin still not set but we have MID, extract from first 2 letters
            if ('country_origin' not in item or not item['country_origin']) and item.get('mid'):
                mid = item.get('mid', '')
                if len(mid) >= 2:
                    item['country_origin'] = mid[:2].upper()

            part_data = item.copy()
            part_data['source_file'] = pdf_name or 'unknown'
            self.parts_db.add_part_occurrence(part_data)

            # Add description and HTS code back to item for CSV export
            if 'description' not in item or not item['description']:
                item['description'] = part_data.get('description', '')
            if 'hts_code' not in item or not item['hts_code']:
                item['hts_code'] = part_data.get('hts_code', '')

            # Remove manufacturer_name from item (we only need MID in output)
            if 'manufacturer_name' in item:
                del item['manufacturer_name']

        # Group by invoice number
        by_invoice = {}
        for item in items:
            inv_num = item.get('invoice_number', 'UNKNOWN')
            if inv_num not in by_invoice:
                by_invoice[inv_num] = []
            by_invoice[inv_num].append(item)

        # Determine columns from items with specific ordering
        columns = ['invoice_number', 'project_number', 'part_number', 'description',
                   'mid', 'country_origin', 'hts_code', 'quantity', 'total_price']

        for item in items:
            for key in item.keys():
                if key not in columns:
                    columns.append(key)

        # Check consolidation mode
        consolidate = self.config.consolidate_multi_invoice

        if consolidate and len(by_invoice) > 1:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if pdf_name:
                base_name = Path(pdf_name).stem
            else:
                base_name = f"consolidated_{list(by_invoice.keys())[0]}"
            filename = f"{base_name}_{timestamp}.csv"
            filepath = output_folder / filename

            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(items)

            invoice_list = ", ".join(sorted(by_invoice.keys()))
            self.log(f"  Saved: {filename} ({len(items)} items from {len(by_invoice)} invoices: {invoice_list})")
            created_files.append(filepath)

        else:
            for inv_num, inv_items in by_invoice.items():
                proj_num = inv_items[0].get('project_number', 'UNKNOWN')
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_inv_num = inv_num.replace('/', '-')
                filename = f"{safe_inv_num}_{proj_num}_{timestamp}.csv"
                filepath = output_folder / filename

                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
                    writer.writeheader()
                    writer.writerows(inv_items)

                self.log(f"  Saved: {filename} ({len(inv_items)} items)")
                created_files.append(filepath)

        return created_files

    def move_to_processed(self, pdf_path: Path, processed_folder: Path):
        """Move processed PDF to the Processed folder."""
        processed_folder.mkdir(exist_ok=True, parents=True)

        dest = processed_folder / pdf_path.name
        counter = 1
        while dest.exists():
            stem = pdf_path.stem
            dest = processed_folder / f"{stem}_{counter}{pdf_path.suffix}"
            counter += 1

        pdf_path.rename(dest)
        self.log(f"  Moved to: Processed/{dest.name}")

    def move_to_failed(self, pdf_path: Path, failed_folder: Path, reason: str = ""):
        """Move failed PDF to the Failed folder."""
        failed_folder.mkdir(exist_ok=True, parents=True)

        dest = failed_folder / pdf_path.name
        counter = 1
        while dest.exists():
            stem = pdf_path.stem
            dest = failed_folder / f"{stem}_{counter}{pdf_path.suffix}"
            counter += 1

        pdf_path.rename(dest)
        reason_msg = f" ({reason})" if reason else ""
        self.log(f"  Moved to: Failed/{dest.name}{reason_msg}")

    def process_folder(self, input_folder: Path = None, output_folder: Path = None) -> int:
        """
        Process all PDFs in the input folder.

        Args:
            input_folder: Input folder path (uses config default if None)
            output_folder: Output folder path (uses config default if None)

        Returns:
            Number of successfully processed PDFs
        """
        input_folder = input_folder or self.config.input_folder
        output_folder = output_folder or self.config.output_folder

        input_folder = Path(input_folder)
        output_folder = Path(output_folder)

        input_folder.mkdir(exist_ok=True, parents=True)
        output_folder.mkdir(exist_ok=True, parents=True)
        processed_folder = input_folder / "Processed"
        failed_folder = input_folder / "Failed"

        pdf_files = list(input_folder.glob("*.pdf"))
        if not pdf_files:
            return 0

        self.log(f"Found {len(pdf_files)} PDF(s) to process")
        processed_count = 0
        failed_count = 0

        for pdf_path in pdf_files:
            try:
                items = self.process_pdf(pdf_path)
                if items:
                    self.save_to_csv(items, output_folder, pdf_name=pdf_path.name)
                    self.move_to_processed(pdf_path, processed_folder)
                    processed_count += 1
                else:
                    self.move_to_failed(pdf_path, failed_folder, "No items extracted")
                    failed_count += 1
            except Exception as e:
                self.log(f"  Error processing {pdf_path.name}: {e}")
                self.move_to_failed(pdf_path, failed_folder, f"Error: {str(e)[:50]}")
                failed_count += 1

        if failed_count > 0:
            self.log(f"Summary: {processed_count} processed successfully, {failed_count} failed")

        return processed_count

    def process_single_file(self, pdf_path: Path, output_folder: Path = None, move_after: bool = True) -> List[Dict]:
        """
        Process a single PDF file manually.

        Args:
            pdf_path: Path to PDF file
            output_folder: Output folder (uses config default if None)
            move_after: Whether to move the file after processing

        Returns:
            List of extracted items
        """
        output_folder = output_folder or self.config.output_folder
        output_folder = Path(output_folder)

        items = self.process_pdf(pdf_path)

        if items:
            self.save_to_csv(items, output_folder, pdf_name=pdf_path.name)
            if move_after:
                processed_folder = pdf_path.parent / "Processed"
                self.move_to_processed(pdf_path, processed_folder)

        return items

    def get_available_templates(self) -> Dict[str, Dict]:
        """Get information about available templates."""
        template_info = {}
        for name, template in self.templates.items():
            template_info[name] = {
                'name': template.name,
                'enabled': template.enabled and self.config.get_template_enabled(name),
                'description': getattr(template, 'description', 'No description'),
            }
        return template_info
