@echo off
rem ==== Lookbook Studio launcher ====
cd /d "%~dp0"
python main.py
if errorlevel 1 (
  echo.
  echo App exited with an error. See the message above.
  pause
)
