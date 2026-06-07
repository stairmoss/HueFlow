import os
import sys
import tkinter as tk
from tkinter import filedialog
import subprocess
import threading
import webbrowser

# CustomTkinter is preferred, but fall back to standard Tkinter
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

    ctk = _CTKCompat()  # type: ignore

# Import the core engine and web server
from core.inference import ColorGraderInference
from ui.web_server import WebServerRunner
import ui.web_server


class MainWindow(ctk.CTk):
    def __init__(self, server_runner, manager):
        super().__init__()
        
        self.server_runner = server_runner
        self.manager = manager
        
        # Bind server runner window reference to this Tkinter instance for main thread polling
        self.server_runner.main_window = self
        
        self.title("HueFlow AI Server Manager")
        self.geometry("520x340")
        self.resizable(False, False)
        
        if _HAS_CUSTOMTKINTER:
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("blue")
            
        self.ai_engine = None
        self.current_image_path = None
        self.current_graded_image_path = None
        self.current_adjustments = {}

        self._setup_ui()
        
        # Start queue checker for thread safety
        self.after(100, self.check_queue)
        
        # Check engine load status
        self.after(200, self._check_engine_loaded)
        
        # Auto-open browser
        self.after(1000, self.open_browser)

    def check_queue(self):
        """Thread-safe runner to handle GUI actions requested by HTTP server threads."""
        try:
            while True:
                task_fn, callback_fn = self.server_runner.cmd_queue.get_nowait()
                res = task_fn()
                callback_fn(res)
        except Exception:
            pass
        self.after(100, self.check_queue)

    def _setup_ui(self):
        if _HAS_CUSTOMTKINTER:
            self.configure(fg_color="#0b0f19")
            
            main_frame = ctk.CTkFrame(self, fg_color="#111827", corner_radius=15)
            main_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Header
            lbl_title = ctk.CTkLabel(
                main_frame,
                text="HueFlow AI Server",
                font=("Inter", 20, "bold"),
                text_color="#c084fc"
            )
            lbl_title.pack(pady=(20, 5))
            
            self.lbl_status = ctk.CTkLabel(
                main_frame,
                text="Initializing AI Engine...",
                font=("Inter", 12),
                text_color="#f59e0b"
            )
            self.lbl_status.pack(pady=5)
            
            # Info block
            info_frame = ctk.CTkFrame(main_frame, fg_color="#1f2937", corner_radius=10)
            info_frame.pack(fill="x", padx=30, pady=15)
            
            self.lbl_url = ctk.CTkLabel(
                info_frame,
                text=f"Web UI: http://127.0.0.1:{self.server_runner.port}",
                font=("Fira Code", 11),
                text_color="#10b981"
            )
            self.lbl_url.pack(pady=10)
            
            # Open Studio Button
            self.btn_open = ctk.CTkButton(
                main_frame,
                text="Open Studio in Browser",
                font=("Inter", 13, "bold"),
                fg_color="#8b5cf6",
                hover_color="#7c3aed",
                height=40,
                corner_radius=10,
                command=self.open_browser
            )
            self.btn_open.pack(pady=(5, 10))
            
            # Footer copyright
            lbl_copy = ctk.CTkLabel(
                main_frame,
                text="AirLLM 6GB Optimization Active",
                font=("Inter", 9),
                text_color="#6b7280"
            )
            lbl_copy.pack(pady=(0, 10))
            return

        # Fallback Standard Tkinter UI
        self.configure(bg="#0b0f19")
        frame = tk.Frame(self, bg="#111827", bd=0)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        lbl_title = tk.Label(
            frame,
            text="HueFlow AI Server",
            font=("Arial", 18, "bold"),
            fg="#c084fc",
            bg="#111827"
        )
        lbl_title.pack(pady=(20, 5))

        self.lbl_status = tk.Label(
            frame,
            text="Initializing AI Engine...",
            font=("Arial", 11),
            fg="#f59e0b",
            bg="#111827"
        )
        self.lbl_status.pack(pady=5)

        info_frame = tk.Frame(frame, bg="#1f2937")
        info_frame.pack(fill="x", padx=30, pady=15)

        self.lbl_url = tk.Label(
            info_frame,
            text=f"Web UI: http://127.0.0.1:{self.server_runner.port}",
            font=("Courier", 10),
            fg="#10b981",
            bg="#1f2937"
        )
        self.lbl_url.pack(pady=10)

        self.btn_open = tk.Button(
            frame,
            text="Open Studio in Browser",
            font=("Arial", 12, "bold"),
            fg="white",
            bg="#8b5cf6",
            activebackground="#7c3aed",
            activeforeground="white",
            relief="flat",
            command=self.open_browser
        )
        self.btn_open.pack(pady=(5, 10), ipadx=10, ipady=5)

    def _check_engine_loaded(self):
        if self.manager.ai_engine is not None:
            self.ai_engine = self.manager.ai_engine
            self._update_status("Server Status: AI Engine Ready", "#10b981")
        else:
            self.after(500, self._check_engine_loaded)

    def _update_status(self, text, color):
        def _update():
            if _HAS_CUSTOMTKINTER:
                self.lbl_status.configure(text=text, text_color=color)
            else:
                self.lbl_status.configure(text=text, fg=color)
        self.after(0, _update)

    def open_browser(self):
        url = f"http://127.0.0.1:{self.server_runner.port}"
        webbrowser.open(url)

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


class ServerManager:
    def __init__(self):
        self.ai_engine = None
        self.current_image_path = None
        self.current_graded_image_path = None
        self.current_adjustments = {}


def launch_app():
    print("Starting HueFlow Color Science Server...")
    
    # 1. Instantiate shared manager to hold states
    manager = ServerManager()
    
    # 2. Start Python background Web Server
    runner = WebServerRunner(manager)
    runner.start()
    
    # 3. Load VLM inference model in background thread
    def load_engine():
        try:
            print("Loading model. Please wait...")
            manager.ai_engine = ColorGraderInference()
            print("AI Engine successfully initialized!")
        except Exception as e:
            print(f"Error loading AI Engine: {e}")
            
    threading.Thread(target=load_engine, daemon=True).start()
    
    # 4. Attempt native pywebview frame launch
    url = f"http://127.0.0.1:{runner.port}"
    try:
        import webview
        print("Initializing native desktop webview window...")
        window = webview.create_window(
            "HueFlow AI Studio", 
            url, 
            width=1200, 
            height=800, 
            min_size=(1000, 650)
        )
        ui.web_server._WEBVIEW_WINDOW = window
        webview.start()
        print("Studio window closed. Shutting down server.")
        sys.exit(0)
    except Exception as e:
        print(f"Native webview unavailable: {e}")
        print("Falling back to server control manager + web browser...")
        
        # Start GUI launcher fallback loop
        app = MainWindow(runner, manager)
        app.mainloop()
