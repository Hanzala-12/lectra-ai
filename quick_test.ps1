# Quick Test Script - Process Audio via API
param(
    [Parameter(Mandatory=$true)]
    [string]$AudioFile
)

. "$PSScriptRoot\use_venv.ps1"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Quick API Test - Voice Cleaning" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

if (-not (Test-Path $AudioFile)) {
    Write-Host "❌ File not found: $AudioFile" -ForegroundColor Red
    exit 1
}

Write-Host "📁 Input: $AudioFile" -ForegroundColor Yellow
Write-Host "🚀 Sending to API: http://localhost:8000/api/process`n" -ForegroundColor Yellow

$response = curl  -X POST "http://localhost:8000/api/process" `
    -F "file=@$AudioFile" `
    -F "enable_cache=true" `
    -F "enable_diarization=true" `
    -F "return_transcript=true"

Write-Host "`n✅ Response:" -ForegroundColor Green
$response | ConvertFrom-Json | ConvertTo-Json -Depth 10

Write-Host "`n========================================" -ForegroundColor Green
