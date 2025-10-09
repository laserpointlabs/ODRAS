#!/usr/bin/env python3
"""
Script to count actual lines of working code by file type in the ODRAS project.
Excludes comments, empty lines, docstrings, and configuration files.
"""

import os
import glob
from collections import defaultdict

def count_lines_in_file(file_path):
    """Count actual lines of code in a single file (excluding comments, empty lines, docstrings)."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # Get file extension to determine comment style
        ext = get_file_extension(file_path)
        
        code_lines = 0
        in_multiline_comment = False
        in_docstring = False
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                continue
                
            # Handle different comment styles based on file type
            if ext in ['py']:
                # Python: # comments, """ or ''' docstrings
                if stripped.startswith('#'):
                    continue
                if '"""' in stripped or "'''" in stripped:
                    if stripped.count('"""') == 1 or stripped.count("'''") == 1:
                        in_docstring = not in_docstring
                    continue
                if in_docstring:
                    continue
                    
            elif ext in ['js', 'jsx', 'ts', 'tsx']:
                # JavaScript/TypeScript: // and /* */ comments
                if stripped.startswith('//'):
                    continue
                if '/*' in stripped and '*/' in stripped:
                    continue
                if '/*' in stripped:
                    in_multiline_comment = True
                    continue
                if '*/' in stripped:
                    in_multiline_comment = False
                    continue
                if in_multiline_comment:
                    continue
                    
            elif ext in ['html', 'htm', 'xml']:
                # HTML/XML: <!-- --> comments
                if stripped.startswith('<!--') and stripped.endswith('-->'):
                    continue
                if '<!--' in stripped:
                    in_multiline_comment = True
                    continue
                if '-->' in stripped:
                    in_multiline_comment = False
                    continue
                if in_multiline_comment:
                    continue
                    
            elif ext in ['css', 'scss', 'sass']:
                # CSS: /* */ comments
                if stripped.startswith('/*') and stripped.endswith('*/'):
                    continue
                if '/*' in stripped:
                    in_multiline_comment = True
                    continue
                if '*/' in stripped:
                    in_multiline_comment = False
                    continue
                if in_multiline_comment:
                    continue
                    
            elif ext in ['sh', 'bash']:
                # Shell: # comments
                if stripped.startswith('#'):
                    continue
                    
            elif ext in ['sql']:
                # SQL: -- and /* */ comments
                if stripped.startswith('--'):
                    continue
                if stripped.startswith('/*') and stripped.endswith('*/'):
                    continue
                if '/*' in stripped:
                    in_multiline_comment = True
                    continue
                if '*/' in stripped:
                    in_multiline_comment = False
                    continue
                if in_multiline_comment:
                    continue
            
            # If we get here, it's a line of actual code
            code_lines += 1
            
        return code_lines
        
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
    # File type patterns to search for (actual code files only)
    patterns = {
        'python': ['**/*.py'],
        'javascript': ['**/*.js', '**/*.jsx'],
        'typescript': ['**/*.ts', '**/*.tsx'],
        'html': ['**/*.html', '**/*.htm'],
        'css': ['**/*.css', '**/*.scss', '**/*.sass'],
        'sql': ['**/*.sql'],
        'shell': ['**/*.sh', '**/*.bash'],
        'docker': ['**/Dockerfile*', '**/*.dockerfile']
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
    print("ODRAS Working Code Lines Counter")
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
