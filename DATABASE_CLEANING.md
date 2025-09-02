# ODRAS Database Cleaning Guide

The ODRAS system now includes comprehensive database cleaning functionality for testing and development.

## 🚀 Quick Start

```bash
# Clean all database data + recreate users (keeps containers running)
./odras.sh clean

# Test database connectivity
python test_db_connectivity.py

# Login with default credentials:
# Username: admin   | Password: admin   (Administrator)
# Username: jdehart | Password: jdehart (Regular user)
```

## 📊 Cleaning Commands

### `./odras.sh clean`
**Recommended for testing** - Cleans all database data while keeping containers running.

**What it cleans:**
- ✅ **PostgreSQL**: All tables (users, projects, files, knowledge assets, chunks, etc.)
- ✅ **Qdrant**: All vector collections and embeddings
- ✅ **Neo4j**: All graph nodes and relationships
- ✅ **Fuseki**: All RDF datasets and triples
- ✅ **MinIO**: All object storage buckets and files
- ✅ **Local Storage**: Upload directories, temp files, model cache

**What it preserves:**
- ✅ Docker containers and volumes
- ✅ Service configurations  
- ✅ Application code and migrations

**What it recreates:**
- 🔄 **Default Users**: admin (administrator) and jdehart (regular user)
- 🔄 **Default Project**: "Default Project" with both users as members
- 🔄 **Login Access**: Ready to login immediately after cleaning

### `./odras.sh clean-all`
**⚠️ DANGER ZONE** - Destroys everything including containers and volumes.

**What it destroys:**
- ❌ All database data (same as `clean`)
- ❌ Docker containers
- ❌ Docker volumes
- ❌ All persistent storage

Use this only when you want to completely reset the entire system.

### `./odras.sh init-db`
Initializes clean databases with proper schema and constraints.

**What it does:**
- 🔄 Runs all PostgreSQL migrations
- 🔄 Sets up Neo4j constraints and indexes
- 🔄 Verifies database schema integrity

## 🔄 Typical Testing Workflow

```bash
# 1. Clean all data + recreate users for fresh testing
./odras.sh clean

# 2. Restart the application
./odras.sh restart

# 3. Login with admin/admin or jdehart/jdehart

# 4. Run your tests with clean data
python test_final_knowledge_workflow.py

# 5. Verify everything is working
python test_db_connectivity.py
```

## 🛡️ Safety Features

- **Confirmation prompts**: Both `clean` and `clean-all` require explicit confirmation
- **Connection checks**: Verifies database connectivity before cleaning
- **Graceful handling**: Continues cleaning even if some services are unreachable
- **Status reporting**: Shows what was cleaned and any warnings

## 🔍 Database Details

### PostgreSQL (Port 5432)
- **Connection**: `postgres://postgres:password@localhost:5432/odras`
- **Tables cleaned**: `knowledge_*`, `files`, `projects`, `users`, etc.
- **Method**: DROP TABLE CASCADE with foreign key handling

### Qdrant (Port 6333)
- **Connection**: `http://localhost:6333`
- **Collections cleaned**: All vector collections
- **Method**: DELETE /collections/{collection_name}

### Neo4j (Port 7687)
- **Connection**: `bolt://localhost:7687` (neo4j/testpassword)
- **Data cleaned**: All nodes and relationships
- **Method**: `MATCH (n) DETACH DELETE n`

### Fuseki (Port 3030)
- **Connection**: `http://localhost:3030`
- **Data cleaned**: All RDF datasets
- **Method**: SPARQL `DELETE WHERE { ?s ?p ?o }`

### MinIO (Port 9000)
- **Connection**: `http://localhost:9000` (minioadmin/minioadmin)
- **Data cleaned**: All buckets and objects
- **Method**: MinIO client or container restart

## 🚨 Important Notes

1. **Always backup important data** before using `clean-all`
2. **Use `clean` for routine testing** - it's faster and safer
3. **Check connectivity first** with `python test_db_connectivity.py`
4. **The application will recreate schemas** automatically on startup
5. **Clean operations require services to be running** (use `./odras.sh up` first)

## 📝 Examples

```bash
# Quick clean and restart for testing
./odras.sh clean && ./odras.sh restart
# Login: admin/admin or jdehart/jdehart

# Complete reset (careful!)
./odras.sh clean-all && ./odras.sh up && ./odras.sh start

# Verify system state
./odras.sh status && python test_db_connectivity.py

# Just create users without cleaning everything
./odras.sh init-db
```

## 🐛 Troubleshooting

**If cleaning fails:**
1. Check that Docker services are running: `./odras.sh docker-status`
2. Test connectivity: `python test_db_connectivity.py`
3. Start services if needed: `./odras.sh up`
4. Check logs: `./odras.sh docker-logs`

**If databases don't initialize:**
1. Run `./odras.sh init-db` manually
2. Check migration files in `backend/migrations/`
3. Restart the application: `./odras.sh restart`
