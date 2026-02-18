import os
import sys
import queue
import json
import threading
import zipfile
import urllib.request
import shutil
import tkinter as tk
from tkinter import font, colorchooser, ttk
from typing import List, Optional, Callable, Dict, Any, Tuple

import sounddevice as sd
import vosk
import numpy as np

# --- Configuration & Constants ---
MODEL_VERSION = "vosk-model-small-en-us-0.15"
MODEL_URL = f"https://alphacephei.com/vosk/models/{MODEL_VERSION}.zip"
MODEL_PATH = "model"
SAMPLE_RATE = 16000
BLOCK_SIZE = 8000
MAX_HISTORY = 10

# --- Helper Classes ---

class AudioTranscriber:
    """
    Handles audio capture and speech recognition using Vosk and sounddevice.
    Runs recognition in a separate thread.
    """
    def __init__(self, model_path: str, on_text_callback: Callable[[str, bool], None]):
        self.model_path = model_path
        self.on_text_callback = on_text_callback
        self.running = False
        self.audio_queue: queue.Queue = queue.Queue()
        self.thread: Optional[threading.Thread] = None

    def _download_model(self) -> None:
        """Downloads and extracts the Vosk model if missing."""
        if not os.path.exists(self.model_path):
            print(f"Model not found. Downloading {MODEL_VERSION}...", file=sys.stderr)
            try:
                file_name = f"{MODEL_VERSION}.zip"
                with urllib.request.urlopen(MODEL_URL) as response, open(file_name, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)
                
                print("Extracting model...", file=sys.stderr)
                with zipfile.ZipFile(file_name, 'r') as zip_ref:
                    zip_ref.extractall(".")
                
                os.rename(MODEL_VERSION, self.model_path)
                os.remove(file_name)
                print("Model downloaded and extracted.", file=sys.stderr)
            except Exception as e:
                print(f"Error downloading model: {e}", file=sys.stderr)
                # In a real app, might want to signal error to UI
                sys.exit(1)

    def _audio_callback(self, indata, frames, time, status):
        """Callback for sounddevice input stream."""
        if status:
            print(status, file=sys.stderr)
        self.audio_queue.put(bytes(indata))

    def _recognition_loop(self) -> None:
        """Main recognition loop running in a separate thread."""
        self._download_model()

        try:
            model = vosk.Model(self.model_path)
        except Exception as e:
            print(f"Failed to load model: {e}", file=sys.stderr)
            self.on_text_callback(f"Error loading model: {e}", True)
            return

        rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)

        try:
            with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE, dtype='int16',
                                   channels=1, callback=self._audio_callback):
                print("Listening...", file=sys.stderr)
                while self.running:
                    try:
                        data = self.audio_queue.get(timeout=1.0)
                        if rec.AcceptWaveform(data):
                            result = json.loads(rec.Result())
                            text = result.get("text", "")
                            if text:
                                self.on_text_callback(text, True)
                        else:
                            partial = json.loads(rec.PartialResult())
                            text = partial.get("partial", "")
                            if text:
                                self.on_text_callback(text, False)
                    except queue.Empty:
                        continue
        except Exception as e:
            print(f"Audio stream error: {e}", file=sys.stderr)
            self.on_text_callback(f"Audio Error: {e}", True)

    def start(self) -> None:
        """Starts the recognition thread."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._recognition_loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        """Stops the recognition loop."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)


class SettingsDialog(tk.Toplevel):
    """
    Modal dialog for user settings configuration.
    """
    def __init__(self, parent: tk.Tk, current_settings: Dict[str, Any], callback: Callable[[Dict[str, Any]], None]):
        super().__init__(parent)
        self.callback = callback
        self.title("Settings")
        self.geometry("300x450")
        self.transient(parent)
        self.grab_set()

        # Vars
        self.font_family = tk.StringVar(value=current_settings.get("font_family", "Helvetica"))
        self.font_size = tk.IntVar(value=current_settings.get("font_size", 24))
        self.text_color = current_settings.get("text_color", "#FFFFFF")
        self.position = tk.StringVar(value=current_settings.get("position", "floating"))
        self.fullscreen = tk.BooleanVar(value=current_settings.get("fullscreen", False))

        self._build_ui()

    def _build_ui(self):
        pad_opts = {'pady': 5}
        
        tk.Label(self, text="Font Family:").pack(**pad_opts)
        ttk.Combobox(self, textvariable=self.font_family, values=font.families(), state="readonly").pack()

        tk.Label(self, text="Font Size:").pack(**pad_opts)
        tk.Spinbox(self, from_=8, to=150, textvariable=self.font_size).pack()

        tk.Button(self, text="Select Text Color", command=self._choose_color).pack(pady=10)

        tk.Label(self, text="Dock Position:").pack(**pad_opts)
        tk.Radiobutton(self, text="Floating", variable=self.position, value="floating").pack()
        tk.Radiobutton(self, text="Dock Top", variable=self.position, value="top").pack()
        tk.Radiobutton(self, text="Dock Bottom", variable=self.position, value="bottom").pack()

        tk.Checkbutton(self, text="Full Screen", variable=self.fullscreen).pack(pady=10)

        tk.Button(self, text="Apply", command=self._apply).pack(side='left', padx=20, pady=20)
        tk.Button(self, text="Close", command=self.destroy).pack(side='right', padx=20, pady=20)

    def _choose_color(self):
        color = colorchooser.askcolor(title="Choose Text Color", color=self.text_color)[1]
        if color:
            self.text_color = color

    def _apply(self):
        settings = {
            "font_family": self.font_family.get(),
            "font_size": self.font_size.get(),
            "text_color": self.text_color,
            "position": self.position.get(),
            "fullscreen": self.fullscreen.get()
        }
        self.callback(settings)


class CaptionWindow:
    """
    Main GUI controller using Tkinter.
    """
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Local Closed Captions")
        self.root.geometry("800x200")
        self.root.attributes("-topmost", True)
        self.root.configure(bg='black')

        # Data State
        self.settings = {
            "font_family": "Helvetica",
            "font_size": 24,
            "text_color": "#FFFFFF",
            "position": "floating",
            "fullscreen": False
        }
        self.history: List[str] = [""] * MAX_HISTORY # Fixed size buffer
        self.color_cache: List[str] = []
        
        # UI Component Pools
        self.history_labels: List[tk.Label] = []
        self.partial_label: Optional[tk.Label] = None
        self.content_frame: Optional[tk.Frame] = None

        self._init_ui()
        self._update_color_cache()
        self._apply_visual_settings()
        
        # Start Transcriber
        self.transcriber = AudioTranscriber(MODEL_PATH, self.on_text_update)
        self.transcriber.start()

        # Handle Cleanup
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _init_ui(self):
        """Initializes the fixed pool of labels."""
        # Top controls
        controls_frame = tk.Frame(self.root, bg='black')
        controls_frame.pack(side='top', anchor='ne', fill='x')
        
        btn = tk.Button(controls_frame, text="⚙ Settings", command=self.open_settings, 
                        bg='#333333', fg='white', font=("Arial", 10), relief='flat')
        btn.pack(side='right', padx=5, pady=5)

        # Content Area
        self.content_frame = tk.Frame(self.root, bg='black')
        self.content_frame.pack(expand=True, fill='both', padx=20, pady=10)

        # 1. Partial Result Label (Always at the very bottom)
        self.partial_label = tk.Label(
            self.content_frame, text="", bg='black', justify='left', anchor='sw'
        )
        self.partial_label.pack(side='bottom', anchor='sw', fill='x', pady=(0, 5))

        # 2. History Labels (Stacked above partial)
        # We want the NEWEST history nearest to the partial label.
        # Pack side='bottom' stacks them upwards.
        # So first packed = Bottom-most history (Newest)
        # Last packed = Top-most history (Oldest)
        for _ in range(MAX_HISTORY):
            lbl = tk.Label(
                self.content_frame, text="", bg='black', justify='left', anchor='sw'
            )
            lbl.pack(side='bottom', anchor='sw', fill='x')
            self.history_labels.append(lbl)

    def _update_color_cache(self):
        """
        Pre-calculates fading colors based on current text_color.
        Index 0 = Newest (100% opacity)
        Index MAX = Oldest (Low opacity)
        """
        base_color = self.settings["text_color"]
        self.color_cache = []

        # Simple hex passthrough if named color, else calc RGB
        if not base_color.startswith("#"):
             # Fallback/simplification: Just use the same color for all if not hex
             # Proper implementation would map names to hex
             self.color_cache = [base_color] * MAX_HISTORY
             return

        r = int(base_color[1:3], 16)
        g = int(base_color[3:5], 16)
        b = int(base_color[5:7], 16)

        for i in range(MAX_HISTORY):
            # i=0 is newest (Factor 1.0)
            # i=MAX is oldest
            factor = 1.0 - (i / (MAX_HISTORY * 1.5))
            factor = max(0.2, factor)
            
            nr = int(r * factor)
            ng = int(g * factor)
            nb = int(b * factor)
            self.color_cache.append(f"#{nr:02x}{ng:02x}{nb:02x}")

    def _apply_visual_settings(self):
        """Updates fonts, geometry, and static properties of pooled labels."""
        font_spec = (self.settings["font_family"], self.settings["font_size"])
        color = self.settings["text_color"]
        
        # Update Partial Label
        self.partial_label.config(font=font_spec, fg=color)

        # Update History Labels
        # We map cache index i (0=Newest) to label index i (0=Bottom-most/Newest)
        for i, lbl in enumerate(self.history_labels):
            lbl.config(font=font_spec, fg=self.color_cache[i])

        # Window Geometry/Fullscreen
        is_fs = self.settings["fullscreen"]
        self.root.attributes("-fullscreen", is_fs)
        
        screen_width = self.root.winfo_screenwidth()
        window_width = screen_width # Default to screen width for now as geometry usually spans width
        
        if not is_fs:
            pos = self.settings["position"]
            sh = self.root.winfo_screenheight()
            
            if pos == "top":
                self.root.geometry(f"{screen_width}x250+0+0")
            elif pos == "bottom":
                taskbar_offset = 40 # Approx
                self.root.geometry(f"{screen_width}x250+0+{sh - 250 - taskbar_offset}")
            else:
                # Floating default or keep current - if floating, calculating wrap length is trickier without binding
                # For now, assume a reasonable max width or update if we were to track geometry
                window_width = self.root.winfo_width() # Might be 1 if not rendered yet, rely on screen width for safe wrapping or fixed width
                if window_width <= 1: window_width = 800 # Default init width
                pass
        
        # Calculate wrap length (window width - padding)
        wrap_len = window_width - 50
        
        # Update Partial Label
        self.partial_label.config(font=font_spec, fg=color, wraplength=wrap_len)

        # Update History Labels
        # We map cache index i (0=Newest) to label index i (0=Bottom-most/Newest)
        for i, lbl in enumerate(self.history_labels):
            lbl.config(font=font_spec, fg=self.color_cache[i], wraplength=wrap_len)

    def open_settings(self):
        SettingsDialog(self.root, self.settings, self.on_settings_changed)

    def on_settings_changed(self, new_settings: Dict[str, Any]):
        self.settings = new_settings
        self._update_color_cache()
        self._apply_visual_settings()

    def on_text_update(self, text: str, is_final: bool):
        """Callback from audio thread. Schedules GUI update on main thread."""
        self.root.after(0, self._process_text_update, text, is_final)

    def _process_text_update(self, text: str, is_final: bool):
        """Updates text content of labels. No widget creation/destruction."""
        if is_final:
            # Shift History
            # self.history is [Newest, ..., Oldest] conceptually for data?
            # Actually, let's keep it simple: insert at 0 (Newest)
            self.history.insert(0, text)
            if len(self.history) > MAX_HISTORY:
                self.history.pop() # Remove oldest
            
            # Update Pooled Labels
            # Label 0 is Bottom (Newest) -> maps to history[0]
            for i, lbl in enumerate(self.history_labels):
                if i < len(self.history):
                    lbl.config(text=self.history[i])
                else:
                    lbl.config(text="")
            
            self.partial_label.config(text="")
        else:
            self.partial_label.config(text=text)

    def on_close(self):
        self.transcriber.stop()
        self.root.destroy()


# --- Main Entry Point ---

if __name__ == "__main__":
    if sys.platform == 'win32':
        # Fix for high-DPI scaling on Windows
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass

    root = tk.Tk()
    app = CaptionWindow(root)
    root.mainloop()
