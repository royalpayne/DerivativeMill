# VisiData Quick Reference Guide

VisiData is now installed and ready to edit your CSV/Excel files!

## How to Use

### Option 1: Using the helper script
```bash
cd /home/heath/work/app/Project_mv
./edit_csv.sh DerivativeMill/Input/your_file.csv
```

### Option 2: Direct command
```bash
source venv/bin/activate
vd DerivativeMill/Input/your_file.csv
```

## Essential Keyboard Shortcuts

### Navigation
- **Arrow keys** - Move around cells
- **h/j/k/l** - Vim-style navigation (left/down/up/right)
- **PageUp/PageDown** - Scroll pages
- **Home/End** - Jump to first/last column
- **g + Home** - Jump to top of sheet
- **g + End** - Jump to bottom of sheet

### Editing
- **e** - Edit current cell
- **Enter** - Finish editing
- **Ctrl+C** or **Esc** - Cancel editing
- **d** - Delete current row
- **a** - Add new row after current
- **za** - Add new column

### Selection
- **s** - Select current row
- **t** - Toggle selection of current row
- **u** - Unselect current row
- **gs** - Select all rows
- **gu** - Unselect all rows

### Sorting & Filtering
- **[** - Sort ascending by current column
- **]** - Sort descending by current column
- **|** - Select rows by regex in current column
- **\\** - Unselect rows by regex
- **"** - Create new sheet with only selected rows

### Search
- **/** - Search forward
- **?** - Search backward
- **n** - Go to next search result
- **N** - Go to previous search result

### Columns
- **-** - Hide current column
- **_** - Adjust column width
- **!** - Set current column as key column (primary)
- **#** - Set column type to integer
- **%** - Set column type to float
- **@** - Set column type to date
- **$** - Set column type to currency

### File Operations
- **Ctrl+S** - Save file
- **Ctrl+Q** - Quit (will prompt to save if modified)
- **Ctrl+R** - Reload file from disk
- **Ctrl+O** - Open options menu

### Undo/Redo
- **U** - Undo last action
- **Ctrl+Y** - Redo

### Other Useful
- **I** - Show/hide rows with errors
- **z?** - Show help menu
- **Ctrl+H** - Full help system
- **F** - Toggle frozen columns
- **Space** - Open sheet menu

## Working with CSV Files

### Viewing data
```bash
# View a CSV file
vd file.csv

# View multiple files
vd file1.csv file2.csv
```

### Editing workflow
1. Open file: `vd file.csv`
2. Navigate to cell you want to edit
3. Press `e` to edit
4. Type new value
5. Press `Enter` to confirm
6. Press `Ctrl+S` to save
7. Press `q` to quit

### Common tasks

**Add a new row:**
1. Press `a` to add row after current
2. Press `e` on each cell to fill in data

**Delete a row:**
1. Navigate to the row
2. Press `d`

**Sort by column:**
1. Navigate to the column
2. Press `[` for ascending or `]` for descending

**Filter rows:**
1. Navigate to the column to filter by
2. Press `|`
3. Enter regex pattern
4. Press `Enter`
5. Press `"` to create new sheet with only matching rows

**Save modified file:**
- Press `Ctrl+S`

## Tips for DerivativeMill CSV Files

Your invoice CSV files typically have columns like:
- Part Number
- Description
- Quantity
- Unit Price
- Total Value
- HTS Code
- Country of Origin

**Quick edits:**
- Edit HTS codes: Navigate to HTS column, press `e`, edit, `Enter`
- Add missing parts: Press `a` to add row, fill in each cell
- Delete invalid rows: Navigate to row, press `d`

**Verify data before saving:**
- Use `/` to search for empty cells
- Use `[` to sort and check for duplicates
- Use `#` on numeric columns to validate numbers

## Getting Help

- **z?** - Quick help menu
- **Ctrl+H** - Full help documentation
- Visit: https://www.visidata.org/docs/

## Exit VisiData

- **q** - Quit current sheet
- **Ctrl+Q** - Quit VisiData (prompts to save if modified)

---

**Installed at:** /home/heath/work/app/Project_mv/venv/bin/vd
**Helper script:** /home/heath/work/app/Project_mv/edit_csv.sh
