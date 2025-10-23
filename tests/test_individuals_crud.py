"""
Individual Tables CRUD Test Suite
Tests create, read, update, delete operations for ontology individuals
"""
import pytest
import requests
import json
import time
from typing import Dict, Any


# Test configuration
BASE_URL = "http://localhost:8000"
PROJECT_ID = "e2f2a845-8415-402b-aea7-d0305a6ee6a2"
GRAPH_IRI = "https://xma-adt.usnc.mil/projects/e2f2a845-8415-402b-aea7-d0305a6ee6a2/ontologies/testontology"
CLASS_NAME = "Aircraft"
TEST_CREDENTIALS = {"username": "das_service", "password": "das_service_2024!"}


class TestIndividualCRUD:
    """Test suite for Individual Tables CRUD operations"""
    
    @pytest.fixture(scope="class")
    def auth_token(self) -> str:
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=TEST_CREDENTIALS,
            timeout=30
        )
        assert response.status_code == 200, f"Authentication failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token: str) -> Dict[str, str]:
        """Get request headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    @pytest.fixture(scope="class")
    def test_individual_name(self) -> str:
        """Generate unique test individual name"""
        return f"CRUDTest_{int(time.time())}"
    
    def test_01_create_individual(self, headers: Dict[str, str], test_individual_name: str) -> str:
        """Test CREATE operation"""
        individual_data = {
            "name": test_individual_name,
            "class_type": CLASS_NAME,
            "properties": {
                "hasMaxSpeed": "200",
                "isOperational": "true"
            },
            "graph_iri": GRAPH_IRI
        }
        
        response = requests.post(
            f"{BASE_URL}/api/individuals/{PROJECT_ID}/individuals/{CLASS_NAME}",
            headers=headers,
            json=individual_data,
            timeout=30
        )
        
        assert response.status_code == 200, f"CREATE failed: {response.text}"
        result = response.json()
        assert result.get("success") is True, "CREATE response missing success flag"
        assert "individual_uri" in result, "CREATE response missing individual_uri"
        
        individual_uri = result["individual_uri"]
        print(f"✅ CREATE passed - URI: {individual_uri}")
        return individual_uri
    
    def test_02_read_individual(self, headers: Dict[str, str], test_individual_name: str):
        """Test READ operation"""
        response = requests.get(
            f"{BASE_URL}/api/individuals/{PROJECT_ID}/individuals/{CLASS_NAME}",
            headers=headers,
            params={"graph": GRAPH_IRI},
            timeout=30
        )
        
        assert response.status_code == 200, f"READ failed: {response.text}"
        result = response.json()
        assert "individuals" in result, "READ response missing individuals array"
        
        # Find our test individual
        individuals = result["individuals"]
        found = any(ind["name"] == test_individual_name for ind in individuals)
        assert found, f"Individual {test_individual_name} not found in list"
        
        print(f"✅ READ passed - Found {len(individuals)} individuals")
    
    def test_03_update_individual(self, headers: Dict[str, str], test_individual_name: str) -> str:
        """Test UPDATE operation"""
        # Get the individual URI first
        response = requests.get(
            f"{BASE_URL}/api/individuals/{PROJECT_ID}/individuals/{CLASS_NAME}",
            headers=headers,
            params={"graph": GRAPH_IRI},
            timeout=30
        )
        
        individuals = response.json()["individuals"]
        test_ind = next((ind for ind in individuals if ind["name"] == test_individual_name), None)
        assert test_ind is not None, "Test individual not found for update"
        
        individual_uri = test_ind["uri"]
        individual_id = individual_uri.split("#")[-1]
        
        # Update the individual
        update_data = {
            "name": f"{test_individual_name}_UPDATED",
            "properties": {
                "hasMaxSpeed": "300",
                "isOperational": "false"
            }
        }
        
        response = requests.put(
            f"{BASE_URL}/api/individuals/{PROJECT_ID}/individuals/{CLASS_NAME}/{individual_id}",
            headers=headers,
            params={"graph": GRAPH_IRI, "uri": individual_uri},
            json=update_data,
            timeout=30
        )
        
        assert response.status_code == 200, f"UPDATE failed: {response.text}"
        result = response.json()
        assert result.get("success") is True, "UPDATE response missing success flag"
        
        print(f"✅ UPDATE passed")
        return individual_uri
    
    def test_04_verify_update(self, headers: Dict[str, str], test_individual_name: str):
        """Verify UPDATE was successful"""
        response = requests.get(
            f"{BASE_URL}/api/individuals/{PROJECT_ID}/individuals/{CLASS_NAME}",
            headers=headers,
            params={"graph": GRAPH_IRI},
            timeout=30
        )
        
        individuals = response.json()["individuals"]
        updated_name = f"{test_individual_name}_UPDATED"
        found = any(ind["name"] == updated_name for ind in individuals)
        assert found, f"Updated individual {updated_name} not found"
        
        # Verify properties were updated
        updated_ind = next((ind for ind in individuals if ind["name"] == updated_name), None)
        assert updated_ind["properties"]["hasMaxSpeed"] == "300", "hasMaxSpeed not updated"
        assert updated_ind["properties"]["isOperational"] == "false", "isOperational not updated"
        
        print(f"✅ Update verified - {updated_name} has correct properties")
    
    def test_05_delete_individual(self, headers: Dict[str, str], test_individual_name: str):
        """Test DELETE operation"""
        # Get the individual URI first
        response = requests.get(
            f"{BASE_URL}/api/individuals/{PROJECT_ID}/individuals/{CLASS_NAME}",
            headers=headers,
            params={"graph": GRAPH_IRI},
            timeout=30
        )
        
        individuals = response.json()["individuals"]
        updated_name = f"{test_individual_name}_UPDATED"
        test_ind = next((ind for ind in individuals if ind["name"] == updated_name), None)
        assert test_ind is not None, "Test individual not found for deletion"
        
        individual_uri = test_ind["uri"]
        individual_id = individual_uri.split("#")[-1]
        
        # Delete the individual
        response = requests.delete(
            f"{BASE_URL}/api/individuals/{PROJECT_ID}/individuals/{CLASS_NAME}/{individual_id}",
            headers=headers,
            params={"graph": GRAPH_IRI, "uri": individual_uri},
            timeout=30
        )
        
        assert response.status_code == 200, f"DELETE failed: {response.text}"
        result = response.json()
        assert result.get("success") is True, "DELETE response missing success flag"
        
        print(f"✅ DELETE passed")
    
    def test_06_verify_deletion(self, headers: Dict[str, str], test_individual_name: str):
        """Verify DELETE was successful"""
        response = requests.get(
            f"{BASE_URL}/api/individuals/{PROJECT_ID}/individuals/{CLASS_NAME}",
            headers=headers,
            params={"graph": GRAPH_IRI},
            timeout=30
        )
        
        individuals = response.json()["individuals"]
        updated_name = f"{test_individual_name}_UPDATED"
        found = any(ind["name"] == updated_name for ind in individuals)
        assert not found, f"Deleted individual {updated_name} still exists"
        
        print(f"✅ Deletion verified - Individual removed from database")
    
    def test_07_fuseki_integration(self, headers: Dict[str, str]):
        """Test Fuseki integration"""
        sparql_query = {
            "query": f"""
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT (COUNT(*) as ?count) WHERE {{
              GRAPH <{GRAPH_IRI}> {{
                ?s rdf:type <{GRAPH_IRI}#Aircraft> .
              }}
            }}
            """
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ontology/sparql",
            headers=headers,
            json=sparql_query,
            timeout=30
        )
        
        assert response.status_code == 200, f"Fuseki query failed: {response.text}"
        result = response.json()
        assert "results" in result, "Fuseki response missing results"
        
        print(f"✅ Fuseki integration verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
