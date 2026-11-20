import yaml
import sounddevice as sd
import numpy as np
import time
from pathlib import Path
from faster_whisper import WhisperModel

# Directory where THIS script lives
_SCRIPT_DIR = Path(__file__).resolve().parent

class STT:
    def __init__(self, config_path="config.yaml"):
        config_file = _SCRIPT_DIR / config_path
        with open(config_file, "r") as f:
            self.config = yaml.safe_load(f)
            
        stt_config = self.config.get("stt", {})
        self.model_size = stt_config.get("model_size", "small")
        self.device = stt_config.get("device", "cpu")
        self.compute_type = stt_config.get("compute_type", "int8")
        
        audio_config = self.config.get("audio", {})
        self.sample_rate = audio_config.get("sample_rate", 16000)
        self.silence_cutoff = audio_config.get("record_seconds_silence_cutoff", 1.5)
        self.max_record = audio_config.get("max_record_seconds", 20)
        
        print(f"Loading Whisper model ({self.model_size})...")
        self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
        print("Whisper model loaded.")

    def listen_and_transcribe(self):
        print("Listening...")
        audio_data = self._record_until_silence()
        if audio_data is None or len(audio_data) == 0:
            return ""
            
        print("Transcribing...")
        # faster-whisper expects a float32 numpy array for audio if passed directly
        segments, info = self.model.transcribe(audio_data, beam_size=5, language=None)
        print(f"Detected language '{info.language}' with probability {info.language_probability}")
        
        text = "".join([segment.text for segment in segments])
        return text.strip()

    def _record_until_silence(self):
        # We will record in chunks and check RMS energy
        chunk_duration = 0.5  # seconds
        chunk_samples = int(self.sample_rate * chunk_duration)
        
        audio_buffer = []
        silence_start_time = None
        start_time = time.time()
        
        # A simple empirical threshold for silence. May need adjustment.
        # Often RMS < 0.01 is quite silent.
        silence_threshold = 0.015 
        
        # A flag to know if we actually heard something before waiting for silence
        has_spoken = False
        
        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='float32') as stream:
                while True:
                    # Read chunk
                    chunk, overflowed = stream.read(chunk_samples)
                    chunk = chunk.flatten()
                    audio_buffer.append(chunk)
                    
                    rms = np.sqrt(np.mean(chunk**2))
                    
                    if rms > silence_threshold:
                        has_spoken = True
                        silence_start_time = None # Reset silence timer
                    else:
                        if has_spoken:
                            if silence_start_time is None:
                                silence_start_time = time.time()
                            elif time.time() - silence_start_time > self.silence_cutoff:
                                print("Silence detected, stopping recording.")
                                break
                                
                    # Hard max cutoff
                    if time.time() - start_time > self.max_record:
                        print("Max recording time reached.")
                        break
                        
        except Exception as e:
            print(f"Error recording audio: {e}")
            return None
            
        return np.concatenate(audio_buffer)

if __name__ == "__main__":
    stt = STT()
    text = stt.listen_and_transcribe()
    print(f"Transcription: {text}")
