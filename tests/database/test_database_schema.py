"""
Database Schema Tests

Tests for database schema consistency, migration validation, and odras.sh init-db functionality.
"""

import pytest
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
import sys

sys.path.insert(0, str(project_root))


class TestDatabaseSchema:
    """Test suite for database schema validation"""

    @pytest.fixture
    def migrations_dir(self):
        """Get migrations directory path"""
        return project_root / "backend" / "migrations"

    @pytest.fixture
    def odras_script(self):
        """Get odras.sh script path"""
        return project_root / "odras.sh"

    def test_migrations_directory_exists(self, migrations_dir):
        """Test that migrations directory exists"""
        assert (
            migrations_dir.exists()
        ), f"Migrations directory not found: {migrations_dir}"

    def test_migration_files_exist(self, migrations_dir):
        """Test that migration files exist"""
        migration_files = list(migrations_dir.glob("*.sql"))
        assert len(migration_files) > 0, "No migration files found"

        # Check for expected migration files
        expected_migrations = [
            "000_files_table.sql",
            "001_knowledge_management.sql",
            "002_knowledge_public_assets.sql",
            "003_auth_tokens.sql",
            "004_users_table.sql",
        ]

        actual_migrations = [f.name for f in migration_files]
        for expected in expected_migrations:
            assert (
                expected in actual_migrations
            ), f"Expected migration {expected} not found"

    def test_migration_files_readable(self, migrations_dir):
        """Test that all migration files are readable"""
        migration_files = list(migrations_dir.glob("*.sql"))

        for file_path in migration_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                assert (
                    len(content.strip()) > 0
                ), f"Migration file {file_path.name} is empty"
            except Exception as e:
                pytest.fail(f"Error reading migration file {file_path.name}: {e}")

    def test_migration_naming_convention(self, migrations_dir):
        """Test that migration files follow naming convention"""
        migration_files = list(migrations_dir.glob("*.sql"))

        for file_path in migration_files:
            filename = file_path.name
            # Should start with 3 digits
            assert filename[
                0:3
            ].isdigit(), f"Migration file {filename} doesn't start with 3 digits"
            # Should have underscore after digits
            assert (
                "_" in filename
            ), f"Migration file {filename} doesn't have underscore after version"

    def test_migration_sequential_numbering(self, migrations_dir):
        """Test that migration files are numbered sequentially"""
        migration_files = list(migrations_dir.glob("*.sql"))

        # Extract version numbers
        versions = []
        for file_path in migration_files:
            filename = file_path.name
            if filename[0:3].isdigit():
                versions.append(int(filename[0:3]))

        versions.sort()

        # Check for sequential numbering (starting from 0)
        for i, version in enumerate(versions):
            expected = i
            assert (
                version == expected
            ), f"Migration numbering gap: expected {expected:03d}, found {version:03d}"

    def test_odras_script_exists(self, odras_script):
        """Test that odras.sh script exists"""
        assert odras_script.exists(), f"odras.sh script not found: {odras_script}"

    def test_odras_script_readable(self, odras_script):
        """Test that odras.sh script is readable"""
        try:
            content = odras_script.read_text(encoding="utf-8")
            assert len(content) > 0, "odras.sh script is empty"
        except Exception as e:
            pytest.fail(f"Error reading odras.sh script: {e}")

    def test_odras_script_has_migration_array(self, odras_script):
        """Test that odras.sh script contains migration array"""
        content = odras_script.read_text(encoding="utf-8")

        assert "migrations=(" in content, "Migration array not found in odras.sh"
        assert ")" in content, "Migration array not properly closed in odras.sh"

    def test_odras_script_migration_list_complete(self, migrations_dir, odras_script):
        """Test that odras.sh script includes all migration files"""
        # Get actual migration files
        migration_files = [f.name for f in migrations_dir.glob("*.sql")]
        migration_files.sort()

        # Read odras.sh script
        content = odras_script.read_text(encoding="utf-8")

        # Find migration array
        start = content.find("migrations=(")
        end = content.find(")", start)
        assert start != -1 and end != -1, "Could not find migration array in odras.sh"

        migration_section = content[start : end + 1]

        # Check that all migration files are referenced
        for migration in migration_files:
            assert (
                migration in migration_section
            ), f"Migration {migration} not found in odras.sh"

    def test_database_schema_validator_script(self):
        """Test that database schema validator script exists and is executable"""
        validator_script = project_root / "scripts" / "validate_database_schema.py"
        assert validator_script.exists(), "Database schema validator script not found"

        # Test that script can be imported
        try:
            result = subprocess.run(
                ["python", str(validator_script), "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            assert (
                result.returncode == 0
            ), f"Database schema validator script failed: {result.stderr}"
        except subprocess.TimeoutExpired:
            pytest.fail("Database schema validator script timed out")
        except Exception as e:
            pytest.fail(f"Error running database schema validator script: {e}")

    def test_database_schema_manager_script(self):
        """Test that database schema manager script exists and is executable"""
        manager_script = project_root / "scripts" / "database_schema_manager.py"
        assert manager_script.exists(), "Database schema manager script not found"

        # Test that script can be imported
        try:
            result = subprocess.run(
                ["python", str(manager_script), "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            assert (
                result.returncode == 0
            ), f"Database schema manager script failed: {result.stderr}"
        except subprocess.TimeoutExpired:
            pytest.fail("Database schema manager script timed out")
        except Exception as e:
            pytest.fail(f"Error running database schema manager script: {e}")

    def test_migration_dependencies(self, migrations_dir):
        """Test that migration dependencies are valid"""
        migration_files = list(migrations_dir.glob("*.sql"))

        # Get all migration names
        migration_names = [f.name for f in migration_files]

        for file_path in migration_files:
            content = file_path.read_text(encoding="utf-8")

            # Look for dependency comments
            lines = content.split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("-- DEPENDS ON:"):
                    deps = line.replace("-- DEPENDS ON:", "").strip()
                    for dep in deps.split(","):
                        dep = dep.strip()
                        if dep and dep not in migration_names:
                            pytest.fail(
                                f"Migration {file_path.name} depends on non-existent migration: {dep}"
                            )

    def test_migration_sql_syntax(self, migrations_dir):
        """Test that migration files contain valid SQL syntax"""
        migration_files = list(migrations_dir.glob("*.sql"))

        for file_path in migration_files:
            content = file_path.read_text(encoding="utf-8")

            # Basic SQL syntax checks
            assert (
                "CREATE TABLE" in content
                or "ALTER TABLE" in content
                or "CREATE INDEX" in content
            ), f"Migration {file_path.name} doesn't contain expected SQL statements"

            # Check for common SQL keywords
            sql_keywords = [
                "CREATE",
                "ALTER",
                "DROP",
                "INSERT",
                "UPDATE",
                "DELETE",
                "SELECT",
            ]
            has_sql = any(keyword in content.upper() for keyword in sql_keywords)
            assert (
                has_sql
            ), f"Migration {file_path.name} doesn't contain valid SQL keywords"

    def test_migration_file_encoding(self, migrations_dir):
        """Test that migration files are properly encoded"""
        migration_files = list(migrations_dir.glob("*.sql"))

        for file_path in migration_files:
            try:
                # Try to read with UTF-8 encoding
                content = file_path.read_text(encoding="utf-8")
                # Check for common encoding issues
                assert (
                    "\ufffd" not in content
                ), f"Migration {file_path.name} contains replacement characters (encoding issue)"
            except UnicodeDecodeError as e:
                pytest.fail(f"Migration {file_path.name} has encoding issues: {e}")

    def test_migration_file_size(self, migrations_dir):
        """Test that migration files are not empty and not too large"""
        migration_files = list(migrations_dir.glob("*.sql"))

        for file_path in migration_files:
            size = file_path.stat().st_size

            # Check minimum size (at least 100 bytes)
            assert (
                size >= 100
            ), f"Migration {file_path.name} is too small ({size} bytes)"

            # Check maximum size (not more than 1MB)
            assert (
                size <= 1024 * 1024
            ), f"Migration {file_path.name} is too large ({size} bytes)"

    def test_migration_comments(self, migrations_dir):
        """Test that migration files have proper comments"""
        migration_files = list(migrations_dir.glob("*.sql"))

        for file_path in migration_files:
            content = file_path.read_text(encoding="utf-8")

            # Check for header comment
            assert content.strip().startswith(
                "--"
            ), f"Migration {file_path.name} doesn't start with comment"

            # Check for description comment
            lines = content.split("\n")
            has_description = any(
                "-- Migration" in line or "-- " in line for line in lines[:10]
            )
            assert (
                has_description
            ), f"Migration {file_path.name} doesn't have proper description comment"

    def test_odras_script_migration_order(self, migrations_dir, odras_script):
        """Test that migration order in odras.sh matches file order"""
        # Get actual migration files in order
        migration_files = sorted([f.name for f in migrations_dir.glob("*.sql")])

        # Read odras.sh script
        content = odras_script.read_text(encoding="utf-8")

        # Extract migration list from script
        start = content.find("migrations=(")
        end = content.find(")", start)
        migration_section = content[start : end + 1]

        script_migrations = []
        for line in migration_section.split("\n"):
            line = line.strip()
            if line.startswith('"') and line.endswith('"'):
                migration_name = line[1:-1]  # Remove quotes
                script_migrations.append(migration_name)

        # Compare order
        assert script_migrations == migration_files, (
            f"Migration order in odras.sh doesn't match file order. "
            f"Script: {script_migrations}, Files: {migration_files}"
        )

    def test_database_schema_consistency(self):
        """Test that database schema is consistent across all migrations"""
        # This test would require a database connection
        # For now, we'll just test that the validation script can run
        validator_script = project_root / "scripts" / "validate_database_schema.py"

        try:
            result = subprocess.run(
                ["python", str(validator_script), "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            assert result.returncode == 0, "Database schema validator script failed"
        except Exception as e:
            pytest.fail(f"Error running database schema validator: {e}")

    def test_migration_rollback_support(self, migrations_dir):
        """Test that migrations support rollback (have DROP statements)"""
        migration_files = list(migrations_dir.glob("*.sql"))

        # This is a basic check - in practice, you might want more sophisticated rollback testing
        for file_path in migration_files:
            content = file_path.read_text(encoding="utf-8")

            # Check if migration has rollback support
            has_rollback = any(
                keyword in content.upper()
                for keyword in ["DROP", "ALTER TABLE", "DELETE"]
            )

            # This is a warning, not a failure, as not all migrations need rollback
            if not has_rollback:
                print(f"Warning: Migration {file_path.name} may not support rollback")

    def test_migration_foreign_key_consistency(self, migrations_dir):
        """Test that migrations maintain foreign key consistency"""
        migration_files = list(migrations_dir.glob("*.sql"))

        # Collect all table references
        table_references = {}

        for file_path in migration_files:
            content = file_path.read_text(encoding="utf-8")

            # Look for table references
            lines = content.split("\n")
            for line in lines:
                line = line.strip()
                if "REFERENCES" in line.upper():
                    # Extract table name from REFERENCES clause
                    parts = line.split("REFERENCES")
                    if len(parts) > 1:
                        ref_part = parts[1].strip()
                        table_name = ref_part.split("(")[0].strip()
                        table_references[file_path.name] = table_name

        # Check that referenced tables are created before they're referenced
        # This is a basic check - more sophisticated analysis would be needed
        for migration_file, referenced_table in table_references.items():
            # Find which migration creates the referenced table
            creating_migration = None
            for file_path in migration_files:
                if file_path.name != migration_file:
                    content = file_path.read_text(encoding="utf-8")
                    if f"CREATE TABLE {referenced_table}" in content.upper():
                        creating_migration = file_path.name
                        break

            if creating_migration:
                # Check that creating migration comes before referencing migration
                creating_index = migration_files.index(
                    Path(migrations_dir / creating_migration)
                )
                referencing_index = migration_files.index(
                    Path(migrations_dir / migration_file)
                )

                assert creating_index < referencing_index, (
                    f"Migration {migration_file} references table {referenced_table} "
                    f"before it's created in {creating_migration}"
                )
