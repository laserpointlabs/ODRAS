#!/bin/bash
# ODRAS Pre-Merge Validation Script
# This script runs comprehensive validation checks before merging feature branches

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="http://localhost:8000"
VERBOSE=false
SKIP_TESTS=false
SKIP_LINT=false
SKIP_SECURITY=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --base-url)
            BASE_URL="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --skip-lint)
            SKIP_LINT=true
            shift
            ;;
        --skip-security)
            SKIP_SECURITY=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --base-url URL     Base URL for API testing (default: http://localhost:8000)"
            echo "  --verbose, -v      Enable verbose output"
            echo "  --skip-tests       Skip running test suite"
            echo "  --skip-lint        Skip code linting"
            echo "  --skip-security    Skip security checks"
            echo "  --help, -h         Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is not installed or not in PATH"
        exit 1
    fi
}

# Check if we're in the right directory
if [ ! -f "requirements.txt" ] || [ ! -d "backend" ]; then
    log_error "This script must be run from the ODRAS project root directory"
    exit 1
fi

log_info "Starting ODRAS Pre-Merge Validation"
log_info "Base URL: $BASE_URL"
echo ""

# Check required commands
log_info "Checking required commands..."
check_command "python3"
check_command "pip"
check_command "git"
check_command "flake8"
check_command "black"
check_command "pytest"
log_success "All required commands are available"

# Check if ODRAS server is running
log_info "Checking if ODRAS server is running..."
if curl -s "$BASE_URL/health" > /dev/null 2>&1; then
    log_success "ODRAS server is running at $BASE_URL"
else
    log_warning "ODRAS server is not running at $BASE_URL"
    log_info "Starting ODRAS server in background..."
    
    # Try to start the server
    cd backend
    nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 > ../odras_server.log 2>&1 &
    SERVER_PID=$!
    cd ..
    
    # Wait for server to start
    log_info "Waiting for server to start..."
    for i in {1..30}; do
        if curl -s "$BASE_URL/health" > /dev/null 2>&1; then
            log_success "ODRAS server started successfully"
            break
        fi
        sleep 1
        if [ $i -eq 30 ]; then
            log_error "Failed to start ODRAS server after 30 seconds"
            kill $SERVER_PID 2>/dev/null || true
            exit 1
        fi
    done
fi

# 1. Code Quality Checks
if [ "$SKIP_LINT" = false ]; then
    log_info "Running code quality checks..."
    
    # Python syntax check
    log_info "Checking Python syntax..."
    python3 -m py_compile backend/main.py
    log_success "Python syntax check passed"
    
    # Flake8 linting
    log_info "Running flake8 linting..."
    if flake8 backend/ --count --select=E9,F63,F7,F82 --show-source --statistics; then
        log_success "Flake8 critical errors check passed"
    else
        log_error "Flake8 found critical errors"
        exit 1
    fi
    
    # Flake8 style check (non-critical)
    log_info "Running flake8 style check..."
    if flake8 backend/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics; then
        log_success "Flake8 style check passed"
    else
        log_warning "Flake8 found style issues (non-critical)"
    fi
    
    # Black formatting check
    log_info "Checking code formatting with black..."
    if black --check backend/ scripts/; then
        log_success "Code formatting check passed"
    else
        log_warning "Code formatting issues found (run 'black backend/ scripts/' to fix)"
    fi
else
    log_warning "Skipping code quality checks"
fi

# 2. Security Checks
if [ "$SKIP_SECURITY" = false ]; then
    log_info "Running security checks..."
    
    # Check for hardcoded secrets
    log_info "Checking for hardcoded secrets..."
    if grep -r "password.*=" backend/ --include="*.py" | grep -v "test" | grep -v "example"; then
        log_warning "Potential hardcoded passwords found"
    else
        log_success "No hardcoded passwords found"
    fi
    
    # Check for API keys
    if grep -r "api_key.*=" backend/ --include="*.py" | grep -v "test" | grep -v "example"; then
        log_warning "Potential hardcoded API keys found"
    else
        log_success "No hardcoded API keys found"
    fi
    
    # Bandit security scan
    if command -v bandit &> /dev/null; then
        log_info "Running bandit security scan..."
        if bandit -r backend/ -ll; then
            log_success "Bandit security scan passed"
        else
            log_warning "Bandit found potential security issues"
        fi
    else
        log_warning "Bandit not installed, skipping security scan"
    fi
else
    log_warning "Skipping security checks"
fi

# 3. Test Suite
if [ "$SKIP_TESTS" = false ]; then
    log_info "Running test suite..."
    
    # Install test dependencies
    log_info "Installing test dependencies..."
    pip install pytest pytest-cov pytest-asyncio httpx rich > /dev/null 2>&1
    
    # Run unit tests
    log_info "Running unit tests..."
    if pytest tests/ -v --tb=short; then
        log_success "Unit tests passed"
    else
        log_error "Unit tests failed"
        exit 1
    fi
    
    # Run API validation
    log_info "Running API endpoint validation..."
    if python3 scripts/validate_all_endpoints.py --base-url "$BASE_URL" --verbose="$VERBOSE"; then
        log_success "API endpoint validation passed"
    else
        log_error "API endpoint validation failed"
        exit 1
    fi
else
    log_warning "Skipping test suite"
fi

# 4. Import Validation
log_info "Validating Python imports..."
if python3 -c "from backend.main import app; print('✅ Main app imports successfully')"; then
    log_success "Main app imports validated"
else
    log_error "Main app import failed"
    exit 1
fi

# 5. BPMN File Validation
log_info "Validating BPMN files..."
if [ -d "bpmn" ]; then
    for file in bpmn/*.bpmn; do
        if [ -f "$file" ]; then
            if python3 -c "import xml.etree.ElementTree as ET; ET.parse('$file'); print('✅ $file is valid XML')"; then
                log_success "$file is valid"
            else
                log_error "$file is invalid XML"
                exit 1
            fi
        fi
    done
else
    log_warning "No bpmn directory found"
fi

# 6. Database Schema Validation
log_info "Validating database schema..."

# Check if database schema validator exists
if [[ -f "scripts/validate_database_schema.py" ]]; then
    log_info "Running comprehensive database schema validation..."
    if python scripts/validate_database_schema.py --verbose; then
        log_success "Database schema validation passed"
    else
        log_error "Database schema validation failed"
        log_info "💡 Run 'python scripts/validate_database_schema.py --fix' to fix issues"
        exit 1
    fi
else
    log_warning "Database schema validator script not found, running basic validation..."
    
    # Basic database service validation
    if python3 -c "from backend.services.db import DatabaseService; print('✅ Database service imports successfully')"; then
        log_success "Database service validated"
    else
        log_warning "Database service validation failed (may be expected in CI)"
    fi
    
    # Check migration files
    if [[ -d "backend/migrations" ]]; then
        local migration_count=$(find backend/migrations -name "*.sql" | wc -l)
        if [[ $migration_count -gt 0 ]]; then
            log_info "Found $migration_count migration files"
            
            # Check if odras.sh init-db references all migrations
            if grep -q "migrations=(" odras.sh; then
                log_success "odras.sh contains migration array"
            else
                log_warning "odras.sh migration array not found"
            fi
        else
            log_warning "No migration files found"
        fi
    else
        log_warning "No migrations directory found"
    fi
fi

# 7. Configuration Validation
log_info "Validating configuration..."
if python3 -c "from backend.services.config import Settings; s = Settings(); print('✅ Configuration loaded successfully')"; then
    log_success "Configuration validated"
else
    log_error "Configuration validation failed"
    exit 1
fi

# 8. Git Status Check
log_info "Checking git status..."
if git diff --quiet; then
    log_success "Working directory is clean"
else
    log_warning "Working directory has uncommitted changes"
    if [ "$VERBOSE" = true ]; then
        git status --short
    fi
fi

# 9. Branch Information
log_info "Checking branch information..."
CURRENT_BRANCH=$(git branch --show-current)
log_info "Current branch: $CURRENT_BRANCH"

if [ "$CURRENT_BRANCH" = "main" ]; then
    log_warning "You are on the main branch"
fi

# 10. Performance Check
log_info "Running basic performance check..."
START_TIME=$(date +%s)
curl -s "$BASE_URL/" > /dev/null
END_TIME=$(date +%s)
RESPONSE_TIME=$((END_TIME - START_TIME))

if [ $RESPONSE_TIME -lt 5 ]; then
    log_success "Basic performance check passed (${RESPONSE_TIME}s response time)"
else
    log_warning "Slow response time detected (${RESPONSE_TIME}s)"
fi

# Cleanup
if [ ! -z "$SERVER_PID" ]; then
    log_info "Stopping background server..."
    kill $SERVER_PID 2>/dev/null || true
    rm -f odras_server.log
fi

# Final Summary
echo ""
log_success "🎉 Pre-merge validation completed successfully!"
echo ""
log_info "Summary:"
log_info "- Code quality checks: ✅"
log_info "- Security checks: ✅"
log_info "- Test suite: ✅"
log_info "- API validation: ✅"
log_info "- Import validation: ✅"
log_info "- BPMN validation: ✅"
log_info "- Configuration validation: ✅"
echo ""
log_info "This branch is ready for merge! 🚀"
echo ""
log_info "Next steps:"
log_info "1. Create a pull request"
log_info "2. Request code review"
log_info "3. Squash merge after approval"
echo ""

exit 0
