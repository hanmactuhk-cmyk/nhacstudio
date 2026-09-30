# HNStudio Musik AI

Prototype Windows app for live vocal processing.

## Current prototype
- Neon dark UI
- Microphone/input and output device selection
- Sample rate + buffer selection
- Realtime direct monitoring
- Realtime input level/audio stream foundation
- Recording to WAV
- Project save/open (`.hnstudio.json`)
- Effect popup controls for Auto-Tune, EQ, Compressor, De-Esser, Reverb, Delay, Noise Reduction and Limiter
- Foundation for realtime waveform/spectrum and DSP engine

## Important
This is the first runnable foundation. The audio callback currently performs **direct monitoring**; the DSP effects are UI/configuration modules ready to be connected to the processing engine. It does not claim studio-grade Auto-Tune yet.

## Run locally
```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

For lowest latency, a Windows ASIO backend/interface should be added in the next DSP build.

## Build EXE with GitHub Actions
Push this repository to GitHub. The included workflow builds a Windows executable with PyInstaller and uploads it as an artifact.
