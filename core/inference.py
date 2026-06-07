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

        # Prompt instruction
        prompt = (
            "Analyze the color profile of this image and output a JSON object with "
            "brightness (float), contrast (float), saturation (float), and rgb_gain (list of 3 floats: [R, G, B]). "
            "Output ONLY valid JSON like: {\"adjustments\": {\"brightness\": 0.05, \"contrast\": 1.15, \"saturation\": 1.3, \"rgb_gain\": [1.1, 1.0, 0.9]}}"
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
                response = '{"adjustments": {"brightness": 0.0, "contrast": 1.0, "saturation": 1.0, "rgb_gain": [1.0, 1.0, 1.0]}}'
                
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
        # A mock output formatted as requested
        return {
            "adjustments": {
                "brightness": 0.05,
                "contrast": 1.15,
                "saturation": 1.3,
                "rgb_gain": [1.1, 1.0, 0.9]
            }
        }

if __name__ == "__main__":
    grader = ColorGraderInference()
    result = grader.analyze_image("dummy.jpg")
    print("Result:", json.dumps(result, indent=2))
