import os
from typing import Dict, Any, List
import numpy as np
from PIL import Image, ImageEnhance


def _clamp_float(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def _safe_rgb_gain(v: Any) -> List[float]:
    if isinstance(v, (list, tuple)) and len(v) == 3:
        try:
            return [float(v[0]), float(v[1]), float(v[2])]
        except Exception:
            return [1.0, 1.0, 1.0]
    return [1.0, 1.0, 1.0]


def apply_adjustments_to_image(
    input_path: str,
    adjustments: Dict[str, Any],
    output_path: str,
) -> str:
    """
    Applies HueFlow adjustments to an image and saves a PNG.
    Supports HSL Color Mixer, 3-Way Color Grading, and AI/Local Masking.
    """
    # 1. Light Panel
    exposure = float(adjustments.get("exposure", 0.0))
    brightness = float(adjustments.get("brightness", 0.0))
    exposure += brightness
    
    contrast = float(adjustments.get("contrast", 1.0))
    highlights = float(adjustments.get("highlights", 0.0))
    shadows = float(adjustments.get("shadows", 0.0))
    whites = float(adjustments.get("whites", 0.0))
    blacks = float(adjustments.get("blacks", 0.0))
    
    # 2. Color Panel
    temp = float(adjustments.get("temp", 0.0))
    tint = float(adjustments.get("tint", 0.0))
    vibrance = float(adjustments.get("vibrance", 0.0))
    saturation = float(adjustments.get("saturation", 1.0))
    rgb_gain = _safe_rgb_gain(adjustments.get("rgb_gain", [1.0, 1.0, 1.0]))
    
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
    
    # 5. Local Masking
    mask_type = str(adjustments.get("mask_type", "None"))
    mask_exposure = float(adjustments.get("mask_exposure", 0.0))
    mask_temp = float(adjustments.get("mask_temp", 0.0))
    mask_vibrance = float(adjustments.get("mask_vibrance", 0.0))

    # Clamp bounds for safety
    exposure = _clamp_float(exposure, -3.0, 3.0)
    contrast = _clamp_float(contrast, 0.0, 4.0)
    highlights = _clamp_float(highlights, -1.0, 1.0)
    shadows = _clamp_float(shadows, -1.0, 1.0)
    whites = _clamp_float(whites, -1.0, 1.0)
    blacks = _clamp_float(blacks, -1.0, 1.0)
    temp = _clamp_float(temp, -1.0, 1.0)
    tint = _clamp_float(tint, -1.0, 1.0)
    vibrance = _clamp_float(vibrance, -1.0, 2.0)
    saturation = _clamp_float(saturation, 0.0, 4.0)
    rgb_gain = [_clamp_float(c, 0.0, 8.0) for c in rgb_gain]
    
    shadows_sat = _clamp_float(shadows_sat, 0.0, 0.5)
    midtones_sat = _clamp_float(midtones_sat, 0.0, 0.5)
    highlights_sat = _clamp_float(highlights_sat, 0.0, 0.5)
    grading_blending = _clamp_float(grading_blending, 0.01, 1.0)
    grading_balance = _clamp_float(grading_balance, -1.0, 1.0)

    # 3-Way Tints conversion
    def get_wheel_offset(h_deg, s_val):
        if s_val == 0.0:
            return 0.0, 0.0, 0.0
        rad = np.radians(h_deg)
        r_off = np.cos(rad) * s_val
        g_off = np.cos(rad - np.radians(120)) * s_val
        b_off = np.cos(rad - np.radians(240)) * s_val
        return r_off, g_off, b_off

    sh_r, sh_g, sh_b = get_wheel_offset(shadows_hue, shadows_sat)
    mid_r, mid_g, mid_b = get_wheel_offset(midtones_hue, midtones_sat)
    hi_r, hi_g, hi_b = get_wheel_offset(highlights_hue, highlights_sat)

    # Load and process image
    img = Image.open(input_path).convert("RGB")
    width, height = img.size
    arr = np.array(img, dtype=np.float32) / 255.0
    
    r = arr[..., 0]
    g = arr[..., 1]
    b = arr[..., 2]
    
    # Apply RGB Gain
    r *= rgb_gain[0]
    g *= rgb_gain[1]
    b *= rgb_gain[2]
    
    # Apply WB Temp and Tint
    r = r * (1.0 + temp * 0.15)
    b = b * (1.0 - temp * 0.15)
    g = g * (1.0 - tint * 0.15)
    r = r * (1.0 + tint * 0.075)
    b = b * (1.0 + tint * 0.075)
    
    # Apply Exposure
    exp_factor = 2.0 ** exposure
    r *= exp_factor
    g *= exp_factor
    b *= exp_factor
    
    # Apply Contrast
    r = (r - 0.5) * contrast + 0.5
    g = (g - 0.5) * contrast + 0.5
    b = (b - 0.5) * contrast + 0.5
    
    # Apply Highlights & Shadows
    r_high_mask = r > 0.5
    r[r_high_mask] += highlights * ((r[r_high_mask] - 0.5) / 0.5) * (1.0 - r[r_high_mask])
    g_high_mask = g > 0.5
    g[g_high_mask] += highlights * ((g[g_high_mask] - 0.5) / 0.5) * (1.0 - g[g_high_mask])
    b_high_mask = b > 0.5
    b[b_high_mask] += highlights * ((b[b_high_mask] - 0.5) / 0.5) * (1.0 - b[b_high_mask])
    
    r_low_mask = r < 0.5
    r[r_low_mask] += shadows * ((0.5 - r[r_low_mask]) / 0.5) * r[r_low_mask]
    g_low_mask = g < 0.5
    g[g_low_mask] += shadows * ((0.5 - g[g_low_mask]) / 0.5) * g[g_low_mask]
    b_low_mask = b < 0.5
    b[b_low_mask] += shadows * ((0.5 - b_low_mask) / 0.5) * b[b_low_mask]
    
    # Whites & Blacks
    r += whites * (r ** 2)
    g += whites * (g ** 2)
    b += whites * (b ** 2)
    
    r += blacks * ((1.0 - r) ** 2)
    g += blacks * ((1.0 - g) ** 2)
    b += blacks * ((1.0 - b) ** 2)
    
    # Apply 3-Way Tints
    L = 0.299 * r + 0.587 * g + 0.114 * b
    midpoint = 0.5 + 0.3 * grading_balance
    
    w_sh = (1.0 - L) * np.clip((midpoint - L) / (0.5 * grading_blending + 1e-5), 0.0, 1.0)
    w_hi = L * np.clip((L - midpoint) / (0.5 * grading_blending + 1e-5), 0.0, 1.0)
    w_mid = np.clip(1.0 - w_sh - w_hi, 0.0, 1.0)
    
    r += w_sh * sh_r + w_mid * mid_r + w_hi * hi_r
    g += w_sh * sh_g + w_mid * mid_g + w_hi * hi_g
    b += w_sh * sh_b + w_mid * mid_b + w_hi * hi_b
    
    # HSL Conversions
    max_c = np.maximum(np.maximum(r, g), b)
    min_c = np.minimum(np.minimum(r, g), b)
    delta = max_c - min_c + 1e-5
    
    h = np.zeros_like(r)
    r_mask = (max_c == r) & (delta > 0)
    g_mask = (max_c == g) & (delta > 0)
    b_mask = (max_c == b) & (delta > 0)
    
    h[r_mask] = ((g[r_mask] - b[r_mask]) / delta[r_mask]) % 6.0
    h[g_mask] = ((b[g_mask] - r[g_mask]) / delta[g_mask]) + 2.0
    h[b_mask] = ((r[b_mask] - g[b_mask]) / delta[b_mask]) + 4.0
    h = h / 6.0
    
    s = np.zeros_like(r)
    non_zero = max_c > 0
    s[non_zero] = delta[non_zero] / max_c[non_zero]
    v = max_c
    
    # Calculate HSL mixer weights (bell-curve around key hues)
    def get_hue_weight(h_val, target):
        dist = np.minimum(np.abs(h_val - target), 1.0 - np.abs(h_val - target))
        return np.exp(- (dist / 0.08) ** 2)
        
    w_red = get_hue_weight(h, 0.0) + get_hue_weight(h, 1.0)
    w_yellow = get_hue_weight(h, 0.167)
    w_green = get_hue_weight(h, 0.333)
    w_blue = get_hue_weight(h, 0.667)
    
    delta_h = w_red * hsl_red_h + w_yellow * hsl_yellow_h + w_green * hsl_green_h + w_blue * hsl_blue_h
    delta_s = w_red * hsl_red_s + w_yellow * hsl_yellow_s + w_green * hsl_green_s + w_blue * hsl_blue_s
    delta_v = w_red * hsl_red_l + w_yellow * hsl_yellow_l + w_green * hsl_green_l + w_blue * hsl_blue_l
    
    h = (h + delta_h) % 1.0
    s = np.clip(s * (1.0 + delta_s), 0.0, 1.0)
    v = np.clip(v * (1.0 + delta_v), 0.0, 1.0)
    
    # Convert HSV back to RGB
    c = v * s
    x = c * (1.0 - np.abs((h * 6.0) % 2.0 - 1.0))
    m = v - c
    
    r_new = np.zeros_like(r)
    g_new = np.zeros_like(g)
    b_new = np.zeros_like(b)
    
    h_six = h * 6.0
    m0 = (h_six >= 0) & (h_six < 1)
    m1 = (h_six >= 1) & (h_six < 2)
    m2 = (h_six >= 2) & (h_six < 3)
    m3 = (h_six >= 3) & (h_six < 4)
    m4 = (h_six >= 4) & (h_six < 5)
    m5 = (h_six >= 5) & (h_six <= 6.0)
    
    r_new[m0], g_new[m0], b_new[m0] = c[m0], x[m0], 0
    r_new[m1], g_new[m1], b_new[m1] = x[m1], c[m1], 0
    r_new[m2], g_new[m2], b_new[m2] = 0, c[m2], x[m2]
    r_new[m3], g_new[m3], b_new[m3] = 0, x[m3], c[m3]
    r_new[m4], g_new[m4], b_new[m4] = x[m4], 0, c[m4]
    r_new[m5], g_new[m5], b_new[m5] = c[m5], 0, x[m5]
    
    r = r_new + m
    g = g_new + m
    b = b_new + m
    
    # Apply Vibrance
    if vibrance != 0.0:
        max_val = np.maximum(np.maximum(r, g), b)
        min_val = np.minimum(np.minimum(r, g), b)
        sat_v = (max_val - min_val) / (max_val + 1e-5)
        boost = vibrance * (1.0 - sat_v)
        mean_val = (r + g + b) / 3.0
        r = r + (r - mean_val) * boost
        g = g + (g - mean_val) * boost
        b = b + (b - mean_val) * boost
        
    # Local Masking
    if mask_type != "None" and (mask_exposure != 0.0 or mask_temp != 0.0 or mask_vibrance != 0.0):
        y_coords, x_coords = np.mgrid[0:height, 0:width]
        
        if mask_type == "Sky":
            # AI Sky detection: top half of image, brighter, bluish
            height_weight = np.clip((height - y_coords) / (height * 0.5), 0.0, 1.0)
            color_weight = np.clip((b - r) / 0.1, 0.0, 1.0)
            mask = height_weight * color_weight
        elif mask_type == "Subject":
            # AI Subject detection: center region
            cy, cx = height / 2.0, width / 2.0
            dist_sq = ((y_coords - cy) / cy) ** 2 + ((x_coords - cx) / cx) ** 2
            mask = np.exp(-dist_sq / 0.3)
        elif mask_type == "Linear":
            mask = 1.0 - (y_coords / height)
        elif mask_type == "Radial":
            cy, cx = height / 2.0, width / 2.0
            dist = np.sqrt(((y_coords - cy) / cy) ** 2 + ((x_coords - cx) / cx) ** 2)
            mask = np.clip(1.0 - dist, 0.0, 1.0)
        else:
            mask = np.zeros_like(r)
            
        # Apply local changes based on mask
        if mask_exposure != 0.0:
            m_exp = 2.0 ** mask_exposure
            r = r * (1.0 - mask + mask * m_exp)
            g = g * (1.0 - mask + mask * m_exp)
            b = b * (1.0 - mask + mask * m_exp)
            
        if mask_temp != 0.0:
            r = r * (1.0 + mask * mask_temp * 0.15)
            b = b * (1.0 - mask * mask_temp * 0.15)
            
        if mask_vibrance != 0.0:
            max_val = np.maximum(np.maximum(r, g), b)
            min_val = np.minimum(np.minimum(r, g), b)
            sat_v = (max_val - min_val) / (max_val + 1e-5)
            boost = mask_vibrance * (1.0 - sat_v) * mask
            mean_val = (r + g + b) / 3.0
            r = r + (r - mean_val) * boost
            g = g + (g - mean_val) * boost
            b = b + (b - mean_val) * boost

    # Clamp and rebuild image
    r = np.clip(r, 0.0, 1.0)
    g = np.clip(g, 0.0, 1.0)
    b = np.clip(b, 0.0, 1.0)
    
    arr[..., 0] = r
    arr[..., 1] = g
    arr[..., 2] = b
    
    graded_arr = (arr * 255.0).astype(np.uint8)
    img_out = Image.fromarray(graded_arr)
    
    if saturation != 1.0:
        img_out = ImageEnhance.Color(img_out).enhance(saturation)
        
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img_out.save(output_path, format="PNG", optimize=True)
    return output_path
