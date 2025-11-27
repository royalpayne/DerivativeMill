"""
Parse MHDV Section 232 HTS codes and add to compiled tariff CSV
"""
import pandas as pd
import re

# Read the MHDV attachment file
with open(r'c:\Users\hpayne\Downloads\Section 232 MHDV Attachment (002).txt', 'r', encoding='utf-8') as f:
    content = f.read()

# Extract HTS codes using regex pattern
hts_pattern = r'\b\d{4}\.\d{2}\.\d{2,4}\b'
all_codes = re.findall(hts_pattern, content)

# Remove duplicates and sort
unique_codes = sorted(set(all_codes))

print(f"Found {len(unique_codes)} unique HTS codes in MHDV document")

# Determine chapter and classification for each code
new_records = []

for hts_code in unique_codes:
    chapter = hts_code[:2]
    
    # Determine material and classification based on chapter
    if chapter in ['87']:  # Vehicles and parts
        classification = "Derivative Steel Article"
        material = "Steel"
        chapter_desc = f"Chapter {chapter}: Vehicles; Parts and Accessories thereof"
        declaration = "08 - MELT & POUR"
        notes = "Section 232 Steel Tariff - MHDV/MHDVP/Buses - Subject to 25% or 50% additional duty (Effective Nov 1, 2025)"
    elif chapter in ['40']:  # Rubber
        classification = "Derivative Steel Article (Other Chapters)"
        material = "Steel"
        chapter_desc = f"Chapter {chapter}: Rubber and articles thereof"
        declaration = "08 - MELT & POUR"
        notes = "Section 232 Steel Tariff - MHDV Parts - Subject to 25% or 50% additional duty (Effective Nov 1, 2025)"
    elif chapter in ['70']:  # Glass
        classification = "Derivative Steel Article (Other Chapters)"
        material = "Steel"
        chapter_desc = f"Chapter {chapter}: Glass and glassware"
        declaration = "08 - MELT & POUR"
        notes = "Section 232 Steel Tariff - MHDV Parts - Subject to 25% or 50% additional duty (Effective Nov 1, 2025)"
    elif chapter in ['73']:  # Articles of iron or steel
        classification = "Derivative Steel Article"
        material = "Steel"
        chapter_desc = f"Chapter {chapter}: Articles of Iron or Steel"
        declaration = "08 - MELT & POUR"
        notes = "Section 232 Steel Tariff - MHDV Parts - Subject to 25% or 50% additional duty (Effective Nov 1, 2025)"
    elif chapter in ['83']:  # Miscellaneous articles of base metal
        classification = "Derivative Steel Article (Other Chapters)"
        material = "Steel"
        chapter_desc = f"Chapter {chapter}: Miscellaneous articles of base metal"
        declaration = "08 - MELT & POUR"
        notes = "Section 232 Steel Tariff - MHDV Parts - Subject to 25% or 50% additional duty (Effective Nov 1, 2025)"
    elif chapter in ['84']:  # Machinery and mechanical appliances
        classification = "Derivative Steel Article (Other Chapters)"
        material = "Steel"
        chapter_desc = f"Chapter {chapter}: Nuclear reactors, boilers, machinery and mechanical appliances; parts thereof"
        declaration = "08 - MELT & POUR"
        notes = "Section 232 Steel Tariff - MHDV Parts - Subject to 25% or 50% additional duty (Effective Nov 1, 2025)"
    elif chapter in ['85']:  # Electrical machinery
        classification = "Derivative Steel Article (Other Chapters)"
        material = "Steel"
        chapter_desc = f"Chapter {chapter}: Electrical machinery and equipment and parts thereof"
        declaration = "08 - MELT & POUR"
        notes = "Section 232 Steel Tariff - MHDV Parts - Subject to 25% or 50% additional duty (Effective Nov 1, 2025)"
    elif chapter in ['90']:  # Optical, measuring instruments
        classification = "Derivative Steel Article (Other Chapters)"
        material = "Steel"
        chapter_desc = f"Chapter {chapter}: Optical, photographic, cinematographic, measuring, checking, precision, medical or surgical instruments"
        declaration = "08 - MELT & POUR"
        notes = "Section 232 Steel Tariff - MHDV Parts - Subject to 25% or 50% additional duty (Effective Nov 1, 2025)"
    elif chapter in ['94']:  # Furniture
        classification = "Derivative Steel Article (Other Chapters)"
        material = "Steel"
        chapter_desc = f"Chapter {chapter}: Furniture; bedding, mattresses, etc."
        declaration = "08 - MELT & POUR"
        notes = "Section 232 Steel Tariff - MHDV Parts - Subject to 25% or 50% additional duty (Effective Nov 1, 2025)"
    else:
        classification = "Derivative Steel Article (Other Chapters)"
        material = "Steel"
        chapter_desc = f"Chapter {chapter}: Non-Steel Chapter"
        declaration = "08 - MELT & POUR"
        notes = "Section 232 Steel Tariff - MHDV Parts - Subject to 25% or 50% additional duty (Effective Nov 1, 2025)"
    
    new_records.append({
        'HTS Code': hts_code,
        'Material': material,
        'Classification': classification,
        'Chapter': chapter,
        'Chapter Description': chapter_desc,
        'Declaration Required': declaration,
        'Notes': notes
    })

# Create DataFrame
new_df = pd.DataFrame(new_records)

# Load existing CSV
existing_df = pd.read_csv('Section_232_Tariffs_Compiled.csv')

print(f"\nExisting records: {len(existing_df)}")
print(f"New MHDV records: {len(new_df)}")

# Check for codes already in existing CSV
existing_codes = set(existing_df['HTS Code'].values)
new_codes = set(new_df['HTS Code'].values)
overlapping_codes = existing_codes.intersection(new_codes)

print(f"Overlapping codes: {len(overlapping_codes)}")
if overlapping_codes:
    print("Overlapping codes:", sorted(overlapping_codes)[:10], "..." if len(overlapping_codes) > 10 else "")

# Remove overlapping codes from new records
new_df_filtered = new_df[~new_df['HTS Code'].isin(overlapping_codes)]
print(f"New unique MHDV codes to add: {len(new_df_filtered)}")

# Combine and sort
combined_df = pd.concat([existing_df, new_df_filtered], ignore_index=True)
combined_df = combined_df.sort_values(['Material', 'Chapter', 'HTS Code'])

# Save updated CSV
combined_df.to_csv('Section_232_Tariffs_Compiled_with_MHDV.csv', index=False)

print(f"\nTotal records in updated CSV: {len(combined_df)}")
print(f"Saved to: Section_232_Tariffs_Compiled_with_MHDV.csv")

# Show summary by chapter
print("\nSummary of new MHDV codes by chapter:")
chapter_summary = new_df_filtered.groupby('Chapter').size().sort_index()
for chapter, count in chapter_summary.items():
    print(f"  Chapter {chapter}: {count} codes")
