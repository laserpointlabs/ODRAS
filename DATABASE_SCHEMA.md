# ODRAS Database Schema Documentation

Generated on: 2025-09-09 12:31:09

## Overview

This document describes the ODRAS database schema and migration system.

## Migration Files

Total migrations: 13

### 000_files_table.sql

- **Version**: 000
- **Description**: Files Table
- **Dependencies**: None
- **Created**: 2025-09-02 16:46:22
- **Modified**: 2025-09-02 16:46:22
- **Checksum**: 0ececc5fd9fd86520fe99af27fe17256

### 001_knowledge_management.sql

- **Version**: 001
- **Description**: Knowledge Management
- **Dependencies**: None
- **Created**: 2025-09-02 16:46:22
- **Modified**: 2025-09-02 16:46:22
- **Checksum**: dd2dbfae291a64b01915db9551a82b3e

### 002_knowledge_public_assets.sql

- **Version**: 002
- **Description**: Knowledge Public Assets
- **Dependencies**: None
- **Created**: 2025-09-02 16:46:22
- **Modified**: 2025-09-02 16:46:22
- **Checksum**: b513b2673f1970801cd5768b03661aaf

### 003_auth_tokens.sql

- **Version**: 003
- **Description**: Auth Tokens
- **Dependencies**: None
- **Created**: 2025-09-04 12:21:23
- **Modified**: 2025-09-04 12:21:23
- **Checksum**: 58c5308b286984d9e34ca01d106bce27

### 004_users_table.sql

- **Version**: 004
- **Description**: Users Table
- **Dependencies**: None
- **Created**: 2025-09-04 12:45:55
- **Modified**: 2025-09-04 12:45:55
- **Checksum**: f9b162340d5303ef39f249ea99b77f46

### 005_prefix_management.sql

- **Version**: 005
- **Description**: Prefix Management
- **Dependencies**: None
- **Created**: 2025-09-05 14:20:18
- **Modified**: 2025-09-05 14:20:18
- **Checksum**: 372ad54e5289e42188d07b84fcecd48b

### 006_update_prefix_constraint.sql

- **Version**: 006
- **Description**: Update Prefix Constraint
- **Dependencies**: None
- **Created**: 2025-09-05 14:51:40
- **Modified**: 2025-09-05 14:51:40
- **Checksum**: 2b577efbbdda0a2226e88c97a1ab6bb0

### 007_revert_prefix_constraint.sql

- **Version**: 007
- **Description**: Revert Prefix Constraint
- **Dependencies**: None
- **Created**: 2025-09-05 17:56:41
- **Modified**: 2025-09-05 17:56:41
- **Checksum**: e259a5979bdb71419172974e10041bf6

### 008_create_projects_table.sql

- **Version**: 008
- **Description**: Create Projects Table
- **Dependencies**: None
- **Created**: 2025-09-08 11:52:04
- **Modified**: 2025-09-08 11:52:04
- **Checksum**: a3961472bf16ab094aa0c19834b5bfe8

### 009_create_domains_table.sql

- **Version**: 009
- **Description**: Create Domains Table
- **Dependencies**: None
- **Created**: 2025-09-08 11:32:21
- **Modified**: 2025-09-08 11:32:21
- **Checksum**: e348af5fde154410364df5d7183dc335

### 010_namespace_management.sql

- **Version**: 010
- **Description**: Namespace Management
- **Dependencies**: None
- **Created**: 2025-09-08 15:13:44
- **Modified**: 2025-09-05 14:20:18
- **Checksum**: c06e1e8660cdb40c95fedb88603a251b

### 011_add_service_namespace_type.sql

- **Version**: 011
- **Description**: Add Service Namespace Type
- **Dependencies**: None
- **Created**: 2025-09-08 15:14:04
- **Modified**: 2025-09-05 14:20:18
- **Checksum**: 8431f9e99251bce670ac84bfed860696

### 012_migrate_auth_system.sql

- **Version**: 012
- **Description**: Migrate Auth System
- **Dependencies**: None
- **Created**: 2025-09-09 11:51:50
- **Modified**: 2025-09-09 11:51:50
- **Checksum**: b4a5f357ba46cdbb9ef7214af161097e


## Schema Validation

To validate the schema:

```bash
python scripts/database_schema_manager.py validate
```

## Updating Schema

When making schema changes:

1. Create a new migration file:
   ```bash
   python scripts/database_schema_manager.py create "Description of changes"
   ```

2. Update schema info:
   ```bash
   python scripts/database_schema_manager.py update-info
   ```

3. Update odras.sh:
   ```bash
   python scripts/database_schema_manager.py update-odras
   ```

4. Test the changes:
   ```bash
   python scripts/database_schema_manager.py test
   ```

## Migration Order

The migrations are applied in this order:

1. 000_files_table.sql
2. 001_knowledge_management.sql
3. 002_knowledge_public_assets.sql
4. 003_auth_tokens.sql
5. 004_users_table.sql
6. 005_prefix_management.sql
7. 006_update_prefix_constraint.sql
8. 007_revert_prefix_constraint.sql
9. 008_create_projects_table.sql
10. 009_create_domains_table.sql
11. 010_namespace_management.sql
12. 011_add_service_namespace_type.sql
13. 012_migrate_auth_system.sql

