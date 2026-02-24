@echo off
echo ========================================
echo    AARO - Complete System Startup
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run: python -m venv venv
    echo Then: venv\Scripts\activate
    echo Then: pip install -r requirements.txt
    pause
    exit /b 1
)

echo [1/3] Activating virtual environment...
call venv\Scripts\activate

echo [2/3] Setting Python path...
set PYTHONPATH=%CD%

echo [3/3] Starting AARO system...
echo.
echo Starting API server (Backend)...
echo API will be available at: http://localhost:8000
echo API Documentation: http://localhost:8000/docs
echo.

REM Start API server in background
start "AARO API Server" cmd /k "echo AARO API Server && python aboa/main.py"

REM Wait a moment for API to start
timeout /t 5 /nobreak > nul

echo Starting UI server (Frontend)...
echo UI will be available at: http://localhost:3000
echo.

REM Start UI server
cd ui
python server.py

echo.
echo System stopped. Press any key to exit.
pause > nul