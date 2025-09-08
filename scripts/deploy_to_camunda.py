#!/usr/bin/env python3
"""
Deploy ODRAS BPMN process to Camunda 7 and start a process instance.
"""

import requests
import json
import time
from pathlib import Path

# Camunda configuration
CAMUNDA_BASE_URL = "http://localhost:8080"
CAMUNDA_REST_API = f"{CAMUNDA_BASE_URL}/engine-rest"


def deploy_bpmn_to_camunda():
    """Deploy the BPMN file to Camunda."""

    # Path to the BPMN file
    bpmn_file = Path(__file__).parent.parent / "bpmn" / "odras_requirements_analysis.bpmn"

    if not bpmn_file.exists():
        print(f"BPMN file not found: {bpmn_file}")
        return None

    # Read BPMN content
    with open(bpmn_file, "rb") as f:
        bpmn_content = f.read()

    # Deploy to Camunda
    deploy_url = f"{CAMUNDA_REST_API}/deployment/create"

    files = {"file": ("odras_requirements_analysis.bpmn", bpmn_content, "application/xml")}

    data = {
        "deployment-name": "odras-requirements-analysis",
        "enable-duplicate-filtering": "true",
    }

    try:
        response = requests.post(deploy_url, files=files, data=data)
        response.raise_for_status()

        deployment_info = response.json()
        print(f"✅ BPMN deployed successfully!")
        print(f"   Deployment ID: {deployment_info['id']}")
        print(f"   Name: {deployment_info['name']}")
        print(f"   Source: {deployment_info['source']}")

        return deployment_info["id"]

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to deploy BPMN: {e}")
        return None


def start_process_instance(
    deployment_id: str,
    document_content: str,
    document_filename: str,
    llm_provider: str = "openai",
    llm_model: str = "gpt-4o-mini",
    iterations: int = 10,
):
    """Start a new process instance with the given parameters."""

    start_url = f"{CAMUNDA_REST_API}/process-definition/key/odras_requirements_analysis/start"

    variables = {
        "document_content": {"value": document_content, "type": "String"},
        "document_filename": {"value": document_filename, "type": "String"},
        "llm_provider": {"value": llm_provider, "type": "String"},
        "llm_model": {"value": llm_model, "type": "String"},
        "iterations": {"value": iterations, "type": "Integer"},
    }

    payload = {"variables": variables}

    try:
        response = requests.post(start_url, json=payload)
        response.raise_for_status()

        process_info = response.json()
        print(f"✅ Process instance started successfully!")
        print(f"   Process Instance ID: {process_info['id']}")
        print(f"   Process Definition ID: {process_info['definitionId']}")

        return process_info["id"]

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to start process instance: {e}")
        return None


def get_process_status(process_instance_id: str):
    """Get the current status of a process instance."""

    status_url = f"{CAMUNDA_REST_API}/process-instance/{process_instance_id}"

    try:
        response = requests.get(status_url)
        response.raise_for_status()

        status_info = response.json()
        return status_info

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to get process status: {e}")
        return None


def get_process_variables(process_instance_id: str):
    """Get the variables of a process instance."""

    variables_url = f"{CAMUNDA_REST_API}/process-instance/{process_instance_id}/variables"

    try:
        response = requests.get(variables_url)
        response.raise_for_status()

        variables = response.json()
        return variables

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to get process variables: {e}")
        return None


def main():
    """Main deployment and testing function."""

    print("🚀 Deploying ODRAS BPMN process to Camunda...")

    # Check if Camunda is running
    try:
        health_response = requests.get(f"{CAMUNDA_BASE_URL}/actuator/health")
        if health_response.status_code != 200:
            print("❌ Camunda is not running. Please start Camunda first.")
            print("   docker compose up -d camunda7")
            return
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to Camunda. Please start Camunda first.")
        print("   docker compose up -d camunda7")
        return

    print("✅ Camunda is running!")

    # Deploy BPMN
    deployment_id = deploy_bpmn_to_camunda()
    if not deployment_id:
        return

    # Wait a moment for deployment to complete
    time.sleep(2)

    # Test with a sample document
    sample_document = """
    The system shall provide user authentication.
    The system must respond within 100ms.
    The component shall interface with external APIs.
    The function will process data efficiently.
    The subsystem should be capable of handling 1000 concurrent users.
    """

    print("\n🧪 Starting test process instance...")

    process_id = start_process_instance(
        deployment_id=deployment_id,
        document_content=sample_document,
        document_filename="sample_requirements.txt",
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        iterations=3,
    )

    if not process_id:
        return

    # Monitor the process
    print(f"\n📊 Monitoring process instance {process_id}...")

    for i in range(10):  # Check status for up to 10 iterations
        time.sleep(2)

        status = get_process_status(process_id)
        if not status:
            continue

        print(f"   Status check {i+1}: {status.get('state', 'unknown')}")

        # Check if process is completed
        if status.get("state") == "completed":
            print("✅ Process completed!")

            # Get final variables
            variables = get_process_variables(process_id)
            if variables:
                print("\n📋 Final process variables:")
                for var_name, var_info in variables.items():
                    if var_name in [
                        "requirements_list",
                        "extraction_metadata",
                        "llm_results",
                    ]:
                        try:
                            value = json.loads(var_info["value"])
                            print(f"   {var_name}: {json.dumps(value, indent=2)}")
                        except:
                            print(f"   {var_name}: {var_info['value']}")
                    else:
                        print(f"   {var_name}: {var_info['value']}")
            break

    print(f"\n🎯 Process monitoring complete!")
    print(f"   View in Camunda Cockpit: {CAMUNDA_BASE_URL}")
    print(f"   Process Instance ID: {process_id}")


if __name__ == "__main__":
    main()
