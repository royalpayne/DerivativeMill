"""
Process banner background image - make transparent and optimize
"""

from PIL import Image
from pathlib import Path

def make_background_transparent(input_path, output_path):
    """Make white/light backgrounds transparent"""
    try:
        # Open image
        img = Image.open(input_path)
        print(f"Original image: {img.size} - {img.mode}")
        
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Get pixel data
        data = img.getdata()
        
        # Create new image data with transparency
        new_data = []
        for item in data:
            # Make white and light colors transparent
            # Adjust threshold as needed
            if item[0] > 240 and item[1] > 240 and item[2] > 240:
                # White/very light - make fully transparent
                new_data.append((255, 255, 255, 0))
            elif item[0] > 200 and item[1] > 200 and item[2] > 200:
                # Light colors - semi-transparent
                new_data.append((item[0], item[1], item[2], 50))
            else:
                # Keep original color
                new_data.append(item)
        
        # Update image data
        img.putdata(new_data)
        
        # Save
        img.save(output_path, 'PNG')
        print(f"✓ Saved transparent image: {output_path}")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Processing Banner Background Image")
    print("=" * 60)
    print()
    
    input_path = Path("C:/Users/hpayne/Documents/DevHouston/metalsplitter/Resources/download.png")
    output_path = Path(__file__).parent / "Resources" / "banner_bg.png"
    
    if not input_path.exists():
        print(f"✗ Input file not found: {input_path}")
    else:
        if make_background_transparent(input_path, output_path):
            print("\n✓ Banner background ready!")
        else:
            print("\n✗ Failed to process image")
