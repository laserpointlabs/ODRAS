# ODRAS Database Schema Testing Guide<br>
<br>
## 🎯 Overview<br>
<br>
This guide explains how to ensure that database schema changes are properly tested and that the `odras.sh init-db` command stays up to date with the latest schema.<br>
<br>
## 🚨 The Problem<br>
<br>
When you modify the database schema, you need to ensure:<br>
<br>
1. **Migration files are created** for all schema changes<br>
2. **odras.sh init-db is updated** to include new migrations<br>
3. **Schema consistency** is maintained across all environments<br>
4. **Tests can run** with the new schema<br>
5. **Rollback scenarios** are handled properly<br>
<br>
## 🛠️ Solution: Comprehensive Database Schema Management<br>
<br>
### **1. Database Schema Manager**<br>
<br>
The `scripts/database_schema_manager.py` script provides:<br>
<br>
- **Migration discovery** and validation<br>
- **Schema consistency checking**<br>
- **Automatic odras.sh updates**<br>
- **Migration template generation**<br>
- **Schema documentation generation**<br>
<br>
### **2. Database Schema Validator**<br>
<br>
The `scripts/validate_database_schema.py` script provides:<br>
<br>
- **Comprehensive validation** of all database components<br>
- **Migration file validation**<br>
- **odras.sh script validation**<br>
- **Database connection testing**<br>
- **Automatic fixing** of common issues<br>
<br>
### **3. Database Testing Suite**<br>
<br>
The `tests/database/test_database_schema.py` provides:<br>
<br>
- **Unit tests** for schema components<br>
- **Integration tests** for migration application<br>
- **Consistency tests** across environments<br>
- **Rollback testing**<br>
<br>
## 🚀 Usage Workflow<br>
<br>
### **When Making Schema Changes**<br>
<br>
#### **Step 1: Create Migration File**<br>
```bash<br>
# Generate a new migration template<br>
python scripts/database_schema_manager.py create "Add new table for user preferences"<br>
<br>
# This creates: backend/migrations/010_add_new_table_for_user_preferences.sql<br>
# Edit the file and add your SQL<br>
```<br>
<br>
#### **Step 2: Update Schema Info**<br>
```bash<br>
# Update the schema information file<br>
python scripts/database_schema_manager.py update-info<br>
```<br>
<br>
#### **Step 3: Update odras.sh**<br>
```bash<br>
# Update odras.sh init-db with new migrations<br>
python scripts/database_schema_manager.py update-odras<br>
```<br>
<br>
#### **Step 4: Validate Changes**<br>
```bash<br>
# Run comprehensive validation<br>
python scripts/validate_database_schema.py --verbose<br>
<br>
# Fix any issues automatically<br>
python scripts/validate_database_schema.py --fix<br>
```<br>
<br>
#### **Step 5: Test Changes**<br>
```bash<br>
# Run database tests<br>
pytest tests/database/test_database_schema.py -v<br>
<br>
# Run full test suite<br>
python scripts/run_comprehensive_tests.py --verbose<br>
```<br>
<br>
### **Before Merging Branches**<br>
<br>
#### **Run Pre-Merge Validation**<br>
```bash<br>
# This automatically includes database schema validation<br>
./scripts/pre_merge_validation.sh --verbose<br>
```<br>
<br>
#### **Test Database Initialization**<br>
```bash<br>
# Test that odras.sh init-db works with new schema<br>
./odras.sh clean-all -y<br>
./odras.sh up<br>
./odras.sh init-db<br>
```<br>
<br>
## 📋 Database Schema Rules<br>
<br>
### **Migration File Naming**<br>
- **Format**: `XXX_description.sql` (e.g., `010_add_user_preferences.sql`)<br>
- **Sequential numbering**: 001, 002, 003, etc.<br>
- **Descriptive names**: Clear description of what the migration does<br>
<br>
### **Migration File Structure**<br>
```sql<br>
-- Description of the migration<br>
-- Migration XXX: Description of the migration<br>
<br>
-- DEPENDS ON: 009_create_domains_table.sql<br>
-- Add any dependencies here<br>
<br>
-- Add your migration SQL here<br>
CREATE TABLE IF NOT EXISTS new_table (<br>
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),<br>
    name VARCHAR(255) NOT NULL,<br>
    created_at TIMESTAMPTZ DEFAULT NOW()<br>
);<br>
<br>
-- Add indexes if needed<br>
CREATE INDEX IF NOT EXISTS idx_new_table_name ON new_table(name);<br>
<br>
-- Add comments for documentation<br>
COMMENT ON TABLE new_table IS 'Description of the new table';<br>
```<br>
<br>
### **Migration Dependencies**<br>
- **Use DEPENDS ON comments** to specify dependencies<br>
- **Ensure proper order** - dependencies must be created first<br>
- **Test dependency resolution** before committing<br>
<br>
### **Rollback Support**<br>
- **Include DROP statements** where appropriate<br>
- **Test rollback scenarios** in development<br>
- **Document rollback procedures** for complex changes<br>
<br>
## 🧪 Testing Database Schema<br>
<br>
### **Unit Tests**<br>
```bash<br>
# Run database schema unit tests<br>
pytest tests/database/test_database_schema.py -v<br>
<br>
# Run specific test<br>
pytest tests/database/test_database_schema.py::TestDatabaseSchema::test_migration_files_exist -v<br>
```<br>
<br>
### **Integration Tests**<br>
```bash<br>
# Test migration application<br>
python scripts/validate_database_schema.py test<br>
<br>
# Test database connection<br>
python scripts/validate_database_schema.py validate<br>
```<br>
<br>
### **End-to-End Tests**<br>
```bash<br>
# Test complete database initialization<br>
./odras.sh clean-all -y<br>
./odras.sh up<br>
./odras.sh init-db<br>
<br>
# Verify all tables exist<br>
python -c "<br>
from backend.services.db import DatabaseService<br>
from backend.services.config import Settings<br>
db = DatabaseService(Settings())<br>
conn = db._conn()<br>
with conn.cursor() as cur:<br>
    cur.execute(\"SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'\")<br>
    tables = [row[0] for row in cur.fetchall()]<br>
    print('Tables:', tables)<br>
db._return(conn)<br>
"<br>
```<br>
<br>
## 🔧 Troubleshooting<br>
<br>
### **Common Issues**<br>
<br>
#### **Migration Not in odras.sh**<br>
```bash<br>
# Fix automatically<br>
python scripts/validate_database_schema.py --fix<br>
<br>
# Or manually update<br>
python scripts/database_schema_manager.py update-odras<br>
```<br>
<br>
#### **Migration Order Issues**<br>
```bash<br>
# Check migration order<br>
python scripts/database_schema_manager.py status<br>
<br>
# Fix order issues<br>
python scripts/database_schema_manager.py update-odras<br>
```<br>
<br>
#### **Database Connection Issues**<br>
```bash<br>
# Check Docker services<br>
docker ps | grep odras<br>
<br>
# Start services if needed<br>
./odras.sh up<br>
<br>
# Test connection<br>
python scripts/validate_database_schema.py validate<br>
```<br>
<br>
#### **Migration Dependencies**<br>
```bash<br>
# Check dependencies<br>
python scripts/database_schema_manager.py validate<br>
<br>
# Fix dependency issues<br>
# Edit migration files to add proper DEPENDS ON comments<br>
```<br>
<br>
### **Schema Validation Failures**<br>
<br>
#### **Missing Migrations**<br>
```bash<br>
# Check what's missing<br>
python scripts/validate_database_schema.py --verbose<br>
<br>
# Create missing migrations<br>
python scripts/database_schema_manager.py create "Missing migration description"<br>
```<br>
<br>
#### **Migration Syntax Errors**<br>
```bash<br>
# Check SQL syntax<br>
python scripts/validate_database_schema.py --verbose<br>
<br>
# Fix syntax errors in migration files<br>
# Test with PostgreSQL directly if needed<br>
```<br>
<br>
## 📊 Monitoring Schema Health<br>
<br>
### **Schema Status Check**<br>
```bash<br>
# Check current schema status<br>
python scripts/database_schema_manager.py status<br>
<br>
# Generate schema documentation<br>
python scripts/database_schema_manager.py docs --output DATABASE_SCHEMA.md<br>
```<br>
<br>
### **Migration History**<br>
```bash<br>
# View migration history<br>
python scripts/database_schema_manager.py status<br>
<br>
# Check migration checksums<br>
python scripts/validate_database_schema.py --verbose<br>
```<br>
<br>
### **Performance Monitoring**<br>
```bash<br>
# Test migration performance<br>
time python scripts/validate_database_schema.py test<br>
<br>
# Monitor database size<br>
docker exec odras_postgres psql -U postgres -d odras -c "SELECT pg_size_pretty(pg_database_size('odras'));"<br>
```<br>
<br>
## 🚀 Best Practices<br>
<br>
### **Development Workflow**<br>
1. **Always create migrations** for schema changes<br>
2. **Test migrations locally** before committing<br>
3. **Update odras.sh** when adding migrations<br>
4. **Run validation** before pushing<br>
5. **Test rollback scenarios** for complex changes<br>
<br>
### **Code Review Checklist**<br>
- [ ] Migration file created with proper naming<br>
- [ ] Migration includes proper comments and documentation<br>
- [ ] Dependencies are correctly specified<br>
- [ ] odras.sh init-db updated with new migration<br>
- [ ] Database tests pass<br>
- [ ] Schema validation passes<br>
- [ ] Rollback scenarios tested<br>
<br>
### **CI/CD Integration**<br>
- **Pre-commit hooks** validate schema consistency<br>
- **Pre-merge validation** includes database testing<br>
- **CI pipeline** runs comprehensive database tests<br>
- **Deployment** includes schema validation<br>
<br>
## 📝 Documentation<br>
<br>
### **Schema Documentation**<br>
```bash<br>
# Generate comprehensive schema documentation<br>
python scripts/database_schema_manager.py docs --output DATABASE_SCHEMA.md<br>
```<br>
<br>
### **Migration Documentation**<br>
- **Comment all migrations** with clear descriptions<br>
- **Document dependencies** and relationships<br>
- **Include rollback procedures** for complex changes<br>
- **Update schema documentation** when making changes<br>
<br>
## 🎯 Conclusion<br>
<br>
The ODRAS database schema management system ensures that:<br>
<br>
- **Schema changes are properly tracked** and tested<br>
- **odras.sh init-db stays up to date** automatically<br>
- **Database consistency** is maintained across environments<br>
- **Testing is comprehensive** and automated<br>
- **Rollback scenarios** are handled properly<br>
<br>
By following this guide, you can confidently make database schema changes while ensuring the system remains stable and testable.<br>
<br>
**Remember**: Database schema changes are critical - always test thoroughly before merging! 🚀<br>
<br>

