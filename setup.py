#!/usr/bin/env python3
"""
Setup script for DerivativeMill
Enables installation via: pip install -e .
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    with open(requirements_path) as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

# Read README if it exists
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    with open(readme_path) as f:
        long_description = f.read()

setup(
    name="derivativemill",
    version="1.08",
    author="Your Name",
    author_email="your.email@example.com",
    description="Derivative tariff compliance and invoice processing system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/derivativemill",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/derivativemill/issues",
        "Documentation": "https://github.com/yourusername/derivativemill/wiki",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: X11 Applications :: Qt",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial",
        "Topic :: System :: Archiving",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "derivativemill=DerivativeMill.derivativemill:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="tariff customs invoice processing derivative",
)
