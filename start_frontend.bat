@echo off
echo Starting Voice Cleaning Frontend...
cd /d %~dp0
cd frontend
call npm run dev
pause
