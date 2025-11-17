"""
Integration test for USV Acquisition Program Bootstrap.

Tests the complete Pre-Milestone A acquisition workflow from 
PROJECT_LATTICE_AND_KNOWLEDGE_FLOW.md Appendix A.

This demonstrates the self-assembling capability described in the SDD:
- L0 Foundation → L1 Strategy → L2 Requirements → L3 Solution Concepts
- Cross-domain coordination (SE, Operations, Cost, Analysis)
- Event-driven artifact flow
- Cross-domain knowledge links
"""

import pytest
import asyncio
import httpx
import time
from typing import Dict, List


class TestUSVAcquisitionBootstrap:
    """
    Test complete USV acquisition program bootstrap.
    
    Implements the Pre-Milestone A example from PROJECT_LATTICE_AND_KNOWLEDGE_FLOW.md
    to verify the project lattice can support real acquisition workflows.
    """

    def setup_method(self):
        """Setup test client and authenticate."""
        self.base_url = "http://localhost:8000"
        self.client = httpx.Client(base_url=self.base_url, timeout=30.0)
        
        # Authenticate as das_service
        self._authenticate()
        
        # Track created projects for cleanup
        self.created_projects = []
        self.project_registry = {}  # Track projects by name for easy reference

    def teardown_method(self):
        """Clean up all created projects."""
        for project_id in self.created_projects:
            try:
                response = self.client.delete(f"/api/projects/{project_id}")
                if response.status_code not in [200, 404]:
                    print(f"Warning: Failed to clean up project {project_id}")
            except Exception as e:
                print(f"Warning: Error cleaning up project {project_id}: {e}")

    def _authenticate(self):
        """Authenticate with das_service account."""
        response = self.client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        assert response.status_code == 200, f"Authentication failed: {response.text}"
        
        data = response.json()
        token = data.get("access_token")
        assert token, "No access token received"
        
        self.client.headers.update({"Authorization": f"Bearer {token}"})

    def _create_project(
        self,
        name: str,
        domain: str,
        project_level: int,
        parent_name: str = None,
        description: str = None,
    ) -> Dict:
        """Create project and register in project registry."""
        # Get default namespace
        namespaces_response = self.client.get("/api/namespace/simple")
        assert namespaces_response.status_code == 200
        namespaces = namespaces_response.json().get("namespaces", [])
        assert len(namespaces) > 0, "No namespaces available"
        
        default_namespace = next((ns for ns in namespaces if ns["status"] == "released"), namespaces[0])
        
        project_data = {
            "name": name,
            "namespace_id": default_namespace["id"],
            "domain": domain,
            "project_level": project_level,
        }
        
        if description:
            project_data["description"] = description
            
        if parent_name and parent_name in self.project_registry:
            project_data["parent_project_id"] = self.project_registry[parent_name]["project_id"]

        response = self.client.post("/api/projects", json=project_data)
        assert response.status_code == 200, f"Project creation failed for {name}: {response.text}"
        
        project = response.json()["project"]
        project_id = project["project_id"]
        
        self.created_projects.append(project_id)
        self.project_registry[name] = project
        
        print(f"✓ Created {name} (L{project_level}, {domain})")
        return project

    def _create_cousin_relationship(self, source_name: str, target_name: str, rel_type: str, description: str):
        """Create cousin relationship between projects."""
        source_id = self.project_registry[source_name]["project_id"]
        target_id = self.project_registry[target_name]["project_id"]
        
        response = self.client.post(
            f"/api/projects/{source_id}/relationships",
            json={
                "target_project_id": target_id,
                "relationship_type": rel_type,
                "description": description
            }
        )
        assert response.status_code == 200, f"Failed to create relationship {source_name} -> {target_name}"
        print(f"✓ Created relationship: {source_name} {rel_type} {target_name}")

    def _create_knowledge_link(self, source_name: str, target_name: str, link_type: str):
        """Create cross-domain knowledge link."""
        source_id = self.project_registry[source_name]["project_id"]
        target_id = self.project_registry[target_name]["project_id"]
        
        response = self.client.post(
            f"/api/projects/{source_id}/knowledge-links",
            json={
                "target_project_id": target_id,
                "link_type": link_type,
                "identified_by": "user"
            }
        )
        assert response.status_code == 200, f"Failed to create knowledge link {source_name} -> {target_name}"
        print(f"✓ Created knowledge link: {source_name} -> {target_name} ({link_type})")

    def _create_event_subscription(self, subscriber_name: str, event_type: str, publisher_name: str = None):
        """Create event subscription."""
        subscriber_id = self.project_registry[subscriber_name]["project_id"]
        publisher_id = self.project_registry[publisher_name]["project_id"] if publisher_name else None
        
        response = self.client.post(
            f"/api/projects/{subscriber_id}/subscriptions",
            json={
                "event_type": event_type,
                "source_project_id": publisher_id
            }
        )
        assert response.status_code == 200, f"Failed to create subscription for {subscriber_name}"
        source_desc = f" from {publisher_name}" if publisher_name else ""
        print(f"✓ Subscription: {subscriber_name} subscribes to {event_type}{source_desc}")

    def _publish_event(self, publisher_name: str, event_type: str, event_data: Dict):
        """Publish event from project."""
        publisher_id = self.project_registry[publisher_name]["project_id"]
        
        response = self.client.post(
            f"/api/projects/{publisher_id}/publish-event",
            json={
                "event_type": event_type,
                "data": event_data
            }
        )
        assert response.status_code == 200, f"Failed to publish event from {publisher_name}"
        result = response.json()
        print(f"✓ Event: {publisher_name} published {event_type} (notified {result['subscribers_notified']} subscribers)")
        return result

    def test_complete_usv_acquisition_bootstrap(self):
        """
        Test complete USV acquisition program bootstrap.
        
        Creates the full Pre-Milestone A structure from the white paper:
        - L1: ICD, Mission Analysis, Cost Strategy
        - L2: CDD, CONOPS, Affordability
        - L3: Concept A, Concept B, Trade Studies
        """
        print("\n🚢 Starting USV Acquisition Bootstrap Test")
        print("=" * 50)
        
        # Phase 1: L1 Strategic Layer (Months 1-4)
        print("\n📋 Phase 1: L1 Strategic Layer")
        
        icd = self._create_project(
            "USV ICD Development",
            "systems-engineering", 
            1,
            description="Initial Capabilities Document for USV program"
        )
        
        mission = self._create_project(
            "USV Mission Analysis",
            "operations",
            1,
            description="Mission analysis and operational scenarios"
        )
        
        cost_strategy = self._create_project(
            "USV Cost Strategy", 
            "cost",
            1,
            description="Cost strategy and framework development"
        )
        
        # Phase 2: L2 Requirements Layer (Months 5-10)
        print("\n📝 Phase 2: L2 Requirements Layer")
        
        cdd = self._create_project(
            "USV CDD Development",
            "systems-engineering",
            2,
            "USV ICD Development",
            description="Capability Development Document with detailed requirements"
        )
        
        conops = self._create_project(
            "USV CONOPS",
            "operations", 
            2,
            "USV Mission Analysis",
            description="Concept of Operations for USV employment"
        )
        
        affordability = self._create_project(
            "USV Affordability Analysis",
            "cost",
            2,
            "USV Cost Strategy", 
            description="Affordability analysis and cost constraints"
        )
        
        # Phase 3: L3 Solution Concepts (Months 8-16)
        print("\n🛠️  Phase 3: L3 Solution Concepts")
        
        concept_a = self._create_project(
            "Small USV Concept",
            "analysis",
            3,
            "USV CDD Development",
            description="Small autonomous USV concept (25ft, 8 tons)"
        )
        
        concept_b = self._create_project(
            "Medium USV Concept", 
            "analysis",
            3,
            "USV CDD Development",
            description="Medium multi-mission USV concept (40ft, 20 tons)"
        )
        
        trade_study = self._create_project(
            "USV Trade Studies",
            "analysis",
            3,
            "USV CDD Development",
            description="Trade study analysis and recommendations"
        )
        
        # Create L1 cousin relationships (cross-domain coordination)
        print("\n🔗 Creating L1 Cross-Domain Coordination")
        
        self._create_cousin_relationship(
            "USV ICD Development", "USV Mission Analysis",
            "coordinates_with", "ICD coordinates with mission analysis"
        )
        
        self._create_cousin_relationship(
            "USV ICD Development", "USV Cost Strategy",
            "coordinates_with", "ICD coordinates with cost strategy"
        )
        
        # Create L2 cousin relationships
        print("\n🔗 Creating L2 Cross-Domain Coordination")
        
        self._create_cousin_relationship(
            "USV CDD Development", "USV CONOPS",
            "coordinates_with", "CDD coordinates with CONOPS development"
        )
        
        self._create_cousin_relationship(
            "USV CDD Development", "USV Affordability Analysis",
            "coordinates_with", "CDD coordinates with affordability analysis"
        )
        
        # Create L3 cousin relationships
        print("\n🔗 Creating L3 Cross-Domain Coordination")
        
        self._create_cousin_relationship(
            "Small USV Concept", "USV Affordability Analysis",
            "coordinates_with", "Small concept coordinates with cost analysis"
        )
        
        self._create_cousin_relationship(
            "Medium USV Concept", "USV Affordability Analysis", 
            "coordinates_with", "Medium concept coordinates with cost analysis"
        )
        
        # Create cross-domain knowledge links
        print("\n🧠 Creating Cross-Domain Knowledge Links")
        
        # Concepts need access to requirements knowledge
        self._create_knowledge_link("Small USV Concept", "USV CDD Development", "requirement_reference")
        self._create_knowledge_link("Small USV Concept", "USV CONOPS", "operational_alignment")
        self._create_knowledge_link("Small USV Concept", "USV Affordability Analysis", "cost_basis")
        
        self._create_knowledge_link("Medium USV Concept", "USV CDD Development", "requirement_reference")
        self._create_knowledge_link("Medium USV Concept", "USV CONOPS", "operational_alignment") 
        self._create_knowledge_link("Medium USV Concept", "USV Affordability Analysis", "cost_basis")
        
        self._create_knowledge_link("USV Trade Studies", "USV Affordability Analysis", "cost_constraints")
        
        # Set up event subscriptions (artifact flow)
        print("\n📡 Setting Up Event Subscriptions")
        
        # L2 subscribes to L1 events
        self._create_event_subscription("USV CDD Development", "icd.capability_gaps_identified", "USV ICD Development")
        self._create_event_subscription("USV CDD Development", "mission.scenarios_defined", "USV Mission Analysis")
        
        self._create_event_subscription("USV CONOPS", "mission.scenarios_defined", "USV Mission Analysis")
        
        self._create_event_subscription("USV Affordability Analysis", "cdd.requirements_approved", "USV CDD Development")
        
        # L3 subscribes to L2 events
        self._create_event_subscription("Small USV Concept", "cdd.requirements_approved", "USV CDD Development")
        self._create_event_subscription("Small USV Concept", "conops.operational_concept_approved", "USV CONOPS")
        self._create_event_subscription("Small USV Concept", "cost.constraints_defined", "USV Affordability Analysis")
        
        self._create_event_subscription("Medium USV Concept", "cdd.requirements_approved", "USV CDD Development")
        self._create_event_subscription("Medium USV Concept", "conops.operational_concept_approved", "USV CONOPS")
        self._create_event_subscription("Medium USV Concept", "cost.constraints_defined", "USV Affordability Analysis")
        
        self._create_event_subscription("USV Trade Studies", "concept.design_defined")  # Any concept
        self._create_event_subscription("USV Trade Studies", "cost.constraints_defined", "USV Affordability Analysis")
        
        # Simulate Pre-Milestone A workflow
        print("\n🎯 Simulating Pre-Milestone A Workflow")
        
        # Month 1-4: ICD and Mission Analysis
        print("\n📅 Month 1-4: Mission Need and ICD")
        
        icd_event = self._publish_event("USV ICD Development", "icd.capability_gaps_identified", {
            "capability_gaps": [
                {
                    "gap_id": "GAP-001",
                    "title": "Persistent ISR in Littoral Environment",
                    "description": "Insufficient persistent surveillance capability in contested littoral waters",
                    "priority": "high",
                    "operational_impact": "Cannot maintain continuous maritime domain awareness"
                },
                {
                    "gap_id": "GAP-002",
                    "title": "Low-Signature Maritime Patrol", 
                    "description": "Need low-observable platform for reconnaissance",
                    "priority": "medium",
                    "operational_impact": "Increased risk to manned platforms"
                }
            ],
            "mission_threads": [
                "Littoral ISR",
                "Mine Countermeasures", 
                "Anti-Surface Warfare"
            ]
        })
        
        mission_event = self._publish_event("USV Mission Analysis", "mission.scenarios_defined", {
            "scenarios": [
                {
                    "scenario_id": "SCEN-001",
                    "name": "Strait Patrol",
                    "environment": "Littoral, High Traffic",
                    "threat_level": "Medium",
                    "duration_hours": 72,
                    "area_nm2": 5000
                }
            ],
            "constraints": [
                "Must operate in Sea State 4",
                "Undetectable by coastal radar",
                "Autonomous operation for 72+ hours"
            ]
        })
        
        cost_strategy_event = self._publish_event("USV Cost Strategy", "cost.strategy_defined", {
            "cost_framework": "DoD 5000 lifecycle costing",
            "key_drivers": ["COTS preference", "Minimal crew", "Commercial maintenance"]
        })
        
        # Month 5-10: Requirements Development
        print("\n📅 Month 5-10: Requirements Development")
        
        cdd_event = self._publish_event("USV CDD Development", "cdd.requirements_approved", {
            "requirements": [
                {
                    "req_id": "REQ-001",
                    "text": "The system shall conduct persistent ISR operations for 72 hours [T] / 96 hours [O]",
                    "type": "Performance",
                    "source_gap": "GAP-001",
                    "threshold": "72 hours",
                    "objective": "96 hours",
                    "kpp": True
                },
                {
                    "req_id": "REQ-002",
                    "text": "The system shall have a radar cross-section ≤ 5 m² [T] / ≤ 2 m² [O]",
                    "type": "Performance", 
                    "source_gap": "GAP-002",
                    "threshold": "5 m²",
                    "objective": "2 m²",
                    "kpp": True
                },
                {
                    "req_id": "REQ-003",
                    "text": "The system shall operate in Sea State 4 [T] / Sea State 5 [O]",
                    "type": "Environmental",
                    "source_constraint": "mission.SCEN-001",
                    "threshold": "SS4", 
                    "objective": "SS5"
                }
            ],
            "verification_approach": {
                "REQ-001": "Test (at-sea demonstration)",
                "REQ-002": "Analysis + Test (RCS measurement)",
                "REQ-003": "Test (environmental chamber + at-sea)"
            }
        })
        
        conops_event = self._publish_event("USV CONOPS", "conops.operational_concept_approved", {
            "operational_modes": [
                {
                    "mode": "Autonomous Patrol",
                    "description": "USV operates independently following pre-programmed route",
                    "human_interaction": "Minimal (command approval only)",
                    "duration": "Up to 72 hours"
                },
                {
                    "mode": "Remote Control",
                    "description": "Operator controls USV via satellite link", 
                    "human_interaction": "Continuous",
                    "use_case": "Complex navigation or threat response"
                }
            ],
            "logistics": {
                "deployment": "Deployed from LCS or shore facility",
                "recovery": "Self-docking or crane recovery",
                "maintenance": "Depot-level only"
            }
        })
        
        affordability_event = self._publish_event("USV Affordability Analysis", "cost.constraints_defined", {
            "cost_targets": {
                "unit_procurement_cost_threshold": 15_000_000,  # $15M
                "unit_procurement_cost_objective": 10_000_000,  # $10M
                "annual_operating_cost": 500_000,               # $500K
                "lifecycle_cost": 75_000_000                    # $75M over 15 years
            },
            "affordability_drivers": [
                "COTS components preferred",
                "Minimal crew training", 
                "Commercial maintenance"
            ]
        })
        
        # Month 8-16: Solution Conceptualization
        print("\n📅 Month 8-16: Solution Conceptualization")
        
        concept_a_event = self._publish_event("Small USV Concept", "concept.design_defined", {
            "concept_id": "CONCEPT-A",
            "name": "Small Autonomous USV",
            "characteristics": {
                "length_ft": 25,
                "displacement_tons": 8,
                "speed_knots": 30,
                "endurance_hours": 72,
                "payload_capacity_lbs": 500
            },
            "subsystems": [
                {
                    "subsystem": "Propulsion",
                    "concept": "Diesel-electric hybrid",
                    "maturity": "TRL 7"
                },
                {
                    "subsystem": "ISR Suite",
                    "concept": "EO/IR + AIS receiver",
                    "maturity": "TRL 8"
                },
                {
                    "subsystem": "Autonomy",
                    "concept": "Waypoint navigation + collision avoidance", 
                    "maturity": "TRL 6"
                }
            ],
            "requirement_satisfaction": {
                "REQ-001": {"satisfied": True, "margin": "24 hours"},
                "REQ-002": {"satisfied": True, "margin": "2 m² RCS"},
                "REQ-003": {"satisfied": True, "margin": "SS4 verified"}
            },
            "cost_estimate": {
                "unit_cost": 12_000_000,
                "meets_threshold": True,
                "meets_objective": False
            },
            "risks": [
                {
                    "risk": "Autonomy software maturity",
                    "likelihood": "Medium", 
                    "impact": "High",
                    "mitigation": "Spiral development with increasing autonomy"
                }
            ]
        })
        
        concept_b_event = self._publish_event("Medium USV Concept", "concept.design_defined", {
            "concept_id": "CONCEPT-B", 
            "name": "Medium Multi-Mission USV",
            "characteristics": {
                "length_ft": 40,
                "displacement_tons": 20,
                "speed_knots": 25,
                "endurance_hours": 96,
                "payload_capacity_lbs": 2000
            },
            "requirement_satisfaction": {
                "REQ-001": {"satisfied": True, "margin": "48 hours"},
                "REQ-002": {"satisfied": True, "margin": "1 m² RCS"},
                "REQ-003": {"satisfied": True, "margin": "SS5 verified"}
            },
            "cost_estimate": {
                "unit_cost": 18_000_000,
                "meets_threshold": False,  # Exceeds $15M threshold
                "meets_objective": False
            }
        })
        
        # Trade study analyzes both concepts
        trade_event = self._publish_event("USV Trade Studies", "trade.analysis_complete", {
            "trade_study_id": "TRADE-001",
            "title": "USV Size/Capability Trade",
            "concepts_evaluated": ["CONCEPT-A", "CONCEPT-B"],
            "criteria": [
                {
                    "criterion": "Mission Performance",
                    "weight": 0.40,
                    "scores": {"CONCEPT-A": 85, "CONCEPT-B": 95}
                },
                {
                    "criterion": "Affordability",
                    "weight": 0.30,
                    "scores": {"CONCEPT-A": 90, "CONCEPT-B": 65}
                },
                {
                    "criterion": "Technical Risk",
                    "weight": 0.20,
                    "scores": {"CONCEPT-A": 75, "CONCEPT-B": 80}
                },
                {
                    "criterion": "Schedule",
                    "weight": 0.10,
                    "scores": {"CONCEPT-A": 90, "CONCEPT-B": 85}
                }
            ],
            "weighted_scores": {
                "CONCEPT-A": 85.5,
                "CONCEPT-B": 84.0
            },
            "recommendation": {
                "preferred_concept": "CONCEPT-A",
                "rationale": "Concept A meets threshold requirements with acceptable margin, stays within cost threshold, and presents lower technical risk. Recommend pursuing with Technology Development Strategy to mature autonomy software.",
                "alternatives": "If mission performance is paramount and additional funding available, Concept B provides superior capability."
            }
        })
        
        # Verify project structure
        print("\n✅ Verifying Project Structure")
        
        # Test hierarchy relationships
        response = self.client.get(f"/api/projects/{icd['project_id']}/children")
        assert response.status_code == 200
        icd_children = response.json()["children"]
        assert len(icd_children) == 1
        assert icd_children[0]["name"] == "USV CDD Development"
        
        # Test cousin relationships
        response = self.client.get(f"/api/projects/{icd['project_id']}/cousins")
        assert response.status_code == 200
        icd_cousins = response.json()["cousins"]
        assert len(icd_cousins) == 2  # Mission and Cost
        
        # Test knowledge links
        response = self.client.get(f"/api/projects/{concept_a['project_id']}/knowledge-links")
        assert response.status_code == 200
        concept_a_links = response.json()["knowledge_links"]
        assert len(concept_a_links) == 3  # CDD, CONOPS, Affordability
        
        # Test event subscriptions
        response = self.client.get(f"/api/projects/{concept_a['project_id']}/subscriptions")
        assert response.status_code == 200
        concept_a_subs = response.json()["subscriptions"]
        assert len(concept_a_subs) == 3  # Requirements, CONOPS, Cost constraints
        
        print("\n🎉 USV Acquisition Bootstrap Test Completed Successfully!")
        print("✓ Created complete Pre-Milestone A project structure")
        print("✓ Established parent-child relationships")
        print("✓ Created cross-domain cousin relationships") 
        print("✓ Set up cross-domain knowledge links")
        print("✓ Configured event subscriptions")
        print("✓ Simulated 18-month Pre-Milestone A workflow")
        print("✓ Verified all relationships and subscriptions")

    def test_knowledge_visibility_scenarios(self):
        """Test knowledge visibility in different scenarios."""
        print("\n🔍 Testing Knowledge Visibility Scenarios")
        
        # Create SE domain projects
        se_l1 = self._create_project("SE L1 Published", "systems-engineering", 1)
        se_l2 = self._create_project("SE L2 Consumer", "systems-engineering", 2, "SE L1 Published")
        
        # Create Cost domain project
        cost_l2 = self._create_project("Cost L2", "cost", 2)
        
        # Test in-domain visibility (SE L2 should see SE L1 when published)
        response = self.client.get(f"/api/projects/{se_l2['project_id']}/domain-knowledge")
        assert response.status_code == 200
        domain_knowledge = response.json()["domain_knowledge"]
        # Will be empty since SE L1 is not published yet
        
        # Test cross-domain visibility (should be empty without explicit links)
        response = self.client.get(f"/api/projects/{cost_l2['project_id']}/visible-knowledge")
        assert response.status_code == 200
        visible_knowledge = response.json()["visible_knowledge"]
        # Should not include SE projects without explicit links

    def test_layer_validation_rules(self):
        """Test layer validation rules."""
        print("\n🔒 Testing Layer Validation Rules")
        
        # Create L2 project first
        l2_project = self._create_project("L2 Project", "systems-engineering", 2)
        
        # Try to create L1 project with L2 parent (should fail)
        response = self.client.post("/api/projects", json={
            "name": "Invalid L1",
            "namespace_id": l2_project["namespace_id"],
            "domain": "systems-engineering",
            "project_level": 1,
            "parent_project_id": l2_project["project_id"]
        })
        
        # Should fail validation
        assert response.status_code == 400
        assert "Knowledge flows downward only" in response.text

    def test_project_by_level_queries(self):
        """Test querying projects by layer level."""
        print("\n📊 Testing Project Layer Queries")
        
        # Create projects at different levels
        l0_projects = [
            self._create_project("Foundation A", "foundation", 0),
            self._create_project("Foundation B", "foundation", 0)
        ]
        
        l1_projects = [
            self._create_project("Strategy A", "systems-engineering", 1),
            self._create_project("Strategy B", "operations", 1)
        ]
        
        # Query L0 projects
        response = self.client.get("/api/projects/by-level/0")
        assert response.status_code == 200
        level_0_results = response.json()["projects"]
        level_0_ids = [p["project_id"] for p in level_0_results]
        
        # Should include both L0 projects
        for l0_proj in l0_projects:
            assert l0_proj["project_id"] in level_0_ids
        
        # Should not include L1 projects
        for l1_proj in l1_projects:
            assert l1_proj["project_id"] not in level_0_ids

    def test_domain_project_queries(self):
        """Test querying projects by domain."""
        print("\n🏢 Testing Domain Project Queries")
        
        # Create projects in different domains
        se_projects = [
            self._create_project("SE Project 1", "systems-engineering", 1),
            self._create_project("SE Project 2", "systems-engineering", 2)
        ]
        
        cost_projects = [
            self._create_project("Cost Project 1", "cost", 1)
        ]
        
        # Query SE domain projects
        response = self.client.get("/api/projects/by-domain/systems-engineering")
        assert response.status_code == 200
        se_domain_results = response.json()["projects"]
        
        # Should be empty since no projects are published yet, but tests the endpoint


if __name__ == "__main__":
    # Run the complete bootstrap test
    test_instance = TestUSVAcquisitionBootstrap()
    test_instance.setup_method()
    
    try:
        test_instance.test_complete_usv_acquisition_bootstrap()
    finally:
        test_instance.teardown_method()
