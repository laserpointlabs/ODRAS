#!/usr/bin/env python3
"""
Multi-Domain Program Bootstrap Example

Demonstrates how a program can bootstrap from a single foundation project.
Shows multi-domain coordination with sibling projects and cross-domain relationships.

Project Structure:
- L0 Foundation: program-foundation (foundation domain)
- L1 SE Strategy: program-se-strategy (systems-engineering domain, parent: foundation)
- L1 Cost Strategy: program-cost-strategy (cost domain, parent: foundation)
- L1 Logistics Strategy: program-logistics-strategy (logistics domain, parent: foundation)
- L2 SE Tactical: program-se-tactical (systems-engineering domain, parent: SE Strategy)
- L2 Cost Analysis: program-cost-analysis (cost domain, parent: Cost Strategy)
- L3 SE Implementation: program-se-impl (systems-engineering domain, parent: SE Tactical)

Usage:
    python scripts/demo/create_lattice_example_3.py [--cleanup]
"""

import sys
import argparse
import httpx
from typing import Dict, Optional

ODRAS_BASE_URL = "http://localhost:8000"
USERNAME = "das_service"
PASSWORD = "das_service_2024!"


class LatticeExample3:
    """Multi-domain program bootstrap demonstration."""

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
            response = self.client.get("/api/namespaces/released")
            if response.status_code == 200:
                namespaces = response.json()
                if isinstance(namespaces, list) and namespaces:
                    # Use first released namespace
                    return namespaces[0]["id"]
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
        """Create the multi-domain program bootstrap lattice."""
        print("\n" + "=" * 60)
        print("Creating Multi-Domain Program Bootstrap Lattice")
        print("=" * 60)

        # Create L0 Foundation
        foundation = self.create_project(
            name="program-foundation",
            domain="foundation",
            project_level=0,
            description="L0 Foundation project for program bootstrap",
        )
        if not foundation:
            return False

        # Create L1 Strategy projects (siblings)
        se_strategy = self.create_project(
            name="program-se-strategy",
            domain="systems-engineering",
            project_level=1,
            parent_name="program-foundation",
            description="L1 Systems Engineering Strategy",
        )
        if not se_strategy:
            return False

        cost_strategy = self.create_project(
            name="program-cost-strategy",
            domain="cost",
            project_level=1,
            parent_name="program-foundation",
            description="L1 Cost Strategy",
        )
        if not cost_strategy:
            return False

        logistics_strategy = self.create_project(
            name="program-logistics-strategy",
            domain="logistics",
            project_level=1,
            parent_name="program-foundation",
            description="L1 Logistics Strategy",
        )
        if not logistics_strategy:
            return False

        # Create L2 Tactical projects
        se_tactical = self.create_project(
            name="program-se-tactical",
            domain="systems-engineering",
            project_level=2,
            parent_name="program-se-strategy",
            description="L2 Systems Engineering Tactical",
        )
        if not se_tactical:
            return False

        cost_analysis = self.create_project(
            name="program-cost-analysis",
            domain="cost",
            project_level=2,
            parent_name="program-cost-strategy",
            description="L2 Cost Analysis",
        )
        if not cost_analysis:
            return False

        # Create L3 Implementation project
        se_impl = self.create_project(
            name="program-se-impl",
            domain="systems-engineering",
            project_level=3,
            parent_name="program-se-tactical",
            description="L3 Systems Engineering Implementation",
        )
        if not se_impl:
            return False

        # Create relationships
        print("\n" + "-" * 60)
        print("Creating Relationships")
        print("-" * 60)

        # Cousin relationships: SE Tactical ↔ Cost Analysis
        self.create_cousin_relationship(
            source_name="program-se-tactical",
            target_name="program-cost-analysis",
            description="SE tactical coordinates with cost analysis",
        )

        # Cousin relationship: SE Implementation ↔ Cost Analysis
        self.create_cousin_relationship(
            source_name="program-se-impl",
            target_name="program-cost-analysis",
            description="SE implementation coordinates with cost analysis",
        )

        # Set up event subscriptions
        print("\n" + "-" * 60)
        print("Setting Up Event Subscriptions")
        print("-" * 60)

        # L2 projects subscribe to their L1 parents
        self.create_event_subscription(
            subscriber_name="program-se-tactical",
            event_type="strategy.approved",
            publisher_name="program-se-strategy",
        )

        self.create_event_subscription(
            subscriber_name="program-cost-analysis",
            event_type="strategy.approved",
            publisher_name="program-cost-strategy",
        )

        # L3 subscribes to L2
        self.create_event_subscription(
            subscriber_name="program-se-impl",
            event_type="tactical.ready",
            publisher_name="program-se-tactical",
        )

        # Cross-domain subscriptions
        self.create_event_subscription(
            subscriber_name="program-cost-analysis",
            event_type="tactical.ready",
            publisher_name="program-se-tactical",
        )

        self.create_event_subscription(
            subscriber_name="program-cost-analysis",
            event_type="implementation.complete",
            publisher_name="program-se-impl",
        )

        # Demonstrate data flow
        print("\n" + "-" * 60)
        print("Demonstrating Data Flow")
        print("-" * 60)

        # Foundation publishes foundational knowledge
        self.publish_event(
            publisher_name="program-foundation",
            event_type="foundation.established",
            data={
                "program_name": "Multi-Domain Program",
                "established_date": "2025-01-15",
                "domains": ["systems-engineering", "cost", "logistics"],
            },
        )

        # L1 Strategies publish
        self.publish_event(
            publisher_name="program-se-strategy",
            event_type="strategy.approved",
            data={
                "strategy_type": "systems-engineering",
                "approval_date": "2025-01-20",
                "objectives": ["design", "development", "integration"],
            },
        )

        self.publish_event(
            publisher_name="program-cost-strategy",
            event_type="strategy.approved",
            data={
                "strategy_type": "cost",
                "approval_date": "2025-01-20",
                "budget_framework": "established",
            },
        )

        # L2 Tactical publishes
        self.publish_event(
            publisher_name="program-se-tactical",
            event_type="tactical.ready",
            data={
                "tactical_plan": "ready",
                "resources_allocated": True,
                "timeline": "2025-Q1",
            },
        )

        # L3 Implementation publishes
        self.publish_event(
            publisher_name="program-se-impl",
            event_type="implementation.complete",
            data={
                "implementation_status": "complete",
                "components_delivered": 5,
                "completion_date": "2025-02-15",
            },
        )

        print("\n✅ Multi-domain program bootstrap lattice created successfully!")
        print("\nLattice Structure:")
        print("  L0: program-foundation (foundation)")
        print("    ├─ L1: program-se-strategy (systems-engineering)")
        print("    │    └─ L2: program-se-tactical (systems-engineering)")
        print("    │         └─ L3: program-se-impl (systems-engineering)")
        print("    ├─ L1: program-cost-strategy (cost)")
        print("    │    └─ L2: program-cost-analysis (cost)")
        print("    └─ L1: program-logistics-strategy (logistics)")
        print("\nCousin Relationships:")
        print("  program-se-tactical ↔ program-cost-analysis")
        print("  program-se-impl ↔ program-cost-analysis")
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
    parser = argparse.ArgumentParser(description="Create multi-domain program bootstrap lattice example")
    parser.add_argument("--cleanup", action="store_true", help="Clean up created projects after demonstration")
    args = parser.parse_args()

    example = LatticeExample3()
    success = example.run(cleanup=args.cleanup)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
