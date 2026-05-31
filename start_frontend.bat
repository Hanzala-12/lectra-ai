@echo off
echo Starting Lectra AI Frontend...
cd /d %~dp0
cd frontend
call npm run dev
pause
