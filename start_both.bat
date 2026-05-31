@echo off
echo Starting Lectra AI Backend and Frontend...
cd /d %~dp0

REM Start backend in a new window
start "Backend Server" cmd /k "call .\venv\Scripts\activate.bat && python backend.py"

REM Wait a moment for backend to start
timeout /t 3 /nobreak

REM Start frontend in a new window
start "Frontend Server" cmd /k "cd frontend && call npm run dev"

echo Both servers are starting...
echo Backend: Check the Backend Server window
echo Frontend: Check the Frontend Server window
pause
