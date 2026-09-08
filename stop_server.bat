@echo off
title Stop A TuBe Server
echo ===================================================
echo           Stopping A TuBe Server (Port 8085)
echo ===================================================
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8085 ^| findstr LISTENING') do (
    taskkill /f /pid %%a >nul 2>&1
    echo Killed process PID: %%a
)
echo.
echo A TuBe Server has been stopped successfully.
timeout /t 3 >nul
