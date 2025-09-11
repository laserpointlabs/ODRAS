#!/usr/bin/env python3
"""
Simple External Task Worker for Script Execution

This worker polls Camunda for external tasks and executes corresponding Python scripts.
Much simpler than the existing complex ExternalTaskWorker.
"""

import asyncio
import subprocess
import json
import sys
import time
import requests
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class SimpleExternalWorker:
    """Simple external task worker that just executes scripts."""

    def __init__(self, camunda_url: str = "http://localhost:8080/engine-rest"):
        self.camunda_url = camunda_url
        self.worker_id = f"simple-script-worker-{int(time.time())}"
        self.script_dir = Path(__file__).parent
        self.running = False

        # Map task topics to script files
        self.script_map = {
            "extract-text": "step_extract_text.py",
            "chunk-document": "step_chunk_document.py",
            "generate-embeddings": "step_generate_embeddings.py",
            "create-knowledge-asset": "step_create_knowledge_asset.py",
            "store-vector-chunks": "step_store_vector_chunks.py",
            "activate-knowledge-asset": "step_activate_knowledge_asset.py",
        }

        print(f"🔧 Simple External Worker initialized: {self.worker_id}")
        print(f"📋 Script mappings: {self.script_map}")

    def fetch_and_lock_tasks(self, topic: str) -> list:
        """Fetch and lock external tasks for a topic."""
        try:
            url = f"{self.camunda_url}/external-task/fetchAndLock"
            payload = {
                "workerId": self.worker_id,
                "maxTasks": 1,
                "topics": [
                    {
                        "topicName": topic,
                        "lockDuration": 30000,  # 30 seconds
                        "variables": [
                            "file_id",
                            "project_id",
                            "filename",
                            "document_type",
                            "embedding_model",
                            "chunking_strategy",
                            "chunk_size",
                            "knowledge_asset_id",
                        ],
                    }
                ],
            }

            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️ Failed to fetch tasks for {topic}: {response.status_code}")
                return []

        except Exception as e:
            print(f"❌ Error fetching tasks for {topic}: {str(e)}")
            return []

    def complete_task(self, task_id: str, variables: dict):
        """Complete an external task."""
        try:
            url = f"{self.camunda_url}/external-task/{task_id}/complete"
            payload = {"workerId": self.worker_id, "variables": variables}

            print(f"🔧 Completing task {task_id} with payload:")
            print(f"   {json.dumps(payload, indent=2)}")

            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 204:
                print(f"✅ Task {task_id} completed successfully")
                return True
            else:
                print(f"❌ Failed to complete task {task_id}: {response.status_code}")
                print(f"   Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error completing task {task_id}: {str(e)}")
            return False

    def handle_task_failure(self, task_id: str, error_message: str):
        """Handle task failure."""
        try:
            url = f"{self.camunda_url}/external-task/{task_id}/failure"
            payload = {
                "workerId": self.worker_id,
                "errorMessage": error_message,
                "retries": 0,  # No retries for now
            }

            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 204:
                print(f"❌ Task {task_id} marked as failed")
                return True
            else:
                print(f"❌ Failed to report task failure {task_id}: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Error reporting task failure {task_id}: {str(e)}")
            return False

    def execute_script(self, topic: str, task_variables: dict) -> tuple:
        """Execute the script for a given topic."""
        try:
            script_name = self.script_map.get(topic)
            if not script_name:
                raise ValueError(f"No script found for topic: {topic}")

            script_path = self.script_dir / script_name
            if not script_path.exists():
                raise FileNotFoundError(f"Script not found: {script_path}")

            # Extract variables from Camunda task
            variables = {}
            for key, var_data in task_variables.items():
                variables[key] = var_data.get("value", "")

            file_id = variables.get("file_id", "")
            project_id = variables.get("project_id", "")

            # Build command based on topic
            if topic == "extract-text":
                cmd = ["python3", str(script_path), file_id, project_id]
            elif topic == "chunk-document":
                chunking_strategy = variables.get("chunking_strategy", "hybrid")
                chunk_size = variables.get("chunk_size", 512)
                cmd = [
                    "python3",
                    str(script_path),
                    file_id,
                    chunking_strategy,
                    str(chunk_size),
                ]
            elif topic == "generate-embeddings":
                embedding_model = variables.get("embedding_model", "all-MiniLM-L6-v2")
                cmd = ["python3", str(script_path), file_id, embedding_model]
            elif topic == "create-knowledge-asset":
                document_type = variables.get("document_type", "text")
                filename = variables.get("filename", "unknown_file")
                cmd = [
                    "python3",
                    str(script_path),
                    file_id,
                    project_id,
                    document_type,
                    filename,
                ]
            elif topic == "store-vector-chunks":
                knowledge_asset_id = variables.get("knowledge_asset_id", "auto")
                cmd = ["python3", str(script_path), file_id, knowledge_asset_id]
            elif topic == "activate-knowledge-asset":
                knowledge_asset_id = variables.get("knowledge_asset_id", "auto")
                cmd = ["python3", str(script_path), knowledge_asset_id]
            else:
                cmd = ["python3", str(script_path), file_id, project_id]

            print(f"🔧 Executing: {' '.join(cmd)}")

            # Execute the script
            result = subprocess.run(
                cmd,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes
            )

            if result.returncode == 0:
                print(f"✅ Script executed successfully")

                # Parse script result
                script_result = {}
                for line in result.stdout.split("\n"):
                    if line.startswith("📋 BPMN_RESULT:"):
                        try:
                            json_str = line.replace("📋 BPMN_RESULT:", "").strip()
                            script_result = json.loads(json_str)
                            break
                        except json.JSONDecodeError:
                            pass

                # Convert script result to Camunda variables (flatten complex objects)
                camunda_vars = {}
                for key, value in script_result.items():
                    if isinstance(value, dict) or isinstance(value, list):
                        # Serialize complex objects as JSON strings
                        camunda_vars[key] = {
                            "value": json.dumps(value),
                            "type": "String",
                        }
                    elif isinstance(value, bool):
                        camunda_vars[key] = {"value": value, "type": "Boolean"}
                    elif isinstance(value, int):
                        camunda_vars[key] = {"value": value, "type": "Integer"}
                    else:
                        # Default to string
                        camunda_vars[key] = {"value": str(value), "type": "String"}

                return True, camunda_vars
            else:
                error_msg = f"Script failed: {result.stderr}"
                print(f"❌ {error_msg}")
                return False, error_msg

        except Exception as e:
            error_msg = f"Script execution error: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    async def run(self):
        """Main worker loop."""
        print("🚀 Starting simple external worker...")
        self.running = True

        topics = list(self.script_map.keys())
        print(f"📋 Monitoring topics: {topics}")

        while self.running:
            try:
                # Poll each topic for tasks
                for topic in topics:
                    tasks = self.fetch_and_lock_tasks(topic)

                    for task in tasks:
                        task_id = task["id"]
                        print(f"🔄 Processing task {task_id} for topic '{topic}'")

                        # Execute the script
                        success, result = self.execute_script(topic, task.get("variables", {}))

                        if success:
                            # Complete the task with results
                            self.complete_task(task_id, result)
                        else:
                            # Report failure
                            self.handle_task_failure(task_id, str(result))

                # Wait before next poll
                await asyncio.sleep(2)  # Poll every 2 seconds

            except KeyboardInterrupt:
                print("🛑 Worker stopped by user")
                break
            except Exception as e:
                print(f"❌ Worker error: {str(e)}")
                await asyncio.sleep(5)  # Wait longer on error

        self.running = False


async def main():
    """Main function."""
    worker = SimpleExternalWorker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
