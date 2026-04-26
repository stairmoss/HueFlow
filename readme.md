# HueFlow 🎨🤖

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Zentalic Labs](https://img.shields.io/badge/Developed%20By-Zentalic%20Labs-blue)](

The **Zentalic AI Photo Color Grader** is a high-performance tool that generates custom `.cube` LUTs by utilizing AI to analyze the color profile of a reference image and apply that look to other footage. By automating the creation of 3D LUTs, the tool streamlines post-production for software like **DaVinci Resolve**, **Adobe Premiere**, and **Final Cut Pro**.

Developed by **Zentalic Labs**, this project is specifically engineered to run advanced Vision LLMs on consumer-grade hardware  using a unique **Layer-by-Layer Inference** architecture via **AirLLM**.

---

## ✨ Key Features

-   **Layer-by-Layer Inference (AirLLM):** Run 11B+ parameter models on just 6GB of RAM by swapping transformer layers from SSD to memory in real-time.
-   **Hybrid Model Support:** Toggle between local execution (AirLLM) and Cloud APIs (Anthropic Claude, OpenAI GPT-4o, or Google Gemini).
-   **Professional .cube Export:** Generates industry-standard 33x33x33 3D LUTs for professional color grading workflows.
-   **Zentalic "Style ID":** Every AI-generated grade is assigned a unique sharing number (e.g., `Z-1024`) for instant style replication.
-   **Dark Immersive UI:** A minimalist, high-end interface inspired by the aesthetics of Claude.ai and Cursor.

---

## 🏗️ The Tech Stack

| Component | Technology |
| :--- | :--- |
| **AI Backend** | Python 3.11+, AirLLM, PyTorch |
| **Vision Models** | Moondream2 (Local), Llama-3.2-Vision (AirLLM) |
| **APIs** | Anthropic (Claude 3.5), OpenAI, Google Gemini |
| **Image Engine** | OpenCV, NumPy, Pillow |
| **Frontend** | React / Next.js (Web), PyQt6 (Desktop EXE) |
| **Compiler** | Nuitka (Standalone Executable) |

---

## 🔄 The "Layer-by-Layer" Workflow

To support low-RAM environments (6GB), this project utilizes the **AirLLM** architecture. Instead of loading the entire model into VRAM, it follows this automated cycle:

1.  **Sharding:** The model is split into atomic transformer layers on the disk.
2.  **Sequential Loading:** Layer 1 is loaded into RAM → Processed → Deleted.
3.  **Cyclic Processing:** This repeats for all layers (1 to 32) until a color analysis is produced.
4.  **Parameter Extraction:** The AI outputs a JSON object containing `Gain`, `Gamma`, `Lift`, and `Saturation` values.
5.  **LUT Generation:** Python calculates the 3D cube map and saves the `.cube` file.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- 6GB RAM (Minimum)
- SSD (Highly recommended for AirLLM swapping speed)

### Local Development
```bash
# Clone the repository
git clone [https://github.com/zentalic/ai-photo-color-grader.git](https://github.com/zentalic/ai-photo-color-grader.git)
cd ai-photo-color-grader

# Install dependencies
pip install airllm opencv-python pillow anthropic openai

# Run the application
python app.py