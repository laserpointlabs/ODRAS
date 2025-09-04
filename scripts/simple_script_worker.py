#!/usr/bin/env python3
"""
Simple Script Worker for BPMN Orchestration

This worker subscribes to BPMN external tasks and executes corresponding Python scripts.
No complex logic - just executes scripts and passes variables.

Usage: python3 simple_script_worker.py
"""

import asyncio
import subprocess
import json
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.external_task_worker import ExternalTaskWorker

class SimpleScriptWorker:
    """Simple worker that executes Python scripts for BPMN tasks."""
    
    def __init__(self):
        self.script_dir = Path(__file__).parent
        
    async def execute_script(self, task_type: str, variables: dict) -> dict:
        """Execute Python script based on task type."""
        try:
            # Map task types to script files
            script_map = {
                'extract-text': 'step_extract_text.py',
                'chunk-document': 'step_chunk_document.py', 
                'generate-embeddings': 'step_generate_embeddings.py',
                'create-knowledge-asset': 'step_create_knowledge_asset.py',
                'store-vector-chunks': 'step_store_vector_chunks.py'
            }
            
            script_name = script_map.get(task_type)
            if not script_name:
                raise ValueError(f"No script found for task type: {task_type}")
            
            script_path = self.script_dir / script_name
            if not script_path.exists():
                raise FileNotFoundError(f"Script not found: {script_path}")
            
            # Extract required parameters from variables
            file_id = variables.get('file_id', '')
            project_id = variables.get('project_id', '')
            
            # Build command arguments based on script type
            if task_type == 'extract-text':
                cmd = ['python3', str(script_path), file_id, project_id]
            elif task_type == 'chunk-document':
                chunking_strategy = variables.get('chunking_strategy', 'hybrid')
                chunk_size = variables.get('chunk_size', 512)
                cmd = ['python3', str(script_path), file_id, chunking_strategy, str(chunk_size)]
            elif task_type == 'generate-embeddings':
                embedding_model = variables.get('embedding_model', 'all-MiniLM-L6-v2')
                cmd = ['python3', str(script_path), file_id, embedding_model]
            elif task_type == 'create-knowledge-asset':
                document_type = variables.get('document_type', 'text')
                cmd = ['python3', str(script_path), file_id, project_id, document_type]
            elif task_type == 'store-vector-chunks':
                knowledge_asset_id = variables.get('knowledge_asset_id', 'auto')
                cmd = ['python3', str(script_path), file_id, knowledge_asset_id]
            else:
                cmd = ['python3', str(script_path), file_id, project_id]
            
            print(f"🔧 Executing: {' '.join(cmd)}")
            
            # Execute the script
            result = subprocess.run(
                cmd,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                print(f"✅ Script executed successfully")
                print(f"📤 Output: {result.stdout}")
                
                # Try to parse JSON result from script output
                script_result = {}
                for line in result.stdout.split('\n'):
                    if line.startswith('📋 BPMN_RESULT:'):
                        try:
                            json_str = line.replace('📋 BPMN_RESULT:', '').strip()
                            script_result = json.loads(json_str)
                            break
                        except json.JSONDecodeError:
                            pass
                
                return {
                    'success': True,
                    'result': script_result,
                    'stdout': result.stdout,
                    'task_type': task_type
                }
            else:
                print(f"❌ Script failed with exit code: {result.returncode}")
                print(f"📤 Error: {result.stderr}")
                
                return {
                    'success': False,
                    'error': result.stderr,
                    'stdout': result.stdout,
                    'exit_code': result.returncode,
                    'task_type': task_type
                }
                
        except Exception as e:
            print(f"❌ Script execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'task_type': task_type
            }

async def main():
    """Main worker function."""
    print("🔄 Starting Simple Script Worker for BPMN Orchestration")
    
    from backend.services.config import Settings
    settings = Settings()
    
    worker = ExternalTaskWorker(settings)
    
    script_worker = SimpleScriptWorker()
    
    # Subscribe to all our task types
    task_types = [
        'extract-text',
        'chunk-document', 
        'generate-embeddings',
        'create-knowledge-asset',
        'store-vector-chunks'
    ]
    
    for task_type in task_types:
        await worker.subscribe_to_topic(
            topic=task_type,
            handler=lambda variables, task_type=task_type: script_worker.execute_script(task_type, variables)
        )
    
    print(f"📋 Subscribed to topics: {', '.join(task_types)}")
    print("✅ Worker ready - waiting for BPMN tasks...")
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        print("🛑 Worker stopped by user")
    except Exception as e:
        print(f"❌ Worker error: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
