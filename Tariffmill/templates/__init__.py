"""
OCR Invoice Templates Package
Contains template classes for different invoice formats.
"""

from .base_template import BaseTemplate
from .mmcite_czech import MMCiteCzechTemplate
from .mmcite_brazilian import MMCiteBrazilianTemplate
from .bill_of_lading import BillOfLadingTemplate

# Registry of all available templates
TEMPLATE_REGISTRY = {
    'mmcite_czech': MMCiteCzechTemplate,
    'mmcite_brazilian': MMCiteBrazilianTemplate,
    'bill_of_lading': BillOfLadingTemplate,
}

def get_template(name: str) -> BaseTemplate:
    """Get a template instance by name."""
    if name in TEMPLATE_REGISTRY:
        return TEMPLATE_REGISTRY[name]()
    raise ValueError(f"Unknown template: {name}")

def get_all_templates() -> dict:
    """Get all available templates."""
    return {name: cls() for name, cls in TEMPLATE_REGISTRY.items()}

def register_template(name: str, template_class):
    """Register a new template."""
    TEMPLATE_REGISTRY[name] = template_class
