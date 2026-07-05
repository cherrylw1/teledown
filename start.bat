@echo off
title Teledown Startup Script
echo ===================================================
echo             Teledown Startup Automation
echo ===================================================
echo.

cd backend

:: Check if local virtual environment exists
if not exist venv (
    echo [INFO] Virtual environment not found. Creating venv...
    
    :: Attempt to locate Python
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        python -m venv venv
    ) else (
        if exist "%USERPROFILE%\miniconda3\python.exe" (
            echo [INFO] System Python not in PATH. Using Miniconda Python...
            "%USERPROFILE%\miniconda3\python.exe" -m venv venv
        ) else (
            echo [ERROR] Python not found. Please install Python 3.8+ or add it to PATH.
            pause
            exit /b 1
        )
    )
    echo [SUCCESS] Virtual environment created.
)

:: Install requirements
echo [INFO] Installing/updating dependencies...
venv\Scripts\python.exe -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [SUCCESS] Dependencies verified.
echo.

:: Check for .env file
if not exist .env (
    echo [WARNING] .env configuration file not found in /backend!
    echo Please create a .env file with TELEGRAM_API_ID and TELEGRAM_API_HASH.
    echo.
)

:: Launch uvicorn server
echo [INFO] Starting FastAPI application on port 8000...
venv\Scripts\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
pause
