"""
Parse Section 232 Copper tariff codes and add to compiled CSV
Effective August 1, 2025
"""
import pandas as pd
import re

# Read existing CSV
df_existing = pd.read_csv('Section_232_Tariffs_Compiled.csv')
print(f"Existing records: {len(df_existing)}")

# Read copper HTS list
with open(r'c:\Users\hpayne\Documents\CBP_INFO\CopperHTSlist073125.txt', 'r', encoding='utf-8', errors='ignore') as f:
    copper_content = f.read()

# Extract HTS codes
hts_pattern = r'\b\d{4}\.\d{2}\.\d{2}\b'
copper_codes = re.findall(hts_pattern, copper_content)
copper_codes = sorted(set(copper_codes))

print(f"Found {len(copper_codes)} unique Copper HTS codes")

# Create copper records
copper_records = []
for hts_code in copper_codes:
    chapter = hts_code[:2]
    
    # Determine classification based on heading
    if chapter == '74':
        # Chapter 74 is copper and copper articles
        heading = hts_code[:4]
        
        if heading in ['7406', '7407', '7408', '7409', '7410', '7411', '7412']:
            classification = 'Semi-Finished Copper Product'
        else:
            classification = 'Intensive Copper Derivative Product'
        
        chapter_desc = 'Chapter 74: Copper and articles thereof'
    elif chapter == '85':
        classification = 'Intensive Copper Derivative Product'
        chapter_desc = 'Chapter 85: Electrical machinery and equipment and parts thereof'
    else:
        classification = 'Intensive Copper Derivative Product'
        chapter_desc = f'Chapter {chapter}: Non-Copper Chapter'
    
    copper_records.append({
        'HTS Code': hts_code,
        'Material': 'Copper',
        'Classification': classification,
        'Chapter': chapter,
        'Chapter Description': chapter_desc,
        'Declaration Required': '11 - COPPER CONTENT',
        'Notes': 'Section 232 Copper Tariff - 50% duty on copper content value (Effective Aug 1, 2025)'
    })

df_copper = pd.DataFrame(copper_records)
print(f"\nNew copper codes: {len(df_copper)}")

# Check for overlaps
existing_codes = set(df_existing['HTS Code'].values)
copper_code_set = set(df_copper['HTS Code'].values)
overlaps = existing_codes.intersection(copper_code_set)

if overlaps:
    print(f"Overlapping codes: {len(overlaps)}")
    print(f"  {sorted(overlaps)}")
    # Remove overlaps from copper records
    df_copper = df_copper[~df_copper['HTS Code'].isin(overlaps)]
    print(f"Copper codes after removing overlaps: {len(df_copper)}")

# Combine and sort
df_combined = pd.concat([df_existing, df_copper], ignore_index=True)
df_combined = df_combined.sort_values(['Material', 'Chapter', 'HTS Code'])

print(f"\nTotal records: {len(df_combined)}")
print("\nSummary by Material:")
print(df_combined.groupby('Material').size())

# Save
df_combined.to_csv('Section_232_Tariffs_Compiled.csv', index=False)
print(f"\nUpdated CSV saved with {len(df_combined)} total records")

# Show copper summary
print("\nCopper tariff codes by classification:")
copper_summary = df_copper.groupby('Classification').size()
for classification, count in copper_summary.items():
    print(f"  {classification}: {count} codes")

print("\nCopper codes by chapter:")
chapter_summary = df_copper.groupby('Chapter').size()
for chapter, count in chapter_summary.items():
    print(f"  Chapter {chapter}: {count} codes")
