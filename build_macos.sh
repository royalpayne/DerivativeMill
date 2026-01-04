#!/bin/bash
# TariffMill macOS Build Script
# Creates a .app bundle and optional .dmg installer

set -e

echo "=========================================="
echo "TariffMill macOS Build Script"
echo "=========================================="

# Change to Tariffmill directory
cd "$(dirname "$0")/Tariffmill"

# Check for required tools
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required"
    exit 1
fi

# Create/activate virtual environment
if [ ! -d "../.venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv ../.venv
fi

source ../.venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -e ..
pip install pyinstaller

# Check if we need to create .icns icon
if [ ! -f "Resources/tariffmill_icon.icns" ]; then
    echo "Creating macOS icon..."
    if [ -f "Resources/tariffmill_icon.png" ]; then
        # Create iconset directory
        mkdir -p Resources/tariffmill_icon.iconset

        # Generate different sizes (requires sips on macOS)
        if command -v sips &> /dev/null; then
            sips -z 16 16     Resources/tariffmill_icon.png --out Resources/tariffmill_icon.iconset/icon_16x16.png
            sips -z 32 32     Resources/tariffmill_icon.png --out Resources/tariffmill_icon.iconset/icon_16x16@2x.png
            sips -z 32 32     Resources/tariffmill_icon.png --out Resources/tariffmill_icon.iconset/icon_32x32.png
            sips -z 64 64     Resources/tariffmill_icon.png --out Resources/tariffmill_icon.iconset/icon_32x32@2x.png
            sips -z 128 128   Resources/tariffmill_icon.png --out Resources/tariffmill_icon.iconset/icon_128x128.png
            sips -z 256 256   Resources/tariffmill_icon.png --out Resources/tariffmill_icon.iconset/icon_128x128@2x.png
            sips -z 256 256   Resources/tariffmill_icon.png --out Resources/tariffmill_icon.iconset/icon_256x256.png
            sips -z 512 512   Resources/tariffmill_icon.png --out Resources/tariffmill_icon.iconset/icon_256x256@2x.png
            sips -z 512 512   Resources/tariffmill_icon.png --out Resources/tariffmill_icon.iconset/icon_512x512.png
            sips -z 1024 1024 Resources/tariffmill_icon.png --out Resources/tariffmill_icon.iconset/icon_512x512@2x.png

            # Convert to .icns
            iconutil -c icns Resources/tariffmill_icon.iconset -o Resources/tariffmill_icon.icns
            rm -rf Resources/tariffmill_icon.iconset
        else
            echo "Warning: sips not available (not on macOS). Icon will use default."
        fi
    fi
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist

# Build with PyInstaller
echo "Building application..."
pyinstaller TariffMill_macOS.spec --clean

# Check if build succeeded
if [ -d "dist/TariffMill.app" ]; then
    echo ""
    echo "=========================================="
    echo "Build successful!"
    echo "Application: dist/TariffMill.app"
    echo "=========================================="

    # Create DMG if create-dmg is available
    if command -v create-dmg &> /dev/null; then
        echo ""
        echo "Creating DMG installer..."

        VERSION=$(grep -o 'version = "[^"]*"' ../pyproject.toml | cut -d'"' -f2)

        create-dmg \
            --volname "TariffMill" \
            --volicon "Resources/tariffmill_icon.icns" \
            --window-pos 200 120 \
            --window-size 600 400 \
            --icon-size 100 \
            --icon "TariffMill.app" 150 190 \
            --hide-extension "TariffMill.app" \
            --app-drop-link 450 190 \
            "dist/TariffMill_${VERSION}_macOS.dmg" \
            "dist/TariffMill.app"

        echo "DMG created: dist/TariffMill_${VERSION}_macOS.dmg"
    else
        echo ""
        echo "Tip: Install create-dmg to generate a DMG installer:"
        echo "  brew install create-dmg"
    fi
else
    echo "Error: Build failed!"
    exit 1
fi

echo ""
echo "Done!"