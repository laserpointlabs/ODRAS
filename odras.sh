#!/bin/bash

# ODRAS Application Management Script
# Usage: ./start.sh [command]
# Commands: start, stop, restart, status, logs, down, up, clean

# Configuration
APP_NAME="odras"
APP_PORT=8000
DOCKER_COMPOSE_FILE="docker-compose.yml"
PYTHON_APP_DIR="backend"
PID_FILE="/tmp/odras_app.pid"
LOG_FILE="/tmp/odras_app.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running from correct directory
check_directory() {
    if [[ ! -f "$DOCKER_COMPOSE_FILE" ]] || [[ ! -d "$PYTHON_APP_DIR" ]]; then
        print_error "Please run this script from the ODRAS root directory (where docker-compose.yml is located)"
        exit 1
    fi
}

# Check if Python app is running
is_app_running() {
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Start the Python application
start_app() {
    print_status "Starting ODRAS application..."
    
    if is_app_running; then
        print_warning "Application is already running (PID: $(cat $PID_FILE))"
        return 0
    fi
    
    # Check if port is available
    if lsof -Pi :$APP_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_error "Port $APP_PORT is already in use"
        return 1
    fi
    
    # Start the application
    cd "$(dirname "$0")"
    nohup python -m backend.main > "$LOG_FILE" 2>&1 &
    local pid=$!
    
    # Save PID
    echo "$pid" > "$PID_FILE"
    
    # Wait a moment and check if it started successfully
    sleep 2
    if ps -p "$pid" > /dev/null 2>&1; then
        print_success "Application started successfully (PID: $pid)"
        print_status "Logs: tail -f $LOG_FILE"
        print_status "URL: http://localhost:$APP_PORT"
    else
        print_error "Failed to start application"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Stop the Python application
stop_app() {
    print_status "Stopping ODRAS application..."
    
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            kill "$pid"
            sleep 2
            
            # Force kill if still running
            if ps -p "$pid" > /dev/null 2>&1; then
                kill -9 "$pid" 2>/dev/null
            fi
            
            rm -f "$PID_FILE"
            print_success "Application stopped"
        else
            print_warning "Application was not running"
            rm -f "$PID_FILE"
        fi
    else
        print_warning "No PID file found - application may not be running"
    fi
}

# Restart the Python application
restart_app() {
    print_status "Restarting ODRAS application..."
    stop_app
    sleep 1
    start_app
}

# Show application status
show_app_status() {
    print_status "ODRAS Application Status:"
    
    if is_app_running; then
        local pid=$(cat "$PID_FILE")
        print_success "✓ Running (PID: $pid)"
        print_status "Port: $APP_PORT"
        print_status "Logs: $LOG_FILE"
        
        # Check if port is listening
        if lsof -Pi :$APP_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
            print_success "✓ Port $APP_PORT is listening"
        else
            print_warning "⚠ Port $APP_PORT is not listening"
        fi
    else
        print_error "✗ Not running"
    fi
}

# Show application logs
show_app_logs() {
    if [[ -f "$LOG_FILE" ]]; then
        print_status "Showing application logs (Ctrl+C to exit):"
        tail -f "$LOG_FILE"
    else
        print_warning "No log file found"
    fi
}

# Docker Compose functions
start_docker() {
    print_status "Starting Docker Compose services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    if [[ $? -eq 0 ]]; then
        print_success "Docker services started"
        show_docker_status
    else
        print_error "Failed to start Docker services"
        return 1
    fi
}

stop_docker() {
    print_status "Stopping Docker Compose services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" stop
    if [[ $? -eq 0 ]]; then
        print_success "Docker services stopped"
    else
        print_error "Failed to stop Docker services"
        return 1
    fi
}

restart_docker() {
    print_status "Restarting Docker Compose services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" restart
    if [[ $? -eq 0 ]]; then
        print_success "Docker services restarted"
        show_docker_status
    else
        print_error "Failed to restart Docker services"
        return 1
    fi
}

down_docker() {
    print_status "Stopping and removing Docker Compose services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" down
    if [[ $? -eq 0 ]]; then
        print_success "Docker services stopped and removed"
    else
        print_error "Failed to stop Docker services"
        return 1
    fi
}

up_docker() {
    print_status "Starting Docker Compose services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    if [[ $? -eq 0 ]]; then
        print_success "Docker services started"
        show_docker_status
    else
        print_error "Failed to start Docker services"
        return 1
    fi
}

# Show Docker services status
show_docker_status() {
    print_status "Docker Services Status:"
    docker-compose -f "$DOCKER_COMPOSE_FILE" ps
}

# Show Docker logs
show_docker_logs() {
    local service=${1:-""}
    if [[ -n "$service" ]]; then
        print_status "Showing logs for service: $service"
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f "$service"
    else
        print_status "Showing logs for all services (Ctrl+C to exit):"
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f
    fi
}

# Clean up everything
clean_all() {
    print_warning "This will stop and remove everything. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_status "Cleaning up everything..."
        
        # Stop app
        stop_app
        
        # Stop Docker
        down_docker
        
        # Clean up PID and log files
        rm -f "$PID_FILE" "$LOG_FILE"
        
        print_success "Cleanup completed"
    else
        print_status "Cleanup cancelled"
    fi
}

# Show help
show_help() {
    echo "ODRAS Application Management Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start          Start the Python application"
    echo "  stop           Stop the Python application"
    echo "  restart        Restart the Python application"
    echo "  status         Show application status"
    echo "  logs           Show application logs"
    echo ""
    echo "Docker Commands:"
    echo "  up             Start Docker Compose services"
    echo "  down           Stop and remove Docker Compose services"
    echo "  restart-docker Restart Docker Compose services"
    echo "  docker-status  Show Docker services status"
    echo "  docker-logs    Show Docker services logs"
    echo ""
    echo "Utility Commands:"
    echo "  clean          Stop everything and clean up"
    echo "  help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start       # Start the app"
    echo "  $0 up          # Start Docker services"
    echo "  $0 status      # Check status"
    echo "  $0 logs        # View app logs"
}

# Main script logic
main() {
    check_directory
    
    case "${1:-help}" in
        start)
            start_app
            ;;
        stop)
            stop_app
            ;;
        restart)
            restart_app
            ;;
        status)
            show_app_status
            ;;
        logs)
            show_app_logs
            ;;
        up)
            start_docker
            ;;
        down)
            down_docker
            ;;
        restart-docker)
            restart_docker
            ;;
        docker-status)
            show_docker_status
            ;;
        docker-logs)
            show_docker_logs "$2"
            ;;
        clean)
            clean_all
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Unknown command: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
