#!/usr/bin/env python3
"""
Test script for reference ontologies functionality.
This script tests the new admin reference ontology feature.
"""

import requests
import json
import sys
import os

# Add the backend directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from services.db import DatabaseService


def test_database_functionality():
    """Test the database service methods for reference ontologies."""
    print("Testing database functionality...")

    try:
        db = DatabaseService()

        # Test listing reference ontologies
        reference_ontologies = db.list_reference_ontologies()
        print(f"Found {len(reference_ontologies)} reference ontologies")

        for onto in reference_ontologies:
            print(
                f"  - {onto.get('label', 'No label')} ({onto.get('graph_iri', 'No IRI')})"
            )
            print(f"    Project: {onto.get('project_name', 'Unknown')}")

        print("✅ Database functionality test passed")
        return True

    except Exception as e:
        print(f"❌ Database functionality test failed: {e}")
        return False


def test_api_endpoints():
    """Test the API endpoints for reference ontologies."""
    print("\nTesting API endpoints...")

    base_url = "http://localhost:8000"

    try:
        # First, try to login as admin
        login_data = {"username": "admin", "password": "admin"}  # Adjust if different

        response = requests.post(f"{base_url}/api/auth/login", json=login_data)
        if response.status_code != 200:
            print("❌ Failed to login as admin")
            return False

        token = response.json().get("token")
        if not token:
            print("❌ No token received from login")
            return False

        headers = {"Authorization": f"Bearer {token}"}

        # Test the reference ontologies endpoint
        response = requests.get(f"{base_url}/api/ontologies/reference", headers=headers)
        if response.status_code == 200:
            data = response.json()
            reference_ontologies = data.get("reference_ontologies", [])
            print(
                f"✅ API endpoint test passed - found {len(reference_ontologies)} reference ontologies"
            )

            for onto in reference_ontologies:
                print(
                    f"  - {onto.get('label', 'No label')} ({onto.get('graph_iri', 'No IRI')})"
                )
                print(f"    Project: {onto.get('project_name', 'Unknown')}")
        else:
            print(
                f"❌ API endpoint test failed with status {response.status_code}: {response.text}"
            )
            return False

        return True

    except requests.exceptions.ConnectionError:
        print(
            "❌ Could not connect to the API server. Make sure the server is running on localhost:8000"
        )
        return False
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Testing Reference Ontologies Feature")
    print("=" * 50)

    # Test database functionality
    db_test_passed = test_database_functionality()

    # Test API endpoints
    api_test_passed = test_api_endpoints()

    print("\n" + "=" * 50)
    if db_test_passed and api_test_passed:
        print("🎉 All tests passed! Reference ontologies feature is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
