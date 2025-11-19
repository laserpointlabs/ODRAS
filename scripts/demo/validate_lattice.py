#!/usr/bin/env python3
"""
Lattice Validation Utility

Validates project lattice structure, relationships, and data flow.
Can validate specific projects or entire lattices.

Usage:
    python scripts/demo/validate_lattice.py [project_id]
    python scripts/demo/validate_lattice.py --all
"""

import sys
import argparse
import httpx
from typing import Dict, List, Optional

ODRAS_BASE_URL = "http://localhost:8000"
USERNAME = "das_service"
PASSWORD = "das_service_2024!"


class LatticeValidator:
    """Validate project lattice structure and relationships."""

    def __init__(self):
        self.base_url = ODRAS_BASE_URL
        self.client = httpx.Client(base_url=self.base_url, timeout=30.0)
        self.token = None
        self.issues = []

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

    def get_project(self, project_id: str) -> Optional[Dict]:
        """Get project details."""
        try:
            response = self.client.get(f"/api/projects/{project_id}")
            if response.status_code == 200:
                return response.json().get("project")
            else:
                self.issues.append(f"Failed to get project {project_id}: {response.status_code}")
                return None
        except Exception as e:
            self.issues.append(f"Error getting project {project_id}: {e}")
            return None

    def get_children(self, project_id: str) -> List[Dict]:
        """Get project children."""
        try:
            response = self.client.get(f"/api/projects/{project_id}/children")
            if response.status_code == 200:
                return response.json().get("children", [])
            else:
                return []
        except Exception as e:
            self.issues.append(f"Error getting children for {project_id}: {e}")
            return []

    def get_parent(self, project_id: str) -> Optional[Dict]:
        """Get project parent."""
        try:
            response = self.client.get(f"/api/projects/{project_id}/parent")
            if response.status_code == 200:
                return response.json().get("parent")
            else:
                return None
        except Exception as e:
            self.issues.append(f"Error getting parent for {project_id}: {e}")
            return None

    def get_lineage(self, project_id: str) -> List[Dict]:
        """Get project lineage."""
        try:
            response = self.client.get(f"/api/projects/{project_id}/lineage")
            if response.status_code == 200:
                return response.json().get("lineage", [])
            else:
                return []
        except Exception as e:
            self.issues.append(f"Error getting lineage for {project_id}: {e}")
            return []

    def get_cousins(self, project_id: str) -> List[Dict]:
        """Get cousin projects."""
        try:
            response = self.client.get(f"/api/projects/{project_id}/cousins")
            if response.status_code == 200:
                return response.json().get("cousins", [])
            else:
                return []
        except Exception as e:
            self.issues.append(f"Error getting cousins for {project_id}: {e}")
            return []

    def get_relationships(self, project_id: str) -> List[Dict]:
        """Get project relationships."""
        try:
            response = self.client.get(f"/api/projects/{project_id}/relationships")
            if response.status_code == 200:
                return response.json().get("relationships", [])
            else:
                return []
        except Exception as e:
            self.issues.append(f"Error getting relationships for {project_id}: {e}")
            return []

    def get_subscriptions(self, project_id: str) -> List[Dict]:
        """Get event subscriptions."""
        try:
            response = self.client.get(f"/api/projects/{project_id}/subscriptions")
            if response.status_code == 200:
                return response.json().get("subscriptions", [])
            else:
                return []
        except Exception as e:
            self.issues.append(f"Error getting subscriptions for {project_id}: {e}")
            return []

    def validate_project(self, project_id: str, indent: int = 0) -> bool:
        """Validate a single project and its relationships."""
        prefix = "  " * indent
        project = self.get_project(project_id)
        if not project:
            print(f"{prefix}❌ Project {project_id} not found")
            return False

        name = project.get("name", "Unknown")
        level = project.get("project_level", "?")
        domain = project.get("domain", "?")
        parent_id = project.get("parent_project_id")

        print(f"{prefix}📁 {name} (L{level}, {domain})")

        # Validate parent-child relationship
        if parent_id:
            parent = self.get_parent(project_id)
            if parent:
                parent_level = parent.get("project_level", "?")
                if parent_level is not None and level is not None:
                    if parent_level >= level:
                        self.issues.append(
                            f"Invalid parent-child: {name} (L{level}) has parent L{parent_level}"
                        )
                        print(f"{prefix}  ⚠️  Invalid parent level: L{parent_level} >= L{level}")
            else:
                self.issues.append(f"Parent {parent_id} not found for {name}")
                print(f"{prefix}  ⚠️  Parent not found")

        # Validate children
        children = self.get_children(project_id)
        if children:
            print(f"{prefix}  └─ Children ({len(children)}):")
            for child in children:
                self.validate_project(child["project_id"], indent + 2)

        # Validate cousins
        cousins = self.get_cousins(project_id)
        if cousins:
            print(f"{prefix}  ↔ Cousins ({len(cousins)}):")
            for cousin in cousins:
                cousin_name = cousin.get("name", "Unknown")
                cousin_domain = cousin.get("domain", "?")
                print(f"{prefix}    - {cousin_name} ({cousin_domain})")

        # Validate relationships
        relationships = self.get_relationships(project_id)
        if relationships:
            print(f"{prefix}  🔗 Relationships ({len(relationships)}):")
            for rel in relationships:
                rel_type = rel.get("relationship_type", "?")
                target_id = rel.get("target_project_id")
                target = self.get_project(target_id) if target_id else None
                target_name = target.get("name", "Unknown") if target else "?"
                print(f"{prefix}    - {rel_type} → {target_name}")

        # Validate subscriptions
        subscriptions = self.get_subscriptions(project_id)
        if subscriptions:
            print(f"{prefix}  📡 Subscriptions ({len(subscriptions)}):")
            for sub in subscriptions:
                event_type = sub.get("event_type", "?")
                source_id = sub.get("source_project_id")
                source = self.get_project(source_id) if source_id else None
                source_name = source.get("name", "any") if source else "any"
                print(f"{prefix}    - {event_type} from {source_name}")

        return True

    def validate_all(self) -> bool:
        """Validate all projects."""
        try:
            response = self.client.get("/api/projects")
            if response.status_code == 200:
                projects = response.json().get("projects", [])
                print(f"\n📊 Found {len(projects)} projects to validate\n")
                
                # Find root projects (no parent)
                root_projects = [p for p in projects if not p.get("parent_project_id")]
                
                if root_projects:
                    print("=" * 60)
                    print("Validating Project Lattices")
                    print("=" * 60)
                    for root in root_projects:
                        print()
                        self.validate_project(root["project_id"])
                else:
                    print("No root projects found")
                    return False
                
                return True
            else:
                print(f"❌ Failed to get projects: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error getting projects: {e}")
            return False

    def validate_single(self, project_id: str) -> bool:
        """Validate a single project and its subtree."""
        print("=" * 60)
        print(f"Validating Project: {project_id}")
        print("=" * 60)
        print()
        return self.validate_project(project_id)

    def print_summary(self):
        """Print validation summary."""
        print("\n" + "=" * 60)
        print("Validation Summary")
        print("=" * 60)
        
        if self.issues:
            print(f"\n⚠️  Found {len(self.issues)} issues:")
            for issue in self.issues:
                print(f"  - {issue}")
            return False
        else:
            print("\n✅ No issues found!")
            return True

    def run(self, project_id: Optional[str] = None, validate_all: bool = False) -> bool:
        """Run validation."""
        if not self.authenticate():
            print("❌ Authentication failed. Exiting.")
            return False

        if validate_all:
            success = self.validate_all()
        elif project_id:
            success = self.validate_single(project_id)
        else:
            print("❌ Must specify --project-id or --all")
            return False

        summary_success = self.print_summary()
        return success and summary_success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate project lattice structure")
    parser.add_argument("project_id", nargs="?", help="Project ID to validate")
    parser.add_argument("--all", action="store_true", help="Validate all projects")
    args = parser.parse_args()

    validator = LatticeValidator()
    
    if args.all:
        success = validator.run(validate_all=True)
    elif args.project_id:
        success = validator.run(project_id=args.project_id)
    else:
        print("❌ Must specify project_id or --all")
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
