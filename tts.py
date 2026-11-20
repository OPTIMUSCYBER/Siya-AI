import yaml
import wave
import io
import sounddevice as sd
import numpy as np
import os
import re
import librosa
from pathlib import Path

# Directory where THIS script lives — all relative paths resolve from here
_SCRIPT_DIR = Path(__file__).resolve().parent

class TTS:
    def __init__(self, config_path="config.yaml"):
        config_file = _SCRIPT_DIR / config_path
        with open(config_file, "r") as f:
            self.config = yaml.safe_load(f)
            
        tts_config = self.config.get("tts", {})
        
        # English voice
        raw_model = tts_config.get("voice_model_path", "models/en_US-libritts-high.onnx")
        raw_config = tts_config.get("voice_config_path", "models/en_US-libritts-high.onnx.json")
        self.model_path = str(_SCRIPT_DIR / raw_model)
        self.config_path_file = str(_SCRIPT_DIR / raw_config)
        
        # Hindi voice
        hi_raw_model = tts_config.get("hindi_voice_model_path", "models/hi_IN-rohan-medium.onnx")
        hi_raw_config = tts_config.get("hindi_voice_config_path", "models/hi_IN-rohan-medium.onnx.json")
        self.hi_model_path = str(_SCRIPT_DIR / hi_raw_model)
        self.hi_config_path_file = str(_SCRIPT_DIR / hi_raw_config)

        self.en_voice = None
        self.hi_voice = None
        self.en_syn_config = None
        self.hi_syn_config = None
        self.target_sample_rate = 22050

        try:
            from piper.voice import PiperVoice
            from piper.config import SynthesisConfig
            
            # Load English
            en_model_exists = os.path.exists(self.model_path)
            en_config_exists = os.path.exists(self.config_path_file)
            if en_model_exists and en_config_exists:
                self.en_voice = PiperVoice.load(self.model_path, config_path=self.config_path_file)
                self.en_syn_config = SynthesisConfig(speaker_id=0)
                print(f"[TTS] English Piper voice loaded.")
            else:
                print(f"Warning: English Piper voice not found at {self.model_path}")
                
            # Load Hindi
            hi_model_exists = os.path.exists(self.hi_model_path)
            hi_config_exists = os.path.exists(self.hi_config_path_file)
            if hi_model_exists and hi_config_exists:
                self.hi_voice = PiperVoice.load(self.hi_model_path, config_path=self.hi_config_path_file)
                self.hi_syn_config = SynthesisConfig(speaker_id=0)
                print(f"[TTS] Hindi Piper voice loaded.")
            else:
                print(f"Warning: Hindi Piper voice not found at {self.hi_model_path}")
                
            if not self.en_voice and not self.hi_voice:
                print("TTS will be stubbed.")
                
        except ImportError:
            print("Warning: piper-tts not installed or import failed. TTS will be stubbed.")

    def _split_text_by_language(self, text):
        runs = []
        current_run = ""
        current_lang = None
        
        for char in text:
            if '\u0900' <= char <= '\u097F':
                lang = 'hi'
            elif char.isalpha():
                lang = 'en'
            else:
                lang = current_lang if current_lang else 'en'
                
            if current_lang is None:
                current_lang = lang
                
            if lang != current_lang:
                if current_run.strip():
                    runs.append((current_lang, current_run))
                current_run = char
                current_lang = lang
            else:
                current_run += char
                
        if current_run.strip():
            runs.append((current_lang, current_run))
            
        return runs

    def _synthesize_chunk(self, lang, text):
        voice = self.hi_voice if lang == 'hi' and self.hi_voice else self.en_voice
        syn_config = self.hi_syn_config if lang == 'hi' and self.hi_voice else self.en_syn_config
        
        if not voice:
            return None, None
            
        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wav_file:
            voice.synthesize_wav(text, wav_file, syn_config=syn_config)
        
        wav_io.seek(0)
        with wave.open(wav_io, 'rb') as wf:
            sample_rate = wf.getframerate()
            n_frames = wf.getnframes()
            if n_frames == 0:
                return None, None
            audio_data = wf.readframes(n_frames)
            audio_int16 = np.frombuffer(audio_data, dtype=np.int16)
            audio_f32 = audio_int16.astype(np.float32) / 32768.0
            return audio_f32, sample_rate

    def speak(self, text):
        if not text.strip():
            return
            
        safe_text = text.encode('ascii', 'replace').decode('ascii')
        print(f"Speaking: {safe_text}")
        if self.en_voice is None and self.hi_voice is None:
            print("[TTS Stub] Imagine natural speech here.")
            return
            
        try:
            runs = self._split_text_by_language(text)
            audio_chunks = []
            
            for lang, chunk_text in runs:
                chunk_text = chunk_text.strip()
                if not chunk_text:
                    continue
                    
                safe_chunk = chunk_text.encode('ascii', 'replace').decode('ascii')
                print(f"  -> [{lang.upper()}] Synthesizing: {safe_chunk}")
                audio_f32, sr = self._synthesize_chunk(lang, chunk_text)
                
                if audio_f32 is not None:
                    # Resample if needed to match the target sample rate
                    if sr != self.target_sample_rate:
                        audio_f32 = librosa.resample(audio_f32, orig_sr=sr, target_sr=self.target_sample_rate)
                    audio_chunks.append(audio_f32)
            
            if audio_chunks:
                # Add a small pause between chunks if needed, but simple concatenation is usually fine
                final_audio = np.concatenate(audio_chunks)
                sd.play(final_audio, samplerate=self.target_sample_rate)
                sd.wait()
                
        except Exception as e:
            print(f"Error during TTS playback: {e}")

if __name__ == "__main__":
    tts = TTS()
    tts.speak("Hello Harsh. कैसे हो तुम? Everything is ready.")
