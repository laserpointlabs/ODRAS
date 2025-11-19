#!/usr/bin/env python3
"""
Quarterly Codebase Cleanup Script

Performs routine maintenance tasks:
- Reviews and reports on repository cleanliness
- Identifies potential cleanup opportunities
- Validates documentation and rules organization
- Checks for obsolete files

Run quarterly to maintain codebase health.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def count_markdown_files() -> Tuple[int, int]:
    """Count active and archived markdown files."""
    docs_dir = project_root / "docs"
    active_count = len(list(docs_dir.rglob("*.md"))) - len(list((docs_dir / "archive").rglob("*.md")))
    archived_count = len(list((docs_dir / "archive").rglob("*.md")))
    return active_count, archived_count


def count_rules_files() -> Tuple[int, int]:
    """Count active and archived rules files."""
    rules_dir = project_root / ".cursor" / "rules"
    archive_dir = project_root / ".cursor" / "archive"
    
    active_count = len(list(rules_dir.rglob("*.mdc"))) if rules_dir.exists() else 0
    archived_count = len(list(archive_dir.rglob("*.mdc"))) if archive_dir.exists() else 0
    
    return active_count, archived_count


def count_root_files() -> int:
    """Count files in root directory."""
    root_files = [
        f for f in os.listdir(project_root)
        if os.path.isfile(project_root / f) and not f.startswith(".")
    ]
    return len(root_files)


def check_limits() -> Dict[str, Dict]:
    """Check against repository limits."""
    active_docs, archived_docs = count_markdown_files()
    active_rules, archived_rules = count_rules_files()
    root_file_count = count_root_files()
    
    limits = {
        "documentation": {
            "active": active_docs,
            "limit": 35,
            "status": "✅" if active_docs <= 35 else "⚠️",
            "archived": archived_docs
        },
        "rules": {
            "active": active_rules,
            "limit": 30,
            "status": "✅" if active_rules <= 30 else "⚠️",
            "archived": archived_rules
        },
        "root_files": {
            "count": root_file_count,
            "limit": 15,
            "status": "✅" if root_file_count <= 15 else "⚠️"
        }
    }
    
    return limits


def find_large_files(size_mb: int = 1) -> List[Tuple[str, float]]:
    """Find files larger than specified size."""
    large_files = []
    for root, dirs, files in os.walk(project_root):
        # Skip common directories
        dirs[:] = [d for d in dirs if d not in ['.git', '.venv', 'node_modules', '__pycache__', '.pytest_cache']]
        
        for file in files:
            file_path = Path(root) / file
            try:
                size_mb_file = file_path.stat().st_size / (1024 * 1024)
                if size_mb_file > size_mb:
                    rel_path = file_path.relative_to(project_root)
                    large_files.append((str(rel_path), size_mb_file))
            except (OSError, PermissionError):
                pass
    
    return sorted(large_files, key=lambda x: x[1], reverse=True)


def check_log_files() -> List[str]:
    """Find log files that should be cleaned up."""
    log_files = []
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in ['.git', '.venv', 'node_modules']]
        
        for file in files:
            if file.endswith('.log') or file.endswith('.log.*'):
                file_path = Path(root) / file
                rel_path = file_path.relative_to(project_root)
                log_files.append(str(rel_path))
    
    return log_files


def generate_report() -> str:
    """Generate quarterly cleanup report."""
    report = []
    report.append("=" * 70)
    report.append("ODRAS Quarterly Codebase Cleanup Report")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 70)
    report.append("")
    
    # Limits check
    limits = check_limits()
    report.append("📊 Repository Limits Check")
    report.append("-" * 70)
    
    for category, data in limits.items():
        status = data["status"]
        if category == "documentation":
            report.append(f"{status} Documentation: {data['active']}/{data['limit']} active files ({data['archived']} archived)")
        elif category == "rules":
            report.append(f"{status} Rules: {data['active']}/{data['limit']} active files ({data['archived']} archived)")
        else:
            report.append(f"{status} Root Files: {data['count']}/{data['limit']} files")
    
    report.append("")
    
    # Large files
    large_files = find_large_files(1)
    if large_files:
        report.append("📦 Large Files (>1MB)")
        report.append("-" * 70)
        for file_path, size_mb in large_files[:10]:  # Top 10
            report.append(f"  {file_path}: {size_mb:.2f} MB")
        report.append("")
    
    # Log files
    log_files = check_log_files()
    if log_files:
        report.append("📝 Log Files Found")
        report.append("-" * 70)
        for log_file in log_files[:10]:  # Top 10
            report.append(f"  {log_file}")
        report.append("")
    
    # Recommendations
    report.append("💡 Recommendations")
    report.append("-" * 70)
    
    if limits["documentation"]["active"] > limits["documentation"]["limit"]:
        report.append("⚠️  Documentation count exceeds limit - consider consolidation")
    
    if limits["rules"]["active"] > limits["rules"]["limit"]:
        report.append("⚠️  Rules count exceeds limit - consider consolidation")
    
    if limits["root_files"]["count"] > limits["root_files"]["limit"]:
        report.append("⚠️  Root directory has too many files - move to appropriate directories")
    
    if log_files:
        report.append(f"⚠️  Found {len(log_files)} log files - ensure they're in .gitignore")
    
    if not large_files and not log_files and all(
        limits[k]["status"] == "✅" for k in limits.keys()
    ):
        report.append("✅ Repository is clean and within limits!")
    
    report.append("")
    report.append("=" * 70)
    
    return "\n".join(report)


def main():
    """Main entry point."""
    print(generate_report())
    
    # Exit with error code if any limits exceeded
    limits = check_limits()
    if any(
        limits[k]["status"] == "⚠️" 
        for k in limits.keys()
    ):
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()

