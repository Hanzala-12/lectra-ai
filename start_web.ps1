# Start Web Interface Script

Write-Host "`n🎙️ Voice Cleaning Pipeline - Web Interface" -ForegroundColor Cyan
Write-Host "=========================================`n" -ForegroundColor Cyan

# Activate virtual environment if it exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & .\venv\Scripts\Activate.ps1
} else {
    Write-Host "⚠️  Virtual environment not found. Run setup.ps1 first!" -ForegroundColor Red
    exit 1
}

# Check if streamlit is installed
$streamlitCheck = python -c "import streamlit" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nInstalling Streamlit..." -ForegroundColor Yellow
    pip install streamlit --quiet
}

# Check for Whisper models
Write-Host "`n📦 Whisper Model Info:" -ForegroundColor Yellow
Write-Host "  - Models download automatically on first use" -ForegroundColor White
Write-Host "  - Stored in: d:\fyp\models\\" -ForegroundColor White
Write-Host "  - Recommended: 'base' model (good balance)" -ForegroundColor White
Write-Host "  - 'large' model available (best quality)" -ForegroundColor White
Write-Host "  - NO tokens or accounts needed - 100% free!" -ForegroundColor Green
Write-Host ""

# Start Streamlit
Write-Host "🚀 Starting web interface..." -ForegroundColor Green
Write-Host "   Opening in browser at http://localhost:8501`n" -ForegroundColor Green

streamlit run app.py
