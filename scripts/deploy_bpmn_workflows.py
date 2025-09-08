#!/usr/bin/env python3
"""
BPMN Workflow Deployment Script
Deploy new RAG Pipeline and Add to Knowledge workflows to Camunda.
"""

import requests
import json
import sys
import os
from pathlib import Path


def deploy_bpmn_workflow(
    camunda_url: str, bpmn_file_path: str, deployment_name: str
) -> bool:
    """
    Deploy a BPMN workflow to Camunda.

    Args:
        camunda_url: Base URL of Camunda engine
        bpmn_file_path: Path to the BPMN file
        deployment_name: Name for the deployment

    Returns:
        True if deployment successful, False otherwise
    """
    try:
        # Check if file exists
        if not os.path.exists(bpmn_file_path):
            print(f"❌ BPMN file not found: {bpmn_file_path}")
            return False

        # Prepare deployment request
        deployment_url = f"{camunda_url}/deployment/create"

        with open(bpmn_file_path, "rb") as bpmn_file:
            files = {
                "deployment-name": (None, deployment_name),
                "enable-duplicate-filtering": (None, "false"),
                "deploy-changed-only": (None, "true"),
                "deployment-source": (None, "ODRAS BPMN Integration"),
                os.path.basename(bpmn_file_path): (
                    os.path.basename(bpmn_file_path),
                    bpmn_file,
                    "application/xml",
                ),
            }

            print(f"🚀 Deploying {deployment_name}...")
            response = requests.post(deployment_url, files=files, timeout=30)

            if response.status_code == 200:
                result = response.json()
                deployment_id = result.get("id")
                deployed_processes = result.get("deployedProcessDefinitions", {})

                print(f"✅ Successfully deployed {deployment_name}")
                print(f"   Deployment ID: {deployment_id}")

                for process_key, process_info in deployed_processes.items():
                    print(
                        f"   Process: {process_info.get('key')} (v{process_info.get('version')})"
                    )

                return True
            else:
                print(f"❌ Failed to deploy {deployment_name}: {response.status_code}")
                print(f"   Error: {response.text}")
                return False

    except Exception as e:
        print(f"❌ Exception during deployment of {deployment_name}: {str(e)}")
        return False


def test_workflow_deployment(camunda_url: str, process_key: str) -> bool:
    """
    Test if a workflow is properly deployed by checking process definitions.

    Args:
        camunda_url: Base URL of Camunda engine
        process_key: Process definition key to check

    Returns:
        True if process is found, False otherwise
    """
    try:
        # Get process definitions
        process_url = f"{camunda_url}/process-definition"
        params = {"key": process_key, "latestVersion": "true"}

        response = requests.get(process_url, params=params, timeout=10)

        if response.status_code == 200:
            definitions = response.json()
            if definitions:
                definition = definitions[0]
                print(f"✅ Process {process_key} is deployed")
                print(f"   Version: {definition.get('version')}")
                print(f"   ID: {definition.get('id')}")
                return True
            else:
                print(f"❌ Process {process_key} not found")
                return False
        else:
            print(f"❌ Failed to check process {process_key}: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Exception checking process {process_key}: {str(e)}")
        return False


def start_test_process(
    camunda_url: str, process_key: str, variables: dict = None
) -> bool:
    """
    Start a test process instance to verify deployment.

    Args:
        camunda_url: Base URL of Camunda engine
        process_key: Process definition key
        variables: Process variables to pass

    Returns:
        True if process started successfully, False otherwise
    """
    try:
        start_url = f"{camunda_url}/process-definition/key/{process_key}/start"

        payload = {"variables": {}}

        if variables:
            for key, value in variables.items():
                payload["variables"][key] = {
                    "value": value,
                    "type": "String" if isinstance(value, str) else "Object",
                }

        print(f"🧪 Starting test instance of {process_key}...")
        response = requests.post(start_url, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            instance_id = result.get("id")
            print(f"✅ Test instance started successfully")
            print(f"   Instance ID: {instance_id}")
            print(f"   Process Key: {result.get('processDefinitionKey')}")
            return True
        else:
            print(f"❌ Failed to start test instance: {response.status_code}")
            print(f"   Error: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Exception starting test instance: {str(e)}")
        return False


def main():
    """Main deployment function."""
    # Configuration
    camunda_url = "http://localhost:8080/engine-rest"
    bpmn_dir = Path(__file__).parent.parent / "bpmn"

    # Workflows to deploy
    workflows = [
        {
            "file": "rag_pipeline.bpmn",
            "name": "RAG Pipeline Process",
            "process_key": "rag_pipeline_process",
        },
        {
            "file": "add_to_knowledge.bpmn",
            "name": "Add to Knowledge Process",
            "process_key": "add_to_knowledge_process",
        },
    ]

    print("🔄 ODRAS BPMN Workflow Deployment")
    print("=" * 50)

    # Check Camunda connection
    try:
        response = requests.get(f"{camunda_url}/engine", timeout=5)
        if response.status_code != 200:
            print(f"❌ Cannot connect to Camunda at {camunda_url}")
            print("   Make sure Camunda is running with: docker compose up -d")
            sys.exit(1)
        print(f"✅ Connected to Camunda at {camunda_url}")
    except Exception as e:
        print(f"❌ Cannot connect to Camunda: {str(e)}")
        print("   Make sure Camunda is running with: docker compose up -d")
        sys.exit(1)

    # Deploy each workflow
    deployment_results = []
    for workflow in workflows:
        bpmn_file_path = bpmn_dir / workflow["file"]
        success = deploy_bpmn_workflow(
            camunda_url, str(bpmn_file_path), workflow["name"]
        )
        deployment_results.append((workflow, success))
        print()

    # Test deployments
    print("🧪 Testing Workflow Deployments")
    print("-" * 30)

    for workflow, deployed in deployment_results:
        if deployed:
            test_workflow_deployment(camunda_url, workflow["process_key"])
        print()

    # Summary
    print("📊 Deployment Summary")
    print("-" * 20)
    successful = sum(1 for _, success in deployment_results if success)
    total = len(deployment_results)

    for workflow, success in deployment_results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"   {workflow['name']}: {status}")

    print(f"\n🎯 {successful}/{total} workflows deployed successfully")

    if successful == total:
        print("\n🚀 All workflows deployed! You can now:")
        print("   1. View processes in Camunda Cockpit: http://localhost:8080")
        print("   2. Start process instances via REST API or UI")
        print("   3. Monitor execution in real-time")
        return True
    else:
        print(f"\n⚠️  Some deployments failed. Check the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
