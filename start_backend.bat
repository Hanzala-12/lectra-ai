@echo off
echo Starting Lectra AI Backend in Virtual Environment...
cd /d %~dp0
call .\venv\Scripts\activate.bat
python backend.py
pause
