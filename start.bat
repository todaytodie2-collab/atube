@echo off
chcp 65001 >nul
title A Tube - Ultra HD Media Experience
echo ===================================================
echo     A Tube - Ultra HD Media Experience Launcher
echo ===================================================
echo.
echo Starting application with real IPTV and VOD streaming services...
echo.

:: Ensure local environment file is created if missing
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] Initializing .env configuration from .env.example...
        copy ".env.example" ".env" >nul
    )
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Starting Production Server at http://localhost:8085 ...
    start "" http://localhost:8085/index.html
    python server.py 8085
) else (
    echo Python not found, opening static app in default browser...
    start "" index.html
)

