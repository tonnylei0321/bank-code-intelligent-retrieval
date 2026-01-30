#!/bin/bash

# Bank Code Retrieval System - Stop Script
# This script stops the FastAPI application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="Bank Code Retrieval API"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$APP_DIR/.api.pid"
FORCE=false
TIMEOUT=10

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

check_if_running() {
    if [ ! -f "$PID_FILE" ]; then
        print_warn "$APP_NAME is not running (no PID file found)"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    if ! ps -p "$PID" > /dev/null 2>&1; then
        print_warn "$APP_NAME is not running (process $PID not found)"
        print_info "Removing stale PID file..."
        rm "$PID_FILE"
        return 1
    fi
    
    return 0
}

stop_service() {
    if ! check_if_running; then
        return 0
    fi
    
    PID=$(cat "$PID_FILE")
    print_info "Stopping $APP_NAME (PID: $PID)..."
    
    if [ "$FORCE" = true ]; then
        # Force kill
        print_warn "Force stopping..."
        kill -9 "$PID" 2>/dev/null || true
        rm "$PID_FILE"
        print_info "$APP_NAME stopped (forced)"
    else
        # Graceful shutdown
        kill -TERM "$PID" 2>/dev/null || {
            print_error "Failed to send TERM signal to process $PID"
            print_info "Try using --force option"
            exit 1
        }
        
        # Wait for process to stop
        print_info "Waiting for graceful shutdown (timeout: ${TIMEOUT}s)..."
        COUNTER=0
        while ps -p "$PID" > /dev/null 2>&1; do
            if [ $COUNTER -ge $TIMEOUT ]; then
                print_warn "Timeout reached. Force stopping..."
                kill -9 "$PID" 2>/dev/null || true
                break
            fi
            sleep 1
            COUNTER=$((COUNTER + 1))
            echo -n "."
        done
        echo ""
        
        # Remove PID file
        rm "$PID_FILE"
        print_info "$APP_NAME stopped successfully"
    fi
}

stop_all_related() {
    print_info "Stopping all related processes..."
    
    # Find all uvicorn processes
    PIDS=$(pgrep -f "uvicorn app.main:app" || true)
    
    if [ -z "$PIDS" ]; then
        print_info "No related processes found"
        return 0
    fi
    
    print_info "Found processes: $PIDS"
    
    for PID in $PIDS; do
        print_info "Stopping process $PID..."
        if [ "$FORCE" = true ]; then
            kill -9 "$PID" 2>/dev/null || true
        else
            kill -TERM "$PID" 2>/dev/null || true
        fi
    done
    
    # Wait for processes to stop
    sleep 2
    
    # Check if any processes are still running
    REMAINING=$(pgrep -f "uvicorn app.main:app" || true)
    if [ -n "$REMAINING" ]; then
        print_warn "Some processes are still running: $REMAINING"
        if [ "$FORCE" = false ]; then
            print_info "Use --force to kill them"
        else
            print_info "Force killing remaining processes..."
            for PID in $REMAINING; do
                kill -9 "$PID" 2>/dev/null || true
            done
        fi
    else
        print_info "All related processes stopped"
    fi
    
    # Clean up PID file
    if [ -f "$PID_FILE" ]; then
        rm "$PID_FILE"
    fi
}

show_status() {
    echo ""
    print_info "========================================="
    print_info "  $APP_NAME - Status"
    print_info "========================================="
    echo ""
    
    if check_if_running; then
        PID=$(cat "$PID_FILE")
        print_info "Status: RUNNING"
        print_info "PID: $PID"
        
        # Show process info
        if command -v ps &> /dev/null; then
            echo ""
            print_info "Process details:"
            ps -p "$PID" -o pid,ppid,user,%cpu,%mem,etime,cmd
        fi
        
        # Show listening ports
        if command -v lsof &> /dev/null; then
            echo ""
            print_info "Listening ports:"
            lsof -Pan -p "$PID" -i 2>/dev/null | grep LISTEN || print_info "No ports found"
        elif command -v netstat &> /dev/null; then
            echo ""
            print_info "Listening ports:"
            netstat -tlnp 2>/dev/null | grep "$PID" || print_info "No ports found"
        fi
    else
        print_info "Status: NOT RUNNING"
    fi
    
    echo ""
    print_info "========================================="
    echo ""
}

# Main execution
main() {
    echo ""
    print_info "========================================="
    print_info "  $APP_NAME - Stop Script"
    print_info "========================================="
    echo ""
    
    stop_service
    
    echo ""
    print_info "========================================="
    print_info "  Shutdown Complete"
    print_info "========================================="
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force|-f)
            FORCE=true
            shift
            ;;
        --all)
            stop_all_related
            exit 0
            ;;
        --status)
            show_status
            exit 0
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --force, -f        Force stop (kill -9)"
            echo "  --all              Stop all related processes"
            echo "  --status           Show service status"
            echo "  --timeout SECONDS  Graceful shutdown timeout (default: 10)"
            echo "  --help, -h         Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                 # Graceful stop"
            echo "  $0 --force         # Force stop"
            echo "  $0 --all           # Stop all related processes"
            echo "  $0 --status        # Show status"
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
