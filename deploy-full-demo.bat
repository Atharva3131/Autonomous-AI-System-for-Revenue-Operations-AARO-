@echo off
REM AARO Full Demo Deployment Script for Windows

echo 🚀 AARO Full Demo Deployment
echo ==============================

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not installed. Please install Docker Desktop first.
    pause
    exit /b 1
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose is not installed. Please install Docker Compose first.
    pause
    exit /b 1
)

echo ✅ Docker and Docker Compose found

REM Create necessary directories
if not exist nginx mkdir nginx
if not exist logs mkdir logs
if not exist data mkdir data

echo 📁 Created necessary directories

REM Build and start the demo
echo 🔨 Building and starting AARO demo...
docker-compose up -d --build

REM Wait for services to start
echo ⏳ Waiting for services to start...
timeout /t 30 /nobreak >nul

echo.
echo 🎉 AARO Demo Deployment Complete!
echo ==================================
echo.
echo 📱 Access your demo at:
echo    • Full UI (Nginx):     http://localhost
echo    • Direct UI:           http://localhost:3000
echo    • API:                 http://localhost:8000
echo    • API Documentation:   http://localhost:8000/docs
echo    • Health Check:        http://localhost:8000/health
echo.
echo 🔧 Management commands:
echo    • View logs:           docker-compose logs -f
echo    • Stop demo:           docker-compose down
echo    • Restart demo:        docker-compose restart
echo.
echo ✨ Your AARO demo is ready for recruiters!
echo.
echo Opening browser...
start http://localhost:3000

pause