#!/usr/bin/env python3
"""Test if the server tabs are working properly."""

import requests
from bs4 import BeautifulSoup
import re

# Fetch the page
response = requests.get("http://localhost:8000")
html = response.text

# Parse HTML
soup = BeautifulSoup(html, 'html.parser')

# Check for tab buttons
tab_buttons = soup.find_all('button', class_='tab-button')
print(f"Found {len(tab_buttons)} tab buttons:")
for btn in tab_buttons:
    onclick = btn.get('onclick', '')
    print(f"  - {btn.text.strip()}: onclick='{onclick}'")

# Check for tab content divs
tab_contents = soup.find_all('div', class_='tab-content')
print(f"\nFound {len(tab_contents)} tab content divs:")
for div in tab_contents:
    div_id = div.get('id', '')
    classes = div.get('class', [])
    print(f"  - {div_id}: classes={classes}")

# Check if showTab function is defined
if 'window.showTab' in html:
    print("\n✅ window.showTab function is defined")
else:
    print("\n❌ window.showTab function NOT found")

# Check for specific tab IDs
expected_tabs = ['upload-tab', 'personas-tab', 'prompts-tab', 'runs-tab']
for tab_id in expected_tabs:
    if soup.find('div', id=tab_id):
        print(f"✅ Found {tab_id}")
    else:
        print(f"❌ Missing {tab_id}")

# Extract and check the showTab function
script_match = re.search(r'window\.showTab\s*=\s*function.*?\n\s*}', html, re.DOTALL)
if script_match:
    print("\n✅ showTab function implementation found")
    # Check if it's looking for the right elements
    func_text = script_match.group()
    if "getElementById(tabName + '-tab')" in func_text:
        print("✅ Function correctly looks for tabName + '-tab'")
    else:
        print("❌ Function may not be looking for correct element IDs")
