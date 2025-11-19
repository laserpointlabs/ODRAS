#!/usr/bin/env python3
"""
Demonstration: Bootstrap Projects from Requirements

Shows the complete flow:
1. Input requirements text
2. System analyzes and creates project lattice
3. Projects appear in visualization

Usage:
    python scripts/demo/demo_bootstrap_flow.py [requirements_file]
"""

import sys
from program_bootstrapper import ProgramBootstrapper

def main():
    print("=" * 80)
    print("ODRAS PROJECT LATTICE BOOTSTRAPPING DEMONSTRATION")
    print("=" * 80)
    print("\nThis demonstrates how ODRAS grows a project lattice from requirements.")
    print("Projects are created as computational cells that process and decide.\n")
    
    # Get requirements
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            requirements = f.read()
    else:
        # Default example
        requirements = """
        Maritime Surveillance Unmanned Surface Vehicle Requirements
        
        The system shall provide autonomous maritime surveillance capability for coastal operations.
        
        Primary Requirements:
        - Autonomous operation for minimum 48 hours without human intervention
        - Surveillance range of 50+ nautical miles from base station  
        - Real-time data transmission and communication capability
        - Operation in sea states up to 4 with 10+ knot winds
        - Cost-effective solution meeting Navy affordability targets
        - Support for multiple mission scenarios including patrol and monitoring
        - Maintainable in harsh maritime environments
        """
    
    print("📋 REQUIREMENTS INPUT:")
    print("-" * 80)
    print(requirements.strip())
    print("-" * 80)
    
    print("\n🚀 BOOTSTRAPPING PROJECT LATTICE...")
    print("   (Analyzing requirements and creating projects)\n")
    
    # Bootstrap
    bootstrapper = ProgramBootstrapper()
    
    if not bootstrapper.authenticate():
        print("❌ Cannot connect to ODRAS. Please ensure ODRAS is running.")
        print("   Run: ./odras.sh status")
        return False
    
    success = bootstrapper.bootstrap_from_requirements(requirements.strip())
    
    if success:
        print("\n" + "=" * 80)
        print("✅ BOOTSTRAPPING COMPLETE!")
        print("=" * 80)
        print(f"\n📊 Created {len(bootstrapper.created_projects)} projects")
        print("\n📋 NEXT STEPS:")
        print("   1. Open visualization: http://localhost:8082/lattice_demo.html")
        print("   2. Projects should appear in grid layout (L0-L3 vertical, domains horizontal)")
        print("   3. Click projects to see details")
        print("   4. Use 'Simulate Event' button to trigger event flow")
        print("\n💡 The lattice shows:")
        print("   • Projects as computational cells (not just data stores)")
        print("   • Parent-child relationships (vertical)")
        print("   • Cousin relationships (horizontal)")
        print("   • Event subscriptions for real-time coordination")
        return True
    else:
        print("\n❌ Bootstrapping failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
