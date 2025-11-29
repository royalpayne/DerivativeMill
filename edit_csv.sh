#!/bin/bash
# Quick CSV/Excel editor using VisiData
# Usage: ./edit_csv.sh [filename]

cd "$(dirname "$0")"

if [ -z "$1" ]; then
    echo "Usage: $0 <csv/xlsx file>"
    echo ""
    echo "Available files in Input folder:"
    ls -1 DerivativeMill/Input/*.csv 2>/dev/null || echo "  (no CSV files found)"
    exit 1
fi

source venv/bin/activate
visidata "$1"
