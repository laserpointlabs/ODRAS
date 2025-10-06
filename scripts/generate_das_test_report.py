#!/usr/bin/env python3
"""
DAS Test Comprehensive Report Generator

Generates detailed reports of DAS test results for CI/CD review.
Outputs to both terminal and log files for easy analysis.

This script analyzes test results and provides:
1. Executive summary of DAS capabilities
2. Detailed test results with confidence scores
3. Performance metrics and thresholds
4. Known issues and limitations
5. Recommendations for improvements
6. Context coverage analysis

Usage:
    python scripts/generate_das_test_report.py [--output-file report.md] [--include-raw-data]
"""

import json
import sys
import argparse
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


class DASTestReportGenerator:
    """Generate comprehensive DAS test reports"""

    def __init__(self, output_file: Optional[str] = None):
        self.output_file = output_file
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.report_data = {
            "generated_at": self.timestamp,
            "test_suites": {},
            "overall_metrics": {},
            "recommendations": [],
            "issues_found": []
        }

    def run_test_and_capture_results(self, test_file: str, test_name: str) -> Dict[str, Any]:
        """Run a test file and capture detailed results"""
        print(f"\n🧪 Running {test_name}...")
        print("=" * 60)

        start_time = time.time()

        try:
            # Run pytest with JSON output for structured results
            result = subprocess.run([
                "python", "-m", "pytest", test_file,
                "-v", "--tb=short", "--json-report",
                f"--json-report-file=/tmp/{test_name}_report.json"
            ], capture_output=True, text=True, timeout=600)

            end_time = time.time()
            duration = end_time - start_time

            # Parse JSON report if available
            json_report_path = f"/tmp/{test_name}_report.json"
            json_report = {}

            if Path(json_report_path).exists():
                try:
                    with open(json_report_path, 'r') as f:
                        json_report = json.load(f)
                except Exception as e:
                    print(f"⚠️  Could not parse JSON report: {e}")

            # Extract key metrics
            return_code = result.returncode
            stdout = result.stdout
            stderr = result.stderr

            # Parse test results from output
            passed_tests = stdout.count(" PASSED")
            failed_tests = stdout.count(" FAILED")
            total_tests = passed_tests + failed_tests

            # Extract confidence scores if available
            confidence_scores = []
            for line in stdout.split('\n'):
                if "Score:" in line or "Confidence:" in line:
                    # Try to extract percentage
                    import re
                    matches = re.findall(r'(\d+)%', line)
                    if matches:
                        confidence_scores.extend([int(m) for m in matches])

            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

            test_result = {
                "name": test_name,
                "file": test_file,
                "duration_seconds": round(duration, 2),
                "return_code": return_code,
                "passed": passed_tests,
                "failed": failed_tests,
                "total": total_tests,
                "success_rate": (passed_tests / max(total_tests, 1)) * 100,
                "avg_confidence": round(avg_confidence, 1),
                "confidence_scores": confidence_scores,
                "stdout": stdout,
                "stderr": stderr,
                "json_report": json_report
            }

            # Console output
            if return_code == 0:
                print(f"✅ {test_name}: {passed_tests}/{total_tests} tests passed")
                if confidence_scores:
                    print(f"   📊 Average Confidence: {avg_confidence:.1f}%")
                print(f"   ⏱️  Duration: {duration:.1f}s")
            else:
                print(f"❌ {test_name}: {failed_tests}/{total_tests} tests failed")
                print(f"   🔍 Check detailed output below")

            return test_result

        except subprocess.TimeoutExpired:
            print(f"⏰ {test_name}: Test timed out after 10 minutes")
            return {
                "name": test_name,
                "file": test_file,
                "duration_seconds": 600,
                "return_code": -1,
                "error": "timeout",
                "passed": 0,
                "failed": 1,
                "total": 1,
                "success_rate": 0
            }
        except Exception as e:
            print(f"💥 {test_name}: Test execution error: {e}")
            return {
                "name": test_name,
                "file": test_file,
                "duration_seconds": 0,
                "return_code": -2,
                "error": str(e),
                "passed": 0,
                "failed": 1,
                "total": 1,
                "success_rate": 0
            }

    def generate_executive_summary(self) -> str:
        """Generate executive summary of DAS test results"""

        total_tests = sum(suite.get("total", 0) for suite in self.report_data["test_suites"].values())
        total_passed = sum(suite.get("passed", 0) for suite in self.report_data["test_suites"].values())
        total_failed = sum(suite.get("failed", 0) for suite in self.report_data["test_suites"].values())

        overall_success_rate = (total_passed / max(total_tests, 1)) * 100

        # Calculate average confidence across all suites with confidence data
        confidence_suites = [s for s in self.report_data["test_suites"].values() if s.get("avg_confidence", 0) > 0]
        avg_confidence = sum(s.get("avg_confidence", 0) for s in confidence_suites) / max(len(confidence_suites), 1)

        # Determine overall grade
        if overall_success_rate >= 90 and avg_confidence >= 80:
            grade = "A (Excellent)"
        elif overall_success_rate >= 80 and avg_confidence >= 70:
            grade = "B+ (Good)"
        elif overall_success_rate >= 70 and avg_confidence >= 60:
            grade = "B (Satisfactory)"
        elif overall_success_rate >= 60:
            grade = "C+ (Acceptable)"
        else:
            grade = "C or Lower (Needs Attention)"

        summary = f"""
🎯 DAS COMPREHENSIVE TEST REPORT
Generated: {self.timestamp}

📊 EXECUTIVE SUMMARY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ Overall Grade: {grade}
📈 Success Rate: {overall_success_rate:.1f}% ({total_passed}/{total_tests} tests passed)
🧠 Average Confidence: {avg_confidence:.1f}% (across {len(confidence_suites)} evaluated suites)
⏱️  Total Test Duration: {sum(s.get('duration_seconds', 0) for s in self.report_data['test_suites'].values()):.1f}s

🎯 DAS CAPABILITIES ASSESSMENT:

"""

        # Add capability assessments
        capabilities = []

        for suite_name, suite_data in self.report_data["test_suites"].items():
            if "ontology" in suite_name.lower():
                if suite_data.get("success_rate", 0) >= 80:
                    capabilities.append("✅ Ontology Intelligence: EXCELLENT (Rich attributes, metadata, hierarchy)")
                elif suite_data.get("success_rate", 0) >= 60:
                    capabilities.append("🟡 Ontology Intelligence: GOOD (Basic functionality working)")
                else:
                    capabilities.append("❌ Ontology Intelligence: NEEDS ATTENTION")

            if "context" in suite_name.lower():
                confidence = suite_data.get("avg_confidence", 0)
                if confidence >= 70:
                    capabilities.append("✅ Context Awareness: EXCELLENT (Comprehensive understanding)")
                elif confidence >= 50:
                    capabilities.append("🟡 Context Awareness: GOOD (Adequate understanding)")
                else:
                    capabilities.append("❌ Context Awareness: NEEDS ATTENTION")

        # Add general capabilities based on overall performance
        if overall_success_rate >= 80:
            capabilities.append("✅ Overall System: RELIABLE")
        elif overall_success_rate >= 60:
            capabilities.append("🟡 Overall System: FUNCTIONAL")
        else:
            capabilities.append("❌ Overall System: UNSTABLE")

        summary += "\n".join(capabilities)

        return summary

    def generate_detailed_results(self) -> str:
        """Generate detailed test results section"""

        details = "\n\n📋 DETAILED TEST RESULTS:\n"
        details += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        for suite_name, suite_data in self.report_data["test_suites"].items():
            details += f"\n🧪 {suite_name.upper()}:\n"
            details += f"   Status: {'✅ PASSED' if suite_data.get('return_code') == 0 else '❌ FAILED'}\n"
            details += f"   Tests: {suite_data.get('passed', 0)}/{suite_data.get('total', 0)} passed ({suite_data.get('success_rate', 0):.1f}%)\n"
            details += f"   Duration: {suite_data.get('duration_seconds', 0):.1f}s\n"

            if suite_data.get("avg_confidence"):
                details += f"   Confidence: {suite_data.get('avg_confidence', 0):.1f}% average\n"

            if suite_data.get("confidence_scores"):
                scores = suite_data["confidence_scores"]
                details += f"   Score Range: {min(scores)}% - {max(scores)}%\n"

            # Add failure details if any
            if suite_data.get("failed", 0) > 0:
                details += f"   ⚠️  Failures: {suite_data.get('failed')} tests failed\n"

                # Extract failure info from stderr if available
                stderr = suite_data.get("stderr", "")
                if "AssertionError" in stderr:
                    # Try to extract assertion message
                    import re
                    assertion_matches = re.findall(r'AssertionError: ([^\n]+)', stderr)
                    if assertion_matches:
                        details += f"   💭 Key Issue: {assertion_matches[0][:100]}...\n"

        return details

    def generate_performance_analysis(self) -> str:
        """Generate performance analysis section"""

        analysis = "\n\n⚡ PERFORMANCE ANALYSIS:\n"
        analysis += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        total_duration = sum(s.get('duration_seconds', 0) for s in self.report_data["test_suites"].values())
        suite_count = len(self.report_data["test_suites"])

        analysis += f"\n📊 Timing Analysis:\n"
        analysis += f"   Total Test Time: {total_duration:.1f}s\n"
        analysis += f"   Average per Suite: {total_duration/max(suite_count, 1):.1f}s\n"

        # Performance assessment
        if total_duration < 300:  # 5 minutes
            analysis += f"   🚀 Performance: EXCELLENT (Fast execution)\n"
        elif total_duration < 600:  # 10 minutes
            analysis += f"   ✅ Performance: GOOD (Reasonable execution time)\n"
        elif total_duration < 900:  # 15 minutes
            analysis += f"   🟡 Performance: ACCEPTABLE (Slower but functional)\n"
        else:
            analysis += f"   ⚠️  Performance: SLOW (May need optimization)\n"

        # Suite-specific timing
        analysis += f"\n⏱️  Suite Breakdown:\n"
        for suite_name, suite_data in self.report_data["test_suites"].items():
            duration = suite_data.get('duration_seconds', 0)
            analysis += f"   {suite_name}: {duration:.1f}s\n"

        return analysis

    def generate_recommendations(self) -> str:
        """Generate recommendations based on test results"""

        recs = "\n\n💡 RECOMMENDATIONS:\n"
        recs += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        # Analyze results and provide recommendations
        failed_suites = [name for name, data in self.report_data["test_suites"].items()
                        if data.get("return_code", 0) != 0]

        low_confidence_suites = [name for name, data in self.report_data["test_suites"].items()
                               if data.get("avg_confidence", 100) < 50]

        slow_suites = [name for name, data in self.report_data["test_suites"].items()
                      if data.get("duration_seconds", 0) > 120]

        if not failed_suites and not low_confidence_suites:
            recs += "\n🎉 EXCELLENT: All tests passing with good confidence levels!\n"
            recs += "\n📈 Next Steps:\n"
            recs += "   • Consider implementing hybrid search enhancement\n"
            recs += "   • Add more edge case coverage\n"
            recs += "   • Expand conversation memory testing\n"

        if failed_suites:
            recs += f"\n🔥 CRITICAL: {len(failed_suites)} test suite(s) failing:\n"
            for suite in failed_suites:
                recs += f"   • {suite}: Investigate failure causes\n"

        if low_confidence_suites:
            recs += f"\n⚠️  LOW CONFIDENCE: {len(low_confidence_suites)} suite(s) below 50% confidence:\n"
            for suite in low_confidence_suites:
                confidence = self.report_data["test_suites"][suite].get("avg_confidence", 0)
                recs += f"   • {suite}: {confidence:.1f}% confidence - needs improvement\n"

        if slow_suites:
            recs += f"\n🐌 PERFORMANCE: {len(slow_suites)} slow suite(s) >2 minutes:\n"
            for suite in slow_suites:
                duration = self.report_data["test_suites"][suite].get("duration_seconds", 0)
                recs += f"   • {suite}: {duration:.1f}s - consider optimization\n"

        # Add standard recommendations
        recs += f"\n🔧 Standard Maintenance:\n"
        recs += f"   • Review logs for any deprecation warnings\n"
        recs += f"   • Check docs/architecture/MULTI_ENDPOINT_ONTOLOGY_ISSUE.md for API guidance\n"
        recs += f"   • Monitor DAS response quality in production\n"
        recs += f"   • Consider updating test thresholds based on improvements\n"

        return recs

    def generate_context_coverage_analysis(self) -> str:
        """Analyze DAS context coverage based on test results"""

        coverage = "\n\n🎯 DAS CONTEXT COVERAGE ANALYSIS:\n"
        coverage += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        # Define context areas and analyze coverage
        context_areas = {
            "Rich Ontology Attributes": {
                "description": "Classes with priority, status, creator, definitions, examples",
                "test_indicator": "ontology_attributes",
                "expected_confidence": 80,
                "importance": "Critical"
            },
            "Project Metadata": {
                "description": "Project name, description, domain, namespace, creator",
                "test_indicator": "project_awareness",
                "expected_confidence": 60,
                "importance": "High"
            },
            "Knowledge Assets": {
                "description": "Uploaded files, content understanding, processing status",
                "test_indicator": "knowledge_asset",
                "expected_confidence": 50,
                "importance": "High"
            },
            "Conversation Memory": {
                "description": "Previous questions, multi-turn context, pronoun resolution",
                "test_indicator": "conversation",
                "expected_confidence": 40,
                "importance": "Medium"
            },
            "Cross-Context Integration": {
                "description": "Synthesis across ontology + files + project + conversation",
                "test_indicator": "integration",
                "expected_confidence": 60,
                "importance": "High"
            },
            "Edge Case Handling": {
                "description": "Error handling, nonsense input, graceful degradation",
                "test_indicator": "edge",
                "expected_confidence": 30,
                "importance": "Medium"
            }
        }

        coverage += "\n📋 Context Coverage Assessment:\n\n"

        for area_name, area_info in context_areas.items():
            # Try to find relevant test data
            area_confidence = 0
            area_tested = False

            for suite_name, suite_data in self.report_data["test_suites"].items():
                if area_info["test_indicator"] in suite_name.lower():
                    area_confidence = suite_data.get("avg_confidence", 0)
                    area_tested = True
                    break

            # Status indicator
            if not area_tested:
                status = "⚪ NOT TESTED"
            elif area_confidence >= area_info["expected_confidence"]:
                status = "✅ EXCELLENT"
            elif area_confidence >= area_info["expected_confidence"] * 0.8:
                status = "🟡 GOOD"
            elif area_confidence >= area_info["expected_confidence"] * 0.6:
                status = "🟠 ACCEPTABLE"
            else:
                status = "❌ NEEDS WORK"

            coverage += f"🎯 {area_name}:\n"
            coverage += f"   {status} ({area_confidence:.1f}% confidence)\n"
            coverage += f"   Target: {area_info['expected_confidence']}% | Importance: {area_info['importance']}\n"
            coverage += f"   Coverage: {area_info['description']}\n\n"

        return coverage

    def run_comprehensive_test_suite(self) -> Dict[str, Any]:
        """Run all DAS tests and generate comprehensive report"""

        print("🚀 DAS COMPREHENSIVE TEST SUITE")
        print("=" * 80)
        print(f"Started: {self.timestamp}")
        print(f"Environment: ODRAS running at http://localhost:8000")
        print()

        # Define test suites to run
        test_suites = [
            ("tests/test_working_ontology_attributes.py", "ontology_attributes"),
            ("tests/test_das_comprehensive_context_awareness.py", "context_awareness"),
            ("tests/test_das_integration_comprehensive.py", "baseline_integration")
        ]

        all_success = True

        # Run each test suite
        for test_file, test_name in test_suites:
            if Path(test_file).exists():
                result = self.run_test_and_capture_results(test_file, test_name)
                self.report_data["test_suites"][test_name] = result

                if result.get("return_code", 0) != 0:
                    all_success = False
            else:
                print(f"⚠️  Test file not found: {test_file}")
                all_success = False

        # Generate comprehensive report
        report = self.generate_executive_summary()
        report += self.generate_detailed_results()
        report += self.generate_performance_analysis()
        report += self.generate_context_coverage_analysis()
        report += self.generate_recommendations()

        # Add footer
        report += f"\n\n📅 Report Generated: {self.timestamp}\n"
        report += f"🔗 For detailed logs, check: /tmp/odras_app.log\n"
        report += f"📖 Architecture docs: docs/architecture/\n"
        report += f"🧪 Test files: tests/test_*das*.py\n"

        # Output to terminal
        print("\n" + "=" * 80)
        print(report)
        print("=" * 80)

        # Output to file if specified
        if self.output_file:
            with open(self.output_file, 'w') as f:
                f.write(report)
            print(f"\n📝 Full report saved to: {self.output_file}")

        # Also save to logs directory
        log_file = f"/tmp/das_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(log_file, 'w') as f:
            f.write(report)
        print(f"📝 Report also saved to: {log_file}")

        # Save structured data for historical analysis and GitHub artifacts
        self._save_structured_data()

        return {
            "success": all_success,
            "report": report,
            "report_data": self.report_data
        }

    def _save_structured_data(self):
        """Save structured data for historical analysis and artifacts"""
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 1. Performance metrics JSON
        performance_data = {
            "timestamp": self.timestamp,
            "total_duration": sum(s.get('duration_seconds', 0) for s in self.report_data["test_suites"].values()),
            "suite_performance": {
                name: {
                    "duration_seconds": data.get('duration_seconds', 0),
                    "success_rate": data.get('success_rate', 0),
                    "avg_confidence": data.get('avg_confidence', 0)
                }
                for name, data in self.report_data["test_suites"].items()
            },
            "overall_metrics": {
                "total_tests": sum(s.get("total", 0) for s in self.report_data["test_suites"].values()),
                "total_passed": sum(s.get("passed", 0) for s in self.report_data["test_suites"].values()),
                "overall_success_rate": (sum(s.get("passed", 0) for s in self.report_data["test_suites"].values()) /
                                       max(sum(s.get("total", 0) for s in self.report_data["test_suites"].values()), 1)) * 100
            }
        }

        performance_file = f"/tmp/das_performance_{timestamp_str}.json"
        with open(performance_file, 'w') as f:
            json.dump(performance_data, f, indent=2)
        print(f"📊 Performance data saved: {performance_file}")

        # 2. Confidence scores JSON for trend analysis
        confidence_data = {
            "timestamp": self.timestamp,
            "confidence_scores": {}
        }

        for suite_name, suite_data in self.report_data["test_suites"].items():
            if suite_data.get("confidence_scores"):
                confidence_data["confidence_scores"][suite_name] = {
                    "scores": suite_data["confidence_scores"],
                    "average": suite_data.get("avg_confidence", 0),
                    "min": min(suite_data["confidence_scores"]),
                    "max": max(suite_data["confidence_scores"]),
                    "count": len(suite_data["confidence_scores"])
                }

        confidence_file = f"/tmp/das_confidence_{timestamp_str}.json"
        with open(confidence_file, 'w') as f:
            json.dump(confidence_data, f, indent=2)
        print(f"🧠 Confidence data saved: {confidence_file}")

        # 3. Summary data for historical comparison
        summary_data = {
            "commit_timestamp": self.timestamp,
            "test_summary": {
                "total_suites": len(self.report_data["test_suites"]),
                "passing_suites": len([s for s in self.report_data["test_suites"].values() if s.get("return_code") == 0]),
                "failing_suites": len([s for s in self.report_data["test_suites"].values() if s.get("return_code") != 0]),
                "average_confidence": sum(s.get("avg_confidence", 0) for s in self.report_data["test_suites"].values()) /
                                   max(len([s for s in self.report_data["test_suites"].values() if s.get("avg_confidence", 0) > 0]), 1),
                "total_duration": sum(s.get('duration_seconds', 0) for s in self.report_data["test_suites"].values())
            },
            "das_capabilities": {
                "ontology_intelligence": "excellent" if any("ontology" in name and data.get("avg_confidence", 0) >= 80
                                                          for name, data in self.report_data["test_suites"].items()) else "good",
                "context_awareness": "good" if any("context" in name and data.get("avg_confidence", 0) >= 50
                                                 for name, data in self.report_data["test_suites"].items()) else "needs_work",
                "overall_grade": "A" if performance_data["overall_metrics"]["overall_success_rate"] >= 90 else
                               "B" if performance_data["overall_metrics"]["overall_success_rate"] >= 80 else
                               "C" if performance_data["overall_metrics"]["overall_success_rate"] >= 70 else "D"
            }
        }

        summary_file = f"/tmp/das_summary_{timestamp_str}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2)
        print(f"📋 Summary data saved: {summary_file}")


def main():
    """Main entry point for report generation"""
    parser = argparse.ArgumentParser(description="Generate DAS comprehensive test report")
    parser.add_argument("--output-file", "-o", help="Output file for report (markdown format)")
    parser.add_argument("--include-raw-data", action="store_true", help="Include raw test output in report")

    args = parser.parse_args()

    # Generate report
    generator = DASTestReportGenerator(output_file=args.output_file)
    result = generator.run_comprehensive_test_suite()

    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
