#!/usr/bin/env python3
"""
Verify what CQMT data exists in the system and provide direct access URLs.
"""

import httpx
import json

BASE_URL = "http://localhost:8000"

def main():
    print("🔍 Verifying CQMT Test Data")
    print("=" * 60)
    
    # Login
    with httpx.Client() as client:
        login_response = client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            return
        
        token = login_response.json().get("access_token") or login_response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
    
    # Get all projects
    with httpx.Client(headers=headers) as client:
        projects_response = client.get(f"{BASE_URL}/api/projects")
        if projects_response.status_code != 200:
            print(f"❌ Failed to get projects: {projects_response.status_code}")
            return
        
        projects = projects_response.json().get("projects", [])
        print(f"\n📋 Found {len(projects)} project(s):\n")
        
        for idx, project in enumerate(projects, 1):
            project_id = project.get("project_id")
            project_name = project.get("name")
            print(f"{idx}. {project_name}")
            print(f"   ID: {project_id}")
            
            # Check ontologies
            ontos_response = client.get(f"{BASE_URL}/api/ontologies?project={project_id}")
            ontos = ontos_response.json().get("ontologies", [])
            print(f"   Ontologies: {len(ontos)}")
            for onto in ontos:
                print(f"      - {onto.get('label')} ({onto.get('graphIri')})")
            
            # Check CQs
            try:
                cqs_response = client.get(f"{BASE_URL}/api/cqmt/projects/{project_id}/cqs")
                cqs = cqs_response.json() if isinstance(cqs_response.json(), list) else []
                print(f"   CQs: {len(cqs)}")
                for cq in cqs:
                    print(f"      - {cq.get('cq_name')} ({cq.get('id')})")
            except Exception as e:
                print(f"   CQs: Error - {e}")
            
            # Check MTs
            try:
                mts_response = client.get(f"{BASE_URL}/api/cqmt/projects/{project_id}/microtheories")
                mts = mts_response.json() if isinstance(mts_response.json(), list) else []
                print(f"   MTs: {len(mts)}")
                for mt in mts:
                    print(f"      - {mt.get('label')} ({mt.get('iri')}) {'[Default]' if mt.get('is_default') else ''}")
            except Exception as e:
                print(f"   MTs: Error - {e}")
            
            # Provide access URLs
            if len(ontos) > 0:
                onto = ontos[0]
                print(f"\n   🌐 Access URLs:")
                print(f"      Ontology: http://localhost:8000/app?project={project_id}&wb=ontology&graph={onto.get('graphIri')}")
                print(f"      CQ/MT: http://localhost:8000/app?project={project_id}&wb=cqmt")
            
            print()

if __name__ == "__main__":
    main()
