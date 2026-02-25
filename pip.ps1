# ===================================================
# RUN PIP COMMAND - Automatic D: drive venv
# ===================================================
# Usage: .\pip.ps1 install package
# Example: .\pip.ps1 install requests

# AUTO-SETUP: Force D: drive venv (automatic!)
. "$PSScriptRoot\use_venv.ps1"

# Run pip with all arguments passed through
& "D:\fyp\venv\Scripts\pip.exe" $args
