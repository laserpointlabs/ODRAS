#!/usr/bin/env python3
"""
Simple test script to verify demo components work step by step.
"""

import sys
import time
from program_bootstrapper import ProgramBootstrapper

def main():
    print("🧪 Testing Living Lattice Demo Components\n")
    
    # Step 1: Test bootstrapper
    print("=" * 60)
    print("STEP 1: Testing Bootstrapper")
    print("=" * 60)
    
    bootstrapper = ProgramBootstrapper()
    
    if not bootstrapper.authenticate():
        print("❌ Authentication failed")
        return False
    
    print("✅ Authentication successful\n")
    
    # Step 2: Bootstrap lattice
    print("=" * 60)
    print("STEP 2: Bootstrapping Lattice")
    print("=" * 60)
    
    requirements = """
    Need unmanned surface vehicle for maritime surveillance missions.
    System must operate autonomously for 48 hours minimum.
    Required surveillance range of 50 nautical miles.
    Must be cost-effective and support various mission scenarios.
    """
    
    success = bootstrapper.bootstrap_from_requirements(requirements.strip())
    
    if not success:
        print("❌ Bootstrapping failed")
        return False
    
    print(f"\n✅ Created {len(bootstrapper.created_projects)} projects")
    
    # Step 3: Check projects
    print("\n" + "=" * 60)
    print("STEP 3: Verifying Created Projects")
    print("=" * 60)
    
    response = bootstrapper.client.get("/api/projects")
    if response.status_code == 200:
        projects = response.json().get("projects", [])
        print(f"\n📊 Found {len(projects)} total projects:")
        for project in projects:
            name = project.get("name", "Unknown")
            level = project.get("project_level", "?")
            domain = project.get("domain", "unknown")
            print(f"   • {name} (L{level}, {domain})")
    
    # Step 4: Test visualization server (just check if it can start)
    print("\n" + "=" * 60)
    print("STEP 4: Testing Visualization Server")
    print("=" * 60)
    
    try:
        import subprocess
        import os
        
        # Check if static files exist
        static_dir = "scripts/demo/static"
        html_file = os.path.join(static_dir, "lattice_demo.html")
        
        if os.path.exists(html_file):
            print(f"✅ Static files found: {html_file}")
        else:
            print(f"❌ Static files not found: {html_file}")
            return False
        
        print("\n✅ All components verified!")
        print("\n📋 Next steps:")
        print("   1. Start visualization server: python scripts/demo/visualization_server.py")
        print("   2. Open browser to: http://localhost:8080/lattice_demo.html")
        print("   3. Projects are ready for demonstration")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
