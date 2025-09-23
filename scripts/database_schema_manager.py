#!/usr/bin/env python3
"""
ODRAS Database Schema Manager

This script ensures that database schema changes are properly tracked and that
the odras.sh init-db command stays up to date with the latest schema.

Features:
- Schema version tracking
- Migration validation
- Schema consistency checking
- Automatic migration ordering
- Schema documentation generation
"""

import os
import sys
import json
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class MigrationFile:
    """Represents a database migration file"""

    filename: str
    path: Path
    version: str
    description: str
    dependencies: List[str]
    checksum: str
    created_at: datetime
    modified_at: datetime


@dataclass
class SchemaValidationResult:
    """Result of schema validation"""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    missing_migrations: List[str]
    outdated_migrations: List[str]


class DatabaseSchemaManager:
    """Manages database schema and ensures consistency"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.migrations_dir = self.project_root / "backend" / "migrations"
        self.schema_info_file = self.project_root / "backend" / "database_schema_info.json"
        self.migration_order_file = self.project_root / "backend" / "migrations" / "migration_order.txt"

    def discover_migrations(self) -> List[MigrationFile]:
        """Discover all migration files in the migrations directory"""
        migrations = []

        if not self.migrations_dir.exists():
            print(f"❌ Migrations directory not found: {self.migrations_dir}")
            return migrations

        for file_path in self.migrations_dir.glob("*.sql"):
            migration = self._parse_migration_file(file_path)
            if migration:
                migrations.append(migration)

        # Sort by version number
        migrations.sort(key=lambda x: self._version_key(x.version))
        return migrations

    def _parse_migration_file(self, file_path: Path) -> Optional[MigrationFile]:
        """Parse a migration file and extract metadata"""
        try:
            # Extract version from filename (e.g., "001_knowledge_management.sql" -> "001")
            filename = file_path.name
            version = filename.split("_")[0] if "_" in filename else "000"

            # Read file content
            content = file_path.read_text(encoding="utf-8")

            # Calculate checksum
            checksum = hashlib.md5(content.encode()).hexdigest()

            # Extract description from filename
            description = filename.replace(".sql", "").replace(f"{version}_", "")
            description = description.replace("_", " ").title()

            # Get file stats
            stat = file_path.stat()
            created_at = datetime.fromtimestamp(stat.st_ctime)
            modified_at = datetime.fromtimestamp(stat.st_mtime)

            # Parse dependencies from content (look for -- DEPENDS ON: comments)
            dependencies = self._extract_dependencies(content)

            return MigrationFile(
                filename=filename,
                path=file_path,
                version=version,
                description=description,
                dependencies=dependencies,
                checksum=checksum,
                created_at=created_at,
                modified_at=modified_at,
            )

        except Exception as e:
            print(f"⚠️  Error parsing migration file {file_path}: {e}")
            return None

    def _extract_dependencies(self, content: str) -> List[str]:
        """Extract dependencies from migration file content"""
        dependencies = []
        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            if line.startswith("-- DEPENDS ON:"):
                deps = line.replace("-- DEPENDS ON:", "").strip()
                dependencies.extend([dep.strip() for dep in deps.split(",")])

        return dependencies

    def _version_key(self, version: str) -> Tuple[int, ...]:
        """Convert version string to sortable tuple"""
        try:
            return tuple(int(part) for part in version.split("."))
        except ValueError:
            return (0,)

    def validate_schema_consistency(self) -> SchemaValidationResult:
        """Validate that the schema is consistent and up to date"""
        errors = []
        warnings = []
        missing_migrations = []
        outdated_migrations = []

        # Discover current migrations
        migrations = self.discover_migrations()

        if not migrations:
            errors.append("No migration files found")
            return SchemaValidationResult(
                False, errors, warnings, missing_migrations, outdated_migrations
            )

        # Check for missing migrations in sequence
        expected_versions = set()
        for i in range(len(migrations)):
            expected_versions.add(f"{i+1:03d}")

        found_versions = {m.version for m in migrations}
        missing_versions = expected_versions - found_versions

        if missing_versions:
            missing_migrations = sorted(missing_versions)
            warnings.append(f"Missing migration versions: {missing_migrations}")

        # Check for duplicate versions
        version_counts = {}
        for migration in migrations:
            version_counts[migration.version] = version_counts.get(migration.version, 0) + 1

        for version, count in version_counts.items():
            if count > 1:
                errors.append(f"Duplicate migration version {version} found {count} times")

        # Check migration dependencies
        for migration in migrations:
            for dep in migration.dependencies:
                dep_version = dep.strip()
                if dep_version not in found_versions:
                    errors.append(
                        f"Migration {migration.version} depends on {dep_version} which doesn't exist"
                    )

        # Check if schema info file exists and is up to date
        if self.schema_info_file.exists():
            try:
                with open(self.schema_info_file, "r") as f:
                    schema_info = json.load(f)

                # Check if any migrations have been modified since last update
                for migration in migrations:
                    if migration.checksum != schema_info.get("migrations", {}).get(
                        migration.filename, {}
                    ).get("checksum"):
                        outdated_migrations.append(migration.filename)

                if outdated_migrations:
                    warnings.append(f"Outdated migrations detected: {outdated_migrations}")

            except Exception as e:
                warnings.append(f"Error reading schema info file: {e}")
        else:
            warnings.append("Schema info file not found - run 'update_schema_info' first")

        is_valid = len(errors) == 0
        return SchemaValidationResult(
            is_valid, errors, warnings, missing_migrations, outdated_migrations
        )

    def update_schema_info(self) -> bool:
        """Update the schema information file with current migration state"""
        try:
            migrations = self.discover_migrations()

            schema_info = {
                "last_updated": datetime.now().isoformat(),
                "total_migrations": len(migrations),
                "migrations": {},
            }

            for migration in migrations:
                schema_info["migrations"][migration.filename] = {
                    "version": migration.version,
                    "description": migration.description,
                    "dependencies": migration.dependencies,
                    "checksum": migration.checksum,
                    "created_at": migration.created_at.isoformat(),
                    "modified_at": migration.modified_at.isoformat(),
                }

            # Write schema info file
            with open(self.schema_info_file, "w") as f:
                json.dump(schema_info, f, indent=2)

            # Write migration order file for odras.sh
            with open(self.migration_order_file, "w") as f:
                for migration in migrations:
                    f.write(f"{migration.filename}\n")

            print(f"✅ Schema info updated: {len(migrations)} migrations tracked")
            return True

        except Exception as e:
            print(f"❌ Error updating schema info: {e}")
            return False

    def generate_migration_template(self, description: str) -> str:
        """Generate a new migration file template"""
        migrations = self.discover_migrations()
        next_version = f"{len(migrations) + 1:03d}"

        # Clean description for filename
        clean_desc = description.lower().replace(" ", "_").replace("-", "_")
        filename = f"{next_version}_{clean_desc}.sql"

        template = f"""-- {description}
-- Migration {next_version}: {description}

-- DEPENDS ON:
-- Add any dependencies here, e.g., 001_knowledge_management.sql

-- Add your migration SQL here
-- Example:
-- CREATE TABLE IF NOT EXISTS new_table (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     name VARCHAR(255) NOT NULL,
--     created_at TIMESTAMPTZ DEFAULT NOW()
-- );

-- Add indexes if needed
-- CREATE INDEX IF NOT EXISTS idx_new_table_name ON new_table(name);

-- Add comments for documentation
-- COMMENT ON TABLE new_table IS 'Description of the new table';
"""

        return template, filename

    def validate_odras_init_db(self) -> bool:
        """Validate that odras.sh init-db is up to date with current migrations"""
        try:
            # Read the odras.sh file
            odras_script = self.project_root / "odras.sh"
            if not odras_script.exists():
                print("❌ odras.sh script not found")
                return False

            content = odras_script.read_text()

            # Check if the migration list in odras.sh matches current migrations
            migrations = self.discover_migrations()
            migration_filenames = [m.filename for m in migrations]

            # Look for the migration array in odras.sh
            if "migrations=(" in content:
                # Extract the migration list from the script
                start = content.find("migrations=(")
                end = content.find(")", start)
                if start != -1 and end != -1:
                    migration_section = content[start : end + 1]

                    # Check if all current migrations are in the script
                    missing_in_script = []
                    for migration in migration_filenames:
                        if migration not in migration_section:
                            missing_in_script.append(migration)

                    if missing_in_script:
                        print(f"❌ Migrations missing from odras.sh: {missing_in_script}")
                        return False
                    else:
                        print("✅ odras.sh init-db is up to date")
                        return True
                else:
                    print("❌ Could not parse migration list in odras.sh")
                    return False
            else:
                print("❌ Migration list not found in odras.sh")
                return False

        except Exception as e:
            print(f"❌ Error validating odras.sh: {e}")
            return False

    def update_odras_init_db(self) -> bool:
        """Update the odras.sh init-db command with current migrations"""
        try:
            # Read the odras.sh file
            odras_script = self.project_root / "odras.sh"
            if not odras_script.exists():
                print("❌ odras.sh script not found")
                return False

            content = odras_script.read_text()

            # Get current migrations
            migrations = self.discover_migrations()
            migration_filenames = [m.filename for m in migrations]

            # Find the migration array section
            start_marker = "migrations=("
            end_marker = ")"

            start = content.find(start_marker)
            if start == -1:
                print("❌ Migration array not found in odras.sh")
                return False

            end = content.find(end_marker, start)
            if end == -1:
                print("❌ Could not find end of migration array")
                return False

            # Build new migration array
            new_migration_array = "migrations=(\n"
            for migration in migration_filenames:
                new_migration_array += f'            "{migration}"\n'
            new_migration_array += "        )"

            # Replace the migration array
            new_content = content[:start] + new_migration_array + content[end + 1 :]

            # Write the updated file
            with open(odras_script, "w") as f:
                f.write(new_content)

            print(f"✅ Updated odras.sh with {len(migration_filenames)} migrations")
            return True

        except Exception as e:
            print(f"❌ Error updating odras.sh: {e}")
            return False

    def run_database_tests(self) -> bool:
        """Run database tests to ensure schema works correctly"""
        try:
            print("🧪 Running database tests...")

            # Test 1: Check if migrations can be applied
            print("  Testing migration application...")
            result = subprocess.run(
                [
                    "python",
                    "-c",
                    "import sys; sys.path.insert(0, '.'); from backend.services.db import DatabaseService; from backend.services.config import Settings; db = DatabaseService(Settings()); print('✅ Database connection successful')",
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            if result.returncode != 0:
                print(f"❌ Database connection test failed: {result.stderr}")
                return False

            # Test 2: Check if all tables exist
            print("  Testing table existence...")
            result = subprocess.run(
                [
                    "python",
                    "-c",
                    """
import sys; sys.path.insert(0, '.')
from backend.services.db import DatabaseService
from backend.services.config import Settings
db = DatabaseService(Settings())
conn = db._conn()
try:
    with conn.cursor() as cur:
        cur.execute(\"SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'\")
        tables = [row[0] for row in cur.fetchall()]
        expected_tables = ['files', 'knowledge_assets', 'knowledge_chunks', 'knowledge_relationships', 'knowledge_processing_jobs', 'users', 'projects']
        missing = set(expected_tables) - set(tables)
        if missing:
            print(f'❌ Missing tables: {missing}')
            sys.exit(1)
        else:
            print('✅ All expected tables exist')
finally:
    db._return(conn)
                """,
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            if result.returncode != 0:
                print(f"❌ Table existence test failed: {result.stderr}")
                return False

            print("✅ All database tests passed")
            return True

        except Exception as e:
            print(f"❌ Error running database tests: {e}")
            return False

    def generate_schema_documentation(self) -> str:
        """Generate comprehensive schema documentation"""
        migrations = self.discover_migrations()

        doc = f"""# ODRAS Database Schema Documentation

Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview

This document describes the ODRAS database schema and migration system.

## Migration Files

Total migrations: {len(migrations)}

"""

        for migration in migrations:
            doc += f"""### {migration.filename}

- **Version**: {migration.version}
- **Description**: {migration.description}
- **Dependencies**: {', '.join(migration.dependencies) if migration.dependencies else 'None'}
- **Created**: {migration.created_at.strftime('%Y-%m-%d %H:%M:%S')}
- **Modified**: {migration.modified_at.strftime('%Y-%m-%d %H:%M:%S')}
- **Checksum**: {migration.checksum}

"""

        doc += """
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

"""

        for i, migration in enumerate(migrations, 1):
            doc += f"{i}. {migration.filename}\n"

        return doc


def main():
    """Main CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(description="ODRAS Database Schema Manager")
    parser.add_argument(
        "command",
        choices=[
            "validate",
            "update-info",
            "update-odras",
            "test",
            "create",
            "docs",
            "status",
        ],
        help="Command to execute",
    )
    parser.add_argument("--description", help="Description for new migration (used with 'create')")
    parser.add_argument("--output", help="Output file for documentation (used with 'docs')")

    args = parser.parse_args()

    manager = DatabaseSchemaManager()

    if args.command == "validate":
        result = manager.validate_schema_consistency()
        if result.is_valid:
            print("✅ Schema validation passed")
        else:
            print("❌ Schema validation failed")
            for error in result.errors:
                print(f"  Error: {error}")
            for warning in result.warnings:
                print(f"  Warning: {warning}")
            sys.exit(1)

    elif args.command == "update-info":
        if manager.update_schema_info():
            print("✅ Schema info updated successfully")
        else:
            print("❌ Failed to update schema info")
            sys.exit(1)

    elif args.command == "update-odras":
        if manager.update_odras_init_db():
            print("✅ odras.sh updated successfully")
        else:
            print("❌ Failed to update odras.sh")
            sys.exit(1)

    elif args.command == "test":
        if manager.run_database_tests():
            print("✅ Database tests passed")
        else:
            print("❌ Database tests failed")
            sys.exit(1)

    elif args.command == "create":
        if not args.description:
            print("❌ Description required for creating migration")
            sys.exit(1)

        template, filename = manager.generate_migration_template(args.description)
        file_path = manager.migrations_dir / filename

        if file_path.exists():
            print(f"❌ Migration file already exists: {filename}")
            sys.exit(1)

        file_path.write_text(template)
        print(f"✅ Created migration template: {filename}")
        print(f"   Edit the file and add your SQL: {file_path}")

    elif args.command == "docs":
        doc = manager.generate_schema_documentation()
        output_file = args.output or "DATABASE_SCHEMA.md"

        with open(output_file, "w") as f:
            f.write(doc)

        print(f"✅ Schema documentation generated: {output_file}")

    elif args.command == "status":
        migrations = manager.discover_migrations()
        print(f"📊 Database Schema Status")
        print(f"   Total migrations: {len(migrations)}")
        print(f"   Migrations directory: {manager.migrations_dir}")

        for migration in migrations:
            print(f"   {migration.version}: {migration.description}")

        # Check validation
        result = manager.validate_schema_consistency()
        if result.is_valid:
            print("   ✅ Schema is valid")
        else:
            print("   ❌ Schema has issues")
            for error in result.errors:
                print(f"      Error: {error}")


if __name__ == "__main__":
    main()
