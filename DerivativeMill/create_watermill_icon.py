"""
Water Mill Wheel Icon Generator for Derivative Mill
Creates a professional water mill wheel icon with transparent background
"""

from PIL import Image, ImageDraw
from pathlib import Path
import math

def create_water_mill_wheel_icon(size=512):
    """Create a high-quality water mill wheel icon"""
    # Create image with transparency
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    center_x = size // 2
    center_y = size // 2
    
    # Outer wheel rim
    outer_radius = size * 0.45
    inner_radius = size * 0.38
    rim_color = (139, 90, 43, 255)  # Dark wood brown
    
    # Draw outer rim circle
    draw.ellipse(
        [center_x - outer_radius, center_y - outer_radius,
         center_x + outer_radius, center_y + outer_radius],
        fill=rim_color
    )
    
    # Draw inner cutout
    draw.ellipse(
        [center_x - inner_radius, center_y - inner_radius,
         center_x + inner_radius, center_y + inner_radius],
        fill=(0, 0, 0, 0)  # Transparent
    )
    
    # Draw paddles/buckets (8 paddles around the wheel)
    paddle_count = 8
    paddle_length = size * 0.18
    paddle_width = size * 0.08
    paddle_offset = size * 0.35
    paddle_color = (101, 67, 33, 255)  # Darker wood
    
    for i in range(paddle_count):
        angle = (i * 2 * math.pi) / paddle_count
        
        # Calculate paddle position
        paddle_x = center_x + paddle_offset * math.cos(angle)
        paddle_y = center_y + paddle_offset * math.sin(angle)
        
        # Calculate paddle rectangle corners (perpendicular to radius)
        perp_angle = angle + math.pi / 2
        hw = paddle_width / 2
        hl = paddle_length / 2
        
        # Four corners of paddle
        corners = [
            (paddle_x + hw * math.cos(perp_angle) - hl * math.cos(angle),
             paddle_y + hw * math.sin(perp_angle) - hl * math.sin(angle)),
            (paddle_x - hw * math.cos(perp_angle) - hl * math.cos(angle),
             paddle_y - hw * math.sin(perp_angle) - hl * math.sin(angle)),
            (paddle_x - hw * math.cos(perp_angle) + hl * math.cos(angle),
             paddle_y - hw * math.sin(perp_angle) + hl * math.sin(angle)),
            (paddle_x + hw * math.cos(perp_angle) + hl * math.cos(angle),
             paddle_y + hw * math.sin(perp_angle) + hl * math.sin(angle))
        ]
        
        draw.polygon(corners, fill=paddle_color)
        
        # Add bucket detail (darker edge)
        bucket_edge = [
            corners[2],
            corners[3],
            (paddle_x + (hw + size * 0.02) * math.cos(perp_angle) + (hl + size * 0.02) * math.cos(angle),
             paddle_y + (hw + size * 0.02) * math.sin(perp_angle) + (hl + size * 0.02) * math.sin(angle)),
            (paddle_x - (hw + size * 0.02) * math.cos(perp_angle) + (hl + size * 0.02) * math.cos(angle),
             paddle_y - (hw + size * 0.02) * math.sin(perp_angle) + (hl + size * 0.02) * math.sin(angle))
        ]
        draw.polygon(bucket_edge, fill=(70, 47, 25, 255))
    
    # Draw spokes (8 spokes connecting to center)
    spoke_width = size * 0.04
    spoke_color = (120, 80, 40, 255)  # Medium wood
    center_hub_radius = size * 0.12
    
    for i in range(paddle_count):
        angle = (i * 2 * math.pi) / paddle_count
        
        # Start point at center hub
        start_x = center_x + center_hub_radius * math.cos(angle)
        start_y = center_y + center_hub_radius * math.sin(angle)
        
        # End point at inner rim
        end_x = center_x + inner_radius * math.cos(angle)
        end_y = center_y + inner_radius * math.sin(angle)
        
        # Draw spoke as thick line
        draw.line([(start_x, start_y), (end_x, end_y)], 
                 fill=spoke_color, width=int(spoke_width))
    
    # Draw center hub
    hub_color = (101, 67, 33, 255)  # Dark wood
    draw.ellipse(
        [center_x - center_hub_radius, center_y - center_hub_radius,
         center_x + center_hub_radius, center_y + center_hub_radius],
        fill=hub_color
    )
    
    # Draw center axle hole
    axle_radius = size * 0.06
    draw.ellipse(
        [center_x - axle_radius, center_y - axle_radius,
         center_x + axle_radius, center_y + axle_radius],
        fill=(50, 30, 15, 255)
    )
    
    # Add some wood grain detail with lighter highlights
    highlight_color = (160, 110, 60, 100)
    for i in range(0, paddle_count, 2):
        angle = (i * 2 * math.pi) / paddle_count
        start_x = center_x + (center_hub_radius + size * 0.02) * math.cos(angle)
        start_y = center_y + (center_hub_radius + size * 0.02) * math.sin(angle)
        end_x = center_x + (inner_radius - size * 0.02) * math.cos(angle)
        end_y = center_y + (inner_radius - size * 0.02) * math.sin(angle)
        draw.line([(start_x, start_y), (end_x, end_y)], 
                 fill=highlight_color, width=int(spoke_width * 0.6))
    
    # Add water droplets effect around bottom paddles
    water_color = (100, 180, 220, 180)
    for i in range(4):
        angle = math.pi / 4 + (i * math.pi / 8)
        droplet_x = center_x + (outer_radius + size * 0.05) * math.cos(angle)
        droplet_y = center_y + (outer_radius + size * 0.05) * math.sin(angle)
        droplet_size = size * 0.015
        draw.ellipse(
            [droplet_x - droplet_size, droplet_y - droplet_size,
             droplet_x + droplet_size, droplet_y + droplet_size],
            fill=water_color
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
    print("Creating Water Mill Wheel Icon for Derivative Mill")
    print("=" * 60)
    print()
    
    # Create 512x512 master icon
    print("Generating water mill wheel artwork...")
    icon_img = create_water_mill_wheel_icon(512)
    
    # Save to Resources folder
    resources_dir = Path(__file__).parent / "Resources"
    resources_dir.mkdir(exist_ok=True)
    
    # Save as PNG first for preview
    png_path = resources_dir / "watermill_preview.png"
    icon_img.save(png_path, 'PNG')
    print(f"✓ Preview saved: {png_path}")
    
    # Save as ICO
    output_path = resources_dir / "watermill.png"
    icon_img.save(output_path, 'PNG')
    print(f"✓ PNG saved: {output_path}")
    
    print("\n" + "=" * 60)
    print("Water mill wheel icon creation complete!")
    print("Icon features:")
    print("  • Transparent background")
    print("  • Wooden texture with realistic wood colors")
    print("  • 8 paddles/buckets around the wheel")
    print("  • Center hub with spokes")
    print("  • Water droplet effects")
    print("=" * 60)
