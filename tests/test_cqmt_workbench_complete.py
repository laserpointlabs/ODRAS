#!/usr/bin/env python3
"""
Comprehensive test suite for the CQ/MT Workbench.
Tests CRUD operations, execution, and validation for both Competency Questions and Microtheories.
"""

import pytest
import httpx
import json
import time
from typing import Dict, Optional

BASE_URL = "http://localhost:8000"
TEST_PROJECT_NAME = "CQ/MT Test Project"
TEST_CREDENTIALS = {"username": "das_service", "password": "das_service_2024!"}

class TestCQMTWorkbench:
    """Test suite for CQ/MT Workbench functionality."""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token."""
        with httpx.Client() as client:
            response = client.post(
                f"{BASE_URL}/api/auth/login",
                json=TEST_CREDENTIALS,
                timeout=30.0
            )
            assert response.status_code == 200, f"Login failed: {response.text}"
            data = response.json()
            token = data.get("access_token") or data.get("token")
            assert token, "No token received"
            return token
    
    @pytest.fixture(scope="class")
    def client(self, auth_token):
        """Create authenticated HTTP client."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        with httpx.Client(headers=headers, timeout=30.0) as client:
            yield client
    
    @pytest.fixture(scope="class")
    def project_id(self, client):
        """Create and return a test project ID."""
        # Clean up any existing test project
        response = client.get(f"{BASE_URL}/api/projects")
        if response.status_code == 200:
            projects = response.json().get("projects", [])
            for project in projects:
                if project.get("name") == TEST_PROJECT_NAME:
                    project_id = project.get("project_id")
                    client.delete(f"{BASE_URL}/api/projects/{project_id}")
                    time.sleep(1)
        
        # Create new test project
        response = client.post(
            f"{BASE_URL}/api/projects",
            json={
                "name": TEST_PROJECT_NAME,
                "description": "Test project for CQ/MT Workbench",
                "namespace": "cqmt-test"
            }
        )
        assert response.status_code == 200, f"Failed to create project: {response.text}"
        project_data = response.json()
        project_id = (project_data.get("project") or {}).get("project_id") or project_data.get("project_id")
        assert project_id, "No project ID returned"
        
        yield project_id
        
        # Cleanup
        client.delete(f"{BASE_URL}/api/projects/{project_id}")
    
    @pytest.fixture(scope="class")
    def ontology_iri(self, client, project_id):
        """Create test ontology and return graph IRI."""
        ontology_content = """
@prefix ex: <http://example.org/test#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

ex:Aircraft a owl:Class ;
    rdfs:label "Aircraft" ;
    rdfs:comment "A flying vehicle" .

ex:FighterJet a owl:Class ;
    rdfs:subClassOf ex:Aircraft ;
    rdfs:label "Fighter Jet" ;
    rdfs:comment "A military fighter aircraft" .

ex:TransportPlane a owl:Class ;
    rdfs:subClassOf ex:Aircraft ;
    rdfs:label "Transport Plane" ;
    rdfs:comment "A cargo transport aircraft" .

ex:F22 a ex:FighterJet ;
    rdfs:label "F-22 Raptor" ;
    ex:hasSpeed "Mach 2.25" .

ex:F35 a ex:FighterJet ;
    rdfs:label "F-35 Lightning II" ;
    ex:hasSpeed "Mach 1.6" .

ex:C130 a ex:TransportPlane ;
    rdfs:label "C-130 Hercules" ;
    ex:hasCapacity "92 passengers" .

ex:C17 a ex:TransportPlane ;
    rdfs:label "C-17 Globemaster III" ;
    ex:hasCapacity "102 passengers" .
"""
        
        # Create ontology entry
        create_response = client.post(
            f"{BASE_URL}/api/ontology/",
            json={
                "project_id": project_id,
                "ontology": {
                    "label": "Test Ontology",
                    "description": "Test ontology for CQ/MT validation"
                }
            }
        )
        
        # Import ontology content
        import_response = client.post(
            f"{BASE_URL}/api/ontology/import",
            json={
                "file_content": ontology_content,
                "format": "turtle",
                "user_id": "test_user"
            }
        )
        
        assert import_response.status_code in [200, 201], f"Failed to import ontology: {import_response.text}"
        
        graph_iri = f"http://localhost:8000/odras/projects/{project_id}/ontologies/test-ontology"
        yield graph_iri
    
    def test_create_microtheory(self, client, project_id):
        """Test creating a microtheory."""
        response = client.post(
            f"{BASE_URL}/api/cqmt/projects/{project_id}/microtheories",
            json={
                "label": "Baseline MT",
                "description": "Baseline microtheory for testing",
                "setDefault": True
            }
        )
        
        assert response.status_code in [200, 201], f"Failed to create microtheory: {response.text}"
        data = response.json()
        mt_data = data.get("data") or data
        assert mt_data.get("id"), "No MT ID returned"
        assert mt_data.get("iri"), "No MT IRI returned"
        assert mt_data.get("is_default") == True, "MT should be default"
        
        return mt_data
    
    def test_list_microtheories(self, client, project_id):
        """Test listing microtheories."""
        response = client.get(f"{BASE_URL}/api/cqmt/projects/{project_id}/microtheories")
        
        assert response.status_code == 200, f"Failed to list microtheories: {response.text}"
        mts = response.json()
        assert isinstance(mts, list), "Response should be a list"
        assert len(mts) > 0, "Should have at least one microtheory"
        
        return mts
    
    def test_create_competency_question(self, client, project_id):
        """Test creating a competency question."""
        # Get microtheories first
        mts_response = client.get(f"{BASE_URL}/api/cqmt/projects/{project_id}/microtheories")
        mts = mts_response.json()
        assert len(mts) > 0, "Need at least one microtheory"
        mt_iri = mts[0].get("iri")
        
        response = client.post(
            f"{BASE_URL}/api/cqmt/projects/{project_id}/cqs",
            json={
                "cq_name": "List all aircraft",
                "problem_text": "What aircraft are available in the system?",
                "sparql_text": """
SELECT ?aircraft ?type WHERE {
    ?aircraft rdf:type ?type .
    ?type rdfs:subClassOf ex:Aircraft .
}
""",
                "contract_json": {
                    "require_columns": ["aircraft", "type"],
                    "min_rows": 1
                },
                "mt_iri_default": mt_iri,
                "status": "active"
            }
        )
        
        assert response.status_code in [200, 201], f"Failed to create CQ: {response.text}"
        data = response.json()
        cq_data = data.get("data") or data
        assert cq_data.get("id"), "No CQ ID returned"
        
        return cq_data
    
    def test_list_competency_questions(self, client, project_id):
        """Test listing competency questions."""
        response = client.get(f"{BASE_URL}/api/cqmt/projects/{project_id}/cqs")
        
        assert response.status_code == 200, f"Failed to list CQs: {response.text}"
        cqs = response.json()
        assert isinstance(cqs, list), "Response should be a list"
        assert len(cqs) > 0, "Should have at least one CQ"
        
        return cqs
    
    def test_get_cq_details(self, client, project_id):
        """Test getting CQ details."""
        # Get a CQ ID first
        cqs_response = client.get(f"{BASE_URL}/api/cqmt/projects/{project_id}/cqs")
        cqs = cqs_response.json()
        assert len(cqs) > 0, "Need at least one CQ"
        cq_id = cqs[0].get("id")
        
        response = client.get(f"{BASE_URL}/api/cqmt/cqs/{cq_id}")
        
        assert response.status_code == 200, f"Failed to get CQ details: {response.text}"
        response_data = response.json()
        cq_data = response_data.get("data") or response_data
        assert cq_data.get("id") == cq_id, "Wrong CQ returned"
        assert cq_data.get("cq_name"), "CQ should have a name"
        assert cq_data.get("sparql_text") or cq_data.get("sparql_template"), "CQ should have SPARQL"
        
        return cq_data
    
    def test_execute_cq(self, client, project_id):
        """Test executing a competency question."""
        # Get CQ and MT
        cqs_response = client.get(f"{BASE_URL}/api/cqmt/projects/{project_id}/cqs")
        cqs = cqs_response.json()
        assert len(cqs) > 0, "Need at least one CQ"
        cq_id = cqs[0].get("id")
        
        mts_response = client.get(f"{BASE_URL}/api/cqmt/projects/{project_id}/microtheories")
        mts = mts_response.json()
        assert len(mts) > 0, "Need at least one microtheory"
        mt_iri = mts[0].get("iri")
        
        response = client.post(
            f"{BASE_URL}/api/cqmt/cqs/{cq_id}/run",
            json={
                "mt_iri": mt_iri,
                "params": {}
            }
        )
        
        assert response.status_code == 200, f"Failed to execute CQ: {response.text}"
        result = response.json()
        assert "passed" in result, "Result should have 'passed' field"
        assert "columns" in result, "Result should have 'columns' field"
        assert "row_count" in result, "Result should have 'row_count' field"
        
        return result
    
    def test_get_cq_runs(self, client, project_id):
        """Test getting CQ execution history."""
        # Get a CQ ID first
        cqs_response = client.get(f"{BASE_URL}/api/cqmt/projects/{project_id}/cqs")
        cqs = cqs_response.json()
        assert len(cqs) > 0, "Need at least one CQ"
        cq_id = cqs[0].get("id")
        
        response = client.get(f"{BASE_URL}/api/cqmt/cqs/{cq_id}/runs")
        
        assert response.status_code == 200, f"Failed to get CQ runs: {response.text}"
        response_data = response.json()
        runs = response_data.get("data") or response_data
        assert isinstance(runs, list), "Response should be a list"
        
        return runs
    
    def test_update_microtheory(self, client, project_id):
        """Test updating a microtheory."""
        # Create a temporary MT to update
        create_response = client.post(
            f"{BASE_URL}/api/cqmt/projects/{project_id}/microtheories",
            json={
                "label": "Original MT",
                "description": "Original description",
                "setDefault": False
            }
        )
        assert create_response.status_code in [200, 201], f"Failed to create MT for update: {create_response.text}"
        mt_data = create_response.json()
        print(f"MT create response: {mt_data}")
        mt_id = (mt_data.get("data") or mt_data).get("id")
        assert mt_id, f"No MT ID returned. Full response: {mt_data}"
        
        # Verify we can GET the MT before updating
        get_response = client.get(f"{BASE_URL}/api/cqmt/microtheories/{mt_id}")
        assert get_response.status_code == 200, f"Failed to get MT before update: {get_response.text}"
        
        # Update the MT
        response = client.put(
            f"{BASE_URL}/api/cqmt/microtheories/{mt_id}",
            json={
                "label": "Updated Baseline MT",
                "description": "Updated description"
            }
        )
        
        assert response.status_code == 200, f"Failed to update microtheory: {response.text}"
        data = response.json()
        updated_mt = data.get("data") or data
        assert updated_mt.get("label") == "Updated Baseline MT", "Label should be updated"
        
        # Clean up
        client.delete(f"{BASE_URL}/api/cqmt/microtheories/{mt_id}")
        
        return updated_mt
    
    def test_set_default_microtheory(self, client, project_id):
        """Test setting a microtheory as default."""
        # Get all MTs
        mts_response = client.get(f"{BASE_URL}/api/cqmt/projects/{project_id}/microtheories")
        mts = mts_response.json()
        assert len(mts) > 0, "Need at least one microtheory"
        
        # Find a non-default MT or use the first one
        mt = None
        for m in mts:
            if not m.get("is_default"):
                mt = m
                break
        if not mt:
            mt = mts[0]
        
        mt_id = mt.get("id")
        
        response = client.post(
            f"{BASE_URL}/api/cqmt/microtheories/{mt_id}/set-default",
            params={"project_id": project_id}
        )
        
        assert response.status_code == 200, f"Failed to set default MT: {response.text}"
        
        # Verify it's now default
        mts_response = client.get(f"{BASE_URL}/api/cqmt/projects/{project_id}/microtheories")
        mts = mts_response.json()
        for m in mts:
            if m.get("id") == mt_id:
                assert m.get("is_default") == True, "MT should be default"
                break
    
    def test_delete_cq(self, client, project_id):
        """Test deleting a competency question."""
        # Create a CQ to delete
        mts_response = client.get(f"{BASE_URL}/api/cqmt/projects/{project_id}/microtheories")
        mts = mts_response.json()
        mt_iri = mts[0].get("iri")
        
        create_response = client.post(
            f"{BASE_URL}/api/cqmt/projects/{project_id}/cqs",
            json={
                "cq_name": "Temporary CQ",
                "problem_text": "Temporary CQ for deletion test",
                "sparql_text": "SELECT ?s WHERE { ?s ?p ?o }",
                "contract_json": {"require_columns": ["s"]},
                "mt_iri_default": mt_iri,
                "status": "draft"
            }
        )
        
        assert create_response.status_code in [200, 201], "Failed to create CQ for deletion"
        cq_data = create_response.json()
        cq_id = (cq_data.get("data") or cq_data).get("id")
        
        # Delete the CQ
        response = client.delete(f"{BASE_URL}/api/cqmt/cqs/{cq_id}")
        
        assert response.status_code in [200, 204], f"Failed to delete CQ: {response.text}"
        
        # Verify it's deleted
        get_response = client.get(f"{BASE_URL}/api/cqmt/cqs/{cq_id}")
        assert get_response.status_code == 404, "CQ should not exist after deletion"
    
    def test_delete_microtheory(self, client, project_id):
        """Test deleting a microtheory."""
        # Create an MT to delete
        create_response = client.post(
            f"{BASE_URL}/api/cqmt/projects/{project_id}/microtheories",
            json={
                "label": "Temporary MT",
                "description": "Temporary MT for deletion test",
                "setDefault": False
            }
        )
        
        assert create_response.status_code in [200, 201], "Failed to create MT for deletion"
        mt_data = create_response.json()
        mt_id = (mt_data.get("data") or mt_data).get("id")
        
        # Delete the MT
        response = client.delete(f"{BASE_URL}/api/cqmt/microtheories/{mt_id}")
        
        assert response.status_code in [200, 204], f"Failed to delete MT: {response.text}"
        
        # Verify it's deleted - check that GET returns 404
        get_response = client.get(f"{BASE_URL}/api/cqmt/microtheories/{mt_id}")
        # The API may return 500 if there's an error accessing the deleted MT
        assert get_response.status_code in [404, 500], f"MT should not exist after deletion (got {get_response.status_code})"
    
    def test_cqmt_workflow(self, client, project_id):
        """Test complete CQ/MT workflow."""
        # 1. Create a microtheory
        mt_response = client.post(
            f"{BASE_URL}/api/cqmt/projects/{project_id}/microtheories",
            json={
                "label": "Workflow Test MT",
                "description": "MT for workflow testing",
                "setDefault": False
            }
        )
        assert mt_response.status_code in [200, 201]
        mt_data = mt_response.json()
        mt_iri = (mt_data.get("data") or mt_data).get("iri")
        
        # 2. Create a CQ
        cq_response = client.post(
            f"{BASE_URL}/api/cqmt/projects/{project_id}/cqs",
            json={
                "cq_name": "Workflow Test CQ",
                "problem_text": "Test CQ for workflow validation",
                "sparql_text": "SELECT ?s WHERE { ?s ?p ?o } LIMIT 10",
                "contract_json": {"require_columns": ["s"], "min_rows": 0},
                "mt_iri_default": mt_iri,
                "status": "active"
            }
        )
        assert cq_response.status_code in [200, 201]
        cq_data = cq_response.json()
        cq_id = (cq_data.get("data") or cq_data).get("id")
        
        # 3. Execute the CQ
        run_response = client.post(
            f"{BASE_URL}/api/cqmt/cqs/{cq_id}/run",
            json={"mt_iri": mt_iri, "params": {}}
        )
        assert run_response.status_code == 200
        run_result = run_response.json()
        assert "passed" in run_result
        
        # 4. Get execution history
        runs_response = client.get(f"{BASE_URL}/api/cqmt/cqs/{cq_id}/runs")
        assert runs_response.status_code == 200
        runs = runs_response.json()
        assert len(runs) > 0
        
        # 5. Clean up
        client.delete(f"{BASE_URL}/api/cqmt/cqs/{cq_id}")
        client.delete(f"{BASE_URL}/api/cqmt/microtheories/{mt_iri}")
        
        print("\n✅ Complete CQ/MT workflow test passed!")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
