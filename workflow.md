# 🔄 HueFlow: Technical Workflow

This document outlines the internal logic and data flow of the Zentalic AI Color Grader, specifically focusing on the optimization for low-RAM (6GB) systems and the conversion of AI analysis into professional `.cube` files.

---

## 🏗️ Phase 1: The "Layer-by-Layer" Inference (AirLLM)

Traditional LLMs load the entire model (10GB - 40GB+) into VRAM or RAM. On an i3 with 6GB RAM, this would cause an immediate crash. Zentalic Labs uses **AirLLM** to solve this.

### The Cycle:
1.  **Model Partitioning:** The Vision LLM (e.g., Llama-3.2-Vision) is stored on the SSD in "shards" (individual transformer layers).
2.  **Request Initialization:** The user uploads a **Source Image** and a **Target Footage Frame**.
3.  **Sequential Execution:** - The CPU loads **Layer 0** into RAM.
    - Data passes through the layer.
    - **Layer 0** is purged; **Layer 1** is loaded.
    - This repeats for all 32+ layers.
4.  **Result:** The AI identifies the **Color Grade Recipe** (Contrast, Saturation, Temperature, RGB Gains).

---

## 🎨 Phase 2: The Color Science Engine

Once the AI produces the numerical recipe, the Python backend translates those numbers into a visual transformation.

### 1. Analysis Output
The AI generates a standardized JSON payload:
```json
{
  "zentalic_id": "Z-9421",
  "adjustments": {
    "brightness": 0.05,
    "contrast": 1.15,
    "saturation": 1.3,
    "rgb_gain": [1.1, 1.0, 0.9]
  }
}

