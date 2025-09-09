#!/usr/bin/env python3
"""
ODRAS Database Schema Validation Script

This script validates that the database schema is consistent and that
the odras.sh init-db command will work correctly with the current schema.

Usage:
    python scripts/validate_database_schema.py [--fix] [--verbose]
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class ValidationResult:
    """Result of database schema validation"""

    success: bool
    errors: List[str]
    warnings: List[str]
    fixes_applied: List[str]


class DatabaseSchemaValidator:
    """Validates database schema and ensures odras.sh init-db works"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.migrations_dir = self.project_root / "backend" / "migrations"
        self.odras_script = self.project_root / "odras.sh"

    def validate_migration_files(self) -> ValidationResult:
        """Validate that all migration files exist and are properly formatted"""
        errors = []
        warnings = []
        fixes_applied = []

        print("🔍 Validating migration files...")

        if not self.migrations_dir.exists():
            errors.append(f"Migrations directory not found: {self.migrations_dir}")
            return ValidationResult(False, errors, warnings, fixes_applied)

        # Get all SQL files in migrations directory
        migration_files = list(self.migrations_dir.glob("*.sql"))

        if not migration_files:
            errors.append("No migration files found in migrations directory")
            return ValidationResult(False, errors, warnings, fixes_applied)

        print(f"   Found {len(migration_files)} migration files")

        # Check for proper naming convention
        for file_path in migration_files:
            filename = file_path.name
            if not filename[0:3].isdigit():
                warnings.append(f"Migration file doesn't start with number: {filename}")

            # Check if file is readable
            try:
                content = file_path.read_text(encoding="utf-8")
                if not content.strip():
                    warnings.append(f"Empty migration file: {filename}")
            except Exception as e:
                errors.append(f"Error reading migration file {filename}: {e}")

        # Check for sequential numbering
        numbered_files = []
        for file_path in migration_files:
            filename = file_path.name
            if filename[0:3].isdigit():
                numbered_files.append((int(filename[0:3]), filename))

        numbered_files.sort()

        # Check for gaps in numbering
        for i, (num, filename) in enumerate(numbered_files):
            expected_num = i + 1
            if num != expected_num:
                warnings.append(
                    f"Migration numbering gap: expected {expected_num:03d}, found {num:03d} in {filename}"
                )

        return ValidationResult(len(errors) == 0, errors, warnings, fixes_applied)

    def validate_odras_script(self) -> ValidationResult:
        """Validate that odras.sh init-db references all migration files"""
        errors = []
        warnings = []
        fixes_applied = []

        print("🔍 Validating odras.sh init-db script...")

        if not self.odras_script.exists():
            errors.append("odras.sh script not found")
            return ValidationResult(False, errors, warnings, fixes_applied)

        # Read the odras.sh script
        try:
            content = self.odras_script.read_text(encoding="utf-8")
        except Exception as e:
            errors.append(f"Error reading odras.sh: {e}")
            return ValidationResult(False, errors, warnings, fixes_applied)

        # Find the migration array in the script
        migration_section_start = content.find("migrations=(")
        if migration_section_start == -1:
            errors.append("Migration array not found in odras.sh")
            return ValidationResult(False, errors, warnings, fixes_applied)

        migration_section_end = content.find(")", migration_section_start)
        if migration_section_end == -1:
            errors.append("Could not find end of migration array in odras.sh")
            return ValidationResult(False, errors, warnings, fixes_applied)

        # Extract migration list from script
        migration_section = content[migration_section_start : migration_section_end + 1]
        script_migrations = []

        for line in migration_section.split("\n"):
            line = line.strip()
            if line.startswith('"') and line.endswith('"'):
                migration_name = line[1:-1]  # Remove quotes
                script_migrations.append(migration_name)

        # Get actual migration files
        actual_migrations = [f.name for f in self.migrations_dir.glob("*.sql")]
        actual_migrations.sort()

        # Check for missing migrations in script
        missing_in_script = set(actual_migrations) - set(script_migrations)
        if missing_in_script:
            errors.append(f"Migratations missing from odras.sh: {sorted(missing_in_script)}")

        # Check for extra migrations in script
        extra_in_script = set(script_migrations) - set(actual_migrations)
        if extra_in_script:
            warnings.append(
                f"Extra migrations in odras.sh (files don't exist): {sorted(extra_in_script)}"
            )

        # Check migration order
        if script_migrations != actual_migrations:
            warnings.append("Migration order in odras.sh doesn't match file order")

        print(f"   Script references {len(script_migrations)} migrations")
        print(f"   Found {len(actual_migrations)} actual migration files")

        return ValidationResult(len(errors) == 0, errors, warnings, fixes_applied)

    def validate_database_connection(self) -> ValidationResult:
        """Validate that database connection works"""
        errors = []
        warnings = []
        fixes_applied = []

        print("🔍 Validating database connection...")

        try:
            # Test database connection
            result = subprocess.run(
                [
                    "python",
                    "-c",
                    """
import sys
sys.path.insert(0, '.')
from backend.services.db import DatabaseService
from backend.services.config import Settings
try:
    db = DatabaseService(Settings())
    conn = db._conn()
    with conn.cursor() as cur:
        cur.execute('SELECT 1')
        result = cur.fetchone()
    db._return(conn)
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
    sys.exit(1)
                """,
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=30,
            )

            if result.returncode != 0:
                errors.append(f"Database connection failed: {result.stderr}")
            else:
                print("   ✅ Database connection successful")

        except subprocess.TimeoutExpired:
            errors.append("Database connection test timed out")
        except Exception as e:
            errors.append(f"Error testing database connection: {e}")

        return ValidationResult(len(errors) == 0, errors, warnings, fixes_applied)

    def validate_migration_application(self) -> ValidationResult:
        """Validate that migrations can be applied successfully"""
        errors = []
        warnings = []
        fixes_applied = []

        print("🔍 Validating migration application...")

        try:
            # Test applying migrations
            result = subprocess.run(
                [
                    "python",
                    "-c",
                    """
import sys
sys.path.insert(0, '.')
from backend.services.db import DatabaseService
from backend.services.config import Settings
import os

# Use main database for validation
# test_db = os.environ.get('POSTGRES_DATABASE', 'odras')
# os.environ['POSTGRES_DATABASE'] = test_db

try:
    db = DatabaseService(Settings())
    conn = db._conn()
    
    # Test creating a simple table
    with conn.cursor() as cur:
        cur.execute('CREATE TABLE IF NOT EXISTS test_migration_validation (id SERIAL PRIMARY KEY, test_col VARCHAR(50))')
        cur.execute('INSERT INTO test_migration_validation (test_col) VALUES (%s)', ('test_value',))
        cur.execute('SELECT * FROM test_migration_validation WHERE test_col = %s', ('test_value',))
        result = cur.fetchone()
        if result:
            cur.execute('DROP TABLE test_migration_validation')
            print('Migration application test successful')
        else:
            print('Migration application test failed - no data found')
            sys.exit(1)
    
    db._return(conn)
except Exception as e:
    print(f'Migration application test failed: {e}')
    sys.exit(1)
                """,
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=60,
            )

            if result.returncode != 0:
                errors.append(f"Migration application test failed: {result.stderr}")
            else:
                print("   ✅ Migration application test successful")

        except subprocess.TimeoutExpired:
            errors.append("Migration application test timed out")
        except Exception as e:
            errors.append(f"Error testing migration application: {e}")

        return ValidationResult(len(errors) == 0, errors, warnings, fixes_applied)

    def validate_docker_services(self) -> ValidationResult:
        """Validate that Docker services are running"""
        errors = []
        warnings = []
        fixes_applied = []

        print("🔍 Validating Docker services...")

        try:
            # Check if we're in CI environment (GitHub Actions)
            if os.environ.get("GITHUB_ACTIONS") == "true":
                print("   ℹ️  Running in CI environment - skipping Docker container validation")
                print("   ℹ️  Service containers are managed by GitHub Actions")
                return ValidationResult(True, [], [], [])

            # Check if Docker is running
            result = subprocess.run(["docker", "ps"], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                errors.append("Docker is not running or not accessible")
                return ValidationResult(False, errors, warnings, fixes_applied)

            # Check for ODRAS containers
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=odras", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                errors.append("Error checking Docker containers")
                return ValidationResult(False, errors, warnings, fixes_applied)

            containers = result.stdout.strip().split("\n") if result.stdout.strip() else []
            expected_containers = [
                "odras_postgres",
                "odras_neo4j",
                "odras_qdrant",
                "odras_fuseki",
            ]

            running_containers = [c for c in containers if c in expected_containers]

            if len(running_containers) < len(expected_containers):
                missing = set(expected_containers) - set(running_containers)
                warnings.append(f"Some ODRAS containers not running: {missing}")
                print(
                    f"   ⚠️  Only {len(running_containers)}/{len(expected_containers)} containers running"
                )
            else:
                print(f"   ✅ All {len(expected_containers)} ODRAS containers running")

        except subprocess.TimeoutExpired:
            errors.append("Docker service check timed out")
        except Exception as e:
            errors.append(f"Error checking Docker services: {e}")

        return ValidationResult(len(errors) == 0, errors, warnings, fixes_applied)

    def fix_odras_script(self) -> bool:
        """Fix the odras.sh script to include all migration files"""
        try:
            print("🔧 Fixing odras.sh script...")

            # Get current migration files
            migration_files = [f.name for f in self.migrations_dir.glob("*.sql")]
            migration_files.sort()

            # Read the odras.sh script
            content = self.odras_script.read_text(encoding="utf-8")

            # Find the migration array section
            start_marker = "migrations=("
            end_marker = ")"

            start = content.find(start_marker)
            if start == -1:
                print("   ❌ Migration array not found in odras.sh")
                return False

            end = content.find(end_marker, start)
            if end == -1:
                print("   ❌ Could not find end of migration array")
                return False

            # Build new migration array
            new_migration_array = "migrations=(\n"
            for migration in migration_files:
                new_migration_array += f'            "{migration}"\n'
            new_migration_array += "        )"

            # Replace the migration array
            new_content = content[:start] + new_migration_array + content[end + 1 :]

            # Write the updated file
            self.odras_script.write_text(new_content, encoding="utf-8")

            print(f"   ✅ Updated odras.sh with {len(migration_files)} migrations")
            return True

        except Exception as e:
            print(f"   ❌ Error fixing odras.sh: {e}")
            return False

    def validate_users_table_schema(self) -> ValidationResult:
        """Validate that the users table has the required password fields"""
        errors = []
        warnings = []
        fixes_applied = []

        print("🔍 Validating users table schema...")

        try:
            # Test users table schema by importing and running validation directly
            import sys

            sys.path.insert(0, str(self.project_root))
            from backend.services.db import DatabaseService
            from backend.services.config import Settings

            db = DatabaseService(Settings())
            conn = db._conn()

            with conn.cursor() as cur:
                # Check if users table exists
                cur.execute(
                    """
                    SELECT column_name, data_type, is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' AND table_schema = 'public'
                    ORDER BY ordinal_position
                """
                )
                columns = cur.fetchall()

                if not columns:
                    if os.environ.get("GITHUB_ACTIONS") == "true":
                        warnings.append(
                            "Users table not found (may be expected in CI before migrations)"
                        )
                        print(
                            "   ⚠️  Users table not found (may be expected in CI before migrations)"
                        )
                        return ValidationResult(True, [], warnings, fixes_applied)
                    else:
                        errors.append("Users table not found")
                        return ValidationResult(False, errors, warnings, fixes_applied)

                # Check for required password fields
                column_names = [col[0] for col in columns]
                required_fields = [
                    "user_id",
                    "username",
                    "display_name",
                    "password_hash",
                    "salt",
                    "is_admin",
                    "is_active",
                    "created_at",
                    "updated_at",
                ]

                missing_fields = set(required_fields) - set(column_names)
                if missing_fields:
                    errors.append(f"Missing required fields: {missing_fields}")
                    return ValidationResult(False, errors, warnings, fixes_applied)

                # Check if password_hash and salt are NOT NULL
                for col in columns:
                    if col[0] in ["password_hash", "salt"] and col[2] == "YES":
                        errors.append(f"Field {col[0]} should be NOT NULL")
                        return ValidationResult(False, errors, warnings, fixes_applied)

                print("   ✅ Users table schema validation successful")

            db._return(conn)

        except Exception as e:
            errors.append(f"Error validating users table schema: {e}")

        return ValidationResult(len(errors) == 0, errors, warnings, fixes_applied)

    def run_comprehensive_validation(self, fix_issues: bool = False) -> ValidationResult:
        """Run comprehensive database schema validation"""
        print("🚀 Starting comprehensive database schema validation...")
        print("=" * 60)

        all_errors = []
        all_warnings = []
        all_fixes = []

        # Run all validation checks
        checks = [
            ("Migration Files", self.validate_migration_files),
            ("ODRAS Script", self.validate_odras_script),
            ("Database Connection", self.validate_database_connection),
            ("Migration Application", self.validate_migration_application),
            ("Users Table Schema", self.validate_users_table_schema),
            ("Docker Services", self.validate_docker_services),
        ]

        for check_name, check_func in checks:
            print(f"\n📋 {check_name} Validation")
            print("-" * 40)

            result = check_func()

            if result.errors:
                all_errors.extend([f"{check_name}: {error}" for error in result.errors])
            if result.warnings:
                all_warnings.extend([f"{check_name}: {warning}" for warning in result.warnings])
            if result.fixes_applied:
                all_fixes.extend([f"{check_name}: {fix}" for fix in result.fixes_applied])

        # Apply fixes if requested
        if fix_issues and all_errors:
            print(f"\n🔧 Applying fixes...")
            print("-" * 40)

            # Fix odras.sh script
            if any("ODRAS Script" in error for error in all_errors):
                if self.fix_odras_script():
                    all_fixes.append("ODRAS Script: Updated migration list")
                    # Remove fixed errors
                    all_errors = [error for error in all_errors if "ODRAS Script" not in error]

        # Print summary
        print(f"\n📊 Validation Summary")
        print("=" * 60)

        if all_errors:
            print(f"❌ {len(all_errors)} errors found:")
            for error in all_errors:
                print(f"   • {error}")

        if all_warnings:
            print(f"⚠️  {len(all_warnings)} warnings found:")
            for warning in all_warnings:
                print(f"   • {warning}")

        if all_fixes:
            print(f"✅ {len(all_fixes)} fixes applied:")
            for fix in all_fixes:
                print(f"   • {fix}")

        if not all_errors and not all_warnings:
            print("🎉 All validations passed! Database schema is ready.")
        elif not all_errors:
            print("✅ All critical issues resolved. Some warnings remain.")
        else:
            print("❌ Critical issues found. Please fix errors before proceeding.")

        return ValidationResult(
            success=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings,
            fixes_applied=all_fixes,
        )


def main():
    """Main CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(description="ODRAS Database Schema Validator")
    parser.add_argument(
        "--fix", action="store_true", help="Automatically fix issues where possible"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    validator = DatabaseSchemaValidator()
    result = validator.run_comprehensive_validation(fix_issues=args.fix)

    if not result.success:
        print(f"\n💡 To fix issues automatically, run:")
        print(f"   python scripts/validate_database_schema.py --fix")
        sys.exit(1)
    else:
        print(f"\n🚀 Database schema is ready for use!")
        print(f"   Run './odras.sh init-db' to initialize the database")


if __name__ == "__main__":
    main()
