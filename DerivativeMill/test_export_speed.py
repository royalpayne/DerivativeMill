"""
Diagnostic tool to identify export performance bottlenecks.
Tests: network path access, file write speed, Excel generation speed.
"""
import time
import pandas as pd
from pathlib import Path
from openpyxl.styles import Font
import tempfile
import shutil

def test_directory_access(output_dir):
    """Test how long it takes to access the output directory"""
    print(f"\n1. Testing directory access: {output_dir}")
    
    start = time.time()
    exists = output_dir.exists()
    elapsed = time.time() - start
    print(f"   - Directory exists check: {elapsed:.3f}s {'✓' if exists else '✗ MISSING'}")
    
    if not exists:
        return False
    
    start = time.time()
    files = list(output_dir.glob("*.xlsx"))
    elapsed = time.time() - start
    print(f"   - List .xlsx files ({len(files)} found): {elapsed:.3f}s")
    
    return True

def test_file_write_speed(output_dir):
    """Test raw file write speed to the directory"""
    print(f"\n2. Testing file write speed to: {output_dir}")
    
    test_data = b"x" * (1024 * 1024)  # 1MB of data
    test_file = output_dir / "test_write_speed.tmp"
    
    try:
        # Write test
        start = time.time()
        with open(test_file, 'wb') as f:
            for _ in range(10):  # Write 10MB
                f.write(test_data)
        elapsed = time.time() - start
        mb_per_sec = 10 / elapsed
        print(f"   - Write 10MB: {elapsed:.3f}s ({mb_per_sec:.1f} MB/s)")
        
        # Read test
        start = time.time()
        with open(test_file, 'rb') as f:
            _ = f.read()
        elapsed = time.time() - start
        mb_per_sec = 10 / elapsed
        print(f"   - Read 10MB: {elapsed:.3f}s ({mb_per_sec:.1f} MB/s)")
        
        # Delete test
        start = time.time()
        test_file.unlink()
        elapsed = time.time() - start
        print(f"   - Delete file: {elapsed:.3f}s")
        
        return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        if test_file.exists():
            test_file.unlink()
        return False

def test_excel_generation(output_dir, num_rows=100):
    """Test Excel file generation speed"""
    print(f"\n3. Testing Excel generation ({num_rows} rows)")
    
    # Create sample data similar to export
    data = {
        'Product No': [f'PART{i:05d}' for i in range(num_rows)],
        'ValueUSD': [100.50 + i for i in range(num_rows)],
        'HTSCode': ['7326.90.8587' for _ in range(num_rows)],
        'MID': ['US' for _ in range(num_rows)],
        'CalcWtNet': [10.5 for _ in range(num_rows)],
        'DecTypeCd': ['CO' for _ in range(num_rows)],
        'CountryofMelt': ['US' for _ in range(num_rows)],
        'CountryOfCast': ['US' for _ in range(num_rows)],
        'PrimCountryOfSmelt': ['' for _ in range(num_rows)],
        'PrimSmeltFlag': ['' for _ in range(num_rows)],
        'SteelRatio': ['100.0%' for _ in range(num_rows)],
        'NonSteelRatio': ['0.0%' for _ in range(num_rows)],
        '232_Status': ['Y' for _ in range(num_rows)]
    }
    df = pd.DataFrame(data)
    
    # Test 1: Write to temp location (fast local disk)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = Path(tmp.name)
    
    start = time.time()
    with pd.ExcelWriter(tmp_path, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    elapsed_temp = time.time() - start
    print(f"   - Write to temp location: {elapsed_temp:.3f}s")
    
    tmp_path.unlink()
    
    # Test 2: Write to actual output directory
    output_file = output_dir / "test_excel_speed.xlsx"
    
    start = time.time()
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    elapsed_output = time.time() - start
    print(f"   - Write to output directory: {elapsed_output:.3f}s")
    
    # Test 3: Write with cell formatting (like red text)
    start = time.time()
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
        ws = next(iter(writer.sheets.values()))
        red_font = Font(color="00FF0000")
        # Apply red font to every other row
        for idx in range(0, num_rows, 2):
            row_num = idx + 2
            for col_idx in range(1, len(df.columns) + 1):
                cell = ws.cell(row=row_num, column=col_idx)
                cell.font = red_font
    elapsed_formatted = time.time() - start
    print(f"   - Write with formatting: {elapsed_formatted:.3f}s")
    
    # Cleanup
    if output_file.exists():
        output_file.unlink()
    
    # Analysis
    if elapsed_output > elapsed_temp * 3:
        print(f"\n   ⚠ WARNING: Output directory is {elapsed_output/elapsed_temp:.1f}x slower than local temp!")
        print(f"   This suggests network/disk latency is the bottleneck.")
    
    if elapsed_formatted > elapsed_output * 1.5:
        print(f"\n   ⚠ Cell formatting adds {(elapsed_formatted - elapsed_output):.2f}s overhead")

def test_move_performance(output_dir):
    """Test file move operation (like moving to Processed folder)"""
    print(f"\n4. Testing file move/rename operations")
    
    # Create test file
    test_file = output_dir / "test_move_source.tmp"
    test_dest = output_dir / "test_move_dest.tmp"
    
    try:
        test_file.write_bytes(b"test" * 1000)
        
        start = time.time()
        test_file.rename(test_dest)
        elapsed = time.time() - start
        print(f"   - Rename/move file: {elapsed:.3f}s")
        
        if test_dest.exists():
            test_dest.unlink()
        
        if elapsed > 0.5:
            print(f"   ⚠ WARNING: File move is unusually slow ({elapsed:.2f}s)")
            
    except Exception as e:
        print(f"   ✗ Error: {e}")
        for f in [test_file, test_dest]:
            if f.exists():
                f.unlink()

def run_diagnostics(output_dir_path):
    """Run all diagnostic tests"""
    output_dir = Path(output_dir_path)
    
    print("="*60)
    print("EXPORT PERFORMANCE DIAGNOSTICS")
    print("="*60)
    print(f"\nOutput Directory: {output_dir}")
    
    # Check if it's a network path
    if str(output_dir).startswith('\\\\') or ':' in str(output_dir)[:3]:
        print(f"Type: {'Network Path' if str(output_dir).startswith('\\\\') else 'Local Drive'}")
    
    total_start = time.time()
    
    # Run tests
    if test_directory_access(output_dir):
        test_file_write_speed(output_dir)
        test_excel_generation(output_dir, num_rows=100)
        test_move_performance(output_dir)
    
    total_elapsed = time.time() - total_start
    
    print("\n" + "="*60)
    print(f"Total diagnostic time: {total_elapsed:.2f}s")
    print("="*60)
    
    # Recommendations
    print("\n📊 RECOMMENDATIONS:")
    print("  - If directory access > 0.1s: Network latency issue")
    print("  - If write speed < 5 MB/s: Slow disk/network")
    print("  - If Excel generation to output >> temp: Use local temp then copy")
    print("  - If formatting adds > 2s: Consider async formatting")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        output_path = sys.argv[1]
    else:
        # Try to read from the app's config
        try:
            from pathlib import Path
            base = Path(__file__).parent
            db_path = base / "derivativemill.db"
            
            if db_path.exists():
                import sqlite3
                conn = sqlite3.connect(str(db_path))
                c = conn.cursor()
                c.execute("SELECT value FROM app_config WHERE key = 'output_dir'")
                row = c.fetchone()
                conn.close()
                
                if row:
                    output_path = row[0]
                    print(f"Using output directory from database: {output_path}")
                else:
                    output_path = str(base / "Output")
            else:
                output_path = str(base / "Output")
        except Exception as e:
            print(f"Error reading config: {e}")
            output_path = "./Output"
    
    run_diagnostics(output_path)
