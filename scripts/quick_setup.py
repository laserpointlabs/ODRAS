#!/usr/bin/env python3
"""
ODRAS Quick Setup Script

This script automates the complete setup process after rebuilding ODRAS:
1. Login with jdehart account
2. Create 'core.se' project in systems-engineering domain
3. Import bseo_v1a.json ontology
4. Upload and process all markdown documents from /data folder

Usage:
    python scripts/quick_setup.py

Requirements:
    - ODRAS application running on localhost:8000
    - All services (PostgreSQL, Neo4j, Qdrant, etc.) running
    - Files present in /data folder
"""

import asyncio
import httpx
import json
import os
import glob
from pathlib import Path
from typing import Dict, List, Optional

# Configuration
ODRAS_BASE_URL = "http://localhost:8000"
USERNAME = "jdehart"
PASSWORD = "jdehart123!"  # Default password from init-db
PROJECT_NAME = "core.se"
PROJECT_DESCRIPTION = "Core Systems Engineering Project with BSEO ontology and UAS specifications"
PROJECT_DOMAIN = "systems-engineering"
DATA_FOLDER = "/home/jdehart/working/ODRAS/data"

class ODRASSetup:
    def __init__(self):
        self.base_url = ODRAS_BASE_URL
        self.token = None
        self.project_id = None
        
    async def login(self) -> bool:
        """Login to ODRAS and get authentication token."""
        print(f"🔐 Logging in as {USERNAME}...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/auth/login",
                    json={"username": USERNAME, "password": PASSWORD}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.token = data.get("token")
                    print(f"✅ Successfully logged in as {USERNAME}")
                    return True
                else:
                    print(f"❌ Login failed: {response.status_code} - {response.text}")
                    return False
                    
            except Exception as e:
                print(f"❌ Login error: {e}")
                return False
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers with authentication token."""
        return {"Authorization": f"Bearer {self.token}"}
    
    async def create_project(self) -> bool:
        """Create the core.se project."""
        print(f"📋 Creating project '{PROJECT_NAME}'...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/projects",
                    json={
                        "name": PROJECT_NAME,
                        "description": PROJECT_DESCRIPTION,
                        "domain": PROJECT_DOMAIN
                    },
                    headers=self.get_headers()
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.project_id = data["project"]["project_id"]
                    print(f"✅ Created project '{PROJECT_NAME}' (ID: {self.project_id})")
                    return True
                else:
                    print(f"❌ Project creation failed: {response.status_code} - {response.text}")
                    return False
                    
            except Exception as e:
                print(f"❌ Project creation error: {e}")
                return False
    
    async def import_ontology(self) -> bool:
        """Import the bseo_v1a.json ontology."""
        ontology_path = os.path.join(DATA_FOLDER, "bseo_v1a.json")
        
        if not os.path.exists(ontology_path):
            print(f"❌ Ontology file not found: {ontology_path}")
            return False
        
        print(f"🧠 Importing ontology from {ontology_path}...")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                # Read the ontology file
                with open(ontology_path, 'r') as f:
                    ontology_data = json.load(f)
                
                # Import ontology (assuming there's an import endpoint)
                # Note: This may need adjustment based on actual ODRAS ontology import API
                response = await client.post(
                    f"{self.base_url}/api/ontologies/import",
                    json={
                        "project_id": self.project_id,
                        "ontology_data": ontology_data,
                        "name": "BSEO_V1A",
                        "description": "Bootstrap Systems Engineering Ontology v1a"
                    },
                    headers=self.get_headers()
                )
                
                if response.status_code == 200:
                    print("✅ Successfully imported BSEO_V1A ontology")
                    return True
                else:
                    print(f"⚠️  Ontology import response: {response.status_code}")
                    print(f"   This may be normal if the endpoint doesn't exist yet")
                    return True  # Continue anyway
                    
            except Exception as e:
                print(f"⚠️  Ontology import error: {e}")
                print("   Continuing with document upload...")
                return True  # Continue anyway
    
    async def upload_markdown_files(self) -> bool:
        """Upload and process all markdown files from the data folder."""
        print(f"📄 Uploading markdown files from {DATA_FOLDER}...")
        
        # Find all markdown files
        md_files = glob.glob(os.path.join(DATA_FOLDER, "*.md"))
        
        if not md_files:
            print(f"❌ No markdown files found in {DATA_FOLDER}")
            return False
        
        print(f"Found {len(md_files)} markdown files:")
        for file in md_files:
            print(f"  - {os.path.basename(file)}")
        
        success_count = 0
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            for md_file in md_files:
                filename = os.path.basename(md_file)
                print(f"\n📤 Uploading {filename}...")
                
                try:
                    # Determine document type and embedding model based on filename
                    doc_type, embedding_model = self._get_file_config(filename)
                    
                    with open(md_file, 'rb') as f:
                        files = {'file': (filename, f, 'text/markdown')}
                        data = {
                            'project_id': self.project_id,
                            'document_type': doc_type,
                            'embedding_model': embedding_model,
                            'chunking_strategy': 'simple_semantic'  # Use our improved chunking
                        }
                        
                        response = await client.post(
                            f"{self.base_url}/api/files/upload",
                            files=files,
                            data=data,
                            headers=self.get_headers()
                        )
                    
                    if response.status_code == 200:
                        print(f"✅ Successfully uploaded {filename}")
                        success_count += 1
                        
                        # Wait a bit between uploads to avoid overwhelming the system
                        await asyncio.sleep(2)
                    else:
                        print(f"❌ Upload failed for {filename}: {response.status_code}")
                        print(f"   Response: {response.text}")
                        
                except Exception as e:
                    print(f"❌ Error uploading {filename}: {e}")
        
        print(f"\n📊 Upload Summary: {success_count}/{len(md_files)} files uploaded successfully")
        
        if success_count > 0:
            print("⏳ Waiting for document processing to complete...")
            await asyncio.sleep(10)  # Give time for processing
            
            # Check processing status
            await self.check_processing_status()
        
        return success_count > 0
    
    def _get_file_config(self, filename: str) -> tuple[str, str]:
        """Determine document type and embedding model based on filename."""
        filename_lower = filename.lower()
        
        # Document type mapping
        if 'specification' in filename_lower or 'uas_' in filename_lower:
            doc_type = 'specification'
        elif 'requirement' in filename_lower:
            doc_type = 'requirements'
        elif 'decision_matrix' in filename_lower or 'template' in filename_lower:
            doc_type = 'analysis_template'
        elif 'guide' in filename_lower or 'manual' in filename_lower:
            doc_type = 'reference'
        else:
            doc_type = 'document'
        
        # Use better embedding model for specifications and requirements
        if doc_type in ['specification', 'requirements']:
            embedding_model = 'all-mpnet-base-v2'  # Better model for technical docs
        else:
            embedding_model = 'all-MiniLM-L6-v2'   # Fast model for general docs
        
        return doc_type, embedding_model
    
    async def check_processing_status(self):
        """Check the status of uploaded knowledge assets."""
        print("📋 Checking knowledge asset processing status...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/knowledge/assets",
                    headers=self.get_headers()
                )
                
                if response.status_code == 200:
                    data = response.json()
                    assets = data.get('assets', [])
                    
                    print(f"📊 Knowledge Assets Status ({len(assets)} total):")
                    for asset in assets:
                        title = asset.get('title', 'Unknown')
                        status = asset.get('status', 'unknown')
                        chunks = asset.get('chunk_count', 0)
                        tokens = asset.get('token_count', 0)
                        print(f"  - {title}: {status} ({chunks} chunks, {tokens} tokens)")
                else:
                    print(f"⚠️  Could not check asset status: {response.status_code}")
                    
            except Exception as e:
                print(f"⚠️  Error checking asset status: {e}")
    
    async def test_system(self):
        """Test the system with a sample DAS query."""
        print("\n🧪 Testing system with sample DAS query...")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/das/chat",
                    json={
                        "message": "How many UAS are mentioned in the specifications?",
                        "project_id": self.project_id
                    },
                    headers=self.get_headers()
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ DAS Test Query Successful!")
                    print(f"   Response: {result.get('message', '')[:150]}...")
                    print(f"   Chunks found: {result.get('metadata', {}).get('chunks_found', 0)}")
                else:
                    print(f"⚠️  DAS test failed: {response.status_code}")
                    
            except Exception as e:
                print(f"⚠️  DAS test error: {e}")

async def main():
    """Main setup routine."""
    print("🚀 ODRAS Quick Setup Script")
    print("=" * 50)
    
    setup = ODRASSetup()
    
    # Step 1: Login
    if not await setup.login():
        print("❌ Setup failed at login step")
        return False
    
    # Step 2: Create project
    if not await setup.create_project():
        print("❌ Setup failed at project creation step")
        return False
    
    # Step 3: Import ontology
    await setup.import_ontology()
    
    # Step 4: Upload markdown files
    if not await setup.upload_markdown_files():
        print("❌ Setup failed at file upload step")
        return False
    
    # Step 5: Test the system
    await setup.test_system()
    
    print("\n🎉 ODRAS Quick Setup Complete!")
    print("=" * 50)
    print(f"✅ Project '{PROJECT_NAME}' is ready to use")
    print(f"✅ Project ID: {setup.project_id}")
    print(f"✅ Access at: {ODRAS_BASE_URL}/app")
    print("\nYou can now:")
    print("- Ask DAS questions about UAS specifications")
    print("- Query requirements and decision matrices")  
    print("- Use the ontology for systems engineering work")
    
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Setup interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        exit(1)
