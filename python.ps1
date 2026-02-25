# ===================================================
# RUN PYTHON SCRIPT - Automatic D: drive venv
# ===================================================
# Usage: .\python.ps1 script.py args
# Example: .\python.ps1 clean_voice.py test.wav --transcript

# AUTO-SETUP: Force D: drive venv (automatic!)
. "$PSScriptRoot\use_venv.ps1"

# Run Python with all arguments passed through
& "D:\fyp\venv\Scripts\python.exe" $args
