import os
import colorsys

def generate_cube_lut(adjustments: dict, output_path: str):
    """
    Generate a 33x33x33 3D LUT (.cube) based on AI adjustments.
    
    Formula:
    NewColor = (OriginalColor * Gain) * Contrast + Brightness
    Saturation is applied in HSV space.
    """
    size = 33
    
    # Extract adjustments, provide defaults if missing
    brightness = adjustments.get("brightness", 0.0)
    contrast = adjustments.get("contrast", 1.0)
    saturation = adjustments.get("saturation", 1.0)
    rgb_gain = adjustments.get("rgb_gain", [1.0, 1.0, 1.0])

    print(f"Generating professional 3D LUT with size {size}x{size}x{size}...")
    
    with open(output_path, 'w') as f:
        # Write Header Generation (Phase 3)
        f.write("TITLE \"HueFlow AI Grade\"\n")
        f.write(f"LUT_3D_SIZE {size}\n\n")
        
        # Generate the 33x33x33 cube
        # The .cube format requires B to change fastest, then G, then R
        # However, the standard is usually R varies fastest in some specs, B in others.
        # Adobe specs: R changes fastest, then G, then B.
        # Wait, Adobe Cube spec says: 
        # The first dimension (R) changes fastest, then G, then B.
        for b in range(size):
            for g in range(size):
                for r in range(size):
                    # Normalized original colors (0.0 to 1.0)
                    r_norm = r / (size - 1)
                    g_norm = g / (size - 1)
                    b_norm = b / (size - 1)
                    
                    # Apply RGB Gain
                    r_new = r_norm * rgb_gain[0]
                    g_new = g_norm * rgb_gain[1]
                    b_new = b_norm * rgb_gain[2]
                    
                    # Apply Contrast (usually pivoting around mid-gray 0.5)
                    r_new = (r_new - 0.5) * contrast + 0.5
                    g_new = (g_new - 0.5) * contrast + 0.5
                    b_new = (b_new - 0.5) * contrast + 0.5
                    
                    # Apply Brightness
                    r_new += brightness
                    g_new += brightness
                    b_new += brightness
                    
                    # Clamp RGB to [0.0, 1.0] before HSV conversion
                    r_new = max(0.0, min(1.0, r_new))
                    g_new = max(0.0, min(1.0, g_new))
                    b_new = max(0.0, min(1.0, b_new))
                    
                    # Apply Saturation
                    if saturation != 1.0:
                        h, s_hsv, v = colorsys.rgb_to_hsv(r_new, g_new, b_new)
                        s_hsv = s_hsv * saturation
                        s_hsv = max(0.0, min(1.0, s_hsv))
                        r_final, g_final, b_final = colorsys.hsv_to_rgb(h, s_hsv, v)
                    else:
                        r_final, g_final, b_final = r_new, g_new, b_new
                    
                    # Final Clamp Validation
                    r_final = max(0.0, min(1.0, r_final))
                    g_final = max(0.0, min(1.0, g_final))
                    b_final = max(0.0, min(1.0, b_final))
                    
                    # Write to file
                    f.write(f"{r_final:.6f} {g_final:.6f} {b_final:.6f}\n")
                    
    print(f"Validation successful. Saved .cube to {output_path}")

if __name__ == "__main__":
    # Test LUT generation
    test_adj = {
        "brightness": 0.0,
        "contrast": 1.2,
        "saturation": 1.5,
        "rgb_gain": [1.0, 0.9, 1.1]
    }
    generate_cube_lut(test_adj, "test_output.cube")
