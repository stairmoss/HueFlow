import os
import json
import torch
from PIL import Image
from transformers import AutoTokenizer, AutoModelForCausalLM

try:
    from airllm import AutoModel
except ImportError:
    AutoModel = None

class ColorGraderInference:
    def __init__(self, model_id="vikhyatk/moondream2"):
        self.model_id = model_id
        self.model = None
        self.tokenizer = None
        print(f"Initializing core AI engine for {model_id}...")
        
        # Load Tokenizer
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        except Exception as e:
            print(f"Could not load tokenizer: {e}")
            
        # Try loading via AirLLM first
        if AutoModel is not None:
            try:
                print("Loading model via AirLLM with 4-bit compression...")
                self.model = AutoModel.from_pretrained(model_id, compression="4bit", trust_remote_code=True)
                print("AirLLM model loaded successfully.")
            except Exception as e:
                print(f"Failed to load AirLLM model: {e}")
        
        # Fallback to BitsAndBytes 4-bit layer-by-layer if AirLLM isn't supported for this Vision model
        if self.model is None:
            try:
                print("Attempting 4-bit transformers layer loading (bitsandbytes)...")
                from transformers import BitsAndBytesConfig
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16
                )
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_id, 
                    trust_remote_code=True,
                    device_map="auto",
                    quantization_config=quantization_config
                )
                print("Model loaded successfully in 4-bit mode.")
            except Exception as e:
                print(f"Failed to load fallback 4-bit model: {e}")
                print("Falling back to simulated inference for UI development.")

    def analyze_image(self, image_path: str) -> dict:
        """
        Analyze the image and return color grading adjustments.
        """
        print(f"Analyzing {image_path}...")
        
        if self.model is None or self.tokenizer is None:
            print("Using mock analysis (model not loaded).")
            return self._mock_analysis()

        # Prompt instruction using Chain of Thought prompt engineering
        prompt = (
            "Analyze the aesthetic quality, colors, and lighting of this image. "
            "First, make a series of creative decisions to improve it (e.g. adjust lighting contrast, establish a cinematic color scheme like warm/cool or orange/teal, decide if sky or subject masking is useful). "
            "Then, translate these decisions into color grading values. "
            "Output a single JSON object containing two fields: "
            "1. 'thought': a string describing your aesthetic decisions and reasoning (1-2 sentences). "
            "2. 'adjustments': an object containing: "
            "exposure (float between -2.0 and 2.0), contrast (float between 0.5 and 2.0), highlights (float between -1.0 and 1.0), shadows (float between -1.0 and 1.0), whites (float between -1.0 and 1.0), blacks (float between -1.0 and 1.0), "
            "temp (float between -1.0 and 1.0), tint (float between -1.0 and 1.0), vibrance (float between -1.0 and 2.0), saturation (float between 0.0 and 2.0), "
            "shadows_hue (float between 0.0 and 360.0), shadows_sat (float between 0.0 and 0.5), midtones_hue (float between 0.0 and 360.0), midtones_sat (float between 0.0 and 0.5), highlights_hue (float between 0.0 and 360.0), highlights_sat (float between 0.0 and 0.5), "
            "grading_blending (float between 0.0 and 1.0), grading_balance (float between -1.0 and 1.0), "
            "hsl_red_h (float), hsl_red_s (float), hsl_red_l (float), hsl_yellow_h (float), hsl_yellow_s (float), hsl_yellow_l (float), "
            "hsl_green_h (float), hsl_green_s (float), hsl_green_l (float), hsl_blue_h (float), hsl_blue_s (float), hsl_blue_l (float), "
            "mask_type (string: 'None' or 'Sky' or 'Subject'), mask_exposure (float), mask_temp (float), mask_vibrance (float), and rgb_gain (list of 3 floats: [R, G, B]). "
            "Output ONLY a valid JSON object starting with { and ending with } without markdown wrapping or backticks."
        )
        
        try:
            print("Running layer-by-layer inference...")
            image = Image.open(image_path)
            
            # Try Moondream's native vision methods
            if hasattr(self.model, "query"):
                query_result = self.model.query(image, prompt)
                if isinstance(query_result, dict) and "answer" in query_result:
                    response = query_result["answer"]
                else:
                    response = str(query_result)
            elif hasattr(self.model, "encode_image") and hasattr(self.model, "answer_question"):
                enc_image = self.model.encode_image(image)
                response = self.model.answer_question(enc_image, prompt, self.tokenizer)
            else:
                # Standard generation fallback if AirLLM wrappers changed the interface
                print("Custom vision encoder not found. Attempting raw string return.")
                response = '{"thought": "Failed to analyze dynamically.", "adjustments": {"exposure": 0.0, "contrast": 1.0, "highlights": 0.0, "shadows": 0.0, "whites": 0.0, "blacks": 0.0, "temp": 0.0, "tint": 0.0, "vibrance": 0.0, "saturation": 1.0, "shadows_hue": 0.0, "shadows_sat": 0.0, "midtones_hue": 0.0, "midtones_sat": 0.0, "highlights_hue": 0.0, "highlights_sat": 0.0, "hsl_red_h": 0.0, "hsl_red_s": 0.0, "hsl_red_l": 0.0, "hsl_yellow_h": 0.0, "hsl_yellow_s": 0.0, "hsl_yellow_l": 0.0, "hsl_green_h": 0.0, "hsl_green_s": 0.0, "hsl_green_l": 0.0, "hsl_blue_h": 0.0, "hsl_blue_s": 0.0, "hsl_blue_l": 0.0, "mask_type": "None", "mask_exposure": 0.0, "mask_temp": 0.0, "mask_vibrance": 0.0, "rgb_gain": [1.0, 1.0, 1.0]}}'
                
            print(f"Model Output: {response}")
            
            # Parse JSON
            if "{" in response and "}" in response:
                json_str = response[response.find("{"):response.rfind("}")+1]
                result = json.loads(json_str)
                if "adjustments" in result:
                    return result
            
            print("Failed to parse JSON from response. Using mock fallback.")
            return self._mock_analysis()
            
        except Exception as e:
            print(f"Inference error: {e}")
            return self._mock_analysis()

    def _mock_analysis(self):
        # A mock output formatted with chain of thought reasoning
        return {
            "thought": "The image has flat contrast with cool lighting. I decided to introduce cinematic warmth by shifting highlights towards orange and cooling down the shadows, boosting contrast slightly to make details pop.",
            "adjustments": {
                "exposure": 0.05,
                "contrast": 1.15,
                "highlights": -0.05,
                "shadows": 0.1,
                "whites": 0.0,
                "blacks": -0.02,
                "temp": 0.05,
                "tint": -0.02,
                "vibrance": 0.15,
                "saturation": 1.3,
                "shadows_hue": 210.0,
                "shadows_sat": 0.05,
                "midtones_hue": 35.0,
                "midtones_sat": 0.02,
                "highlights_hue": 55.0,
                "highlights_sat": 0.03,
                "grading_blending": 0.5,
                "grading_balance": 0.0,
                "hsl_red_h": 0.0,
                "hsl_red_s": 0.05,
                "hsl_red_l": 0.0,
                "hsl_yellow_h": 0.0,
                "hsl_yellow_s": -0.02,
                "hsl_yellow_l": 0.0,
                "hsl_green_h": 0.0,
                "hsl_green_s": 0.02,
                "hsl_green_l": 0.0,
                "hsl_blue_h": 0.0,
                "hsl_blue_s": -0.03,
                "hsl_blue_l": 0.0,
                "mask_type": "None",
                "mask_exposure": 0.0,
                "mask_temp": 0.0,
                "mask_vibrance": 0.0,
                "rgb_gain": [1.1, 1.0, 0.9]
            }
        }

    def chat_grade_image(self, current_adjustments: dict, prompt: str) -> dict:
        """
        Process a chat prompt to modify the color grading adjustments.
        Supports semantic rule-based keyword mapping for instant local upgrades,
        with fallback/integration options.
        """
        import copy
        adjustments = copy.deepcopy(current_adjustments)
        
        defaults = {
            "exposure": 0.0, "contrast": 1.0, "highlights": 0.0, "shadows": 0.0, "whites": 0.0, "blacks": 0.0,
            "temp": 0.0, "tint": 0.0, "vibrance": 0.0, "saturation": 1.0,
            "shadows_hue": 0.0, "shadows_sat": 0.0, "midtones_hue": 0.0, "midtones_sat": 0.0, "highlights_hue": 0.0, "highlights_sat": 0.0,
            "grading_blending": 0.5, "grading_balance": 0.0,
            "hsl_red_h": 0.0, "hsl_red_s": 0.0, "hsl_red_l": 0.0,
            "hsl_yellow_h": 0.0, "hsl_yellow_s": 0.0, "hsl_yellow_l": 0.0,
            "hsl_green_h": 0.0, "hsl_green_s": 0.0, "hsl_green_l": 0.0,
            "hsl_blue_h": 0.0, "hsl_blue_s": 0.0, "hsl_blue_l": 0.0,
            "mask_type": "None", "mask_exposure": 0.0, "mask_temp": 0.0, "mask_vibrance": 0.0
        }
        
        for k, v in defaults.items():
            if k not in adjustments:
                adjustments[k] = v

        prompt_lower = prompt.lower()
        thought = ""
        
        if "teal" in prompt_lower and "orange" in prompt_lower:
            thought = "Establishing a classic Hollywood teal-and-orange contrast. Shifting highlights to warm golden-orange and shadows to cool cyan-teal, boosting contrast for dynamic pop."
            adjustments["shadows_hue"] = 210.0
            adjustments["shadows_sat"] = 0.25
            adjustments["highlights_hue"] = 35.0
            adjustments["highlights_sat"] = 0.20
            adjustments["contrast"] = max(adjustments["contrast"], 1.15)
            adjustments["temp"] = max(adjustments["temp"], 0.05)
            
        elif "cinematic" in prompt_lower or "film" in prompt_lower or "movie" in prompt_lower:
            thought = "Applying a cinematic film grade. Lowering highlights slightly to protect whites, lifting shadows, shifting highlights toward warm hues, and adding gentle saturation."
            adjustments["contrast"] = 1.15
            adjustments["shadows"] = 0.10
            adjustments["highlights"] = -0.05
            adjustments["temp"] = 0.05
            adjustments["saturation"] = 1.1
            adjustments["shadows_hue"] = 220.0
            adjustments["shadows_sat"] = 0.08
            adjustments["highlights_hue"] = 45.0
            adjustments["highlights_sat"] = 0.08
            
        elif "sunset" in prompt_lower or "warm" in prompt_lower or "golden" in prompt_lower:
            thought = "Enhancing warm golden tones. Shifting white balance towards amber-yellow, boosting saturation of reds/yellows, and warming the highlights."
            adjustments["temp"] = min(adjustments["temp"] + 0.3, 1.0)
            adjustments["hsl_yellow_s"] = min(adjustments["hsl_yellow_s"] + 0.2, 1.0)
            adjustments["hsl_red_s"] = min(adjustments["hsl_red_s"] + 0.15, 1.0)
            adjustments["highlights_hue"] = 45.0
            adjustments["highlights_sat"] = 0.15
            
        elif "cool" in prompt_lower or "cold" in prompt_lower or "winter" in prompt_lower or "blue" in prompt_lower:
            thought = "Cooling down the aesthetic. Shifting white balance towards blue, increasing green/blue saturation, and adding cool cyan shadows."
            adjustments["temp"] = max(adjustments["temp"] - 0.3, -1.0)
            adjustments["hsl_blue_s"] = min(adjustments["hsl_blue_s"] + 0.25, 1.0)
            adjustments["shadows_hue"] = 215.0
            adjustments["shadows_sat"] = 0.15
            
        elif "matrix" in prompt_lower or "green" in prompt_lower or "cyberpunk" in prompt_lower:
            thought = "Applying a stylized cyberpunk matrix look. Shifting tint towards green and tinting shadows/midtones to emerald hues."
            adjustments["tint"] = max(adjustments["tint"] - 0.3, -1.0)
            adjustments["midtones_hue"] = 120.0
            adjustments["midtones_sat"] = 0.12
            adjustments["shadows_hue"] = 140.0
            adjustments["shadows_sat"] = 0.15
            
        elif "black and white" in prompt_lower or "monochrome" in prompt_lower or "noir" in prompt_lower or "bw" in prompt_lower:
            thought = "Converting to dramatic high-contrast monochrome. Setting global saturation to zero, boosting contrast, and adjusting whites and blacks for punchy shadows."
            adjustments["saturation"] = 0.0
            adjustments["vibrance"] = -1.0
            adjustments["contrast"] = max(adjustments["contrast"], 1.35)
            adjustments["blacks"] = min(adjustments["blacks"] - 0.1, -0.05)
            adjustments["whites"] = min(adjustments["whites"] + 0.1, 0.2)
            
        elif "bright" in prompt_lower or "expose" in prompt_lower or "high key" in prompt_lower:
            thought = "Increasing brightness. Raising exposure, opening shadows, and lifting whites to introduce a high-key airy look."
            adjustments["exposure"] = min(adjustments["exposure"] + 0.4, 2.0)
            adjustments["shadows"] = min(adjustments["shadows"] + 0.2, 1.0)
            adjustments["whites"] = min(adjustments["whites"] + 0.15, 1.0)
            
        elif "dark" in prompt_lower or "moody" in prompt_lower or "low key" in prompt_lower:
            thought = "Establishing a dark, moody atmosphere. Lowering exposure, dropping shadows, and shifting blacks downward while boosting midtone contrast."
            adjustments["exposure"] = max(adjustments["exposure"] - 0.4, -2.0)
            adjustments["shadows"] = max(adjustments["shadows"] - 0.25, -1.0)
            adjustments["blacks"] = max(adjustments["blacks"] - 0.15, -1.0)
            adjustments["contrast"] = max(adjustments["contrast"], 1.2)
            
        elif "vibrant" in prompt_lower or "pop" in prompt_lower or "colorful" in prompt_lower:
            thought = "Boosting vibrance and saturation. Selectively enhancing muted colors first via vibrance, and slightly lifting global saturation for extra punch."
            adjustments["vibrance"] = min(adjustments["vibrance"] + 0.35, 2.0)
            adjustments["saturation"] = min(adjustments["saturation"] + 0.15, 2.0)
            
        elif "flat" in prompt_lower or "log" in prompt_lower or "soft" in prompt_lower:
            thought = "Softening the image. Decreasing contrast, lifting blacks, and dropping highlights to create a low-contrast logarithmic look."
            adjustments["contrast"] = max(adjustments["contrast"] - 0.3, 0.5)
            adjustments["blacks"] = min(adjustments["blacks"] + 0.15, 1.0)
            adjustments["highlights"] = max(adjustments["highlights"] - 0.15, -1.0)
            
        elif "reset" in prompt_lower or "clear" in prompt_lower or "default" in prompt_lower:
            thought = "Resetting all grading controls to absolute neutral defaults."
            adjustments = copy.deepcopy(defaults)
            
        else:
            thought = f"Adjusting settings to reflect: '{prompt}'. Applied minor adjustments to saturation and contrast balance."
            if "saturation" in prompt_lower or "color" in prompt_lower:
                adjustments["saturation"] = min(adjustments["saturation"] + 0.1, 2.0)
            if "contrast" in prompt_lower:
                adjustments["contrast"] = min(adjustments["contrast"] + 0.1, 2.0)
            if "brightness" in prompt_lower or "exposure" in prompt_lower:
                adjustments["exposure"] = min(adjustments["exposure"] + 0.1, 2.0)
                
        return {
            "thought": thought,
            "adjustments": adjustments
        }

if __name__ == "__main__":
    grader = ColorGraderInference()
    result = grader.analyze_image("dummy.jpg")
    print("Result:", json.dumps(result, indent=2))
