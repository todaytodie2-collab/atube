@echo off
title A Tube - Ultra HD Media Experience
echo ===================================================
echo     A Tube - Ultra HD Media Experience Launcher
echo ===================================================
echo.
echo Starting application with real IPTV and VOD streaming services...
echo.

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Starting Production Server at http://localhost:8085 ...
    start "" http://localhost:8085/index.html
    python server.py 8085
) else (
    echo Python not found, opening static app in default browser...
    start "" index.html
)
