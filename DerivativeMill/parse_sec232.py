"""
Parse SEC232.txt and create a comprehensive CSV file with Section 232 tariff information
"""
import csv
import pandas as pd
from pathlib import Path

# Input and output paths
input_file = Path(r"c:\Users\hpayne\Documents\DevHouston\metalsplitter\Resources\SEC232.txt")
output_file = Path(r"c:\Users\hpayne\Documents\DevHouston\Packaged\DerivativeMill\Section_232_Tariffs_Compiled.csv")

# Read the file
steel_codes = []
aluminum_codes = []

with open(input_file, 'r') as f:
    reader = csv.reader(f)
    header = next(reader)  # Skip header
    
    for row in reader:
        if len(row) >= 2:
            steel = row[0].strip().replace('"', '')
            aluminum = row[1].strip().replace('"', '')
            
            if steel and steel != "steel tariffs":
                steel_codes.append(steel)
            if aluminum and aluminum != "aluminum tariffs":
                aluminum_codes.append(aluminum)

# Remove duplicates and sort
steel_codes = sorted(list(set(steel_codes)))
aluminum_codes = sorted(list(set(aluminum_codes)))

print(f"Found {len(steel_codes)} unique Steel HTS codes")
print(f"Found {len(aluminum_codes)} unique Aluminum HTS codes")

# Create comprehensive data structure
data = []

# Add steel codes
for code in steel_codes:
    # Determine chapter and classify
    chapter = code[:2]
    
    # Determine if it's primary or derivative based on Federal Register classifications
    if chapter in ['72', '73']:
        if chapter == '72':
            classification = "Primary Steel Article"
            chapter_desc = "Chapter 72: Iron and Steel"
        else:  # Chapter 73
            classification = "Derivative Steel Article"
            chapter_desc = "Chapter 73: Articles of Iron or Steel"
    else:
        classification = "Derivative Steel Article (Other Chapters)"
        chapter_desc = f"Chapter {chapter}: Non-Steel Chapter"
    
    data.append({
        'HTS Code': code,
        'Material': 'Steel',
        'Classification': classification,
        'Chapter': chapter,
        'Chapter Description': chapter_desc,
        'Declaration Required': '08 - MELT & POUR',
        'Notes': 'Section 232 Steel Tariff - Subject to 25% or 50% additional duty'
    })

# Add aluminum codes
for code in aluminum_codes:
    # Determine chapter and classify
    chapter = code[:2]
    
    # Determine if it's primary or derivative based on Federal Register classifications
    if chapter == '76':
        # Check specific ranges for primary vs derivative
        if code[:4] in ['7601', '7604', '7605', '7606', '7607', '7608', '7609']:
            classification = "Primary Aluminum Article"
            chapter_desc = "Chapter 76: Aluminum and Articles Thereof (Primary)"
        else:
            classification = "Derivative Aluminum Article"
            chapter_desc = "Chapter 76: Aluminum and Articles Thereof (Derivative)"
    else:
        classification = "Derivative Aluminum Article (Other Chapters)"
        chapter_desc = f"Chapter {chapter}: Non-Aluminum Chapter"
    
    data.append({
        'HTS Code': code,
        'Material': 'Aluminum',
        'Classification': classification,
        'Chapter': chapter,
        'Chapter Description': chapter_desc,
        'Declaration Required': '07 - SMELT & CAST',
        'Notes': 'Section 232 Aluminum Tariff - Subject to 10% or 25% additional duty'
    })

# Create DataFrame and save to CSV
df = pd.DataFrame(data)
df = df.sort_values(['Material', 'Chapter', 'HTS Code'])

# Save to CSV
df.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"\n✓ Created comprehensive CSV file: {output_file}")
print(f"  Total records: {len(df)}")
print(f"\n  Steel codes: {len(steel_codes)}")
print(f"  Aluminum codes: {len(aluminum_codes)}")

# Print summary statistics
print("\n" + "="*70)
print("SUMMARY BY CLASSIFICATION")
print("="*70)
summary = df.groupby(['Material', 'Classification']).size().reset_index(name='Count')
for _, row in summary.iterrows():
    print(f"  {row['Material']:10} - {row['Classification']:50} {row['Count']:4} codes")

print("\n" + "="*70)
print("SUMMARY BY CHAPTER")
print("="*70)
chapter_summary = df.groupby(['Material', 'Chapter']).size().reset_index(name='Count')
for _, row in chapter_summary.iterrows():
    print(f"  {row['Material']:10} - Chapter {row['Chapter']:2}  {row['Count']:4} codes")

print("\n✓ Processing complete!")
