#!/usr/bin/env python3
"""
Test script to verify DAS frontend integration

This script tests if the DAS dock is properly connected to the backend.
"""

import requests
import json

def test_das_frontend():
    """Test DAS frontend integration"""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing DAS Frontend Integration...")
    
    # Test 1: Check if main app loads
    try:
        response = requests.get(f"{base_url}/app")
        if response.status_code == 200:
            print("✅ Main app loads successfully")
            
            # Check if DAS dock HTML is present
            if "dasPanel" in response.text:
                print("✅ DAS dock HTML is present in the frontend")
            else:
                print("❌ DAS dock HTML not found in frontend")
        else:
            print(f"❌ Main app failed to load: {response.status_code}")
    except Exception as e:
        print(f"❌ Error loading main app: {e}")
    
    # Test 2: Check if ontology editor loads
    try:
        response = requests.get(f"{base_url}/ontology-editor")
        if response.status_code == 200:
            print("✅ Ontology editor loads successfully")
            
            # Check if DAS dock HTML is present
            if "dasPanel" in response.text:
                print("✅ DAS dock HTML is present in ontology editor")
            else:
                print("❌ DAS dock HTML not found in ontology editor")
        else:
            print(f"❌ Ontology editor failed to load: {response.status_code}")
    except Exception as e:
        print(f"❌ Error loading ontology editor: {e}")
    
    # Test 3: Check DAS API health
    try:
        response = requests.get(f"{base_url}/api/das/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ DAS API health check: {data['status']}")
        else:
            print(f"❌ DAS API health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error checking DAS API health: {e}")
    
    print("\n🎯 To test the DAS dock:")
    print("1. Open http://localhost:8000/app in your browser")
    print("2. Press Ctrl+Alt+D to open the DAS dock")
    print("3. Try asking: 'How do I upload a document?'")
    print("4. The DAS should return real guidance from the instruction collection")

if __name__ == "__main__":
    test_das_frontend()
