#!/usr/bin/env python3
"""
Test script for persona and prompt management functionality.
This script demonstrates how to use the new API endpoints.
"""

import requests
import json

# Base URL for the ODRAS API
BASE_URL = "http://localhost:8000"

def test_personas():
    """Test persona management endpoints."""
    print("=== Testing Persona Management ===")
    
    # List current personas
    print("\n1. Listing current personas:")
    response = requests.get(f"{BASE_URL}/api/personas")
    if response.status_code == 200:
        personas = response.json()["personas"]
        for persona in personas:
            print(f"  - {persona['name']}: {persona['description']}")
    else:
        print(f"Error: {response.status_code}")
    
    # Create a new persona
    print("\n2. Creating a new persona:")
    new_persona = {
        "name": "Tester",
        "description": "A test persona for validation",
        "system_prompt": "You are a test persona. Validate the input and return test results.",
        "is_active": True
    }
    
    response = requests.post(f"{BASE_URL}/api/personas", json=new_persona)
    if response.status_code == 200:
        created = response.json()["persona"]
        print(f"  Created: {created['name']} (ID: {created['id']})")
    else:
        print(f"Error creating persona: {response.status_code}")
    
    # Test updating a persona
    print("\n3. Updating a persona:")
    update_data = {"description": "Updated description for testing"}
    response = requests.put(f"{BASE_URL}/api/personas/extractor", json=update_data)
    if response.status_code == 200:
        updated = response.json()["persona"]
        print(f"  Updated: {updated['name']} - {updated['description']}")
    else:
        print(f"Error updating persona: {response.status_code}")

def test_prompts():
    """Test prompt management endpoints."""
    print("\n=== Testing Prompt Management ===")
    
    # List current prompts
    print("\n1. Listing current prompts:")
    response = requests.get(f"{BASE_URL}/api/prompts")
    if response.status_code == 200:
        prompts = response.json()["prompts"]
        for prompt in prompts:
            print(f"  - {prompt['name']}: {prompt['description']}")
    else:
        print(f"Error: {response.status_code}")
    
    # Create a new prompt
    print("\n2. Creating a new prompt:")
    new_prompt = {
        "name": "Test Prompt",
        "description": "A test prompt for validation",
        "prompt_template": "Test the following requirement: {requirement_text}",
        "variables": ["requirement_text"],
        "is_active": True
    }
    
    response = requests.post(f"{BASE_URL}/api/prompts", json=new_prompt)
    if response.status_code == 200:
        created = response.json()["prompt"]
        print(f"  Created: {created['name']} (ID: {created['id']})")
    else:
        print(f"Error creating prompt: {response.status_code}")
    
    # Test a prompt
    print("\n3. Testing a prompt:")
    test_variables = {"requirement_text": "The system shall be fast"}
    response = requests.post(f"{BASE_URL}/api/prompts/default_analysis/test", json=test_variables)
    if response.status_code == 200:
        result = response.json()
        print(f"  Test result:")
        print(f"    Filled prompt: {result['filled_prompt']}")
    else:
        print(f"Error testing prompt: {response.status_code}")

def test_ui():
    """Test the UI endpoints."""
    print("\n=== Testing UI ===")
    
    # Get the main page
    print("\n1. Getting main page:")
    response = requests.get(f"{BASE_URL}/")
    if response.status_code == 200:
        print(f"  Main page loaded successfully ({len(response.text)} characters)")
        if "Personas" in response.text and "Prompts" in response.text:
            print("  ✓ Personas and Prompts tabs found")
        else:
            print("  ✗ Personas and Prompts tabs not found")
    else:
        print(f"Error loading main page: {response.status_code}")

if __name__ == "__main__":
    try:
        test_personas()
        test_prompts()
        test_ui()
        print("\n=== All tests completed ===")
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to ODRAS API. Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"Error during testing: {e}")
