# ===================================================
# RUN PROJECT - Always uses D: drive venv
# ===================================================
# This script ensures venv is used and starts backend

# Setup venv (permanent for this session)
. .\use_venv.ps1

Write-Host "`nStarting backend server...`n" -ForegroundColor Yellow

# Start backend using venv Python
& "D:\fyp\venv\Scripts\python.exe" -m uvicorn backend:app --host 0.0.0.0 --port 8000 --reload
