@echo off
title NutriX Server & Ngrok Launcher
cd /d "%~dp0"
python start_server_and_ngrok.py
if errorlevel 1 (
    echo.
    echo Server stopped with error.
    pause
)
