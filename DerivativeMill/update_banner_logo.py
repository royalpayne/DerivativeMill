#!/usr/bin/env python3
"""
Script to update the banner logo with transparent background
Save your watermill image as 'new_logo.png' in the same directory as this script,
or provide the path as a command line argument.
"""
from PIL import Image
import numpy as np
import sys
import os

# Get input path from command line or use default
if len(sys.argv) > 1:
    input_image_path = sys.argv[1]
else:
    # Check common locations
    possible_paths = [
        "new_logo.png",
        "Resources/new_logo.png",
        "/home/heath/work/app/watermill.png",
        "../watermill.png"
    ]
    input_image_path = None
    for path in possible_paths:
        if os.path.exists(path):
            input_image_path = path
            break
    
    if not input_image_path:
        print("ERROR: No input image found.")
        print("Please save your watermill image and run:")
        print(f"  python3 {sys.argv[0]} <path-to-watermill-image>")
        print("\nOr save it as one of these:")
        for p in possible_paths:
            print(f"  - {p}")
        sys.exit(1)

output_image_path = "Resources/banner_bg.png"

print(f"Processing: {input_image_path}")
print(f"Output will be: {output_image_path}")

# Load the image
img = Image.open(input_image_path)
print(f"Original size: {img.size}, mode: {img.mode}")

# Convert to RGBA if not already
if img.mode != 'RGBA':
    img = img.convert('RGBA')

# Get the image data
data = np.array(img)

# Make light-colored background transparent
# The background appears to be light gray/white (around 230-245 RGB)
light_threshold = 220  # Pixels lighter than this become transparent

# Create mask for light pixels (potential background)
r, g, b, a = data[:, :, 0], data[:, :, 1], data[:, :, 2], data[:, :, 3]
is_light = (r > light_threshold) & (g > light_threshold) & (b > light_threshold)

# Set alpha to 0 for light pixels (make transparent)
data[is_light, 3] = 0

# Create new image from modified data
result = Image.fromarray(data, 'RGBA')

# Save the result
result.save(output_image_path, 'PNG')
print(f"\n✓ Transparent logo saved to: {output_image_path}")
print(f"  Background pixels removed: {is_light.sum()}")
print(f"  Image ready for use in application!")
