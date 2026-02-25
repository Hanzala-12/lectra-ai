# ===================================================
# QUICK START GUIDE - Voice Cleaning Pipeline
# ===================================================

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Voice Cleaning Pipeline - Quick Start" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "\u2705 All scripts automatically use D: drive venv!" -ForegroundColor Green
Write-Host "\u2705 No manual venv activation needed!" -ForegroundColor Green
Write-Host "\u2705 Just run the scripts directly!`n" -ForegroundColor Green

Write-Host "Available Commands:`n" -ForegroundColor Yellow

Write-Host "1. Install packages (first time only):" -ForegroundColor White
Write-Host "   .\install_packages.ps1`n" -ForegroundColor Cyan

Write-Host "2. Process audio file:" -ForegroundColor White
Write-Host "   .\python.ps1 clean_voice.py audio.mp3 --transcript`n" -ForegroundColor Cyan

Write-Host "3. Start backend server:" -ForegroundColor White
Write-Host "   .\start_backend.ps1`n" -ForegroundColor Cyan

Write-Host "4. Start frontend (needs Node.js):" -ForegroundColor White
Write-Host "   .\start_frontend.ps1`n" -ForegroundColor Cyan

Write-Host "5. Start both frontend + backend:" -ForegroundColor White
Write-Host "   .\start_servers.ps1`n" -ForegroundColor Cyan

Write-Host "6. Run tests:" -ForegroundColor White
Write-Host "   .\python.ps1 -m pytest`n" -ForegroundColor Cyan

Write-Host "========================================" -ForegroundColor Green
Write-Host "  Everything uses D:\fyp\venv automatically!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green
