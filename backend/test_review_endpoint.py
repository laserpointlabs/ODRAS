"""
Test endpoint for the Requirements Review Interface
This creates mock data so you can test the review interface without running a full workflow
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter

router = APIRouter()

# Mock requirements data for testing
MOCK_REQUIREMENTS = [
    {
        "requirement_text": "The system shall provide user authentication using OAuth 2.0 standards",
        "text": "The system shall provide user authentication using OAuth 2.0 standards",
        "category": "Security",
        "confidence": 0.95,
        "source": "requirements.docx",
        "priority": "High",
        "id": "REQ-001",
    },
    {
        "requirement_text": "The system must support at least 1000 concurrent users",
        "text": "The system must support at least 1000 concurrent users",
        "category": "Performance",
        "confidence": 0.88,
        "source": "requirements.docx",
        "priority": "High",
        "id": "REQ-002",
    },
    {
        "requirement_text": "All data shall be encrypted at rest using AES-256 encryption",
        "text": "All data shall be encrypted at rest using AES-256 encryption",
        "category": "Security",
        "confidence": 0.92,
        "source": "requirements.docx",
        "priority": "Critical",
        "id": "REQ-003",
    },
    {
        "requirement_text": "The user interface should be responsive and work on mobile devices",
        "text": "The user interface should be responsive and work on mobile devices",
        "category": "User Interface",
        "confidence": 0.75,
        "source": "requirements.docx",
        "priority": "Medium",
        "id": "REQ-004",
    },
    {
        "requirement_text": "System backups must be performed daily at 2:00 AM UTC",
        "text": "System backups must be performed daily at 2:00 AM UTC",
        "category": "Operations",
        "confidence": 0.82,
        "source": "requirements.docx",
        "priority": "High",
        "id": "REQ-005",
    },
    {
        "requirement_text": "The API response time should not exceed 200ms for 95% of requests",
        "text": "The API response time should not exceed 200ms for 95% of requests",
        "category": "Performance",
        "confidence": 0.68,
        "source": "requirements.docx",
        "priority": "Medium",
        "id": "REQ-006",
    },
    {
        "requirement_text": "Users can export their data in CSV, JSON, or XML formats",
        "text": "Users can export their data in CSV, JSON, or XML formats",
        "category": "Functional",
        "confidence": 0.45,
        "source": "requirements.docx",
        "priority": "Low",
        "id": "REQ-007",
    },
    {
        "requirement_text": "The system must comply with GDPR regulations for data privacy",
        "text": "The system must comply with GDPR regulations for data privacy",
        "category": "Compliance",
        "confidence": 0.91,
        "source": "requirements.docx",
        "priority": "Critical",
        "id": "REQ-008",
    },
]

# Store for test process instances
TEST_PROCESSES = {}


@router.get("/api/test/create-review-task")
async def create_test_review_task():
    """Create a test process instance with mock requirements for testing the review interface"""

    # Generate a test process instance ID
    process_id = f"test-process-{uuid.uuid4().hex[:8]}"
    task_id = f"test-task-{uuid.uuid4().hex[:8]}"

    # Store the test data
    TEST_PROCESSES[process_id] = {
        "process_instance_id": process_id,
        "task_id": task_id,
        "requirements": MOCK_REQUIREMENTS,
        "document_filename": "test_requirements.docx",
        "document_content": "This is a test document with various requirements for testing the review interface.",
        "created": datetime.now().isoformat(),
        "status": "pending_review",
    }

    return {
        "success": True,
        "message": "Test review task created successfully",
        "process_instance_id": process_id,
        "task_id": task_id,
        "review_url": f"/user-review?taskId={task_id}&process_instance_id={process_id}",
        "instructions": f"Go to http://localhost:8000/user-review?taskId={task_id}&process_instance_id={process_id} to test the review interface",
    }


@router.get("/api/test/user-tasks")
async def get_test_user_tasks():
    """Return test user tasks including any created test review tasks"""

    tasks = []
    for process_id, data in TEST_PROCESSES.items():
        if data["status"] == "pending_review":
            tasks.append(
                {
                    "id": data["task_id"],
                    "name": "Review Requirements (TEST)",
                    "description": "Test task for reviewing extracted requirements",
                    "taskDefinitionKey": "Task_UserReview",
                    "processInstanceId": process_id,
                    "created": data["created"],
                    "priority": 50,
                }
            )

    # Also return the regular endpoint response structure
    return {"tasks": tasks}


@router.get("/api/test/user-tasks/{process_instance_id}/requirements")
async def get_test_requirements(process_instance_id: str):
    """Return mock requirements for testing"""

    if process_instance_id in TEST_PROCESSES:
        data = TEST_PROCESSES[process_instance_id]
        return {
            "process_instance_id": process_instance_id,
            "requirements": data["requirements"],
            "document_content": data["document_content"],
            "document_filename": data["document_filename"],
            "total_requirements": len(data["requirements"]),
        }
    else:
        # Return default mock data for any test process
        if process_instance_id.startswith("test"):
            return {
                "process_instance_id": process_instance_id,
                "requirements": MOCK_REQUIREMENTS,
                "document_content": "This is a test document with various requirements.",
                "document_filename": "test_document.docx",
                "total_requirements": len(MOCK_REQUIREMENTS),
            }

    return {
        "error": "Process instance not found",
        "process_instance_id": process_instance_id,
        "requirements": [],
        "total_requirements": 0,
    }


@router.post("/api/test/user-tasks/{process_instance_id}/complete")
async def complete_test_task(process_instance_id: str, user_decision: Dict):
    """Handle test task completion"""

    decision = user_decision.get("decision", "approve")

    # Update test process status
    if process_instance_id in TEST_PROCESSES:
        TEST_PROCESSES[process_instance_id]["status"] = f"completed_{decision}"
        TEST_PROCESSES[process_instance_id]["decision"] = user_decision
        TEST_PROCESSES[process_instance_id]["completed_at"] = datetime.now().isoformat()

    return {
        "task_id": TEST_PROCESSES.get(process_instance_id, {}).get("task_id", "unknown"),
        "process_instance_id": process_instance_id,
        "decision": decision,
        "status": "completed",
        "message": f"TEST: User task completed with decision: {decision}",
        "test_mode": True,
        "next_step": {
            "approve": "Would proceed to LLM processing",
            "rerun": "Would re-extract requirements with new parameters",
            "edit": "Would allow editing requirements",
        }.get(decision, "Unknown"),
    }


@router.get("/api/test/status")
async def get_test_status():
    """Get status of all test processes"""
    return {
        "test_processes": TEST_PROCESSES,
        "total_processes": len(TEST_PROCESSES),
        "pending_review": sum(
            1 for p in TEST_PROCESSES.values() if p["status"] == "pending_review"
        ),
        "completed": sum(1 for p in TEST_PROCESSES.values() if p["status"].startswith("completed")),
    }
