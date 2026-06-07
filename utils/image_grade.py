import os
from typing import Dict, Any, List

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


def _generate_lut_for_channel(
    gain: float,
    exposure: float,
    contrast: float,
    highlights: float,
    shadows: float,
    whites: float,
    blacks: float,
) -> List[int]:
    lut = []
    exp_factor = 2.0 ** exposure
    for i in range(256):
        val = i / 255.0

        # Apply Gain
        val *= gain

        # Apply Exposure
        val *= exp_factor

        # Apply Contrast (pivoting around mid-gray 0.5)
        val = (val - 0.5) * contrast + 0.5

        # Apply Highlights (adjusts highlights, val > 0.5)
        if val > 0.5:
            w = (val - 0.5) / 0.5
            val = val + highlights * w * (1.0 - val)

        # Apply Shadows (adjusts shadows, val < 0.5)
        if val < 0.5:
            w = (0.5 - val) / 0.5
            val = val + shadows * w * val

        # Apply Whites (strongest at 1.0)
        val += whites * (val ** 2)

        # Apply Blacks (strongest at 0.0)
        val += blacks * ((1.0 - val) ** 2)

        # Clamp to [0.0, 1.0]
        val = max(0.0, min(1.0, val))
        lut.append(int(val * 255.0))
    return lut


def apply_adjustments_to_image(
    input_path: str,
    adjustments: Dict[str, Any],
    output_path: str,
) -> str:
    """
    Applies HueFlow adjustments to an image and saves a PNG.
    This includes Exposure, Contrast, Highlights, Shadows, Whites, Blacks, Saturation, and RGB Gain.
    """
    exposure = float(adjustments.get("exposure", 0.0))
    brightness = float(adjustments.get("brightness", 0.0))
    exposure += brightness  # Merge legacy brightness into exposure

    contrast = float(adjustments.get("contrast", 1.0))
    highlights = float(adjustments.get("highlights", 0.0))
    shadows = float(adjustments.get("shadows", 0.0))
    whites = float(adjustments.get("whites", 0.0))
    blacks = float(adjustments.get("blacks", 0.0))
    saturation = float(adjustments.get("saturation", 1.0))
    rgb_gain = _safe_rgb_gain(adjustments.get("rgb_gain", [1.0, 1.0, 1.0]))

    # Clamp ranges for sanity
    exposure = _clamp_float(exposure, -3.0, 3.0)
    contrast = _clamp_float(contrast, 0.0, 4.0)
    highlights = _clamp_float(highlights, -1.0, 1.0)
    shadows = _clamp_float(shadows, -1.0, 1.0)
    whites = _clamp_float(whites, -1.0, 1.0)
    blacks = _clamp_float(blacks, -1.0, 1.0)
    saturation = _clamp_float(saturation, 0.0, 4.0)
    rgb_gain = [_clamp_float(c, 0.0, 8.0) for c in rgb_gain]

    r_lut = _generate_lut_for_channel(rgb_gain[0], exposure, contrast, highlights, shadows, whites, blacks)
    g_lut = _generate_lut_for_channel(rgb_gain[1], exposure, contrast, highlights, shadows, whites, blacks)
    b_lut = _generate_lut_for_channel(rgb_gain[2], exposure, contrast, highlights, shadows, whites, blacks)

    img = Image.open(input_path).convert("RGB")

    r, g, b = img.split()
    r = r.point(r_lut)
    g = g.point(g_lut)
    b = b.point(b_lut)
    img = Image.merge("RGB", (r, g, b))

    # Apply Saturation
    if saturation != 1.0:
        img = ImageEnhance.Color(img).enhance(saturation)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path, format="PNG", optimize=True)
    return output_path
