"""
Comprehensive integration tests for CQ/MT Workbench.
Tests the complete workflow from microtheory creation to CQ execution.

Requirements:
- ODRAS services must be running (PostgreSQL, Fuseki, Redis)
- ODRAS API must be running
- Tests use das_service credentials
"""

import pytest
import json
import uuid
from typing import Dict, Any
import httpx
import asyncio
import time


@pytest.fixture
def auth_headers():
    """Authentication headers for das_service user."""
    return {"Authorization": "Bearer test_token_das_service"}  # Will be set up properly


@pytest.fixture
def test_project_id():
    """Generate a unique test project ID."""
    return str(uuid.uuid4())


@pytest.fixture
def api_client():
    """HTTP client for API requests."""
    return httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0)


@pytest.mark.integration
class TestCQMTWorkbench:
    """Comprehensive CQ/MT Workbench integration tests."""
    
    async def test_microtheory_lifecycle(self, api_client, auth_headers, test_project_id):
        """Test complete microtheory CRUD lifecycle."""
        
        # 1. Create a microtheory
        mt_data = {
            "label": "Test Baseline",
            "setDefault": True
        }
        
        response = await api_client.post(
            f"/api/cqmt/projects/{test_project_id}/microtheories",
            json=mt_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        
        mt_id = result["data"]["id"]
        mt_iri = result["data"]["iri"]
        
        # 2. List microtheories
        response = await api_client.get(
            f"/api/cqmt/projects/{test_project_id}/microtheories",
            headers=auth_headers
        )
        assert response.status_code == 200
        microtheories = response.json()
        assert len(microtheories) == 1
        assert microtheories[0]["label"] == "Test Baseline"
        assert microtheories[0]["is_default"] is True
        assert microtheories[0]["triple_count"] == 0  # Empty initially
        
        # 3. Create a clone
        clone_data = {
            "label": "Test Clone",
            "cloneFrom": mt_iri,
            "setDefault": False
        }
        
        response = await api_client.post(
            f"/api/cqmt/projects/{test_project_id}/microtheories",
            json=clone_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        clone_result = response.json()
        assert clone_result["success"] is True
        
        clone_id = clone_result["data"]["id"]
        
        # 4. Set clone as default
        response = await api_client.post(
            f"/api/cqmt/microtheories/{clone_id}/set-default?project_id={test_project_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # 5. Verify default changed
        response = await api_client.get(
            f"/api/cqmt/projects/{test_project_id}/microtheories",
            headers=auth_headers
        )
        microtheories = response.json()
        assert len(microtheories) == 2
        
        default_mt = next(mt for mt in microtheories if mt["is_default"])
        assert default_mt["id"] == clone_id
        
        # 6. Delete original microtheory
        response = await api_client.delete(
            f"/api/cqmt/microtheories/{mt_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # 7. Verify deletion
        response = await api_client.get(
            f"/api/cqmt/projects/{test_project_id}/microtheories",
            headers=auth_headers
        )
        microtheories = response.json()
        assert len(microtheories) == 1
        assert microtheories[0]["id"] == clone_id
    
    async def test_competency_question_lifecycle(self, api_client, auth_headers, test_project_id):
        """Test complete CQ CRUD lifecycle."""
        
        # 1. Create a CQ
        cq_data = {
            "cq_name": "Test CQ - List Subjects",
            "problem_text": "What subjects are in the knowledge graph?",
            "sparql_text": "SELECT ?s WHERE { ?s ?p ?o } LIMIT 10",
            "contract_json": {
                "require_columns": ["s"],
                "min_rows": 1,
                "max_latency_ms": 5000
            },
            "status": "active"
        }
        
        response = await api_client.post(
            f"/api/cqmt/projects/{test_project_id}/cqs",
            json=cq_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        
        cq_id = result["data"]["id"]
        
        # 2. List CQs
        response = await api_client.get(
            f"/api/cqmt/projects/{test_project_id}/cqs",
            headers=auth_headers
        )
        assert response.status_code == 200
        cqs = response.json()
        assert len(cqs) == 1
        assert cqs[0]["cq_name"] == "Test CQ - List Subjects"
        assert cqs[0]["status"] == "active"
        assert cqs[0]["last_run_status"] is None  # No runs yet
        
        # 3. Get CQ details
        response = await api_client.get(
            f"/api/cqmt/cqs/{cq_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        details = response.json()
        assert details["success"] is True
        cq_details = details["data"]
        assert cq_details["cq_name"] == "Test CQ - List Subjects"
        assert len(cq_details["recent_runs"]) == 0
        
        # 4. Update CQ
        updated_cq = {
            "cq_name": "Test CQ - List Subjects",  # Same name for upsert
            "problem_text": "What subjects are in the knowledge graph? (Updated)",
            "sparql_text": "SELECT DISTINCT ?s WHERE { ?s ?p ?o } LIMIT 5",
            "contract_json": {
                "require_columns": ["s"],
                "min_rows": 1,
                "max_latency_ms": 3000
            },
            "status": "active"
        }
        
        response = await api_client.post(
            f"/api/cqmt/projects/{test_project_id}/cqs",
            json=updated_cq,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # 5. Verify update
        response = await api_client.get(
            f"/api/cqmt/cqs/{cq_id}",
            headers=auth_headers
        )
        details = response.json()["data"]
        assert "Updated" in details["problem_text"]
        assert "DISTINCT" in details["sparql_text"]
    
    async def test_cq_execution_and_contract_validation(self, api_client, auth_headers, test_project_id):
        """Test CQ execution with contract validation."""
        
        # 1. Create microtheory with sample data
        mt_data = {"label": "Test Data MT", "setDefault": True}
        response = await api_client.post(
            f"/api/cqmt/projects/{test_project_id}/microtheories",
            json=mt_data,
            headers=auth_headers
        )
        mt_iri = response.json()["data"]["iri"]
        
        # 2. Add sample triples (would be done via SPARQL INSERT)
        # This test assumes the SPARQLRunner.insert_sample_triples works
        
        # 3. Create CQ with contract that should PASS
        passing_cq = {
            "cq_name": "Always Pass CQ",
            "problem_text": "Test CQ designed to pass contract validation",
            "sparql_text": "SELECT ('test' AS ?result) WHERE { }",
            "contract_json": {
                "require_columns": ["result"],
                "min_rows": 1,
                "max_latency_ms": 5000
            },
            "mt_iri_default": mt_iri,
            "status": "active"
        }
        
        response = await api_client.post(
            f"/api/cqmt/projects/{test_project_id}/cqs",
            json=passing_cq,
            headers=auth_headers
        )
        passing_cq_id = response.json()["data"]["id"]
        
        # 4. Run the CQ
        run_data = {"params": {}}
        response = await api_client.post(
            f"/api/cqmt/cqs/{passing_cq_id}/run",
            json=run_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        run_result = response.json()
        
        assert run_result["pass"] is True
        assert run_result["reason"] == "pass"
        assert "result" in run_result["columns"]
        assert run_result["row_count"] == 1
        assert run_result["latency_ms"] > 0
        assert run_result["run_id"] is not None
        
        # 5. Create CQ that should FAIL (missing columns)
        failing_cq = {
            "cq_name": "Failing CQ",
            "problem_text": "Test CQ designed to fail contract validation",
            "sparql_text": "SELECT ('test' AS ?wrong_column) WHERE { }",
            "contract_json": {
                "require_columns": ["missing_column"],
                "min_rows": 1
            },
            "mt_iri_default": mt_iri,
            "status": "active"
        }
        
        response = await api_client.post(
            f"/api/cqmt/projects/{test_project_id}/cqs",
            json=failing_cq,
            headers=auth_headers
        )
        failing_cq_id = response.json()["data"]["id"]
        
        # 6. Run the failing CQ
        response = await api_client.post(
            f"/api/cqmt/cqs/{failing_cq_id}/run",
            json={"params": {}},
            headers=auth_headers
        )
        run_result = response.json()
        
        assert run_result["pass"] is False
        assert "missing_required_columns" in run_result["reason"]
        assert "missing_column" in run_result["reason"]
        
        # 7. Check run history
        response = await api_client.get(
            f"/api/cqmt/cqs/{passing_cq_id}/runs",
            headers=auth_headers
        )
        assert response.status_code == 200
        runs = response.json()
        assert runs["success"] is True
        assert len(runs["data"]) == 1
        assert runs["data"][0]["pass"] is True
    
    async def test_sparql_parameter_binding(self, api_client, auth_headers, test_project_id):
        """Test SPARQL parameter binding with {{var}} syntax."""
        
        # 1. Create microtheory
        mt_data = {"label": "Param Test MT", "setDefault": True}
        response = await api_client.post(
            f"/api/cqmt/projects/{test_project_id}/microtheories",
            json=mt_data,
            headers=auth_headers
        )
        mt_iri = response.json()["data"]["iri"]
        
        # 2. Create CQ with parameters
        param_cq = {
            "cq_name": "Parameterized CQ",
            "problem_text": "Test parameter binding in SPARQL queries",
            "sparql_text": "SELECT (?value AS ?result) WHERE { BIND({{test_param}} AS ?value) }",
            "contract_json": {
                "require_columns": ["result"],
                "min_rows": 1
            },
            "mt_iri_default": mt_iri,
            "status": "active"
        }
        
        response = await api_client.post(
            f"/api/cqmt/projects/{test_project_id}/cqs",
            json=param_cq,
            headers=auth_headers
        )
        cq_id = response.json()["data"]["id"]
        
        # 3. Run with parameters
        run_data = {
            "params": {
                "test_param": "Hello World"
            }
        }
        
        response = await api_client.post(
            f"/api/cqmt/cqs/{cq_id}/run",
            json=run_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        result = response.json()
        
        assert result["pass"] is True
        assert result["row_count"] == 1
        # The bound parameter should appear in the results
        assert len(result["rows_preview"]) == 1
        assert "Hello World" in str(result["rows_preview"][0])
    
    async def test_das_assist_stubs(self, api_client, auth_headers, test_project_id):
        """Test DAS assist stub endpoints."""
        
        # 1. Test SPARQL suggestion
        suggest_data = {
            "problem_text": "I want to find all aircraft in the system"
        }
        
        response = await api_client.post(
            "/api/cqmt/assist/suggest-sparql",
            json=suggest_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        result = response.json()
        
        assert "sparql_draft" in result
        assert "confidence" in result
        assert "notes" in result
        assert "SELECT" in result["sparql_draft"]
        assert "aircraft" in result["sparql_draft"].lower()
        
        # 2. Test ontology deltas
        deltas_data = {
            "sparql_text": "SELECT ?aircraft WHERE { ?aircraft rdf:type ex:Aircraft }",
            "project_id": test_project_id
        }
        
        response = await api_client.post(
            "/api/cqmt/assist/suggest-ontology-deltas",
            json=deltas_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        result = response.json()
        
        assert "existing" in result
        assert "missing" in result
        assert isinstance(result["existing"], list)
        assert isinstance(result["missing"], list)
    
    async def test_error_handling(self, api_client, auth_headers, test_project_id):
        """Test error handling and validation."""
        
        # 1. Invalid CQ contract
        invalid_cq = {
            "cq_name": "Invalid CQ",
            "problem_text": "Test invalid contract",
            "sparql_text": "SELECT ?s WHERE { ?s ?p ?o }",
            "contract_json": {
                "require_columns": "not_an_array"  # Should be array
            }
        }
        
        response = await api_client.post(
            f"/api/cqmt/projects/{test_project_id}/cqs",
            json=invalid_cq,
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "Invalid contract" in response.json()["detail"]
        
        # 2. Invalid SPARQL
        invalid_sparql_cq = {
            "cq_name": "Invalid SPARQL CQ", 
            "problem_text": "Test invalid SPARQL",
            "sparql_text": "INVALID SPARQL QUERY",
            "contract_json": {
                "require_columns": ["s"]
            }
        }
        
        response = await api_client.post(
            f"/api/cqmt/projects/{test_project_id}/cqs",
            json=invalid_sparql_cq,
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "Invalid SPARQL" in response.json()["detail"]
        
        # 3. Nonexistent CQ run
        response = await api_client.post(
            f"/api/cqmt/cqs/{str(uuid.uuid4())}/run",
            json={"params": {}},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "CQ not found" in response.json()["pass"] is False
        
        # 4. Nonexistent microtheory deletion
        response = await api_client.delete(
            f"/api/cqmt/microtheories/{str(uuid.uuid4())}",
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.integration 
async def test_complete_workflow(api_client, auth_headers):
    """Test the complete CQ/MT workflow from start to finish."""
    
    project_id = str(uuid.uuid4())
    
    # 1. Create baseline microtheory with default data
    baseline_data = {"label": "Baseline", "setDefault": True}
    response = await api_client.post(
        f"/api/cqmt/projects/{project_id}/microtheories",
        json=baseline_data,
        headers=auth_headers
    )
    baseline_iri = response.json()["data"]["iri"]
    
    # 2. Create empty test microtheory
    empty_data = {"label": "Empty Test", "setDefault": False}
    response = await api_client.post(
        f"/api/cqmt/projects/{project_id}/microtheories",
        json=empty_data,
        headers=auth_headers
    )
    empty_iri = response.json()["data"]["iri"]
    
    # 3. Create a competency question
    cq_data = {
        "cq_name": "Test Workflow CQ",
        "problem_text": "Does the system have any data?",
        "sparql_text": "SELECT ?s WHERE { ?s ?p ?o } LIMIT 1",
        "contract_json": {
            "require_columns": ["s"],
            "min_rows": 1
        },
        "mt_iri_default": baseline_iri,
        "status": "active"
    }
    
    response = await api_client.post(
        f"/api/cqmt/projects/{project_id}/cqs",
        json=cq_data,
        headers=auth_headers
    )
    cq_id = response.json()["data"]["id"]
    
    # 4. Run CQ in baseline MT (might pass if there's data)
    response = await api_client.post(
        f"/api/cqmt/cqs/{cq_id}/run",
        json={"mt_iri": baseline_iri, "params": {}},
        headers=auth_headers
    )
    baseline_result = response.json()
    assert "pass" in baseline_result
    assert "reason" in baseline_result
    
    # 5. Run CQ in empty MT (should fail)
    response = await api_client.post(
        f"/api/cqmt/cqs/{cq_id}/run",
        json={"mt_iri": empty_iri, "params": {}},
        headers=auth_headers
    )
    empty_result = response.json()
    assert empty_result["pass"] is False
    assert "min_rows_not_met" in empty_result["reason"]
    
    # 6. Verify run history exists
    response = await api_client.get(
        f"/api/cqmt/cqs/{cq_id}/runs",
        headers=auth_headers
    )
    runs = response.json()["data"]
    assert len(runs) == 2  # Both runs recorded
    
    # 7. Verify microtheory list shows correct counts
    response = await api_client.get(
        f"/api/cqmt/projects/{project_id}/microtheories",
        headers=auth_headers
    )
    microtheories = response.json()
    assert len(microtheories) == 2
    
    print("✅ Complete CQ/MT workflow test passed!")


if __name__ == "__main__":
    # Run tests manually if needed
    print("CQ/MT Workbench Integration Tests")
    print("Run with: pytest tests/test_cqmt_workbench.py -v -s")
    print("Ensure ODRAS services are running first!")
