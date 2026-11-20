import threading
import time
import yaml
import pystray
from PIL import Image, ImageDraw
import sys
import os
from pathlib import Path

# Directory where THIS script lives — all relative paths resolve from here
_SCRIPT_DIR = Path(__file__).resolve().parent

from wake_word import WakeWordListener
from stt import STT
from brain import Brain
from tts import TTS

class SiyaApp:
    def __init__(self):
        self.state = "idle" # idle, listening, thinking, speaking, muted
        self.muted = False
        self.running = True
        
        # Load config
        config_file = _SCRIPT_DIR / "config.yaml"
        with open(config_file, "r") as f:
            self.config = yaml.safe_load(f)
            
        print("Initializing modules...")
        self.tts = TTS()
        self.brain = Brain()
        self.stt = STT()
        self.ww = WakeWordListener()
        
        # Setup tray icon
        self.icon = None
        self._setup_tray()
        
    def _create_image(self, color):
        # Generate an image for the tray icon based on state color
        image = Image.new('RGB', (64, 64), color=(0, 0, 0))
        dc = ImageDraw.Draw(image)
        dc.ellipse((8, 8, 56, 56), fill=color)
        return image
        
    def _get_icon_image(self):
        if self.muted:
            return self._create_image('gray')
        elif self.state == "idle":
            return self._create_image('green')
        elif self.state == "listening":
            return self._create_image('blue')
        elif self.state == "thinking":
            return self._create_image('orange')
        elif self.state == "speaking":
            return self._create_image('purple')
        return self._create_image('green')

    def _update_icon(self):
        if self.icon:
            self.icon.icon = self._get_icon_image()

    def set_state(self, new_state):
        self.state = new_state
        self._update_icon()
        
    def toggle_mute(self, icon, item):
        self.muted = not self.muted
        self._update_icon()
        if self.muted:
            print("Microphone muted.")
        else:
            print("Microphone unmuted.")
            
    def quit_app(self, icon, item):
        print("Quitting Siya...")
        self.running = False
        self.ww.stop()
        icon.stop()
        # forcefully exit to kill any hanging threads
        os._exit(0)

    def _setup_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem('Mute/Unmute', self.toggle_mute, checked=lambda item: self.muted),
            pystray.MenuItem('Quit', self.quit_app)
        )
        self.icon = pystray.Icon("Siya", self._get_icon_image(), "Siya PC Companion", menu)

    def process_interaction(self):
        """The main interaction loop after wake word is detected."""
        if self.muted:
            return
            
        self.set_state("listening")
        try:
            # 1. Listen and transcribe
            user_text = self.stt.listen_and_transcribe()
            
            if not user_text:
                print("No speech detected.")
                self.set_state("idle")
                return
                
            print(f"User: {user_text}")
            
            # 2. Think
            self.set_state("thinking")
            reply = self.brain.chat(user_text)
            print(f"Siya: {reply}")
            
            # 3. Speak
            self.set_state("speaking")
            self.tts.speak(reply)
            
        except Exception as e:
            print(f"Error during interaction: {e}")
        finally:
            self.set_state("idle")

    def run(self):
        # Optionally greet on startup
        if self.config.get("user", {}).get("greet_on_startup", False):
            name = self.config.get("user", {}).get("name", "there")
            self.set_state("speaking")
            self.tts.speak(f"Welcome back, {name}. I'm ready.")
            self.set_state("idle")
            
        # Start wake word listener in background
        ww_thread = threading.Thread(target=self.ww.start, args=(self.process_interaction,), daemon=True)
        ww_thread.start()
        
        # Run tray icon (blocking)
        self.icon.run()

if __name__ == "__main__":
    try:
        app = SiyaApp()
        app.run()
    except Exception as e:
        print(f"Application error: {e}")
