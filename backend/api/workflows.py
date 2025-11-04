"""
Workflows API: Deploy and start BPMN processes by key.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from ..services.config import Settings
from ..services.auth import get_user
from backend.run_registry import RUNS  # shared run registry
from ..services.ingestion_worker import IngestionWorker


router = APIRouter(prefix="/api/workflows", tags=["workflows"])


class StartWorkflowRequest(BaseModel):
    processKey: str
    projectId: Optional[str] = None
    fileIds: Optional[List[str]] = None
    params: Optional[Dict[str, Any]] = None
    businessKey: Optional[str] = None


class StartWorkflowResponse(BaseModel):
    success: bool
    runId: Optional[str] = None
    processKey: Optional[str] = None
    camunda_url: Optional[str] = None
    error: Optional[str] = None


_PROCESS_KEY_TO_BPMN: Dict[str, str] = {
    "odras_requirements_analysis": "odras_requirements_analysis.bpmn",
    "ingestion_pipeline": "ingestion_pipeline.bpmn",
    "requirements_extraction": "requirements_extraction.bpmn",
    "knowledge_enrichment": "knowledge_enrichment.bpmn",
    "rag_playground_session": "rag_playground_session.bpmn",
    "document_ingestion_process": "document_ingestion_pipeline.bpmn",
    "rag_query_process": "rag_query_pipeline.bpmn",
    "add_to_knowledge_process": "add_to_knowledge.bpmn",
    "automatic_knowledge_processing": "automatic_knowledge_processing.bpmn",
}


async def _ensure_bpmn_deployed(process_key: str, settings: Settings) -> None:
    """Ensure a BPMN definition for the given key exists in Camunda; deploy if missing."""
    camunda_rest = f"{settings.camunda_base_url.rstrip('/')}/engine-rest"

    # Check if definition exists
    try:
        async with httpx.AsyncClient(timeout=60) as client:  # Increased timeout
            r = await client.get(f"{camunda_rest}/process-definition/key/{process_key}")
            if r.status_code == 200:
                return
    except Exception:
        # Fall through to deploy attempt
        pass

    # Deploy BPMN
    filename = _PROCESS_KEY_TO_BPMN.get(process_key)
    if not filename:
        raise HTTPException(status_code=400, detail=f"Unknown processKey: {process_key}")

    project_root = Path(__file__).resolve().parents[2]
    bpmn_path = project_root / "bpmn" / filename
    if not bpmn_path.exists():
        raise HTTPException(status_code=500, detail=f"BPMN file not found: {bpmn_path}")

    try:
        async with httpx.AsyncClient(timeout=120) as client:  # Much longer timeout
            with open(bpmn_path, "rb") as f:
                files = {"file": (filename, f, "application/xml")}
                data = {
                    "deployment-name": process_key,
                    "enable-duplicate-filtering": "true",
                }
                r = await client.post(f"{camunda_rest}/deployment/create", files=files, data=data)
                r.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to deploy BPMN: {str(e)}")


def _to_camunda_variables(
    body: StartWorkflowRequest, user: Dict[str, Any]
) -> Dict[str, Dict[str, Any]]:
    """Convert request body to Camunda variables map.
    Use simple String types for JSON payloads for portability in Camunda 7.
    """
    variables: Dict[str, Dict[str, Any]] = {}
    if body.projectId is not None:
        variables["projectId"] = {"value": body.projectId, "type": "String"}
    if body.fileIds is not None:
        variables["fileIds"] = {"value": json.dumps(body.fileIds), "type": "String"}
    if body.params is not None:
        variables["params"] = {"value": json.dumps(body.params), "type": "String"}
    if user and user.get("user_id"):
        variables["userId"] = {"value": user["user_id"], "type": "String"}
    if user and user.get("username"):
        variables["username"] = {"value": user["username"], "type": "String"}
    return variables


@router.post("/start", response_model=StartWorkflowResponse)
async def start_workflow(
    body: StartWorkflowRequest,
    user=Depends(get_user),
    authorization: Optional[str] = Header(None),
):
    """
    Start a BPMN workflow by `processKey`. Deploys definition if missing.
    """
    # Require auth for workflow starts
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    settings = Settings()
    await _ensure_bpmn_deployed(body.processKey, settings)

    camunda_rest = f"{settings.camunda_base_url.rstrip('/')}/engine-rest"
    variables = _to_camunda_variables(body, user or {})

    payload: Dict[str, Any] = {"variables": variables}
    if body.businessKey:
        payload["businessKey"] = body.businessKey

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{camunda_rest}/process-definition/key/{body.processKey}/start",
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
            pid = data.get("id")
            # Record in in-memory RUNS registry for UI Recent Runs (MVP)
            try:
                RUNS[str(pid)] = {
                    "status": "started",
                    "process_id": pid,
                    "processKey": body.processKey,
                    "filename": "",
                    "iterations": None,
                    "llm_provider": None,
                    "llm_model": None,
                    "camunda_url": f"{settings.camunda_base_url.rstrip('/')}/cockpit/default/#/process-instance/{pid}",
                    "project_id": body.projectId,
                    "user_id": (user or {}).get("user_id"),
                }
            except Exception:
                pass
            # Fire-and-forget background ingestion for ingestion_pipeline (MVP)
            try:
                if body.processKey == "ingestion_pipeline" and body.fileIds:
                    # Run in background without blocking response
                    async def _bg():
                        worker = IngestionWorker()
                        await worker.ingest_files(body.fileIds or [], body.params or {})

                    import asyncio

                    asyncio.create_task(_bg())
            except Exception:
                pass
            return StartWorkflowResponse(
                success=True,
                runId=pid,
                processKey=body.processKey,
                camunda_url=f"{settings.camunda_base_url.rstrip('/')}/cockpit/default/#/process-instance/{pid}",
            )
    except httpx.HTTPStatusError as he:
        detail = he.response.json() if he.response is not None else {"error": str(he)}
        raise HTTPException(status_code=500, detail=f"Camunda start error: {detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {str(e)}")


class RAGQueryRequest(BaseModel):
    query: str
    max_results: Optional[int] = 10
    similarity_threshold: Optional[float] = 0.6
    user_context: Optional[Dict[str, Any]] = None


class RAGQueryResponse(BaseModel):
    success: bool
    process_instance_id: Optional[str] = None
    query: Optional[str] = None
    camunda_url: Optional[str] = None
    error: Optional[str] = None


@router.post("/rag-query", response_model=RAGQueryResponse)
async def start_rag_query(
    body: RAGQueryRequest,
    authorization: Optional[str] = Header(None),
):
    """
    Start a RAG query process to answer a user question.
    This triggers the complete RAG pipeline: Query Processing → Context Retrieval → LLM Generation → Response.
    """
    # Simple auth bypass for testing - in production this would use proper auth
    user = {"user_id": "api_user", "username": "api_user"}

    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    settings = Settings()
    process_key = "rag_query_process"

    # Ensure the RAG query workflow is deployed
    await _ensure_bpmn_deployed(process_key, settings)

    # Prepare query metadata
    query_metadata = {
        "user_id": (user or {}).get("user_id", "anonymous"),
        "username": (user or {}).get("username", "anonymous"),
        "max_results": body.max_results,
        "similarity_threshold": body.similarity_threshold,
        "timestamp": time.time(),
    }

    if body.user_context:
        query_metadata.update(body.user_context)

    # Prepare Camunda variables
    variables = {
        "user_query": {"value": body.query, "type": "String"},
        "query_metadata": {"value": json.dumps(query_metadata), "type": "String"},
    }

    camunda_rest = f"{settings.camunda_base_url.rstrip('/')}/engine-rest"

    try:
        async with httpx.AsyncClient(timeout=120) as client:  # Longer timeout
            r = await client.post(
                f"{camunda_rest}/process-definition/key/{process_key}/start",
                json={"variables": variables},
            )
            r.raise_for_status()
            data = r.json()
            instance_id = data.get("id")

            # Record in run registry
            try:
                RUNS[str(instance_id)] = {
                    "status": "processing",
                    "process_id": instance_id,
                    "processKey": process_key,
                    "query": body.query,
                    "user_query": body.query,
                    "camunda_url": f"{settings.camunda_base_url.rstrip('/')}/cockpit/default/#/process-instance/{instance_id}",
                    "user_id": (user or {}).get("user_id"),
                    "start_time": time.time(),
                }
            except Exception:
                pass

            return RAGQueryResponse(
                success=True,
                process_instance_id=instance_id,
                query=body.query,
                camunda_url=f"{settings.camunda_base_url.rstrip('/')}/cockpit/default/#/process-instance/{instance_id}",
            )

    except httpx.HTTPStatusError as he:
        detail = he.response.json() if he.response is not None else {"error": str(he)}
        raise HTTPException(status_code=500, detail=f"Camunda start error: {detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start RAG query: {str(e)}")


@router.get("/rag-query/{process_instance_id}/status")
async def get_rag_query_status(
    process_instance_id: str,
    authorization: Optional[str] = Header(None),
):
    """
    Get the status and results of a RAG query process.
    """
    # Simple auth bypass for testing - in production this would use proper auth
    user = {"user_id": "api_user", "username": "api_user"}

    settings = Settings()
    camunda_rest = f"{settings.camunda_base_url.rstrip('/')}/engine-rest"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Try to get process instance status (active)
            r = await client.get(f"{camunda_rest}/process-instance/{process_instance_id}")

            if r.status_code == 404:
                # Process not found in active instances, try history
                r = await client.get(f"{camunda_rest}/history/process-instance/{process_instance_id}")
                if r.status_code == 404:
                    raise HTTPException(status_code=404, detail="Process instance not found")
                elif r.status_code != 200:
                    raise HTTPException(status_code=500, detail="Failed to get process status from history")
                process_data = r.json()
                is_ended = True  # If it's in history, it's completed
            elif r.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to get process status")
            else:
                process_data = r.json()
                is_ended = process_data.get("ended", False)

            # Get process variables
            if is_ended:
                # If process is completed, get variables from history
                var_response = await client.get(
                    f"{camunda_rest}/history/variable-instance?processInstanceId={process_instance_id}"
                )
                if var_response.status_code == 200:
                    # Convert history format to variables format
                    history_vars = var_response.json()
                    variables = {}
                    for var in history_vars:
                        var_name = var["name"]
                        var_value = var["value"]
                        var_type = var.get("type", "String")

                        # DEBUG: Show raw Camunda data for key variables
                        if var_name in ["sources", "chunks_found"]:
                            print(f"CAMUNDA RAW: {var_name} = {var_value} (type: {var_type})")

                        # Handle different Camunda variable types correctly
                        if var_type == "Json" and isinstance(var_value, str):
                            # JSON variables are stored as strings in history
                            try:
                                var_value = json.loads(var_value)
                                if var_name in ["sources", "chunks_found"]:
                                    print(f"CAMUNDA PARSED: {var_name} = {var_value}")
                            except Exception as e:
                                print(f"Failed to parse JSON variable {var_name}: {e}")
                                pass
                        elif isinstance(var_value, str) and var_value.startswith(('[', '{')):
                            # Try to parse JSON even if not marked as Json type
                            try:
                                var_value = json.loads(var_value)
                            except:
                                pass

                        variables[var_name] = {"value": var_value, "type": var_type}
                        print(f"WORKFLOWS: Extracted {var_name} = {type(var_value)} ({len(str(var_value))} chars)")
                else:
                    variables = {}
            else:
                # Process is still active, get variables normally
                var_response = await client.get(
                    f"{camunda_rest}/process-instance/{process_instance_id}/variables"
                )
                variables = var_response.json() if var_response.status_code == 200 else {}

            # Extract key results
            result = {
                "process_instance_id": process_instance_id,
                "status": "completed" if is_ended else "running",
                "process_ended": is_ended,
                "variables": {},
            }

            # Extract important variables with proper format handling
            important_vars = [
                "user_query",
                "final_response",
                "processed_query",
                "retrieval_stats",
                "context_quality_score",
                "sources",  # Add sources for metadata display
                "citations",  # Add citations
                "retrieved_chunks",  # Add retrieved chunks for counting
                "reranked_context",  # Add reranked context
                "confidence",  # Add LLM confidence
                "llm_confidence",  # Add specific LLM confidence
                "chunks_found",  # Add chunks count
            ]
            for var_name in important_vars:
                if var_name in variables:
                    var_data = variables[var_name]
                    # Handle both active process format and history format
                    if isinstance(var_data, dict) and "value" in var_data:
                        var_value = var_data.get("value")
                    else:
                        var_value = var_data  # Direct value
                    result["variables"][var_name] = var_value

            # If process completed, get the final response
            if is_ended and "final_response" in variables:
                result["final_response"] = variables["final_response"].get("value")
                result["query"] = variables.get("user_query", {}).get("value", "")

            # Debug what we're returning
            print(f"WORKFLOWS RETURN: variables keys = {list(result['variables'].keys())}")
            if "chunks_found" in result["variables"]:
                print(f"WORKFLOWS RETURN: chunks_found = {result['variables']['chunks_found']}")
            if "sources" in result["variables"]:
                sources_data = result["variables"]["sources"]
                if isinstance(sources_data, list):
                    print(f"WORKFLOWS RETURN: sources = list with {len(sources_data)} items")
                else:
                    print(f"WORKFLOWS RETURN: sources = {type(sources_data)}")

            return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get RAG query status: {str(e)}")


@router.get("/user-tasks/{process_instance_id}/status")
async def get_user_task_status(process_instance_id: str, user=Depends(get_user)):
    """Get status of a user task in a BPMN workflow"""
    settings = Settings()
    camunda_rest = f"{settings.camunda_base_url.rstrip('/')}/engine-rest"
    
    try:
        instance_url = f"{camunda_rest}/process-instance/{process_instance_id}"
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(instance_url)
            response.raise_for_status()
            instance = response.json()

            # Get current activities
            activities_url = (
                f"{camunda_rest}/process-instance/{process_instance_id}/activity-instances"
            )
            activities_response = await client.get(activities_url)
            activities_response.raise_for_status()
            activities = activities_response.json()

            # Determine current state
            current_state = "unknown"
            if activities.get("childActivityInstances"):
                for activity in activities["childActivityInstances"]:
                    if activity.get("activityId") == "Task_UserReview":
                        current_state = "waiting_for_user_review"
                    elif activity.get("activityId") == "Gateway_UserChoice":
                        current_state = "user_decision_made"
                    elif activity.get("activityId") == "Task_LLMProcessing":
                        current_state = "llm_processing"
                    elif activity.get("activityId") == "Task_StoreVector":
                        current_state = "storing_results"

            return {
                "process_instance_id": process_instance_id,
                "current_state": current_state,
                "process_status": instance.get("state", "unknown"),
                "business_key": instance.get("businessKey"),
                "start_time": instance.get("startTime"),
                "end_time": instance.get("endTime"),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching task status: {str(e)}")

