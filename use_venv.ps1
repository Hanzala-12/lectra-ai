# ===================================================
# FORCE USE OF VENV ON D: DRIVE (PERMANENT SETUP)
# Run this ONCE when opening new PowerShell window
# ===================================================

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Voice Cleaning Pipeline - Venv Setup  " -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "\u2705 Python location: D:\fyp\venv\Scripts\python.exe" -ForegroundColor Green
Write-Host "\u2705 Packages install to: D:\fyp\venv\Lib\site-packages\" -ForegroundColor Green
Write-Host "\u2705 Pip cache: D:\fyp\.pip_cache\" -ForegroundColor Green
Write-Host "\u2705 Models download to: D:\fyp\models\" -ForegroundColor Green
Write-Host "\u274c NOTHING goes to C: drive!`n" -ForegroundColor Red

# Set environment variables for this session
$env:VIRTUAL_ENV = "D:\fyp\venv"
$env:PATH = "D:\fyp\venv\Scripts;$env:PATH"
$env:PYTHONPATH = "D:\fyp\src"
$env:PIP_CACHE_DIR = "D:\fyp\.pip_cache"  # Force pip cache to D: drive!

# Create PowerShell functions that override python/pip
function python { & "D:\fyp\venv\Scripts\python.exe" $args }
function pip { & "D:\fyp\venv\Scripts\pip.exe" $args }

Write-Host "Setting up python and pip commands..." -ForegroundColor Yellow

# Verify it worked
$pythonPath = & "D:\fyp\venv\Scripts\python.exe" -c "import sys; print(sys.executable)"
Write-Host "`n\u2705 Verified: python command now uses: $pythonPath`n" -ForegroundColor Green

Write-Host "Ready! Now you can use:" -ForegroundColor White
Write-Host "  - python <file.py>" -ForegroundColor White
Write-Host "  - pip install <package>" -ForegroundColor White
Write-Host "  - .\start_backend.ps1" -ForegroundColor White
Write-Host "`nAll will use D:\fyp\venv only!`n" -ForegroundColor Cyan
