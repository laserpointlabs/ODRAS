# Individual Property Migration System

## Overview

When ontology properties are renamed (e.g., "has Max Speed" → "Max Speed"), individual property values are preserved through an automated migration system that:
1. Detects property renames
2. Creates mapping records
3. Migrates individual data with user confirmation
4. Prevents data loss from destructive changes

## Architecture

### Database Schema

**New Table: `property_mappings`**
- Tracks property renames across ontology versions
- Records old/new property names, IRIs, and migration status
- Links to project, graph, and class

### Backend Services

**`PropertyMigrationService`** (`backend/services/property_migration.py`)
- `create_mapping()` - Record a property rename
- `get_pending_mappings()` - Get unmigrated mappings
- `migrate_individuals()` - Migrate individual data
- `get_affected_individuals_count()` - Count affected instances
- `skip_mapping()` - Skip migration (data loss warning)

### API Endpoints

**GET `/api/individuals/{project_id}/property-mappings`**
- Returns pending property mappings
- Includes affected individual counts

**POST `/api/individuals/{project_id}/property-mappings/migrate`**
- Migrates individual properties from old to new name
- Returns migration results

**POST `/api/individuals/{project_id}/property-mappings/skip`**
- Skips migration (property values will be lost)
- Requires explicit user confirmation

## Workflow

### 1. Property Rename Detection

When an ontology is saved:
1. Change detector compares old vs new ontology
2. Detects property deletions and additions
3. Creates mapping records for likely renames

### 2. User Confirmation

Before migration:
1. System shows affected individuals count
2. User can choose to migrate or skip
3. Skip requires explicit acknowledgment of data loss

### 3. Migration Execution

When user confirms migration:
1. Individual properties JSON is parsed
2. Old property keys are renamed to new property keys
3. Database records are updated
4. Mapping status set to "applied"

## Status: Implementation Complete ✅

- ✅ Database schema created
- ✅ PropertyMigrationService implemented
- ✅ API endpoints created
- ✅ Backend integration complete

## Pending Work

### High Priority
- ⏳ Enhance change detector to auto-create mappings
- ⏳ Add frontend UI for migration confirmation
- ⏳ Add migration notifications

### Medium Priority
- ⏳ Support property type changes
- ⏳ Support property domain changes
- ⏳ Migration rollback capability

## Usage Example

```python
# Create a mapping
migration_service = PropertyMigrationService()
mapping_id = migration_service.create_mapping(
    project_id="...",
    graph_iri="...",
    class_name="Aircraft",
    old_property_name="has Max Speed",
    new_property_name="Max Speed"
)

# Check affected individuals
count = migration_service.get_affected_individuals_count(
    project_id="...",
    graph_iri="...",
    class_name="Aircraft",
    old_property_name="has Max Speed"
)

# Migrate data
result = migration_service.migrate_individuals(
    project_id="...",
    graph_iri="...",
    class_name="Aircraft",
    old_property_name="has Max Speed",
    new_property_name="Max Speed"
)
```

## Benefits

1. **Data Preservation** - Individual property values survive ontology changes
2. **User Control** - Explicit confirmation before migrations
3. **Audit Trail** - All migrations tracked in database
4. **Flexible** - Supports renames, skips, and future enhancements
