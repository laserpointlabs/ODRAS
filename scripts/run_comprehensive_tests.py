#!/usr/bin/env python3
"""
ODRAS Comprehensive Test Runner

This script runs all test suites in the correct order and generates comprehensive reports.
"""

import asyncio
import json
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeElapsedColumn,
)

console = Console()


@dataclass
class TestSuite:
    """Represents a test suite to run"""

    name: str
    command: List[str]
    description: str
    critical: bool = True
    timeout: int = 300  # 5 minutes default


class ODRASTestRunner:
    """Comprehensive test runner for ODRAS"""

    def __init__(self, verbose: bool = False, base_url: str = "http://localhost:8000"):
        self.verbose = verbose
        self.base_url = base_url
        self.results: Dict[str, Any] = {}
        self.project_root = Path(__file__).parent.parent

    def get_test_suites(self) -> List[TestSuite]:
        """Get all test suites to run"""
        return [
            TestSuite(
                name="unit_tests",
                command=["python", "-m", "pytest", "tests/unit/", "-v", "--tb=short"],
                description="Unit tests for individual components",
                critical=True,
            ),
            TestSuite(
                name="api_tests",
                command=["python", "-m", "pytest", "tests/api/", "-v", "--tb=short"],
                description="API endpoint tests",
                critical=True,
            ),
            TestSuite(
                name="integration_tests",
                command=[
                    "python",
                    "-m",
                    "pytest",
                    "tests/integration/",
                    "-v",
                    "--tb=short",
                ],
                description="Integration tests for workflows",
                critical=True,
            ),
            TestSuite(
                name="file_management_tests",
                command=[
                    "python",
                    "-m",
                    "pytest",
                    "tests/unit/test_file_management.py",
                    "-v",
                ],
                description="File management specific tests",
                critical=True,
            ),
            TestSuite(
                name="api_validation",
                command=[
                    "python",
                    "scripts/validate_all_endpoints.py",
                    f"--base-url={self.base_url}",
                ],
                description="Comprehensive API endpoint validation",
                critical=True,
            ),
            TestSuite(
                name="code_quality",
                command=[
                    "flake8",
                    "backend/",
                    "--count",
                    "--select=E9,F63,F7,F82",
                    "--show-source",
                    "--statistics",
                ],
                description="Code quality and syntax checks",
                critical=True,
            ),
            TestSuite(
                name="security_scan",
                command=["bandit", "-r", "backend/", "-ll"],
                description="Security vulnerability scan",
                critical=False,
            ),
            TestSuite(
                name="import_validation",
                command=[
                    "python",
                    "-c",
                    "from backend.main import app; print('✅ Imports successful')",
                ],
                description="Python import validation",
                critical=True,
            ),
        ]

    async def run_test_suite(self, suite: TestSuite) -> Dict[str, Any]:
        """Run a single test suite"""
        console.print(f"\n🧪 Running {suite.name}...", style="blue")

        start_time = time.time()

        try:
            # Change to project root directory
            result = subprocess.run(
                suite.command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=suite.timeout,
            )

            end_time = time.time()
            duration = end_time - start_time

            success = result.returncode == 0

            if self.verbose or not success:
                if result.stdout:
                    console.print("STDOUT:", style="green")
                    console.print(result.stdout)
                if result.stderr:
                    console.print("STDERR:", style="red")
                    console.print(result.stderr)

            return {
                "name": suite.name,
                "description": suite.description,
                "success": success,
                "return_code": result.returncode,
                "duration": duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "critical": suite.critical,
            }

        except subprocess.TimeoutExpired:
            return {
                "name": suite.name,
                "description": suite.description,
                "success": False,
                "return_code": -1,
                "duration": suite.timeout,
                "stdout": "",
                "stderr": f"Test suite timed out after {suite.timeout} seconds",
                "critical": suite.critical,
            }
        except Exception as e:
            return {
                "name": suite.name,
                "description": suite.description,
                "success": False,
                "return_code": -1,
                "duration": time.time() - start_time,
                "stdout": "",
                "stderr": str(e),
                "critical": suite.critical,
            }

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all test suites"""
        console.print("🚀 Starting ODRAS Comprehensive Test Suite", style="bold blue")
        console.print(f"Base URL: {self.base_url}")
        console.print(f"Project Root: {self.project_root}")

        test_suites = self.get_test_suites()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Running test suites...", total=len(test_suites))

            for suite in test_suites:
                progress.update(task, description=f"Running {suite.name}")

                result = await self.run_test_suite(suite)
                self.results[suite.name] = result

                progress.advance(task)

        return self.generate_report()

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_suites = len(self.results)
        successful_suites = sum(1 for r in self.results.values() if r["success"])
        failed_suites = total_suites - successful_suites

        critical_failures = sum(
            1 for r in self.results.values() if not r["success"] and r["critical"]
        )

        total_duration = sum(r["duration"] for r in self.results.values())

        # Categorize results
        successful = [r for r in self.results.values() if r["success"]]
        failed = [r for r in self.results.values() if not r["success"]]
        critical_failed = [r for r in failed if r["critical"]]
        non_critical_failed = [r for r in failed if not r["critical"]]

        report = {
            "summary": {
                "total_suites": total_suites,
                "successful_suites": successful_suites,
                "failed_suites": failed_suites,
                "critical_failures": critical_failures,
                "success_rate": (
                    (successful_suites / total_suites * 100) if total_suites > 0 else 0
                ),
                "total_duration": total_duration,
            },
            "results": self.results,
            "successful": successful,
            "failed": failed,
            "critical_failed": critical_failed,
            "non_critical_failed": non_critical_failed,
        }

        return report

    def print_report(self, report: Dict[str, Any]):
        """Print formatted test report"""
        summary = report["summary"]

        # Summary panel
        status_icon = "✅" if summary["critical_failures"] == 0 else "❌"
        summary_text = f"""
{status_icon} Test Suites: {summary['successful_suites']}/{summary['total_suites']} passed
⏱️  Total Duration: {summary['total_duration']:.1f}s
🎯 Success Rate: {summary['success_rate']:.1f}%
🚨 Critical Failures: {summary['critical_failures']}
        """.strip()

        border_style = "green" if summary["critical_failures"] == 0 else "red"
        console.print(Panel(summary_text, title="Test Summary", border_style=border_style))

        # Detailed results table
        results_table = Table(title="Detailed Results")
        results_table.add_column("Test Suite", style="cyan")
        results_table.add_column("Status", style="magenta")
        results_table.add_column("Duration", style="yellow")
        results_table.add_column("Critical", style="blue")

        for result in self.results.values():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            duration = f"{result['duration']:.1f}s"
            critical = "Yes" if result["critical"] else "No"

            results_table.add_row(result["name"], status, duration, critical)

        console.print(results_table)

        # Failed tests details
        if report["failed"]:
            console.print("\n❌ Failed Test Details:", style="bold red")

            for result in report["failed"]:
                console.print(f"\n🔴 {result['name']} ({result['description']})")
                console.print(f"   Return Code: {result['return_code']}")
                console.print(f"   Duration: {result['duration']:.1f}s")

                if result["stderr"]:
                    console.print("   Error Output:", style="red")
                    for line in result["stderr"].split("\n")[:5]:  # Show first 5 lines
                        if line.strip():
                            console.print(f"     {line}", style="red")

        # Recommendations
        if summary["critical_failures"] > 0:
            console.print("\n🚨 Critical Issues Found:", style="bold red")
            console.print("   - Fix critical test failures before merging")
            console.print("   - Review error messages above")
            console.print("   - Run individual test suites for detailed debugging")
        elif summary["failed_suites"] > 0:
            console.print("\n⚠️  Non-Critical Issues Found:", style="bold yellow")
            console.print("   - Some non-critical tests failed")
            console.print("   - Review warnings and consider fixing")
        else:
            console.print("\n🎉 All Tests Passed!", style="bold green")
            console.print("   - System is ready for merge")
            console.print("   - All critical functionality validated")


async def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Run comprehensive ODRAS test suite")
    parser.add_argument(
        "--base-url", default="http://localhost:8000", help="Base URL for API testing"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--output", "-o", help="Save results to JSON file")
    parser.add_argument("--suite", "-s", help="Run only specific test suite")

    args = parser.parse_args()

    try:
        runner = ODRASTestRunner(verbose=args.verbose, base_url=args.base_url)

        if args.suite:
            # Run specific test suite
            suites = runner.get_test_suites()
            suite = next((s for s in suites if s.name == args.suite), None)
            if not suite:
                console.print(f"❌ Test suite '{args.suite}' not found", style="red")
                sys.exit(1)

            result = await runner.run_test_suite(suite)
            runner.results[suite.name] = result
            report = runner.generate_report()
        else:
            # Run all test suites
            report = await runner.run_all_tests()

        runner.print_report(report)

        # Save report if requested
        if args.output:
            with open(args.output, "w") as f:
                json.dump(report, f, indent=2, default=str)
            console.print(f"\n💾 Report saved to {args.output}", style="green")

        # Exit with appropriate code
        if report["summary"]["critical_failures"] > 0:
            console.print(
                f"\n❌ {report['summary']['critical_failures']} critical test failures!",
                style="red",
            )
            sys.exit(1)
        else:
            console.print("\n🎉 All critical tests passed!", style="green")
            sys.exit(0)

    except KeyboardInterrupt:
        console.print("\n⏹️  Testing interrupted by user", style="yellow")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n💥 Testing failed with error: {e}", style="red")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

