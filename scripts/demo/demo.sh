#!/bin/bash

# ODRAS Demo Management Script
# Usage: ./demo.sh [command]
# Commands: start, stop, restart, status, logs, logs-watch, clean

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEMO_DIR="$SCRIPT_DIR"

HTTP_PORT=8082
WS_PORT=8081
LLM_PORT=8083

HTTP_PID_FILE="/tmp/demo_http.pid"
WS_PID_FILE="/tmp/demo_ws.pid"
LLM_PID_FILE="/tmp/demo_llm.pid"

HTTP_LOG="/tmp/demo_http.log"
WS_LOG="/tmp/demo_ws.log"
LLM_LOG="/tmp/llm_service.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

print_header() {
    echo -e "${CYAN}$1${NC}"
}

# Check if ODRAS is running
check_odras() {
    if ! curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        print_error "ODRAS is not running on port 8000"
        print_status "Start it with: ./odras.sh start"
        return 1
    fi
    return 0
}

# Get PID from PID file or process
get_pid() {
    local pid_file=$1
    local process_pattern=$2
    
    # First try to find by process pattern (more reliable)
    # Filter out bash wrappers by checking the actual command
    if [[ -n "$process_pattern" ]]; then
        local pids=$(pgrep -f "$process_pattern")
        local actual_pid=""
        for pid in $pids; do
            # Check if this is actually the Python process, not a bash wrapper
            local cmd=$(ps -p "$pid" -o cmd= 2>/dev/null)
            if [[ "$cmd" == *"python"* ]] && [[ "$cmd" != *"bash"* ]]; then
                actual_pid="$pid"
                break
            fi
        done
        
        if [[ -n "$actual_pid" ]] && ps -p "$actual_pid" > /dev/null 2>&1; then
            # Update PID file with correct PID
            echo "$actual_pid" > "$pid_file"
            echo "$actual_pid"
            return 0
        fi
    fi
    
    # Fall back to PID file
    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        # Verify it's actually the right process
        local cmd=$(ps -p "$pid" -o cmd= 2>/dev/null)
        if [[ -n "$cmd" ]] && [[ "$cmd" == *"python"* ]] && [[ "$cmd" != *"bash"* ]]; then
            echo "$pid"
            return 0
        else
            rm -f "$pid_file"
        fi
    fi
    
    return 1
}

# Check if port is in use
is_port_in_use() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

# Start HTTP server
start_http() {
    print_status "Starting HTTP server on port $HTTP_PORT..."
    
    if is_port_in_use $HTTP_PORT; then
        print_warning "Port $HTTP_PORT is already in use"
        local existing_pid=$(lsof -ti :$HTTP_PORT)
        print_status "Port $HTTP_PORT is used by PID: $existing_pid"
        return 1
    fi
    
    cd "$DEMO_DIR"
    python3 -m http.server $HTTP_PORT --directory static > "$HTTP_LOG" 2>&1 &
    local pid=$!
    
    # Wait a moment and find the actual Python process
    sleep 1
    local actual_pid=$(pgrep -f "http.server.*$HTTP_PORT" | head -1)
    if [[ -n "$actual_pid" ]]; then
        echo "$actual_pid" > "$HTTP_PID_FILE"
        print_success "HTTP server started (PID: $actual_pid, Port: $HTTP_PORT)"
        return 0
    else
        print_error "HTTP server failed to start"
        rm -f "$HTTP_PID_FILE"
        return 1
    fi
}

# Start WebSocket server
start_ws() {
    print_status "Starting WebSocket server on port $WS_PORT..."
    
    if is_port_in_use $WS_PORT; then
        print_warning "Port $WS_PORT is already in use"
        local existing_pid=$(lsof -ti :$WS_PORT)
        print_status "Port $WS_PORT is used by PID: $existing_pid"
        return 1
    fi
    
    cd "$DEMO_DIR"
    
    # Use venv Python if available, otherwise system Python
    local python_cmd="python3"
    if [[ -f "$PROJECT_ROOT/.venv/bin/python3" ]]; then
        python_cmd="$PROJECT_ROOT/.venv/bin/python3"
    fi
    
    "$python_cmd" visualization_server.py --ws-port $WS_PORT --websocket-only > "$WS_LOG" 2>&1 &
    local pid=$!
    
    # Wait a moment and find the actual Python process
    sleep 2
    local actual_pid=$(pgrep -f "visualization_server.py.*$WS_PORT" | head -1)
    if [[ -n "$actual_pid" ]] && ps -p "$actual_pid" > /dev/null 2>&1; then
        echo "$actual_pid" > "$WS_PID_FILE"
        print_success "WebSocket server started (PID: $actual_pid, Port: $WS_PORT)"
        return 0
    else
        print_error "WebSocket server failed to start"
        rm -f "$WS_PID_FILE"
        print_status "Check logs: tail -20 $WS_LOG"
        return 1
    fi
}

# Start LLM debug service
start_llm() {
    print_status "Starting LLM service on port $LLM_PORT..."
    
    if is_port_in_use $LLM_PORT; then
        print_warning "Port $LLM_PORT is already in use"
        local existing_pid=$(lsof -ti :$LLM_PORT)
        print_status "Port $LLM_PORT is used by PID: $existing_pid"
        return 1
    fi
    
    cd "$PROJECT_ROOT"
    
    # Use venv Python if available, otherwise system Python
    local python_cmd="python3"
    if [[ -f "$PROJECT_ROOT/.venv/bin/python3" ]]; then
        python_cmd="$PROJECT_ROOT/.venv/bin/python3"
    fi
    
    cd "$DEMO_DIR"
    nohup "$python_cmd" llm_service.py > "$LLM_LOG" 2>&1 &
    local pid=$!
    
    # Wait a moment and find the actual Python process
    sleep 2
    local actual_pid=$(pgrep -f "llm_service.py" | head -1)
    if [[ -n "$actual_pid" ]] && ps -p "$actual_pid" > /dev/null 2>&1; then
        echo "$actual_pid" > "$LLM_PID_FILE"
        # Check if service is responding
        if curl -s http://localhost:$LLM_PORT/health > /dev/null 2>&1; then
            print_success "LLM service started (PID: $actual_pid, Port: $LLM_PORT)"
            return 0
        else
            print_warning "LLM service started but not responding yet (PID: $actual_pid)"
            return 0
        fi
    else
        print_error "LLM service failed to start"
        rm -f "$LLM_PID_FILE"
        print_status "Check logs: tail -20 $LLM_LOG"
        return 1
    fi
}

# Stop service by PID file
stop_service() {
    local service_name=$1
    local pid_file=$2
    local process_pattern=$3
    
    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            print_status "Stopping $service_name (PID: $pid)..."
            kill "$pid" 2>/dev/null
            sleep 1
            if ps -p "$pid" > /dev/null 2>&1; then
                print_warning "Force killing $service_name..."
                kill -9 "$pid" 2>/dev/null
            fi
            rm -f "$pid_file"
            print_success "$service_name stopped"
            return 0
        else
            rm -f "$pid_file"
        fi
    fi
    
    # Try to find and kill by process pattern
    if [[ -n "$process_pattern" ]]; then
        local pids=$(pgrep -f "$process_pattern")
        if [[ -n "$pids" ]]; then
            print_status "Stopping $service_name (found by pattern)..."
            echo "$pids" | xargs kill 2>/dev/null
            sleep 1
            local remaining=$(pgrep -f "$process_pattern")
            if [[ -n "$remaining" ]]; then
                echo "$remaining" | xargs kill -9 2>/dev/null
            fi
            print_success "$service_name stopped"
            return 0
        fi
    fi
    
    print_warning "$service_name is not running"
    return 1
}

# Start all services
start_all() {
    print_header "=========================================="
    print_header "Starting ODRAS Demo Services"
    print_header "=========================================="
    echo ""
    
    if ! check_odras; then
        exit 1
    fi
    
    local failed=0
    
    start_http || failed=1
    start_ws || failed=1
    start_llm || failed=1
    
    echo ""
    if [[ $failed -eq 0 ]]; then
        print_success "All demo services started successfully!"
        echo ""
        print_status "Services:"
        echo "  • HTTP Server:      http://localhost:$HTTP_PORT"
        echo "  • WebSocket Server: ws://localhost:$WS_PORT"
        echo "  • LLM Service:      http://localhost:$LLM_PORT"
        echo ""
        print_status "Demo URLs:"
        echo "  • Lattice Demo:     http://localhost:$HTTP_PORT/lattice_demo.html"
        echo "  • Intelligent Demo: http://localhost:$HTTP_PORT/intelligent_lattice_demo.html"
        echo ""
        print_status "View logs: ./demo.sh logs"
        print_status "Stop all:  ./demo.sh stop"
    else
        print_error "Some services failed to start"
        exit 1
    fi
}

# Stop all services
stop_all() {
    print_header "=========================================="
    print_header "Stopping ODRAS Demo Services"
    print_header "=========================================="
    echo ""
    
    stop_service "HTTP server" "$HTTP_PID_FILE" "http.server.*$HTTP_PORT"
    stop_service "WebSocket server" "$WS_PID_FILE" "visualization_server.py"
    stop_service "LLM service" "$LLM_PID_FILE" "llm_service.py"
    
    echo ""
    print_success "All demo services stopped"
}

# Restart all services
restart_all() {
    print_header "=========================================="
    print_header "Restarting ODRAS Demo Services"
    print_header "=========================================="
    echo ""
    
    stop_all
    sleep 2
    start_all
}

# Show status of all services
show_status() {
    print_header "=========================================="
    print_header "ODRAS Demo Services Status"
    print_header "=========================================="
    echo ""
    
    # Check ODRAS
    if check_odras; then
        print_success "ODRAS API: Running (port 8000)"
    else
        print_error "ODRAS API: Not running"
    fi
    echo ""
    
    # Check HTTP server
    local http_pid=$(get_pid "$HTTP_PID_FILE" "http.server.*$HTTP_PORT")
    if [[ -n "$http_pid" ]]; then
        if is_port_in_use $HTTP_PORT; then
            print_success "HTTP Server: Running (PID: $http_pid, Port: $HTTP_PORT)"
            echo "  URL: http://localhost:$HTTP_PORT"
        else
            print_warning "HTTP Server: PID exists but port not listening"
        fi
    else
        print_error "HTTP Server: Not running"
    fi
    echo ""
    
    # Check WebSocket server
    local ws_pid=$(get_pid "$WS_PID_FILE" "visualization_server.py")
    if [[ -n "$ws_pid" ]]; then
        if is_port_in_use $WS_PORT; then
            print_success "WebSocket Server: Running (PID: $ws_pid, Port: $WS_PORT)"
            echo "  URL: ws://localhost:$WS_PORT"
        else
            print_warning "WebSocket Server: PID exists but port not listening"
        fi
    else
        print_error "WebSocket Server: Not running"
    fi
    echo ""
    
    # Check LLM service
    local llm_pid=$(get_pid "$LLM_PID_FILE" "llm_service.py")
    if [[ -n "$llm_pid" ]]; then
        if is_port_in_use $LLM_PORT; then
            if curl -s http://localhost:$LLM_PORT/health > /dev/null 2>&1; then
                print_success "LLM Service: Running (PID: $llm_pid, Port: $LLM_PORT)"
                local health=$(curl -s http://localhost:$LLM_PORT/health 2>/dev/null)
                echo "  Health: $health"
            else
                print_warning "LLM Service: Running but not responding"
            fi
        else
            print_warning "LLM Service: PID exists but port not listening"
        fi
    else
        print_error "LLM Service: Not running"
    fi
    echo ""
}

# Show logs
show_logs() {
    local service=${1:-all}
    
    case "$service" in
        http)
            print_header "HTTP Server Logs"
            tail -50 "$HTTP_LOG"
            ;;
        ws|websocket)
            print_header "WebSocket Server Logs"
            tail -50 "$WS_LOG"
            ;;
        llm)
            print_header "LLM Debug Service Logs"
            tail -50 "$LLM_LOG"
            ;;
        all|*)
            print_header "All Demo Service Logs (last 20 lines each)"
            echo ""
            print_status "=== HTTP Server ==="
            tail -20 "$HTTP_LOG" 2>/dev/null || echo "No logs available"
            echo ""
            print_status "=== WebSocket Server ==="
            tail -20 "$WS_LOG" 2>/dev/null || echo "No logs available"
            echo ""
            print_status "=== LLM Service ==="
            tail -20 "$LLM_LOG" 2>/dev/null || echo "No logs available"
            ;;
    esac
}

# Watch logs
watch_logs() {
    local service=${1:-all}
    
    case "$service" in
        http)
            tail -f "$HTTP_LOG"
            ;;
        ws|websocket)
            tail -f "$WS_LOG"
            ;;
        llm)
            tail -f "$LLM_LOG"
            ;;
        all|*)
            print_status "Watching all logs (Ctrl+C to stop)..."
            tail -f "$HTTP_LOG" "$WS_LOG" "$LLM_LOG" 2>/dev/null
            ;;
    esac
}

# Clean up old processes
clean_all() {
    print_header "=========================================="
    print_header "Cleaning Up Demo Services"
    print_header "=========================================="
    echo ""
    
    print_status "Killing old processes..."
    
    # Kill by PID files first
    [[ -f "$HTTP_PID_FILE" ]] && kill $(cat "$HTTP_PID_FILE") 2>/dev/null || true
    [[ -f "$WS_PID_FILE" ]] && kill $(cat "$WS_PID_FILE") 2>/dev/null || true
    [[ -f "$LLM_PID_FILE" ]] && kill $(cat "$LLM_PID_FILE") 2>/dev/null || true
    
    # Kill by process patterns
    pkill -f "http.server.*$HTTP_PORT" 2>/dev/null || true
    pkill -f "visualization_server.py" 2>/dev/null || true
    pkill -f "llm_service.py" 2>/dev/null || true
    
    sleep 1
    
    # Force kill if still running
    pkill -9 -f "http.server.*$HTTP_PORT" 2>/dev/null || true
    pkill -9 -f "visualization_server.py" 2>/dev/null || true
    pkill -9 -f "llm_service.py" 2>/dev/null || true
    
    # Remove PID files
    rm -f "$HTTP_PID_FILE" "$WS_PID_FILE" "$LLM_PID_FILE"
    
    print_success "Cleanup complete"
}

# Show usage
show_usage() {
    echo "ODRAS Demo Management Script"
    echo ""
    echo "Usage: ./demo.sh [command]"
    echo ""
    echo "Commands:"
    echo "  start          Start all demo services"
    echo "  stop           Stop all demo services"
    echo "  restart        Restart all demo services"
    echo "  status         Show status of all services"
    echo "  logs [service] Show logs (http|ws|llm|all)"
    echo "  logs-watch [service] Watch logs continuously (http|ws|llm|all)"
    echo "  clean          Clean up old processes and PID files"
    echo ""
    echo "Services:"
    echo "  • HTTP Server (port $HTTP_PORT) - Static file server"
    echo "  • WebSocket Server (port $WS_PORT) - Visualization updates"
    echo "  • LLM Service (port $LLM_PORT) - LLM lattice generation"
    echo ""
    echo "Examples:"
    echo "  ./demo.sh start              # Start all services"
    echo "  ./demo.sh status             # Check status"
    echo "  ./demo.sh logs llm           # Show LLM service logs"
    echo "  ./demo.sh logs-watch all     # Watch all logs"
    echo "  ./demo.sh stop               # Stop all services"
}

# Main command handler
main() {
    cd "$PROJECT_ROOT"
    
    case "${1:-}" in
        start)
            start_all
            ;;
        stop)
            stop_all
            ;;
        restart)
            restart_all
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "${2:-all}"
            ;;
        logs-watch|watch)
            watch_logs "${2:-all}"
            ;;
        clean)
            clean_all
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            if [[ -n "${1:-}" ]]; then
                print_error "Unknown command: $1"
                echo ""
            fi
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
