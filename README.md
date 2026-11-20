# Siya - Personal PC AI Companion

Siya is a local, offline AI companion for Windows that runs silently in the background. She listens for the wake word "Hey Siya", thinks using a local LLM (Ollama), and replies using natural text-to-speech.

All computation is performed locally. Nothing leaves your PC.

## Prerequisites

1. **Python 3.10 or 3.11** installed.
2. **Gemini API Key** (Free Tier): Set the `GEMINI_API_KEY` environment variable on your system.
3. *(Optional)* **Ollama** installed on your system for offline fallback. Download from [ollama.com](https://ollama.com).

## Installation

1. **Clone/Download this repository** to your PC.
2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **(Optional) Pull the LLM model for Offline Fallback:**
   Start Ollama, then run:
   ```bash
   ollama pull llama3.1:8b
   ```
4. **Prepare the Models:**
   - **Wake Word:** Train your wake word model (`hey_siya.onnx`) via the openWakeWord Colab notebook and place it in the `models/` directory.
   - **TTS:** Download a Piper voice model (e.g., `en_US-libritts-high.onnx` and its `.json` config) and place them in the `models/` directory. (Ensure paths match `config.yaml`).

## Running Manually

To test the application, simply run:
```bash
python main.py
```
You should see a system tray icon appear. The icon color indicates Siya's state:
- Green: Idle
- Blue: Listening
- Orange: Thinking
- Purple: Speaking
- Gray: Muted

## Autostart on Logon

To make Siya run automatically and silently whenever you log in:
```bash
python install_startup.py
```

To remove the startup task:
```bash
python install_startup.py remove
```

## Configuration

Edit `config.yaml` to change:
- Your name
- The system prompt / personality
- Audio devices and cutoff thresholds
- Model paths
