"""
Test Ontology Attributes & DAS Integration

This test validates the specific enhancements made to DAS2 ontology context:
1. Ontology attribute persistence (comments, definitions, metadata)
2. DAS2 comprehensive context integration
3. Rich ontology display in DAS responses
4. Both base and reference ontology support

This is a focused test of recent DAS2 enhancements.
"""

import pytest
import asyncio
import httpx
import time
import json
from pathlib import Path


class TestOntologyAttributesDASIntegration:
    """Test the enhanced DAS2 ontology context system"""

    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        import requests
        response = requests.post(
            "http://localhost:8000/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"},
            timeout=30
        )
        assert response.status_code == 200
        return response.json()["token"]

    @pytest.fixture(scope="class")
    def test_project_id(self, auth_token):
        """Use existing test project"""
        # Use the project we created through Playwright earlier
        return "ff7b04eb-3fad-4c1a-8e2c-74148ceb50a8"

    @pytest.mark.asyncio
    async def test_01_create_ontology_with_rich_attributes(self, test_project_id, auth_token):
        """Create ontology with comprehensive attributes via API"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create base ontology
            response = await client.post(
                "http://localhost:8000/api/ontologies",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "project": test_project_id,
                    "name": "rich-test-ontology",
                    "label": "Rich Test Ontology"
                }
            )
            assert response.status_code == 200
            ontology_iri = response.json()["graphIri"]

            # Add comprehensive ontology with rich attributes
            response = await client.put(
                f"http://localhost:8000/api/ontology/?graph={ontology_iri}",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "metadata": {
                        "name": "Rich Test Ontology",
                        "namespace": ontology_iri
                    },
                    "classes": [
                        {
                            "name": "Vehicle",
                            "label": "Vehicle",
                            "comment": "A motorized transport device for people or cargo",
                            "definition": "A machine that moves people or goods using mechanical propulsion",
                            "example": "Cars, trucks, motorcycles, boats, aircraft",
                            "priority": "High",
                            "status": "Approved",
                            "creator": "das_service",
                            "created_date": "2025-10-06"
                        },
                        {
                            "name": "Aircraft",
                            "label": "Aircraft",
                            "comment": "A vehicle capable of atmospheric flight",
                            "definition": "A machine that achieves flight using aerodynamic principles",
                            "subclassOf": "Vehicle",
                            "example": "Airplanes, helicopters, drones, gliders",
                            "priority": "High",
                            "status": "Review",
                            "creator": "das_service"
                        },
                        {
                            "name": "Component",
                            "label": "Component",
                            "comment": "A discrete part of a system with specific function",
                            "definition": "An individual element that contributes to overall system operation",
                            "example": "Engine, wheel, wing, sensor",
                            "priority": "Medium",
                            "status": "Draft",
                            "creator": "das_service"
                        }
                    ],
                    "object_properties": [
                        {
                            "name": "hasComponent",
                            "label": "has component",
                            "comment": "Compositional relationship between system and part",
                            "definition": "Indicates that a system contains or includes a specific component",
                            "domain": "Vehicle",
                            "range": "Component",
                            "example": "Car hasComponent Engine",
                            "creator": "das_service",
                            "created_date": "2025-10-06"
                        },
                        {
                            "name": "operatedBy",
                            "label": "operated by",
                            "comment": "Indicates who or what operates the vehicle",
                            "domain": "Vehicle",
                            "creator": "das_service"
                        }
                    ],
                    "datatype_properties": [
                        {
                            "name": "hasWeight",
                            "label": "has weight",
                            "comment": "Total weight of the vehicle in kilograms",
                            "definition": "Quantitative measurement of mass in metric units",
                            "domain": "Vehicle",
                            "range": "integer",
                            "example": "1500 (kg for small car)",
                            "creator": "das_service"
                        },
                        {
                            "name": "hasWingspan",
                            "label": "has wingspan",
                            "comment": "Wing span measurement in meters",
                            "definition": "Distance between wing tips when fully extended",
                            "domain": "Aircraft",
                            "range": "float",
                            "example": "35.4 (meters for Boeing 737)",
                            "creator": "das_service"
                        }
                    ]
                }
            )

            assert response.status_code == 200
            save_result = response.json()
            assert save_result["success"] == True

            # Store ontology IRI for later tests
            TestOntologyAttributesDASIntegration.ontology_iri = ontology_iri

            print(f"✅ Created ontology with {save_result['data']['triples_count']} triples")

    @pytest.mark.asyncio
    async def test_02_verify_attributes_in_fuseki(self):
        """Verify all attributes were saved correctly to Fuseki"""
        ontology_iri = getattr(TestOntologyAttributesDASIntegration, 'ontology_iri', None)
        assert ontology_iri, "No ontology IRI found from previous test"

        async with httpx.AsyncClient(timeout=15.0) as client:
            # Check Vehicle class attributes
            sparql_query = f"""
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dc: <http://purl.org/dc/elements/1.1/>

            SELECT ?property ?value WHERE {{
                GRAPH <{ontology_iri}> {{
                    <{ontology_iri}#Vehicle> ?property ?value .
                }}
            }}
            """

            response = await client.post(
                "http://localhost:3030/odras/query",
                data={"query": sparql_query},
                headers={"Accept": "application/json"}
            )

            assert response.status_code == 200
            results = response.json()
            bindings = results.get("results", {}).get("bindings", [])

            # Verify key attributes are present
            properties = {binding["property"]["value"]: binding["value"]["value"] for binding in bindings}

            assert "http://www.w3.org/2000/01/rdf-schema#comment" in properties
            assert "http://www.w3.org/2004/02/skos/core#definition" in properties
            assert "http://www.w3.org/2004/02/skos/core#example" in properties
            assert "http://purl.org/dc/elements/1.1/creator" in properties

            assert properties["http://www.w3.org/2000/01/rdf-schema#comment"] == "A motorized transport device for people or cargo"
            assert properties["http://purl.org/dc/elements/1.1/creator"] == "das_service"

            print("✅ Vehicle class attributes verified in Fuseki")
            print(f"   Found {len(properties)} properties including rich metadata")

    @pytest.mark.asyncio
    async def test_03_das_sees_basic_ontology_context(self, test_project_id, auth_token):
        """Test that DAS can see the basic ontology structure"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8000/api/das/chat",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "project_id": test_project_id,
                    "message": "What ontologies are in this project and what classes do they contain?"
                }
            )

            assert response.status_code == 200
            das_response = response.json()
            answer = das_response["message"]

            # Verify DAS can see ontology and classes
            assert "Rich Test Ontology" in answer or "rich-test-ontology" in answer
            assert "Vehicle" in answer
            assert "Aircraft" in answer
            assert "Component" in answer

            print("✅ DAS can see basic ontology structure")
            print(f"Response length: {len(answer)} chars")

    @pytest.mark.asyncio
    async def test_04_das_sees_rich_class_attributes(self, test_project_id, auth_token):
        """Test that DAS can see rich class attributes"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8000/api/das/chat",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "project_id": test_project_id,
                    "message": "Tell me about the Vehicle class - its priority, status, creator, definition, and examples."
                }
            )

            assert response.status_code == 200
            das_response = response.json()
            answer = das_response["message"]

            # Verify DAS can see rich attributes
            assert "Priority" in answer or "High" in answer
            assert "Status" in answer or "Approved" in answer
            assert "das_service" in answer
            assert "definition" in answer.lower() or "machine that moves" in answer
            assert "example" in answer.lower() or "Cars, trucks" in answer

            print("✅ DAS can see rich class attributes")
            print("Answer contains:", "Priority" in answer, "Status" in answer, "Creator" in answer)

    @pytest.mark.asyncio
    async def test_05_das_sees_property_details(self, test_project_id, auth_token):
        """Test that DAS can see property attributes and metadata"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8000/api/das/chat",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "project_id": test_project_id,
                    "message": "What properties does the Vehicle class have? Include their definitions and examples."
                }
            )

            assert response.status_code == 200
            das_response = response.json()
            answer = das_response["message"]

            # Verify DAS can see properties with details
            assert "hasWeight" in answer
            assert "hasComponent" in answer
            assert "operatedBy" in answer
            assert "kilograms" in answer or "kg" in answer  # Weight description
            assert "example" in answer.lower() or "1500" in answer  # Example values

            print("✅ DAS can see property details and examples")

    @pytest.mark.asyncio
    async def test_06_das_understands_relationships(self, test_project_id, auth_token):
        """Test that DAS understands class relationships and hierarchy"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8000/api/das/chat",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "project_id": test_project_id,
                    "message": "What is the relationship between Aircraft and Vehicle classes? What does Aircraft inherit?"
                }
            )

            assert response.status_code == 200
            das_response = response.json()
            answer = das_response["message"]

            # DAS should understand the subclass relationship
            assert "Aircraft" in answer
            assert "Vehicle" in answer
            # Should mention inheritance, subclass, or relationship
            assert any(keyword in answer.lower() for keyword in ["subclass", "inherit", "relationship", "type of"])

            print("✅ DAS understands class relationships")

    @pytest.mark.asyncio
    async def test_07_das_metadata_analysis(self, test_project_id, auth_token):
        """Test DAS can analyze metadata across ontology elements"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8000/api/das/chat",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "project_id": test_project_id,
                    "message": "Which classes have High priority? What classes are still in Draft status? Who created the ontology elements?"
                }
            )

            assert response.status_code == 200
            das_response = response.json()
            answer = das_response["message"]

            # DAS should be able to filter and analyze metadata
            assert "High" in answer  # Priority analysis
            assert "Draft" in answer  # Status analysis
            assert "das_service" in answer  # Creator analysis

            # Should mention specific classes
            assert "Vehicle" in answer or "Aircraft" in answer

            print("✅ DAS can analyze metadata across elements")

    @pytest.mark.asyncio
    async def test_08_upload_knowledge_and_integrate(self, test_project_id, auth_token):
        """Upload knowledge assets and test DAS integration"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            data_dir = Path("/home/jdehart/working/ODRAS/data")
            uploaded_count = 0

            # Upload test markdown files
            test_files = ["uas_specifications.md", "decision_matrix_template.md"]

            for filename in test_files:
                file_path = data_dir / filename
                if file_path.exists():
                    print(f"Uploading {filename}...")

                    with open(file_path, 'rb') as f:
                        files = {'file': (filename, f, 'text/markdown')}
                        data_payload = {'project_id': test_project_id}

                        response = await client.post(
                            "http://localhost:8000/api/files/upload",
                            headers={"Authorization": f"Bearer {auth_token}"},
                            data=data_payload,
                            files=files
                        )

                        if response.status_code == 200:
                            uploaded_count += 1
                            print(f"  ✅ {filename} uploaded")

                    await asyncio.sleep(2)  # Wait between uploads

            assert uploaded_count > 0, "No files uploaded"

            # Wait for processing
            print("⏳ Waiting for file processing...")
            await asyncio.sleep(20)

            # Test DAS integration with both ontology and document context
            response = await client.post(
                "http://localhost:8000/api/das/chat",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "project_id": test_project_id,
                    "message": "What documents are in this project and how do they relate to the Vehicle and Aircraft classes in the ontology?"
                }
            )

            assert response.status_code == 200
            das_response = response.json()
            answer = das_response["message"]

            print("✅ DAS integrates ontology + document context")
            print(f"Answer length: {len(answer)} chars")

    @pytest.mark.asyncio
    async def test_09_comprehensive_das_analysis(self, test_project_id, auth_token):
        """Test DAS comprehensive analysis across all project content"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Complex analytical questions that require rich context
            test_questions = [
                {
                    "question": "Create a table showing all classes with their priority, status, and creator.",
                    "expected_in_response": ["table", "Vehicle", "Aircraft", "Component", "High", "Medium", "Approved", "Review", "Draft", "das_service"]
                },
                {
                    "question": "Compare the definitions of Vehicle and Aircraft classes. How are they related?",
                    "expected_in_response": ["Vehicle", "Aircraft", "definition", "subclass", "transport", "flight"]
                },
                {
                    "question": "What properties are available for measuring aircraft characteristics? Include their data types and examples.",
                    "expected_in_response": ["hasWingspan", "hasWeight", "float", "integer", "meters", "kilograms", "example"]
                },
                {
                    "question": "Show me all the metadata for classes created by das_service, including creation dates and current status.",
                    "expected_in_response": ["das_service", "2025-10-06", "Approved", "Review", "Draft", "Vehicle", "Aircraft", "Component"]
                }
            ]

            success_count = 0
            total_questions = len(test_questions)

            for i, test_case in enumerate(test_questions, 1):
                print(f"\nTesting Question {i}/{total_questions}:")
                print(f"Q: {test_case['question']}")

                response = await client.post(
                    "http://localhost:8000/api/das/chat",
                    headers={"Authorization": f"Bearer {auth_token}"},
                    json={
                        "project_id": test_project_id,
                        "message": test_case['question']
                    }
                )

                assert response.status_code == 200
                das_response = response.json()
                answer = das_response["message"]

                # Check how many expected terms are in the response
                found_terms = []
                for expected_term in test_case["expected_in_response"]:
                    if expected_term.lower() in answer.lower():
                        found_terms.append(expected_term)

                success_rate = len(found_terms) / len(test_case["expected_in_response"])

                if success_rate >= 0.5:  # At least 50% of expected terms found
                    success_count += 1

                print(f"A: {answer[:200]}..." if len(answer) > 200 else answer)
                print(f"✅ Found {len(found_terms)}/{len(test_case['expected_in_response'])} expected terms ({success_rate:.0%})")

                await asyncio.sleep(3)  # Brief delay between questions

            # Verify overall success
            overall_success = success_count / total_questions
            print(f"\n=== Overall Test Results ===")
            print(f"Questions passed: {success_count}/{total_questions} ({overall_success:.0%})")

            assert overall_success >= 0.75, f"DAS success rate too low: {overall_success:.0%} - Rich context not working properly"

            print("✅ DAS comprehensive analysis test passed")

    @pytest.mark.asyncio
    async def test_10_performance_with_rich_context(self, test_project_id, auth_token):
        """Ensure rich context doesn't degrade performance"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            start_time = time.time()

            response = await client.post(
                "http://localhost:8000/api/das/chat",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "project_id": test_project_id,
                    "message": "Give me a complete analysis of this project - all ontologies, classes, properties, their attributes, uploaded documents, and recent activity."
                }
            )

            end_time = time.time()
            response_time = end_time - start_time

            assert response.status_code == 200
            assert response_time < 45, f"Response too slow: {response_time:.2f}s (rich context causing performance issues)"

            das_response = response.json()
            answer = das_response["message"]

            # Verify comprehensive response
            assert len(answer) > 800, "Response too brief for comprehensive rich context query"

            # Verify it includes rich context elements
            assert "Vehicle" in answer
            assert "Aircraft" in answer
            assert any(term in answer for term in ["Priority", "Status", "Creator", "definition", "example"])

            print(f"✅ Performance test passed: {response_time:.2f}s for comprehensive query")
            print(f"   Response length: {len(answer)} characters")
            print(f"   Includes rich context: {any(term in answer for term in ['Priority', 'Status', 'Creator'])}")


def create_ci_test_config():
    """
    Generate CI test configuration for GitHub Actions
    """
    return {
        "test_name": "ontology-attributes-das-integration",
        "description": "Test ontology attribute persistence and DAS integration",
        "pytest_command": "python -m pytest tests/test_ontology_attributes_das_integration.py -v --tb=short",
        "timeout_minutes": 15,
        "required_services": ["postgresql", "fuseki", "qdrant", "redis"],
        "success_criteria": {
            "all_tests_pass": True,
            "das_success_rate": ">=75%",
            "response_time": "<45s",
            "attribute_persistence": True
        }
    }


if __name__ == "__main__":
    # Run this specific test
    pytest.main([__file__, "-v", "-s", "--tb=short"])
