#!/usr/bin/env python3
"""
BPMN Step 1: Extract Text Content

Focused script for text extraction from uploaded files.
This script is called by the BPMN workflow and handles only text extraction.

Usage: python3 step_extract_text.py <file_id> <project_id>
"""

import sys
import os
import asyncio
import json
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.file_storage import get_file_storage_service
from backend.services.knowledge_transformation import get_knowledge_transformation_service
from backend.services.config import Settings

async def extract_text_from_file(file_id: str, project_id: str):
    """Extract text content from file and output as JSON."""
    try:
        settings = Settings()
        
        # Get knowledge transformation service (has text extraction)
        knowledge_service = get_knowledge_transformation_service(settings)
        
        print(f"🔍 Step 1: Extracting text from file {file_id}")
        
        # Extract text content using existing service method
        extracted_text, extraction_metadata = await knowledge_service.extract_text_content(file_id)
        
        if not extracted_text or not extracted_text.strip():
            raise ValueError("No text content could be extracted from file")
        
        # Store extracted text for next step
        temp_text_file = f"/tmp/odras_text_{file_id}.txt"
        with open(temp_text_file, 'w', encoding='utf-8') as f:
            f.write(extracted_text)
        
        # Prepare output data
        result = {
            "success": True,
            "file_id": file_id,
            "project_id": project_id,
            "text_length": len(extracted_text),
            "temp_text_file": temp_text_file,
            "extraction_metadata": extraction_metadata,
            "step": "text_extraction",
            "step_status": "completed"
        }
        
        # Output result as JSON for BPMN process variables
        print("✅ Text extraction completed")
        print(f"📊 Extracted {len(extracted_text)} characters")
        print("📋 BPMN_RESULT:", json.dumps(result))
        
        return result
        
    except Exception as e:
        error_result = {
            "success": False,
            "file_id": file_id,
            "project_id": project_id,
            "error": str(e),
            "step": "text_extraction", 
            "step_status": "failed"
        }
        
        print(f"❌ Text extraction failed: {str(e)}")
        print("📋 BPMN_RESULT:", json.dumps(error_result))
        
        # Exit with error code for BPMN error handling
        sys.exit(1)

def main():
    """Main function for command line usage."""
    if len(sys.argv) < 3:
        print("Usage: python3 step_extract_text.py <file_id> <project_id>")
        sys.exit(1)
    
    file_id = sys.argv[1]
    project_id = sys.argv[2]
    
    # Run async extraction
    asyncio.run(extract_text_from_file(file_id, project_id))

if __name__ == "__main__":
    main()
