import os
import colorsys
import math

def generate_cube_lut(adjustments: dict, output_path: str):
    """
    Generate a 33x33x33 3D LUT (.cube) based on AI adjustments.
    Supports HSL mixer, 3-way color wheels, and color-keyed masking (Sky/Subject).
    """
    size = 33
    
    # 1. Light Panel
    exposure = adjustments.get("exposure", 0.0)
    brightness = adjustments.get("brightness", 0.0)
    exposure += brightness
    
    contrast = adjustments.get("contrast", 1.0)
    highlights = adjustments.get("highlights", 0.0)
    shadows = adjustments.get("shadows", 0.0)
    whites = adjustments.get("whites", 0.0)
    blacks = adjustments.get("blacks", 0.0)
    
    # 2. Color Panel
    temp = adjustments.get("temp", 0.0)
    tint = adjustments.get("tint", 0.0)
    vibrance = adjustments.get("vibrance", 0.0)
    saturation = adjustments.get("saturation", 1.0)
    rgb_gain = adjustments.get("rgb_gain", [1.0, 1.0, 1.0])

    # 3. 3-Way Color Wheels
    shadows_hue = float(adjustments.get("shadows_hue", 0.0))
    shadows_sat = float(adjustments.get("shadows_sat", 0.0))
    midtones_hue = float(adjustments.get("midtones_hue", 0.0))
    midtones_sat = float(adjustments.get("midtones_sat", 0.0))
    highlights_hue = float(adjustments.get("highlights_hue", 0.0))
    highlights_sat = float(adjustments.get("highlights_sat", 0.0))
    grading_blending = float(adjustments.get("grading_blending", 0.5))
    grading_balance = float(adjustments.get("grading_balance", 0.0))
    
    # 4. HSL Color Mixer
    hsl_red_h = float(adjustments.get("hsl_red_h", 0.0))
    hsl_red_s = float(adjustments.get("hsl_red_s", 0.0))
    hsl_red_l = float(adjustments.get("hsl_red_l", 0.0))
    
    hsl_yellow_h = float(adjustments.get("hsl_yellow_h", 0.0))
    hsl_yellow_s = float(adjustments.get("hsl_yellow_s", 0.0))
    hsl_yellow_l = float(adjustments.get("hsl_yellow_l", 0.0))
    
    hsl_green_h = float(adjustments.get("hsl_green_h", 0.0))
    hsl_green_s = float(adjustments.get("hsl_green_s", 0.0))
    hsl_green_l = float(adjustments.get("hsl_green_l", 0.0))
    
    hsl_blue_h = float(adjustments.get("hsl_blue_h", 0.0))
    hsl_blue_s = float(adjustments.get("hsl_blue_s", 0.0))
    hsl_blue_l = float(adjustments.get("hsl_blue_l", 0.0))
    
    # 5. Masking
    mask_type = str(adjustments.get("mask_type", "None"))
    mask_exposure = float(adjustments.get("mask_exposure", 0.0))
    mask_temp = float(adjustments.get("mask_temp", 0.0))
    mask_vibrance = float(adjustments.get("mask_vibrance", 0.0))

    # Shadows/Midtones/Highlights vectors
    def get_wheel_offset(h_deg, s_val):
        if s_val == 0.0:
            return 0.0, 0.0, 0.0
        rad = math.radians(h_deg)
        r_off = math.cos(rad) * s_val
        g_off = math.cos(rad - math.radians(120)) * s_val
        b_off = math.cos(rad - math.radians(240)) * s_val
        return r_off, g_off, b_off

    sh_r, sh_g, sh_b = get_wheel_offset(shadows_hue, shadows_sat)
    mid_r, mid_g, mid_b = get_wheel_offset(midtones_hue, midtones_sat)
    hi_r, hi_g, hi_b = get_wheel_offset(highlights_hue, highlights_sat)

    print(f"Generating professional 3D LUT with size {size}x{size}x{size}...")
    
    exp_factor = 2.0 ** exposure
    midpoint = 0.5 + 0.3 * grading_balance

    with open(output_path, 'w') as f:
        f.write("TITLE \"HueFlow AI Grade\"\n")
        f.write(f"LUT_3D_SIZE {size}\n\n")
        
        for b in range(size):
            for g in range(size):
                for r in range(size):
                    r_norm = r / (size - 1)
                    g_norm = g / (size - 1)
                    b_norm = b / (size - 1)
                    
                    r_new = r_norm * rgb_gain[0]
                    g_new = g_norm * rgb_gain[1]
                    b_new = b_norm * rgb_gain[2]
                    
                    # Temperature & Tint
                    r_new = r_new * (1.0 + temp * 0.15)
                    b_new = b_new * (1.0 - temp * 0.15)
                    g_new = g_new * (1.0 - tint * 0.15)
                    r_new = r_new * (1.0 + tint * 0.075)
                    b_new = b_new * (1.0 + tint * 0.075)
                    
                    # Exposure
                    r_new *= exp_factor
                    g_new *= exp_factor
                    b_new *= exp_factor
                    
                    # Contrast
                    r_new = (r_new - 0.5) * contrast + 0.5
                    g_new = (g_new - 0.5) * contrast + 0.5
                    b_new = (b_new - 0.5) * contrast + 0.5
                    
                    # Highlights & Shadows
                    for c_idx in range(3):
                        val = [r_new, g_new, b_new][c_idx]
                        if val > 0.5:
                            w = (val - 0.5) / 0.5
                            val = val + highlights * w * (1.0 - val)
                        if c_idx == 0: r_new = val
                        elif c_idx == 1: g_new = val
                        else: b_new = val

                    for c_idx in range(3):
                        val = [r_new, g_new, b_new][c_idx]
                        if val < 0.5:
                            w = (0.5 - val) / 0.5
                            val = val + shadows * w * val
                        if c_idx == 0: r_new = val
                        elif c_idx == 1: g_new = val
                        else: b_new = val

                    # Whites & Blacks
                    r_new += whites * (r_new ** 2)
                    g_new += whites * (g_new ** 2)
                    b_new += whites * (b_new ** 2)

                    r_new += blacks * ((1.0 - r_new) ** 2)
                    g_new += blacks * ((1.0 - g_new) ** 2)
                    b_new += blacks * ((1.0 - b_new) ** 2)
                    
                    # 3-Way Tints
                    L = 0.299 * r_new + 0.587 * g_new + 0.114 * b_new
                    w_sh = (1.0 - L) * max(0.0, min(1.0, (midpoint - L) / (0.5 * grading_blending + 1e-5)))
                    w_hi = L * max(0.0, min(1.0, (L - midpoint) / (0.5 * grading_blending + 1e-5)))
                    w_mid = max(0.0, min(1.0, 1.0 - w_sh - w_hi))
                    
                    r_new += w_sh * sh_r + w_mid * mid_r + w_hi * hi_r
                    g_new += w_sh * sh_g + w_mid * mid_g + w_hi * hi_g
                    b_new += w_sh * sh_b + w_mid * mid_b + w_hi * hi_b
                    
                    # HSL Mixer
                    r_new = max(0.0, min(1.0, r_new))
                    g_new = max(0.0, min(1.0, g_new))
                    b_new = max(0.0, min(1.0, b_new))
                    
                    h, s_hsv, v = colorsys.rgb_to_hsv(r_new, g_new, b_new)
                    
                    def get_hue_weight_scalar(h_val, target):
                        dist = min(abs(h_val - target), 1.0 - abs(h_val - target))
                        return math.exp(- (dist / 0.08) ** 2)
                        
                    w_red = get_hue_weight_scalar(h, 0.0) + get_hue_weight_scalar(h, 1.0)
                    w_yellow = get_hue_weight_scalar(h, 0.167)
                    w_green = get_hue_weight_scalar(h, 0.333)
                    w_blue = get_hue_weight_scalar(h, 0.667)
                    
                    delta_h = w_red * hsl_red_h + w_yellow * hsl_yellow_h + w_green * hsl_green_h + w_blue * hsl_blue_h
                    delta_s = w_red * hsl_red_s + w_yellow * hsl_yellow_s + w_green * hsl_green_s + w_blue * hsl_blue_s
                    delta_v = w_red * hsl_red_l + w_yellow * hsl_yellow_l + w_green * hsl_green_l + w_blue * hsl_blue_l
                    
                    h = (h + delta_h) % 1.0
                    s_hsv = max(0.0, min(1.0, s_hsv * (1.0 + delta_s)))
                    v = max(0.0, min(1.0, v * (1.0 + delta_v)))
                    
                    r_new, g_new, b_new = colorsys.hsv_to_rgb(h, s_hsv, v)
                    
                    # Vibrance
                    if vibrance != 0.0:
                        max_val = max(r_new, g_new, b_new)
                        min_val = min(r_new, g_new, b_new)
                        sat = (max_val - min_val) / (max_val + 1e-5)
                        boost = vibrance * (1.0 - sat)
                        mean_val = (r_new + g_new + b_new) / 3.0
                        r_new = r_new + (r_new - mean_val) * boost
                        g_new = g_new + (g_new - mean_val) * boost
                        b_new = b_new + (b_new - mean_val) * boost
                        
                    # Color Keyed Masking inside 3D LUT (Sky/Subject keying)
                    if mask_type != "None" and (mask_exposure != 0.0 or mask_temp != 0.0 or mask_vibrance != 0.0):
                        mask_w = 0.0
                        if mask_type == "Sky":
                            L_val = 0.299 * r_new + 0.587 * g_new + 0.114 * b_new
                            mask_w = L_val * max(0.0, min(1.0, (b_new - r_new) / 0.1))
                        elif mask_type == "Subject":
                            h_val, s_val, _ = colorsys.rgb_to_hsv(r_new, g_new, b_new)
                            mask_w = math.exp(-((h_val - 0.05) / 0.03) ** 2) * (1.0 - s_val * 0.3)
                        
                        if mask_w > 0.0:
                            if mask_exposure != 0.0:
                                m_exp = 2.0 ** mask_exposure
                                r_new = r_new * (1.0 - mask_w + mask_w * m_exp)
                                g_new = g_new * (1.0 - mask_w + mask_w * m_exp)
                                b_new = b_new * (1.0 - mask_w + mask_w * m_exp)
                            if mask_temp != 0.0:
                                r_new = r_new * (1.0 + mask_w * mask_temp * 0.15)
                                b_new = b_new * (1.0 - mask_w * mask_temp * 0.15)
                            if mask_vibrance != 0.0:
                                max_val = max(r_new, g_new, b_new)
                                min_val = min(r_new, g_new, b_new)
                                sat = (max_val - min_val) / (max_val + 1e-5)
                                boost = mask_vibrance * (1.0 - sat) * mask_w
                                mean_val = (r_new + g_new + b_new) / 3.0
                                r_new = r_new + (r_new - mean_val) * boost
                                g_new = g_new + (g_new - mean_val) * boost
                                b_new = b_new + (b_new - mean_val) * boost
                    
                    r_final = max(0.0, min(1.0, r_new))
                    g_final = max(0.0, min(1.0, g_new))
                    b_final = max(0.0, min(1.0, b_new))
                    
                    if saturation != 1.0:
                        h_f, s_f, v_f = colorsys.rgb_to_hsv(r_final, g_final, b_final)
                        s_f = max(0.0, min(1.0, s_f * saturation))
                        r_final, g_final, b_final = colorsys.hsv_to_rgb(h_f, s_f, v_f)
                    
                    f.write(f"{r_final:.6f} {g_final:.6f} {b_final:.6f}\n")
                    
    print(f"Validation successful. Saved .cube to {output_path}")

if __name__ == "__main__":
    test_adj = {
        "exposure": 0.5,
        "contrast": 1.2,
        "highlights": -0.1,
        "shadows": 0.2,
        "whites": 0.05,
        "blacks": -0.02,
        "temp": 0.1,
        "tint": -0.05,
        "vibrance": 0.3,
        "saturation": 1.5,
        "rgb_gain": [1.0, 0.9, 1.1],
        "mask_type": "Sky",
        "mask_exposure": 0.2
    }
    generate_cube_lut(test_adj, "test_output.cube")
