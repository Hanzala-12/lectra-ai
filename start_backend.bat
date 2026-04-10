@echo off
echo Starting Voice Cleaning Backend in Virtual Environment...
cd /d %~dp0
call .\venv\Scripts\activate.bat
python backend.py
pause
