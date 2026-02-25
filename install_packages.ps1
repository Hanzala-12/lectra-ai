# ===================================================
# INSTALL ALL PACKAGES TO D: DRIVE VENV
# ===================================================
# This script installs everything to D:\fyp\venv ONLY

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Installing Packages to D: Drive Venv  " -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Setup venv first
. .\use_venv.ps1

# Verify we're using D: drive
$pythonPath = & "D:\fyp\venv\Scripts\python.exe" -c "import sys; print(sys.executable)"
if ($pythonPath -notlike "*D:\fyp\venv*") {
    Write-Host "`n\u274c ERROR: Not using D: drive venv!" -ForegroundColor Red
    Write-Host "Current Python: $pythonPath" -ForegroundColor Red
    exit 1
}

Write-Host "\u2705 Confirmed using: $pythonPath`n" -ForegroundColor Green

# Ask for confirmation
Write-Host "This will install all packages to: D:\fyp\venv\Lib\site-packages\" -ForegroundColor Yellow
Write-Host "Estimated size: ~3-4 GB on D: drive" -ForegroundColor Yellow
Write-Host "C: drive will NOT be used!`n" -ForegroundColor Green

$confirmation = Read-Host "Continue? (yes/no)"
if ($confirmation -ne "yes") {
    Write-Host "Installation cancelled." -ForegroundColor Red
    exit 0
}

Write-Host "`nInstalling packages (this may take 5-10 minutes)...`n" -ForegroundColor Cyan

# Install using venv pip directly
& "D:\fyp\venv\Scripts\pip.exe" install -r requirements.txt

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  Installation Complete!  " -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

# Verify installation location
Write-Host "Verifying installation location..." -ForegroundColor Yellow
$numpyLocation = & "D:\fyp\venv\Scripts\pip.exe" show numpy | Select-String "Location"
Write-Host "\u2705 Packages installed at: $numpyLocation" -ForegroundColor Green

Write-Host "`nAll packages are on D: drive! \u2705" -ForegroundColor Cyan
Write-Host "`nNext steps:" -ForegroundColor White
Write-Host "  1. Run: . .\use_venv.ps1 (sets up environment)" -ForegroundColor White
Write-Host "  2. Run: .\run.ps1 (starts the project)" -ForegroundColor White
