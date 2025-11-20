#!/usr/bin/env python3
"""
Convert markdown file to PDF with proper code block word wrapping.
"""

import sys
import os
import re
from pathlib import Path

try:
    import markdown
    from markdown.extensions import codehilite, fenced_code, tables
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown", "weasyprint", "--user"])
    import markdown
    from markdown.extensions import codehilite, fenced_code, tables

try:
    from weasyprint import HTML, CSS
except ImportError:
    print("Installing weasyprint...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "weasyprint", "--user"])
    from weasyprint import HTML, CSS


def remove_code_language_identifiers(markdown_text):
    """Remove language identifiers from code blocks."""
    # Pattern to match code block markers with language identifiers
    # Matches: ```bash, ```python, ```powershell, etc.
    pattern = r'^(\s*)```\w+'
    replacement = r'\1```'
    
    lines = markdown_text.split('\n')
    result = []
    for line in lines:
        # Replace code block markers with language identifiers with plain markers
        result.append(re.sub(pattern, replacement, line))
    
    return '\n'.join(result)


def wrap_code_blocks(markdown_text):
    """Wrap long lines in code blocks to prevent overflow."""
    # Split into lines
    lines = markdown_text.split('\n')
    result = []
    in_code_block = False
    code_block_indent = 0
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Detect code block start
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            result.append(line)
            if in_code_block:
                # Get the language identifier if present
                code_block_indent = len(line) - len(line.lstrip())
            i += 1
            continue
        
        if in_code_block:
            # For code blocks, wrap long lines
            # Preserve indentation
            indent = len(line) - len(line.lstrip())
            content = line.lstrip()
            
            # If line is too long (more than 80 chars), wrap it
            if len(content) > 80 and content.strip():
                # Split on spaces to preserve words
                words = content.split(' ')
                current_line = ' ' * indent
                
                for word in words:
                    # Check if adding this word would exceed 80 chars
                    if len(current_line) + len(word) + 1 > 80 and current_line.strip():
                        result.append(current_line.rstrip())
                        current_line = ' ' * indent + word
                    else:
                        if current_line.strip():
                            current_line += ' ' + word
                        else:
                            current_line += word
                
                if current_line.strip():
                    result.append(current_line.rstrip())
            else:
                result.append(line)
        else:
            result.append(line)
        
        i += 1
    
    return '\n'.join(result)


def markdown_to_pdf(markdown_file, output_file):
    """Convert markdown file to PDF with proper formatting."""
    
    # Read markdown file
    with open(markdown_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Remove language identifiers from code blocks
    md_content = remove_code_language_identifiers(md_content)
    
    # Wrap code blocks
    md_content = wrap_code_blocks(md_content)
    
    # Convert markdown to HTML (don't use codehilite to avoid language labels)
    md = markdown.Markdown(extensions=[
        'fenced_code',
        'tables',
        'toc',
        'nl2br'
    ])
    
    html_content = md.convert(md_content)
    
    # Create full HTML document with CSS for proper formatting
    html_template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {{
            size: letter;
            margin: 1in;
        }}
        
        body {{
            font-family: 'DejaVu Sans', Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #333;
        }}
        
        h1 {{
            font-size: 24pt;
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-top: 20px;
            page-break-after: avoid;
        }}
        
        h2 {{
            font-size: 18pt;
            color: #34495e;
            border-bottom: 2px solid #95a5a6;
            padding-bottom: 8px;
            margin-top: 30px;
            page-break-after: avoid;
        }}
        
        h3 {{
            font-size: 14pt;
            color: #555;
            margin-top: 25px;
            page-break-after: avoid;
        }}
        
        h4 {{
            font-size: 12pt;
            color: #666;
            margin-top: 20px;
            page-break-after: avoid;
        }}
        
        p {{
            margin: 10px 0;
            text-align: justify;
        }}
        
        code {{
            font-family: 'DejaVu Sans Mono', 'Courier New', monospace;
            font-size: 9pt;
            background-color: #f4f4f4;
            padding: 2px 4px;
            border-radius: 3px;
            word-wrap: break-word;
            word-break: break-all;
            white-space: pre-wrap;
        }}
        
        pre {{
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 12px;
            overflow-x: auto;
            page-break-inside: avoid;
            word-wrap: break-word;
            white-space: pre-wrap;
            font-family: 'DejaVu Sans Mono', 'Courier New', monospace;
            font-size: 9pt;
            line-height: 1.4;
        }}
        
        pre code {{
            background-color: transparent;
            padding: 0;
            border-radius: 0;
            word-wrap: break-word;
            word-break: break-all;
            white-space: pre-wrap;
            display: block;
        }}
        
        /* Hide any language labels that might appear */
        .codehilite::before,
        .highlight::before,
        pre::before,
        .language-label,
        [class*="language-"]::before {{
            display: none !important;
        }}
        
        /* Hide code block language identifiers */
        .codehilite .language,
        .highlight .language {{
            display: none !important;
        }}
        
        ul, ol {{
            margin: 10px 0;
            padding-left: 30px;
        }}
        
        li {{
            margin: 5px 0;
        }}
        
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
            page-break-inside: avoid;
        }}
        
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        
        th {{
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }}
        
        tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
        
        blockquote {{
            border-left: 4px solid #3498db;
            padding-left: 15px;
            margin: 15px 0;
            color: #555;
            font-style: italic;
        }}
        
        hr {{
            border: none;
            border-top: 2px solid #ddd;
            margin: 20px 0;
        }}
        
        strong {{
            color: #2c3e50;
        }}
        
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        
        .toc {{
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            padding: 15px;
            margin: 20px 0;
            page-break-inside: avoid;
        }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""
    
    # Convert HTML to PDF
    try:
        HTML(string=html_template).write_pdf(output_file)
        print(f"✓ Successfully created PDF: {output_file}")
        return True
    except Exception as e:
        print(f"✗ Error creating PDF: {e}")
        print("\nTrying alternative method...")
        
        # Fallback: try with reportlab if available
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            
            # This is a simpler fallback - just save HTML for manual conversion
            html_file = output_file.replace('.pdf', '.html')
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_template)
            print(f"✓ Created HTML file instead: {html_file}")
            print("  You can open this in a browser and print to PDF")
            return False
        except Exception as e2:
            print(f"✗ Fallback also failed: {e2}")
            return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 convert_markdown_to_pdf.py <markdown_file> [output_file]")
        sys.exit(1)
    
    markdown_file = sys.argv[1]
    if not os.path.exists(markdown_file):
        print(f"Error: File not found: {markdown_file}")
        sys.exit(1)
    
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        output_file = markdown_file.replace('.md', '.pdf')
    
    success = markdown_to_pdf(markdown_file, output_file)
    sys.exit(0 if success else 1)
