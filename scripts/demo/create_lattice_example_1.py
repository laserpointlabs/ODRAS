#!/usr/bin/env python3
"""
Simple 3-Project Bootstrap Example

Minimal example showing basic lattice growth with parent-child and cousin relationships.
This is the simplest demonstration of ODRAS's self-growing capability.

Project Structure:
- L1 Parent: demo-parent (systems-engineering domain)
- L2 Child: demo-child (systems-engineering domain, parent: parent)
- L2 Cousin: demo-cousin (cost domain, cousin to child)

Usage:
    python scripts/demo/create_lattice_example_1.py [--cleanup]
"""

import sys
import argparse
import httpx
from typing import Dict, Optional

ODRAS_BASE_URL = "http://localhost:8000"
USERNAME = "das_service"
PASSWORD = "das_service_2024!"


class LatticeExample1:
    """Simple 3-project bootstrap demonstration."""

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
        """Create the simple 3-project lattice."""
        print("\n" + "=" * 60)
        print("Creating Simple 3-Project Bootstrap Lattice")
        print("=" * 60)

        # Create L1 Parent
        parent = self.create_project(
            name="demo-parent",
            domain="systems-engineering",
            project_level=1,
            description="L1 Parent project demonstrating vertical hierarchy",
        )
        if not parent:
            return False

        # Create L2 Child
        child = self.create_project(
            name="demo-child",
            domain="systems-engineering",
            project_level=2,
            parent_name="demo-parent",
            description="L2 Child project inheriting from parent",
        )
        if not child:
            return False

        # Create L2 Cousin
        cousin = self.create_project(
            name="demo-cousin",
            domain="cost",
            project_level=2,
            description="L2 Cousin project for cross-domain coordination",
        )
        if not cousin:
            return False

        # Create cousin relationship (bidirectional)
        self.create_cousin_relationship(
            source_name="demo-child",
            target_name="demo-cousin",
            description="Child coordinates with cousin for cost analysis",
        )

        # Set up event subscriptions
        self.create_event_subscription(
            subscriber_name="demo-child",
            event_type="parent.data_ready",
            publisher_name="demo-parent",
        )

        self.create_event_subscription(
            subscriber_name="demo-cousin",
            event_type="child.processed",
            publisher_name="demo-child",
        )

        # Demonstrate data flow
        print("\n" + "-" * 60)
        print("Demonstrating Data Flow")
        print("-" * 60)

        # Parent publishes initial data
        self.publish_event(
            publisher_name="demo-parent",
            event_type="parent.data_ready",
            data={
                "status": "ready",
                "data_points": 100,
                "timestamp": "2025-01-15T10:00:00Z",
            },
        )

        # Child processes and publishes
        self.publish_event(
            publisher_name="demo-child",
            event_type="child.processed",
            data={
                "processed_items": 100,
                "processing_time_ms": 250,
                "status": "complete",
            },
        )

        print("\n✅ Simple 3-project lattice created successfully!")
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
    parser = argparse.ArgumentParser(description="Create simple 3-project lattice example")
    parser.add_argument("--cleanup", action="store_true", help="Clean up created projects after demonstration")
    args = parser.parse_args()

    example = LatticeExample1()
    success = example.run(cleanup=args.cleanup)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
