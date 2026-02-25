# Setup script for Voice Cleaning Pipeline

Write-Host "Voice Cleaning Pipeline - Setup Script" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

# Check Python installation
Write-Host "Checking Python installation..." -ForegroundColor Yellow
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue

if (-not $pythonCmd) {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ from https://www.python.org/" -ForegroundColor Red
    exit 1
}

$pythonVersion = python --version
Write-Host "Found: $pythonVersion" -ForegroundColor Green

# Check FFmpeg installation
Write-Host "`nChecking FFmpeg installation..." -ForegroundColor Yellow
$ffmpegCmd = Get-Command ffmpeg -ErrorAction SilentlyContinue

if (-not $ffmpegCmd) {
    Write-Host "WARNING: FFmpeg is not installed or not in PATH" -ForegroundColor Yellow
    Write-Host "Video processing will not work without FFmpeg" -ForegroundColor Yellow
    Write-Host "Download from: https://ffmpeg.org/download.html" -ForegroundColor Yellow
} else {
    $ffmpegVersion = ffmpeg -version | Select-Object -First 1
    Write-Host "Found: $ffmpegVersion" -ForegroundColor Green
}

# Create virtual environment
Write-Host "`nCreating virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "Virtual environment already exists" -ForegroundColor Yellow
} else {
    python -m venv venv
    Write-Host "Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "`nActivating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "`nUpgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install requirements
Write-Host "`nInstalling dependencies..." -ForegroundColor Yellow
Write-Host "This may take several minutes..." -ForegroundColor Yellow
pip install -r requirements.txt

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nDependencies installed successfully!" -ForegroundColor Green
} else {
    Write-Host "`nERROR: Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# Create necessary directories
Write-Host "`nCreating project directories..." -ForegroundColor Yellow
$dirs = @("uploads", "outputs", "temp", "models")
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-Host "Created: $dir/" -ForegroundColor Green
    }
}

# Check GPU availability
Write-Host "`nChecking GPU availability..." -ForegroundColor Yellow
$gpuCheck = python -c "import torch; print('CUDA' if torch.cuda.is_available() else 'CPU')" 2>$null
if ($gpuCheck -eq "CUDA") {
    Write-Host "GPU (CUDA) detected - Processing will be accelerated!" -ForegroundColor Green
} else {
    Write-Host "No GPU detected - Will use CPU (slower)" -ForegroundColor Yellow
}

# Setup instructions
Write-Host "`n=======================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. (Optional) Set Hugging Face token for speaker diarization:" -ForegroundColor White
Write-Host "   `$env:HUGGING_FACE_HUB_TOKEN='your_token_here'" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Test the pipeline:" -ForegroundColor White
Write-Host "   python clean_voice.py your_audio.mp3" -ForegroundColor Gray
Write-Host ""
Write-Host "3. See README.md for full documentation" -ForegroundColor White
Write-Host ""
Write-Host "Quick test command:" -ForegroundColor Yellow
Write-Host "   python clean_voice.py --help" -ForegroundColor Gray
Write-Host ""
