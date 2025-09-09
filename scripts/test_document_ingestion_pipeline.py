#!/usr/bin/env python3
"""
Test Script for Document Ingestion BPMN Pipeline
Tests the document ingestion workflow through Camunda.
"""

import json
import sys
import os
import time
import tempfile
from pathlib import Path
from typing import Dict

import requests


def create_test_document(content: str) -> str:
    """Create a temporary test document."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(content)
        return f.name


def deploy_document_ingestion_workflow(camunda_url: str, bpmn_path: str) -> bool:
    """Deploy the document ingestion workflow to Camunda."""
    try:
        deployment_url = f"{camunda_url}/deployment/create"

        with open(bpmn_path, "rb") as bpmn_file:
            files = {
                "deployment-name": (None, "Document Ingestion Pipeline"),
                "enable-duplicate-filtering": (None, "false"),
                "deploy-changed-only": (None, "true"),
                os.path.basename(bpmn_path): (
                    os.path.basename(bpmn_path),
                    bpmn_file,
                    "application/xml",
                ),
            }

            response = requests.post(deployment_url, files=files, timeout=30)

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Successfully deployed Document Ingestion Pipeline")
                print(f"   Deployment ID: {result.get('id')}")
                return True
            else:
                print(f"❌ Failed to deploy workflow: {response.status_code}")
                print(f"   Error: {response.text}")
                return False

    except Exception as e:
        print(f"❌ Exception during deployment: {str(e)}")
        return False


def start_document_ingestion_process(camunda_url: str, document_path: str, filename: str) -> str:
    """Start a document ingestion process instance."""
    try:
        start_url = f"{camunda_url}/process-definition/key/document_ingestion_process/start"

        payload = {
            "variables": {
                "document_content": {"value": document_path, "type": "String"},
                "document_filename": {"value": filename, "type": "String"},
                "document_mime_type": {"value": "text/plain", "type": "String"},
            }
        }

        response = requests.post(start_url, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            instance_id = result.get("id")
            print(f"✅ Started document ingestion process")
            print(f"   Process Instance ID: {instance_id}")
            return instance_id
        else:
            print(f"❌ Failed to start process: {response.status_code}")
            print(f"   Error: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Exception starting process: {str(e)}")
        return None


def main():
    """Main test function."""
    camunda_url = "http://localhost:8080/engine-rest"
    bpmn_path = Path(__file__).parent.parent / "bpmn" / "document_ingestion_pipeline.bpmn"

    print("🧪 Document Ingestion Pipeline Test")
    print("=" * 40)

    # Check Camunda connection
    try:
        response = requests.get(f"{camunda_url}/engine", timeout=5)
        if response.status_code != 200:
            print(f"❌ Cannot connect to Camunda at {camunda_url}")
            print("   Make sure Camunda is running with: docker compose up -d")
            sys.exit(1)
        print(f"✅ Connected to Camunda")
    except Exception as e:
        print(f"❌ Cannot connect to Camunda: {str(e)}")
        sys.exit(1)

    # Deploy the workflow
    if not deploy_document_ingestion_workflow(camunda_url, str(bpmn_path)):
        sys.exit(1)

    # Create persistent test document
    test_content = """
This is a test document for the document ingestion pipeline.

The system shall process documents efficiently and extract meaningful content.
The document ingestion pipeline must handle various document formats including text, PDF, and Word documents.

Requirements:
- The system shall validate all uploaded documents
- The system must chunk documents into appropriate sizes  
- The system shall generate vector embeddings for all chunks
- The system must store embeddings in the vector database
- The system shall update search indices for discoverability

This test document contains enough content to test the chunking and embedding generation processes.
It includes multiple paragraphs and requirements statements that should be properly processed.

The system shall ensure data integrity throughout the pipeline.
Performance requirements specify that documents must be processed within 60 seconds.
The system must support concurrent processing of multiple documents.
"""

    document_path = "/tmp/odras-test/ingestion_test_document.txt"
    os.makedirs(os.path.dirname(document_path), exist_ok=True)
    with open(document_path, "w", encoding="utf-8") as f:
        f.write(test_content.strip())

    filename = "ingestion_test_document.txt"

    print(f"\n📄 Created test document: {document_path}")
    print(f"   Content length: {len(test_content)} characters")

    # Start the process
    instance_id = start_document_ingestion_process(camunda_url, document_path, filename)

    if instance_id:
        print("\n🎯 Document Ingestion Process Started Successfully!")
        print("\n💡 Next Steps:")
        print("   1. Start external task worker: python scripts/run_external_task_worker.py")
        print("   2. Monitor in Camunda Cockpit: http://localhost:8080")
        print(f"   3. Process Instance ID: {instance_id}")

        return instance_id
    else:
        print("❌ Failed to start document ingestion process")
        return None


if __name__ == "__main__":
    main()
