# Start FastAPI Backend Server
Write-Host "Starting Voice Cleaning Backend Server..." -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

# AUTO-SETUP: Force D: drive venv (automatic, no manual steps!)
. "$PSScriptRoot\use_venv.ps1"

# Start uvicorn server
Write-Host "`nStarting server on http://localhost:8000" -ForegroundColor Green
Write-Host "API endpoints:" -ForegroundColor Yellow
Write-Host "  POST /api/process - Process audio/video file" -ForegroundColor White
Write-Host "  GET /api/download/{filename} - Download processed files" -ForegroundColor White
Write-Host "`nPress Ctrl+C to stop the server`n" -ForegroundColor Red

# Use venv Python directly - D: drive guaranteed!
Write-Host \"Starting uvicorn with D:\\fyp\\venv Python...`n\" -ForegroundColor Yellow
& "D:\fyp\venv\Scripts\python.exe" -m uvicorn backend:app --host 0.0.0.0 --port 8000 --reload
