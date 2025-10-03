#!/usr/bin/env python3
"""
Simple script to count lines of code by file type in the ODRAS project.
"""

import os
import glob
from collections import defaultdict

def count_lines_in_file(file_path):
    """Count lines in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return len(f.readlines())
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0

def get_file_extension(file_path):
    """Get file extension, handling special cases."""
    if '.' in file_path:
        return file_path.split('.')[-1].lower()
    return 'no_extension'

def count_lines_by_type():
    """Count lines of code by file type."""
    # File type patterns to search for
    patterns = {
        'python': ['**/*.py'],
        'javascript': ['**/*.js', '**/*.jsx'],
        'typescript': ['**/*.ts', '**/*.tsx'],
        'html': ['**/*.html', '**/*.htm'],
        'css': ['**/*.css', '**/*.scss', '**/*.sass'],
        'json': ['**/*.json'],
        'yaml': ['**/*.yml', '**/*.yaml'],
        'xml': ['**/*.xml'],
        'sql': ['**/*.sql'],
        'shell': ['**/*.sh', '**/*.bash'],
        'docker': ['**/Dockerfile*', '**/*.dockerfile'],
        'text': ['**/*.txt'],
        'config': ['**/*.ini', '**/*.cfg', '**/*.conf', '**/*.env']
    }

    # Count lines by type
    counts = defaultdict(int)
    file_counts = defaultdict(int)

    # Get project root (assuming script is in scripts/ folder)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    print(f"Scanning project at: {project_root}")
    print("=" * 50)

    # Process each file type
    for file_type, glob_patterns in patterns.items():
        for pattern in glob_patterns:
            for file_path in glob.glob(os.path.join(project_root, pattern), recursive=True):
                # Skip hidden files and common ignore patterns
                if any(part.startswith('.') for part in file_path.split(os.sep)):
                    continue
                if 'node_modules' in file_path or '__pycache__' in file_path:
                    continue
                if 'venv' in file_path or 'env' in file_path:
                    continue

                lines = count_lines_in_file(file_path)
                counts[file_type] += lines
                file_counts[file_type] += 1

    # Handle other files not caught by patterns
    for root, dirs, files in os.walk(project_root):
        # Skip common ignore directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', 'env']]

        for file in files:
            if file.startswith('.'):
                continue

            file_path = os.path.join(root, file)
            ext = get_file_extension(file_path)

            # Skip markdown, log, and other non-code files
            skip_extensions = ['.md', '.log']
            if any(file_path.endswith(ext) for ext in skip_extensions):
                continue

            # If not already categorized, skip it (don't count as 'other')
            categorized = False
            for file_type, file_patterns in patterns.items():
                for pattern in file_patterns:
                    if any(file_path.endswith(p.replace('**/*', '')) for p in pattern.split(',')):
                        categorized = True
                        break
                if categorized:
                    break

            # Skip uncategorized files entirely

    return counts, file_counts

def main():
    """Main function to run the line count analysis."""
    print("ODRAS Lines of Code Counter")
    print("=" * 50)

    counts, file_counts = count_lines_by_type()

    # Sort by line count (descending)
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)

    total_lines = 0
    total_files = 0

    print(f"{'File Type':<15} {'Files':<8} {'Lines':<10} {'Percentage':<10}")
    print("-" * 50)

    for file_type, line_count in sorted_counts:
        if line_count > 0:  # Only show types with lines
            file_count = file_counts[file_type]
            percentage = (line_count / sum(counts.values())) * 100 if sum(counts.values()) > 0 else 0
            print(f"{file_type:<15} {file_count:<8} {line_count:<10} {percentage:<10.1f}%")
            total_lines += line_count
            total_files += file_count

    print("-" * 50)
    print(f"{'TOTAL':<15} {total_files:<8} {total_lines:<10} {'100.0%':<10}")
    print("=" * 50)
    print(f"Total files: {total_files}")
    print(f"Total lines: {total_lines:,}")

if __name__ == "__main__":
    main()
