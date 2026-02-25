# Start React Frontend Development Server
Write-Host "Starting Voice Cleaning Frontend..." -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

# AUTO-SETUP: Force D: drive venv (automatic, no manual steps!)
. "$PSScriptRoot\use_venv.ps1"

# Check if Node.js is installed
$nodeVersion = node --version 2>$null
if (-not $nodeVersion) {
    Write-Host "`nERROR: Node.js is not installed!" -ForegroundColor Red
    Write-Host "`nPlease install Node.js from: https://nodejs.org/" -ForegroundColor Yellow
    Write-Host "Download the LTS version (20.x or higher)" -ForegroundColor Yellow
    Write-Host "`nAfter installation:" -ForegroundColor White
    Write-Host "  1. Restart PowerShell" -ForegroundColor White
    Write-Host "  2. Go to frontend folder: cd d:\fyp\frontend" -ForegroundColor White
    Write-Host "  3. Install dependencies: npm install" -ForegroundColor White
    Write-Host "  4. Run this script again" -ForegroundColor White
    pause
    exit 1
}

Write-Host "`nNode.js version: $nodeVersion" -ForegroundColor Green

# Change to frontend directory
Set-Location -Path ".\frontend"

# Check if node_modules exists
if (-not (Test-Path ".\node_modules")) {
    Write-Host "`nInstalling dependencies (this may take a few minutes)..." -ForegroundColor Yellow
    npm install
}

# Start development server
Write-Host "`nStarting development server on http://localhost:3000" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server`n" -ForegroundColor Red

npm run dev
