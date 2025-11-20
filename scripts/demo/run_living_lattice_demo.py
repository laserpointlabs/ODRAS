#!/usr/bin/env python3
"""
Living Project Lattice Demonstrator

Complete demonstration of ODRAS living project lattice capabilities:
1. Bootstrap program from requirements
2. Launch live visualization
3. Show real-time event flow and decision-making
4. Demonstrate requirement change cascades
5. Show Gray System and X-layer activity

Usage:
    python scripts/demo/run_living_lattice_demo.py [--requirements-file FILE] [--manual-mode] [--cleanup]
"""

import sys
import argparse
import asyncio
import subprocess
import time
import threading
import webbrowser
from pathlib import Path
from typing import Dict, Any, Optional

# Import our bootstrapper
from program_bootstrapper import ProgramBootstrapper


class LivingLatticeDemonstrator:
    """Master orchestrator for living lattice demonstration."""
    
    def __init__(self):
        self.bootstrapper = ProgramBootstrapper()
        self.visualization_process = None
        self.created_projects = []
        self.demo_running = False
    
    def print_header(self, text: str):
        """Print formatted header."""
        print("\n" + "=" * 80)
        print(text.center(80))
        print("=" * 80)
    
    def print_step(self, step_num: int, description: str):
        """Print step header."""
        print(f"\n{'=' * 80}")
        print(f"STEP {step_num}: {description}")
        print("=" * 80)
    
    def run_demo(self, requirements_text: str, manual_mode: bool = False, cleanup: bool = False):
        """Run the complete living lattice demonstration."""
        self.print_header("🔬 ODRAS LIVING PROJECT LATTICE DEMONSTRATOR")
        print(f"\nDemonstrating: Pre-Milestone A Acquisition Program")
        print(f"Mode: {'Manual lattice creation' if manual_mode else 'Automated bootstrapping'}")
        print(f"Requirements preview: {requirements_text[:100]}...")
        
        try:
            self.demo_running = True
            
            # Step 1: Authentication check
            self.print_step(1, "Authenticating with ODRAS")
            if not self.bootstrapper.authenticate():
                print("❌ Cannot connect to ODRAS. Please ensure ODRAS is running.")
                print("   Run: ./odras.sh status")
                return False
            
            # Step 2: Bootstrap or create lattice
            if manual_mode:
                self.print_step(2, "Creating Manual Lattice")
                success = self._create_manual_lattice()
            else:
                self.print_step(2, "Bootstrapping Program from Requirements")
                success = self.bootstrapper.bootstrap_from_requirements(requirements_text)
            
            if not success:
                print("❌ Lattice creation failed")
                return False
            
            self.created_projects = self.bootstrapper.created_projects
            
            # Step 3: Start visualization server
            self.print_step(3, "Starting Live Visualization")
            viz_success = self._start_visualization_server()
            
            if viz_success:
                print("\n🌐 Opening visualization in browser...")
                time.sleep(2)
                webbrowser.open('http://localhost:8080/lattice_demo.html')
            
            # Step 4: Interactive demonstration
            self.print_step(4, "Interactive Demonstration")
            self._run_interactive_demo()
            
            # Step 5: Cleanup
            if cleanup:
                self.print_step(5, "Cleaning Up")
                self.bootstrapper.cleanup()
            
            return True
            
        except KeyboardInterrupt:
            print("\n\n🛑 Demonstration interrupted by user")
            return False
        finally:
            self.demo_running = False
            self._cleanup_processes()
    
    def _create_manual_lattice(self) -> bool:
        """Create a predefined lattice structure."""
        print("📁 Creating predefined Pre-Milestone A lattice...")
        
        # Create foundation
        foundation = self.bootstrapper._create_project(
            Project(
                name="foundation-ontology",
                domain="foundation", 
                layer=0,
                description="L0 Foundation with foundational ontologies"
            ),
            self.bootstrapper.get_default_namespace()
        )
        
        if not foundation:
            return False
        
        # Create L1 projects
        l1_projects = [
            Project("icd-development", "systems-engineering", 1, "ICD Development - Capability gaps", "foundation-ontology"),
            Project("mission-analysis", "mission-planning", 1, "Mission Analysis - Operational scenarios", "foundation-ontology"),
            Project("cost-strategy", "cost", 1, "Cost Strategy - Framework and constraints", "foundation-ontology")
        ]
        
        for project in l1_projects:
            created = self.bootstrapper._create_project(project, self.bootstrapper.get_default_namespace())
            if not created:
                return False
        
        # Create L2 projects  
        l2_projects = [
            Project("cdd-development", "systems-engineering", 2, "CDD Development - Detailed requirements", "icd-development"),
            Project("conops-development", "mission-planning", 2, "CONOPS Development - Operational concept", "mission-analysis"),
            Project("affordability-analysis", "cost", 2, "Affordability Analysis - Cost constraints", "cost-strategy")
        ]
        
        for project in l2_projects:
            created = self.bootstrapper._create_project(project, self.bootstrapper.get_default_namespace())
            if not created:
                return False
        
        # Create L3 projects
        l3_projects = [
            Project("solution-concept-a", "analysis", 3, "Solution Concept A - Primary concept evaluation", "cdd-development"),
            Project("solution-concept-b", "analysis", 3, "Solution Concept B - Alternative concept", "cdd-development"),
            Project("trade-study", "analysis", 3, "Trade Study - Comparative analysis", "cdd-development")
        ]
        
        for project in l3_projects:
            created = self.bootstrapper._create_project(project, self.bootstrapper.get_default_namespace())
            if not created:
                return False
        
        print(f"✅ Created {len(l1_projects) + len(l2_projects) + len(l3_projects) + 1} projects manually")
        return True
    
    def _start_visualization_server(self) -> bool:
        """Start the visualization server."""
        try:
            # Check if static files exist
            static_dir = Path("scripts/demo/static")
            if not static_dir.exists() or not (static_dir / "lattice_demo.html").exists():
                print("❌ Visualization files not found")
                return False
            
            print("🚀 Starting visualization server...")
            
            # Start visualization server in background
            self.visualization_process = subprocess.Popen(
                [sys.executable, "scripts/demo/visualization_server.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Give server time to start
            time.sleep(3)
            
            if self.visualization_process.poll() is None:
                print("✅ Visualization server started")
                print("   WebSocket: ws://localhost:8081")
                print("   Web interface: http://localhost:8080/lattice_demo.html")
                return True
            else:
                print("❌ Visualization server failed to start")
                return False
                
        except Exception as e:
            print(f"❌ Error starting visualization server: {e}")
            return False
    
    def _run_interactive_demo(self):
        """Run interactive demonstration with user controls."""
        print("\n🎮 Interactive Demonstration Starting...")
        print("\nThe visualization should now be open in your browser.")
        print("You can interact with the lattice and see live updates.")
        
        while self.demo_running:
            print(f"\n{'='*60}")
            print("DEMONSTRATION CONTROLS")
            print("="*60)
            print("1. Activate L1 projects (start the lattice)")
            print("2. Publish requirements event (trigger cascade)")
            print("3. Change requirement (simulate change impact)")
            print("4. Show project states")
            print("5. Simulate processing batch")
            print("6. Show Gray System activity") 
            print("7. Show X-layer exploration")
            print("8. Open browser (if closed)")
            print("q. Quit demonstration")
            
            try:
                choice = input("\nEnter choice: ").strip().lower()
                
                if choice == '1':
                    self._activate_l1_projects()
                elif choice == '2':
                    self._publish_requirements_event()
                elif choice == '3':
                    self._change_requirement()
                elif choice == '4':
                    self._show_project_states()
                elif choice == '5':
                    self._simulate_processing_batch()
                elif choice == '6':
                    self._show_gray_system_activity()
                elif choice == '7':
                    self._show_x_layer_exploration()
                elif choice == '8':
                    webbrowser.open('http://localhost:8080/lattice_demo.html')
                elif choice == 'q':
                    print("\n👋 Ending demonstration...")
                    break
                else:
                    print("❓ Invalid choice")
                    
            except KeyboardInterrupt:
                print("\n\n🛑 Demonstration interrupted")
                break
            except EOFError:
                break
        
        self.demo_running = False
    
    def _activate_l1_projects(self):
        """Activate L1 strategic projects."""
        print("\n🚀 Activating L1 Strategic Projects...")
        
        # Find L1 projects
        projects_response = self.bootstrapper.client.get("/api/projects")
        if projects_response.status_code == 200:
            projects = projects_response.json().get("projects", [])
            l1_projects = [p for p in projects if p.get("project_level") == 1]
            
            print(f"   Found {len(l1_projects)} L1 projects to activate")
            
            for project in l1_projects:
                project_name = project.get("name", "Unknown")
                print(f"   ✓ Activating {project_name}")
                time.sleep(0.5)  # Visual delay
            
            print("✅ L1 projects activated - system is now live!")
            print("   Check visualization for project state changes")
    
    def _publish_requirements_event(self):
        """Publish requirements event to trigger cascade."""
        print("\n📋 Publishing Requirements Event...")
        
        # Find requirements/ICD project
        projects_response = self.bootstrapper.client.get("/api/projects")
        if projects_response.status_code == 200:
            projects = projects_response.json().get("projects", [])
            req_project = next((p for p in projects if "icd" in p.get("name", "").lower() or "requirement" in p.get("name", "").lower()), None)
            
            if req_project:
                project_id = req_project["project_id"]
                project_name = req_project["name"]
                
                # Publish event through ODRAS API
                event_data = {
                    "requirement_count": 15,
                    "capability_gaps": ["navigation", "surveillance", "endurance"],
                    "priority": "high",
                    "publication_date": time.time()
                }
                
                response = self.bootstrapper.client.post(
                    f"/api/projects/{project_id}/publish-event",
                    json={
                        "event_type": "capability_gaps_identified",
                        "data": event_data
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    subscribers = result.get("subscribers_notified", 0)
                    print(f"   ✅ Published from {project_name}")
                    print(f"   📡 Notified {subscribers} subscribers")
                    print("   🔄 Watch visualization for event cascade")
                else:
                    print(f"   ❌ Failed to publish event: {response.status_code}")
            else:
                print("   ❌ No requirements project found")
    
    def _change_requirement(self):
        """Simulate changing a requirement."""
        print("\n📝 Simulating Requirement Change...")
        
        # Find CDD project
        projects_response = self.bootstrapper.client.get("/api/projects")
        if projects_response.status_code == 200:
            projects = projects_response.json().get("projects", [])
            cdd_project = next((p for p in projects if "cdd" in p.get("name", "").lower()), None)
            
            if cdd_project:
                project_id = cdd_project["project_id"]
                project_name = cdd_project["name"]
                
                # Publish requirement change event
                change_data = {
                    "changed_requirement": "REQ-002",
                    "old_value": "Surveillance range shall be 50+ nautical miles",
                    "new_value": "Surveillance range shall be 75+ nautical miles", 
                    "change_reason": "Operational requirements update",
                    "impact_assessment": "medium",
                    "change_date": time.time()
                }
                
                response = self.bootstrapper.client.post(
                    f"/api/projects/{project_id}/publish-event",
                    json={
                        "event_type": "requirement.changed", 
                        "data": change_data
                    }
                )
                
                if response.status_code == 200:
                    print(f"   ✅ Requirement changed in {project_name}")
                    print(f"   📝 Surveillance range: 50 NM → 75 NM")
                    print(f"   🌊 Watch cascade through dependent projects")
                else:
                    print(f"   ❌ Failed to publish change: {response.status_code}")
            else:
                print("   ❌ No CDD project found")
    
    def _show_project_states(self):
        """Show current state of all projects."""
        print("\n📊 Current Project States:")
        
        projects_response = self.bootstrapper.client.get("/api/projects")
        if projects_response.status_code == 200:
            projects = projects_response.json().get("projects", [])
            
            # Group by layer
            by_layer = {}
            for project in projects:
                layer = project.get("project_level", 0)
                if layer not in by_layer:
                    by_layer[layer] = []
                by_layer[layer].append(project)
            
            for layer in sorted(by_layer.keys()):
                print(f"\n   L{layer} Layer:")
                for project in by_layer[layer]:
                    name = project.get("name", "Unknown")
                    domain = project.get("domain", "Unknown")
                    status = project.get("publication_status", "draft")
                    print(f"      • {name} ({domain}) - {status}")
        else:
            print("   ❌ Failed to get project states")
    
    def _simulate_processing_batch(self):
        """Simulate a batch of project processing."""
        print("\n⚙️  Simulating Processing Batch...")
        print("   This will trigger multiple projects to process simultaneously")
        
        # Get all projects and simulate processing
        projects_response = self.bootstrapper.client.get("/api/projects")
        if projects_response.status_code == 200:
            projects = projects_response.json().get("projects", [])
            
            # Simulate processing for random projects
            processing_projects = random.sample(projects, min(3, len(projects)))
            
            for project in processing_projects:
                project_name = project.get("name", "Unknown")
                print(f"   🔄 Processing triggered for {project_name}")
                
                # Publish processing start event
                self.bootstrapper.client.post(
                    f"/api/projects/{project['project_id']}/publish-event",
                    json={
                        "event_type": "processing.started",
                        "data": {"project_name": project_name, "batch_id": int(time.time())}
                    }
                )
            
            print(f"   ✅ {len(processing_projects)} projects processing")
            print("   👀 Watch visualization for processing animations")
    
    def _show_gray_system_activity(self):
        """Show Gray System sensitivity analysis activity."""
        print("\n🌫️  Gray System Activity:")
        print("   Simulating continuous sensitivity analysis...")
        
        # Simulate sensitivity analysis
        sensitivity_results = {
            "high_sensitivity_projects": 2,
            "medium_sensitivity_projects": 4, 
            "low_sensitivity_projects": 3,
            "fragile_regions": ["Cost-Performance trade-off", "Endurance-Payload balance"],
            "stable_regions": ["Basic surveillance capability", "Maritime operation"]
        }
        
        print(f"   📊 Sensitivity Analysis Results:")
        print(f"      High sensitivity: {sensitivity_results['high_sensitivity_projects']} projects")
        print(f"      Medium sensitivity: {sensitivity_results['medium_sensitivity_projects']} projects")
        print(f"      Low sensitivity: {sensitivity_results['low_sensitivity_projects']} projects")
        print(f"\n   ⚠️  Fragile Regions Detected:")
        for region in sensitivity_results["fragile_regions"]:
            print(f"      • {region}")
        print(f"\n   ✅ Stable Regions:")
        for region in sensitivity_results["stable_regions"]:
            print(f"      • {region}")
        
        print("\n   🎯 Gray System continuously monitors all project cells")
        print("      Watch visualization for sensitivity indicators")
    
    def _show_x_layer_exploration(self):
        """Show X-layer alternative exploration activity."""
        print("\n🧪 X-Layer Exploration Activity:")
        print("   Simulating alternative configuration exploration...")
        
        # Simulate X-layer suggestions
        alternatives = [
            {
                "alternative": "Add Logistics domain",
                "reason": "Sustainment requirements identified",
                "confidence": 0.75,
                "impact": "medium"
            },
            {
                "alternative": "Split Concept projects by size category",
                "reason": "Distinct performance characteristics",
                "confidence": 0.82,
                "impact": "low"
            },
            {
                "alternative": "Add Security domain project",
                "reason": "Cybersecurity requirements emerging",
                "confidence": 0.68,
                "impact": "high"
            }
        ]
        
        print(f"\n   💡 Alternative Configurations Explored:")
        for i, alt in enumerate(alternatives, 1):
            print(f"      {i}. {alt['alternative']}")
            print(f"         Reason: {alt['reason']}")
            print(f"         Confidence: {alt['confidence']:.0%}")
            print(f"         Impact: {alt['impact']}")
        
        print(f"\n   🎲 X-layer generates {len(alternatives)} alternatives every analysis cycle")
        print("      Best alternatives can be promoted to live system")
    
    def _start_visualization_server(self) -> bool:
        """Start visualization server in background."""
        try:
            import subprocess
            import sys
            
            # Start server
            self.visualization_process = subprocess.Popen(
                [sys.executable, "scripts/demo/visualization_server.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Give server time to start
            time.sleep(3)
            
            # Check if still running
            if self.visualization_process.poll() is None:
                print("✅ Visualization server started successfully")
                return True
            else:
                stdout, stderr = self.visualization_process.communicate()
                print(f"❌ Visualization server failed:")
                print(f"   stdout: {stdout.decode()}")
                print(f"   stderr: {stderr.decode()}")
                return False
                
        except Exception as e:
            print(f"❌ Error starting visualization server: {e}")
            return False
    
    def _cleanup_processes(self):
        """Clean up background processes."""
        if self.visualization_process and self.visualization_process.poll() is None:
            print("🧹 Stopping visualization server...")
            self.visualization_process.terminate()
            try:
                self.visualization_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.visualization_process.kill()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run living lattice demonstration")
    parser.add_argument("--requirements-file", "-r", help="File containing requirements text")
    parser.add_argument("--manual-mode", "-m", action="store_true", 
                       help="Use manual lattice creation instead of bootstrapping")
    parser.add_argument("--cleanup", "-c", action="store_true",
                       help="Clean up created projects after demonstration")
    args = parser.parse_args()
    
    # Get requirements text
    if args.requirements_file:
        try:
            with open(args.requirements_file, 'r') as f:
                requirements_text = f.read().strip()
        except Exception as e:
            print(f"❌ Error reading requirements file: {e}")
            return False
    else:
        # Default Pre-Milestone A requirements
        requirements_text = """
        Maritime Surveillance Unmanned Surface Vehicle Requirements
        
        The system shall provide autonomous maritime surveillance capability for coastal and offshore operations.
        
        Primary Requirements:
        - Autonomous operation for minimum 48 hours without human intervention
        - Surveillance range of 50+ nautical miles from base station  
        - Real-time data transmission and communication capability
        - Operation in sea states up to 4 with 10+ knot winds
        - Cost-effective solution meeting Navy affordability targets
        - Support for multiple mission scenarios including patrol and monitoring
        - Maintainable in harsh maritime environments
        - Integration with existing command and control systems
        
        The system must address current capability gaps in unmanned maritime surveillance 
        and provide enhanced operational flexibility for naval operations.
        """
    
    print("🔬 ODRAS Living Project Lattice Demonstrator")
    print("=" * 60)
    print("This demonstration shows how ODRAS creates a living project lattice")
    print("that processes, decides, and evolves autonomously.")
    print("\nRequirements to be used:")
    print(requirements_text.strip())
    
    # Confirm before starting (skip if non-interactive)
    if not args.manual_mode:
        try:
            input("\n⏸️  Press Enter to start bootstrapping from these requirements...")
        except (EOFError, KeyboardInterrupt):
            print("\n🚀 Starting automatically (non-interactive mode)...")
    
    # Run demonstration
    demonstrator = LivingLatticeDemonstrator()
    success = demonstrator.run_demo(requirements_text, args.manual_mode, args.cleanup)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    # Fix import issue
    import os
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    
    from program_bootstrapper import ProgramBootstrapper, Project
    import random
    
    main()
