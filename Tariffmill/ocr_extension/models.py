"""
Data models for OCR Extension.
Defines structured data classes for extracted document information.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import pandas as pd


@dataclass
class LineItem:
    """Represents a single line item from a commercial invoice."""
    line_number: int = 0
    description: str = ""
    quantity: float = 0.0
    unit: str = ""
    unit_price: float = 0.0
    total_price: float = 0.0
    hts_code: str = ""
    country_of_origin: str = ""
    part_number: str = ""
    po_number: str = ""
    raw_text: str = ""  # Original extracted text for this line

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DataFrame creation."""
        return {
            'line_number': self.line_number,
            'description': self.description,
            'quantity': self.quantity,
            'unit': self.unit,
            'unit_price': self.unit_price,
            'total_price': self.total_price,
            'hts_code': self.hts_code,
            'country_of_origin': self.country_of_origin,
            'part_number': self.part_number,
            'po_number': self.po_number,
            'raw_text': self.raw_text
        }


@dataclass
class InvoiceTotals:
    """Invoice total amounts and summary data."""
    subtotal: float = 0.0
    freight: float = 0.0
    insurance: float = 0.0
    other_charges: float = 0.0
    total_amount: float = 0.0
    currency: str = "USD"
    total_quantity: float = 0.0
    total_weight: float = 0.0
    weight_unit: str = "KG"
    total_packages: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'subtotal': self.subtotal,
            'freight': self.freight,
            'insurance': self.insurance,
            'other_charges': self.other_charges,
            'total_amount': self.total_amount,
            'currency': self.currency,
            'total_quantity': self.total_quantity,
            'total_weight': self.total_weight,
            'weight_unit': self.weight_unit,
            'total_packages': self.total_packages
        }


@dataclass
class VendorInfo:
    """Vendor/Seller information from the invoice."""
    name: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    postal_code: str = ""
    phone: str = ""
    fax: str = ""
    email: str = ""
    tax_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'vendor_name': self.name,
            'vendor_address': self.address,
            'vendor_city': self.city,
            'vendor_state': self.state,
            'vendor_country': self.country,
            'vendor_postal_code': self.postal_code,
            'vendor_phone': self.phone,
            'vendor_fax': self.fax,
            'vendor_email': self.email,
            'vendor_tax_id': self.tax_id
        }


@dataclass
class ReceiverInfo:
    """Receiver/Buyer/Consignee information."""
    name: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    postal_code: str = ""
    phone: str = ""
    email: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'receiver_name': self.name,
            'receiver_address': self.address,
            'receiver_city': self.city,
            'receiver_state': self.state,
            'receiver_country': self.country,
            'receiver_postal_code': self.postal_code,
            'receiver_phone': self.phone,
            'receiver_email': self.email
        }


@dataclass
class ReferenceNumbers:
    """Reference numbers from invoice documents."""
    invoice_number: str = ""
    invoice_date: str = ""
    po_number: str = ""
    bill_of_lading: str = ""
    container_number: str = ""
    seal_number: str = ""
    shipment_reference: str = ""
    customer_reference: str = ""
    export_reference: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'invoice_number': self.invoice_number,
            'invoice_date': self.invoice_date,
            'po_number': self.po_number,
            'bill_of_lading': self.bill_of_lading,
            'container_number': self.container_number,
            'seal_number': self.seal_number,
            'shipment_reference': self.shipment_reference,
            'customer_reference': self.customer_reference,
            'export_reference': self.export_reference
        }


@dataclass
class InvoiceData:
    """Complete invoice data structure."""
    vendor: VendorInfo = field(default_factory=VendorInfo)
    receiver: ReceiverInfo = field(default_factory=ReceiverInfo)
    references: ReferenceNumbers = field(default_factory=ReferenceNumbers)
    line_items: List[LineItem] = field(default_factory=list)
    totals: InvoiceTotals = field(default_factory=InvoiceTotals)
    incoterms: str = ""
    payment_terms: str = ""
    ship_date: str = ""
    port_of_loading: str = ""
    port_of_discharge: str = ""
    final_destination: str = ""
    raw_text: str = ""  # Full extracted text

    def to_dataframe(self) -> pd.DataFrame:
        """Convert line items to a Pandas DataFrame with header info."""
        if not self.line_items:
            return pd.DataFrame()

        # Create DataFrame from line items
        df = pd.DataFrame([item.to_dict() for item in self.line_items])

        # Add header columns to each row for complete data
        df['invoice_number'] = self.references.invoice_number
        df['invoice_date'] = self.references.invoice_date
        df['vendor_name'] = self.vendor.name
        df['vendor_country'] = self.vendor.country
        df['receiver_name'] = self.receiver.name
        df['po_number_header'] = self.references.po_number
        df['bill_of_lading'] = self.references.bill_of_lading
        df['container_number'] = self.references.container_number
        df['incoterms'] = self.incoterms
        df['port_of_loading'] = self.port_of_loading
        df['port_of_discharge'] = self.port_of_discharge

        return df

    def get_summary_dict(self) -> Dict[str, Any]:
        """Get a summary dictionary of all non-line-item data."""
        summary = {}
        summary.update(self.vendor.to_dict())
        summary.update(self.receiver.to_dict())
        summary.update(self.references.to_dict())
        summary.update(self.totals.to_dict())
        summary['incoterms'] = self.incoterms
        summary['payment_terms'] = self.payment_terms
        summary['ship_date'] = self.ship_date
        summary['port_of_loading'] = self.port_of_loading
        summary['port_of_discharge'] = self.port_of_discharge
        summary['final_destination'] = self.final_destination
        summary['line_item_count'] = len(self.line_items)
        return summary


@dataclass
class PackingListData:
    """Packing list specific data."""
    references: ReferenceNumbers = field(default_factory=ReferenceNumbers)
    packages: List[Dict[str, Any]] = field(default_factory=list)
    total_packages: int = 0
    total_gross_weight: float = 0.0
    total_net_weight: float = 0.0
    weight_unit: str = "KG"
    total_volume: float = 0.0
    volume_unit: str = "CBM"
    raw_text: str = ""

    def to_dataframe(self) -> pd.DataFrame:
        """Convert packages to DataFrame."""
        if not self.packages:
            return pd.DataFrame()
        return pd.DataFrame(self.packages)


@dataclass
class BillOfLadingData:
    """Bill of Lading specific data."""
    bl_number: str = ""
    bl_type: str = ""  # Ocean, Air, etc.
    shipper: str = ""
    consignee: str = ""
    notify_party: str = ""
    vessel_name: str = ""
    voyage_number: str = ""
    port_of_loading: str = ""
    port_of_discharge: str = ""
    place_of_delivery: str = ""
    container_numbers: List[str] = field(default_factory=list)
    seal_numbers: List[str] = field(default_factory=list)
    goods_description: str = ""
    gross_weight: float = 0.0
    measurement: float = 0.0
    freight_terms: str = ""
    issue_date: str = ""
    issue_place: str = ""
    raw_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'bl_number': self.bl_number,
            'bl_type': self.bl_type,
            'shipper': self.shipper,
            'consignee': self.consignee,
            'notify_party': self.notify_party,
            'vessel_name': self.vessel_name,
            'voyage_number': self.voyage_number,
            'port_of_loading': self.port_of_loading,
            'port_of_discharge': self.port_of_discharge,
            'place_of_delivery': self.place_of_delivery,
            'container_numbers': ', '.join(self.container_numbers),
            'seal_numbers': ', '.join(self.seal_numbers),
            'goods_description': self.goods_description,
            'gross_weight': self.gross_weight,
            'measurement': self.measurement,
            'freight_terms': self.freight_terms,
            'issue_date': self.issue_date,
            'issue_place': self.issue_place
        }


@dataclass
class DocumentResult:
    """
    Complete result from processing a document.
    Main return type from OCRProcessor.process()
    """
    success: bool = False
    error_message: str = ""
    source_file: str = ""
    processed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    page_count: int = 0

    # Document type detection
    document_types: List[str] = field(default_factory=list)  # ['invoice', 'packing_list', 'bol']

    # Extracted data by type
    invoice: Optional[InvoiceData] = None
    packing_list: Optional[PackingListData] = None
    bill_of_lading: Optional[BillOfLadingData] = None

    # Convenience properties
    @property
    def has_invoice(self) -> bool:
        return self.invoice is not None

    @property
    def has_packing_list(self) -> bool:
        return self.packing_list is not None

    @property
    def has_bill_of_lading(self) -> bool:
        return self.bill_of_lading is not None

    @property
    def line_items(self) -> pd.DataFrame:
        """Get invoice line items as DataFrame (convenience property)."""
        if self.invoice:
            return self.invoice.to_dataframe()
        return pd.DataFrame()

    @property
    def totals(self) -> Dict[str, Any]:
        """Get invoice totals (convenience property)."""
        if self.invoice:
            return self.invoice.totals.to_dict()
        return {}

    @property
    def vendor(self) -> Dict[str, Any]:
        """Get vendor info (convenience property)."""
        if self.invoice:
            return self.invoice.vendor.to_dict()
        return {}

    @property
    def references(self) -> Dict[str, Any]:
        """Get reference numbers (convenience property)."""
        if self.invoice:
            return self.invoice.references.to_dict()
        return {}

    def to_combined_dataframe(self) -> pd.DataFrame:
        """
        Create a combined DataFrame with all extracted data.
        Each line item row includes header data and totals.
        """
        if not self.invoice or not self.invoice.line_items:
            # Return summary row only
            summary = self.get_summary()
            return pd.DataFrame([summary])

        df = self.invoice.to_dataframe()

        # Add BOL info if available
        if self.bill_of_lading:
            bol = self.bill_of_lading
            df['bl_number'] = bol.bl_number
            df['vessel_name'] = bol.vessel_name
            df['voyage_number'] = bol.voyage_number

        # Add processing metadata
        df['source_file'] = self.source_file
        df['processed_at'] = self.processed_at

        return df

    def get_summary(self) -> Dict[str, Any]:
        """Get complete summary of all extracted data."""
        summary = {
            'success': self.success,
            'source_file': self.source_file,
            'processed_at': self.processed_at,
            'page_count': self.page_count,
            'document_types': ', '.join(self.document_types)
        }

        if self.invoice:
            summary.update(self.invoice.get_summary_dict())

        if self.bill_of_lading:
            summary.update(self.bill_of_lading.to_dict())

        return summary
