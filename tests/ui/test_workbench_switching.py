"""
UI Tests for Workbench Switching

Tests the core workbench switching functionality in the refactored frontend.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.ui
class TestWorkbenchSwitching:
    """Test workbench switching functionality"""
    
    def test_requirements_workbench_loads(self, authenticated_page: Page):
        """Test that requirements workbench can be switched to and loads"""
        page = authenticated_page
        
        # Click requirements workbench icon
        requirements_icon = page.locator('[data-wb="requirements"]')
        expect(requirements_icon).to_be_visible()
        requirements_icon.click()
        
        # Wait for workbench to activate
        requirements_workbench = page.locator("#wb-requirements.workbench.active")
        expect(requirements_workbench).to_be_visible(timeout=10000)
        
        # Verify workbench content is loaded
        # (This will depend on what the requirements workbench actually renders)
        assert page.locator("#wb-requirements").is_visible()
    
    def test_ontology_workbench_loads(self, authenticated_page: Page):
        """Test that ontology workbench can be switched to and loads"""
        page = authenticated_page
        
        # Click ontology workbench icon
        ontology_icon = page.locator('[data-wb="ontology"]')
        expect(ontology_icon).to_be_visible()
        ontology_icon.click()
        
        # Wait for workbench to activate (check for active class, not visibility)
        page.wait_for_function(
            "document.querySelector('#wb-ontology.workbench.active') !== null",
            timeout=10000
        )
        
        # Verify workbench exists
        assert page.locator("#wb-ontology").count() > 0
    
    def test_workbench_switching_updates_url(self, authenticated_page: Page):
        """Test that switching workbenches updates the URL"""
        page = authenticated_page
        
        # Switch to requirements
        page.locator('[data-wb="requirements"]').click()
        page.wait_for_timeout(500)  # Wait for URL update
        
        # Check URL contains workbench parameter
        url = page.url
        assert "wb=requirements" in url or "requirements" in url.lower()
        
        # Switch to ontology
        page.locator('[data-wb="ontology"]').click()
        page.wait_for_timeout(500)
        
        # Check URL updated
        url = page.url
        assert "wb=ontology" in url or "ontology" in url.lower()
    
    def test_only_one_workbench_active(self, authenticated_page: Page):
        """Test that only one workbench is active at a time"""
        page = authenticated_page
        
        # Wait for main view
        page.wait_for_selector("#mainView[style*='display: grid']", timeout=10000)
        
        # Start with ontology (default active) - check for active class
        page.wait_for_function(
            "document.querySelector('#wb-ontology.workbench.active') !== null",
            timeout=5000
        )
        
        # Switch to requirements
        page.locator('[data-wb="requirements"]').click()
        page.wait_for_timeout(500)
        
        # Verify ontology is no longer active (no active class)
        ontology_wb = page.locator("#wb-ontology.workbench")
        assert not ontology_wb.evaluate("el => el.classList.contains('active')"), "Ontology should not be active"
        
        # Verify requirements is active (has active class)
        page.wait_for_function(
            "document.querySelector('#wb-requirements.workbench.active') !== null",
            timeout=5000
        )


@pytest.mark.ui
class TestAuthentication:
    """Test authentication flow"""
    
    def test_login_flow(self, page: Page):
        """Test that login flow works correctly"""
        base_url = "http://localhost:8000"
        page.goto(f"{base_url}/app")
        
        # Wait for login form
        page.wait_for_selector("#u", timeout=10000)
        
        # Fill credentials
        page.fill("#u", "das_service")
        page.fill("#p", "das_service_2024!")
        
        # Click login
        page.click("#loginBtn")
        
        # Wait for main view
        page.wait_for_selector("#mainView", timeout=15000)
        
        # Verify we're logged in
        expect(page.locator("#mainView")).to_be_visible()
        expect(page.locator("#authView")).not_to_be_visible()
    
    def test_logout_flow(self, authenticated_page: Page):
        """Test that logout flow works correctly"""
        page = authenticated_page
        
        # Click logout button
        logout_btn = page.locator("#logoutBtn")
        expect(logout_btn).to_be_visible()
        logout_btn.click()
        
        # Wait for auth view
        page.wait_for_selector("#authView", timeout=10000)
        
        # Verify we're logged out
        expect(page.locator("#authView")).to_be_visible()
        expect(page.locator("#mainView")).not_to_be_visible()
