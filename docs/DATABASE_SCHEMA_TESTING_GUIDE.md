# ODRAS Database Schema Testing Guide

## 🎯 Overview

This guide explains how to ensure that database schema changes are properly tested and that the `odras.sh init-db` command stays up to date with the latest schema.

## 🚨 The Problem

When you modify the database schema, you need to ensure:

1. **Migration files are created** for all schema changes
2. **odras.sh init-db is updated** to include new migrations
3. **Schema consistency** is maintained across all environments
4. **Tests can run** with the new schema
5. **Rollback scenarios** are handled properly

## 🛠️ Solution: Comprehensive Database Schema Management

### **1. Database Schema Manager**

The `scripts/database_schema_manager.py` script provides:

- **Migration discovery** and validation
- **Schema consistency checking**
- **Automatic odras.sh updates**
- **Migration template generation**
- **Schema documentation generation**

### **2. Database Schema Validator**

The `scripts/validate_database_schema.py` script provides:

- **Comprehensive validation** of all database components
- **Migration file validation**
- **odras.sh script validation**
- **Database connection testing**
- **Automatic fixing** of common issues

### **3. Database Testing Suite**

The `tests/database/test_database_schema.py` provides:

- **Unit tests** for schema components
- **Integration tests** for migration application
- **Consistency tests** across environments
- **Rollback testing**

## 🚀 Usage Workflow

### **When Making Schema Changes**

#### **Step 1: Create Migration File**
```bash
# Generate a new migration template
python scripts/database_schema_manager.py create "Add new table for user preferences"

# This creates: backend/migrations/010_add_new_table_for_user_preferences.sql
# Edit the file and add your SQL
```

#### **Step 2: Update Schema Info**
```bash
# Update the schema information file
python scripts/database_schema_manager.py update-info
```

#### **Step 3: Update odras.sh**
```bash
# Update odras.sh init-db with new migrations
python scripts/database_schema_manager.py update-odras
```

#### **Step 4: Validate Changes**
```bash
# Run comprehensive validation
python scripts/validate_database_schema.py --verbose

# Fix any issues automatically
python scripts/validate_database_schema.py --fix
```

#### **Step 5: Test Changes**
```bash
# Run database tests
pytest tests/database/test_database_schema.py -v

# Run full test suite
python scripts/run_comprehensive_tests.py --verbose
```

### **Before Merging Branches**

#### **Run Pre-Merge Validation**
```bash
# This automatically includes database schema validation
./scripts/pre_merge_validation.sh --verbose
```

#### **Test Database Initialization**
```bash
# Test that odras.sh init-db works with new schema
./odras.sh clean-all -y
./odras.sh up
./odras.sh init-db
```

## 📋 Database Schema Rules

### **Migration File Naming**
- **Format**: `XXX_description.sql` (e.g., `010_add_user_preferences.sql`)
- **Sequential numbering**: 001, 002, 003, etc.
- **Descriptive names**: Clear description of what the migration does

### **Migration File Structure**
```sql
-- Description of the migration
-- Migration XXX: Description of the migration

-- DEPENDS ON: 009_create_domains_table.sql
-- Add any dependencies here

-- Add your migration SQL here
CREATE TABLE IF NOT EXISTS new_table (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add indexes if needed
CREATE INDEX IF NOT EXISTS idx_new_table_name ON new_table(name);

-- Add comments for documentation
COMMENT ON TABLE new_table IS 'Description of the new table';
```

### **Migration Dependencies**
- **Use DEPENDS ON comments** to specify dependencies
- **Ensure proper order** - dependencies must be created first
- **Test dependency resolution** before committing

### **Rollback Support**
- **Include DROP statements** where appropriate
- **Test rollback scenarios** in development
- **Document rollback procedures** for complex changes

## 🧪 Testing Database Schema

### **Unit Tests**
```bash
# Run database schema unit tests
pytest tests/database/test_database_schema.py -v

# Run specific test
pytest tests/database/test_database_schema.py::TestDatabaseSchema::test_migration_files_exist -v
```

### **Integration Tests**
```bash
# Test migration application
python scripts/validate_database_schema.py test

# Test database connection
python scripts/validate_database_schema.py validate
```

### **End-to-End Tests**
```bash
# Test complete database initialization
./odras.sh clean-all -y
./odras.sh up
./odras.sh init-db

# Verify all tables exist
python -c "
from backend.services.db import DatabaseService
from backend.services.config import Settings
db = DatabaseService(Settings())
conn = db._conn()
with conn.cursor() as cur:
    cur.execute(\"SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'\")
    tables = [row[0] for row in cur.fetchall()]
    print('Tables:', tables)
db._return(conn)
"
```

## 🔧 Troubleshooting

### **Common Issues**

#### **Migration Not in odras.sh**
```bash
# Fix automatically
python scripts/validate_database_schema.py --fix

# Or manually update
python scripts/database_schema_manager.py update-odras
```

#### **Migration Order Issues**
```bash
# Check migration order
python scripts/database_schema_manager.py status

# Fix order issues
python scripts/database_schema_manager.py update-odras
```

#### **Database Connection Issues**
```bash
# Check Docker services
docker ps | grep odras

# Start services if needed
./odras.sh up

# Test connection
python scripts/validate_database_schema.py validate
```

#### **Migration Dependencies**
```bash
# Check dependencies
python scripts/database_schema_manager.py validate

# Fix dependency issues
# Edit migration files to add proper DEPENDS ON comments
```

### **Schema Validation Failures**

#### **Missing Migrations**
```bash
# Check what's missing
python scripts/validate_database_schema.py --verbose

# Create missing migrations
python scripts/database_schema_manager.py create "Missing migration description"
```

#### **Migration Syntax Errors**
```bash
# Check SQL syntax
python scripts/validate_database_schema.py --verbose

# Fix syntax errors in migration files
# Test with PostgreSQL directly if needed
```

## 📊 Monitoring Schema Health

### **Schema Status Check**
```bash
# Check current schema status
python scripts/database_schema_manager.py status

# Generate schema documentation
python scripts/database_schema_manager.py docs --output DATABASE_SCHEMA.md
```

### **Migration History**
```bash
# View migration history
python scripts/database_schema_manager.py status

# Check migration checksums
python scripts/validate_database_schema.py --verbose
```

### **Performance Monitoring**
```bash
# Test migration performance
time python scripts/validate_database_schema.py test

# Monitor database size
docker exec odras_postgres psql -U postgres -d odras -c "SELECT pg_size_pretty(pg_database_size('odras'));"
```

## 🚀 Best Practices

### **Development Workflow**
1. **Always create migrations** for schema changes
2. **Test migrations locally** before committing
3. **Update odras.sh** when adding migrations
4. **Run validation** before pushing
5. **Test rollback scenarios** for complex changes

### **Code Review Checklist**
- [ ] Migration file created with proper naming
- [ ] Migration includes proper comments and documentation
- [ ] Dependencies are correctly specified
- [ ] odras.sh init-db updated with new migration
- [ ] Database tests pass
- [ ] Schema validation passes
- [ ] Rollback scenarios tested

### **CI/CD Integration**
- **Pre-commit hooks** validate schema consistency
- **Pre-merge validation** includes database testing
- **CI pipeline** runs comprehensive database tests
- **Deployment** includes schema validation

## 📝 Documentation

### **Schema Documentation**
```bash
# Generate comprehensive schema documentation
python scripts/database_schema_manager.py docs --output DATABASE_SCHEMA.md
```

### **Migration Documentation**
- **Comment all migrations** with clear descriptions
- **Document dependencies** and relationships
- **Include rollback procedures** for complex changes
- **Update schema documentation** when making changes

## 🎯 Conclusion

The ODRAS database schema management system ensures that:

- **Schema changes are properly tracked** and tested
- **odras.sh init-db stays up to date** automatically
- **Database consistency** is maintained across environments
- **Testing is comprehensive** and automated
- **Rollback scenarios** are handled properly

By following this guide, you can confidently make database schema changes while ensuring the system remains stable and testable.

**Remember**: Database schema changes are critical - always test thoroughly before merging! 🚀

