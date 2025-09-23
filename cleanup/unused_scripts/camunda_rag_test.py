#!/usr/bin/env python3
"""
Camunda RAG Test - Direct Camunda REST API queries for process data
No timing circuits - just query Camunda for stored results
"""

import json
import time
import requests
import sys
import subprocess
from pathlib import Path


def start_external_task_worker():
    """Start external task worker if not running."""
    # Kill any existing workers first
    try:
        subprocess.run(["pkill", "-f", "external_task_worker"], capture_output=True)
        time.sleep(2)
    except:
        pass

    print("🔄 Starting external task worker...")
    worker_script = Path(__file__).parent / "run_external_task_worker.py"

    worker_process = subprocess.Popen(
        [sys.executable, str(worker_script)],
        cwd=Path(__file__).parent.parent,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Give it time to start
    time.sleep(3)

    if worker_process.poll() is None:
        print(f"✅ External task worker started (PID: {worker_process.pid})")
        return worker_process
    else:
        print("❌ Failed to start external task worker")
        return None


def get_camunda_process_data(process_id: str) -> dict:
    """Get all data for a process from Camunda."""
    try:
        # Get process instance info
        process_response = requests.get(
            f"http://localhost:8080/engine-rest/process-instance/{process_id}",
            timeout=10,
        )

        # Get process variables
        variables_response = requests.get(
            f"http://localhost:8080/engine-rest/process-instance/{process_id}/variables",
            timeout=10,
        )

        # Get process history if current call fails
        history_response = None
        if process_response.status_code == 404:
            print("   Process not in active instances, checking history...")
            history_response = requests.get(
                f"http://localhost:8080/engine-rest/history/process-instance/{process_id}",
                timeout=10,
            )

        result = {
            "process_id": process_id,
            "found": False,
            "completed": False,
            "variables": {},
            "error": None,
        }

        # Parse process status
        if process_response.status_code == 200:
            process_data = process_response.json()
            result["found"] = True
            result["completed"] = process_data.get("ended", False)
            result["suspended"] = process_data.get("suspended", False)
        elif history_response and history_response.status_code == 200:
            history_data = history_response.json()
            result["found"] = True
            result["completed"] = history_data.get("endTime") is not None
            result["from_history"] = True
        else:
            result["error"] = f"Process not found (status: {process_response.status_code})"
            return result

        # Parse variables
        if variables_response.status_code == 200:
            variables_data = variables_response.json()
            result["variables"] = variables_data
        else:
            # Try historic variables
            try:
                hist_vars_response = requests.get(
                    f"http://localhost:8080/engine-rest/history/variable-instance?processInstanceId={process_id}",
                    timeout=10,
                )
                if hist_vars_response.status_code == 200:
                    hist_vars = hist_vars_response.json()
                    # Convert to current format
                    variables_dict = {}
                    for var in hist_vars:
                        variables_dict[var["name"]] = {
                            "value": var.get("value"),
                            "type": var.get("type", "String"),
                        }
                    result["variables"] = variables_dict
                    result["from_history"] = True
            except:
                result["error"] = (
                    f"Could not get variables (status: {variables_response.status_code})"
                )

        return result

    except Exception as e:
        return {
            "process_id": process_id,
            "found": False,
            "error": f"Exception: {str(e)}",
        }


def start_rag_query(query: str) -> str:
    """Start RAG query and return process ID."""
    try:
        print(f"🚀 Starting RAG query: '{query}'")

        response = requests.post(
            "http://localhost:8000/api/workflows/rag-query",
            json={"query": query, "max_results": 5, "similarity_threshold": 0.3},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        if response.status_code == 200:
            result = response.json()
            process_id = result.get("process_instance_id")
            print(f"✅ Query started with process ID: {process_id}")
            return process_id
        else:
            print(f"❌ Failed to start query: {response.status_code}")
            print(f"   Error: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error starting query: {str(e)}")
        return None


def extract_results(process_data: dict):
    """Extract and display results from process data."""
    variables = process_data.get("variables", {})

    print(f"📊 Process Results:")
    print(f"   Found: {process_data.get('found')}")
    print(f"   Completed: {process_data.get('completed')}")

    if process_data.get("error"):
        print(f"   Error: {process_data['error']}")
        return False

    # Show key variables
    key_vars = [
        "user_query",
        "final_response",
        "retrieval_stats",
        "context_quality_score",
        "reranked_context",
    ]

    for var_name in key_vars:
        if var_name in variables:
            value = variables[var_name].get("value")
            if var_name == "final_response" and value:
                print(f"\n💬 Final Response:")
                print(f"   {value}")

                # Check for real data
                if "3 meters CEP" in value:
                    print(f"\n🎯 CONFIRMED: Real position accuracy data found!")
                    return True
                elif "Navigation System" in value:
                    print(f"\n🎯 CONFIRMED: Real navigation system data found!")
                    return True

            elif var_name == "reranked_context" and value:
                try:
                    context_data = json.loads(value) if isinstance(value, str) else value
                    if context_data:
                        print(f"\n📚 Retrieved Context:")
                        for i, chunk in enumerate(context_data[:3], 1):
                            source = chunk.get("source_document", "Unknown")
                            score = chunk.get("similarity_score", 0)
                            content = chunk.get("content", "")[:100]
                            print(f"   {i}. {source} (score: {score:.3f})")
                            print(f"      Content: {content}...")
                except:
                    pass

            elif var_name == "context_quality_score" and value:
                print(f"   Context Quality: {value}")

    return variables.get("final_response", {}).get("value") is not None


def test_rag_complete(query: str):
    """Complete RAG test using Camunda REST API."""
    print(f"🧪 ODRAS RAG Test via Camunda API")
    print(f"Query: '{query}'")
    print("=" * 50)

    # Start worker
    worker = start_external_task_worker()
    if not worker:
        return False

    try:
        # Start query
        process_id = start_rag_query(query)
        if not process_id:
            return False

        # Poll Camunda until process completes
        print(f"⏳ Monitoring process completion...")

        max_checks = 60  # Maximum 60 checks (60 seconds)
        check_count = 0

        while check_count < max_checks:
            time.sleep(1)
            check_count += 1

            try:
                # Check if process is complete
                status_response = requests.get(
                    f"http://localhost:8080/engine-rest/process-instance/{process_id}",
                    timeout=5,
                )

                if status_response.status_code == 200:
                    # Process still active, check if ended
                    process_info = status_response.json()
                    if process_info.get("ended"):
                        print(f"   ✅ Process completed after {check_count} seconds!")
                        break
                    else:
                        if check_count % 5 == 0:  # Show progress every 5 seconds
                            print(f"   🔄 Still processing... ({check_count}s)")

                elif status_response.status_code == 404:
                    # Process completed and cleaned up
                    print(f"   ✅ Process completed and cleaned up after {check_count} seconds!")
                    break
                else:
                    print(f"   ⚠️  Unexpected status: {status_response.status_code}")

            except Exception as e:
                if check_count % 10 == 0:  # Don't spam errors
                    print(f"   ⚠️  Check error: {str(e)}")

        else:
            print(f"   ⏰ Process did not complete within {max_checks} seconds")
            return False

        # Now get results from Camunda
        print(f"🔍 Retrieving results from Camunda...")
        process_data = get_camunda_process_data(process_id)

        if not process_data.get("found"):
            print(f"❌ Process not found in Camunda: {process_data.get('error', 'Unknown error')}")
            return False

        # Extract and show results
        success = extract_results(process_data)

        if success:
            print(f"\n🎉 RAG query completed successfully with real data!")
        else:
            print(f"\n⚠️  Process completed but results need verification")

        return success

    finally:
        # Stop worker
        try:
            worker.terminate()
            worker.wait(timeout=5)
            print(f"\n🛑 External task worker stopped")
        except:
            try:
                worker.kill()
            except:
                pass


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "What is the required position accuracy?"
    success = test_rag_complete(query)

    if not success:
        print(f"\n❌ Test did not complete successfully")
        print(f"🔍 Debug: Check http://localhost:8080 for process details")

    sys.exit(0 if success else 1)

