# HueFlow Project Rules & Constraints

## Hardware & Environment
- **Target Hardware**: Intel i3 processor with a maximum of 6GB RAM.
- **Inference Mode**: Layer-by-layer inference must be used to minimize memory footprint. Do not load entire models into RAM at once.

## AI Engine
- **Framework**: `AirLLM`
- **Model**: `thauto/Moondream2`
- **Quantization**: 4-bit quantization must be used to keep memory usage under the 4.5GB peak limit.
- **Output**: The model must analyze an image and return a JSON object with specific color grading parameters: RGB gain, contrast, and saturation.

## Output Structure
```json
{
  "adjustments": {
    "brightness": <float>,
    "contrast": <float>,
    "saturation": <float>,
    "rgb_gain": [<float>, <float>, <float>]
  }
}
```

## User Interface
- **Framework**: `CustomTkinter`
- **Style**: Minimalist, "dark immersive" desktop window.

## Utilities
- **LUT Export**: Generate `.cube` format 3D LUTs (size 33x33x33) from the AI's parameter output.
- **Validation**: Clamp generated RGB values between 0.0 and 1.0 to prevent clipping and ensure professional stability.
