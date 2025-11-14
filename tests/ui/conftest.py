"""
UI Testing Configuration for ODRAS Frontend

Provides fixtures and utilities for Playwright-based UI testing.
"""

import pytest
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
import os
from typing import Generator


@pytest.fixture(scope="session")
def browser() -> Generator[Browser, None, None]:
    """Launch browser for UI tests"""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        yield browser
        browser.close()


@pytest.fixture(scope="function")
def context(browser: Browser) -> Generator[BrowserContext, None, None]:
    """Create browser context for each test"""
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        ignore_https_errors=True
    )
    yield context
    context.close()


@pytest.fixture(scope="function")
def page(context: BrowserContext) -> Generator[Page, None, None]:
    """Create page for each test"""
    page = context.new_page()
    
    # Set base URL from environment or default
    base_url = os.getenv("ODRAS_BASE_URL", "http://localhost:8000")
    page.set_default_timeout(30000)  # 30 second timeout for slow operations
    
    yield page
    page.close()


@pytest.fixture(scope="function")
def authenticated_page(page: Page) -> Generator[Page, None, None]:
    """
    Create authenticated page with test user logged in.
    
    Uses das_service credentials for automated testing.
    """
    base_url = os.getenv("ODRAS_BASE_URL", "http://localhost:8000")
    
    # Navigate to login page
    page.goto(f"{base_url}/app")
    
    # Wait for login form
    page.wait_for_selector("#u", timeout=10000)
    
    # Fill login form
    page.fill("#u", "das_service")
    page.fill("#p", "das_service_2024!")
    
    # Click login button
    page.click("#loginBtn")
    
    # Wait for main view (indicating successful login)
    page.wait_for_selector("#mainView", timeout=15000)
    
    # Verify we're logged in
    assert page.locator("#mainView").is_visible(), "Main view should be visible after login"
    
    yield page


@pytest.fixture(scope="function")
def test_project(authenticated_page: Page) -> str:
    """
    Create a test project and return its ID.
    
    Assumes authenticated page fixture.
    """
    # Navigate to project creation or use existing test project
    # For now, return a known test project ID
    # In the future, create a project via API and return its ID
    return "test-project-id"  # Placeholder - implement actual project creation

