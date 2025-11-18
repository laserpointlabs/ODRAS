#!/usr/bin/env python3
"""
Aircraft Development Workflow Example (FEA Example)

Demonstrates vertical parent-child hierarchy with cross-domain cousin coordination.
Shows how requirements flow through loads analysis to FEA, with cost modeling coordination.

Project Structure:
- L0 Foundation: aircraft-foundation (foundation domain)
- L1 Requirements: aircraft-requirements (systems-engineering domain, parent: foundation)
- L2 Loads Analysis: aircraft-loads (structures domain, parent: requirements)
- L3 FEA Analysis: aircraft-fea (analysis domain, parent: loads)
- L2 Cost Model: aircraft-cost (cost domain, cousin to FEA)

Usage:
    python scripts/demo/create_lattice_example_2.py [--cleanup]
"""

import sys
import argparse
import httpx
from typing import Dict, Optional

ODRAS_BASE_URL = "http://localhost:8000"
USERNAME = "das_service"
PASSWORD = "das_service_2024!"


class LatticeExample2:
    """Aircraft development workflow demonstration."""

    def __init__(self):
        self.base_url = ODRAS_BASE_URL
        self.client = httpx.Client(base_url=self.base_url, timeout=30.0)
        self.token = None
        self.project_registry = {}
        self.created_projects = []

    def authenticate(self) -> bool:
        """Authenticate with ODRAS API."""
        print(f"🔐 Authenticating as {USERNAME}...")
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
                    print(f"✅ Authenticated successfully")
                    return True
                else:
                    print(f"❌ No token in response: {data}")
                    return False
            else:
                print(f"❌ Authentication failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False

    def get_default_namespace(self) -> Optional[str]:
        """Get default namespace ID."""
        try:
            response = self.client.get("/api/namespace/simple")
            if response.status_code == 200:
                namespaces = response.json().get("namespaces", [])
                if namespaces:
                    default_ns = next((ns for ns in namespaces if ns["status"] == "released"), namespaces[0])
                    return default_ns["id"]
            return None
        except Exception as e:
            print(f"⚠️  Error getting namespace: {e}")
            return None

    def create_project(
        self,
        name: str,
        domain: str,
        project_level: int,
        parent_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[Dict]:
        """Create a project."""
        namespace_id = self.get_default_namespace()
        if not namespace_id:
            print(f"❌ Failed to get namespace for {name}")
            return None

        project_data = {
            "name": name,
            "namespace_id": namespace_id,
            "domain": domain,
            "project_level": project_level,
        }

        if description:
            project_data["description"] = description

        if parent_name and parent_name in self.project_registry:
            project_data["parent_project_id"] = self.project_registry[parent_name]["project_id"]

        try:
            response = self.client.post("/api/projects", json=project_data)
            if response.status_code == 200:
                project = response.json()["project"]
                project_id = project["project_id"]
                self.created_projects.append(project_id)
                self.project_registry[name] = project
                print(f"✓ Created {name} (L{project_level}, {domain})")
                return project
            else:
                print(f"❌ Failed to create {name}: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error creating {name}: {e}")
            return None

    def create_cousin_relationship(
        self,
        source_name: str,
        target_name: str,
        relationship_type: str = "coordinates_with",
        description: Optional[str] = None,
    ) -> bool:
        """Create cousin relationship between projects."""
        if source_name not in self.project_registry or target_name not in self.project_registry:
            print(f"❌ Projects not found for relationship {source_name} -> {target_name}")
            return False

        source_id = self.project_registry[source_name]["project_id"]
        target_id = self.project_registry[target_name]["project_id"]

        try:
            response = self.client.post(
                f"/api/projects/{source_id}/relationships",
                json={
                    "target_project_id": target_id,
                    "relationship_type": relationship_type,
                    "description": description or f"{source_name} coordinates with {target_name}",
                }
            )
            if response.status_code == 200:
                print(f"✓ Created relationship: {source_name} {relationship_type} {target_name}")
                return True
            else:
                print(f"❌ Failed to create relationship: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error creating relationship: {e}")
            return False

    def create_knowledge_link(
        self,
        source_name: str,
        target_name: str,
        link_type: str = "requirement_reference",
    ) -> bool:
        """Create cross-domain knowledge link."""
        if source_name not in self.project_registry or target_name not in self.project_registry:
            print(f"❌ Projects not found for knowledge link {source_name} -> {target_name}")
            return False

        source_id = self.project_registry[source_name]["project_id"]
        target_id = self.project_registry[target_name]["project_id"]

        try:
            response = self.client.post(
                f"/api/projects/{source_id}/knowledge-links",
                json={
                    "target_project_id": target_id,
                    "link_type": link_type,
                    "identified_by": "user",
                }
            )
            if response.status_code == 200:
                print(f"✓ Created knowledge link: {source_name} -> {target_name} ({link_type})")
                return True
            else:
                print(f"❌ Failed to create knowledge link: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error creating knowledge link: {e}")
            return False

    def create_event_subscription(
        self,
        subscriber_name: str,
        event_type: str,
        publisher_name: Optional[str] = None,
    ) -> bool:
        """Create event subscription."""
        if subscriber_name not in self.project_registry:
            print(f"❌ Subscriber project {subscriber_name} not found")
            return False

        subscriber_id = self.project_registry[subscriber_name]["project_id"]
        publisher_id = None
        if publisher_name:
            if publisher_name not in self.project_registry:
                print(f"❌ Publisher project {publisher_name} not found")
                return False
            publisher_id = self.project_registry[publisher_name]["project_id"]

        try:
            response = self.client.post(
                f"/api/projects/{subscriber_id}/subscriptions",
                json={
                    "event_type": event_type,
                    "source_project_id": publisher_id,
                }
            )
            if response.status_code == 200:
                print(f"✓ Created subscription: {subscriber_name} subscribes to {event_type} from {publisher_name or 'any'}")
                return True
            else:
                print(f"❌ Failed to create subscription: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error creating subscription: {e}")
            return False

    def publish_event(
        self,
        publisher_name: str,
        event_type: str,
        data: Dict,
    ) -> bool:
        """Publish an event."""
        if publisher_name not in self.project_registry:
            print(f"❌ Publisher project {publisher_name} not found")
            return False

        publisher_id = self.project_registry[publisher_name]["project_id"]

        try:
            response = self.client.post(
                f"/api/projects/{publisher_id}/publish-event",
                json={
                    "event_type": event_type,
                    "data": data,
                }
            )
            if response.status_code == 200:
                result = response.json()
                subscribers_notified = result.get("subscribers_notified", 0)
                print(f"✓ Published {event_type} from {publisher_name} (notified {subscribers_notified} subscribers)")
                return True
            else:
                print(f"❌ Failed to publish event: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error publishing event: {e}")
            return False

    def create_lattice(self) -> bool:
        """Create the aircraft development workflow lattice."""
        print("\n" + "=" * 60)
        print("Creating Aircraft Development Workflow Lattice")
        print("=" * 60)

        # Create L0 Foundation
        foundation = self.create_project(
            name="aircraft-foundation",
            domain="foundation",
            project_level=0,
            description="L0 Foundation project for aircraft development",
        )
        if not foundation:
            return False

        # Create L1 Requirements
        requirements = self.create_project(
            name="aircraft-requirements",
            domain="systems-engineering",
            project_level=1,
            parent_name="aircraft-foundation",
            description="L1 Requirements project defining aircraft specifications",
        )
        if not requirements:
            return False

        # Create L2 Loads Analysis
        loads = self.create_project(
            name="aircraft-loads",
            domain="structures",
            project_level=2,
            parent_name="aircraft-requirements",
            description="L2 Loads analysis project calculating structural loads",
        )
        if not loads:
            return False

        # Create L3 FEA Analysis
        fea = self.create_project(
            name="aircraft-fea",
            domain="analysis",
            project_level=3,
            parent_name="aircraft-loads",
            description="L3 FEA analysis project performing finite element analysis",
        )
        if not fea:
            return False

        # Create L2 Cost Model
        cost = self.create_project(
            name="aircraft-cost",
            domain="cost",
            project_level=2,
            description="L2 Cost model project for cost estimation",
        )
        if not cost:
            return False

        # Create relationships
        print("\n" + "-" * 60)
        print("Creating Relationships")
        print("-" * 60)

        # Cousin relationship: FEA coordinates with Cost
        self.create_cousin_relationship(
            source_name="aircraft-fea",
            target_name="aircraft-cost",
            description="FEA provides mass/material data for cost calculation",
        )

        # Cross-domain knowledge link: FEA needs Requirements knowledge
        self.create_knowledge_link(
            source_name="aircraft-fea",
            target_name="aircraft-requirements",
            link_type="requirement_reference",
        )

        # Set up event subscriptions
        print("\n" + "-" * 60)
        print("Setting Up Event Subscriptions")
        print("-" * 60)

        # Loads subscribes to Requirements
        self.create_event_subscription(
            subscriber_name="aircraft-loads",
            event_type="requirements.approved",
            publisher_name="aircraft-requirements",
        )

        # FEA subscribes to Requirements and Loads
        self.create_event_subscription(
            subscriber_name="aircraft-fea",
            event_type="requirements.approved",
            publisher_name="aircraft-requirements",
        )
        self.create_event_subscription(
            subscriber_name="aircraft-fea",
            event_type="loads.calculated",
            publisher_name="aircraft-loads",
        )

        # Cost subscribes to FEA
        self.create_event_subscription(
            subscriber_name="aircraft-cost",
            event_type="fea.analysis_complete",
            publisher_name="aircraft-fea",
        )

        # Demonstrate data flow
        print("\n" + "-" * 60)
        print("Demonstrating Data Flow")
        print("-" * 60)

        # Step 1: Requirements publishes approved requirements
        self.publish_event(
            publisher_name="aircraft-requirements",
            event_type="requirements.approved",
            data={
                "max_weight": 25000,
                "range": 3000,
                "requirement_count": 15,
                "status": "approved",
            },
        )

        # Step 2: Loads calculates and publishes
        self.publish_event(
            publisher_name="aircraft-loads",
            event_type="loads.calculated",
            data={
                "wing_load": 15000,
                "fuselage_load": 8000,
                "max_load": 23000,
                "analysis_id": "loads-001",
            },
        )

        # Step 3: FEA performs analysis and publishes
        self.publish_event(
            publisher_name="aircraft-fea",
            event_type="fea.analysis_complete",
            data={
                "margin_of_safety": 0.86,
                "factor_of_safety_yield": 1.15,
                "factor_of_safety_ultimate": 1.50,
                "material": "17-4PH",
                "mass": 25.4,
                "analysis_id": "fea-001",
            },
        )

        print("\n✅ Aircraft development workflow lattice created successfully!")
        print("\nLattice Structure:")
        print("  L0: aircraft-foundation (foundation)")
        print("    └─ L1: aircraft-requirements (systems-engineering)")
        print("         └─ L2: aircraft-loads (structures)")
        print("              └─ L3: aircraft-fea (analysis)")
        print("  L2: aircraft-cost (cost) ↔ aircraft-fea (cousin)")
        return True

    def cleanup(self):
        """Clean up created projects."""
        print("\n🧹 Cleaning up created projects...")
        for project_id in self.created_projects:
            try:
                response = self.client.delete(f"/api/projects/{project_id}")
                if response.status_code in [200, 404]:
                    print(f"✓ Deleted project {project_id}")
                else:
                    print(f"⚠️  Failed to delete project {project_id}: {response.status_code}")
            except Exception as e:
                print(f"⚠️  Error deleting project {project_id}: {e}")

    def run(self, cleanup: bool = False):
        """Run the demonstration."""
        if not self.authenticate():
            print("❌ Authentication failed. Exiting.")
            return False

        success = self.create_lattice()

        if cleanup:
            self.cleanup()
        else:
            print("\n💡 Tip: Run with --cleanup to remove demo projects")

        return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Create aircraft development workflow lattice example")
    parser.add_argument("--cleanup", action="store_true", help="Clean up created projects after demonstration")
    args = parser.parse_args()

    example = LatticeExample2()
    success = example.run(cleanup=args.cleanup)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
