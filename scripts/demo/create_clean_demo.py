#!/usr/bin/env python3
"""
Create Clean Demo - Fresh 10-project lattice
"""

import httpx
import sys
from program_bootstrapper import ProgramBootstrapper

def main():
    print("🧹 Creating Clean Demo Lattice")
    print("=" * 50)
    
    # Authenticate
    client = httpx.Client(base_url="http://localhost:8000", timeout=30.0)
    resp = client.post("/api/auth/login", json={"username": "das_service", "password": "das_service_2024!"})
    if resp.status_code != 200:
        print("❌ Authentication failed")
        return False
    
    token = resp.json().get("access_token") or resp.json().get("token")
    client.headers.update({"Authorization": f"Bearer {token}"})
    
    # Get all projects
    projs_resp = client.get("/api/projects")
    if projs_resp.status_code != 200:
        print("❌ Failed to get projects")
        return False
    
    all_projects = projs_resp.json().get("projects", [])
    print(f"Found {len(all_projects)} existing projects")
    
    # Delete ALL existing projects to start fresh
    print("\n🧹 Deleting all existing projects...")
    deleted = 0
    for project in all_projects:
        try:
            resp = client.delete(f"/api/projects/{project['project_id']}")
            if resp.status_code in [200, 204, 404]:
                deleted += 1
                if deleted % 10 == 0:
                    print(f"   Deleted {deleted} projects...")
        except:
            pass
    
    print(f"✅ Deleted {deleted} old projects")
    
    # Create fresh lattice
    print("\n🏗️  Creating fresh lattice...")
    bootstrapper = ProgramBootstrapper()
    bootstrapper.token = token
    bootstrapper.client = client
    
    requirements = """
    Maritime Surveillance Unmanned Surface Vehicle Requirements
    
    The system shall provide autonomous maritime surveillance capability.
    Required surveillance range of 50+ nautical miles.
    Autonomous operation for 48+ hours minimum.
    Cost-effective solution meeting affordability targets.
    """
    
    success = bootstrapper.bootstrap_from_requirements(requirements.strip())
    
    if success:
        print(f"\n✅ Created {len(bootstrapper.created_projects)} fresh projects")
        print("\n🌐 Open browser: http://localhost:8082/lattice_demo.html")
        print("   Should show exactly 10 projects in clean grid layout")
        return True
    else:
        print("\n❌ Failed to create lattice")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
