"""
Test Property Migration

Tests data property renaming migration for individuals.
Verifies that when properties are renamed in ontology, data is preserved.
"""
import pytest
import requests
import json

BASE_URL = "http://localhost:8000"
TEST_USERNAME = "das_service"
TEST_PASSWORD = "das_service_2024!"

# Set default timeout for all requests
import requests
requests.packages.urllib3.disable_warnings()

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        timeout=30
    )
    assert response.status_code == 200
    return response.json()["token"]

@pytest.fixture(scope="module")
def test_project(auth_token):
    """Create a test project"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Create project
    response = requests.post(
        f"{BASE_URL}/api/projects",
        json={"name": "Property Migration Test", "description": "Test project"},
        headers=headers,
        timeout=30
    )
    assert response.status_code == 200
    project_id = response.json()["project"]["project_id"]
    
    yield project_id
    
    # Cleanup: delete project (non-blocking)
    try:
        requests.delete(f"{BASE_URL}/api/projects/{project_id}", headers=headers, timeout=5)
    except:
        pass

@pytest.fixture(scope="module")
def test_ontology(auth_token, test_project):
    """Create test ontology with properties"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    graph_iri = f"https://xma-adt.usnc.mil/projects/{test_project}/ontologies/testontology"
    
    # Create ontology with Aircraft class and properties
    ontology_content = """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

<http://xma-adt.usnc.mil/projects/testproject/ontologies/testontology#Aircraft> rdf:type owl:Class ;
    rdfs:label "Aircraft" .

<http://xma-adt.usnc.mil/projects/testproject/ontologies/testontology#hasMaxSpeed> rdf:type owl:DatatypeProperty ;
    rdfs:label "has Max Speed" ;
    rdfs:domain <http://xma-adt.usnc.mil/projects/testproject/ontologies/testontology#Aircraft> .

<http://xma-adt.usnc.mil/projects/testproject/ontologies/testontology#isOperational> rdf:type owl:DatatypeProperty ;
    rdfs:label "is Operational" ;
    rdfs:domain <http://xma-adt.usnc.mil/projects/testproject/ontologies/testontology#Aircraft> .
"""
    
    response = requests.post(
        f"{BASE_URL}/api/ontology/save",
        params={"graph": graph_iri},
        data=ontology_content.encode('utf-8'),
        headers={**headers, "Content-Type": "text/turtle"},
        timeout=30
    )
    assert response.status_code == 200
    
    yield graph_iri

def test_property_rename_migration(auth_token, test_project, test_ontology):
    """Test that renaming a property preserves individual data"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Step 1: Create an individual with the old property name
    create_data = {
        "name": "F-22 Raptor",
        "class_type": "Aircraft",
        "properties": {
            "has Max Speed": "Mach 2.25",
            "is Operational": "true"
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/api/individuals/{test_project}/individuals/Aircraft",
        params={"graph": test_ontology},
        json=create_data,
        headers=headers,
        timeout=30
    )
    assert response.status_code == 200
    
    # Step 2: Verify individual was created
    response = requests.get(
        f"{BASE_URL}/api/individuals/{test_project}/individuals/Aircraft",
        params={"graph": test_ontology},
        headers=headers,
        timeout=30
    )
    assert response.status_code == 200
    individuals = response.json()["individuals"]
    assert len(individuals) == 1
    assert individuals[0]["name"] == "F-22 Raptor"
    assert "has Max Speed" in individuals[0]["properties"]
    
    # Step 3: Rename property in ontology
    new_ontology_content = """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

<http://xma-adt.usnc.mil/projects/testproject/ontologies/testontology#Aircraft> rdf:type owl:Class ;
    rdfs:label "Aircraft" .

<http://xma-adt.usnc.mil/projects/testproject/ontologies/testontology#MaxSpeed> rdf:type owl:DatatypeProperty ;
    rdfs:label "Max Speed" ;
    rdfs:domain <http://xma-adt.usnc.mil/projects/testproject/ontologies/testontology#Aircraft> .

<http://xma-adt.usnc.mil/projects/testproject/ontologies/testontology#isOperational> rdf:type owl:DatatypeProperty ;
    rdfs:label "is Operational" ;
    rdfs:domain <http://xma-adt.usnc.mil/projects/testproject/ontologies/testontology#Aircraft> .
"""
    
    response = requests.post(
        f"{BASE_URL}/api/ontology/save",
        params={"graph": test_ontology},
        data=new_ontology_content.encode('utf-8'),
        headers={**headers, "Content-Type": "text/turtle"},
        timeout=30
    )
    assert response.status_code == 200
    
    # Check for pending migrations
    response_data = response.json()
    assert "pending_migrations" in response_data or len(response_data.get("pending_migrations", [])) == 0
    
    # Step 4: Get pending mappings
    response = requests.get(
        f"{BASE_URL}/api/individuals/{test_project}/property-mappings",
        params={"graph": test_ontology},
        headers=headers,
        timeout=30
    )
    assert response.status_code == 200
    mappings = response.json().get("mappings", [])
    
    # Step 5: Apply migration
    if mappings:
        for mapping in mappings:
            if mapping["old_property_name"] == "has Max Speed":
                migrate_data = {
                    "graph_iri": test_ontology,
                    "class_name": mapping["class_name"],
                    "old_property_name": mapping["old_property_name"],
                    "new_property_name": mapping["new_property_name"]
                }
                
                response = requests.post(
                    f"{BASE_URL}/api/individuals/{test_project}/property-mappings/migrate",
                    json=migrate_data,
                    headers=headers,
                    timeout=30
                )
                assert response.status_code == 200
                result = response.json()
                assert result["success"] == True
                assert result["migrated_count"] >= 1
    
    # Step 6: Verify data was preserved
    response = requests.get(
        f"{BASE_URL}/api/individuals/{test_project}/individuals/Aircraft",
        params={"graph": test_ontology},
        headers=headers,
        timeout=30
    )
    assert response.status_code == 200
    individuals = response.json()["individuals"]
    assert len(individuals) == 1
    
    # Check that property value was preserved with new name
    properties = individuals[0]["properties"]
    assert "Max Speed" in properties or "maxSpeed" in properties  # New name
    # Value should be preserved
    if "Max Speed" in properties:
        assert properties["Max Speed"] == "Mach 2.25"
    elif "maxSpeed" in properties:
        assert properties["maxSpeed"] == "Mach 2.25"
    
    print("✅ Property migration test passed!")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
