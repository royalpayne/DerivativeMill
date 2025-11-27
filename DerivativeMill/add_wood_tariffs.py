"""
Parse Section 232 Wood tariff codes and add to compiled CSV
Effective October 14, 2025
"""
import pandas as pd

# Read existing CSV
df_existing = pd.read_csv('Section_232_Tariffs_Compiled.csv')
print(f"Existing records: {len(df_existing)}")

# Define wood tariff codes from CSMS 66492057
wood_codes = {
    # Softwood Timber and Lumber (10% all countries)
    '4403.11.00': ('Softwood Timber', 'Chapter 44', '09 - TIMBER/LUMBER', 'Section 232 Wood Tariff - Softwood Timber/Lumber - 10% additional duty (Effective Oct 14, 2025)'),
    '4403.21.01': ('Softwood Timber', 'Chapter 44', '09 - TIMBER/LUMBER', 'Section 232 Wood Tariff - Softwood Timber/Lumber - 10% additional duty (Effective Oct 14, 2025)'),
    '4403.22.01': ('Softwood Timber', 'Chapter 44', '09 - TIMBER/LUMBER', 'Section 232 Wood Tariff - Softwood Timber/Lumber - 10% additional duty (Effective Oct 14, 2025)'),
    '4403.23.01': ('Softwood Timber', 'Chapter 44', '09 - TIMBER/LUMBER', 'Section 232 Wood Tariff - Softwood Timber/Lumber - 10% additional duty (Effective Oct 14, 2025)'),
    '4403.24.01': ('Softwood Timber', 'Chapter 44', '09 - TIMBER/LUMBER', 'Section 232 Wood Tariff - Softwood Timber/Lumber - 10% additional duty (Effective Oct 14, 2025)'),
    '4403.25.01': ('Softwood Timber', 'Chapter 44', '09 - TIMBER/LUMBER', 'Section 232 Wood Tariff - Softwood Timber/Lumber - 10% additional duty (Effective Oct 14, 2025)'),
    '4403.26.01': ('Softwood Timber', 'Chapter 44', '09 - TIMBER/LUMBER', 'Section 232 Wood Tariff - Softwood Timber/Lumber - 10% additional duty (Effective Oct 14, 2025)'),
    '4403.99.01': ('Softwood Timber', 'Chapter 44', '09 - TIMBER/LUMBER', 'Section 232 Wood Tariff - Softwood Timber/Lumber - 10% additional duty (Effective Oct 14, 2025)'),
    '4406.11.00': ('Softwood Timber', 'Chapter 44', '09 - TIMBER/LUMBER', 'Section 232 Wood Tariff - Softwood Timber/Lumber - 10% additional duty (Effective Oct 14, 2025)'),
    '4406.91.00': ('Softwood Timber', 'Chapter 44', '09 - TIMBER/LUMBER', 'Section 232 Wood Tariff - Softwood Timber/Lumber - 10% additional duty (Effective Oct 14, 2025)'),
    '4407.11.00': ('Softwood Lumber', 'Chapter 44', '09 - TIMBER/LUMBER', 'Section 232 Wood Tariff - Softwood Timber/Lumber - 10% additional duty (Effective Oct 14, 2025)'),
    '4407.12.00': ('Softwood Lumber', 'Chapter 44', '09 - TIMBER/LUMBER', 'Section 232 Wood Tariff - Softwood Timber/Lumber - 10% additional duty (Effective Oct 14, 2025)'),
    '4407.13.00': ('Softwood Lumber', 'Chapter 44', '09 - TIMBER/LUMBER', 'Section 232 Wood Tariff - Softwood Timber/Lumber - 10% additional duty (Effective Oct 14, 2025)'),
    '4407.14.00': ('Softwood Lumber', 'Chapter 44', '09 - TIMBER/LUMBER', 'Section 232 Wood Tariff - Softwood Timber/Lumber - 10% additional duty (Effective Oct 14, 2025)'),
    '4407.19.00': ('Softwood Lumber', 'Chapter 44', '09 - TIMBER/LUMBER', 'Section 232 Wood Tariff - Softwood Timber/Lumber - 10% additional duty (Effective Oct 14, 2025)'),
    
    # Upholstered Wooden Furniture (25% most countries, 10-15% UK/Japan/EU)
    '9401.61.4011': ('Upholstered Wooden Furniture', 'Chapter 94', '10 - FURNITURE/CABINETS', 'Section 232 Wood Tariff - Furniture - 25% (or 10-15% UK/JP/EU) additional duty (Effective Oct 14, 2025)'),
    '9401.61.4031': ('Upholstered Wooden Furniture', 'Chapter 94', '10 - FURNITURE/CABINETS', 'Section 232 Wood Tariff - Furniture - 25% (or 10-15% UK/JP/EU) additional duty (Effective Oct 14, 2025)'),
    '9401.61.6011': ('Upholstered Wooden Furniture', 'Chapter 94', '10 - FURNITURE/CABINETS', 'Section 232 Wood Tariff - Furniture - 25% (or 10-15% UK/JP/EU) additional duty (Effective Oct 14, 2025)'),
    '9401.61.6031': ('Upholstered Wooden Furniture', 'Chapter 94', '10 - FURNITURE/CABINETS', 'Section 232 Wood Tariff - Furniture - 25% (or 10-15% UK/JP/EU) additional duty (Effective Oct 14, 2025)'),
    
    # Kitchen Cabinets/Vanities and Parts (25% most countries, 10-15% UK/Japan/EU)
    '9403.40.9060': ('Kitchen Cabinets/Vanities', 'Chapter 94', '10 - FURNITURE/CABINETS', 'Section 232 Wood Tariff - Cabinets/Vanities - 25% (or 10-15% UK/JP/EU) additional duty (Effective Oct 14, 2025)'),
    '9403.60.8093': ('Kitchen Cabinets/Vanities', 'Chapter 94', '10 - FURNITURE/CABINETS', 'Section 232 Wood Tariff - Cabinets/Vanities - 25% (or 10-15% UK/JP/EU) additional duty (Effective Oct 14, 2025)'),
    '9403.91.0080': ('Kitchen Cabinets/Vanities Parts', 'Chapter 94', '10 - FURNITURE/CABINETS', 'Section 232 Wood Tariff - Cabinets/Vanities - 25% (or 10-15% UK/JP/EU) additional duty (Effective Oct 14, 2025)'),
}

# Create wood records
wood_records = []
for hts_code, (classification, chapter, declaration, notes) in wood_codes.items():
    chapter_num = hts_code[:2]
    
    if chapter_num == '44':
        chapter_desc = 'Chapter 44: Wood and articles of wood; wood charcoal'
    else:
        chapter_desc = 'Chapter 94: Furniture; bedding, mattresses, etc.'
    
    wood_records.append({
        'HTS Code': hts_code,
        'Material': 'Wood',
        'Classification': classification,
        'Chapter': chapter_num,
        'Chapter Description': chapter_desc,
        'Declaration Required': declaration,
        'Notes': notes
    })

df_wood = pd.DataFrame(wood_records)
print(f"\nNew wood codes: {len(df_wood)}")

# Check for overlaps
existing_codes = set(df_existing['HTS Code'].values)
wood_code_set = set(df_wood['HTS Code'].values)
overlaps = existing_codes.intersection(wood_code_set)

if overlaps:
    print(f"Overlapping codes: {len(overlaps)}")
    print(f"  {sorted(overlaps)}")
    # Remove overlaps from wood records
    df_wood = df_wood[~df_wood['HTS Code'].isin(overlaps)]
    print(f"Wood codes after removing overlaps: {len(df_wood)}")

# Combine and sort
df_combined = pd.concat([df_existing, df_wood], ignore_index=True)
df_combined = df_combined.sort_values(['Material', 'Chapter', 'HTS Code'])

print(f"\nTotal records: {len(df_combined)}")
print("\nSummary by Material:")
print(df_combined.groupby('Material').size())

# Save
df_combined.to_csv('Section_232_Tariffs_Compiled.csv', index=False)
print(f"\nUpdated CSV saved with {len(df_combined)} total records")

# Show wood summary
print("\nWood tariff codes by type:")
wood_summary = df_wood.groupby('Classification').size()
for classification, count in wood_summary.items():
    print(f"  {classification}: {count} codes")
