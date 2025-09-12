#!/bin/bash

# ODRAS Application Management Script
# Usage: ./odras.sh [command]
# Commands: start, stop, restart, status, logs, down, up, clean, clean-all, init-db

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
        fi
    fi
    
    # Check if any process is using our port
    if lsof -Pi :$APP_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
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
        
        # Start external workers for BPMN processing
        sleep 5  # Give app time to fully start
        start_external_workers
    else
        print_error "Failed to start application"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Stop the Python application
stop_app() {
    print_status "Stopping ODRAS application..."
    
    # Stop external workers first
    stop_external_workers
    
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
    
    # First, kill any process using port 8000
    print_status "Checking for processes on port $APP_PORT..."
    local port_pids=$(lsof -ti tcp:$APP_PORT 2>/dev/null)
    if [[ -n "$port_pids" ]]; then
        print_status "Found processes on port $APP_PORT, killing them..."
        echo "$port_pids" | xargs kill -9 2>/dev/null || true
        sleep 1
        
        # Verify port is free
        if lsof -ti tcp:$APP_PORT >/dev/null 2>&1; then
            print_warning "Some processes may still be using port $APP_PORT"
        else
            print_success "Port $APP_PORT is now free"
        fi
    else
        print_status "No processes found on port $APP_PORT"
    fi
    
    # Now do the regular stop
    stop_app
    sleep 1
    start_app
}

# Show application status
show_app_status() {
    print_status "ODRAS Application Status:"
    
    if is_app_running; then
        if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        print_success "✓ Running (PID: $pid)"
        else
            local port_pid=$(lsof -Pi :$APP_PORT -sTCP:LISTEN -t 2>/dev/null | head -1)
            print_success "✓ Running (PID: ${port_pid:-unknown})"
            print_warning "⚠ Started outside of odras.sh (no PID file)"
        fi
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
        print_warning "No log file found at $LOG_FILE"
        
        # Check if app is running and suggest alternatives
        if is_app_running; then
            print_status "Application is running but was likely started outside of odras.sh"
            print_status "Available log viewing options:"
            
            # Check for common log locations
            local alt_logs_found=false
            
            # Check for systemd/journal logs
            if systemctl --user is-active odras >/dev/null 2>&1 || systemctl is-active odras >/dev/null 2>&1; then
                print_status "  1. View systemd logs: journalctl -u odras -f"
                alt_logs_found=true
            fi
            
            # Check for Docker logs if running in container
            local docker_containers=$(docker ps --format "{{.Names}}" 2>/dev/null | grep -i odras | head -1)
            if [[ -n "$docker_containers" ]]; then
                print_status "  2. View Docker logs: docker logs -f [container_name]"
                print_status "     Available containers: $(docker ps --format "{{.Names}}" 2>/dev/null | grep -i odras | tr '\n' ' ')"
                alt_logs_found=true
            fi
            
            # Check for nohup.out in current directory
            if [[ -f "nohup.out" ]]; then
                print_status "  3. View nohup output: tail -f nohup.out"
                alt_logs_found=true
            fi
            
            # Always offer restart option for proper logging
            local main_pid=$(ps aux | grep "python -m backend.main" | grep -v grep | awk '{print $2}' | head -1)
            if [[ -n "$main_pid" ]]; then
                local option_num=$((alt_logs_found == true ? 4 : 1))
                print_status "  $option_num. Restart app with odras.sh to generate logs: ./odras.sh restart"
                alt_logs_found=true
            fi
            
            if [[ "$alt_logs_found" == "false" ]]; then
                print_status "  1. Restart the app with odras.sh to generate logs: ./odras.sh restart"
            fi
        else
            print_status "Application is not running. Start it to generate logs:"
            print_status "  ./odras.sh start"
        fi
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

# Clean all databases (data only, keeps containers running)
clean_databases() {
    # Check if -y flag was passed
    local skip_confirm=false
    if [[ "$1" == "-y" ]] || [[ "$SKIP_CONFIRM" == "true" ]]; then
        skip_confirm=true
    fi
    
    if [[ "$skip_confirm" == "false" ]]; then
        print_warning "This will DELETE ALL DATA from all databases. Are you sure? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            print_status "Database cleaning cancelled"
            return
        fi
    else
        print_status "Cleaning all databases (auto-confirmed)..."
    fi
    
    if [[ true ]]; then
        print_status "Cleaning all databases..."
        
        # Check if Docker services are running
        if ! docker-compose -f "$DOCKER_COMPOSE_FILE" ps | grep -q "Up"; then
            print_status "Starting Docker services first..."
            start_docker
            print_status "Waiting for services to initialize..."
            sleep 10
        fi
        
        # Clean PostgreSQL
        clean_postgresql
        
        # Clean Qdrant
        clean_qdrant
        
        # Clean Neo4j
        clean_neo4j
        
        # Clean Fuseki
        clean_fuseki
        
        # Clean MinIO
        clean_minio
        
        # Clean local storage
        clean_local_storage
        
        # Clean browser local storage data
        clean_browser_storage
        
        print_success "All databases cleaned successfully!"
        
        # DO NOT create users here - that's what init-db is for!
        # Just recreate empty collections
        
        # Recreate Qdrant collections
        print_status "Recreating Qdrant collections..."
        if curl -s http://localhost:6333/collections >/dev/null 2>&1; then
            # Create knowledge_chunks collection (384 dimensions for sentence-transformers)
            curl -s -X PUT "http://localhost:6333/collections/knowledge_chunks" \
                 -H "Content-Type: application/json" \
                 -d '{"vectors": {"size": 384, "distance": "Cosine"}}' >/dev/null 2>&1
            
            # Create knowledge_large collection (1536 dimensions for OpenAI embeddings)
            curl -s -X PUT "http://localhost:6333/collections/knowledge_large" \
                 -H "Content-Type: application/json" \
                 -d '{"vectors": {"size": 1536, "distance": "Cosine"}}' >/dev/null 2>&1
                 
            # Create odras_requirements collection (384 dimensions)
            curl -s -X PUT "http://localhost:6333/collections/odras_requirements" \
                 -H "Content-Type: application/json" \
                 -d '{"vectors": {"size": 384, "distance": "Cosine"}}' >/dev/null 2>&1
            
            print_success "✓ Recreated Qdrant collections"
        else
            print_warning "⚠ Could not connect to Qdrant to recreate collections"
        fi
        
        print_success "🎉 All databases cleaned!"
        print_status "⚠️  Databases are now empty - run './odras.sh init-db' to create users and default project"
        print_status "💡 After init-db, restart the application: ./odras.sh restart"
    else
        print_status "Database cleaning cancelled"
    fi
}

# Clean PostgreSQL database
clean_postgresql() {
    print_status "Cleaning PostgreSQL database..."
    
    # Try to connect and clean database
    if docker exec odras_postgres psql -U postgres -d odras -c "SELECT 1;" >/dev/null 2>&1; then
        # Drop all tables in correct order (respecting foreign key constraints)
        docker exec odras_postgres psql -U postgres -d odras -c "
        -- Disable foreign key checks temporarily
        SET session_replication_role = replica;
        
        -- Drop knowledge management tables
        DROP TABLE IF EXISTS knowledge_processing_jobs CASCADE;
        DROP TABLE IF EXISTS knowledge_relationships CASCADE;
        DROP TABLE IF EXISTS knowledge_chunks CASCADE;
        DROP TABLE IF EXISTS knowledge_assets CASCADE;
        
        -- Drop file tables
        DROP TABLE IF EXISTS file_content CASCADE;
        DROP TABLE IF EXISTS files CASCADE;
        
        -- Drop project and user tables
        DROP TABLE IF EXISTS project_members CASCADE;
        DROP TABLE IF EXISTS projects CASCADE;
        DROP TABLE IF EXISTS users CASCADE;
        
        -- Drop functions
        DROP FUNCTION IF EXISTS update_files_updated_at CASCADE;
        DROP FUNCTION IF EXISTS update_updated_at_column CASCADE;
        
        -- Re-enable foreign key checks
        SET session_replication_role = DEFAULT;
        "
        
        print_success "✓ PostgreSQL cleaned"
    else
        print_warning "⚠ Could not connect to PostgreSQL"
    fi
}

# Clean Qdrant vector database
clean_qdrant() {
    print_status "Cleaning Qdrant vector database..."
    
    # Get all collections and delete them
    local collections=$(curl -s http://localhost:6333/collections 2>/dev/null | jq -r '.result.collections[].name' 2>/dev/null)
    
    if [[ $? -eq 0 ]] && [[ -n "$collections" ]]; then
        for collection in $collections; do
            if [[ "$collection" != "null" ]] && [[ -n "$collection" ]]; then
                print_status "  Deleting collection: $collection"
                curl -s -X DELETE "http://localhost:6333/collections/$collection" >/dev/null 2>&1
            fi
        done
        print_success "✓ Qdrant cleaned"
    else
        print_warning "⚠ Could not connect to Qdrant or no collections found"
    fi
}

# Clean Neo4j graph database
clean_neo4j() {
    print_status "Cleaning Neo4j graph database..."
    
    # Delete all nodes and relationships
    if docker exec odras_neo4j cypher-shell -u neo4j -p testpassword "RETURN 1;" >/dev/null 2>&1; then
        docker exec odras_neo4j cypher-shell -u neo4j -p testpassword "
        // Delete all relationships and nodes
        MATCH (n) DETACH DELETE n;
        
        // Drop all constraints
        CALL apoc.schema.assert({},{},true) YIELD label, key 
        RETURN label, key;
        " >/dev/null 2>&1
        
        print_success "✓ Neo4j cleaned"
    else
        print_warning "⚠ Could not connect to Neo4j"
    fi
}

# Initialize Fuseki RDF store
init_fuseki() {
    print_status "Setting up Fuseki RDF datasets..."
    
    # Wait for Fuseki to be ready
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:3030/$/ping >/dev/null 2>&1; then
            print_success "  ✓ Fuseki is ready"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            print_warning "  ⚠ Fuseki may not be ready, continuing anyway..."
            return
        fi
        
        sleep 2
        attempt=$((attempt + 1))
    done
    
    # Create ODRAS dataset for ontologies
    print_status "  Creating 'odras' dataset for ontology storage..."
    
    # First check if dataset already exists
    local existing_datasets=$(curl -s http://localhost:3030/$/datasets 2>/dev/null)
    
    if echo "$existing_datasets" | grep -q '"name":"odras"'; then
        print_status "  Dataset 'odras' already exists, clearing it..."
        curl -s -X POST "http://localhost:3030/odras/update" \
             -H "Content-Type: application/sparql-update" \
             -d "DELETE WHERE { ?s ?p ?o }" >/dev/null 2>&1
    else
        # Create new dataset
        print_status "  Creating new 'odras' dataset..."
        curl -s -X POST "http://localhost:3030/$/datasets" \
             -H "Content-Type: application/x-www-form-urlencoded" \
             -d "dbName=odras&dbType=tdb2" >/dev/null 2>&1
    fi
    
    # Verify dataset creation
    local verification=$(curl -s http://localhost:3030/$/server 2>/dev/null)
    if echo "$verification" | grep -q '"/odras"'; then
        print_success "  ✓ Fuseki 'odras' dataset ready for ontology storage"
    else
        print_warning "  ⚠ Fuseki dataset creation may have failed"
        print_status "  Debug: $verification"
    fi
}

# Deploy BPMN workflows to Camunda
deploy_bpmn_workflows() {
    print_status "Deploying BPMN workflows to Camunda..."
    
    # Wait for Camunda to be ready
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:8080/camunda/ >/dev/null 2>&1; then
            print_success "  ✓ Camunda is ready"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            print_warning "  ⚠ Camunda may not be ready, skipping BPMN deployment..."
            return
        fi
        
        sleep 2
        attempt=$((attempt + 1))
    done
    
    # Deploy all BPMN workflow files
    local bpmn_files=(
        "automatic_knowledge_processing.bpmn:ODRAS Automatic Knowledge Processing"
        "rag_query_pipeline.bpmn:ODRAS RAG Query Pipeline"
        "requirements_extraction.bpmn:ODRAS Requirements Extraction"
        "add_to_knowledge.bpmn:ODRAS Add to Knowledge"
        "knowledge_enrichment.bpmn:ODRAS Knowledge Enrichment"
    )
    
    local deployed_count=0
    
    for bpmn_entry in "${bpmn_files[@]}"; do
        local bpmn_file=$(echo "$bpmn_entry" | cut -d':' -f1)
        local deployment_name=$(echo "$bpmn_entry" | cut -d':' -f2)
        
        if [[ -f "bpmn/$bpmn_file" ]]; then
            print_status "  Deploying $bpmn_file..."
            
            local deployment_response=$(curl -s -X POST "http://localhost:8080/engine-rest/deployment/create" \
                -F "deployment-name=$deployment_name" \
                -F "deployment-source=ODRAS Init-DB" \
                -F "$bpmn_file=@bpmn/$bpmn_file" 2>/dev/null)
            
            if echo "$deployment_response" | grep -q '"id"'; then
                print_success "    ✓ $bpmn_file deployed successfully"
                deployed_count=$((deployed_count + 1))
            else
                print_warning "    ⚠ $bpmn_file deployment may have failed"
            fi
        else
            print_warning "    ⚠ BPMN file not found: bpmn/$bpmn_file"
        fi
    done
    
    print_success "✓ Deployed $deployed_count BPMN workflows to Camunda"
    print_status "  🖥️  Monitor workflows at: http://localhost:8080/camunda/app/cockpit/"
    
    # Start the external workers for BPMN task processing
    print_status "Starting external workers for BPMN task processing..."
    start_external_workers
}

# Start external workers for BPMN task processing
start_external_workers() {
    print_status "Starting BPMN external workers..."
    
    # Start the complex worker (handles RAG query process and other advanced tasks)
    start_complex_worker
    
    # Start the simple worker (handles file upload processing tasks)
    start_simple_worker
}

# Start complex external worker (RAG query process support)
start_complex_worker() {
    print_status "Starting complex external worker (RAG query process support)..."
    
    local worker_script="scripts/run_external_task_worker.py"
    local worker_log="/tmp/odras_complex_worker.log"
    local worker_pid_file="/tmp/odras_complex_worker.pid"
    
    if [[ ! -f "$worker_script" ]]; then
        print_warning "  ⚠ External worker script not found: $worker_script"
        return
    fi
    
    # Kill existing complex worker if running
    if [[ -f "$worker_pid_file" ]]; then
        local old_pid=$(cat "$worker_pid_file")
        if kill -0 "$old_pid" 2>/dev/null; then
            print_status "  Stopping existing complex worker (PID: $old_pid)..."
            kill "$old_pid" 2>/dev/null
            sleep 2
        fi
        rm -f "$worker_pid_file"
    fi
    
    # Start new complex worker in background
    print_status "  Starting complex worker daemon..."
    nohup python3 "$worker_script" > "$worker_log" 2>&1 &
    local worker_pid=$!
    
    # Save PID for management
    echo "$worker_pid" > "$worker_pid_file"
    
    # Verify worker started
    sleep 3
    if kill -0 "$worker_pid" 2>/dev/null; then
        print_success "  ✓ Complex worker started (PID: $worker_pid)"
        print_status "    📋 Handles: RAG query process, knowledge management, document ingestion"
        print_status "    📄 Logs: $worker_log"
    else
        print_warning "  ⚠ Complex worker may have failed to start"
        if [[ -f "$worker_log" ]]; then
            print_status "    Error: $(tail -n 1 "$worker_log")"
        fi
    fi
}

# Start simple external worker (file upload processing)
start_simple_worker() {
    print_status "Starting simple external worker (file upload processing)..."
    
    local worker_script="scripts/simple_external_worker.py"
    local worker_log="/tmp/odras_simple_worker.log"
    local worker_pid_file="/tmp/odras_simple_worker.pid"
    
    if [[ ! -f "$worker_script" ]]; then
        print_warning "  ⚠ Simple worker script not found: $worker_script"
        return
    fi
    
    # Kill existing simple worker if running
    if [[ -f "$worker_pid_file" ]]; then
        local old_pid=$(cat "$worker_pid_file")
        if kill -0 "$old_pid" 2>/dev/null; then
            print_status "  Stopping existing simple worker (PID: $old_pid)..."
            kill "$old_pid" 2>/dev/null
            sleep 2
        fi
        rm -f "$worker_pid_file"
    fi
    
    # Start new simple worker in background
    print_status "  Starting simple worker daemon..."
    nohup python3 "$worker_script" > "$worker_log" 2>&1 &
    local worker_pid=$!
    
    # Save PID for management
    echo "$worker_pid" > "$worker_pid_file"
    
    # Verify worker started
    sleep 3
    if kill -0 "$worker_pid" 2>/dev/null; then
        print_success "  ✓ Simple worker started (PID: $worker_pid)"
        print_status "    📋 Handles: extract-text, chunk-document, generate-embeddings,"
        print_status "               create-knowledge-asset, store-vector-chunks, activate-knowledge-asset"
        print_status "    📄 Logs: $worker_log"
    else
        print_warning "  ⚠ Simple worker may have failed to start"
        if [[ -f "$worker_log" ]]; then
            print_status "    Error: $(tail -n 1 "$worker_log")"
        fi
    fi
}

# Stop external workers
stop_external_workers() {
    print_status "Stopping external workers..."
    
    # Stop complex worker
    stop_complex_worker
    
    # Stop simple worker
    stop_simple_worker
}

# Stop complex worker
stop_complex_worker() {
    local worker_pid_file="/tmp/odras_complex_worker.pid"
    
    if [[ -f "$worker_pid_file" ]]; then
        local worker_pid=$(cat "$worker_pid_file")
        if kill -0 "$worker_pid" 2>/dev/null; then
            print_status "Stopping complex worker (PID: $worker_pid)..."
            kill "$worker_pid" 2>/dev/null
            sleep 2
            if ! kill -0 "$worker_pid" 2>/dev/null; then
                print_success "✓ Complex worker stopped"
            else
                kill -9 "$worker_pid" 2>/dev/null
                print_success "✓ Complex worker terminated"
            fi
        fi
        rm -f "$worker_pid_file"
    fi
}

# Stop simple worker
stop_simple_worker() {
    local worker_pid_file="/tmp/odras_simple_worker.pid"
    
    if [[ -f "$worker_pid_file" ]]; then
        local worker_pid=$(cat "$worker_pid_file")
        if kill -0 "$worker_pid" 2>/dev/null; then
            print_status "Stopping simple worker (PID: $worker_pid)..."
            kill "$worker_pid" 2>/dev/null
            sleep 2
            if ! kill -0 "$worker_pid" 2>/dev/null; then
                print_success "✓ Simple worker stopped"
            else
                kill -9 "$worker_pid" 2>/dev/null
                print_success "✓ Simple worker terminated"
            fi
        fi
        rm -f "$worker_pid_file"
    fi
}

# Clean Fuseki RDF store
clean_fuseki() {
    print_status "Cleaning Fuseki RDF store..."
    
    # Get all datasets and delete them completely
    local datasets=$(curl -s http://localhost:3030/$/datasets 2>/dev/null | jq -r '.datasets[]."ds.name"' 2>/dev/null)
    
    if [[ $? -eq 0 ]] && [[ -n "$datasets" ]]; then
        for dataset in $datasets; do
            if [[ "$dataset" != "null" ]] && [[ -n "$dataset" ]]; then
                # Remove leading slash from dataset name
                local clean_dataset=$(echo "$dataset" | sed 's|^/||')
                print_status "  Deleting dataset: $clean_dataset"
                # Delete the entire dataset (not just clear data)
                curl -s -X DELETE "http://localhost:3030/$/datasets/$clean_dataset" >/dev/null 2>&1
            fi
        done
        print_success "✓ Fuseki datasets deleted"
    else
        print_warning "⚠ Could not connect to Fuseki or no datasets found"
    fi
    
    # Also clear any persistent data in the volume
    print_status "Clearing Fuseki persistent volume data..."
    if docker exec odras_fuseki rm -rf /fuseki/databases/* 2>/dev/null; then
        print_success "✓ Fuseki persistent data cleared"
    else
        print_warning "⚠ Could not clear Fuseki persistent data (container may not be running)"
    fi
}

# Clean MinIO storage
clean_minio() {
    print_status "Cleaning MinIO object storage..."
    
    # Use MinIO client if available, otherwise use REST API
    if command -v mc >/dev/null 2>&1; then
        # Configure MinIO client and remove all buckets
        mc alias set odras-minio http://localhost:9000 minioadmin minioadmin >/dev/null 2>&1
        local buckets=$(mc ls odras-minio 2>/dev/null | awk '{print $5}')
        for bucket in $buckets; do
            if [[ -n "$bucket" ]]; then
                print_status "  Removing bucket: $bucket"
                mc rm --recursive --force "odras-minio/$bucket" >/dev/null 2>&1
                mc rb "odras-minio/$bucket" >/dev/null 2>&1
            fi
        done
    else
        # Fallback: restart MinIO container to clear data
        print_status "  Restarting MinIO container to clear data..."
        docker-compose -f "$DOCKER_COMPOSE_FILE" restart minio >/dev/null 2>&1
    fi
    
    print_success "✓ MinIO cleaned"
}

# Clean local storage
clean_local_storage() {
    print_status "Cleaning local storage..."
    
    # Clean upload directories
    if [[ -d "uploads" ]]; then
        rm -rf uploads/*
        print_status "  Cleared uploads directory"
    fi
    
    if [[ -d "storage" ]]; then
        rm -rf storage/*
        print_status "  Cleared storage directory"
    fi
    
    # Clean models cache
    if [[ -d "models" ]]; then
        find models -name "*.cache" -delete 2>/dev/null
        print_status "  Cleared model cache"
    fi
    
    # Clean temp files
    rm -f /tmp/odras_*
    
    print_success "✓ Local storage cleaned"
}

# Clean browser local storage data
clean_browser_storage() {
    print_status "Cleaning browser local storage data..."
    
    # Create a simple HTML file that clears localStorage when opened
    local clear_script="
<!DOCTYPE html>
<html>
<head>
    <title>Clear ODRAS Local Storage</title>
</head>
<body>
    <h1>Clearing ODRAS Local Storage...</h1>
    <script>
        // Clear all localStorage data
        localStorage.clear();
        sessionStorage.clear();
        
        // Clear specific ODRAS keys
        const odrasKeys = [
            'odras_token',
            'odras_user',
            'activeOntologyIri',
            'visibleImports',
            'ontologyLayouts',
            'projectData',
            'knowledgeAssets'
        ];
        
        odrasKeys.forEach(key => {
            localStorage.removeItem(key);
            sessionStorage.removeItem(key);
        });
        
        document.body.innerHTML = '<h1>✅ ODRAS Local Storage Cleared!</h1><p>You can close this tab now.</p>';
    </script>
</body>
</html>"
    
    # Write the script to a temporary file
    echo "$clear_script" > /tmp/clear_odras_storage.html
    
    print_status "  Created browser storage clearing script: /tmp/clear_odras_storage.html"
    print_status "  💡 To clear browser storage:"
    print_status "     1. Open: file:///tmp/clear_odras_storage.html in your browser"
    print_status "     2. Or manually clear localStorage in browser dev tools"
    print_status "     3. Or restart your browser"
    
    print_success "✓ Browser storage clearing instructions provided"
}

# Clean everything (containers + volumes)
clean_all() {
    # Check if -y flag was passed
    local skip_confirm=false
    if [[ "$1" == "-y" ]] || [[ "$SKIP_CONFIRM" == "true" ]]; then
        skip_confirm=true
    fi
    
    if [[ "$skip_confirm" == "false" ]]; then
        print_warning "This will DESTROY ALL DATA and remove Docker containers/volumes. Are you sure? (y/N)"
    read -r response
        if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            print_status "Cleanup cancelled"
            return
        fi
    else
        print_status "Destroying all data and containers (auto-confirmed)..."
    fi
    
    if [[ true ]]; then
        print_status "Cleaning up everything..."
        
        # Stop app
        stop_app
        
        # Stop and remove containers with volumes
        docker-compose -f "$DOCKER_COMPOSE_FILE" down -v --remove-orphans
        
        # Remove any remaining volumes (including Fuseki data)
        docker volume rm $(docker volume ls -q | grep odras) 2>/dev/null || true
        
        # Ensure Fuseki volume is completely removed
        docker volume rm odras_fuseki_data 2>/dev/null || true
        
        # Clean up PID and log files (only if application is not running)
        if [[ -f "$PID_FILE" ]]; then
            local pid=$(cat "$PID_FILE")
            if ! ps -p "$pid" > /dev/null 2>&1; then
                print_status "Cleaning up stale PID and log files..."
        rm -f "$PID_FILE" "$LOG_FILE"
            else
                print_warning "Application is running (PID: $pid) - keeping log files"
            fi
        else
            # No PID file, safe to remove log file
            rm -f "$LOG_FILE"
        fi
        
        # Clean local storage
        clean_local_storage
        
        # Clean browser local storage data
        clean_browser_storage
        
        print_success "Complete cleanup completed"
        print_status "Run './odras.sh up' to start fresh containers"
    else
        print_status "Cleanup cancelled"
    fi
}

# Create default users
create_default_users() {
    print_status "Creating default users..."
    
    if docker exec odras_postgres psql -U postgres -d odras -c "SELECT 1;" >/dev/null 2>&1; then
        # Create users table if it doesn't exist
        docker exec odras_postgres psql -U postgres -d odras -c "
        CREATE TABLE IF NOT EXISTS users (
            user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            username VARCHAR(255) UNIQUE NOT NULL,
            display_name VARCHAR(255) NOT NULL,
            is_admin BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Create projects table if it doesn't exist  
        CREATE TABLE IF NOT EXISTS projects (
            project_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            created_by UUID,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            is_active BOOLEAN DEFAULT TRUE
        );
        
        -- Create project_members table if it doesn't exist
        CREATE TABLE IF NOT EXISTS project_members (
            user_id UUID NOT NULL,
            project_id UUID NOT NULL,
            role VARCHAR(50) DEFAULT 'member',
            joined_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, project_id)
        );
        " >/dev/null 2>&1
        
        # Insert default users
        docker exec odras_postgres psql -U postgres -d odras -c "
        -- Insert admin user
        INSERT INTO users (username, display_name, is_admin) 
        VALUES ('admin', 'Administrator', TRUE) 
        ON CONFLICT (username) DO UPDATE SET 
            display_name = EXCLUDED.display_name, 
            is_admin = EXCLUDED.is_admin,
            updated_at = NOW();
            
        -- Insert jdehart user  
        INSERT INTO users (username, display_name, is_admin)
        VALUES ('jdehart', 'J DeHart', FALSE)
        ON CONFLICT (username) DO UPDATE SET
            display_name = EXCLUDED.display_name,
            is_admin = EXCLUDED.is_admin,
            updated_at = NOW();
        " >/dev/null 2>&1
        
        # Create a default project and assign users
        docker exec odras_postgres psql -U postgres -d odras -c "
        -- Create default project
        INSERT INTO projects (name, description, created_by)
        SELECT 'Default Project', 'Default project for testing', u.user_id
        FROM users u WHERE u.username = 'admin'
        ON CONFLICT DO NOTHING;
        
        -- Add admin to default project
        INSERT INTO project_members (user_id, project_id, role)
        SELECT u.user_id, p.project_id, 'admin'
        FROM users u, projects p 
        WHERE u.username = 'admin' AND p.name = 'Default Project'
        ON CONFLICT DO NOTHING;
        
        -- Add jdehart to default project
        INSERT INTO project_members (user_id, project_id, role) 
        SELECT u.user_id, p.project_id, 'member'
        FROM users u, projects p
        WHERE u.username = 'jdehart' AND p.name = 'Default Project'
        ON CONFLICT DO NOTHING;
        " >/dev/null 2>&1
        
        print_success "✓ Created default users: admin (admin), jdehart (member)"
        print_status "  Login credentials:"
        print_status "    Username: admin  | Password: admin"
        print_status "    Username: jdehart | Password: jdehart"
    else
        print_warning "⚠ Could not connect to PostgreSQL to create users"
    fi
}

# Initialize clean databases with schema
init_databases() {
    print_status "Initializing databases with schema..."
    
    # Wait for services to be ready
    print_status "Waiting for database services to be ready..."
    sleep 5
    
    # Run PostgreSQL migrations in order
    if [[ -d "backend/migrations" ]]; then
        print_status "Running PostgreSQL migrations..."
        
        # Run migrations in specific order to ensure dependencies
        local migrations=(
            "000_files_table.sql"
            "001_knowledge_management.sql"
            "002_knowledge_public_assets.sql"
            "003_auth_tokens.sql"
            "004_users_table.sql"
            "005_prefix_management.sql"
            "006_update_prefix_constraint.sql"
            "007_revert_prefix_constraint.sql"
            "008_create_projects_table.sql"
            "009_create_domains_table.sql"
            "010_namespace_management.sql"
            "011_add_service_namespace_type.sql"
            "012_migrate_auth_system.sql"
        )
        
        for migration in "${migrations[@]}"; do
            local migration_file="backend/migrations/$migration"
            if [[ -f "$migration_file" ]]; then
                print_status "  Running $migration..."
                if cat "$migration_file" | docker exec -i odras_postgres psql -U postgres -d odras; then
                    print_success "    ✓ $migration completed"
                else
                    print_warning "    ⚠ $migration may have failed or was already applied"
                fi
            else
                print_warning "    Migration file $migration not found"
            fi
        done
    else
        print_warning "No migrations directory found"
    fi
    
    # Initialize Neo4j schema
    print_status "Initializing Neo4j schema..."
    docker exec odras_neo4j cypher-shell -u neo4j -p testpassword "
    // Create basic constraints
    CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;
    CREATE CONSTRAINT asset_id IF NOT EXISTS FOR (a:KnowledgeAsset) REQUIRE a.id IS UNIQUE;
    CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE;
    " >/dev/null 2>&1 || print_warning "  Neo4j initialization may have failed"
    
    # Initialize Fuseki RDF store
    print_status "Initializing Fuseki RDF store..."
    init_fuseki
    
    # Deploy BPMN workflows to Camunda
    print_status "Deploying BPMN workflows to Camunda..."
    deploy_bpmn_workflows
    
    # Initialize Qdrant collections
    print_status "Initializing Qdrant collections..."
    if curl -s http://localhost:6333/collections >/dev/null 2>&1; then
        # Create knowledge_chunks collection (384 dimensions for sentence-transformers)
        curl -s -X PUT "http://localhost:6333/collections/knowledge_chunks" \
             -H "Content-Type: application/json" \
             -d '{"vectors": {"size": 384, "distance": "Cosine"}}' >/dev/null 2>&1
        
        # Create knowledge_large collection (1536 dimensions for OpenAI embeddings)
        curl -s -X PUT "http://localhost:6333/collections/knowledge_large" \
             -H "Content-Type: application/json" \
             -d '{"vectors": {"size": 1536, "distance": "Cosine"}}' >/dev/null 2>&1
             
        # Create odras_requirements collection (384 dimensions)
        curl -s -X PUT "http://localhost:6333/collections/odras_requirements" \
             -H "Content-Type: application/json" \
             -d '{"vectors": {"size": 384, "distance": "Cosine"}}' >/dev/null 2>&1
        
        print_success "✓ Created Qdrant collections: knowledge_chunks, knowledge_large, odras_requirements"
    else
        print_warning "⚠ Could not connect to Qdrant to create collections"
    fi
    
    # Create default users
    print_status "Creating default users..."
    docker exec odras_postgres psql -U postgres -d odras -c "
    INSERT INTO users (username, display_name, is_admin) 
    VALUES ('admin', 'Administrator', TRUE), ('jdehart', 'J DeHart', FALSE)
    ON CONFLICT (username) DO UPDATE SET 
        display_name = EXCLUDED.display_name, 
        is_admin = EXCLUDED.is_admin,
        updated_at = NOW();
    " >/dev/null 2>&1 && print_success "✓ Created default users: admin, jdehart"
    
    print_success "🎉 Database initialization completed!"
    print_status "📊 Database schema and collections are ready"
    print_status "👤 Default users created: admin/admin, jdehart/jdehart"
    print_status "🌐 URL: http://localhost:8000/app"
}

# Create demo content with navigation system knowledge for Default Project
create_demo_content() {
    print_status "Creating demo content with navigation system knowledge for Default Project..."
    
    # Wait for application to be ready
    print_status "Waiting for application to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:8000/health >/dev/null 2>&1; then
            print_success "✓ Application is ready"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            print_warning "⚠ Application may not be ready, continuing anyway..."
            break
        fi
        
        sleep 2
        attempt=$((attempt + 1))
    done
    
    # Run the demo setup script
    if [[ -f "setup_test_knowledge_data.py" ]]; then
        print_status "Running demo project setup..."
        print_status "  📄 Uploading navigation system requirements..."
        print_status "  📋 Uploading safety protocols..."
        print_status "  🔧 Uploading technical specifications..."
        print_status "  ⏳ Processing documents (this may take 30-60 seconds)..."
        
        # Run with timeout to prevent hanging, capture output for error reporting
        local setup_output=$(mktemp)
        if timeout 180 python setup_test_knowledge_data.py >"$setup_output" 2>&1; then
            print_success "✓ Demo project setup completed successfully"
            rm -f "$setup_output"
            
            # Verify the setup worked
            local asset_count=$(curl -s \
                -H "Authorization: Bearer $(curl -s -X POST http://localhost:8000/api/auth/login \
                    -H 'Content-Type: application/json' \
                    -d '{"username":"jdehart","password":"jdehart"}' | \
                    python3 -c "import sys, json; print(json.load(sys.stdin)['token'])" 2>/dev/null)" \
                "http://localhost:8000/api/knowledge/assets" 2>/dev/null | \
                python3 -c "import sys, json; print(json.load(sys.stdin)['total_count'])" 2>/dev/null)
            
            if [[ "$asset_count" =~ ^[0-9]+$ ]] && [[ $asset_count -gt 0 ]]; then
                print_success "✓ Demo contains $asset_count knowledge assets"
            else
                print_warning "⚠ Demo setup may not have completed properly"
            fi
        else
            print_warning "⚠ Demo setup encountered issues, but basic database is ready"
            if [[ -f "$setup_output" ]]; then
                print_status "  Error details: $(tail -n 5 "$setup_output" | head -n 1)"
                rm -f "$setup_output"
            fi
        fi
    else
        print_warning "⚠ Demo setup script not found, creating basic demo manually..."
        create_basic_demo
    fi
}

# Create a basic demo if the full setup script is not available
create_basic_demo() {
    print_status "Creating basic demo environment..."
    
    # This is a fallback - just ensure we have the basic structure
    # The full demo will be created when the user first uses the system
    print_success "✓ Basic demo environment ready"
    print_status "💡 Upload documents via the UI to create knowledge assets"
}

# Create default ontology for the Default Project
create_default_ontology() {
    print_status "Creating default ontology for Default Project..."
    
    # Check if the script exists
    if [[ -f "scripts/create_default_ontology.py" ]]; then
        print_status "Running ontology creation script..."
        
        # Run the script
        if python scripts/create_default_ontology.py; then
            print_success "✓ Default ontology created successfully"
            print_status "   Includes: CADFile, Specification, TestCase, and other data objects"
        else
            print_warning "⚠ Ontology creation encountered issues, but project is ready"
        fi
    else
        print_warning "⚠ Ontology creation script not found"
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
    echo "Database Commands:"
    echo "  clean          Clean all database data (keeps containers running)"
    echo "  clean -y       Clean all database data without confirmation prompt"
    echo "  clean-all      DESTROY everything - containers, volumes, and data"
    echo "  clean-all -y   DESTROY everything without confirmation prompt"
    echo "  init-db        Initialize databases with schema and default project"
    echo ""
    echo "Utility Commands:"
    echo "  help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start       # Start the app"
    echo "  $0 up          # Start Docker services"
    echo "  $0 status      # Check status"
    echo "  $0 logs        # View app logs"
    echo "  $0 clean       # Clean all database data for fresh testing"
    echo "  $0 init-db     # Initialize databases with default project"
    echo "  $0 clean-all   # DANGER: Destroy everything and start over"
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
            shift  # Remove 'clean' from arguments
            clean_databases "$@"  # Pass remaining arguments (like -y)
            ;;
        clean-all)
            shift  # Remove 'clean-all' from arguments
            clean_all "$@"  # Pass remaining arguments (like -y)
            ;;
        init-db)
            init_databases
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
