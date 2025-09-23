#!/usr/bin/env python3
"""
Test script for comprehensive cleanup functionality
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123!"

def login():
    """Login and get admin token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD
    })

    if response.status_code == 200:
        token = response.json()["token"]
        print(f"✅ Logged in as admin")
        return token
    else:
        print(f"❌ Login failed: {response.status_code}")
        return None

def test_cleanup_unknown_assets(token):
    """Test the cleanup unknown assets endpoint"""
    print("\n🧹 Testing cleanup unknown assets...")

    headers = {"Authorization": f"Bearer {token}"}

    # Test dry run
    response = requests.delete(
        f"{BASE_URL}/api/knowledge/admin/cleanup-unknown?dry_run=true",
        headers=headers
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Dry run successful: {result['message']}")
        return True
    else:
        print(f"❌ Dry run failed: {response.status_code} - {response.text}")
        return False

def test_files_admin_endpoint(token):
    """Test the files admin endpoint"""
    print("\n📁 Testing files admin endpoint...")

    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(
        f"{BASE_URL}/api/files/admin/all?limit=100",
        headers=headers
    )

    if response.status_code == 200:
        result = response.json()
        files = result.get("files", [])
        print(f"✅ Found {len(files)} files")

        # Check for potential duplicates
        file_groups = {}
        for file in files:
            key = f"{file['filename']}_{file['size']}"
            if key not in file_groups:
                file_groups[key] = []
            file_groups[key].append(file)

        duplicates = {k: v for k, v in file_groups.items() if len(v) > 1}
        if duplicates:
            print(f"🔍 Found {len(duplicates)} potential duplicate groups:")
            for key, group in duplicates.items():
                print(f"   - {key}: {len(group)} files")
        else:
            print("✅ No duplicate files found")

        return True
    else:
        print(f"❌ Files admin endpoint failed: {response.status_code} - {response.text}")
        return False

def test_knowledge_assets_admin_endpoint(token):
    """Test the knowledge assets admin endpoint"""
    print("\n🧠 Testing knowledge assets admin endpoint...")

    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(
        f"{BASE_URL}/api/knowledge/admin/assets?limit=100",
        headers=headers
    )

    if response.status_code == 200:
        result = response.json()
        assets = result.get("assets", [])
        print(f"✅ Found {len(assets)} knowledge assets")

        # Check for problematic assets
        problematic = []
        for asset in assets:
            title = asset.get("title", "")
            if not title or title == "unknown" or title == "":
                problematic.append(asset)

        if problematic:
            print(f"🔍 Found {len(problematic)} potentially problematic assets:")
            for asset in problematic[:5]:  # Show first 5
                print(f"   - ID: {asset['id']}, Title: '{asset.get('title', 'NULL')}'")
        else:
            print("✅ No problematic knowledge assets found")

        return True
    else:
        print(f"❌ Knowledge assets admin endpoint failed: {response.status_code} - {response.text}")
        return False

def main():
    """Main test function"""
    print("🚀 Testing Comprehensive Cleanup Functionality")
    print("=" * 50)

    # Login
    token = login()
    if not token:
        return 1

    # Test all endpoints
    success = True

    success &= test_cleanup_unknown_assets(token)
    success &= test_files_admin_endpoint(token)
    success &= test_knowledge_assets_admin_endpoint(token)

    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed! Comprehensive cleanup functionality is working.")
        print("\n📋 Summary:")
        print("   - Admin authentication: ✅")
        print("   - Cleanup unknown assets: ✅")
        print("   - Files admin endpoint: ✅")
        print("   - Knowledge assets admin endpoint: ✅")
        print("\n🎉 The comprehensive cleanup button should now work properly!")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
