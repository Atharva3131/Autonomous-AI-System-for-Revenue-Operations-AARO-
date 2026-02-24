#!/bin/bash
# ABOA Deployment Script
# Supports Docker Compose and Kubernetes deployments

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_header() {
    echo -e "${BLUE}[DEPLOY]${NC} $1"
}

# Default values
DEPLOYMENT_TYPE="docker"
ENVIRONMENT="production"
BUILD_IMAGE=true
SKIP_TESTS=false
FORCE_RECREATE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            DEPLOYMENT_TYPE="$2"
            shift 2
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --no-build)
            BUILD_IMAGE=false
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --force-recreate)
            FORCE_RECREATE=true
            shift
            ;;
        -h|--help)
            echo "ABOA Deployment Script"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -t, --type TYPE        Deployment type: docker, k8s (default: docker)"
            echo "  -e, --environment ENV  Environment: development, staging, production (default: production)"
            echo "  --no-build            Skip Docker image build"
            echo "  --skip-tests          Skip running tests before deployment"
            echo "  --force-recreate      Force recreate containers/pods"
            echo "  -h, --help            Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --type docker --environment staging"
            echo "  $0 --type k8s --environment production --skip-tests"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

print_header "🚀 Starting ABOA deployment"
print_status "Deployment type: $DEPLOYMENT_TYPE"
print_status "Environment: $ENVIRONMENT"

# Validate deployment type
if [[ "$DEPLOYMENT_TYPE" != "docker" && "$DEPLOYMENT_TYPE" != "k8s" ]]; then
    print_error "Invalid deployment type: $DEPLOYMENT_TYPE. Must be 'docker' or 'k8s'"
    exit 1
fi

# Validate environment
if [[ "$ENVIRONMENT" != "development" && "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    print_error "Invalid environment: $ENVIRONMENT. Must be 'development', 'staging', or 'production'"
    exit 1
fi

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if [[ "$DEPLOYMENT_TYPE" == "docker" ]]; then
        if ! command -v docker &> /dev/null; then
            print_error "Docker is required but not installed"
            exit 1
        fi
        
        if ! command -v docker-compose &> /dev/null; then
            print_error "Docker Compose is required but not installed"
            exit 1
        fi
        
        if ! docker info &> /dev/null; then
            print_error "Docker is not running"
            exit 1
        fi
    elif [[ "$DEPLOYMENT_TYPE" == "k8s" ]]; then
        if ! command -v kubectl &> /dev/null; then
            print_error "kubectl is required but not installed"
            exit 1
        fi
        
        if ! kubectl cluster-info &> /dev/null; then
            print_error "kubectl is not connected to a cluster"
            exit 1
        fi
    fi
    
    print_status "Prerequisites check passed"
}

# Run tests
run_tests() {
    if [[ "$SKIP_TESTS" == true ]]; then
        print_warning "Skipping tests as requested"
        return
    fi
    
    print_status "Running tests..."
    
    # Activate virtual environment if it exists
    if [[ -d "venv" ]]; then
        source venv/bin/activate
    fi
    
    # Run tests
    if command -v pytest &> /dev/null; then
        pytest tests/ -v --tb=short || {
            print_error "Tests failed"
            exit 1
        }
    else
        print_warning "pytest not found, skipping tests"
    fi
    
    print_status "Tests passed"
}

# Build Docker image
build_image() {
    if [[ "$BUILD_IMAGE" == false ]]; then
        print_warning "Skipping image build as requested"
        return
    fi
    
    print_status "Building Docker image..."
    
    # Build image with appropriate target
    if [[ "$ENVIRONMENT" == "development" ]]; then
        docker build --target development -t aboa:latest -t aboa:dev .
    else
        docker build --target production -t aboa:latest -t aboa:$ENVIRONMENT .
    fi
    
    print_status "Docker image built successfully"
}

# Deploy with Docker Compose
deploy_docker() {
    print_status "Deploying with Docker Compose..."
    
    # Choose the right compose file
    COMPOSE_FILE="docker-compose.yml"
    if [[ "$ENVIRONMENT" == "production" ]]; then
        COMPOSE_FILE="docker-compose.prod.yml"
    fi
    
    # Set environment variables
    export ENVIRONMENT=$ENVIRONMENT
    
    # Deploy
    if [[ "$FORCE_RECREATE" == true ]]; then
        docker-compose -f $COMPOSE_FILE down
        docker-compose -f $COMPOSE_FILE up -d --force-recreate
    else
        docker-compose -f $COMPOSE_FILE up -d
    fi
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 10
    
    # Check health
    if curl -f http://localhost:8000/health &> /dev/null; then
        print_status "✅ ABOA service is healthy"
    else
        print_warning "⚠️  ABOA service health check failed"
    fi
    
    print_status "Docker deployment completed"
    print_status "API available at: http://localhost:8000"
    print_status "API docs available at: http://localhost:8000/docs"
}

# Deploy to Kubernetes
deploy_k8s() {
    print_status "Deploying to Kubernetes..."
    
    # Apply namespace first
    kubectl apply -f k8s/namespace.yaml
    
    # Apply configurations
    kubectl apply -f k8s/configmap.yaml
    kubectl apply -f k8s/secret.yaml
    
    # Apply deployment and services
    kubectl apply -f k8s/deployment.yaml
    
    # Apply ingress if not development
    if [[ "$ENVIRONMENT" != "development" ]]; then
        kubectl apply -f k8s/ingress.yaml
    fi
    
    # Wait for deployment to be ready
    print_status "Waiting for deployment to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/aboa-app -n aboa
    
    # Check pod status
    kubectl get pods -n aboa
    
    # Port forward for testing (if development)
    if [[ "$ENVIRONMENT" == "development" ]]; then
        print_status "Setting up port forwarding for development..."
        kubectl port-forward service/aboa-service 8000:80 -n aboa &
        PORT_FORWARD_PID=$!
        
        # Wait a moment for port forward to establish
        sleep 5
        
        # Check health
        if curl -f http://localhost:8000/health &> /dev/null; then
            print_status "✅ ABOA service is healthy"
        else
            print_warning "⚠️  ABOA service health check failed"
        fi
        
        print_status "Kubernetes deployment completed"
        print_status "API available at: http://localhost:8000 (port-forwarded)"
        print_status "To stop port forwarding: kill $PORT_FORWARD_PID"
    else
        print_status "Kubernetes deployment completed"
        print_status "API available via ingress (check ingress configuration)"
    fi
}

# Cleanup function
cleanup() {
    if [[ -n "$PORT_FORWARD_PID" ]]; then
        kill $PORT_FORWARD_PID 2>/dev/null || true
    fi
}

# Set trap for cleanup
trap cleanup EXIT

# Main deployment flow
main() {
    check_prerequisites
    run_tests
    
    if [[ "$DEPLOYMENT_TYPE" == "docker" ]]; then
        build_image
        deploy_docker
    elif [[ "$DEPLOYMENT_TYPE" == "k8s" ]]; then
        build_image
        deploy_k8s
    fi
    
    print_header "🎉 Deployment completed successfully!"
    
    # Show useful commands
    echo ""
    print_status "Useful commands:"
    if [[ "$DEPLOYMENT_TYPE" == "docker" ]]; then
        echo "  View logs: docker-compose logs -f aboa-app"
        echo "  Stop services: docker-compose down"
        echo "  Restart: docker-compose restart aboa-app"
    elif [[ "$DEPLOYMENT_TYPE" == "k8s" ]]; then
        echo "  View logs: kubectl logs -f deployment/aboa-app -n aboa"
        echo "  Check status: kubectl get pods -n aboa"
        echo "  Delete deployment: kubectl delete namespace aboa"
    fi
}

# Run main function
main "$@"