#!/usr/bin/env python3
"""
ODRAS Test Summary Script

Provides an overview of all available tests and quick commands to run them.
"""

import os
import sys
from pathlib import Path
import subprocess
from typing import List, Dict

# Color codes
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RESET = '\033[0m'
BOLD = '\033[1m'


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{BLUE}{BOLD}{'='*70}{RESET}")
    print(f"{BLUE}{BOLD}{text:^70}{RESET}")
    print(f"{BLUE}{BOLD}{'='*70}{RESET}\n")


def print_section(text: str):
    """Print a section header"""
    print(f"\n{GREEN}{BOLD}{text}{RESET}")
    print(f"{GREEN}{'─' * len(text)}{RESET}")


def get_test_files(directory: Path) -> List[Path]:
    """Get all test files in a directory"""
    return sorted(directory.glob("test_*.py"))


def count_test_functions(file_path: Path) -> int:
    """Count test functions in a file"""
    count = 0
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            count = content.count("def test_") + content.count("async def test_")
    except:
        pass
    return count


def main():
    """Main function"""
    project_root = Path(__file__).parent.parent
    tests_dir = project_root / "tests"

    print_header("ODRAS Test Suite Summary")

    # Gather test information
    test_categories = {
        "Database Tests": tests_dir / "database",
        "API Tests": tests_dir / "api",
        "Unit Tests": tests_dir / "unit",
        "Integration Tests": tests_dir / "integration"
    }

    total_files = 0
    total_tests = 0

    # Core test files
    print_section("Core Test Files")
    core_tests = [
        ("Comprehensive Suite", tests_dir / "test_comprehensive_suite.py"),
        ("Configuration", tests_dir / "conftest.py")
    ]

    for name, path in core_tests:
        if path.exists():
            test_count = count_test_functions(path)
            print(f"  • {name}: {path.name}")
            if test_count > 0:
                print(f"    └─ {test_count} test functions")

    # Category breakdown
    for category, directory in test_categories.items():
        if directory.exists():
            test_files = get_test_files(directory)
            if test_files:
                print_section(category)
                category_tests = 0

                for test_file in test_files:
                    test_count = count_test_functions(test_file)
                    category_tests += test_count
                    total_files += 1

                    print(f"  • {test_file.name}")
                    if test_count > 0:
                        print(f"    └─ {test_count} test functions")

                    # Special descriptions for key files
                    if test_file.name == "test_full_stack_api.py":
                        print(f"    {YELLOW}└─ Complete end-to-end API testing{RESET}")
                    elif test_file.name == "test_crud_operations.py":
                        print(f"    {YELLOW}└─ All CRUD operations for major entities{RESET}")
                    elif test_file.name == "test_edge_cases.py":
                        print(f"    {YELLOW}└─ Error handling and edge cases{RESET}")
                    elif test_file.name == "test_database_schema.py":
                        print(f"    {YELLOW}└─ Migration and schema validation{RESET}")

                total_tests += category_tests
                print(f"\n  {GREEN}Total: {len(test_files)} files, ~{category_tests} tests{RESET}")

    # Quick commands
    print_section("Quick Test Commands")

    commands = [
        ("Run all tests", "pytest tests/ -v"),
        ("Quick validation", "python scripts/quick_db_test.py --api"),
        ("Database tests only", "pytest tests/database/ -v"),
        ("API tests only", "pytest tests/api/ -v"),
        ("Full stack tests", "pytest tests/api/test_full_stack_api.py -v"),
        ("CRUD operations", "pytest tests/api/test_crud_operations.py -v"),
        ("Edge cases", "pytest tests/api/test_edge_cases.py -v"),
        ("With coverage", "pytest tests/ --cov=backend --cov-report=html -v"),
        ("Specific test", "pytest tests/api/test_full_stack_api.py::TestFullStackAPI::test_complete_project_lifecycle -v")
    ]

    for desc, cmd in commands:
        print(f"  {desc}:")
    print(f"    {BLUE}$ {cmd}{RESET}")

    # CI/CD Information
    print_section("CI/CD Workflows")
    workflows_dir = project_root / ".github" / "workflows"
    if workflows_dir.exists():
        workflows = list(workflows_dir.glob("*.yml"))
        for workflow in workflows:
            print(f"  • {workflow.name}")
            if workflow.name == "ci.yml":
                print(f"    {YELLOW}└─ Main CI pipeline (runs on every commit){RESET}")
            elif workflow.name == "database-tests.yml":
                print(f"    {YELLOW}└─ Database-specific tests (runs on migration changes){RESET}")
            elif workflow.name == "smoke-tests.yml":
                print(f"    {YELLOW}└─ Quick validation tests{RESET}")

    # Summary
    print_section("Summary")
    print(f"  Total test files: {total_files}")
    print(f"  Estimated total tests: ~{total_tests}")
    print(f"  Test categories: {len(test_categories)}")

    # Recent test results (if pytest cache exists)
    cache_dir = project_root / ".pytest_cache"
    if cache_dir.exists():
        print(f"\n  {YELLOW}ℹ pytest cache found - previous test results available{RESET}")

    # Check if services are running
    print_section("Current Environment")

    # Quick service check
    import socket
    services = {
        "PostgreSQL": ("localhost", 5432),
        "API": ("localhost", 8000),
        "Qdrant": ("localhost", 6333)
    }

    running_services = []
    for service, (host, port) in services.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            running_services.append(service)

    if running_services:
        print(f"  {GREEN}✓ Services running: {', '.join(running_services)}{RESET}")
    else:
        print(f"  {YELLOW}⚠ No services detected - start with: ./odras.sh start{RESET}")

    print(f"\n{BLUE}{'='*70}{RESET}\n")

    # Interactive mode
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        while True:
            print("\nSelect a test to run (or 'q' to quit):")
            print("1. All tests")
            print("2. API tests only")
            print("3. Database tests only")
            print("4. Full stack integration")
            print("5. Quick validation")
            print("q. Quit")

            choice = input("\nYour choice: ").strip()

            if choice == 'q':
                break
            elif choice == '1':
                subprocess.run(["pytest", "tests/", "-v"])
            elif choice == '2':
                subprocess.run(["pytest", "tests/api/", "-v"])
            elif choice == '3':
                subprocess.run(["pytest", "tests/database/", "-v"])
            elif choice == '4':
                subprocess.run(["pytest", "tests/api/test_full_stack_api.py", "-v"])
            elif choice == '5':
                subprocess.run(["python", "scripts/quick_db_test.py", "--api"])
            else:
                print("Invalid choice!")


if __name__ == "__main__":
    main()
