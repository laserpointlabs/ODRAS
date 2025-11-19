#!/usr/bin/env python3
"""
Workflow Execution with Mock Workbenches

Executes a step-by-step workflow demonstration showing how data flows
through the lattice with mock calculations at each project.

Usage:
    python scripts/demo/execute_workflow.py <scenario_number> [--interactive]
    
    Scenarios:
    1 - Simple 3-project bootstrap
    2 - Aircraft development workflow (FEA)
    3 - Multi-domain program bootstrap
"""

import sys
import argparse
import httpx
import time
import json
from typing import Dict, Optional, Any
from pathlib import Path

ODRAS_BASE_URL = "http://localhost:8000"
USERNAME = "das_service"
PASSWORD = "das_service_2024!"


class MockWorkbench:
    """Mock workbench that performs calculations."""
    
    @staticmethod
    def requirements_workbench(data: Dict) -> Dict:
        """Mock requirements workbench - validates and approves requirements."""
        print("  📋 Requirements Workbench:")
        print(f"     - Validating {data.get('requirement_count', 0)} requirements...")
        time.sleep(0.5)
        print(f"     - Max weight: {data.get('max_weight', 0)} lbs")
        print(f"     - Range: {data.get('range', 0)} miles")
        print("     ✅ Requirements approved!")
        return {
            "status": "approved",
            "requirement_count": data.get("requirement_count", 0),
            "max_weight": data.get("max_weight", 0),
            "range": data.get("range", 0)
        }
    
    @staticmethod
    def loads_workbench(data: Dict) -> Dict:
        """Mock loads workbench - calculates structural loads."""
        print("  🔧 Loads Workbench:")
        max_weight = data.get("max_weight", 0)
        print(f"     - Calculating loads for max weight: {max_weight} lbs...")
        time.sleep(0.5)
        wing_load = max_weight * 0.6  # Mock calculation: 60% on wings
        fuselage_load = max_weight * 0.4  # Mock calculation: 40% on fuselage
        print(f"     - Wing load: {wing_load:.0f} lbs")
        print(f"     - Fuselage load: {fuselage_load:.0f} lbs")
        print("     ✅ Loads calculated!")
        return {
            "wing_load": wing_load,
            "fuselage_load": fuselage_load,
            "max_load": max_weight
        }
    
    @staticmethod
    def fea_workbench(data: Dict) -> Dict:
        """Mock FEA workbench - performs finite element analysis."""
        print("  🧮 FEA Workbench:")
        wing_load = data.get("wing_load", 0)
        fuselage_load = data.get("fuselage_load", 0)
        print(f"     - Analyzing structure with loads: {wing_load:.0f} + {fuselage_load:.0f} = {wing_load + fuselage_load:.0f} lbs")
        time.sleep(0.5)
        # Mock calculation: simple addition (2+2 equivalent)
        total_load = wing_load + fuselage_load
        margin_of_safety = 0.86  # Mock result
        material = "17-4PH"
        mass = total_load / 1000  # Mock mass calculation
        print(f"     - Margin of safety: {margin_of_safety}")
        print(f"     - Material: {material}")
        print(f"     - Mass: {mass:.1f} kg")
        print("     ✅ FEA analysis complete!")
        return {
            "margin_of_safety": margin_of_safety,
            "material": material,
            "mass": mass,
            "total_load": total_load
        }
    
    @staticmethod
    def cost_workbench(data: Dict) -> Dict:
        """Mock cost workbench - estimates cost based on mass/material."""
        print("  💰 Cost Workbench:")
        mass = data.get("mass", 0)
        material = data.get("material", "Unknown")
        print(f"     - Estimating cost for {mass:.1f} kg of {material}...")
        time.sleep(0.5)
        # Mock calculation: cost = mass * material_factor
        material_factors = {"17-4PH": 150, "Aluminum": 50, "Steel": 30}
        factor = material_factors.get(material, 100)
        cost = mass * factor
        print(f"     - Estimated cost: ${cost:.0f}")
        print("     ✅ Cost estimate complete!")
        return {
            "estimated_cost": cost,
            "mass": mass,
            "material": material
        }
    
    @staticmethod
    def strategy_workbench(data: Dict) -> Dict:
        """Mock strategy workbench - develops strategy."""
        print("  📊 Strategy Workbench:")
        print(f"     - Developing strategy for: {data.get('strategy_type', 'unknown')}...")
        time.sleep(0.5)
        print("     ✅ Strategy approved!")
        return {"status": "approved", "strategy_type": data.get("strategy_type")}
    
    @staticmethod
    def tactical_workbench(data: Dict) -> Dict:
        """Mock tactical workbench - creates tactical plan."""
        print("  🎯 Tactical Workbench:")
        print("     - Creating tactical plan...")
        time.sleep(0.5)
        print("     ✅ Tactical plan ready!")
        return {"status": "ready", "tactical_plan": "ready"}
    
    @staticmethod
    def implementation_workbench(data: Dict) -> Dict:
        """Mock implementation workbench - implements solution."""
        print("  🛠️  Implementation Workbench:")
        print("     - Implementing solution...")
        time.sleep(0.5)
        print("     ✅ Implementation complete!")
        return {"status": "complete", "components_delivered": 5}


class WorkflowExecutor:
    """Execute workflow with mock workbenches."""
    
    def __init__(self):
        self.base_url = ODRAS_BASE_URL
        self.client = httpx.Client(base_url=self.base_url, timeout=30.0)
        self.token = None
        self.project_registry = {}
        self.workbench = MockWorkbench()
    
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
    
    def find_project_by_name(self, name: str) -> Optional[Dict]:
        """Find project by name."""
        try:
            response = self.client.get("/api/projects")
            if response.status_code == 200:
                projects = response.json().get("projects", [])
                for project in projects:
                    if project.get("name") == name:
                        return project
            return None
        except Exception:
            return None
    
    def publish_event(self, project_id: str, event_type: str, data: Dict) -> bool:
        """Publish event and return subscribers notified."""
        try:
            response = self.client.post(
                f"/api/projects/{project_id}/publish-event",
                json={"event_type": event_type, "data": data}
            )
            if response.status_code == 200:
                result = response.json()
                return result.get("subscribers_notified", 0)
            return 0
        except Exception:
            return 0
    
    def execute_scenario_1(self, interactive: bool = False):
        """Execute simple 3-project bootstrap workflow."""
        print("\n" + "=" * 70)
        print("SCENARIO 1: Simple 3-Project Bootstrap Workflow")
        print("=" * 70)
        
        # Find projects
        parent = self.find_project_by_name("demo-parent")
        child = self.find_project_by_name("demo-child")
        cousin = self.find_project_by_name("demo-cousin")
        
        if not all([parent, child, cousin]):
            print("❌ Projects not found. Run create_lattice_example_1.py first!")
            return False
        
        print("\n📁 Projects Found:")
        print(f"   - {parent.get('name', 'Unknown')} (L{parent.get('project_level', '?')})")
        print(f"   - {child.get('name', 'Unknown')} (L{child.get('project_level', '?')})")
        print(f"   - {cousin.get('name', 'Unknown')} (L{cousin.get('project_level', '?')})")
        
        if interactive:
            input("\n⏸️  Press Enter to start workflow...")
        
        # Step 1: Parent processes data
        print("\n" + "-" * 70)
        print("STEP 1: Parent Project Processes Data")
        print("-" * 70)
        parent_data = {"data_points": 100, "status": "ready"}
        result = self.workbench.strategy_workbench(parent_data)
        
        # Publish event
        subscribers = self.publish_event(parent["project_id"], "parent.data_ready", result)
        print(f"\n📡 Published 'parent.data_ready' event → {subscribers} subscriber(s) notified")
        
        if interactive:
            input("\n⏸️  Press Enter to continue...")
        
        # Step 2: Child processes
        print("\n" + "-" * 70)
        print("STEP 2: Child Project Processes Parent Data")
        print("-" * 70)
        child_data = result.copy()
        child_result = self.workbench.tactical_workbench(child_data)
        
        # Publish event
        subscribers = self.publish_event(child["project_id"], "child.processed", child_result)
        print(f"\n📡 Published 'child.processed' event → {subscribers} subscriber(s) notified")
        
        if interactive:
            input("\n⏸️  Press Enter to continue...")
        
        # Step 3: Cousin processes
        print("\n" + "-" * 70)
        print("STEP 3: Cousin Project Processes Child Data")
        print("-" * 70)
        cousin_data = child_result.copy()
        cousin_result = self.workbench.cost_workbench(cousin_data)
        
        print("\n✅ Workflow Complete!")
        print("\n📊 Final Results:")
        print(f"   Parent: {result}")
        print(f"   Child: {child_result}")
        print(f"   Cousin: {cousin_result}")
        
        return True
    
    def execute_scenario_2(self, interactive: bool = False):
        """Execute aircraft development workflow."""
        print("\n" + "=" * 70)
        print("SCENARIO 2: Aircraft Development Workflow (FEA Example)")
        print("=" * 70)
        
        # Find projects
        requirements = self.find_project_by_name("aircraft-requirements")
        loads = self.find_project_by_name("aircraft-loads")
        fea = self.find_project_by_name("aircraft-fea")
        cost = self.find_project_by_name("aircraft-cost")
        
        if not all([requirements, loads, fea, cost]):
            print("❌ Projects not found. Run create_lattice_example_2.py first!")
            return False
        
        print("\n📁 Projects Found:")
        print(f"   - {requirements.get('name', 'Unknown')} (L{requirements.get('project_level', '?')})")
        print(f"   - {loads.get('name', 'Unknown')} (L{loads.get('project_level', '?')})")
        print(f"   - {fea.get('name', 'Unknown')} (L{fea.get('project_level', '?')})")
        print(f"   - {cost.get('name', 'Unknown')} (L{cost.get('project_level', '?')})")
        
        if interactive:
            input("\n⏸️  Press Enter to start workflow...")
        
        # Step 1: Requirements
        print("\n" + "-" * 70)
        print("STEP 1: Requirements Project")
        print("-" * 70)
        req_data = {"max_weight": 25000, "range": 3000, "requirement_count": 15}
        req_result = self.workbench.requirements_workbench(req_data)
        subscribers = self.publish_event(requirements["project_id"], "requirements.approved", req_result)
        print(f"\n📡 Published 'requirements.approved' → {subscribers} subscriber(s) notified")
        
        if interactive:
            input("\n⏸️  Press Enter to continue...")
        
        # Step 2: Loads
        print("\n" + "-" * 70)
        print("STEP 2: Loads Analysis Project")
        print("-" * 70)
        loads_data = req_result.copy()
        loads_result = self.workbench.loads_workbench(loads_data)
        subscribers = self.publish_event(loads["project_id"], "loads.calculated", loads_result)
        print(f"\n📡 Published 'loads.calculated' → {subscribers} subscriber(s) notified")
        
        if interactive:
            input("\n⏸️  Press Enter to continue...")
        
        # Step 3: FEA
        print("\n" + "-" * 70)
        print("STEP 3: FEA Analysis Project")
        print("-" * 70)
        fea_data = {**req_result, **loads_result}
        fea_result = self.workbench.fea_workbench(fea_data)
        subscribers = self.publish_event(fea["project_id"], "fea.analysis_complete", fea_result)
        print(f"\n📡 Published 'fea.analysis_complete' → {subscribers} subscriber(s) notified")
        
        if interactive:
            input("\n⏸️  Press Enter to continue...")
        
        # Step 4: Cost
        print("\n" + "-" * 70)
        print("STEP 4: Cost Model Project")
        print("-" * 70)
        cost_data = fea_result.copy()
        cost_result = self.workbench.cost_workbench(cost_data)
        
        print("\n✅ Workflow Complete!")
        print("\n📊 Final Results:")
        print(f"   Requirements: {req_result}")
        print(f"   Loads: {loads_result}")
        print(f"   FEA: {fea_result}")
        print(f"   Cost: {cost_result}")
        
        return True
    
    def execute_scenario_3(self, interactive: bool = False):
        """Execute multi-domain program bootstrap workflow."""
        print("\n" + "=" * 70)
        print("SCENARIO 3: Multi-Domain Program Bootstrap Workflow")
        print("=" * 70)
        
        # Find projects
        foundation = self.find_project_by_name("program-foundation")
        se_strategy = self.find_project_by_name("program-se-strategy")
        cost_strategy = self.find_project_by_name("program-cost-strategy")
        se_tactical = self.find_project_by_name("program-se-tactical")
        cost_analysis = self.find_project_by_name("program-cost-analysis")
        se_impl = self.find_project_by_name("program-se-impl")
        
        if not all([foundation, se_strategy, cost_strategy, se_tactical, cost_analysis, se_impl]):
            print("❌ Projects not found. Run create_lattice_example_3.py first!")
            return False
        
        print("\n📁 Projects Found:")
        for proj in [foundation, se_strategy, cost_strategy, se_tactical, cost_analysis, se_impl]:
            print(f"   - {proj.get('name', 'Unknown')} (L{proj.get('project_level', '?')})")
        
        if interactive:
            input("\n⏸️  Press Enter to start workflow...")
        
        # Step 1: Foundation
        print("\n" + "-" * 70)
        print("STEP 1: Foundation Project")
        print("-" * 70)
        foundation_data = {"program_name": "Multi-Domain Program", "domains": ["systems-engineering", "cost", "logistics"]}
        print("  🏛️  Foundation Workbench:")
        print("     - Establishing program foundation...")
        time.sleep(0.5)
        print("     ✅ Foundation established!")
        subscribers = self.publish_event(foundation["project_id"], "foundation.established", foundation_data)
        print(f"\n📡 Published 'foundation.established' → {subscribers} subscriber(s) notified")
        
        if interactive:
            input("\n⏸️  Press Enter to continue...")
        
        # Step 2: Strategies
        print("\n" + "-" * 70)
        print("STEP 2: Strategy Projects")
        print("-" * 70)
        se_strategy_result = self.workbench.strategy_workbench({"strategy_type": "systems-engineering"})
        self.publish_event(se_strategy["project_id"], "strategy.approved", se_strategy_result)
        
        cost_strategy_result = self.workbench.strategy_workbench({"strategy_type": "cost"})
        self.publish_event(cost_strategy["project_id"], "strategy.approved", cost_strategy_result)
        
        if interactive:
            input("\n⏸️  Press Enter to continue...")
        
        # Step 3: Tactical
        print("\n" + "-" * 70)
        print("STEP 3: Tactical Project")
        print("-" * 70)
        tactical_result = self.workbench.tactical_workbench(se_strategy_result)
        subscribers = self.publish_event(se_tactical["project_id"], "tactical.ready", tactical_result)
        print(f"\n📡 Published 'tactical.ready' → {subscribers} subscriber(s) notified")
        
        if interactive:
            input("\n⏸️  Press Enter to continue...")
        
        # Step 4: Implementation
        print("\n" + "-" * 70)
        print("STEP 4: Implementation Project")
        print("-" * 70)
        impl_result = self.workbench.implementation_workbench(tactical_result)
        subscribers = self.publish_event(se_impl["project_id"], "implementation.complete", impl_result)
        print(f"\n📡 Published 'implementation.complete' → {subscribers} subscriber(s) notified")
        
        # Step 5: Cost Analysis (subscribes to both tactical and implementation)
        print("\n" + "-" * 70)
        print("STEP 5: Cost Analysis Project")
        print("-" * 70)
        cost_data = {**tactical_result, **impl_result}
        cost_result = self.workbench.cost_workbench(cost_data)
        
        print("\n✅ Workflow Complete!")
        print("\n📊 Final Results:")
        print(f"   SE Strategy: {se_strategy_result}")
        print(f"   Cost Strategy: {cost_strategy_result}")
        print(f"   SE Tactical: {tactical_result}")
        print(f"   SE Implementation: {impl_result}")
        print(f"   Cost Analysis: {cost_result}")
        
        return True
    
    def run(self, scenario: int, interactive: bool = False):
        """Run workflow execution."""
        if not self.authenticate():
            print("❌ Authentication failed")
            return False
        
        if scenario == 1:
            return self.execute_scenario_1(interactive)
        elif scenario == 2:
            return self.execute_scenario_2(interactive)
        elif scenario == 3:
            return self.execute_scenario_3(interactive)
        else:
            print(f"❌ Unknown scenario: {scenario}")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Execute workflow with mock workbenches")
    parser.add_argument("scenario", type=int, choices=[1, 2, 3], help="Scenario number (1, 2, or 3)")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode (pause between steps)")
    args = parser.parse_args()
    
    executor = WorkflowExecutor()
    success = executor.run(args.scenario, args.interactive)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

