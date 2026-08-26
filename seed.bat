@echo off
rem ==== Lookbook Studio — run the live seeder (needs API keys in config.json) ====
cd /d "%~dp0"
python seed.py
pause
