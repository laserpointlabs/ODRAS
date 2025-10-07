# ODRAS Quick Setup Scripts

This folder contains scripts to quickly set up ODRAS after a system rebuild.

## Quick Setup Scripts

### `quick_setup.py` - Complete Setup
**Purpose**: Automates the complete ODRAS setup process
**Usage**: `python scripts/quick_setup.py`

**What it does**:
1. ✅ Login with jdehart account
2. ✅ Create 'core.se' project in systems-engineering domain
3. ✅ Import bseo_v1a.json ontology (if import endpoint exists)
4. ✅ Upload and process all markdown documents from `/data` folder
5. ✅ Test system with sample DAS query

**Smart Features**:
- Auto-detects document types based on filename
- Uses better embedding model (all-mpnet-base-v2) for specifications/requirements
- Uses fast embedding model (all-MiniLM-L6-v2) for general documents
- Uses improved semantic chunking strategy
- Validates processing status

### `quick_setup.sh` - Shell Wrapper
**Purpose**: Shell script wrapper with error checking
**Usage**: `./scripts/quick_setup.sh`

**What it does**:
1. ✅ Checks if ODRAS is running
2. ✅ Validates required data files exist
3. ✅ Runs Python setup script
4. ✅ Runs embedding model tests
5. ✅ Provides helpful error messages

### `test_embedders.py` - Embedding Model Validation
**Purpose**: Tests both embedding models with improved chunking
**Usage**: `python scripts/test_embedders.py`

**What it does**:
1. ✅ Tests all-MiniLM-L6-v2 (fast, 384 dims)
2. ✅ Tests all-mpnet-base-v2 (better, 768 dims)
3. ✅ Runs comprehensive query tests
4. ✅ Compares performance between models
5. ✅ Validates Qdrant collection usage

## Usage Instructions

### After System Rebuild

1. **Start ODRAS**:
   ```bash
   ./odras.sh clean -y && ./odras.sh init-db && ./odras.sh start
   ```

2. **Run Quick Setup**:
   ```bash
   ./scripts/quick_setup.sh
   ```

3. **Access System**:
   - Open: http://localhost:8000/app
   - Login: jdehart / jdehart123!
   - Project: core.se

### Manual Setup (Alternative)

If you prefer manual setup:

```bash
# 1. Login and create project manually via UI
# 2. Run just the embedder tests
python scripts/test_embedders.py

# 3. Or run just the document upload
python scripts/quick_setup.py
```

## Expected Results

After successful setup:

- ✅ **Project 'core.se' created** with systems-engineering domain
- ✅ **All markdown documents uploaded** and processed
- ✅ **Both embedding models working**:
  - Fast (all-MiniLM-L6-v2): 384 dimensions
  - Better (all-mpnet-base-v2): 768 dimensions
- ✅ **Improved chunking active** for structured documents
- ✅ **DAS can find all 9 UAS** in specifications
- ✅ **RAG performance excellent** for both models

## Troubleshooting

**"ODRAS not running"**:
```bash
./odras.sh restart
```

**"Login failed"**:
```bash
./odras.sh init-db  # Recreate users
```

**"Upload failed"**:
- Check if files exist in `/data` folder
- Verify ODRAS workers are running: `./odras.sh status`

**"No chunks found"**:
- Wait longer for processing (up to 30 seconds)
- Check worker logs: `tail /tmp/odras_simple_worker.log`

## File Configurations

The setup script automatically configures:

| **File Type** | **Document Type** | **Embedding Model** | **Chunking Strategy** |
|---------------|-------------------|---------------------|----------------------|
| `*specification*` | specification | all-mpnet-base-v2 | simple_semantic |
| `*requirement*` | requirements | all-mpnet-base-v2 | simple_semantic |
| `*template*` | analysis_template | all-MiniLM-L6-v2 | simple_semantic |
| `*guide*` | reference | all-MiniLM-L6-v2 | simple_semantic |
| Other files | document | all-MiniLM-L6-v2 | simple_semantic |

This ensures optimal performance for different document types while maintaining system efficiency.
