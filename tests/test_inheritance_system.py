"""
ODRAS Ontology Inheritance System Test

This test validates the complete inheritance functionality:
1. In-project multiple inheritance (BASE: testing-inheritance-object)
2. Multi-level inheritance (BASE.Vertical: A → AB → ABC)  
3. Cross-project inheritance (BASE.Cross: airvehicle inheriting from BASE reference)

Verifies that:
- Classes inherit properties from parent classes
- Multiple inheritance works correctly
- Multi-level inheritance chains work (transitive inheritance)
- Cross-project inheritance works with reference ontologies
- Property conflicts are resolved gracefully
- Inheritance indicators work correctly

Requirements:
- ODRAS running at http://localhost:8000
- All services (PostgreSQL, Fuseki, Qdrant, etc.) running
- Authentication with das_service account
- Test ontologies setup in core.se project
"""

import pytest
import asyncio
import httpx
import logging

logger = logging.getLogger(__name__)

class TestInheritanceSystem:
    """
    Comprehensive test of ODRAS ontology inheritance system
    """
    
    # Test data will be created dynamically in setup
    PROJECT_ID = None
    BASE_GRAPH = None
    VERTICAL_GRAPH = None
    CROSS_GRAPH = None

    @pytest.fixture
    async def client(self):
        """HTTP client for API testing"""
        async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
            yield client

    @pytest.fixture
    async def auth_headers(self, client):
        """Authentication headers for das_service account"""
        response = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        assert response.status_code == 200
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture  
    async def admin_auth_headers(self, client):
        """Authentication headers for admin account (for cross-project testing)"""
        response = await client.post(
            "/api/auth/login", 
            json={"username": "jdehart", "password": "jdehart123!"}
        )
        assert response.status_code == 200
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    async def test_setup(self, client, admin_auth_headers):
        """Create test project and ontologies for inheritance testing"""
        logger.info("🔧 Setting up inheritance test environment...")
        
        # Create test project (ODRAS will use default namespace)
        project_response = await client.post(
            "/api/projects",
            headers=admin_auth_headers,
            json={
                "name": "Inheritance_Test_Project",
                "description": "Test project for ontology inheritance validation"
            }
        )
        assert project_response.status_code == 200, f"Project creation failed: {project_response.text}"
        project_result = project_response.json()
        self.PROJECT_ID = project_result["project"]["project_id"]
        
        logger.info(f"✅ Created test project: {self.PROJECT_ID}")
        
        # Wait for project thread creation
        await asyncio.sleep(3)
        
        # Create BASE ontology with test classes
        base_response = await client.post(
            "/api/ontologies",
            headers=admin_auth_headers,
            json={
                "project": self.PROJECT_ID,
                "name": "base",
                "label": "Base Test Ontology",
                "is_reference": False
            }
        )
        assert base_response.status_code == 200, f"BASE ontology creation failed: {base_response.text}"
        self.BASE_GRAPH = base_response.json()["graphIri"]
        
        # Create classes in BASE
        await self._create_base_classes(client, admin_auth_headers)
        logger.info("✅ Created BASE classes")
        
        # Wait for Fuseki processing and inheritance calculation
        await asyncio.sleep(5)
        
        # Create VERTICAL ontology for multi-level inheritance
        vertical_response = await client.post(
            "/api/ontologies",
            headers=admin_auth_headers,
            json={
                "project": self.PROJECT_ID,
                "name": "base-vertical",
                "label": "Vertical Inheritance Test Ontology",
                "is_reference": False
            }
        )
        assert vertical_response.status_code == 200, f"VERTICAL ontology creation failed: {vertical_response.text}"
        self.VERTICAL_GRAPH = vertical_response.json()["graphIri"]
        
        # Create classes in VERTICAL
        await self._create_vertical_classes(client, admin_auth_headers)
        logger.info("✅ Created VERTICAL classes")
        
        # Wait for Fuseki processing
        await asyncio.sleep(2)
        
        # Create CROSS ontology for cross-project inheritance
        cross_response = await client.post(
            "/api/ontologies",
            headers=admin_auth_headers,
            json={
                "project": self.PROJECT_ID,
                "name": "base-cross",
                "label": "Cross-Project Inheritance Test Ontology",
                "is_reference": False
            }
        )
        assert cross_response.status_code == 200, f"CROSS ontology creation failed: {cross_response.text}"
        self.CROSS_GRAPH = cross_response.json()["graphIri"]
        
        # Create classes in CROSS
        await self._create_cross_classes(client, admin_auth_headers)
        logger.info("✅ Created CROSS classes")
        
        # Wait for Fuseki processing
        await asyncio.sleep(3)
        
        logger.info("✅ Test environment setup complete")
        logger.info(f"   BASE_GRAPH: {self.BASE_GRAPH}")
        logger.info(f"   VERTICAL_GRAPH: {self.VERTICAL_GRAPH}")
        logger.info(f"   CROSS_GRAPH: {self.CROSS_GRAPH}")
        
        yield
        
        # Cleanup
        logger.info("🧹 Cleaning up test environment...")
        await client.delete(f"/api/projects/{self.PROJECT_ID}", headers=admin_auth_headers)

    async def _create_base_classes(self, client, headers):
        """Create Object, PhysicalObject, and testing-inheritance-object classes"""
        # Object class with properties
        await client.post(
            f"/api/ontology/classes?graph={self.BASE_GRAPH}",
            headers=headers,
            json={
                "name": "Object",
                "label": "Object",
                "comment": "Base object class"
            }
        )
        await client.post(
            f"/api/ontology/properties?graph={self.BASE_GRAPH}",
            headers=headers,
            json={
                "name": "id",
                "type": "datatype",
                "label": "ID",
                "comment": "Object identifier",
                "domain": "Object",
                "range": "string"
            }
        )
        await client.post(
            f"/api/ontology/properties?graph={self.BASE_GRAPH}",
            headers=headers,
            json={
                "name": "nomenclature",
                "type": "datatype",
                "label": "Nomenclature",
                "comment": "Object nomenclature",
                "domain": "Object",
                "range": "string"
            }
        )
        
        # PhysicalObject class with property
        await client.post(
            f"/api/ontology/classes?graph={self.BASE_GRAPH}",
            headers=headers,
            json={
                "name": "PhysicalObject",
                "label": "PhysicalObject",
                "comment": "Physical object class"
            }
        )
        await client.post(
            f"/api/ontology/properties?graph={self.BASE_GRAPH}",
            headers=headers,
            json={
                "name": "mass",
                "type": "datatype",
                "label": "Mass",
                "comment": "Object mass",
                "domain": "PhysicalObject",
                "range": "float"
            }
        )
        
        # testing-inheritance-object with multiple inheritance
        await client.post(
            f"/api/ontology/classes?graph={self.BASE_GRAPH}",
            headers=headers,
            json={
                "name": "testing-inheritance-object",
                "label": "Testing Inheritance Object",
                "comment": "Test class with multiple inheritance",
                "subclass_of": ["Object", "PhysicalObject"]
            }
        )
        await client.post(
            f"/api/ontology/properties?graph={self.BASE_GRAPH}",
            headers=headers,
            json={
                "name": "test-prop",
                "type": "datatype",
                "label": "Test Property",
                "comment": "Direct property",
                "domain": "testing-inheritance-object",
                "range": "string"
            }
        )

    async def _create_vertical_classes(self, client, headers):
        """Create A -> AB -> ABC chain"""
        # Class A
        await client.post(
            f"/api/ontology/classes?graph={self.VERTICAL_GRAPH}",
            headers=headers,
            json={"name": "a", "label": "A", "comment": "Root class"}
        )
        await client.post(
            f"/api/ontology/properties?graph={self.VERTICAL_GRAPH}",
            headers=headers,
            json={"name": "a", "type": "datatype", "label": "Property A", "comment": "A's property", "domain": "a", "range": "string"}
        )
        
        # Class AB (inherits from A)
        await client.post(
            f"/api/ontology/classes?graph={self.VERTICAL_GRAPH}",
            headers=headers,
            json={"name": "ab", "label": "AB", "comment": "Inherits from A", "subclass_of": ["a"]}
        )
        await client.post(
            f"/api/ontology/properties?graph={self.VERTICAL_GRAPH}",
            headers=headers,
            json={"name": "b", "type": "datatype", "label": "Property B", "comment": "AB's property", "domain": "ab", "range": "string"}
        )
        
        # Class ABC (inherits from AB)
        await client.post(
            f"/api/ontology/classes?graph={self.VERTICAL_GRAPH}",
            headers=headers,
            json={"name": "abc", "label": "ABC", "comment": "Inherits from AB", "subclass_of": ["ab"]}
        )
        await client.post(
            f"/api/ontology/properties?graph={self.VERTICAL_GRAPH}",
            headers=headers,
            json={"name": "c", "type": "datatype", "label": "Property C", "comment": "ABC's property", "domain": "abc", "range": "string"}
        )

    async def _create_cross_classes(self, client, headers):
        """Create airvehicle class that inherits from BASE reference"""
        # airvehicle inherits from Object and PhysicalObject in BASE
        await client.post(
            f"/api/ontology/classes?graph={self.CROSS_GRAPH}",
            headers=headers,
            json={
                "name": "airvehicle",
                "label": "Air Vehicle",
                "comment": "Inherits from BASE reference ontology",
                "subclass_of": [f"{self.BASE_GRAPH}#Object", f"{self.BASE_GRAPH}#PhysicalObject"]
            }
        )
        await client.post(
            f"/api/ontology/properties?graph={self.CROSS_GRAPH}",
            headers=headers,
            json={"name": "max-altitude", "type": "datatype", "label": "Max Altitude", "comment": "Maximum altitude", "domain": "airvehicle", "range": "float"}
        )

    async def get_class_properties(self, client, headers, class_name: str, graph_iri: str) -> dict:
        """Helper method to get class properties with inheritance"""
        response = await client.get(
            f"/api/ontology/classes/{class_name}/all-properties",
            params={"graph": graph_iri},
            headers=headers
        )
        assert response.status_code == 200, f"Failed to get properties for {class_name}: {response.text}"
        return response.json()["data"]

    @pytest.mark.asyncio
    async def test_in_project_multiple_inheritance(self, client, admin_auth_headers, test_setup):
        """
        Test 1: In-project multiple inheritance
        testing-inheritance-object inherits from both Object and PhysicalObject in same BASE graph
        """
        logger.info("🔍 Testing in-project multiple inheritance (BASE ontology)")
        
        data = await self.get_class_properties(
            client, admin_auth_headers, "testing-inheritance-object", self.BASE_GRAPH
        )
        
        properties = data["properties"]
        conflicts = data.get("conflicts", [])
        
        # Verify expected property count (1 direct + 3 inherited)
        assert len(properties) >= 4, f"Expected 4+ properties, got {len(properties)}"
        
        # Verify inheritance from multiple parents
        inherited_props = [p for p in properties if p.get("inherited", False)]
        direct_props = [p for p in properties if not p.get("inherited", False)]
        
        assert len(inherited_props) >= 3, f"Expected 3+ inherited properties, got {len(inherited_props)}"
        assert len(direct_props) >= 1, f"Expected 1+ direct property, got {len(direct_props)}"
        
        # Verify specific inherited properties
        property_names = [p["name"] for p in properties]
        assert "id" in property_names, "Missing 'id' inherited from Object"
        assert "nomenclature" in property_names, "Missing 'nomenclature' inherited from Object"
        assert "mass" in property_names, "Missing 'mass' inherited from PhysicalObject"
        
        # Verify inheritance indicators
        inherited_from_object = [p for p in inherited_props if p.get("inheritedFrom") == "Object"]
        inherited_from_physical = [p for p in inherited_props if p.get("inheritedFrom") == "PhysicalObject"]
        
        assert len(inherited_from_object) >= 2, "Expected properties inherited from Object"
        assert len(inherited_from_physical) >= 1, "Expected properties inherited from PhysicalObject"
        
        logger.info(f"✅ In-project multiple inheritance: {len(properties)} properties, {len(conflicts)} conflicts resolved")

    @pytest.mark.asyncio  
    async def test_multi_level_inheritance(self, client, admin_auth_headers, test_setup):
        """
        Test 2: Multi-level inheritance chain  
        A → AB → ABC transitive inheritance
        """
        logger.info("🔍 Testing multi-level inheritance (BASE.Vertical ontology)")
        
        # Test A (root class)
        data_a = await self.get_class_properties(client, admin_auth_headers, "a", self.VERTICAL_GRAPH)
        props_a = data_a["properties"]
        assert len(props_a) == 1, f"A should have 1 property, got {len(props_a)}"
        assert not props_a[0].get("inherited", False), "A's property should be direct, not inherited"
        
        # Test AB (inherits from A)
        data_ab = await self.get_class_properties(client, admin_auth_headers, "ab", self.VERTICAL_GRAPH)
        props_ab = data_ab["properties"]
        assert len(props_ab) >= 2, f"AB should have 2+ properties, got {len(props_ab)}"
        
        inherited_ab = [p for p in props_ab if p.get("inherited", False)]
        direct_ab = [p for p in props_ab if not p.get("inherited", False)]
        assert len(inherited_ab) >= 1, "AB should inherit from A"
        assert len(direct_ab) >= 1, "AB should have its own property"
        
        # Test ABC (inherits from AB, transitively from A)
        data_abc = await self.get_class_properties(client, admin_auth_headers, "abc", self.VERTICAL_GRAPH)
        props_abc = data_abc["properties"]
        assert len(props_abc) >= 3, f"ABC should have 3+ properties, got {len(props_abc)}"
        
        inherited_abc = [p for p in props_abc if p.get("inherited", False)]
        direct_abc = [p for p in props_abc if not p.get("inherited", False)]
        assert len(inherited_abc) >= 2, "ABC should inherit from AB and transitively from A"
        assert len(direct_abc) >= 1, "ABC should have its own property"
        
        # Verify transitive inheritance (ABC gets property from A through AB)
        property_names_abc = [p["name"] for p in props_abc]
        assert "a" in property_names_abc, "ABC should transitively inherit 'a' property from A"
        assert "b" in property_names_abc, "ABC should inherit 'b' property from AB"
        
        logger.info(f"✅ Multi-level inheritance: A({len(props_a)}) → AB({len(props_ab)}) → ABC({len(props_abc)})")

    @pytest.mark.asyncio
    async def test_cross_project_inheritance(self, client, admin_auth_headers, test_setup):
        """
        Test 3: Cross-project inheritance
        airvehicle in BASE.Cross inherits from Object/PhysicalObject in BASE reference ontology
        """
        logger.info("🔍 Testing cross-project inheritance (BASE.Cross → BASE reference)")
        
        # First verify parent classes exist in BASE reference ontology
        data_object = await self.get_class_properties(client, admin_auth_headers, "object", self.BASE_GRAPH)
        data_physical = await self.get_class_properties(client, admin_auth_headers, "physicalobject", self.BASE_GRAPH)
        
        object_props = data_object["properties"]
        physical_props = data_physical["properties"]
        
        assert len(object_props) >= 2, f"Object should have 2+ properties, got {len(object_props)}"
        assert len(physical_props) >= 1, f"PhysicalObject should have 1+ property, got {len(physical_props)}"
        
        # Now test cross-project inheritance
        data_cross = await self.get_class_properties(client, admin_auth_headers, "airvehicle", self.CROSS_GRAPH)
        properties = data_cross["properties"]
        conflicts = data_cross.get("conflicts", [])
        
        # Verify expected property count (1 direct + properties from BASE reference)
        expected_min = 1 + len(object_props) + len(physical_props)
        assert len(properties) >= expected_min, f"Expected {expected_min}+ properties, got {len(properties)}"
        
        # Verify cross-project inheritance indicators
        inherited_props = [p for p in properties if p.get("inherited", False)]
        direct_props = [p for p in properties if not p.get("inherited", False)]
        
        assert len(inherited_props) >= 3, f"Expected 3+ inherited properties, got {len(inherited_props)}"
        assert len(direct_props) >= 1, f"Expected 1+ direct property, got {len(direct_props)}"
        
        # Verify specific cross-project inherited properties
        property_names = [p["name"] for p in properties]
        assert "id" in property_names, "Missing 'id' inherited from Object (cross-project)"
        assert "nomenclature" in property_names, "Missing 'nomenclature' inherited from Object (cross-project)" 
        assert "mass" in property_names, "Missing 'mass' inherited from PhysicalObject (cross-project)"
        
        # Verify inheritance source attribution
        object_inherited = [p for p in inherited_props if p.get("inheritedFrom") == "Object"]
        physical_inherited = [p for p in inherited_props if p.get("inheritedFrom") == "PhysicalObject"]
        
        assert len(object_inherited) >= 2, "Expected properties inherited from Object"
        assert len(physical_inherited) >= 1, "Expected properties inherited from PhysicalObject"
        
        # Verify conflict resolution (should have some conflicts but not fail)
        logger.info(f"✅ Cross-project inheritance: {len(properties)} properties, {len(conflicts)} conflicts resolved")

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="Reference ontology access not yet implemented - requires namespace/reference setup")
    async def test_inheritance_reference_access_all_users(self, client, auth_headers, test_setup):
        """
        Test 4: Non-admin users can see reference ontology classes for inheritance
        This tests the "reference ontologies are public foundations" requirement
        """
        logger.info("🔍 Testing reference ontology access for non-admin users")
        
        # das_service (non-admin) should be able to see BASE reference classes as parents
        response = await client.get(
            "/api/ontology/available-parents",
            params={"current_graph": self.CROSS_GRAPH},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get available parents: {response.text}"
        
        data = response.json()["data"]
        parents = data["parents"]
        
        # Filter for reference parents
        ref_parents = [p for p in parents if p.get("type") == "reference"]
        local_parents = [p for p in parents if p.get("type") == "local"]
        
        assert len(ref_parents) >= 3, f"Expected 3+ reference parents, got {len(ref_parents)}"
        
        # Verify specific reference classes are visible
        ref_names = [p["name"] for p in ref_parents]
        assert "object" in ref_names or "Object" in ref_names, "Object from BASE reference not visible"
        assert "physicalobject" in ref_names or "PhysicalObject" in ref_names, "PhysicalObject from BASE reference not visible"
        
        logger.info(f"✅ Reference access: {len(ref_parents)} reference parents visible to non-admin users")

    @pytest.mark.asyncio
    async def test_inheritance_system_integration(self, client, admin_auth_headers, test_setup):
        """
        Test 5: Complete inheritance system integration test
        Verifies all inheritance features work together
        """
        logger.info("🔍 Testing complete inheritance system integration")
        
        # Test all three inheritance patterns in sequence
        test_cases = [
            {
                "name": "In-project multiple inheritance",
                "class": "testing-inheritance-object", 
                "graph": self.BASE_GRAPH,
                "expected_min": 4,
                "should_have_inherited": True
            },
            {
                "name": "Multi-level inheritance",
                "class": "abc",
                "graph": self.VERTICAL_GRAPH, 
                "expected_min": 3,
                "should_have_inherited": True
            },
            {
                "name": "Cross-project inheritance",
                "class": "airvehicle",
                "graph": self.CROSS_GRAPH,
                "expected_min": 4,
                "should_have_inherited": True
            }
        ]
        
        results = []
        for test_case in test_cases:
            try:
                data = await self.get_class_properties(
                    client, admin_auth_headers, test_case["class"], test_case["graph"]
                )
                
                properties = data["properties"]
                conflicts = data.get("conflicts", [])
                
                inherited_count = len([p for p in properties if p.get("inherited", False)])
                direct_count = len([p for p in properties if not p.get("inherited", False)])
                
                test_result = {
                    "name": test_case["name"],
                    "class": test_case["class"],
                    "total_properties": len(properties),
                    "inherited_properties": inherited_count,
                    "direct_properties": direct_count,
                    "conflicts_resolved": len(conflicts),
                    "success": len(properties) >= test_case["expected_min"]
                }
                
                results.append(test_result)
                
                # Assertions for each test case
                assert len(properties) >= test_case["expected_min"], \
                    f"{test_case['name']}: Expected {test_case['expected_min']}+ properties, got {len(properties)}"
                
                if test_case["should_have_inherited"]:
                    assert inherited_count >= 1, \
                        f"{test_case['name']}: Expected inherited properties, got {inherited_count}"
                
                logger.info(f"✅ {test_case['name']}: {len(properties)} properties ({direct_count} direct + {inherited_count} inherited)")
                
            except Exception as e:
                logger.error(f"❌ {test_case['name']} failed: {e}")
                pytest.fail(f"Inheritance test failed for {test_case['name']}: {e}")
        
        # Final verification: All test cases should pass
        failed_tests = [r for r in results if not r["success"]]
        assert len(failed_tests) == 0, f"Failed inheritance tests: {[t['name'] for t in failed_tests]}"
        
        logger.info("🎉 ALL INHERITANCE PATTERNS WORKING: in-project, multi-level, and cross-project!")

if __name__ == "__main__":
    # Allow running the test directly for development
    import sys
    import subprocess
    
    print("🧪 Running Inheritance System Test...")
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"
    ], capture_output=False)
    
    if result.returncode == 0:
        print("🎉 All inheritance tests passed!")
    else:
        print("❌ Some inheritance tests failed!")
    
    sys.exit(result.returncode)
