"""
High-Quality Icon Generator for Derivative Mill
Creates a professional icon with gear/cog design
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import math

def create_derivative_mill_icon(size=512):
    """Create a high-quality icon with gear design"""
    # Create image with transparency
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    center_x = size // 2
    center_y = size // 2
    
    # Gradient background circle (blue theme)
    for i in range(size // 2, 0, -1):
        # Create gradient from light to dark blue
        progress = i / (size // 2)
        r = int(0 + (0 * progress))
        g = int(120 + (78 * progress))
        b = int(215 + (0 * progress))
        draw.ellipse(
            [center_x - i, center_y - i, center_x + i, center_y + i],
            fill=(r, g, b, 255)
        )
    
    # Draw outer gear (main gear)
    outer_radius = size * 0.42
    inner_radius = size * 0.28
    teeth_count = 12
    tooth_height = size * 0.08
    
    # Create gear shape
    gear_points = []
    for i in range(teeth_count * 2):
        angle = (i * math.pi) / teeth_count
        if i % 2 == 0:
            # Outer tooth
            radius = outer_radius + tooth_height
        else:
            # Inner tooth
            radius = outer_radius
        
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        gear_points.append((x, y))
    
    # Draw main gear body (white/silver)
    draw.polygon(gear_points, fill=(240, 240, 245, 255), outline=(180, 180, 190, 255))
    
    # Draw inner circle (darker)
    draw.ellipse(
        [center_x - inner_radius, center_y - inner_radius,
         center_x + inner_radius, center_y + inner_radius],
        fill=(60, 90, 150, 255)
    )
    
    # Draw center hole
    center_hole = size * 0.12
    draw.ellipse(
        [center_x - center_hole, center_y - center_hole,
         center_x + center_hole, center_y + center_hole],
        fill=(30, 45, 80, 255)
    )
    
    # Add small accent gear (top right)
    accent_x = center_x + size * 0.25
    accent_y = center_y - size * 0.25
    accent_outer = size * 0.15
    accent_inner = size * 0.08
    accent_teeth = 8
    accent_tooth = size * 0.03
    
    accent_points = []
    for i in range(accent_teeth * 2):
        angle = (i * math.pi) / accent_teeth
        if i % 2 == 0:
            radius = accent_outer + accent_tooth
        else:
            radius = accent_outer
        
        x = accent_x + radius * math.cos(angle)
        y = accent_y + radius * math.sin(angle)
        accent_points.append((x, y))
    
    # Draw accent gear (lighter color)
    draw.polygon(accent_points, fill=(255, 255, 255, 220), outline=(200, 200, 210, 255))
    draw.ellipse(
        [accent_x - accent_inner, accent_y - accent_inner,
         accent_x + accent_inner, accent_y + accent_inner],
        fill=(0, 188, 242, 255)
    )
    
    # Add highlight effect on main gear
    highlight_offset = size * 0.15
    highlight_size = size * 0.25
    draw.ellipse(
        [center_x - highlight_size - highlight_offset,
         center_y - highlight_size - highlight_offset,
         center_x - highlight_offset,
         center_y - highlight_offset],
        fill=(255, 255, 255, 60)
    )
    
    return img

def save_icon(img, output_path):
    """Save image as multi-resolution ICO file"""
    # Create multiple resolutions
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icon_images = []
    
    for size in sizes:
        resized = img.resize(size, Image.Resampling.LANCZOS)
        icon_images.append(resized)
        print(f"Created {size[0]}x{size[1]} version")
    
    # Save as ICO with all sizes
    icon_images[0].save(
        output_path,
        format='ICO',
        sizes=[(img.width, img.height) for img in icon_images],
        append_images=icon_images[1:]
    )
    
    print(f"\n✓ Successfully created: {output_path}")

if __name__ == "__main__":
    print("=" * 60)
    print("Creating High-Quality Icon for Derivative Mill")
    print("=" * 60)
    print()
    
    # Create 512x512 master icon
    print("Generating icon artwork...")
    icon_img = create_derivative_mill_icon(512)
    
    # Save to Resources folder
    resources_dir = Path(__file__).parent / "Resources"
    resources_dir.mkdir(exist_ok=True)
    output_path = resources_dir / "icon.ico"
    
    print("\nCreating multi-resolution ICO file...")
    save_icon(icon_img, output_path)
    
    # Also save as PNG for preview
    png_path = resources_dir / "icon_preview.png"
    icon_img.save(png_path, 'PNG')
    print(f"✓ Preview saved: {png_path}")
    
    print("\n" + "=" * 60)
    print("Icon creation complete!")
    print("=" * 60)
