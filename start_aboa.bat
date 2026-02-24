@echo off
echo Starting ABOA (Autonomous AI Agent for Revenue Operations)
echo.

REM Activate virtual environment
call venv\Scripts\activate

REM Set Python path to current directory
set PYTHONPATH=%CD%

REM Start the FastAPI server
echo Starting server at http://localhost:8000
echo API Documentation will be available at http://localhost:8000/docs
echo.
python aboa/main.py

pause