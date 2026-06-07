import os
import json
import tkinter as tk
from tkinter import filedialog
import subprocess
import sys
from PIL import Image
import threading

# Create graded PNG output from adjustments
from utils.image_grade import apply_adjustments_to_image

# CustomTkinter is preferred, but fall back to standard Tkinter so the app
# still runs in minimal mode even if dependencies aren't installed.
try:
    import customtkinter as ctk  # type: ignore
    _HAS_CUSTOMTKINTER = True
except Exception:
    _HAS_CUSTOMTKINTER = False

    class _CTKCompat:
        CTk = tk.Tk
        CTkFrame = tk.Frame
        CTkLabel = tk.Label
        CTkButton = tk.Button
        CTkTextbox = tk.Text

        @staticmethod
        def set_appearance_mode(_mode: str):
            return

        @staticmethod
        def set_default_color_theme(_theme: str):
            return

        class CTkImage:
            def __init__(self, light_image, dark_image=None, size=None):
                img = light_image
                if size:
                    img = img.copy()
                    img = img.resize(size)
                try:
                    from PIL import ImageTk  # pillow-imagetk on some distros
                    self._photo = ImageTk.PhotoImage(img)
                except Exception:
                    self._photo = None

            @property
            def image(self):
                return self._photo

    ctk = _CTKCompat()  # type: ignore

# Import the core engine and LUT generator
from core.inference import ColorGraderInference
from utils.lut_gen import generate_cube_lut


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("HueFlow AI")
        self.geometry("1000x700")
        self.minsize(900, 600)
        
        # Initialize core engine variables
        self.ai_engine = None
        self.current_image_path = None
        self.current_adjustments = {}
        self.current_graded_image_path = None
        self._preview_timer = None
        
        # Define ranges: (min, max, default)
        self.slider_ranges = {
            "exposure": (-3.0, 3.0, 0.0),
            "contrast": (0.0, 4.0, 1.0),
            "highlights": (-1.0, 1.0, 0.0),
            "shadows": (-1.0, 1.0, 0.0),
            "whites": (-1.0, 1.0, 0.0),
            "blacks": (-1.0, 1.0, 0.0),
            "temp": (-1.0, 1.0, 0.0),
            "tint": (-1.0, 1.0, 0.0),
            "vibrance": (-1.0, 2.0, 0.0),
            "saturation": (0.0, 4.0, 1.0),
        }
        
        # Tkinter variables for sliders
        self.slider_vars = {}
        self.slider_widgets = {}
        self.label_widgets = {}
        for key, (lo, hi, default) in self.slider_ranges.items():
            self.slider_vars[key] = tk.DoubleVar(value=default)
            self.current_adjustments[key] = default
        self.current_adjustments["rgb_gain"] = [1.0, 1.0, 1.0]
        
        self._setup_ui()
        
        # Initialize AI engine in background so UI opens immediately
        threading.Thread(target=self._init_ai_engine, daemon=True).start()

    def _try_zenity_file_dialog(self, *, mode: str, title: str, patterns=None, suggested_filename: str | None = None):
        if not sys.platform.startswith("linux"):
            return None

        args = ["zenity"]
        if mode == "open":
            args += ["--file-selection", "--title", title]
            if patterns:
                for p in patterns:
                    args += ["--file-filter", p]
        elif mode == "save":
            args += ["--file-selection", "--save", "--confirm-overwrite", "--title", title]
            if suggested_filename:
                args += ["--filename", os.path.join(os.path.expanduser("~"), suggested_filename)]
            if patterns:
                for p in patterns:
                    args += ["--file-filter", p]
        else:
            return None

        try:
            proc = subprocess.run(args, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except Exception:
            return None

        if proc.returncode != 0:
            return None

        picked = (proc.stdout or "").strip()
        return picked or None

    def _pick_image_path(self) -> str | None:
        picked = self._try_zenity_file_dialog(
            mode="open",
            title="Select Image",
            patterns=["Images | *.jpg *.jpeg *.png *.webp"],
        )
        if picked:
            return picked

        initialdir = os.path.expanduser("~/Pictures")
        if not os.path.isdir(initialdir):
            initialdir = os.path.expanduser("~")

        return filedialog.askopenfilename(
            parent=self,
            title="Select Image",
            initialdir=initialdir,
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.webp")],
        ) or None

    def _pick_lut_save_path(self) -> str | None:
        picked = self._try_zenity_file_dialog(
            mode="save",
            title="Save 3D LUT",
            patterns=["CUBE LUT | *.cube"],
            suggested_filename="HueFlow_Grade.cube",
        )
        if picked:
            if not picked.lower().endswith(".cube"):
                picked += ".cube"
            return picked

        initialdir = os.path.expanduser("~/Documents")
        if not os.path.isdir(initialdir):
            initialdir = os.path.expanduser("~")

        return filedialog.asksaveasfilename(
            parent=self,
            title="Save 3D LUT",
            initialdir=initialdir,
            defaultextension=".cube",
            initialfile="HueFlow_Grade.cube",
            filetypes=[("CUBE files", "*.cube")],
        ) or None

    def _init_ai_engine(self):
        self.after(0, self.log, "Initializing AI Engine (downloading models if needed)...\nThis may take a few minutes on first run.")
        try:
            self.ai_engine = ColorGraderInference()
            self.after(0, self.log, "Status: AI Engine Ready.\nMemory footprint: 6GB Limit Mode.\nWaiting for image...")
        except Exception as e:
            self.after(0, self.log, f"Failed to load AI Engine: {e}")

    def _setup_ui(self):
        if _HAS_CUSTOMTKINTER:
            # Grid layout: left side has visual preview, right side has control panels
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
            self.right_panel.grid_columnconfigure(0, weight=1)
            self.right_panel.grid_rowconfigure(3, weight=1) # Let the text box expand
            
            # Header Row
            header_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
            header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
            
            self.title_label = ctk.CTkLabel(
                header_frame, 
                text="HueFlow AI", 
                font=("Inter", 24, "bold"),
                text_color="#ffffff"
            )
            self.title_label.pack(side="left")
            self.subtitle_label = ctk.CTkLabel(
                header_frame, 
                text="  Zentalic Color Science", 
                font=("Inter", 12),
                text_color="#888888"
            )
            self.subtitle_label.pack(side="left", padx=5, pady=(5, 0))
            
            # Buttons Row
            buttons_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
            buttons_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
            
            self.btn_upload = ctk.CTkButton(
                buttons_frame, 
                text="Upload Image", 
                font=("Inter", 13),
                height=36,
                command=self.upload_image
            )
            self.btn_upload.pack(side="left", fill="x", expand=True, padx=(0, 5))
            
            self.btn_analyze = ctk.CTkButton(
                buttons_frame, 
                text="Analyze (AI Auto)", 
                font=("Inter", 13),
                height=36,
                fg_color="#006400",
                hover_color="#004d00",
                state="disabled",
                command=self.start_analysis
            )
            self.btn_analyze.pack(side="left", fill="x", expand=True, padx=5)
            
            self.btn_export = ctk.CTkButton(
                buttons_frame, 
                text="Export .cube LUT", 
                font=("Inter", 13),
                height=36,
                fg_color="#8b0000",
                hover_color="#660000",
                state="disabled",
                command=self.export_lut
            )
            self.btn_export.pack(side="left", fill="x", expand=True, padx=(5, 0))
            
            # Scrollable Slider Panel
            self.scroll_panel = ctk.CTkScrollableFrame(self.right_panel, fg_color="#222222", corner_radius=10)
            self.scroll_panel.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
            self.scroll_panel.grid_columnconfigure(0, weight=1)
            
            # Add sliders to the scroll panel
            row_idx = 0
            
            # SECTION: LIGHT PANEL
            lbl_light = ctk.CTkLabel(self.scroll_panel, text="Light Panel (Exposure & Contrast)", font=("Inter", 14, "bold"), text_color="#3b82f6")
            lbl_light.grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))
            row_idx += 1
            
            light_keys = ["exposure", "contrast", "highlights", "shadows", "whites", "blacks"]
            for k in light_keys:
                row_idx = self._add_ctk_slider(self.scroll_panel, k, row_idx)
                
            # SECTION: COLOR PANEL
            lbl_color = ctk.CTkLabel(self.scroll_panel, text="Color Panel (White Balance & Vibrance)", font=("Inter", 14, "bold"), text_color="#10b981")
            lbl_color.grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=10, pady=(15, 5))
            row_idx += 1
            
            color_keys = ["temp", "tint", "vibrance", "saturation"]
            for k in color_keys:
                row_idx = self._add_ctk_slider(self.scroll_panel, k, row_idx)
                
            # Output Text Box
            self.output_box = ctk.CTkTextbox(
                self.right_panel, 
                font=("Courier", 11), 
                fg_color="#1e1e1e",
                text_color="#00ff00",
                height=120
            )
            self.output_box.grid(row=3, column=0, sticky="nsew", padx=20, pady=(10, 20))
            self.output_box.insert("0.0", "Status: Ready.\nMemory footprint: 6GB Limit Mode.\nWaiting for image...")
            self.output_box.configure(state="disabled")
            return

        # Minimal Tkinter UI Fallback
        self.configure(bg="#1e1e1e")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = tk.Frame(self, bg="#1e1e1e")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)

        title = tk.Label(header, text="HueFlow AI", fg="white", bg="#1e1e1e", font=("Arial", 18, "bold"))
        title.grid(row=0, column=0, sticky="w")
        subtitle = tk.Label(header, text="(minimal mode)", fg="#aaaaaa", bg="#1e1e1e", font=("Arial", 10))
        subtitle.grid(row=1, column=0, sticky="w")

        controls = tk.Frame(self, bg="#1e1e1e")
        controls.grid(row=2, column=0, sticky="ew", padx=16, pady=8)

        self.btn_upload = tk.Button(controls, text="Upload Image", command=self.upload_image)
        self.btn_upload.pack(side="left", padx=(0, 8))
        self.btn_analyze = tk.Button(controls, text="Analyze (AI)", command=self.start_analysis, state="disabled")
        self.btn_analyze.pack(side="left", padx=(0, 8))
        self.btn_export = tk.Button(controls, text="Export .cube LUT", command=self.export_lut, state="disabled")
        self.btn_export.pack(side="left")

        body = tk.Frame(self, bg="#1e1e1e")
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left = tk.Frame(body, bg="#111111")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)
        self.image_label = tk.Label(left, text="No Image Selected.\nClick Upload to begin.", fg="#aaaaaa", bg="#111111")
        self.image_label.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

        right = tk.Frame(body, bg="#111111")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(2, weight=1)
        
        # Minimal Sliders Frame
        sliders_frame = tk.Frame(right, bg="#111111")
        sliders_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        sliders_frame.grid_columnconfigure(1, weight=1)
        
        row_idx = 0
        # Add normal sliders
        all_keys = ["exposure", "contrast", "highlights", "shadows", "whites", "blacks", "temp", "tint", "vibrance", "saturation"]
        for k in all_keys:
            row_idx = self._add_tk_slider(sliders_frame, k, row_idx)

        self.output_box = tk.Text(right, bg="#0f0f0f", fg="#00ff00", insertbackground="#00ff00", font=("Courier", 10), height=8)
        self.output_box.grid(row=2, column=0, sticky="nsew", padx=12, pady=12)
        self.output_box.insert("1.0", "Status: Ready.\nMemory footprint: 6GB Limit Mode.\nWaiting for image...")
        self.output_box.configure(state="disabled")

    def _add_ctk_slider(self, parent, key: str, row_idx: int) -> int:
        lo, hi, default = self.slider_ranges[key]
        
        lbl_name = ctk.CTkLabel(parent, text=key.capitalize(), font=("Inter", 12), text_color="#dddddd")
        lbl_name.grid(row=row_idx, column=0, sticky="w", padx=15, pady=2)
        
        lbl_val = ctk.CTkLabel(parent, text=f"{default:.2f}", font=("Inter", 11), text_color="#aaaaaa")
        lbl_val.grid(row=row_idx, column=1, sticky="e", padx=15, pady=2)
        self.label_widgets[key] = lbl_val
        row_idx += 1
        
        slider = ctk.CTkSlider(
            parent, 
            from_=lo, 
            to=hi, 
            variable=self.slider_vars[key],
            command=self._on_slider_move
        )
        slider.grid(row=row_idx, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 8))
        self.slider_widgets[key] = slider
        row_idx += 1
        return row_idx

    def _add_tk_slider(self, parent, key: str, row_idx: int) -> int:
        lo, hi, default = self.slider_ranges[key]
        lbl = tk.Label(parent, text=key.capitalize(), fg="#cccccc", bg="#111111", font=("Arial", 9))
        lbl.grid(row=row_idx, column=0, sticky="w", padx=5)
        
        slider = tk.Scale(
            parent, 
            from_=lo, 
            to=hi, 
            resolution=0.05, 
            orient="horizontal", 
            variable=self.slider_vars[key],
            showvalue=True,
            bg="#111111",
            fg="white",
            highlightthickness=0,
            command=self._on_slider_move
        )
        slider.grid(row=row_idx, column=1, sticky="ew", padx=5)
        self.slider_widgets[key] = slider
        row_idx += 1
        return row_idx

    def _update_all_labels(self):
        for key in self.slider_ranges.keys():
            val = self.slider_vars[key].get()
            if key in self.label_widgets:
                self.label_widgets[key].configure(text=f"{val:.2f}")

    def _on_slider_move(self, _val=None):
        self._update_all_labels()
        # Debounce the preview update to avoid lagging the UI while dragging
        if self._preview_timer:
            self.after_cancel(self._preview_timer)
        self._preview_timer = self.after(120, self._apply_current_slider_adjustments)

    def _apply_current_slider_adjustments(self):
        if not self.current_image_path:
            return
        adj = {}
        for k in self.slider_ranges.keys():
            adj[k] = self.slider_vars[k].get()
        # Keep the AI-predicted RGB gain if we have it
        if "rgb_gain" in self.current_adjustments:
            adj["rgb_gain"] = self.current_adjustments["rgb_gain"]
        else:
            adj["rgb_gain"] = [1.0, 1.0, 1.0]
            
        self.current_adjustments = adj
        threading.Thread(target=self._run_slider_grade_task, args=(adj,), daemon=True).start()

    def _run_slider_grade_task(self, adj):
        try:
            base, _ext = os.path.splitext(self.current_image_path)
            graded_path = base + "_graded.png"
            self.current_graded_image_path = apply_adjustments_to_image(
                self.current_image_path,
                adj,
                graded_path
            )
            # Display updated image on main thread
            self.after(0, lambda: self._display_image(self.current_graded_image_path))
        except Exception as e:
            print(f"Error grading from slider: {e}")

    def _update_sliders_from_adjustments(self, adj: dict):
        for key in self.slider_ranges.keys():
            if key in adj:
                self.slider_vars[key].set(float(adj[key]))
            elif key == "temp" and "temperature" in adj:
                self.slider_vars[key].set(float(adj["temperature"]))
        self._update_all_labels()

    def log(self, text):
        if _HAS_CUSTOMTKINTER:
            self.output_box.configure(state="normal")
            self.output_box.delete("0.0", "end")
            self.output_box.insert("0.0", text)
            self.output_box.configure(state="disabled")
        else:
            self.output_box.configure(state="normal")
            self.output_box.delete("1.0", "end")
            self.output_box.insert("1.0", text)
            self.output_box.configure(state="disabled")

    def upload_image(self):
        file_path = self._pick_image_path()
        if file_path:
            self.current_image_path = file_path
            self.current_graded_image_path = None
            
            # Reset sliders to default values
            for key, (lo, hi, default) in self.slider_ranges.items():
                self.slider_vars[key].set(default)
            self._update_all_labels()
            self.current_adjustments = {k: self.slider_ranges[k][2] for k in self.slider_ranges.keys()}
            self.current_adjustments["rgb_gain"] = [1.0, 1.0, 1.0]
            
            # Display Image
            try:
                self._display_image(file_path)
                self.log(f"Image loaded: {os.path.basename(file_path)}\nReady for analysis.")
                self.btn_analyze.configure(state="normal")
                self.btn_export.configure(state="disabled")
            except Exception as e:
                self.log(f"Error loading image: {e}")

    def start_analysis(self):
        if not self.current_image_path:
            return
        if self.ai_engine is None:
            self.log("AI Engine is still loading. Please wait...")
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

            # Write a graded PNG next to the input image
            base, _ext = os.path.splitext(self.current_image_path)
            graded_path = base + "_graded.png"
            try:
                self.current_graded_image_path = apply_adjustments_to_image(
                    self.current_image_path,
                    self.current_adjustments,
                    graded_path,
                )
            except Exception as e:
                self.current_graded_image_path = None
                result["graded_png_error"] = str(e)
            
            display_text = "Analysis Complete!\n\nExtracted Parameters:\n"
            display_text += json.dumps(result, indent=2)
            if self.current_graded_image_path:
                display_text += f"\n\nGraded PNG saved to:\n{self.current_graded_image_path}"
            
            # Update UI from main thread
            self.after(0, self.log, display_text)
            self.after(0, lambda: self._update_sliders_from_adjustments(self.current_adjustments))
            self.after(0, lambda: self.btn_export.configure(state="normal"))
            self.after(0, lambda: self.btn_upload.configure(state="normal"))
            self.after(0, lambda: self.btn_analyze.configure(state="normal"))

            # Swap preview to the graded image if possible
            if self.current_graded_image_path:
                self.after(0, lambda: self._display_image(self.current_graded_image_path))
            
        except Exception as e:
            self.after(0, self.log, f"Analysis Error: {e}")
            self.after(0, lambda: self.btn_upload.configure(state="normal"))
            self.after(0, lambda: self.btn_analyze.configure(state="normal"))

    def _display_image(self, file_path: str):
        try:
            img = Image.open(file_path)
            img.thumbnail((500, 500))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            if _HAS_CUSTOMTKINTER:
                self.image_label.configure(image=ctk_img, text="")
                self.image_label.image = ctk_img
            else:
                if ctk_img.image is not None:
                    self.image_label.configure(image=ctk_img.image, text="")
                    self.image_label.image = ctk_img.image
                else:
                    self.image_label.configure(image="", text=f"Saved:\n{os.path.basename(file_path)}")
        except Exception as e:
            self.log(f"Error displaying image: {e}")

    def export_lut(self):
        # Read final slider values to ensure any custom tweaks are included
        adj = {}
        for k in self.slider_ranges.keys():
            adj[k] = self.slider_vars[k].get()
        if "rgb_gain" in self.current_adjustments:
            adj["rgb_gain"] = self.current_adjustments["rgb_gain"]
        else:
            adj["rgb_gain"] = [1.0, 1.0, 1.0]
            
        self.current_adjustments = adj
        
        output_path = self._pick_lut_save_path()
        if output_path:
            try:
                generate_cube_lut(self.current_adjustments, output_path)
                self.log(f"Successfully exported 33x33x33 LUT to:\n{output_path}\n\nReady for use in DaVinci Resolve or Premiere Pro.")
            except Exception as e:
                self.log(f"Error generating LUT: {e}")


if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
