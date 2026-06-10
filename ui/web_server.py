import os
import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import queue

# Global references
_SERVER_RUNNER = None
_WEBVIEW_WINDOW = None

class WebServerRunner:
    def __init__(self, main_window):
        global _SERVER_RUNNER
        self.main_window = main_window
        self.cmd_queue = queue.Queue()
        self.server = None
        self.port = 5000
        _SERVER_RUNNER = self

    def start(self):
        def run_server():
            handler = HueFlowHTTPHandler
            # Try ports in case 5000 is occupied
            for p in range(5000, 5020):
                try:
                    self.port = p
                    self.server = HTTPServer(('127.0.0.1', self.port), handler)
                    print(f"HueFlow Web Server running on http://127.0.0.1:{self.port}")
                    self.server.serve_forever()
                    break
                except Exception as e:
                    print(f"Port {p} failed: {e}")
                    
        t = threading.Thread(target=run_server, daemon=True)
        t.start()

    def run_on_main_thread(self, fn):
        """Runs a function on the main thread and returns the result using a blocking queue."""
        res_queue = queue.Queue()
        self.cmd_queue.put((fn, lambda res: res_queue.put(res)))
        return res_queue.get()


class HueFlowHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            try:
                html_path = os.path.join(os.path.dirname(__file__), "index.html")
                with open(html_path, "r", encoding="utf-8") as f:
                    self.wfile.write(f.read().encode("utf-8"))
            except Exception as e:
                self.wfile.write(f"Error loading index.html: {e}".encode("utf-8"))
            return

        elif path == "/static/load":
            image_path = query.get("path", [""])[0]
            if not image_path or not os.path.exists(image_path):
                self.send_response(404)
                self.end_headers()
                return

            self.send_response(200)
            if image_path.lower().endswith(".png"):
                self.send_header("Content-Type", "image/png")
            elif image_path.lower().endswith((".jpg", ".jpeg")):
                self.send_header("Content-Type", "image/jpeg")
            else:
                self.send_header("Content-Type", "image/octet-stream")
            self.end_headers()

            try:
                with open(image_path, "rb") as f:
                    self.wfile.write(f.read())
            except Exception as e:
                print(f"Error loading image static asset: {e}")
            return

        elif path == "/api/upload":
            runner = _SERVER_RUNNER
            global _WEBVIEW_WINDOW
            
            if _WEBVIEW_WINDOW is not None:
                try:
                    import webview
                    res = _WEBVIEW_WINDOW.create_file_dialog(
                        webview.OPEN_DIALOG, 
                        file_types=('Image Files (*.jpg;*.jpeg;*.png;*.webp)',)
                    )
                    file_path = res[0] if res else None
                except Exception as e:
                    print(f"Webview dialog error: {e}")
                    file_path = None
            elif runner.main_window is not None:
                file_path = runner.run_on_main_thread(runner.main_window._pick_image_path)
            else:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "error",
                    "message": "Native dialog unavailable in headless mode. Please drag & drop or upload your image directly."
                }).encode("utf-8"))
                return
            
            if file_path:
                base, _ext = os.path.splitext(file_path)
                graded_path = base + "_graded.png"
                
                runner.main_window.current_image_path = file_path
                runner.main_window.current_graded_image_path = graded_path
                
                try:
                    from PIL import Image
                    img = Image.open(file_path)
                    img.save(graded_path)
                except Exception as e:
                    print(f"Failed to create start graded image: {e}")

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "success",
                    "original_path": file_path,
                    "graded_path": graded_path
                }).encode("utf-8"))
            else:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "cancel",
                    "message": "User canceled file selection"
                }).encode("utf-8"))
            return

        elif path == "/api/analyze":
            runner = _SERVER_RUNNER
            image_path = query.get("path", [""])[0]
            
            if not image_path or not os.path.exists(image_path):
                self.send_response(400)
                self.end_headers()
                return

            if runner.main_window.ai_engine is None:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "error",
                    "message": "AI Engine is still loading"
                }).encode("utf-8"))
                return

            try:
                result = runner.main_window.ai_engine.analyze_image(image_path)
                runner.main_window.current_adjustments = result.get("adjustments", {})
                
                from utils.image_grade import apply_adjustments_to_image
                base, _ext = os.path.splitext(image_path)
                graded_path = base + "_graded.png"
                
                apply_adjustments_to_image(image_path, runner.main_window.current_adjustments, graded_path)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "success",
                    "result": result
                }).encode("utf-8"))
            except Exception as e:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "error",
                    "message": str(e)
                }).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        content_length = int(self.headers.get('Content-Length', 0))
        
        if path == "/api/upload_web":
            body_bytes = self.rfile.read(content_length)
            uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
            os.makedirs(uploads_dir, exist_ok=True)
            
            filename = self.headers.get('X-File-Name', 'uploaded_image.png')
            file_path = os.path.join(uploads_dir, filename)
            
            with open(file_path, 'wb') as f:
                f.write(body_bytes)
                
            base, _ext = os.path.splitext(file_path)
            graded_path = base + "_graded.png"
            
            runner = _SERVER_RUNNER
            runner.main_window.current_image_path = file_path
            runner.main_window.current_graded_image_path = graded_path
            
            try:
                from PIL import Image
                img = Image.open(file_path)
                img.save(graded_path)
            except Exception as e:
                print(f"Failed to create start graded image: {e}")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success",
                "original_path": file_path,
                "graded_path": graded_path
            }).encode("utf-8"))
            return

        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            params = json.loads(body)
        except Exception:
            params = {}

        if path == "/api/grade":
            original_path = params.get("original_path")
            graded_path = params.get("graded_path")
            adjustments = params.get("adjustments", {})

            if not original_path or not graded_path:
                self.send_response(400)
                self.end_headers()
                return

            try:
                from utils.image_grade import apply_adjustments_to_image
                apply_adjustments_to_image(original_path, adjustments, graded_path)
                
                _SERVER_RUNNER.main_window.current_adjustments = adjustments
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                print(f"Error grading image in server: {e}")
            return

        elif path == "/api/chat":
            prompt = params.get("prompt", "")
            current_adjustments = params.get("current_adjustments", {})
            runner = _SERVER_RUNNER
            engine = runner.main_window.ai_engine
            
            if engine is None:
                from core.inference import ColorGraderInference
                engine = ColorGraderInference()
                
            try:
                result = engine.chat_grade_image(current_adjustments, prompt)
                original_path = runner.main_window.current_image_path
                graded_path = runner.main_window.current_graded_image_path
                if original_path and graded_path:
                    from utils.image_grade import apply_adjustments_to_image
                    apply_adjustments_to_image(original_path, result.get("adjustments", {}), graded_path)
                    runner.main_window.current_adjustments = result.get("adjustments", {})

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "success",
                    "result": result
                }).encode("utf-8"))
            except Exception as e:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "error",
                    "message": str(e)
                }).encode("utf-8"))
            return

        elif path == "/api/export":
            adjustments = params.get("adjustments", {})
            runner = _SERVER_RUNNER
            global _WEBVIEW_WINDOW
            
            if _WEBVIEW_WINDOW is not None:
                try:
                    import webview
                    res = _WEBVIEW_WINDOW.create_file_dialog(
                        webview.SAVE_DIALOG, 
                        save_filename='HueFlow_Grade.cube', 
                        file_types=('CUBE files (*.cube)',)
                    )
                    lut_path = res if res else None
                except Exception as e:
                    print(f"Webview save dialog error: {e}")
                    lut_path = None
            elif runner.main_window is not None:
                lut_path = runner.run_on_main_thread(runner.main_window._pick_lut_save_path)
            else:
                os.makedirs(os.path.join(os.path.dirname(__file__), "..", "uploads"), exist_ok=True)
                lut_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads", "HueFlow_Grade.cube"))
            
            if lut_path:
                try:
                    from utils.lut_gen import generate_cube_lut
                    generate_cube_lut(adjustments, lut_path)
                    
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "status": "success",
                        "path": lut_path
                    }).encode("utf-8"))
                except Exception as e:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "status": "error",
                        "message": str(e)
                    }).encode("utf-8"))
            else:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "cancel",
                    "message": "User canceled save path selection"
                }).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()
