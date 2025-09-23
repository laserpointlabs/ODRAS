# Clear Project Threads Script

This script clears out the data from the `project_threads` collections in both Qdrant vector database and Redis cache, while preserving the collection structure.

## Usage

```bash
# Show what would be cleared (dry run)
python scripts/clear_project_threads.py --dry-run

# Clear with confirmation prompt
python scripts/clear_project_threads.py

# Clear without confirmation (force)
python scripts/clear_project_threads.py --force

# Clear only Redis cache
python scripts/clear_project_threads.py --redis-only

# Clear only Qdrant collection
python scripts/clear_project_threads.py --qdrant-only
```

## Options

- `--dry-run`: Show what would be cleared without actually clearing
- `--force`: Skip confirmation prompts
- `--redis-only`: Only clear Redis cache
- `--qdrant-only`: Only clear Qdrant collection
- `--help`: Show help message

## What it clears

### Redis
- `project_thread:*` - Direct thread storage
- `project_index:*` - Project to thread mapping
- `project_events` - Event queue
- `project_watch:*` - Real-time monitoring keys

### Qdrant
- `project_threads` collection - Clears all points from the collection (preserves collection structure)

## Safety Features

- **Dry-run mode**: Test what would be cleared without making changes
- **Confirmation prompts**: Ask for user confirmation before clearing (unless `--force` is used)
- **Detailed logging**: Shows exactly what keys/collections are found and cleared
- **Error handling**: Graceful handling of connection failures
- **Summary report**: Clear summary of what was cleaned

## Examples

```bash
# Safe test run
python scripts/clear_project_threads.py --dry-run

# Interactive cleanup
python scripts/clear_project_threads.py

# Automated cleanup (for scripts)
python scripts/clear_project_threads.py --force

# Clear only Redis (if Qdrant is down)
python scripts/clear_project_threads.py --redis-only --force
```

## Configuration

The script uses the same configuration as the ODRAS backend:
- Qdrant URL: `http://localhost:6333` (configurable via environment)
- Redis URL: `redis://localhost:6379` (configurable via environment)

## Requirements

- Python 3.7+
- `requests` library
- `redis` library (async)
- Access to ODRAS backend configuration
