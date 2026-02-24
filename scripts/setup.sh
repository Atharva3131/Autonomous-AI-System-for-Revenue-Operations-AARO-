#!/bin/bash
# ABOA System Setup Script
# This script sets up the development environment and initializes the database

set -e  # Exit on any error

echo "🚀 Setting up ABOA system..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python 3.9+ is installed
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        REQUIRED_VERSION="3.9"
        
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"; then
            print_status "Python $PYTHON_VERSION found"
        else
            print_error "Python 3.9+ required, found $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python 3 not found. Please install Python 3.9+"
        exit 1
    fi
}

# Check if Docker is installed and running
check_docker() {
    if command -v docker &> /dev/null; then
        if docker info &> /dev/null; then
            print_status "Docker is running"
        else
            print_error "Docker is installed but not running. Please start Docker."
            exit 1
        fi
    else
        print_warning "Docker not found. Some features may not work."
    fi
}

# Create virtual environment
setup_venv() {
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv venv
    else
        print_status "Virtual environment already exists"
    fi
    
    print_status "Activating virtual environment..."
    source venv/bin/activate
    
    print_status "Upgrading pip..."
    pip install --upgrade pip
    
    print_status "Installing dependencies..."
    pip install -r requirements.txt
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    mkdir -p logs
    mkdir -p data
    mkdir -p scripts/migrations
    mkdir -p config
    mkdir -p nginx
}

# Copy environment configuration
setup_env() {
    if [ ! -f ".env" ]; then
        print_status "Creating .env file from template..."
        cp config/development.env .env
        print_warning "Please review and update .env file with your specific configuration"
    else
        print_status ".env file already exists"
    fi
}

# Initialize database
init_database() {
    print_status "Initializing database..."
    
    # Check if we're using Docker
    if command -v docker &> /dev/null && docker info &> /dev/null; then
        print_status "Starting database services with Docker..."
        docker-compose up -d postgres chroma redis
        
        # Wait for services to be ready
        print_status "Waiting for services to be ready..."
        sleep 10
        
        # Run migrations
        print_status "Running database migrations..."
        python scripts/migrate.py migrate
    else
        print_warning "Docker not available. Please set up database manually."
        print_warning "Update DATABASE_URL in .env to point to your database."
    fi
}

# Create nginx configuration
setup_nginx() {
    print_status "Creating nginx configuration..."
    mkdir -p nginx
    
    cat > nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream aboa_app {
        server aboa-app:8000;
    }
    
    server {
        listen 80;
        server_name localhost;
        
        location / {
            proxy_pass http://aboa_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        location /health {
            proxy_pass http://aboa_app/health;
            access_log off;
        }
    }
}
EOF
}

# Run tests to verify setup
run_tests() {
    print_status "Running basic tests to verify setup..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Run a simple import test
    python -c "
import sys
sys.path.insert(0, '.')
try:
    from aboa.core.config import get_settings
    from aboa.main import create_app
    print('✅ Basic imports successful')
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
"
    
    # Run pytest if available
    if command -v pytest &> /dev/null; then
        print_status "Running unit tests..."
        pytest tests/ -v --tb=short || print_warning "Some tests failed, but setup is complete"
    fi
}

# Main setup process
main() {
    echo "🔍 Checking prerequisites..."
    check_python
    check_docker
    
    echo "📁 Setting up project structure..."
    create_directories
    setup_env
    setup_nginx
    
    echo "🐍 Setting up Python environment..."
    setup_venv
    
    echo "🗄️ Setting up database..."
    init_database
    
    echo "🧪 Verifying setup..."
    run_tests
    
    echo ""
    print_status "✅ ABOA setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Review and update .env file with your configuration"
    echo "2. Start the development server:"
    echo "   source venv/bin/activate"
    echo "   python -m uvicorn aboa.main:app --reload"
    echo "3. Or use Docker:"
    echo "   docker-compose up"
    echo ""
    echo "The API will be available at http://localhost:8000"
    echo "API documentation at http://localhost:8000/docs"
}

# Run main function
main "$@"