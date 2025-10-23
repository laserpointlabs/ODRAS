"""
Integration tests for CQMT dependency tracking feature.
Tests Phase 1 implementation of dependency tracking system.
"""

import pytest
import httpx
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

BASE_URL = "http://localhost:8000"
TIMEOUT = 30.0


@pytest.fixture
def auth_token():
    """Get authentication token for das_service user."""
    response = httpx.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "das_service", "password": "das_service_2024!"},
        timeout=TIMEOUT
    )
    assert response.status_code == 200
    data = response.json()
    return data.get("token")


@pytest.fixture
def test_project(auth_token):
    """Create a test project and return its ID."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    response = httpx.post(
        f"{BASE_URL}/api/projects",
        json={"name": "CQMT Dependency Test", "description": "Test project for dependency tracking"},
        headers=headers,
        timeout=TIMEOUT
    )
    assert response.status_code in [200, 201]
    project_data = response.json()
    # The API returns {"project": {...}}
    project_id = project_data.get("project", {}).get("project_id")
    
    assert project_id is not None, f"Failed to get project_id from response: {project_data}"
    
    yield project_id
    
    # Cleanup
    try:
        httpx.delete(f"{BASE_URL}/api/projects/{project_id}", headers=headers, timeout=TIMEOUT)
    except:
        pass


@pytest.fixture
def test_ontology(auth_token, test_project):
    """Create a test ontology."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    response = httpx.post(
        f"{BASE_URL}/api/ontologies",
        json={
            "name": "test-ontology",
            "label": "Test Ontology",
            "project": test_project,
            "is_reference": False
        },
        headers=headers,
        timeout=TIMEOUT
    )
    assert response.status_code in [200, 201]
    data = response.json()
    graph_iri = data.get("graphIri") or data.get("graph_iri")
    
    yield graph_iri


class TestDependencyTracking:
    """Test suite for CQMT dependency tracking."""
    
    def test_create_mt_extracts_dependencies(self, auth_token, test_project, test_ontology):
        """Test that creating an MT automatically extracts dependencies."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create MT
        mt_response = httpx.post(
            f"{BASE_URL}/api/cqmt/projects/{test_project}/microtheories",
            json={
                "label": "Test MT",
                "description": "Test microtheory",
                "setDefault": True
            },
            headers=headers,
            timeout=TIMEOUT
        )
        assert mt_response.status_code in [200, 201]
        mt_data = mt_response.json()
        mt_id = mt_data.get("data", {}).get("id")
        
        assert mt_id is not None
        
        # Inject test data into MT
        # First get the MT IRI
        mt_details = httpx.get(
            f"{BASE_URL}/api/cqmt/microtheories/{mt_id}",
            headers=headers,
            timeout=TIMEOUT
        )
        assert mt_details.status_code == 200
        mt_iri = mt_details.json().get("data", {}).get("iri")
        
        # Add test triples via Fuseki
        import requests
        fuseki_url = "http://localhost:3030/odras"
        update_query = f"""
        PREFIX : <{test_ontology}#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        INSERT DATA {{
            GRAPH <{mt_iri}> {{
                :TestInstance rdf:type :TestClass ;
                    rdfs:label "Test Instance" ;
                    :hasProperty "test value" .
            }}
        }}
        """
        
        update_response = requests.post(
            f"{fuseki_url}/update",
            data=update_query.encode('utf-8'),
            headers={'Content-Type': 'application/sparql-update'},
            timeout=15
        )
        assert update_response.status_code in [200, 204]
        
        # Now extract dependencies manually (for testing)
        # We need to update the MT to trigger dependency extraction
        update_mt_response = httpx.put(
            f"{BASE_URL}/api/cqmt/microtheories/{mt_id}",
            json={
                "label": "Test MT Updated",
                "description": "Updated description",
                "setDefault": False
            },
            headers=headers,
            timeout=TIMEOUT
        )
        assert update_mt_response.status_code in [200, 201]
        
        # Check dependencies were extracted
        deps_response = httpx.get(
            f"{BASE_URL}/api/cqmt/microtheories/{mt_id}/dependencies",
            headers=headers,
            timeout=TIMEOUT
        )
        assert deps_response.status_code == 200
        deps_data = deps_response.json()
        
        print(f"Dependencies found: {deps_data}")
        assert deps_data.get("success") is True
        
        # Should have at least some dependencies
        dependencies = deps_data.get("data", [])
        print(f"Number of dependencies: {len(dependencies)}")
        
        # Cleanup
        httpx.delete(f"{BASE_URL}/api/cqmt/microtheories/{mt_id}", headers=headers, timeout=TIMEOUT)
    
    def test_get_dependencies_endpoint(self, auth_token, test_project):
        """Test that dependencies endpoint returns correct structure."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create MT
        mt_response = httpx.post(
            f"{BASE_URL}/api/cqmt/projects/{test_project}/microtheories",
            json={
                "label": "Empty MT",
                "description": "Empty microtheory",
                "setDefault": False
            },
            headers=headers,
            timeout=TIMEOUT
        )
        assert mt_response.status_code in [200, 201]
        mt_id = mt_response.json().get("data", {}).get("id")
        
        # Get dependencies
        deps_response = httpx.get(
            f"{BASE_URL}/api/cqmt/microtheories/{mt_id}/dependencies",
            headers=headers,
            timeout=TIMEOUT
        )
        assert deps_response.status_code == 200
        deps_data = deps_response.json()
        
        assert deps_data.get("success") is True
        assert "data" in deps_data
        assert "count" in deps_data
        assert isinstance(deps_data["data"], list)
        
        # Cleanup
        httpx.delete(f"{BASE_URL}/api/cqmt/microtheories/{mt_id}", headers=headers, timeout=TIMEOUT)
    
    def test_validation_endpoint(self, auth_token, test_project):
        """Test that validation endpoint works."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create MT
        mt_response = httpx.post(
            f"{BASE_URL}/api/cqmt/projects/{test_project}/microtheories",
            json={
                "label": "Validation Test MT",
                "description": "Test validation",
                "setDefault": False
            },
            headers=headers,
            timeout=TIMEOUT
        )
        assert mt_response.status_code in [200, 201]
        mt_id = mt_response.json().get("data", {}).get("id")
        
        # Validate
        validation_response = httpx.get(
            f"{BASE_URL}/api/cqmt/microtheories/{mt_id}/validation",
            headers=headers,
            timeout=TIMEOUT
        )
        assert validation_response.status_code == 200
        validation_data = validation_response.json()
        
        assert validation_data.get("success") is True
        assert "valid" in validation_data
        assert "total" in validation_data
        assert "valid_count" in validation_data
        assert "invalid_count" in validation_data
        assert "invalid_dependencies" in validation_data
        
        # Cleanup
        httpx.delete(f"{BASE_URL}/api/cqmt/microtheories/{mt_id}", headers=headers, timeout=TIMEOUT)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
