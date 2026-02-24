@echo off
REM ABOA System Setup Script for Windows
REM This script sets up the development environment and initializes the database

echo 🚀 Setting up ABOA system...

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found. Please install Python 3.9+
    exit /b 1
)

REM Check Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python %PYTHON_VERSION% found

REM Check if Docker is installed and running
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Docker not found. Some features may not work.
    set DOCKER_AVAILABLE=false
) else (
    docker info >nul 2>&1
    if %errorlevel% neq 0 (
        echo ❌ Docker is installed but not running. Please start Docker.
        set DOCKER_AVAILABLE=false
    ) else (
        echo ✅ Docker is running
        set DOCKER_AVAILABLE=true
    )
)

REM Create necessary directories
echo 📁 Creating necessary directories...
if not exist "logs" mkdir logs
if not exist "data" mkdir data
if not exist "scripts\migrations" mkdir scripts\migrations
if not exist "config" mkdir config
if not exist "nginx" mkdir nginx

REM Create virtual environment
if not exist "venv" (
    echo 🐍 Creating virtual environment...
    python -m venv venv
) else (
    echo ✅ Virtual environment already exists
)

REM Activate virtual environment and install dependencies
echo 📦 Installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Copy environment configuration
if not exist ".env" (
    echo ⚙️  Creating .env file from template...
    copy config\development.env .env
    echo ⚠️  Please review and update .env file with your specific configuration
) else (
    echo ✅ .env file already exists
)

REM Initialize database if Docker is available
if "%DOCKER_AVAILABLE%"=="true" (
    echo 🗄️ Starting database services with Docker...
    docker-compose up -d postgres chroma redis
    
    echo ⏳ Waiting for services to be ready...
    timeout /t 10 /nobreak >nul
    
    echo 🔄 Running database migrations...
    python scripts\migrate.py migrate
) else (
    echo ⚠️  Docker not available. Please set up database manually.
    echo ⚠️  Update DATABASE_URL in .env to point to your database.
)

REM Run basic tests
echo 🧪 Running basic tests to verify setup...
python -c "import sys; sys.path.insert(0, '.'); from aboa.core.config import get_settings; from aboa.main import create_app; print('✅ Basic imports successful')" 2>nul
if %errorlevel% neq 0 (
    echo ❌ Import test failed
    exit /b 1
)

echo.
echo ✅ ABOA setup complete!
echo.
echo Next steps:
echo 1. Review and update .env file with your configuration
echo 2. Start the development server:
echo    venv\Scripts\activate.bat
echo    python -m uvicorn aboa.main:app --reload
echo 3. Or use Docker:
echo    docker-compose up
echo.
echo The API will be available at http://localhost:8000
echo API documentation at http://localhost:8000/docs

pause