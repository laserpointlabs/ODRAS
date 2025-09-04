#!/usr/bin/env python3
"""
BPMN Step 2: Chunk Document Content

Focused script for intelligent document chunking.
This script reads extracted text and creates semantic chunks.

Usage: python3 step_chunk_document.py <file_id> <chunking_strategy> <chunk_size>
"""

import sys
import os
import asyncio
import json
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.chunking_service import get_chunking_service
from backend.services.config import Settings

async def chunk_document_content(file_id: str, chunking_strategy: str = "hybrid", chunk_size: int = 512):
    """Chunk document content using intelligent strategies."""
    try:
        settings = Settings()
        
        # Get chunking service
        chunking_service = get_chunking_service(settings)
        
        print(f"🔪 Step 2: Chunking document {file_id} with {chunking_strategy} strategy")
        
        # Read extracted text from step 1 (from BPMN process variables or temp storage)
        # In a real BPMN setup, this would come from process variables
        # For now, we'll need to get it from the previous step's output
        
        # TODO: In production, read from BPMN process variables
        # For now, let's assume text is passed via environment or temp file
        extracted_text = os.getenv('EXTRACTED_TEXT', '')
        
        if not extracted_text:
            # Fallback: try to read from a temporary file created by previous step
            temp_file = f"/tmp/odras_text_{file_id}.txt"
            if os.path.exists(temp_file):
                with open(temp_file, 'r', encoding='utf-8') as f:
                    extracted_text = f.read()
            else:
                raise ValueError("No extracted text available from previous step")
        
        if not extracted_text.strip():
            raise ValueError("Empty text content cannot be chunked")
        
        # Chunk the document
        chunks = chunking_service.chunk_document(
            text=extracted_text,
            document_metadata={'file_id': file_id, 'source': 'bpmn_workflow'},
            chunking_config={
                'chunking_strategy': chunking_strategy,
                'chunk_size': int(chunk_size),
                'chunk_overlap': 50
            }
        )
        
        if not chunks:
            raise ValueError("No chunks could be generated from content")
        
        # Serialize chunks for next step
        chunks_data = []
        for i, chunk in enumerate(chunks):
            chunks_data.append({
                'sequence_number': chunk.metadata.sequence_number,
                'content': chunk.content,
                'metadata': chunk.metadata.to_dict() if hasattr(chunk.metadata, 'to_dict') else chunk.metadata.__dict__,
                'chunk_index': i
            })
        
        # Store chunks for next step (in production, this would be BPMN variables)
        chunks_file = f"/tmp/odras_chunks_{file_id}.json"
        with open(chunks_file, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, indent=2)
        
        # Prepare output
        result = {
            "success": True,
            "file_id": file_id,
            "chunk_count": len(chunks),
            "chunking_strategy": chunking_strategy,
            "chunk_size": int(chunk_size),
            "chunks_file": chunks_file,
            "step": "document_chunking",
            "step_status": "completed"
        }
        
        print(f"✅ Document chunking completed: {len(chunks)} chunks created")
        print(f"📊 Strategy: {chunking_strategy}, Size: {chunk_size}")
        print("📋 BPMN_RESULT:", json.dumps(result))
        
        return result
        
    except Exception as e:
        error_result = {
            "success": False,
            "file_id": file_id,
            "error": str(e),
            "step": "document_chunking",
            "step_status": "failed"
        }
        
        print(f"❌ Document chunking failed: {str(e)}")
        print("📋 BPMN_RESULT:", json.dumps(error_result))
        
        sys.exit(1)

def main():
    """Main function for command line usage."""
    if len(sys.argv) < 2:
        print("Usage: python3 step_chunk_document.py <file_id> [chunking_strategy] [chunk_size]")
        sys.exit(1)
    
    file_id = sys.argv[1]
    chunking_strategy = sys.argv[2] if len(sys.argv) > 2 else "hybrid"
    chunk_size = int(sys.argv[3]) if len(sys.argv) > 3 else 512
    
    # Run async chunking
    asyncio.run(chunk_document_content(file_id, chunking_strategy, chunk_size))

if __name__ == "__main__":
    main()
