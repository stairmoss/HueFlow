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


def apply_adjustments_to_image(
    input_path: str,
    adjustments: Dict[str, Any],
    output_path: str,
) -> str:
    """
    Applies HueFlow adjustments to an image and saves a PNG.

    This is intentionally lightweight (Pillow) so it runs on low-RAM systems.
    """
    brightness = float(adjustments.get("brightness", 0.0))
    contrast = float(adjustments.get("contrast", 1.0))
    saturation = float(adjustments.get("saturation", 1.0))
    rgb_gain = _safe_rgb_gain(adjustments.get("rgb_gain", [1.0, 1.0, 1.0]))

    # Keep things sane if a model returns extreme values
    brightness = _clamp_float(brightness, -1.0, 1.0)
    contrast = _clamp_float(contrast, 0.0, 4.0)
    saturation = _clamp_float(saturation, 0.0, 4.0)
    rgb_gain = [_clamp_float(c, 0.0, 8.0) for c in rgb_gain]

    img = Image.open(input_path).convert("RGB")

    # Apply per-channel gain
    r, g, b = img.split()
    r = r.point(lambda p: int(_clamp_float(p * rgb_gain[0], 0, 255)))
    g = g.point(lambda p: int(_clamp_float(p * rgb_gain[1], 0, 255)))
    b = b.point(lambda p: int(_clamp_float(p * rgb_gain[2], 0, 255)))
    img = Image.merge("RGB", (r, g, b))

    # Contrast around mid-gray using Pillow's enhancer
    if contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(contrast)

    # Brightness: HueFlow's "brightness" is additive in LUT space;
    # approximate by scaling around 1.0 (small values behave similarly).
    if brightness != 0.0:
        img = ImageEnhance.Brightness(img).enhance(1.0 + brightness)

    # Saturation
    if saturation != 1.0:
        img = ImageEnhance.Color(img).enhance(saturation)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path, format="PNG", optimize=True)
    return output_path

