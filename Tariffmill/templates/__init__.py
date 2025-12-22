"""
OCR Invoice Templates Package
Contains template classes for different invoice formats.
Dynamically discovers and loads templates from this directory.
"""

import os
import importlib
import importlib.util
import sys
from pathlib import Path

from .base_template import BaseTemplate

# Registry of all available templates (populated dynamically)
TEMPLATE_REGISTRY = {}

# Files to exclude from template discovery
EXCLUDED_FILES = {'__init__.py', 'base_template.py', 'sample_template.py'}


def _discover_templates():
    """
    Dynamically discover and load all template classes from this directory.
    Templates must:
    - Be .py files in the templates directory
    - Contain a class that inherits from BaseTemplate
    - Not be in EXCLUDED_FILES
    """
    global TEMPLATE_REGISTRY
    TEMPLATE_REGISTRY.clear()

    templates_dir = Path(__file__).parent

    for file_path in templates_dir.glob('*.py'):
        if file_path.name in EXCLUDED_FILES:
            continue

        # Skip files with spaces in names (invalid Python module names)
        if ' ' in file_path.name:
            print(f"Warning: Skipping template '{file_path.name}' - filename contains spaces. Rename to use underscores.")
            continue

        module_name = file_path.stem  # filename without .py

        try:
            # Load the module
            spec = importlib.util.spec_from_file_location(
                f"templates.{module_name}",
                file_path
            )
            if spec is None or spec.loader is None:
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[f"templates.{module_name}"] = module
            spec.loader.exec_module(module)

            # Find template class (class that inherits from BaseTemplate)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, BaseTemplate) and
                    attr is not BaseTemplate):
                    # Register the template
                    TEMPLATE_REGISTRY[module_name] = attr
                    break

        except Exception as e:
            print(f"Warning: Failed to load template {module_name}: {e}")
            continue


def refresh_templates():
    """
    Re-scan the templates directory and reload all templates.
    Call this to pick up new templates or remove deleted ones.
    """
    _discover_templates()


def get_template(name: str) -> BaseTemplate:
    """Get a template instance by name."""
    if not TEMPLATE_REGISTRY:
        _discover_templates()
    if name in TEMPLATE_REGISTRY:
        return TEMPLATE_REGISTRY[name]()
    raise ValueError(f"Unknown template: {name}")


def get_all_templates() -> dict:
    """Get all available templates."""
    if not TEMPLATE_REGISTRY:
        _discover_templates()
    return {name: cls() for name, cls in TEMPLATE_REGISTRY.items()}


def register_template(name: str, template_class):
    """Register a new template manually."""
    TEMPLATE_REGISTRY[name] = template_class


# Initial discovery on import
_discover_templates()
