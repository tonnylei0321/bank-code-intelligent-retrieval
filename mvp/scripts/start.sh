#!/bin/bash

# Bank Code Retrieval System - Start Script
# This script starts the FastAPI application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="Bank Code Retrieval API"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$APP_DIR/.venv"
PID_FILE="$APP_DIR/.api.pid"
LOG_DIR="$APP_DIR/logs"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-4}"
RELOAD="${RELOAD:-false}"

# Functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    print_info "Checking requirements..."
    
    # Check Python version
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    REQUIRED_VERSION="3.9"
    
    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
        print_error "Python $REQUIRED_VERSION or higher is required (found $PYTHON_VERSION)"
        exit 1
    fi
    
    print_info "Python version: $PYTHON_VERSION ✓"
    
    # Check virtual environment
    if [ ! -d "$VENV_DIR" ]; then
        print_error "Virtual environment not found at $VENV_DIR"
        print_info "Please run: python3 -m venv .venv"
        exit 1
    fi
    
    print_info "Virtual environment found ✓"
    
    # Check .env file
    if [ ! -f "$APP_DIR/.env" ]; then
        print_warn ".env file not found"
        if [ -f "$APP_DIR/.env.example" ]; then
            print_info "Copying .env.example to .env"
            cp "$APP_DIR/.env.example" "$APP_DIR/.env"
            print_warn "Please edit .env file with your configuration"
        else
            print_error ".env.example not found"
            exit 1
        fi
    fi
    
    print_info ".env file found ✓"
    
    # Check database
    if [ ! -f "$APP_DIR/data/bank_code.db" ]; then
        print_warn "Database not found. Initializing..."
        source "$VENV_DIR/bin/activate"
        python "$APP_DIR/scripts/init_db.py"
        deactivate
    fi
    
    print_info "Database ready ✓"
}

check_if_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            print_warn "$APP_NAME is already running (PID: $PID)"
            print_info "Use './scripts/stop.sh' to stop it first"
            exit 1
        else
            print_warn "Stale PID file found. Removing..."
            rm "$PID_FILE"
        fi
    fi
}

create_directories() {
    print_info "Creating necessary directories..."
    mkdir -p "$LOG_DIR"
    mkdir -p "$APP_DIR/data"
    mkdir -p "$APP_DIR/models/base"
    mkdir -p "$APP_DIR/models/finetuned"
    mkdir -p "$APP_DIR/reports"
    mkdir -p "$APP_DIR/uploads"
    print_info "Directories created ✓"
}

start_service() {
    print_info "Starting $APP_NAME..."
    
    cd "$APP_DIR"
    source "$VENV_DIR/bin/activate"
    
    # Build uvicorn command
    UVICORN_CMD="uvicorn app.main:app --host $HOST --port $PORT"
    
    if [ "$RELOAD" = "true" ]; then
        print_info "Starting in development mode (auto-reload enabled)"
        UVICORN_CMD="$UVICORN_CMD --reload"
    else
        print_info "Starting in production mode"
        UVICORN_CMD="$UVICORN_CMD --workers $WORKERS"
    fi
    
    # Start the service
    if [ "$RELOAD" = "true" ]; then
        # Development mode - run in foreground
        print_info "Service URL: http://$HOST:$PORT"
        print_info "API Docs: http://$HOST:$PORT/docs"
        print_info "Press Ctrl+C to stop"
        echo ""
        $UVICORN_CMD
    else
        # Production mode - run in background
        LOG_FILE="$LOG_DIR/uvicorn_$(date +%Y%m%d).log"
        nohup $UVICORN_CMD > "$LOG_FILE" 2>&1 &
        PID=$!
        echo $PID > "$PID_FILE"
        
        # Wait a moment and check if process is still running
        sleep 2
        if ps -p "$PID" > /dev/null 2>&1; then
            print_info "$APP_NAME started successfully!"
            print_info "PID: $PID"
            print_info "Service URL: http://$HOST:$PORT"
            print_info "API Docs: http://$HOST:$PORT/docs"
            print_info "Logs: $LOG_FILE"
            print_info ""
            print_info "Use './scripts/stop.sh' to stop the service"
        else
            print_error "Failed to start $APP_NAME"
            print_error "Check logs at: $LOG_FILE"
            rm "$PID_FILE"
            exit 1
        fi
    fi
    
    deactivate
}

# Main execution
main() {
    echo ""
    print_info "========================================="
    print_info "  $APP_NAME - Start Script"
    print_info "========================================="
    echo ""
    
    check_requirements
    check_if_running
    create_directories
    start_service
    
    echo ""
    print_info "========================================="
    print_info "  Startup Complete"
    print_info "========================================="
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dev|--reload)
            RELOAD=true
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dev, --reload    Start in development mode with auto-reload"
            echo "  --port PORT        Port to listen on (default: 8000)"
            echo "  --host HOST        Host to bind to (default: 0.0.0.0)"
            echo "  --workers N        Number of worker processes (default: 4)"
            echo "  --help, -h         Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                 # Start in production mode"
            echo "  $0 --dev           # Start in development mode"
            echo "  $0 --port 8080     # Start on port 8080"
            echo "  $0 --workers 8     # Start with 8 workers"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

main
