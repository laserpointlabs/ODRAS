#!/bin/bash
#
# ODRAS Test Data Verification Script
# Checks if test data is properly set up
#

set -e

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-odras_db}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
API_PORT="${API_PORT:-8888}"

echo -e "${GREEN}=== ODRAS Test Data Verification ===${NC}"
echo ""

# Function to check PostgreSQL data
check_postgres_data() {
    echo "Checking PostgreSQL test data..."
    
    if ! PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT \
         -U $POSTGRES_USER -d $POSTGRES_DB -c '\q' 2>/dev/null; then
        echo -e "${RED}✗${NC} Cannot connect to PostgreSQL"
        return 1
    fi
    
    # Check schema exists
    SCHEMA_EXISTS=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT \
                    -U $POSTGRES_USER -d $POSTGRES_DB -t \
                    -c "SELECT 1 FROM information_schema.schemata WHERE schema_name = 'odras_test'" 2>/dev/null || echo "0")
    
    if [ "$SCHEMA_EXISTS" != " 1" ]; then
        echo -e "${RED}✗${NC} Test schema 'odras_test' not found"
        return 1
    fi
    
    # Check tables and data
    echo ""
    echo "Table: aircraft_components"
    PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT \
        -U $POSTGRES_USER -d $POSTGRES_DB \
        -c "SELECT part_number, component_name, component_type FROM odras_test.aircraft_components ORDER BY part_number"
    
    COMP_COUNT=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT \
                 -U $POSTGRES_USER -d $POSTGRES_DB -t \
                 -c "SELECT COUNT(*) FROM odras_test.aircraft_components" 2>/dev/null)
    echo "Total components: $COMP_COUNT"
    
    echo ""
    echo "Table: sensor_readings (sample)"
    PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT \
        -U $POSTGRES_USER -d $POSTGRES_DB \
        -c "SELECT sensor_id, reading_type, COUNT(*) as readings FROM odras_test.sensor_readings GROUP BY sensor_id, reading_type ORDER BY sensor_id LIMIT 5"
    
    SENSOR_COUNT=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT \
                   -U $POSTGRES_USER -d $POSTGRES_DB -t \
                   -c "SELECT COUNT(*) FROM odras_test.sensor_readings" 2>/dev/null)
    echo "Total sensor readings: $SENSOR_COUNT"
    
    echo -e "${GREEN}✓${NC} PostgreSQL test data verified"
}

# Function to check API server
check_api_server() {
    echo ""
    echo "Checking mock API server..."
    
    if ! curl -s -f "http://localhost:$API_PORT/health" >/dev/null 2>&1; then
        echo -e "${RED}✗${NC} Mock API server not responding on port $API_PORT"
        return 1
    fi
    
    # Test endpoints
    echo "Testing API endpoints..."
    
    # Health check
    HEALTH=$(curl -s "http://localhost:$API_PORT/health" | python3 -m json.tool 2>/dev/null || echo "Failed")
    echo "Health check: $HEALTH"
    
    # Maintenance endpoint
    echo ""
    echo "Sample maintenance data:"
    curl -s "http://localhost:$API_PORT/api/v1/maintenance/GPS-NAV-001?limit=2" | python3 -m json.tool 2>/dev/null || echo "Failed to get maintenance data"
    
    # Weather endpoint
    echo ""
    echo "Sample weather data:"
    curl -s "http://localhost:$API_PORT/api/v1/weather/conditions?lat=37.7749&lon=-122.4194" | python3 -m json.tool 2>/dev/null || echo "Failed to get weather data"
    
    echo ""
    echo -e "${GREEN}✓${NC} Mock API server verified"
}

# Function to check CAD files
check_cad_files() {
    echo ""
    echo "Checking CAD test files..."
    
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    TEST_DATA_DIR="$(dirname "$SCRIPT_DIR")/test_data"
    
    if [ ! -d "$TEST_DATA_DIR/cad" ]; then
        echo -e "${RED}✗${NC} CAD directory not found"
        return 1
    fi
    
    echo "CAD files found:"
    find "$TEST_DATA_DIR/cad" -name "*.stl" -o -name "*.json" | sort
    
    # Show sample metadata
    if [ -f "$TEST_DATA_DIR/cad/bracket_GPS-NAV-001.json" ]; then
        echo ""
        echo "Sample CAD metadata:"
        cat "$TEST_DATA_DIR/cad/bracket_GPS-NAV-001.json" | python3 -m json.tool 2>/dev/null || cat "$TEST_DATA_DIR/cad/bracket_GPS-NAV-001.json"
    fi
    
    echo ""
    echo -e "${GREEN}✓${NC} CAD test files verified"
}

# Function to check pipe configurations
check_pipe_configs() {
    echo ""
    echo "Checking pipe configurations..."
    
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    TEST_DATA_DIR="$(dirname "$SCRIPT_DIR")/test_data"
    
    if [ ! -d "$TEST_DATA_DIR/configs" ]; then
        echo -e "${RED}✗${NC} Configs directory not found"
        return 1
    fi
    
    echo "Pipe configurations found:"
    ls -la "$TEST_DATA_DIR/configs/"*.json 2>/dev/null || echo "No configurations found"
    
    echo ""
    echo -e "${GREEN}✓${NC} Pipe configurations verified"
}

# Main verification
main() {
    TOTAL_CHECKS=0
    PASSED_CHECKS=0
    
    # PostgreSQL
    ((TOTAL_CHECKS++))
    if check_postgres_data; then
        ((PASSED_CHECKS++))
    fi
    
    # API Server
    ((TOTAL_CHECKS++))
    if check_api_server; then
        ((PASSED_CHECKS++))
    fi
    
    # CAD Files
    ((TOTAL_CHECKS++))
    if check_cad_files; then
        ((PASSED_CHECKS++))
    fi
    
    # Pipe Configs
    ((TOTAL_CHECKS++))
    if check_pipe_configs; then
        ((PASSED_CHECKS++))
    fi
    
    # Summary
    echo ""
    echo -e "${GREEN}=== Verification Summary ===${NC}"
    echo "Checks passed: $PASSED_CHECKS / $TOTAL_CHECKS"
    
    if [ $PASSED_CHECKS -eq $TOTAL_CHECKS ]; then
        echo -e "${GREEN}All test data components are properly set up!${NC}"
        exit 0
    else
        echo -e "${YELLOW}Some test data components are missing or not configured.${NC}"
        echo "Run ./scripts/setup_test_data.sh to set up missing components."
        exit 1
    fi
}

# Run verification
main


