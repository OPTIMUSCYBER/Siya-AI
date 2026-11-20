import yaml
import sounddevice as sd
import numpy as np
import time
import os
from pathlib import Path
from openwakeword.model import Model

# Directory where THIS script lives
_SCRIPT_DIR = Path(__file__).resolve().parent

def _ensure_pretrained_models():
    """Download openwakeword's pretrained/embedding/melspec models if missing."""
    try:
        from openwakeword.utils import download_models
        print("[WakeWord] Checking for pretrained openwakeword models...")
        download_models()
        print("[WakeWord] Pretrained models ready.")
    except Exception as e:
        print(f"[WakeWord] Warning: could not download pretrained models: {e}")

class WakeWordListener:
    def __init__(self, config_path="config.yaml"):
        config_file = _SCRIPT_DIR / config_path
        with open(config_file, "r") as f:
            self.config = yaml.safe_load(f)
            
        ww_config = self.config.get("wake_word", {})
        raw_model = ww_config.get("model_path", "models/hey_siya.onnx")
        self.threshold = ww_config.get("threshold", 0.5)

        # Resolve relative to script dir
        self.model_path = str(_SCRIPT_DIR / raw_model)
        
        audio_config = self.config.get("audio", {})
        # openwakeword requires 16000Hz
        self.sample_rate = 16000 
        self.chunk_size = 1280 # 80ms chunks
        
        self.is_listening = False
        self.stream = None
        
        # Initialize model
        print("Initializing wake word model...")
        if os.path.exists(self.model_path):
            print(f"[WakeWord] Loading custom model: {self.model_path}")
            self.model = Model(wakeword_models=[self.model_path], inference_framework="onnx")
            self.model_name = os.path.splitext(os.path.basename(self.model_path))[0]
        else:
            print(f"[WakeWord] Custom model not found at {self.model_path}")
            print("[WakeWord] Using pretrained 'hey_jarvis' for testing.")
            # Ensure pretrained model files are downloaded first
            _ensure_pretrained_models()
            self.model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
            self.model_name = "hey_jarvis"
        print(f"Wake word model loaded: {self.model_name}")

    def start(self, callback):
        """Starts listening in a blocking loop (should be run in a thread)."""
        self.is_listening = True
        print(f"Listening for wake word ({self.model_name})...")
        
        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='int16', blocksize=self.chunk_size) as stream:
                while self.is_listening:
                    chunk, _ = stream.read(self.chunk_size)
                    audio_data = np.frombuffer(chunk, dtype=np.int16)
                    
                    # Feed to model
                    prediction = self.model.predict(audio_data)
                    
                    # prediction is a dict like {'hey_jarvis': 0.8}
                    # We check if any score > threshold
                    for model_name, score in prediction.items():
                        if score > self.threshold:
                            print(f"\nWake word detected! Score: {score}")
                            # Reset model state to avoid continuous triggers
                            self.model.reset()
                            
                            # Call the callback
                            callback()
                            break # Go back to listening after callback finishes
                            
        except Exception as e:
            print(f"Error in wake word listener: {e}")

    def stop(self):
        self.is_listening = False

if __name__ == "__main__":
    def on_wake():
        print("Callback triggered! (Waiting 2 seconds before resuming...)")
        time.sleep(2)
        
    listener = WakeWordListener()
    try:
        listener.start(on_wake)
    except KeyboardInterrupt:
        print("Stopping...")
        listener.stop()
