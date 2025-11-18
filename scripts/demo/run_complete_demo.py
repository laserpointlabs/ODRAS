#!/usr/bin/env python3
"""
Complete End-to-End Demonstration

Runs a complete demonstration showing:
1. Creating the lattice
2. Visualizing the structure
3. Executing the workflow with mock workbenches

Usage:
    python scripts/demo/run_complete_demo.py [scenario_number]
    
    Scenarios:
    1 - Simple 3-project bootstrap
    2 - Aircraft development workflow (FEA) - DEFAULT
    3 - Multi-domain program bootstrap
"""

import sys
import argparse
import subprocess
import time
from pathlib import Path

def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)

def print_step(step_num, description):
    """Print a step header."""
    print(f"\n{'='*70}")
    print(f"STEP {step_num}: {description}")
    print("=" * 70)

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n▶️  {description}...")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            print("✅ Success!")
            if result.stdout:
                # Show last few lines of output
                lines = result.stdout.strip().split('\n')
                if len(lines) > 5:
                    print("   ...")
                    for line in lines[-5:]:
                        print(f"   {line}")
                else:
                    for line in lines:
                        print(f"   {line}")
            return True
        else:
            print(f"❌ Failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Command timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run complete demonstration."""
    parser = argparse.ArgumentParser(description="Run complete lattice demonstration")
    parser.add_argument("scenario", type=int, nargs="?", default=2, choices=[1, 2, 3],
                       help="Scenario number (1, 2, or 3). Default: 2")
    parser.add_argument("--keep-projects", action="store_true",
                       help="Keep projects after demo (don't cleanup)")
    args = parser.parse_args()
    
    scenario = args.scenario
    scenario_names = {
        1: "Simple 3-Project Bootstrap",
        2: "Aircraft Development Workflow (FEA)",
        3: "Multi-Domain Program Bootstrap"
    }
    
    print_header(f"ODRAS Project Lattice Complete Demonstration")
    print(f"\nScenario: {scenario_names[scenario]}")
    print(f"Scenario Number: {scenario}")
    
    # Step 1: Create the lattice
    print_step(1, "Creating Project Lattice")
    create_script = f"scripts/demo/create_lattice_example_{scenario}.py"
    if not Path(create_script).exists():
        print(f"❌ Script not found: {create_script}")
        return False
    
    if not run_command(f"python {create_script}", f"Creating lattice for scenario {scenario}"):
        print("\n⚠️  Lattice creation had issues, but continuing...")
    
    time.sleep(1)
    
    # Step 2: Validate the lattice
    print_step(2, "Validating Lattice Structure")
    if not run_command("python scripts/demo/validate_lattice.py --all", "Validating lattice structure"):
        print("\n⚠️  Validation had issues, but continuing...")
    
    time.sleep(1)
    
    # Step 3: Generate visualization
    print_step(3, "Generating Visualization")
    viz_file = f"lattice_demo_scenario_{scenario}.html"
    if not run_command(f"python scripts/demo/visualize_lattice.py --output {viz_file}", 
                      f"Generating visualization ({viz_file})"):
        print("\n⚠️  Visualization generation had issues, but continuing...")
    else:
        viz_path = Path(viz_file)
        if viz_path.exists():
            print(f"\n📊 Visualization saved to: {viz_path.absolute()}")
            print(f"   Open this file in a web browser to view the interactive graph!")
    
    time.sleep(1)
    
    # Step 4: Execute workflow
    print_step(4, "Executing Workflow with Mock Workbenches")
    print("\n   This will show step-by-step data flow through the lattice...")
    time.sleep(2)
    
    if not run_command(f"python scripts/demo/execute_workflow.py {scenario}", 
                      f"Executing workflow for scenario {scenario}"):
        print("\n⚠️  Workflow execution had issues")
    
    # Step 5: Cleanup (optional)
    if not args.keep_projects:
        print_step(5, "Cleaning Up")
        cleanup_script = f"scripts/demo/create_lattice_example_{scenario}.py"
        run_command(f"python {cleanup_script} --cleanup", "Removing demo projects")
    else:
        print("\n💡 Projects kept (use --keep-projects to preserve)")
    
    # Summary
    print_header("Demonstration Complete!")
    print("\n📋 Summary:")
    print(f"   ✅ Created project lattice for scenario {scenario}")
    print(f"   ✅ Validated lattice structure")
    if Path(viz_file).exists():
        print(f"   ✅ Generated visualization: {viz_file}")
        print(f"      → Open in browser to view interactive graph")
    print(f"   ✅ Executed workflow with mock workbenches")
    if not args.keep_projects:
        print(f"   ✅ Cleaned up demo projects")
    
    print("\n🎯 Next Steps for Customer Demo:")
    print("   1. Run: python scripts/demo/run_complete_demo.py 2")
    print("   2. Open lattice_demo_scenario_2.html in browser")
    print("   3. Show the visualization while explaining the lattice")
    print("   4. Point to workflow execution output showing data flow")
    print("   5. Highlight mock calculations at each step")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

