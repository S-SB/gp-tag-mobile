"""
MIT License

Copyright (c) 2025 S. E. Sundén Byléhn

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import reedsolo
import os

def create_fiducial_marker(latitude, longitude, altitude, quaternion, scale, accuracy, tag_id, version_id, U=10):
    """
    Creates a GP-Tag fiducial marker encoding global positioning data.
    
    Args:
        latitude (float): Latitude in degrees (-90 to +90)
        longitude (float): Longitude in degrees (-180 to +180)
        altitude (float): Altitude in meters (-10000 to +10000)
        quaternion (list): Orientation as quaternion [qx, qy, qz, qw]
        scale (float): Scale factor in cells/mm (0.0036 to 3.6)
        accuracy (int): Accuracy level (0-3)
        tag_id (int): Unique tag identifier (0-4095)
        version_id (int): Version identifier (0-15)
        U (int): Base unit size in pixels (default: 2)
    
    Returns:
        PIL.Image: The generated GP-Tag image
    """
    # Basic dimensions
    grid_size = 21  # 21x21 grid
    grid_diagonal = 15 * U
    outer_annulus_outer_radius = math.floor(grid_diagonal + (3 * U))
    
    # Define image dimensions and origin
    image_size_x = 2 * outer_annulus_outer_radius
    image_size_y = 2 * outer_annulus_outer_radius
    origin_x = outer_annulus_outer_radius
    origin_y = outer_annulus_outer_radius
    
    # Create image with white background
    img = Image.new('RGB', (image_size_x, image_size_y), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw outer black ring
    draw.ellipse([
        origin_x - outer_annulus_outer_radius,
        origin_y - outer_annulus_outer_radius,
        origin_x + outer_annulus_outer_radius,
        origin_y + outer_annulus_outer_radius
    ], fill='black')
    
    # Calculate annuli
    inner_annulus_inner_radius = math.floor(grid_diagonal)
    inner_annulus_outer_radius = inner_annulus_inner_radius + U
    middle_annulus_outer_radius = inner_annulus_outer_radius + U

    # Middle and inner annuli (white)
    draw.ellipse([
        origin_x - middle_annulus_outer_radius,
        origin_y - middle_annulus_outer_radius,
        origin_x + middle_annulus_outer_radius,
        origin_y + middle_annulus_outer_radius
    ], fill='white')
    
    draw.ellipse([
        origin_x - inner_annulus_outer_radius,
        origin_y - inner_annulus_outer_radius,
        origin_x + inner_annulus_outer_radius,
        origin_y + inner_annulus_outer_radius
    ], fill='white')

    # Define spike tips and middle points of grid borders
    spike_coordinates = [
        (outer_annulus_outer_radius, -outer_annulus_outer_radius),   # top-right
        (-outer_annulus_outer_radius, -outer_annulus_outer_radius),  # top-left
        (-outer_annulus_outer_radius, outer_annulus_outer_radius),   # bottom-left
        (outer_annulus_outer_radius, outer_annulus_outer_radius)     # bottom-right
    ]
    
    grid_half_size = (grid_size * U) / 2
    border_middle_points = [
        (origin_x + grid_half_size, origin_y),                # right_middle
        (origin_x, origin_y - grid_half_size),                # top_middle
        (origin_x - grid_half_size, origin_y),                # left_middle
        (origin_x, origin_y + grid_half_size)                 # bottom_middle
    ]
    
    # Draw spikes
    for i, spike_tip in enumerate(spike_coordinates):
        x_tip, y_tip = origin_x + spike_tip[0], origin_y + spike_tip[1]
        point1 = border_middle_points[i]
        point2 = border_middle_points[(i+1) % 4]
        polygon_points = [
            (x_tip, y_tip),
            point1,
            point2
        ]
        draw.polygon(polygon_points, fill='black')

    # Save the region inside the inner circle of the inner annulus
    inner_circle_size = int(2 * inner_annulus_inner_radius)
    temp_inner_circle = Image.new('RGBA', (inner_circle_size, inner_circle_size), (0, 0, 0, 0))
    temp_draw = ImageDraw.Draw(temp_inner_circle)
    temp_draw.ellipse([0, 0, inner_circle_size, inner_circle_size], fill=(255, 255, 255, 255))
    
    cropped_inner = img.crop((
        int(origin_x - inner_annulus_inner_radius),
        int(origin_y - inner_annulus_inner_radius),
        int(origin_x + inner_annulus_inner_radius),
        int(origin_y + inner_annulus_inner_radius)
    )).convert('RGBA')
    
    temp_inner_circle = Image.composite(cropped_inner, Image.new('RGBA', cropped_inner.size, (0, 0, 0, 0)), temp_inner_circle)

    # Re-draw outer black ring to clean up overlap
    draw.ellipse([
        origin_x - outer_annulus_outer_radius,
        origin_y - outer_annulus_outer_radius,
        origin_x + outer_annulus_outer_radius,
        origin_y + outer_annulus_outer_radius
    ], outline='black')

    # Define quadrants for annuli patterns
    quadrants = [
        (0, 90, 1, 1),     # Q4: Bottom-right 1, 1
        (90, 180, 1, 0),   # Q3: Bottom-left 1, 0
        (180, 270, 0, 1),  # Q2: Top-left 0, 1
        (270, 360, 0, 0)   # Q1: Top-right 0, 0
    ]

    # Draw annuli quadrants
    for start_angle, end_angle, middle_bit, inner_bit in quadrants:
        # Middle annulus quadrants
        draw.pieslice([
            origin_x - middle_annulus_outer_radius,
            origin_y - middle_annulus_outer_radius,
            origin_x + middle_annulus_outer_radius,
            origin_y + middle_annulus_outer_radius
        ], start_angle, end_angle, fill='black' if middle_bit == 1 else 'white')
        
        # Inner annulus quadrants
        draw.pieslice([
            origin_x - inner_annulus_outer_radius,
            origin_y - inner_annulus_outer_radius,
            origin_x + inner_annulus_outer_radius,
            origin_y + inner_annulus_outer_radius
        ], start_angle, end_angle, fill='black' if inner_bit == 1 else 'white')

    # Paste inner circle back
    img = img.convert('RGBA')
    img.alpha_composite(temp_inner_circle, (
        int(origin_x - inner_annulus_inner_radius),
        int(origin_y - inner_annulus_inner_radius)
    ))
    img = img.convert('RGB')

    # Initialize grid for GP-Tag data
    grid = np.ones((grid_size, grid_size), dtype=np.uint8)
    
    def place_finder_pattern(x, y):
        pattern = np.array([
            [1,1,1,1,1],
            [1,0,0,0,1],
            [1,0,1,0,1],
            [1,0,0,0,1],
            [1,1,1,1,1]
        ], dtype=np.uint8)
        grid[y:y+5, x:x+5] = pattern

    # Place finder patterns at corners
    place_finder_pattern(0, 0)
    place_finder_pattern(grid_size - 5, 0)
    place_finder_pattern(0, grid_size - 5)
    place_finder_pattern(grid_size - 5, grid_size - 5)

    # Add timing patterns
    for i in range(5, grid_size - 5):
        grid[5, i] = 1 if i % 2 == 0 else 0  # horizontal
        grid[i, 5] = 1 if i % 2 == 0 else 0  # vertical

    try:
        # Main data encoding
        lat_value = int((latitude + 90) * ((2**35 - 1) / 180))
        lat_bits = format(lat_value, '035b')
        
        lon_value = int((longitude + 180) * ((2**36 - 1) / 360))
        lon_bits = format(lon_value, '036b')
        
        alt_value = int((altitude + 10000) * ((2**25 - 1) / 20000))
        alt_bits = format(alt_value, '025b')
        
        quat_bits = ''.join(format(int((q + 1) * ((2**16 - 1) / 2)), '016b') for q in quaternion)
        
        accuracy_bits = format(accuracy, '02b')
        scale_value = int(scale * ((2**16 - 1) / 3.6))
        scale_bits = format(scale_value, '016b')
        
        # Combine main data and apply error correction
        main_data_bits = lat_bits + lon_bits + alt_bits + quat_bits + accuracy_bits + scale_bits
        main_data_bytes = int(np.ceil(len(main_data_bits) / 8))
        main_ecc_bytes = int(np.ceil(main_data_bytes * 0.5))
        main_data_int = int(main_data_bits, 2)
        main_data_bytes_array = main_data_int.to_bytes(main_data_bytes, 'big')
        rs_main = reedsolo.RSCodec(main_ecc_bytes)
        main_encoded_data = rs_main.encode(main_data_bytes_array)
        encoded_bits = ''.join(format(byte, '08b') for byte in main_encoded_data)

        # Reserved area data (IDs) - 16 bits to be encoded
        tag_id_bits = format(tag_id, '012b')         # 12 bits for Tag ID
        version_id_bits = format(version_id, '04b')   # 4 bits for Version ID
        id_encoded_bits = tag_id_bits + version_id_bits
        
        # Error correction applied to expand this to 24 bits total
        id_encoded_bytes = int(id_encoded_bits, 2).to_bytes(2, 'big')  # 16 bits as 2 bytes
        rs_reserved = reedsolo.RSCodec(1)  # Minimal RS overhead to make 3 bytes (24 bits)
        id_encoded_data = rs_reserved.encode(id_encoded_bytes)
        id_encoded_bits = ''.join(format(byte, '08b') for byte in id_encoded_data)
    except ValueError as e:
        return None

    reserved_modules = set()
    for y in range(grid_size):
        for x in range(grid_size):
            if (x < 5 and y < 5) or (x < 5 and y > grid_size-6) or (x > grid_size-6 and y < 5) or (x > grid_size-6 and y > grid_size-6) or x == 5 or y == 5:
                reserved_modules.add((x, y))

    bit_index = 0
    for x in range(grid_size - 1, -1, -1):
        if x == 6:
            continue
        for y in range(grid_size - 1, -1, -1):
            if (x, y) not in reserved_modules:
                if bit_index < len(encoded_bits):
                    grid[y, x] = 1 if int(encoded_bits[bit_index]) else 0
                    bit_index += 1
                else:
                    break
        if bit_index >= len(encoded_bits):
            break

    # Draw the inner grid
    grid_start_x = math.floor(origin_x - (grid_size * U) // 2)
    grid_start_y = math.floor(origin_y - (grid_size * U) // 2)
    draw = ImageDraw.Draw(img)

    # Count available and used data cells
    available_cells = 0
    used_cells = 0
    
    # Regular encoding
    for y in range(grid_size):
        for x in range(grid_size):
            if (x, y) not in reserved_modules:
                if used_cells < len(encoded_bits):
                    color = 'black' if grid[y, x] == 1 else 'white'  # Actual data bits
            else:
                color = 'black' if grid[y, x] == 1 else 'white'  # Finder/timing patterns
                
            draw.rectangle([
                grid_start_x + x * U,
                grid_start_y + y * U,
                grid_start_x + (x + 1) * U - 1,
                grid_start_y + (y + 1) * U - 1
            ], fill=color)

    # Draw the full 36x36 grid
    grid_size_for_start = 36
    full_grid_start_x = math.floor(origin_x - (grid_size_for_start * U) // 2 - U/2)
    full_grid_start_y = math.floor(origin_y - (grid_size_for_start * U) // 2 - U/2)

    fill_reserved_area(draw, full_grid_start_x, full_grid_start_y, U, id_encoded_bits)

    return img


def fill_reserved_area(draw, full_grid_start_x, full_grid_start_y, U, id_encoded_bits):
    """
    Fill the reserved areas of the GP-Tag with encoded ID data.
    
    Args:
        draw: PIL ImageDraw object
        full_grid_start_x (int): Starting x coordinate for the full grid
        full_grid_start_y (int): Starting y coordinate for the full grid
        U (int): Base unit size in pixels
        id_encoded_bits (str): Binary string of encoded ID data
    """
    # Predefined list of cell pairs in the specified order
    cell_pairs = [
        ((15,32), (21,4)), ((16,32), (20,4)), ((17,32), (19,4)),
        ((18,32), (18,4)), ((19,32), (17,4)), ((20,32), (16,4)),
        ((21,32), (15,4)), ((14,31), (22,5)), ((15,31), (21,5)),
        ((16,31), (20,5)), ((17,31), (19,5)), ((18,31), (18,5)),
        ((19,31), (17,5)), ((20,31), (16,5)), ((21,31), (15,5)),
        ((22,31), (14,5)), ((17,30), (19,6)), ((18,30), (18,6)),
        ((19,30), (17,6)), ((4,15), (32,21)), ((4,16), (32,20)),
        ((4,17), (32,19)), ((4,18), (32,18)), ((4,19), (32,17)),
        ((4,20), (32,16)), ((4,21), (32,15)), ((5,14), (31,22)),
        ((5,15), (31,21)), ((5,16), (31,20)), ((5,17), (31,19)),
        ((5,18), (31,18)), ((5,19), (31,17)), ((5,20), (31,16)),
        ((5,21), (31,15)), ((5,22), (31,14)), ((6,17), (30,19)),
        ((6,18), (30,18)), ((6,19), (30,17))
    ]

    # Iterate over each pair of cells and fill them based on id_encoded_bits
    for i, (primary_cell, mirror_cell) in enumerate(cell_pairs):
        if i < len(id_encoded_bits):  # Ensure there's enough data
            bit = int(id_encoded_bits[i])  # Get the current bit
            color = 'black' if bit else 'white'  # Set color based on bit value

            # Fill both the primary and mirror cells
            for cell in (primary_cell, mirror_cell):
                x, y = cell
                draw.rectangle([
                    full_grid_start_x + x * U,
                    full_grid_start_y + y * U,
                    full_grid_start_x + (x + 1) * U - 1,
                    full_grid_start_y + (y + 1) * U - 1
                ], fill=color)


def calculate_scale_from_dpi_and_U(dpi, U):
    """
    Calculate scale (cells/mm) from printer DPI and U value
    
    Args:
        dpi (int): Printer DPI (e.g., 600 DPI)
        U (int): Base unit in pixels (e.g., 256)
    
    Returns:
        float: Scale value in cells/mm
    """
    # Convert DPI to dots/mm (1 inch = 25.4 mm)
    dots_per_mm = dpi / 25.4
    
    # Calculate how many mm one cell (U pixels) represents
    mm_per_cell = U / dots_per_mm
    
    # Calculate cells per mm (inverse)
    scale = 1 / mm_per_cell
    
    return scale


def calculate_U_and_scale_from_dpi_and_size(dpi, size_mm):
    """
    Calculate both U value and scale from printer DPI and desired tag size
    
    Args:
        dpi (int): Printer DPI (e.g., 600 DPI)
        size_mm (float): Desired tag size in mm (length/width since it's square)
    
    Returns:
        tuple: (U: Base unit in pixels, scale: cells/mm value)
    """
    # Convert DPI to dots/mm
    dots_per_mm = dpi / 25.4
    
    # Total size is 36 cells (full grid)
    cells = 36
    
    # Calculate U (pixels per cell)
    # size_mm * dots_per_mm = total pixels
    # total pixels / cells = pixels per cell (U)
    U = round((size_mm * dots_per_mm) / cells)
    
    # Calculate scale (cells/mm)
    cells_per_mm = cells / size_mm
    
    return U, cells_per_mm


if __name__ == "__main__":
    """
    Example usage of GP-Tag generation with different scale calculation methods.
    
    Position data defines global location and orientation:
    - Latitude/Longitude: Global coordinates (-90/+90, -180/+180 degrees)
    - Altitude: Height above sea level (-10000 to +10000 meters)
    - Quaternion: Orientation as [qx, qy, qz, qw]
    - Scale: Physical size conversion (cells/mm)
    - Accuracy: Position confidence (0-3)
    - Tag ID: Unique identifier (0-4095)
    - Version: Protocol version (0-15)
    """
    # Example tag data - University location
    latitude = 63.8203894
    longitude = 20.3058847
    altitude = 45.16
    quaternion = [0.707, 0, 0.707, 0]  # 90-degree rotation around Y
    accuracy = 2  # High accuracy
    tag_id = 123
    version_id = 3

    # Scale calculation methods
    # Option 1: From printer DPI and resolution
    if False:
        dpi = 600  # Printer's resolution
        U = 40    # Pixels per cell (larger = higher quality)
        scale = calculate_scale_from_dpi_and_U(dpi, U)
        print(f"Method 1 - Scale from DPI:")
        print(f"  Scale: {scale:.4f} cells/mm")
        print(f"  Resolution: {U*36}x{U*36} pixels")

    # Option 2: From desired physical size and DPI
    if False:
        dpi = 600      # Printer's resolution
        size_mm = 100  # Desired tag size (100mm x 100mm)
        U, scale = calculate_U_and_scale_from_dpi_and_size(dpi, size_mm)
        print(f"Method 2 - Scale from physical size:")
        print(f"  U value: {U} pixels/cell")
        print(f"  Scale: {scale:.4f} cells/mm")
        print(f"  Resolution: {U*36}x{U*36} pixels")

    # Option 3: Direct physical size (recommended)
    if True:
        size_mm = 100  # Physical tag size (100mm x 100mm)
        U = 40        # Resolution (40 pixels/cell = 1440x1440 image)
        scale = 36 / size_mm  # 36 cells (full grid) / physical size
        print(f"Method 3 - Direct physical size:")
        print(f"  Size: {size_mm}x{size_mm}mm")
        print(f"  Scale: {scale:.4f} cells/mm")
        print(f"  Resolution: {U*36}x{U*36} pixels")

    # Generate tag
    tag_image = create_fiducial_marker(
        latitude, longitude, altitude, quaternion, 
        scale, accuracy, tag_id, version_id, U=U
    )

    if tag_image:
        # Option 1: Save in current directory
        tag_image.save("gptag.png")
        print("\nTag saved as 'gptag.png' in current directory")

        # Option 2: Save with custom path
        # tag_image.save("path/to/your/directory/gptag.png")
        
        # Option 3: Save with size in filename
        # tag_image.save(f"gptag_{size_mm}mm_{U*36}px.png")
    else:
        print("Error: Tag generation failed")