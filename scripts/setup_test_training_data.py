"""
Setup Test Training Data for DAS Training Collections

Uploads example training documents to DAS training collections for testing.
This script is idempotent - can be run multiple times safely.
"""

import asyncio
import httpx
import os
from pathlib import Path
from typing import Dict, List

BASE_URL = "http://localhost:8000"
TEST_USERNAME = "admin"
TEST_PASSWORD = "admin123!"

# Training data mapping: collection domain -> file path
TRAINING_DATA = {
    "ontology": "tests/test_data/das_training/ontology_basics.txt",
    "requirements": "tests/test_data/das_training/requirements_writing.txt",
    "systems_engineering": "tests/test_data/das_training/systems_engineering.txt",
    "odras_usage": "tests/test_data/das_training/odras_usage.txt",
    "acquisition": "tests/test_data/das_training/acquisition_basics.txt",
}

COLLECTION_DOMAIN_MAP = {
    "ontology": "das_training_ontology",
    "requirements": "das_training_requirements",
    "systems_engineering": "das_training_systems_engineering",
    "odras_usage": "das_training_odras_usage",
    "acquisition": "das_training_acquisition",
}


async def get_auth_token(client: httpx.AsyncClient) -> str:
    """Get authentication token."""
    response = await client.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    response.raise_for_status()
    return response.json()["token"]


async def get_or_create_collection(
    client: httpx.AsyncClient, token: str, collection_name: str, domain: str, display_name: str
) -> str:
    """Get existing collection or create it if it doesn't exist."""
    # Check if collection exists
    try:
        response = await client.get(
            f"{BASE_URL}/api/das-training/collections",
            headers={"Authorization": f"Bearer {token}"},
            params={"active_only": False},
        )
        if response.status_code == 200:
            collections = response.json()
            
            # Find collection by name
            for collection in collections:
                if collection["collection_name"] == collection_name:
                    print(f"✓ Found existing collection: {display_name}")
                    return collection["collection_id"]
        else:
            print(f"  ⚠️  Warning: Could not list collections (status {response.status_code})")
    except Exception as e:
        print(f"  ⚠️  Warning: Error checking collections: {e}")
    
    # Create collection if it doesn't exist
    print(f"  Creating collection: {display_name}")
    try:
        response = await client.post(
            f"{BASE_URL}/api/das-training/collections",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "collection_name": collection_name,
                "display_name": display_name,
                "description": f"Training knowledge for {domain} domain",
                "domain": domain,
                "vector_size": 384,
                "embedding_model": "all-MiniLM-L6-v2",
            },
        )
        if response.status_code in [200, 201]:
            collection = response.json()
            print(f"  ✓ Created collection: {display_name}")
            return collection["collection_id"]
        else:
            error_msg = response.text
            print(f"  ✗ Failed to create collection: {error_msg}")
            raise Exception(f"Failed to create collection: {error_msg}")
    except Exception as e:
        print(f"  ✗ Error creating collection: {e}")
        raise


async def check_asset_exists(
    client: httpx.AsyncClient, token: str, collection_id: str, title: str
) -> List[Dict]:
    """Check if an asset with the given title already exists in the collection."""
    response = await client.get(
        f"{BASE_URL}/api/das-training/collections/{collection_id}/assets",
        headers={"Authorization": f"Bearer {token}"},
    )
    response.raise_for_status()
    assets = response.json()
    
    matching = [asset for asset in assets if asset["title"] == title]
    return matching


async def upload_training_document(
    client: httpx.AsyncClient,
    token: str,
    collection_id: str,
    file_path: Path,
    domain: str,
) -> Dict:
    """Upload a training document to a collection."""
    file_name = file_path.name
    title = file_path.stem.replace("_", " ").title()
    
    # Check if already uploaded and completed (not processing/failed)
    existing_assets = await check_asset_exists(client, token, collection_id, title)
    if existing_assets:
        # Check if any are completed
        completed = [a for a in existing_assets if a.get("processing_status") == "completed" and a.get("chunk_count", 0) > 0]
        if completed:
            print(f"  ⏭️  Skipping {title} (already processed with {completed[0].get('chunk_count', 0)} chunks)")
            return {"skipped": True, "title": title}
        # If stuck in processing/failed, delete and re-upload
        for asset in existing_assets:
            if asset.get("processing_status") in ["processing", "failed"]:
                print(f"  🗑️  Deleting stuck asset: {asset['asset_id']}")
                await client.delete(
                    f"{BASE_URL}/api/das-training/assets/{asset['asset_id']}",
                    headers={"Authorization": f"Bearer {token}"},
                )
    
    # Read file content
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Upload file
    print(f"  📄 Uploading {title}...")
    files = {"file": (file_name, content.encode("utf-8"), "text/plain")}
    data = {
        "title": title,
        "description": f"Example training document for {domain}",
        "source_type": "text",
        "chunking_strategy": "hybrid",
        "chunk_size": "512",
        "chunk_overlap": "50",
    }
    
    response = await client.post(
        f"{BASE_URL}/api/das-training/collections/{collection_id}/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data=data,
        timeout=120.0,  # Longer timeout for processing
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"  ✓ Uploaded {title} ({result.get('chunk_count', 0)} chunks)")
        return {"success": True, "title": title, **result}
    else:
        error_msg = response.text
        print(f"  ✗ Failed to upload {title}: {error_msg}")
        return {"success": False, "title": title, "error": error_msg}


async def setup_training_data():
    """Main function to set up all training data."""
    print("🚀 Setting up DAS Training Test Data")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Authenticate
        print("🔐 Authenticating...")
        token = await get_auth_token(client)
        print("✓ Authenticated\n")
        
        # Process each training domain
        results = {}
        for domain, file_path in TRAINING_DATA.items():
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                print(f"⚠️  Warning: File not found: {file_path}")
                continue
            
            collection_name = COLLECTION_DOMAIN_MAP.get(domain)
            if not collection_name:
                print(f"⚠️  Warning: No collection mapping for domain: {domain}")
                continue
            
            display_name = domain.replace("_", " ").title()
            print(f"📚 Processing {display_name} domain...")
            
            # Get or create collection
            collection_id = await get_or_create_collection(
                client, token, collection_name, domain, display_name
            )
            
            # Upload document
            result = await upload_training_document(
                client, token, collection_id, file_path_obj, domain
            )
            results[domain] = result
            print()
        
        # Summary
        print("=" * 60)
        print("📊 Summary:")
        uploaded = sum(1 for r in results.values() if r.get("success"))
        skipped = sum(1 for r in results.values() if r.get("skipped"))
        failed = sum(1 for r in results.values() if not r.get("success") and not r.get("skipped"))
        
        print(f"  ✓ Uploaded: {uploaded}")
        print(f"  ⏭️  Skipped (already exists): {skipped}")
        print(f"  ✗ Failed: {failed}")
        
        if uploaded > 0 or skipped > 0:
            print("\n✅ Training data setup complete!")
            print("   Training collections are ready for testing.")
        else:
            print("\n⚠️  No training data was uploaded.")


if __name__ == "__main__":
    asyncio.run(setup_training_data())
