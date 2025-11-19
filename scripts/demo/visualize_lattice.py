#!/usr/bin/env python3
"""
Lattice Visualization Generator

Generates an HTML file with an interactive Cytoscape.js visualization
of the project lattice, showing relationships and data flow.

Usage:
    python scripts/demo/visualize_lattice.py [project_id]
    python scripts/demo/visualize_lattice.py --all
"""

import sys
import argparse
import httpx
import json
from typing import Dict, List, Optional
from pathlib import Path

ODRAS_BASE_URL = "http://localhost:8000"
USERNAME = "das_service"
PASSWORD = "das_service_2024!"


class LatticeVisualizer:
    """Generate HTML visualization of project lattice."""

    def __init__(self):
        self.base_url = ODRAS_BASE_URL
        self.client = httpx.Client(base_url=self.base_url, timeout=30.0)
        self.token = None
        self.projects = {}
        self.relationships = []
        self.subscriptions = []

    def authenticate(self) -> bool:
        """Authenticate with ODRAS API."""
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
                    return True
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
            return None
        except Exception:
            return None

    def get_all_projects(self) -> List[Dict]:
        """Get all projects."""
        try:
            response = self.client.get("/api/projects")
            if response.status_code == 200:
                return response.json().get("projects", [])
            return []
        except Exception:
            return []

    def get_children(self, project_id: str) -> List[Dict]:
        """Get project children."""
        try:
            response = self.client.get(f"/api/projects/{project_id}/children")
            if response.status_code == 200:
                return response.json().get("children", [])
            return []
        except Exception:
            return []

    def get_cousins(self, project_id: str) -> List[Dict]:
        """Get cousin projects."""
        try:
            response = self.client.get(f"/api/projects/{project_id}/cousins")
            if response.status_code == 200:
                return response.json().get("cousins", [])
            return []
        except Exception:
            return []

    def get_relationships(self, project_id: str) -> List[Dict]:
        """Get project relationships."""
        try:
            response = self.client.get(f"/api/projects/{project_id}/relationships")
            if response.status_code == 200:
                return response.json().get("relationships", [])
            return []
        except Exception:
            return []

    def get_subscriptions(self, project_id: str) -> List[Dict]:
        """Get event subscriptions."""
        try:
            response = self.client.get(f"/api/projects/{project_id}/subscriptions")
            if response.status_code == 200:
                return response.json().get("subscriptions", [])
            return []
        except Exception:
            return []

    def build_lattice_graph(self, root_project_id: Optional[str] = None) -> Dict:
        """Build complete lattice graph structure."""
        if root_project_id:
            # Start from specific project
            projects = [self.get_project(root_project_id)]
            if not projects[0]:
                return {"nodes": [], "edges": []}
        else:
            # Get all projects
            projects = self.get_all_projects()

        nodes = []
        edges = []
        processed = set()

        def process_project(project: Dict):
            if not project or project["project_id"] in processed:
                return
            
            processed.add(project["project_id"])
            self.projects[project["project_id"]] = project

            # Add node
            level = project.get("project_level", 0)
            domain = project.get("domain", "unknown")
            nodes.append({
                "data": {
                    "id": project["project_id"],
                    "label": project.get("name", "Unknown"),
                    "level": level,
                    "domain": domain,
                    "type": "project"
                },
                "classes": f"level-{level} domain-{domain.replace('-', '_')}"
            })

            # Process children
            children = self.get_children(project["project_id"])
            for child in children:
                process_project(child)
                edges.append({
                    "data": {
                        "id": f"{project['project_id']}-{child['project_id']}",
                        "source": project["project_id"],
                        "target": child["project_id"],
                        "type": "parent-child"
                    }
                })

            # Process cousins
            cousins = self.get_cousins(project["project_id"])
            for cousin in cousins:
                if cousin["project_id"] not in processed:
                    process_project(cousin)
                edges.append({
                    "data": {
                        "id": f"{project['project_id']}-{cousin['project_id']}",
                        "source": project["project_id"],
                        "target": cousin["project_id"],
                        "type": "cousin"
                    }
                })

            # Process relationships
            relationships = self.get_relationships(project["project_id"])
            for rel in relationships:
                target_id = rel.get("target_project_id")
                target = self.get_project(target_id) if target_id else None
                if target and target_id not in processed:
                    process_project(target)
                if target_id:
                    edges.append({
                        "data": {
                            "id": f"{project['project_id']}-rel-{target_id}",
                            "source": project["project_id"],
                            "target": target_id,
                            "type": "relationship",
                            "relationship_type": rel.get("relationship_type", "coordinates_with")
                        }
                    })

        # Process all projects
        for project in projects:
            process_project(project)

        return {"nodes": nodes, "edges": edges}

    def generate_html(self, graph_data: Dict, output_file: str = "lattice_visualization.html"):
        """Generate HTML file with Cytoscape.js visualization."""
        nodes_json = json.dumps(graph_data["nodes"], indent=2)
        edges_json = json.dumps(graph_data["edges"], indent=2)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ODRAS Project Lattice Visualization</title>
    <script src="https://unpkg.com/cytoscape@3.28.1/dist/cytoscape.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0b1220;
            color: #e2e8f0;
        }}
        #cy {{
            width: 100vw;
            height: 100vh;
            background: #0b1220;
        }}
        .info-panel {{
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(15, 23, 42, 0.95);
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 16px;
            max-width: 300px;
            z-index: 1000;
        }}
        .info-panel h3 {{
            margin: 0 0 12px 0;
            color: #60a5fa;
        }}
        .legend {{
            display: flex;
            flex-direction: column;
            gap: 8px;
            font-size: 12px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
            border: 1px solid #334155;
        }}
    </style>
</head>
<body>
    <div class="info-panel">
        <h3>Project Lattice</h3>
        <div class="legend">
            <div class="legend-item">
                <div class="legend-color" style="background: #3b82f6;"></div>
                <span>L0 Foundation</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #10b981;"></div>
                <span>L1 Strategy</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #f59e0b;"></div>
                <span>L2 Tactical</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #ef4444;"></div>
                <span>L3 Implementation</span>
            </div>
            <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #334155;">
                <div style="font-size: 11px; color: #94a3b8;">
                    Solid lines: Parent-Child<br>
                    Dashed lines: Cousin/Relationship
                </div>
            </div>
        </div>
    </div>
    <div id="cy"></div>
    <script>
        const nodes = {nodes_json};
        const edges = {edges_json};

        const cy = cytoscape({{
            container: document.getElementById('cy'),
            elements: [...nodes, ...edges],
            style: [
                {{
                    selector: 'node',
                    style: {{
                        'label': 'data(label)',
                        'width': 80,
                        'height': 80,
                        'shape': 'round-rectangle',
                        'background-color': function(ele) {{
                            const level = ele.data('level');
                            if (level === 0) return '#3b82f6';
                            if (level === 1) return '#10b981';
                            if (level === 2) return '#f59e0b';
                            if (level === 3) return '#ef4444';
                            return '#64748b';
                        }},
                        'color': '#ffffff',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'font-size': '12px',
                        'font-weight': 'bold',
                        'border-width': 2,
                        'border-color': '#334155'
                    }}
                }},
                {{
                    selector: 'edge[type="parent-child"]',
                    style: {{
                        'width': 3,
                        'line-color': '#60a5fa',
                        'target-arrow-color': '#60a5fa',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier'
                    }}
                }},
                {{
                    selector: 'edge[type="cousin"], edge[type="relationship"]',
                    style: {{
                        'width': 2,
                        'line-color': '#94a3b8',
                        'line-style': 'dashed',
                        'target-arrow-color': '#94a3b8',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier'
                    }}
                }}
            ],
            layout: {{
                name: 'breadthfirst',
                directed: true,
                spacingFactor: 1.5,
                avoidOverlap: true,
                nodeDimensionsIncludeLabels: true,
                animate: true,
                animationDuration: 1000
            }}
        }});

        // Add hover effects
        cy.on('mouseover', 'node', function(evt) {{
            const node = evt.target;
            node.style('border-color', '#60a5fa');
            node.style('border-width', 4);
        }});

        cy.on('mouseout', 'node', function(evt) {{
            const node = evt.target;
            node.style('border-color', '#334155');
            node.style('border-width', 2);
        }});
    </script>
</body>
</html>"""

        output_path = Path(output_file)
        output_path.write_text(html_content)
        print(f"✅ Generated visualization: {output_path.absolute()}")

    def run(self, project_id: Optional[str] = None, output_file: str = "lattice_visualization.html"):
        """Generate visualization."""
        if not self.authenticate():
            print("❌ Authentication failed")
            return False

        print("📊 Building lattice graph...")
        graph_data = self.build_lattice_graph(project_id)
        
        print(f"✓ Found {len(graph_data['nodes'])} projects")
        print(f"✓ Found {len(graph_data['edges'])} relationships")
        
        self.generate_html(graph_data, output_file)
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate lattice visualization")
    parser.add_argument("project_id", nargs="?", help="Root project ID (optional)")
    parser.add_argument("--output", "-o", default="lattice_visualization.html", help="Output HTML file")
    args = parser.parse_args()

    visualizer = LatticeVisualizer()
    success = visualizer.run(args.project_id, args.output)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

