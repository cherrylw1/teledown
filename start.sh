#!/bin/bash

echo "==================================================="
echo "            Teledown Startup Automation"
echo "==================================================="
echo ""

cd backend

# Check if local virtual environment exists
if [ ! -d "venv" ]; then
    echo "[INFO] Virtual environment not found. Creating venv..."
    
    # Attempt to locate Python 3
    if command -v python3 &>/dev/null; then
        python3 -m venv venv
    elif command -v python &>/dev/null; then
        python -m venv venv
    else
        echo "[ERROR] Python 3 not found. Please install Python 3.8+."
        exit 1
    fi
    echo "[SUCCESS] Virtual environment created."
fi

# Install requirements
echo "[INFO] Installing/updating dependencies..."
venv/bin/python -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies."
    exit 1
fi
echo "[SUCCESS] Dependencies verified."
echo ""

# Check for .env file
if [ ! -f ".env" ]; then
    echo "[WARNING] .env configuration file not found in /backend!"
    echo "Please create a .env file with TELEGRAM_API_ID and TELEGRAM_API_HASH."
    echo ""
fi

# Launch uvicorn server
echo "[INFO] Starting FastAPI application on port 8000..."
venv/bin/python -m uvicorn main:app --reload --port 8000
