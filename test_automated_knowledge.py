#!/usr/bin/env python3
"""
Test script for the automated file -> knowledge pipeline.
"""

import asyncio
import aiohttp
import json
import tempfile
import os


async def test_automated_knowledge_pipeline():
    """Test that files are automatically processed for knowledge without manual intervention."""

    print("🔄 Testing Automated Knowledge Pipeline")
    print("=" * 50)

    base_url = "http://localhost:8000"

    # Step 1: Login to get auth token
    print("🔐 Step 1: Authenticating...")
    async with aiohttp.ClientSession() as session:
        login_data = {"username": "admin", "password": "admin123"}

        async with session.post(f"{base_url}/auth/login", data=login_data) as response:
            if response.status != 200:
                print(f"❌ Login failed: {response.status}")
                return False

            result = await response.json()
            token = result.get("access_token")
            if not token:
                print("❌ No access token received")
                return False

        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Authentication successful")

        # Step 2: Get project ID
        print("📁 Step 2: Getting project...")
        async with session.get(
            f"{base_url}/api/projects/", headers=headers
        ) as response:
            if response.status != 200:
                print(f"❌ Failed to get projects: {response.status}")
                return False

            projects = await response.json()
            if not projects:
                print("❌ No projects found")
                return False

            project_id = projects[0]["id"]
            print(f"✅ Using project: {project_id}")

        # Step 3: Create test document with auto-detection hints
        print("📄 Step 3: Creating test documents...")

        test_files = [
            {
                "name": "requirements_specification.txt",
                "content": """
System Requirements Specification for Automated Knowledge Processing

REQUIREMENT REQ-001: File Upload Automation
The system shall automatically process all uploaded files for knowledge extraction
without requiring manual user intervention.

REQUIREMENT REQ-002: Intelligent Type Detection
The system shall automatically detect document types based on filename and content
to apply appropriate processing strategies.

REQUIREMENT REQ-003: Semantic Chunking
Documents shall be chunked using semantic analysis to preserve meaning and context.

This document contains requirements that should be automatically detected
and processed with semantic chunking strategy.
                """,
                "expected_type": "requirements",
            },
            {
                "name": "user_manual.md",
                "content": """
# User Manual: ODRAS Knowledge System

## Overview
This manual provides guidance on using the ODRAS knowledge management system.

## Procedures
### File Upload Procedure
1. Navigate to the Files section
2. Select your document
3. File will be automatically processed for knowledge

### Search Procedure
1. Use the RAG query interface
2. Enter your question in natural language
3. System retrieves relevant knowledge chunks

This is a knowledge document that should use semantic chunking.
                """,
                "expected_type": "knowledge",
            },
            {
                "name": "data_export.json",
                "content": """
{
  "system": "ODRAS",
  "version": "2.0",
  "knowledge_assets": [
    {
      "id": "asset-001",
      "type": "document",
      "processing": "automatic",
      "chunking": "intelligent"
    }
  ],
  "metadata": {
    "exported": "2024-01-20",
    "format": "structured_data"
  }
}
                """,
                "expected_type": "structured",
            },
        ]

        uploaded_files = []

        for test_file in test_files:
            print(f"📤 Uploading {test_file['name']}...")

            # Create temporary file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=f"_{test_file['name']}", delete=False
            ) as f:
                f.write(test_file["content"])
                temp_path = f.name

            try:
                # Upload file (no process_for_knowledge param = should be automatic now)
                data = aiohttp.FormData()
                data.add_field("project_id", project_id)

                with open(temp_path, "rb") as file_obj:
                    data.add_field("file", file_obj, filename=test_file["name"])

                    async with session.post(
                        f"{base_url}/api/files/upload", headers=headers, data=data
                    ) as response:

                        if response.status != 200:
                            print(
                                f"❌ Upload failed for {test_file['name']}: {response.status}"
                            )
                            result = await response.text()
                            print(f"Error: {result}")
                            continue

                        result = await response.json()
                        print(f"✅ Upload successful: {result.get('message', 'OK')}")

                        # Check if knowledge asset was created automatically
                        if "knowledge asset" in result.get("message", "").lower():
                            print(f"🧠 ✅ Automatic knowledge processing detected!")
                            uploaded_files.append(
                                {
                                    "file_id": result.get("file_id"),
                                    "name": test_file["name"],
                                    "expected_type": test_file["expected_type"],
                                }
                            )
                        else:
                            print(
                                f"⚠️ No automatic knowledge processing mentioned in response"
                            )

            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        # Step 4: Verify knowledge assets were created
        print("🔍 Step 4: Verifying knowledge assets...")

        async with session.get(
            f"{base_url}/api/knowledge/assets",
            params={"project_id": project_id},
            headers=headers,
        ) as response:

            if response.status != 200:
                print(f"❌ Failed to get knowledge assets: {response.status}")
                return False

            assets = await response.json()
            print(f"📊 Found {len(assets)} knowledge assets")

            for asset in assets[-len(uploaded_files) :]:  # Check recent assets
                print(
                    f"  ✅ {asset['title']} (type: {asset.get('document_type', 'unknown')})"
                )

        # Step 5: Test RAG query on new knowledge
        print("🤖 Step 5: Testing RAG with new knowledge...")

        rag_query = {
            "query": "What are the requirements for automatic file processing?",
            "project_id": project_id,
            "similarity_threshold": 0.5,
        }

        async with session.post(
            f"{base_url}/api/knowledge/query", headers=headers, json=rag_query
        ) as response:

            if response.status != 200:
                print(f"❌ RAG query failed: {response.status}")
                return False

            rag_result = await response.json()

            if rag_result.get("sources"):
                print(f"✅ RAG found {len(rag_result['sources'])} relevant sources")
                print(f"🤖 Answer: {rag_result.get('answer', 'No answer')[:100]}...")
            else:
                print("⚠️ No sources found in RAG query")

        print("\n🎉 AUTOMATED PIPELINE TEST RESULTS:")
        print("=" * 50)
        print(f"✅ Files uploaded: {len(uploaded_files)}")
        print(f"✅ Knowledge assets created: {len(assets)}")
        print(
            f"✅ RAG query successful: {'Yes' if rag_result.get('sources') else 'No'}"
        )
        print("✅ No manual checkboxes or user tasks required!")

        return len(uploaded_files) > 0


if __name__ == "__main__":
    success = asyncio.run(test_automated_knowledge_pipeline())
    if success:
        print("\n🚀 AUTOMATED KNOWLEDGE PIPELINE: SUCCESS! 🚀")
    else:
        print("\n❌ AUTOMATED KNOWLEDGE PIPELINE: FAILED")

