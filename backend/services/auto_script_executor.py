"""
Auto Script Executor for BPMN Integration

Automatically executes Python scripts when BPMN processes are started.
No manual worker management required - scripts run automatically.
"""

import subprocess
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from .config import Settings

logger = logging.getLogger(__name__)

class AutoScriptExecutor:
    """Automatically execute BPMN workflow scripts without manual workers."""
    
    def __init__(self, settings: Settings = None):
        self.settings = settings or Settings()
        self.script_dir = Path(__file__).parent.parent.parent / "scripts"
        self.project_root = Path(__file__).parent.parent.parent
        
    async def execute_complete_workflow(self, file_id: str, project_id: str, processing_options: Dict[str, Any]) -> str:
        """Execute the complete knowledge processing workflow using individual scripts."""
        try:
            logger.info(f"🔄 Auto-executing knowledge processing workflow for file {file_id}")
            
            # Step 1: Extract text
            step1_result = await self._run_script("step_extract_text.py", [file_id, project_id])
            if not step1_result.get('success'):
                raise ValueError(f"Text extraction failed: {step1_result.get('error')}")
            
            # Step 2: Chunk document  
            chunking_strategy = processing_options.get('chunking_strategy', 'hybrid')
            chunk_size = str(processing_options.get('chunk_size', 512))
            step2_result = await self._run_script("step_chunk_document.py", [file_id, chunking_strategy, chunk_size])
            if not step2_result.get('success'):
                raise ValueError(f"Document chunking failed: {step2_result.get('error')}")
            
            # Step 3: Generate embeddings
            embedding_model = processing_options.get('embedding_model', 'all-MiniLM-L6-v2')
            step3_result = await self._run_script("step_generate_embeddings.py", [file_id, embedding_model])
            if not step3_result.get('success'):
                raise ValueError(f"Embedding generation failed: {step3_result.get('error')}")
            
            # Step 4: Create knowledge asset
            document_type = processing_options.get('document_type', 'text')
            step4_result = await self._run_script("step_create_knowledge_asset.py", [file_id, project_id, document_type])
            if not step4_result.get('success'):
                raise ValueError(f"Knowledge asset creation failed: {step4_result.get('error')}")
            
            knowledge_asset_id = step4_result.get('knowledge_asset_id')
            if not knowledge_asset_id:
                raise ValueError("No knowledge asset ID returned")
            
            # Step 5: Store vector chunks
            step5_result = await self._run_script("step_store_vector_chunks.py", [file_id, knowledge_asset_id])
            if not step5_result.get('success'):
                raise ValueError(f"Vector storage failed: {step5_result.get('error')}")
            
            logger.info(f"✅ Complete workflow executed successfully: Knowledge asset {knowledge_asset_id}")
            return knowledge_asset_id
            
        except Exception as e:
            logger.error(f"❌ Auto script execution failed: {str(e)}")
            raise
    
    async def _run_script(self, script_name: str, args: list) -> Dict[str, Any]:
        """Run a single script and return parsed result."""
        try:
            script_path = self.script_dir / script_name
            if not script_path.exists():
                raise FileNotFoundError(f"Script not found: {script_path}")
            
            cmd = ["python3", str(script_path)] + [str(arg) for arg in args]
            
            logger.info(f"🔧 Executing: {' '.join(cmd)}")
            
            # Execute script with proper async subprocess (non-blocking)
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.project_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for completion with reasonable timeout
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
                result_returncode = process.returncode
                result_stdout = stdout.decode('utf-8') if stdout else ""
                result_stderr = stderr.decode('utf-8') if stderr else ""
            except asyncio.TimeoutError:
                process.kill()
                raise TimeoutError(f"Script {script_name} timed out after 60 seconds")
            
            if result_returncode == 0:
                # Parse BPMN_RESULT from output
                for line in result_stdout.split('\n'):
                    if line.startswith('📋 BPMN_RESULT:'):
                        try:
                            json_str = line.replace('📋 BPMN_RESULT:', '').strip()
                            return json.loads(json_str)
                        except json.JSONDecodeError:
                            pass
                
                # Fallback if no BPMN_RESULT found
                return {"success": True, "stdout": result_stdout}
            else:
                return {"success": False, "error": result_stderr, "stdout": result_stdout}
                
        except Exception as e:
            return {"success": False, "error": str(e)}

# Global instance
_auto_executor = None

def get_auto_script_executor(settings: Settings = None) -> AutoScriptExecutor:
    """Get the global auto script executor instance."""
    global _auto_executor
    if _auto_executor is None:
        _auto_executor = AutoScriptExecutor(settings)
    return _auto_executor
