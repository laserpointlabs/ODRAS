"""
UI Tests for Ontology Workbench

Tests the ontology workbench functionality in the refactored frontend.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.ui
@pytest.mark.ontology
class TestOntologyWorkbench:
    """Test ontology workbench functionality"""
    
    def test_ontology_workbench_initializes(self, authenticated_page: Page):
        """Test that ontology workbench initializes correctly"""
        page = authenticated_page
        
        # Wait for main view to be visible
        page.wait_for_selector("#mainView[style*='display: grid']", timeout=10000)
        
        # Ontology workbench should exist and have active class
        ontology_workbench = page.locator("#wb-ontology.workbench.active")
        
        # Check that it exists and has the active class (may be hidden by CSS initially)
        assert ontology_workbench.count() > 0, "Ontology workbench not found"
        
        # Verify workbench has content structure
        assert page.locator("#wb-ontology").count() > 0, "Ontology workbench element not found"
        
        # Check for key elements
        assert page.locator("#ontoTree, #ontoEmpty").count() > 0, "Ontology tree or empty state not found"
    
    def test_ontology_workbench_has_canvas(self, authenticated_page: Page):
        """Test that ontology workbench has Cytoscape canvas"""
        page = authenticated_page
        
        # Wait for main view to be visible
        page.wait_for_selector("#mainView[style*='display: grid']", timeout=10000)
        
        # Wait for workbench to have active class (don't check visibility as CSS handles it)
        page.wait_for_function(
            "document.querySelector('#wb-ontology.workbench.active') !== null",
            timeout=5000
        )
        
        # Check for canvas element (may be hidden if no ontology selected)
        canvas = page.locator("#cy")
        empty_state = page.locator("#ontoEmpty")
        # Canvas or empty state should exist
        assert canvas.count() > 0 or empty_state.count() > 0, "Canvas or empty state should exist"
    
    def test_ontology_workbench_switching(self, authenticated_page: Page):
        """Test that switching to ontology workbench works"""
        page = authenticated_page
        
        # Wait for main view to be visible
        page.wait_for_selector("#mainView[style*='display: grid']", timeout=10000)
        
        # Wait for initial workbench to have active class
        page.wait_for_function(
            "document.querySelector('#wb-ontology.workbench.active') !== null",
            timeout=5000
        )
        
        # Switch away from ontology first
        page.locator('[data-wb="requirements"]').click()
        page.wait_for_timeout(500)
        
        # Verify ontology is not active (should not have active class)
        ontology_workbench = page.locator("#wb-ontology.workbench")
        assert not ontology_workbench.evaluate("el => el.classList.contains('active')"), "Ontology workbench should not be active"
        
        # Switch back to ontology
        page.locator('[data-wb="ontology"]').click()
        page.wait_for_timeout(500)
        
        # Verify ontology is active (has active class)
        page.wait_for_function(
            "document.querySelector('#wb-ontology.workbench.active') !== null",
            timeout=5000
        )
    
    def test_ontology_tree_panel_exists(self, authenticated_page: Page):
        """Test that ontology tree panel exists"""
        page = authenticated_page
        
        # Wait for main view to be visible
        page.wait_for_selector("#mainView[style*='display: grid']", timeout=10000)
        
        # Wait for workbench to have active class
        page.wait_for_function(
            "document.querySelector('#wb-ontology.workbench.active') !== null",
            timeout=5000
        )
        
        # Check for tree panel (may be in layout section)
        tree_panel = page.locator("#ontoTree, .onto-tree")
        empty_state = page.locator("#ontoEmpty")
        # Tree panel or empty state should exist
        assert tree_panel.count() > 0 or empty_state.count() > 0, "Tree panel or empty state should exist"
    
    def test_ontology_properties_panel_exists(self, authenticated_page: Page):
        """Test that ontology properties panel exists"""
        page = authenticated_page
        
        # Wait for main view to be visible
        page.wait_for_selector("#mainView[style*='display: grid']", timeout=10000)
        
        # Wait for workbench to have active class
        page.wait_for_function(
            "document.querySelector('#wb-ontology.workbench.active') !== null",
            timeout=5000
        )
        
        # Check for properties panel
        props_panel = page.locator("#ontoProps, .onto-props")
        # Properties panel should exist
        assert props_panel.count() > 0, "Properties panel should exist"
