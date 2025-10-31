"""
Test Class Rename Migration

Tests class renaming migration for individuals.
Verifies that when classes are renamed in ontology, individuals are preserved.

NOTE: This test is currently marked as XFAIL due to known issues with class renaming
and individual table updates. Changing a class name results in updates to lots of
individual tables, which is a complex operation that needs further work.
"""
import pytest
import requests
import json

BASE_URL = "http://localhost:8000"
TEST_USERNAME = "das_service"
TEST_PASSWORD = "das_service_2024!"

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
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
        json={"name": "Class Migration Test", "description": "Test project"},
        headers=headers
    )
    assert response.status_code == 200
    project_id = response.json()["project"]["project_id"]
    
    yield project_id
    
    # Cleanup: delete project
    requests.delete(f"{BASE_URL}/api/projects/{project_id}", headers=headers)

@pytest.fixture(scope="module")
def test_ontology(auth_token, test_project):
    """Create test ontology with Aircraft class"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    graph_iri = f"https://xma-adt.usnc.mil/projects/{test_project}/ontologies/testontology"
    
    # Create ontology with Aircraft class
    ontology_content = """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

<http://xma-adt.usnc.mil/projects/testproject/ontologies/testontology#Aircraft> rdf:type owl:Class ;
    rdfs:label "Aircraft" .

<http://xma-adt.usnc.mil/projects/testproject/ontologies/testontology#hasMaxSpeed> rdf:type owl:DatatypeProperty ;
    rdfs:label "has Max Speed" ;
    rdfs:domain <http://xma-adt.usnc.mil/projects/testproject/ontologies/testontology#Aircraft> .
"""
    
    response = requests.post(
        f"{BASE_URL}/api/ontology/save",
        params={"graph": graph_iri},
        data=ontology_content.encode('utf-8'),
        headers={**headers, "Content-Type": "text/turtle"}
    )
    assert response.status_code == 200
    
    yield graph_iri

@pytest.mark.xfail(reason="Class renaming updates many individual tables - complex operation needing further work")
def test_class_rename_migration(auth_token, test_project, test_ontology):
    """Test that renaming a class preserves individuals"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Step 1: Create individuals with the old class name
    create_data = {
        "name": "F-22 Raptor",
        "class_type": "Aircraft",
        "properties": {
            "has Max Speed": "Mach 2.25"
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/api/individuals/{test_project}/individuals/Aircraft",
        params={"graph": test_ontology},
        json=create_data,
        headers=headers
    )
    assert response.status_code == 200
    
    # Create second individual
    create_data2 = {
        "name": "F-35 Lightning",
        "class_type": "Aircraft",
        "properties": {
            "has Max Speed": "Mach 1.6"
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/api/individuals/{test_project}/individuals/Aircraft",
        params={"graph": test_ontology},
        json=create_data2,
        headers=headers
    )
    assert response.status_code == 200
    
    # Step 2: Verify individuals were created
    response = requests.get(
        f"{BASE_URL}/api/individuals/{test_project}/individuals/Aircraft",
        params={"graph": test_ontology},
        headers=headers
    )
    assert response.status_code == 200
    individuals = response.json()["individuals"]
    assert len(individuals) == 2
    
    # Step 3: Rename class in ontology (Aircraft -> Airplane)
    new_ontology_content = """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

<http://xma-adt.usnc.mil/projects/testproject/ontologies/testontology#Airplane> rdf:type owl:Class ;
    rdfs:label "Airplane" .

<http://xma-adt.usnc.mil/projects/testproject/ontologies/testontology#hasMaxSpeed> rdf:type owl:DatatypeProperty ;
    rdfs:label "has Max Speed" ;
    rdfs:domain <http://xma-adt.usnc.mil/projects/testproject/ontologies/testontology#Airplane> .
"""
    
    response = requests.post(
        f"{BASE_URL}/api/ontology/save",
        params={"graph": test_ontology},
        data=new_ontology_content.encode('utf-8'),
        headers={**headers, "Content-Type": "text/turtle"}
    )
    assert response.status_code == 200
    
    # Check for pending class migrations
    response_data = response.json()
    assert "pending_class_migrations" in response_data
    
    # Step 4: Apply class migration
    if response_data.get("pending_class_migrations"):
        for class_migration in response_data["pending_class_migrations"]:
            if class_migration["old_class_name"] == "Aircraft":
                migrate_data = {
                    "graph_iri": test_ontology,
                    "old_class_name": class_migration["old_class_name"],
                    "new_class_name": class_migration["new_class_name"]
                }
                
                response = requests.post(
                    f"{BASE_URL}/api/individuals/{test_project}/class-mappings/migrate",
                    json=migrate_data,
                    headers=headers
                )
                assert response.status_code == 200
                result = response.json()
                assert result["success"] == True
                assert result["migrated_count"] == 2  # Both individuals
    
    # Step 5: Verify individuals are still accessible with new class name
    response = requests.get(
        f"{BASE_URL}/api/individuals/{test_project}/individuals/Airplane",
        params={"graph": test_ontology},
        headers=headers
    )
    assert response.status_code == 200
    individuals = response.json()["individuals"]
    assert len(individuals) == 2
    
    # Verify individuals are no longer accessible with old class name
    response = requests.get(
        f"{BASE_URL}/api/individuals/{test_project}/individuals/Aircraft",
        params={"graph": test_ontology},
        headers=headers
    )
    assert response.status_code == 200
    old_individuals = response.json()["individuals"]
    assert len(old_individuals) == 0
    
    # Verify data was preserved
    names = [ind["name"] for ind in individuals]
    assert "F-22 Raptor" in names
    assert "F-35 Lightning" in names
    
    print("✅ Class migration test passed!")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
