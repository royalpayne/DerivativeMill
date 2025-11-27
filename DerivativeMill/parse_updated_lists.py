"""
Parse updated Steel and Aluminum HTS lists (August 18, 2025) and MHDV codes
Create comprehensive Section 232 tariff database
"""
import pandas as pd
import re

def extract_hts_codes(text):
    """Extract HTS codes from text using regex"""
    hts_pattern = r'\b\d{4}\.\d{2}\.\d{2,4}\b'
    codes = re.findall(hts_pattern, text)
    return sorted(set(codes))

def get_chapter_description(chapter):
    """Get description for HTS chapter"""
    descriptions = {
        '04': 'Chapter 04: Dairy produce; birds\' eggs; natural honey',
        '21': 'Chapter 21: Miscellaneous edible preparations',
        '22': 'Chapter 22: Beverages, spirits and vinegar',
        '27': 'Chapter 27: Mineral fuels, mineral oils',
        '29': 'Chapter 29: Organic chemicals',
        '30': 'Chapter 30: Pharmaceutical products',
        '32': 'Chapter 32: Tanning or dyeing extracts; paints and varnishes',
        '33': 'Chapter 33: Essential oils and resinoids; perfumery, cosmetic or toilet preparations',
        '34': 'Chapter 34: Soap, organic surface-active agents, washing preparations, lubricating preparations',
        '35': 'Chapter 35: Albuminoidal substances; modified starches; glues; enzymes',
        '37': 'Chapter 37: Photographic or cinematographic goods',
        '38': 'Chapter 38: Miscellaneous chemical products',
        '40': 'Chapter 40: Rubber and articles thereof',
        '66': 'Chapter 66: Umbrellas, walking-sticks, seat-sticks, whips, riding-crops',
        '70': 'Chapter 70: Glass and glassware',
        '72': 'Chapter 72: Iron and Steel',
        '73': 'Chapter 73: Articles of Iron or Steel',
        '76': 'Chapter 76: Aluminum and articles thereof',
        '83': 'Chapter 83: Miscellaneous articles of base metal',
        '84': 'Chapter 84: Nuclear reactors, boilers, machinery and mechanical appliances; parts thereof',
        '85': 'Chapter 85: Electrical machinery and equipment and parts thereof',
        '87': 'Chapter 87: Vehicles; Parts and Accessories thereof',
        '88': 'Chapter 88: Aircraft, spacecraft, and parts thereof',
        '90': 'Chapter 90: Optical, photographic, cinematographic, measuring, checking, precision, medical or surgical instruments',
        '94': 'Chapter 94: Furniture; bedding, mattresses, etc.',
        '95': 'Chapter 95: Toys, games and sports requisites; parts and accessories thereof',
        '96': 'Chapter 96: Miscellaneous manufactured articles',
        '99': 'Chapter 99: Special classification provisions'
    }
    return descriptions.get(chapter, f'Chapter {chapter}: Non-Steel/Aluminum Chapter')

# Read Steel HTS list
print("Reading Steel HTS list...")
with open(r'c:\Users\hpayne\Downloads\Updated steelHTSlist 081525.txt', 'r', encoding='utf-8') as f:
    steel_content = f.read()

steel_codes = extract_hts_codes(steel_content)
print(f"Found {len(steel_codes)} unique Steel HTS codes")

# Read Aluminum HTS list
print("\nReading Aluminum HTS list...")
with open(r'c:\Users\hpayne\Downloads\Updated aluminumHTSlist 081525.txt', 'r', encoding='utf-8') as f:
    aluminum_content = f.read()

aluminum_codes = extract_hts_codes(aluminum_content)
print(f"Found {len(aluminum_codes)} unique Aluminum HTS codes")

# Read MHDV codes
print("\nReading MHDV codes...")
with open(r'c:\Users\hpayne\Downloads\Section 232 MHDV Attachment (002).txt', 'r', encoding='utf-8') as f:
    mhdv_content = f.read()

mhdv_codes = extract_hts_codes(mhdv_content)
print(f"Found {len(mhdv_codes)} unique MHDV HTS codes")

# Check for overlaps
steel_aluminum_overlap = set(steel_codes).intersection(set(aluminum_codes))
print(f"\nCodes in both Steel and Aluminum: {len(steel_aluminum_overlap)}")

# Create records
all_records = []

# Process Steel codes
for hts_code in steel_codes:
    chapter = hts_code[:2]
    
    # Determine classification
    if chapter in ['72']:
        classification = "Primary Steel Article"
    elif chapter in ['73']:
        classification = "Derivative Steel Article"
    else:
        classification = "Derivative Steel Article (Other Chapters)"
    
    # Check if it's also MHDV
    is_mhdv = hts_code in mhdv_codes
    notes = "Section 232 Steel Tariff - Subject to 25% or 50% additional duty"
    if is_mhdv:
        notes += " (MHDV/MHDVP/Buses - Effective Nov 1, 2025)"
    
    all_records.append({
        'HTS Code': hts_code,
        'Material': 'Steel',
        'Classification': classification,
        'Chapter': chapter,
        'Chapter Description': get_chapter_description(chapter),
        'Declaration Required': '08 - MELT & POUR',
        'Notes': notes
    })

# Process Aluminum codes
for hts_code in aluminum_codes:
    chapter = hts_code[:2]
    
    # Determine classification
    if chapter in ['76'] and hts_code in ['7601', '7604', '7605', '7606', '7607', '7608', '7609']:
        classification = "Primary Aluminum Article"
    elif chapter in ['76']:
        classification = "Derivative Aluminum Article"
    else:
        classification = "Derivative Aluminum Article (Other Chapters)"
    
    # Check if it's also MHDV
    is_mhdv = hts_code in mhdv_codes
    notes = "Section 232 Aluminum Tariff - Subject to 10% or 25% additional duty"
    if is_mhdv:
        notes += " (MHDV/MHDVP/Buses - Effective Nov 1, 2025)"
    
    all_records.append({
        'HTS Code': hts_code,
        'Material': 'Aluminum',
        'Classification': classification,
        'Chapter': chapter,
        'Chapter Description': get_chapter_description(chapter),
        'Declaration Required': '07 - SMELT & CAST',
        'Notes': notes
    })

# Create DataFrame and sort
df = pd.DataFrame(all_records)
df = df.sort_values(['Material', 'Chapter', 'HTS Code'])

# Remove exact duplicates (keep first occurrence)
df_deduped = df.drop_duplicates(subset=['HTS Code', 'Material'], keep='first')

print(f"\nTotal records before deduplication: {len(df)}")
print(f"Total records after deduplication: {len(df_deduped)}")

# Save to CSV
output_file = 'Section_232_Tariffs_Complete.csv'
df_deduped.to_csv(output_file, index=False)

print(f"\nSaved to: {output_file}")

# Summary statistics
print("\nSummary by Material:")
print(df_deduped.groupby('Material').size())

print("\nSummary by Classification:")
print(df_deduped.groupby(['Material', 'Classification']).size())

print("\nTop 10 chapters by count:")
chapter_counts = df_deduped.groupby('Chapter').size().sort_values(ascending=False).head(10)
for chapter, count in chapter_counts.items():
    print(f"  Chapter {chapter}: {count} codes")

# Check for codes that appear in both materials
both_materials = df_deduped.groupby('HTS Code').size()
dual_material_codes = both_materials[both_materials > 1].index.tolist()
if dual_material_codes:
    print(f"\n{len(dual_material_codes)} codes appear for both Steel and Aluminum:")
    print(f"  Examples: {dual_material_codes[:5]}")
