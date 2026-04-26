import os
import json
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from PIL import Image
import threading

# Import the core engine and LUT generator
from core.inference import ColorGraderInference
from utils.lut_gen import generate_cube_lut

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configure "dark immersive" window
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.title("HueFlow AI Color Grader")
        self.geometry("900x600")
        self.minsize(800, 500)
        
        # Initialize Core AI Engine
        self.ai_engine = ColorGraderInference()
        self.current_image_path = None
        self.current_adjustments = None
        
        self._setup_ui()

    def _setup_ui(self):
        # Grid layout (1 row, 2 columns)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Left Panel (Image Display)
        self.left_panel = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=15)
        self.left_panel.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.left_panel.grid_rowconfigure(0, weight=1)
        self.left_panel.grid_columnconfigure(0, weight=1)
        
        self.image_label = ctk.CTkLabel(
            self.left_panel, 
            text="No Image Selected\n\nClick 'Upload Image' to begin.",
            font=("Inter", 16),
            text_color="gray"
        )
        self.image_label.grid(row=0, column=0, sticky="nsew")
        
        # Right Panel (Controls & Stats)
        self.right_panel = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=15)
        self.right_panel.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        # Title
        self.title_label = ctk.CTkLabel(
            self.right_panel, 
            text="HueFlow AI", 
            font=("Inter", 28, "bold"),
            text_color="#ffffff"
        )
        self.title_label.pack(pady=(30, 10))
        
        self.subtitle_label = ctk.CTkLabel(
            self.right_panel, 
            text="Zentalic Core Engine", 
            font=("Inter", 12),
            text_color="#888888"
        )
        self.subtitle_label.pack(pady=(0, 30))
        
        # Buttons
        self.btn_upload = ctk.CTkButton(
            self.right_panel, 
            text="Upload Source Image", 
            font=("Inter", 14),
            height=40,
            command=self.upload_image
        )
        self.btn_upload.pack(pady=10, padx=40, fill="x")
        
        self.btn_analyze = ctk.CTkButton(
            self.right_panel, 
            text="Analyze with AirLLM", 
            font=("Inter", 14),
            height=40,
            fg_color="#006400",
            hover_color="#004d00",
            state="disabled",
            command=self.start_analysis
        )
        self.btn_analyze.pack(pady=10, padx=40, fill="x")
        
        self.btn_export = ctk.CTkButton(
            self.right_panel, 
            text="Export .cube LUT", 
            font=("Inter", 14),
            height=40,
            fg_color="#8b0000",
            hover_color="#660000",
            state="disabled",
            command=self.export_lut
        )
        self.btn_export.pack(pady=10, padx=40, fill="x")
        
        # Output Text Box
        self.output_box = ctk.CTkTextbox(
            self.right_panel, 
            font=("Courier", 12), 
            fg_color="#1e1e1e",
            text_color="#00ff00"
        )
        self.output_box.pack(pady=20, padx=40, fill="both", expand=True)
        self.output_box.insert("0.0", "Status: Ready.\nMemory footprint: 6GB Limit Mode.\nWaiting for image...")
        self.output_box.configure(state="disabled")

    def log(self, text):
        self.output_box.configure(state="normal")
        self.output_box.delete("0.0", "end")
        self.output_box.insert("0.0", text)
        self.output_box.configure(state="disabled")

    def upload_image(self):
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.webp")]
        )
        if file_path:
            self.current_image_path = file_path
            
            # Display Image
            try:
                img = Image.open(file_path)
                # Resize for display
                img.thumbnail((500, 500))
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                self.image_label.configure(image=ctk_img, text="")
                self.image_label.image = ctk_img
                
                self.log(f"Image loaded: {os.path.basename(file_path)}\nReady for analysis.")
                self.btn_analyze.configure(state="normal")
                self.btn_export.configure(state="disabled")
            except Exception as e:
                self.log(f"Error loading image: {e}")

    def start_analysis(self):
        if not self.current_image_path:
            return
            
        self.btn_analyze.configure(state="disabled")
        self.btn_upload.configure(state="disabled")
        self.log("Running AirLLM layer-by-layer inference...\nThis may take a moment on i3 CPUs.")
        
        # Run inference in a background thread to keep UI responsive
        threading.Thread(target=self._run_inference_task).start()

    def _run_inference_task(self):
        try:
            result = self.ai_engine.analyze_image(self.current_image_path)
            self.current_adjustments = result.get("adjustments", {})
            
            display_text = "Analysis Complete!\n\nExtracted Parameters:\n"
            display_text += json.dumps(result, indent=2)
            
            # Update UI from main thread
            self.after(0, self.log, display_text)
            self.after(0, lambda: self.btn_export.configure(state="normal"))
            self.after(0, lambda: self.btn_upload.configure(state="normal"))
            self.after(0, lambda: self.btn_analyze.configure(state="normal"))
            
        except Exception as e:
            self.after(0, self.log, f"Analysis Error: {e}")
            self.after(0, lambda: self.btn_upload.configure(state="normal"))
            self.after(0, lambda: self.btn_analyze.configure(state="normal"))

    def export_lut(self):
        if not self.current_adjustments:
            return
            
        output_path = filedialog.asksaveasfilename(
            title="Save 3D LUT",
            defaultextension=".cube",
            initialfile="HueFlow_Grade.cube",
            filetypes=[("CUBE files", "*.cube")]
        )
        
        if output_path:
            try:
                generate_cube_lut(self.current_adjustments, output_path)
                self.log(f"Successfully exported 33x33x33 LUT to:\n{output_path}\n\nReady for use in DaVinci Resolve or Premiere Pro.")
            except Exception as e:
                self.log(f"Error generating LUT: {e}")

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
