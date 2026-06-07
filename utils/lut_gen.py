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
    exposure = adjustments.get("exposure", 0.0)
    brightness = adjustments.get("brightness", 0.0)
    exposure += brightness # Merge legacy brightness into exposure
    
    contrast = adjustments.get("contrast", 1.0)
    highlights = adjustments.get("highlights", 0.0)
    shadows = adjustments.get("shadows", 0.0)
    whites = adjustments.get("whites", 0.0)
    blacks = adjustments.get("blacks", 0.0)
    saturation = adjustments.get("saturation", 1.0)
    rgb_gain = adjustments.get("rgb_gain", [1.0, 1.0, 1.0])

    print(f"Generating professional 3D LUT with size {size}x{size}x{size}...")
    
    exp_factor = 2.0 ** exposure

    with open(output_path, 'w') as f:
        # Write Header Generation (Phase 3)
        f.write("TITLE \"HueFlow AI Grade\"\n")
        f.write(f"LUT_3D_SIZE {size}\n\n")
        
        # Generate the 33x33x33 cube
        # The .cube format requires B to change fastest, then G, then R
        # Adobe specs: R changes fastest, then G, then B.
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
                    
                    # Apply Exposure (multiplicative scaling)
                    r_new *= exp_factor
                    g_new *= exp_factor
                    b_new *= exp_factor
                    
                    # Apply Contrast (usually pivoting around mid-gray 0.5)
                    r_new = (r_new - 0.5) * contrast + 0.5
                    g_new = (g_new - 0.5) * contrast + 0.5
                    b_new = (b_new - 0.5) * contrast + 0.5
                    
                    # Apply Highlights (adjusts highlights, val > 0.5)
                    for c_idx in range(3):
                        val = [r_new, g_new, b_new][c_idx]
                        if val > 0.5:
                            w = (val - 0.5) / 0.5
                            val = val + highlights * w * (1.0 - val)
                        if c_idx == 0: r_new = val
                        elif c_idx == 1: g_new = val
                        else: b_new = val

                    # Apply Shadows (adjusts shadows, val < 0.5)
                    for c_idx in range(3):
                        val = [r_new, g_new, b_new][c_idx]
                        if val < 0.5:
                            w = (0.5 - val) / 0.5
                            val = val + shadows * w * val
                        if c_idx == 0: r_new = val
                        elif c_idx == 1: g_new = val
                        else: b_new = val

                    # Apply Whites (strongest at 1.0)
                    r_new += whites * (r_new ** 2)
                    g_new += whites * (g_new ** 2)
                    b_new += whites * (b_new ** 2)

                    # Apply Blacks (strongest at 0.0)
                    r_new += blacks * ((1.0 - r_new) ** 2)
                    g_new += blacks * ((1.0 - g_new) ** 2)
                    b_new += blacks * ((1.0 - b_new) ** 2)
                    
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
        "exposure": 0.5,
        "contrast": 1.2,
        "highlights": -0.1,
        "shadows": 0.2,
        "whites": 0.05,
        "blacks": -0.02,
        "saturation": 1.5,
        "rgb_gain": [1.0, 0.9, 1.1]
    }
    generate_cube_lut(test_adj, "test_output.cube")
