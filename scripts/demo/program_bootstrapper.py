#!/usr/bin/env python3
"""
Program Bootstrapper

Automatically creates project lattice from initial requirements using rule-based system.
Demonstrates DAS capability: self-assembling enterprise from intent.

Usage:
    python scripts/demo/program_bootstrapper.py [requirements_file]
    python scripts/demo/program_bootstrapper.py --interactive

Interactive mode prompts for requirements input.
"""

import sys
import argparse
import httpx
import re
import time
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

ODRAS_BASE_URL = "http://localhost:8000"
USERNAME = "das_service"
PASSWORD = "das_service_2024!"


@dataclass
class Project:
    """Project definition for bootstrapping."""
    name: str
    domain: str
    layer: int
    description: str
    parent_name: Optional[str] = None
    justification: Optional[str] = None


@dataclass
class Relationship:
    """Relationship definition for bootstrapping."""
    source_name: str
    target_name: str
    relationship_type: str
    description: str


@dataclass
class EventSubscription:
    """Event subscription definition for bootstrapping."""
    subscriber_name: str
    event_type: str
    publisher_name: Optional[str] = None


class RequirementParser:
    """Simple requirement parser using keyword matching."""
    
    DOMAIN_KEYWORDS = {
        "systems-engineering": ["requirement", "capability", "gap", "specification", "system"],
        "mission-planning": ["mission", "scenario", "operation", "surveillance", "patrol"],
        "cost": ["cost", "affordability", "budget", "price", "economic"],
        "logistics": ["logistics", "sustainment", "maintenance", "supply"],
        "communications": ["communication", "radio", "data link", "network"],
        "cybersecurity": ["cybersecurity", "security", "encryption", "protection"]
    }
    
    def parse_requirements(self, requirements_text: str) -> Dict[str, any]:
        """Parse requirements and extract concepts."""
        text_lower = requirements_text.lower()
        
        # Detect domains based on keywords
        detected_domains = set()
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            if any(keyword in text_lower for keyword in keywords):
                detected_domains.add(domain)
        
        # Always include systems-engineering as primary domain
        detected_domains.add("systems-engineering")
        
        # Extract key concepts
        concepts = {
            "domains": list(detected_domains),
            "has_mission_focus": any(word in text_lower for word in ["mission", "operation", "scenario"]),
            "has_cost_focus": any(word in text_lower for word in ["cost", "budget", "afford"]),
            "has_surveillance": "surveillance" in text_lower,
            "has_vehicle": any(word in text_lower for word in ["vehicle", "platform", "system"]),
            "complexity": "high" if len(detected_domains) > 3 else "medium" if len(detected_domains) > 2 else "low"
        }
        
        return concepts


class BootstrapRules:
    """Rule engine for creating project lattice from requirements."""
    
    def __init__(self):
        self.projects = []
        self.relationships = []
        self.subscriptions = []
        self.decision_log = []
    
    def apply_rules(self, concepts: Dict[str, any]) -> Dict[str, any]:
        """Apply bootstrapping rules to create lattice structure."""
        self.projects.clear()
        self.relationships.clear()
        self.subscriptions.clear()
        self.decision_log.clear()
        
        # Rule 1: Always create L0 Foundation
        self._create_foundation()
        
        # Rule 2: Create L1 Strategic projects based on detected domains
        self._create_l1_strategic(concepts)
        
        # Rule 3: Create L2 Tactical projects
        self._create_l2_tactical(concepts)
        
        # Rule 4: Create L3 Concrete projects if complexity is high
        if concepts["complexity"] in ["medium", "high"]:
            self._create_l3_concrete(concepts)
        
        # Rule 5: Create relationships
        self._create_relationships()
        
        # Rule 6: Create event subscriptions
        self._create_subscriptions()
        
        return {
            "projects": self.projects,
            "relationships": self.relationships,
            "subscriptions": self.subscriptions,
            "decision_log": self.decision_log
        }
    
    def _create_foundation(self):
        """Rule: Always create L0 foundation with ontologies."""
        project = Project(
            name="foundation-ontology",
            domain="foundation",
            layer=0,
            description="L0 Foundation with BFO and foundational ontologies",
            justification="Rule 1: Always create L0 Foundation for ontological grounding"
        )
        self.projects.append(project)
        self._log_decision("Created L0 Foundation project", "Rule 1: Foundation required for semantic grounding")
    
    def _create_l1_strategic(self, concepts: Dict[str, any]):
        """Rule: Create L1 strategic projects based on domains."""
        domains = concepts["domains"]
        
        # Always create ICD/Requirements project
        if "systems-engineering" in domains:
            project = Project(
                name="icd-development",
                domain="systems-engineering",
                layer=1,
                parent_name="foundation-ontology",
                description="L1 ICD Development - Capability gap identification",
                justification="Rule 2a: Systems Engineering domain detected → Create ICD project"
            )
            self.projects.append(project)
            self._log_decision("Created ICD Development project", "SE domain detected in requirements")
        
        # Create Mission Analysis if mission focus detected
        if concepts["has_mission_focus"] and "mission-planning" in domains:
            project = Project(
                name="mission-analysis",
                domain="mission-planning",
                layer=1,
                parent_name="foundation-ontology",
                description="L1 Mission Analysis - Operational scenarios and constraints",
                justification="Rule 2b: Mission focus detected → Create Mission Analysis project"
            )
            self.projects.append(project)
            self._log_decision("Created Mission Analysis project", "Mission/operation keywords detected")
        
        # Create Cost Strategy if cost focus detected
        if concepts["has_cost_focus"] and "cost" in domains:
            project = Project(
                name="cost-strategy",
                domain="cost",
                layer=1,
                parent_name="foundation-ontology",
                description="L1 Cost Strategy - Cost framework and constraints",
                justification="Rule 2c: Cost focus detected → Create Cost Strategy project"
            )
            self.projects.append(project)
            self._log_decision("Created Cost Strategy project", "Cost/budget keywords detected")
    
    def _create_l2_tactical(self, concepts: Dict[str, any]):
        """Rule: Create L2 tactical projects."""
        # CDD Development (always if ICD exists)
        if any(p.name == "icd-development" for p in self.projects):
            project = Project(
                name="cdd-development",
                domain="systems-engineering",
                layer=2,
                parent_name="icd-development",
                description="L2 CDD Development - Detailed requirements development",
                justification="Rule 3a: ICD exists → Create CDD for requirements development"
            )
            self.projects.append(project)
            self._log_decision("Created CDD Development project", "ICD project exists → need detailed requirements")
        
        # CONOPS (if mission analysis exists)
        if any(p.name == "mission-analysis" for p in self.projects):
            project = Project(
                name="conops-development",
                domain="mission-planning",
                layer=2,
                parent_name="mission-analysis",
                description="L2 CONOPS Development - Operational concept development",
                justification="Rule 3b: Mission Analysis exists → Create CONOPS"
            )
            self.projects.append(project)
            self._log_decision("Created CONOPS Development project", "Mission Analysis exists → need operational concept")
        
        # Affordability Analysis (if cost strategy exists)
        if any(p.name == "cost-strategy" for p in self.projects):
            project = Project(
                name="affordability-analysis",
                domain="cost",
                layer=2,
                parent_name="cost-strategy",
                description="L2 Affordability Analysis - Cost constraints and modeling",
                justification="Rule 3c: Cost Strategy exists → Create Affordability Analysis"
            )
            self.projects.append(project)
            self._log_decision("Created Affordability Analysis project", "Cost Strategy exists → need detailed cost analysis")
    
    def _create_l3_concrete(self, concepts: Dict[str, any]):
        """Rule: Create L3 concrete projects for solution concepts."""
        # Solution concepts (if CDD exists)
        if any(p.name == "cdd-development" for p in self.projects):
            concept_a = Project(
                name="solution-concept-a",
                domain="analysis",
                layer=3,
                parent_name="cdd-development",
                description="L3 Solution Concept A - Primary solution evaluation",
                justification="Rule 4a: CDD exists → Create solution concepts"
            )
            self.projects.append(concept_a)
            
            concept_b = Project(
                name="solution-concept-b",
                domain="analysis",
                layer=3,
                parent_name="cdd-development",
                description="L3 Solution Concept B - Alternative solution evaluation",
                justification="Rule 4b: CDD exists → Create alternative concepts"
            )
            self.projects.append(concept_b)
            
            # Trade study (if multiple concepts)
            trade_study = Project(
                name="trade-study",
                domain="analysis",
                layer=3,
                parent_name="cdd-development",
                description="L3 Trade Study - Comparative analysis of solution concepts",
                justification="Rule 4c: Multiple concepts exist → Create trade study"
            )
            self.projects.append(trade_study)
            
            self._log_decision("Created solution concept projects", "CDD project exists → need solution evaluation")
    
    def _create_relationships(self):
        """Rule: Create cousin relationships between domains."""
        # Find projects for cousin relationships
        l1_projects = [p for p in self.projects if p.layer == 1]
        l2_projects = [p for p in self.projects if p.layer == 2]
        
        # L1 cousin relationships (cross-domain coordination)
        for i, proj1 in enumerate(l1_projects):
            for proj2 in l1_projects[i+1:]:
                if proj1.domain != proj2.domain:
                    rel = Relationship(
                        source_name=proj1.name,
                        target_name=proj2.name,
                        relationship_type="coordinates_with",
                        description=f"{proj1.domain} coordinates with {proj2.domain} at strategic level"
                    )
                    self.relationships.append(rel)
                    self._log_decision(f"Created cousin relationship: {proj1.name} ↔ {proj2.name}", 
                                     "Rule 5a: Different domains at same layer → cousin relationship")
        
        # L2 cousin relationships
        for i, proj1 in enumerate(l2_projects):
            for proj2 in l2_projects[i+1:]:
                if proj1.domain != proj2.domain:
                    rel = Relationship(
                        source_name=proj1.name,
                        target_name=proj2.name,
                        relationship_type="coordinates_with",
                        description=f"{proj1.domain} coordinates with {proj2.domain} at tactical level"
                    )
                    self.relationships.append(rel)
                    self._log_decision(f"Created cousin relationship: {proj1.name} ↔ {proj2.name}", 
                                     "Rule 5b: Different domains at same layer → cousin relationship")
    
    def _create_subscriptions(self):
        """Rule: Create event subscriptions based on relationships."""
        # Each child subscribes to parent events
        for project in self.projects:
            if project.parent_name:
                parent_domain = next((p.domain for p in self.projects if p.name == project.parent_name), None)
                if parent_domain:
                    # Create domain-specific event subscription
                    event_type = self._get_domain_event_type(parent_domain)
                    subscription = EventSubscription(
                        subscriber_name=project.name,
                        event_type=event_type,
                        publisher_name=project.parent_name
                    )
                    self.subscriptions.append(subscription)
                    self._log_decision(f"Created subscription: {project.name} subscribes to {event_type}",
                                     "Rule 6a: Children subscribe to parent events")
        
        # Cross-domain subscriptions based on cousin relationships
        for rel in self.relationships:
            if rel.relationship_type == "coordinates_with":
                # Create bidirectional subscriptions
                source_domain = next((p.domain for p in self.projects if p.name == rel.source_name), None)
                target_domain = next((p.domain for p in self.projects if p.name == rel.target_name), None)
                
                if source_domain and target_domain:
                    source_event = self._get_domain_event_type(source_domain)
                    target_event = self._get_domain_event_type(target_domain)
                    
                    # Source subscribes to target
                    subscription1 = EventSubscription(
                        subscriber_name=rel.source_name,
                        event_type=target_event,
                        publisher_name=rel.target_name
                    )
                    self.subscriptions.append(subscription1)
                    
                    # Target subscribes to source
                    subscription2 = EventSubscription(
                        subscriber_name=rel.target_name,
                        event_type=source_event,
                        publisher_name=rel.source_name
                    )
                    self.subscriptions.append(subscription2)
                    
                    self._log_decision(f"Created cross-domain subscriptions between {rel.source_name} and {rel.target_name}",
                                     "Rule 6b: Cousin projects subscribe to each other's events")
    
    def _get_domain_event_type(self, domain: str) -> str:
        """Get appropriate event type for domain."""
        event_map = {
            "systems-engineering": "requirements.approved",
            "mission-planning": "scenarios.defined",
            "cost": "constraints.defined",
            "analysis": "analysis.complete",
            "foundation": "ontology.published"
        }
        return event_map.get(domain, "data.published")
    
    def _log_decision(self, decision: str, justification: str):
        """Log bootstrapping decision for transparency."""
        self.decision_log.append({
            "decision": decision,
            "justification": justification,
            "timestamp": time.time()
        })


class ProgramBootstrapper:
    """Main bootstrapping engine for creating project lattice from requirements."""
    
    def __init__(self):
        self.base_url = ODRAS_BASE_URL
        self.client = httpx.Client(base_url=self.base_url, timeout=30.0)
        self.token = None
        self.parser = RequirementParser()
        self.rules = BootstrapRules()
        self.project_registry = {}
        self.created_projects = []
    
    def authenticate(self) -> bool:
        """Authenticate with ODRAS API."""
        print("🔐 Authenticating...")
        try:
            response = self.client.post(
                "/api/auth/login",
                json={"username": USERNAME, "password": PASSWORD}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token") or data.get("token")
                if self.token:
                    self.client.headers.update({"Authorization": f"Bearer {self.token}"})
                    print("✅ Authenticated successfully")
                    return True
            
            print(f"❌ Authentication failed: {response.status_code}")
            return False
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def get_default_namespace(self) -> Optional[str]:
        """Get default namespace ID."""
        try:
            response = self.client.get("/api/namespaces/released")
            if response.status_code == 200:
                namespaces = response.json()
                if isinstance(namespaces, list) and namespaces:
                    return namespaces[0]["id"]
            return None
        except Exception as e:
            print(f"⚠️  Error getting namespace: {e}")
            return None
    
    def bootstrap_from_requirements(self, requirements_text: str) -> bool:
        """Bootstrap program lattice from requirements text."""
        print("\n" + "=" * 70)
        print("BOOTSTRAPPING PROGRAM FROM REQUIREMENTS")
        print("=" * 70)
        
        print(f"\n📋 Requirements Input:")
        print(f"   {requirements_text[:200]}{'...' if len(requirements_text) > 200 else ''}")
        
        # Step 1: Parse requirements
        print("\n🔍 Parsing requirements...")
        concepts = self.parser.parse_requirements(requirements_text)
        print(f"   Detected domains: {', '.join(concepts['domains'])}")
        print(f"   Complexity: {concepts['complexity']}")
        print(f"   Mission focus: {'Yes' if concepts['has_mission_focus'] else 'No'}")
        print(f"   Cost focus: {'Yes' if concepts['has_cost_focus'] else 'No'}")
        
        # Step 2: Apply rules
        print("\n⚙️  Applying bootstrapping rules...")
        structure = self.rules.apply_rules(concepts)
        
        # Step 3: Explain decisions
        print("\n📊 Bootstrapping Decisions:")
        for i, log_entry in enumerate(structure["decision_log"], 1):
            print(f"   {i}. {log_entry['decision']}")
            print(f"      → {log_entry['justification']}")
        
        print(f"\n📈 Generated Structure:")
        print(f"   Projects: {len(structure['projects'])}")
        print(f"   Relationships: {len(structure['relationships'])}")
        print(f"   Subscriptions: {len(structure['subscriptions'])}")
        
        # Step 4: Create in ODRAS
        print(f"\n🏗️  Creating lattice in ODRAS...")
        success = self._create_lattice(structure)
        
        if success:
            print("\n✅ Program lattice bootstrapped successfully!")
            print(f"\n📋 Summary:")
            print(f"   Created {len(self.created_projects)} projects")
            print(f"   Established relationships and event subscriptions")
            print(f"   System ready for activation and data flow")
            return True
        else:
            print("\n❌ Bootstrapping failed")
            return False
    
    def _create_lattice(self, structure: Dict[str, any]) -> bool:
        """Create the lattice structure in ODRAS."""
        namespace_id = self.get_default_namespace()
        if not namespace_id:
            print("❌ Could not get namespace")
            return False
        
        # Create projects
        print("\n📁 Creating projects...")
        for project in structure["projects"]:
            created_project = self._create_project(project, namespace_id)
            if not created_project:
                print(f"❌ Failed to create project: {project.name}")
                return False
            print(f"   ✓ Created {project.name} (L{project.layer}, {project.domain})")
        
        # Create relationships
        print("\n🔗 Creating relationships...")
        for relationship in structure["relationships"]:
            success = self._create_relationship(relationship)
            if success:
                print(f"   ✓ {relationship.source_name} {relationship.relationship_type} {relationship.target_name}")
        
        # Create subscriptions
        print("\n📡 Creating event subscriptions...")
        for subscription in structure["subscriptions"]:
            success = self._create_subscription(subscription)
            if success:
                print(f"   ✓ {subscription.subscriber_name} subscribes to {subscription.event_type}")
        
        return True
    
    def _create_project(self, project: Project, namespace_id: str) -> Optional[Dict]:
        """Create a project via ODRAS API."""
        project_data = {
            "name": project.name,
            "namespace_id": namespace_id,
            "domain": project.domain,
            "project_level": project.layer,
            "description": project.description
        }
        
        if project.parent_name and project.parent_name in self.project_registry:
            project_data["parent_project_id"] = self.project_registry[project.parent_name]["project_id"]
        
        try:
            response = self.client.post("/api/projects", json=project_data)
            if response.status_code == 200:
                created_project = response.json()["project"]
                project_id = created_project["project_id"]
                self.created_projects.append(project_id)
                self.project_registry[project.name] = created_project
                return created_project
            else:
                print(f"❌ Failed to create {project.name}: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error creating {project.name}: {e}")
            return None
    
    def _create_relationship(self, relationship: Relationship) -> bool:
        """Create a cousin relationship."""
        if (relationship.source_name not in self.project_registry or 
            relationship.target_name not in self.project_registry):
            return False
        
        source_id = self.project_registry[relationship.source_name]["project_id"]
        target_id = self.project_registry[relationship.target_name]["project_id"]
        
        try:
            response = self.client.post(
                f"/api/projects/{source_id}/relationships",
                json={
                    "target_project_id": target_id,
                    "relationship_type": relationship.relationship_type,
                    "description": relationship.description
                }
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def _create_subscription(self, subscription: EventSubscription) -> bool:
        """Create an event subscription."""
        if subscription.subscriber_name not in self.project_registry:
            return False
        
        subscriber_id = self.project_registry[subscription.subscriber_name]["project_id"]
        publisher_id = None
        if subscription.publisher_name and subscription.publisher_name in self.project_registry:
            publisher_id = self.project_registry[subscription.publisher_name]["project_id"]
        
        try:
            response = self.client.post(
                f"/api/projects/{subscriber_id}/subscriptions",
                json={
                    "event_type": subscription.event_type,
                    "source_project_id": publisher_id
                }
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def cleanup(self):
        """Clean up created projects."""
        print(f"\n🧹 Cleaning up {len(self.created_projects)} created projects...")
        for project_id in self.created_projects:
            try:
                response = self.client.delete(f"/api/projects/{project_id}")
                if response.status_code in [200, 404]:
                    print(f"   ✓ Deleted project {project_id}")
                else:
                    print(f"   ⚠️  Failed to delete project {project_id}")
            except Exception as e:
                print(f"   ⚠️  Error deleting project {project_id}: {e}")
    
    def run(self, requirements_text: str, cleanup: bool = False) -> bool:
        """Run the bootstrapping process."""
        if not self.authenticate():
            return False
        
        success = self.bootstrap_from_requirements(requirements_text)
        
        if cleanup and self.created_projects:
            self.cleanup()
        elif self.created_projects:
            print("\n💡 Tip: Projects created. Use --cleanup to remove them")
        
        return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Bootstrap program lattice from requirements")
    parser.add_argument("requirements_file", nargs="?", help="File containing requirements text")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--cleanup", action="store_true", help="Clean up created projects after demo")
    args = parser.parse_args()
    
    # Get requirements text
    if args.requirements_file:
        try:
            with open(args.requirements_file, 'r') as f:
                requirements_text = f.read()
        except Exception as e:
            print(f"❌ Error reading requirements file: {e}")
            return False
    elif args.interactive:
        print("📝 Interactive Requirements Input")
        print("Enter requirements (press Ctrl+D when done):")
        try:
            requirements_text = sys.stdin.read()
        except KeyboardInterrupt:
            print("\n❌ Cancelled")
            return False
    else:
        # Default example requirements
        requirements_text = """
        Need unmanned surface vehicle for maritime surveillance missions.
        System must operate autonomously for 48 hours minimum.
        Required surveillance range of 50 nautical miles.
        Must be cost-effective and support various mission scenarios.
        Communications capability for real-time data transmission.
        System must be maintainable in harsh maritime environments.
        """
        print("📝 Using default example requirements:")
        print(requirements_text.strip())
    
    # Run bootstrapper
    bootstrapper = ProgramBootstrapper()
    success = bootstrapper.run(requirements_text.strip(), cleanup=args.cleanup)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
