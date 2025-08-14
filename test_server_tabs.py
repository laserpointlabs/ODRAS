#!/usr/bin/env python3
"""Test if the server tabs are working properly."""

import requests
import webbrowser
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_server_tabs():
    """Test the server tabs functionality."""
    try:
        # Test the server
        response = requests.get("http://localhost:8000/user-review")
        if response.status_code == 200:
            logger.info("✅ Server is running")
            
            # Parse the HTML to find tab buttons
            html = response.text
            
            # Find tab buttons
            tab_buttons = []
            lines = html.split('\n')
            for line in lines:
                if 'onclick="showTab(' in line:
                    # Extract button text and onclick
                    if '<button' in line and 'onclick=' in line:
                        # Simple parsing - in production use BeautifulSoup
                        parts = line.split('onclick="showTab(\'')
                        if len(parts) > 1:
                            tab_id = parts[1].split('\'')[0]
                            # Find button text
                            text_start = line.find('>') + 1
                            text_end = line.find('</button>')
                            if text_start > 0 and text_end > text_start:
                                btn_text = line[text_start:text_end].strip()
                                tab_buttons.append((tab_id, btn_text))
            
            logger.info(f"Found {len(tab_buttons)} tab buttons:")
            for tab_id, btn_text in tab_buttons:
                onclick = f"showTab('{tab_id}')"
                logger.info(f"  - {btn_text}: onclick='{onclick}'")
            
            # Find tab content divs
            tab_contents = []
            for line in lines:
                if 'id="' in line and '-tab"' in line:
                    # Extract div ID and classes
                    if 'id="' in line:
                        id_start = line.find('id="') + 4
                        id_end = line.find('"', id_start)
                        if id_start > 3 and id_end > id_start:
                            div_id = line[id_start:id_end]
                            # Find classes
                            classes = ""
                            if 'class="' in line:
                                class_start = line.find('class="') + 7
                                class_end = line.find('"', class_start)
                                if class_start > 6 and class_end > class_start:
                                    classes = line[class_start:class_end]
                            tab_contents.append((div_id, classes))
            
            logger.info(f"\nFound {len(tab_contents)} tab content divs:")
            for div_id, classes in tab_contents:
                logger.info(f"  - {div_id}: classes={classes}")
            
            # Check if showTab function is defined
            if 'function showTab(' in html:
                logger.info("\n✅ window.showTab function is defined")
            else:
                logger.warning("\n❌ window.showTab function NOT found")
            
            # Test each tab button
            for tab_id, btn_text in tab_buttons:
                if f'id="{tab_id}-tab"' in html:
                    logger.info(f"✅ Found {tab_id}")
                else:
                    logger.warning(f"❌ Missing {tab_id}")
            
            # Check showTab function implementation
            if 'showTab(' in html:
                logger.info("\n✅ showTab function implementation found")
                # Check if it looks for correct element IDs
                if f'getElementById(\'{tab_id}-tab\')' in html or f'getElementById("{tab_id}-tab")' in html:
                    logger.info("✅ Function correctly looks for tabName + '-tab'")
                else:
                    logger.warning("❌ Function may not be looking for correct element IDs")
            
            return True
            
        else:
            logger.error(f"❌ Server returned status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        logger.error("❌ Could not connect to server. Make sure it's running on localhost:8000")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing server: {e}")
        return False

if __name__ == "__main__":
    test_server_tabs()
