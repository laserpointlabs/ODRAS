#!/usr/bin/env python3
"""
Clear all projects for das_service account.

Usage:
    python scripts/demo/clear_das_service_projects.py
"""

import sys
import httpx
from typing import List, Dict

ODRAS_BASE_URL = "http://localhost:8000"
USERNAME = "das_service"
PASSWORD = "das_service_2024!"


def authenticate(client: httpx.Client) -> bool:
    """Authenticate with ODRAS API."""
    print(f"🔐 Authenticating as {USERNAME}...")
    try:
        response = client.post(
            "/api/auth/login",
            json={"username": USERNAME, "password": PASSWORD}
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token") or data.get("token")
            if token:
                client.headers.update({"Authorization": f"Bearer {token}"})
                print(f"✅ Authenticated successfully")
                return True
            else:
                print(f"❌ No token in response: {data}")
                return False
        else:
            print(f"❌ Authentication failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return False


def get_all_projects(client: httpx.Client) -> List[Dict]:
    """Get all projects for the authenticated user."""
    try:
        response = client.get("/api/projects?state=all")
        if response.status_code == 200:
            data = response.json()
            return data.get("projects", [])
        else:
            print(f"❌ Failed to get projects: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"❌ Error getting projects: {e}")
        return []


def delete_project(client: httpx.Client, project_id: str, project_name: str) -> bool:
    """Delete a project."""
    try:
        response = client.delete(f"/api/projects/{project_id}")
        if response.status_code in [200, 204]:
            print(f"   ✅ Deleted: {project_name} ({project_id})")
            return True
        else:
            print(f"   ⚠️  Failed to delete {project_name}: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error deleting {project_name}: {e}")
        return False


def main():
    """Main entry point."""
    print("=" * 60)
    print("Clearing all projects for das_service account")
    print("=" * 60)
    
    client = httpx.Client(base_url=ODRAS_BASE_URL, timeout=30.0)
    
    # Authenticate
    if not authenticate(client):
        print("❌ Authentication failed. Exiting.")
        sys.exit(1)
    
    # Get all projects
    print("\n📋 Fetching all projects...")
    projects = get_all_projects(client)
    
    if not projects:
        print("✅ No projects found. Nothing to delete.")
        return
    
    print(f"Found {len(projects)} project(s)")
    
    # Confirm deletion
    print("\n⚠️  WARNING: This will delete ALL projects for das_service!")
    response = input("Continue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("❌ Cancelled.")
        return
    
    # Delete all projects
    print("\n🗑️  Deleting projects...")
    deleted_count = 0
    failed_count = 0
    
    for project in projects:
        project_id = project.get("project_id")
        project_name = project.get("name", "Unknown")
        
        if delete_project(client, project_id, project_name):
            deleted_count += 1
        else:
            failed_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"   ✅ Deleted: {deleted_count}")
    if failed_count > 0:
        print(f"   ❌ Failed: {failed_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
