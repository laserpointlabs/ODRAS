# Old Migration Files - Archived

## Summary

These migration files were consolidated into a single schema file during the alpha phase cleanup on September 29, 2025.

## What Changed

- **Before**: 16 individual migration files (000-015) that were run sequentially
- **After**: Single consolidated schema file `backend/odras_schema.sql`
- **Reason**: Simplified alpha development - migrations not needed until production deployments

## Files Moved

All files from `backend/migrations/` directory:
- `000_files_table.sql` through `015_installation_specific_iris.sql`
- `001_neo4j_knowledge_graph.cypher`
- `migration_order.txt`

## New System

The `odras.sh init-db` command now:
1. Tries to apply `backend/odras_schema.sql` first
2. Falls back to individual migrations if schema file doesn't exist
3. Same Neo4j, Fuseki, and Qdrant initialization as before

## Testing

The consolidated schema was tested successfully with:
```bash
./odras.sh clean -y && ./odras.sh init-db
```

All 5 required Qdrant collections are created:
- knowledge_chunks (384 dim)
- knowledge_large (1536 dim)
- odras_requirements (384 dim)
- das_instructions (384 dim)
- project_threads (384 dim)

Default users are created with proper password authentication:
- admin / admin123!
- jdehart / jdehart123!
- das_service / das_service_2024!

## When to Use Migrations Again

When ODRAS moves from alpha to production and we need to preserve existing data during schema changes, we'll:
1. Move these files back to `backend/migrations/`
2. Update `odras.sh` to prefer migrations over consolidated schema
3. Create new migration files for future changes

## Branch

This consolidation was done in branch: `feature/consolidate-schema`
