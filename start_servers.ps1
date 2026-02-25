# Start Both Frontend and Backend Servers
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Voice Cleaning Pipeline - Full Stack" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# AUTO-SETUP: Force D: drive venv (automatic, no manual steps!)
. "$PSScriptRoot\use_venv.ps1"

Write-Host "`nThis will start both servers in separate windows:" -ForegroundColor Yellow
Write-Host "  - Backend (FastAPI): http://localhost:8000" -ForegroundColor White
Write-Host "  - Frontend (React): http://localhost:3000" -ForegroundColor White
Write-Host "`nPress any key to continue..." -ForegroundColor Green
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Start backend in new window
Write-Host "`nStarting backend server..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-File", ".\start_backend.ps1"

# Wait a moment for backend to start
Start-Sleep -Seconds 2

# Start frontend in new window
Write-Host "Starting frontend server..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-File", ".\start_frontend.ps1"

Write-Host "`n✅ Both servers are starting in separate windows!" -ForegroundColor Green
Write-Host "`nOnce both servers are ready:" -ForegroundColor Yellow
Write-Host "  Open your browser to http://localhost:3000" -ForegroundColor White
Write-Host "`nTo stop the servers, close both PowerShell windows or press Ctrl+C in each.`n" -ForegroundColor Red
