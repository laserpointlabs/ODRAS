#!/usr/bin/env python3
"""
Requirements Test Script

Allows you to review, delete, and add test requirements to the Requirements Workbench database.
This script performs HARD DELETE operations - use with caution!

Usage:
  python scripts/requirements_test.py                # Interactive mode
  python scripts/requirements_test.py batch          # Delete all (with confirmation)
  python scripts/requirements_test.py batch force    # Delete all (no confirmation)
  python scripts/requirements_test.py add            # Add 10 test requirements
  python scripts/requirements_test.py add-constraints # Add equation constraints to requirements
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import uuid
import json

def get_db_connection():
    """Get database connection using docker-compose credentials."""
    try:
        conn = psycopg2.connect(
            host='localhost',
            port='5432',
            database='odras',
            user='postgres',
            password='password'
        )
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return None

def list_all_requirements():
    """List all requirements in the database."""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    re.requirement_id,
                    re.project_id,
                    re.requirement_identifier,
                    re.requirement_title,
                    re.requirement_type,
                    re.state,
                    re.priority,
                    re.created_at,
                    p.name as project_name,
                    u.username as created_by_username
                FROM requirements_enhanced re
                LEFT JOIN projects p ON re.project_id = p.project_id
                LEFT JOIN users u ON re.created_by = u.user_id
                ORDER BY re.created_at DESC
            """)
            
            requirements = cursor.fetchall()
            return [dict(req) for req in requirements]
    
    except Exception as e:
        print(f"❌ Error listing requirements: {e}")
        return []
    finally:
        conn.close()

def display_requirements(requirements):
    """Display requirements in a readable format."""
    if not requirements:
        print("📝 No requirements found in the database.")
        return
    
    print(f"\n📝 Found {len(requirements)} requirements in the database:\n")
    print("=" * 120)
    print(f"{'#':<3} {'ID':<8} {'Project':<20} {'Identifier':<15} {'Title':<30} {'Type':<12} {'State':<10} {'Created':<12}")
    print("=" * 120)
    
    for i, req in enumerate(requirements, 1):
        req_id_short = req['requirement_id'][:8] if req['requirement_id'] else 'N/A'
        project_name = req['project_name'][:18] if req['project_name'] else 'Unknown'
        identifier = req['requirement_identifier'][:13] if req['requirement_identifier'] else 'N/A'
        title = req['requirement_title'][:28] if req['requirement_title'] else 'N/A'
        req_type = req['requirement_type'][:10] if req['requirement_type'] else 'N/A'
        state = req['state'] if req['state'] else 'N/A'
        created = req['created_at'].strftime('%Y-%m-%d') if req['created_at'] else 'N/A'
        
        print(f"{i:<3} {req_id_short:<8} {project_name:<20} {identifier:<15} {title:<30} {req_type:<12} {state:<10} {created:<12}")

def delete_requirement(requirement_id, requirement_identifier):
    """Delete a requirement and its constraints from the database."""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cursor:
            # First delete constraints (foreign key dependency)
            cursor.execute("""
                DELETE FROM requirements_constraints 
                WHERE requirement_id = %s
            """, (requirement_id,))
            constraints_deleted = cursor.rowcount
            
            # Then delete the requirement
            cursor.execute("""
                DELETE FROM requirements_enhanced 
                WHERE requirement_id = %s
            """, (requirement_id,))
            requirements_deleted = cursor.rowcount
            
            if requirements_deleted > 0:
                conn.commit()
                print(f"✅ Deleted requirement '{requirement_identifier}' and {constraints_deleted} associated constraints")
                return True
            else:
                print(f"❌ Requirement '{requirement_identifier}' not found")
                return False
    
    except Exception as e:
        conn.rollback()
        print(f"❌ Error deleting requirement '{requirement_identifier}': {e}")
        return False
    finally:
        conn.close()

def delete_all_requirements_for_project(project_id, project_name):
    """Delete all requirements for a specific project."""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cursor:
            # First get count
            cursor.execute("""
                SELECT COUNT(*) FROM requirements_enhanced 
                WHERE project_id = %s
            """, (project_id,))
            count = cursor.fetchone()[0]
            
            if count == 0:
                print(f"📝 No requirements found for project '{project_name}'")
                return True
            
            # Delete constraints first
            cursor.execute("""
                DELETE FROM requirements_constraints 
                WHERE requirement_id IN (
                    SELECT requirement_id FROM requirements_enhanced 
                    WHERE project_id = %s
                )
            """, (project_id,))
            constraints_deleted = cursor.rowcount
            
            # Then delete requirements
            cursor.execute("""
                DELETE FROM requirements_enhanced 
                WHERE project_id = %s
            """, (project_id,))
            requirements_deleted = cursor.rowcount
            
            conn.commit()
            print(f"✅ Deleted {requirements_deleted} requirements and {constraints_deleted} constraints from project '{project_name}'")
            return True
    
    except Exception as e:
        conn.rollback()
        print(f"❌ Error deleting requirements for project '{project_name}': {e}")
        return False
    finally:
        conn.close()

def get_test_requirements():
    """Return a list of 10 clean, simple UAS disaster response requirements."""
    return [
        {
            "identifier": "DRUAS-001",
            "title": "Coverage Rate Capability",
            "text": "The UAS SHALL be capable of surveying 5-10 square kilometers within 2 hours for systematic disaster area assessment."
        },
        {
            "identifier": "DRUAS-002", 
            "title": "Grid Accuracy Level",
            "text": "The UAS MUST provide the ability to fly in precise grid patterns with accuracy within ±10 meters for comprehensive coverage."
        },
        {
            "identifier": "DRUAS-003",
            "title": "Wind Operations Tolerance",
            "text": "The UAS MUST operate in winds up to 25 knots to ensure operational capability during adverse weather conditions."
        },
        {
            "identifier": "DRUAS-004",
            "title": "Temperature Range Operations", 
            "text": "The UAS SHALL be operational in temperatures from -10°C to +45°C to support diverse environmental disaster scenarios."
        },
        {
            "identifier": "DRUAS-005",
            "title": "Deployment Time Requirement",
            "text": "The UAS SHALL be ready for flight within 15 minutes of arrival on scene to enable rapid emergency response."
        },
        {
            "identifier": "DRUAS-006",
            "title": "Endurance Duration Capability",
            "text": "The UAS SHALL maintain a minimum of 3 hours continuous operation without refueling or battery change for extended missions."
        },
        {
            "identifier": "DRUAS-007", 
            "title": "Operational Radius Range",
            "text": "The UAS SHALL maintain a minimum 50 km operational radius from the ground control station for wide-area coverage."
        },
        {
            "identifier": "DRUAS-008",
            "title": "Communications Security and Range", 
            "text": "The UAS MUST maintain a minimum 50 km line-of-sight secure encrypted data link for reliable command and control."
        },
        {
            "identifier": "DRUAS-009",
            "title": "Sensor Suite (EO/IR Stabilized)",
            "text": "The UAS MUST be equipped with a high-resolution visible light camera and IR camera with 3-axis gimbal stabilization."
        },
        {
            "identifier": "DRUAS-010",
            "title": "Crew and Training Requirements",
            "text": "The UAS MUST be deployable and operable by a maximum of 2 personnel with training not exceeding 40 hours."
        }
    ]

def add_test_requirements():
    """Add 10 test requirements to the database."""
    conn = get_db_connection()
    if not conn:
        return False
    
    # Get the project ID for core.se
    project_id = "37c945eb-7d3a-40cd-a8d6-75fc236bfce1"
    
    try:
        test_requirements = get_test_requirements()
        
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Verify project exists
            cursor.execute("SELECT name FROM projects WHERE project_id = %s", (project_id,))
            project = cursor.fetchone()
            if not project:
                print(f"❌ Project {project_id} not found")
                return False
            
            print(f"📝 Adding {len(test_requirements)} test requirements to project '{project['name']}'...")
            
            added_count = 0
            for req in test_requirements:
                try:
                    # Generate new requirement ID
                    req_id = str(uuid.uuid4())
                    
                    # Insert requirement with required fields and good defaults
                    cursor.execute("""
                        INSERT INTO requirements_enhanced (
                            requirement_id,
                            project_id,
                            requirement_identifier,
                            requirement_title,
                            requirement_text,
                            requirement_type,
                            priority,
                            state,
                            created_at,
                            updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                        )
                    """, (
                        req_id,
                        project_id,
                        req["identifier"],
                        req["title"], 
                        req["text"],
                        'functional',  # Default requirement type
                        'medium',      # Default priority
                        'draft'        # Default state
                    ))
                    
                    added_count += 1
                    print(f"✅ Added {req['identifier']}: {req['title']}")
                    
                except Exception as e:
                    print(f"❌ Failed to add {req['identifier']}: {e}")
            
            conn.commit()
            print(f"\n✅ Successfully added {added_count}/{len(test_requirements)} test requirements")
            return True
    
    except Exception as e:
        conn.rollback()
        print(f"❌ Error adding test requirements: {e}")
        return False
    finally:
        conn.close()

def get_equation_constraints():
    """Return equation constraints for each UAS requirement."""
    return {
        "DRUAS-001": {
            "constraint_name": "Coverage Rate Calculation",
            "constraint_description": "Mathematical relationship between survey area, flight speed, and time",
            "equation_expression": "coverage_rate = (flight_speed * swath_width * efficiency_factor) / 3600",
            "equation_parameters": {
                "coverage_rate": {"unit": "km²/hour", "description": "Area coverage rate", "min_value": 2.5},
                "flight_speed": {"unit": "m/s", "description": "UAS ground speed", "typical_value": 15},
                "swath_width": {"unit": "m", "description": "Sensor footprint width", "typical_value": 200},
                "efficiency_factor": {"unit": "dimensionless", "description": "Mission efficiency factor", "typical_value": 0.85}
            }
        },
        "DRUAS-002": {
            "constraint_name": "Grid Pattern Accuracy",
            "constraint_description": "Position accuracy calculation based on GPS, IMU, and atmospheric conditions",
            "equation_expression": "position_error = sqrt(gps_error^2 + imu_drift^2 + wind_drift^2)",
            "equation_parameters": {
                "position_error": {"unit": "m", "description": "Total position error", "max_value": 10},
                "gps_error": {"unit": "m", "description": "GPS horizontal accuracy", "typical_value": 3},
                "imu_drift": {"unit": "m", "description": "IMU accumulated drift", "typical_value": 2},
                "wind_drift": {"unit": "m", "description": "Wind-induced position error", "max_value": 5}
            }
        },
        "DRUAS-003": {
            "constraint_name": "Wind Load Resistance",
            "constraint_description": "Maximum sustainable wind load based on UAS mass and aerodynamic properties",
            "equation_expression": "max_wind_speed = sqrt((2 * max_thrust) / (air_density * drag_coefficient * frontal_area))",
            "equation_parameters": {
                "max_wind_speed": {"unit": "m/s", "description": "Maximum operational wind speed", "min_value": 12.86},
                "max_thrust": {"unit": "N", "description": "Maximum available thrust", "typical_value": 400},
                "air_density": {"unit": "kg/m³", "description": "Air density at operating altitude", "typical_value": 1.225},
                "drag_coefficient": {"unit": "dimensionless", "description": "UAS drag coefficient", "typical_value": 0.8},
                "frontal_area": {"unit": "m²", "description": "UAS frontal area", "typical_value": 0.5}
            }
        },
        "DRUAS-004": {
            "constraint_name": "Battery Performance vs Temperature",
            "constraint_description": "Battery capacity degradation with temperature variation",
            "equation_expression": "effective_capacity = nominal_capacity * (1 - temp_derating_factor * abs(temp - optimal_temp))",
            "equation_parameters": {
                "effective_capacity": {"unit": "Wh", "description": "Temperature-adjusted battery capacity", "min_value": 3000},
                "nominal_capacity": {"unit": "Wh", "description": "Rated battery capacity", "typical_value": 5000},
                "temp_derating_factor": {"unit": "1/°C", "description": "Capacity reduction per degree", "typical_value": 0.02},
                "temp": {"unit": "°C", "description": "Operating temperature", "min_value": -10, "max_value": 45},
                "optimal_temp": {"unit": "°C", "description": "Optimal battery temperature", "typical_value": 20}
            }
        },
        "DRUAS-005": {
            "constraint_name": "Deployment Time Components",
            "constraint_description": "Total system deployment time breakdown",
            "equation_expression": "total_deployment_time = setup_time + pre_flight_check_time + mission_planning_time",
            "equation_parameters": {
                "total_deployment_time": {"unit": "minutes", "description": "Total deployment time", "max_value": 15},
                "setup_time": {"unit": "minutes", "description": "Physical setup time", "typical_value": 8},
                "pre_flight_check_time": {"unit": "minutes", "description": "System checks time", "typical_value": 4},
                "mission_planning_time": {"unit": "minutes", "description": "Route planning time", "typical_value": 3}
            }
        },
        "DRUAS-006": {
            "constraint_name": "Flight Endurance Calculation",
            "constraint_description": "Flight time based on battery capacity and power consumption",
            "equation_expression": "flight_time = (battery_capacity * discharge_efficiency) / average_power_consumption",
            "equation_parameters": {
                "flight_time": {"unit": "hours", "description": "Mission duration", "min_value": 3},
                "battery_capacity": {"unit": "Wh", "description": "Total battery energy", "typical_value": 5000},
                "discharge_efficiency": {"unit": "dimensionless", "description": "Battery discharge efficiency", "typical_value": 0.9},
                "average_power_consumption": {"unit": "W", "description": "Average system power draw", "typical_value": 1200}
            }
        },
        "DRUAS-007": {
            "constraint_name": "Communication Range Calculation",
            "constraint_description": "Line-of-sight communication range based on antenna height and Earth curvature",
            "equation_expression": "max_range = 1.23 * (sqrt(h_ground) + sqrt(h_aircraft))",
            "equation_parameters": {
                "max_range": {"unit": "km", "description": "Maximum communication range", "min_value": 50},
                "h_ground": {"unit": "m", "description": "Ground station antenna height", "typical_value": 10},
                "h_aircraft": {"unit": "m", "description": "Aircraft altitude AGL", "typical_value": 1000}
            }
        },
        "DRUAS-008": {
            "constraint_name": "Link Budget Analysis",
            "constraint_description": "Communication link margin calculation for reliable data transmission",
            "equation_expression": "link_margin = tx_power + tx_gain + rx_gain - path_loss - implementation_loss - required_snr",
            "equation_parameters": {
                "link_margin": {"unit": "dB", "description": "Communication link margin", "min_value": 10},
                "tx_power": {"unit": "dBm", "description": "Transmitter power", "typical_value": 30},
                "tx_gain": {"unit": "dBi", "description": "Transmit antenna gain", "typical_value": 12},
                "rx_gain": {"unit": "dBi", "description": "Receive antenna gain", "typical_value": 12},
                "path_loss": {"unit": "dB", "description": "Free space path loss", "typical_value": 140},
                "implementation_loss": {"unit": "dB", "description": "System losses", "typical_value": 6},
                "required_snr": {"unit": "dB", "description": "Required signal-to-noise ratio", "typical_value": 12}
            }
        },
        "DRUAS-009": {
            "constraint_name": "Sensor Resolution vs Altitude",
            "constraint_description": "Ground sample distance calculation for imaging sensors",
            "equation_expression": "ground_sample_distance = (altitude * pixel_size) / focal_length",
            "equation_parameters": {
                "ground_sample_distance": {"unit": "cm", "description": "Ground resolution per pixel", "max_value": 5},
                "altitude": {"unit": "m", "description": "Aircraft altitude AGL", "typical_value": 300},
                "pixel_size": {"unit": "μm", "description": "Sensor pixel size", "typical_value": 2.4},
                "focal_length": {"unit": "mm", "description": "Camera focal length", "typical_value": 35}
            }
        },
        "DRUAS-010": {
            "constraint_name": "Training Effectiveness Model",
            "constraint_description": "Required training hours based on system complexity and operator experience",
            "equation_expression": "training_hours = base_training_hours * complexity_factor * (1 - experience_factor)",
            "equation_parameters": {
                "training_hours": {"unit": "hours", "description": "Total required training time", "max_value": 40},
                "base_training_hours": {"unit": "hours", "description": "Baseline training requirement", "typical_value": 50},
                "complexity_factor": {"unit": "dimensionless", "description": "System complexity multiplier", "typical_value": 0.9},
                "experience_factor": {"unit": "dimensionless", "description": "Operator experience reduction factor", "typical_value": 0.1}
            }
        }
    }

def add_equation_constraints_to_requirements():
    """Add equation constraints to all existing requirements."""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        equation_constraints = get_equation_constraints()
        
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get all current requirements
            cursor.execute("""
                SELECT requirement_id, requirement_identifier 
                FROM requirements_enhanced 
                WHERE requirement_identifier LIKE 'DRUAS-%'
                ORDER BY requirement_identifier
            """)
            requirements = cursor.fetchall()
            
            if not requirements:
                print("❌ No DRUAS requirements found to add constraints to")
                return False
            
            print(f"📊 Adding equation constraints to {len(requirements)} requirements...")
            
            added_count = 0
            for req in requirements:
                req_id = req['requirement_identifier']
                if req_id in equation_constraints:
                    constraint_data = equation_constraints[req_id]
                    
                    try:
                        # Insert the equation constraint
                        constraint_id = str(uuid.uuid4())
                        cursor.execute("""
                            INSERT INTO requirements_constraints (
                                constraint_id,
                                requirement_id,
                                constraint_type,
                                constraint_name,
                                constraint_description,
                                value_type,
                                equation_expression,
                                equation_parameters,
                                priority,
                                created_at,
                                updated_at
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                            )
                        """, (
                            constraint_id,
                            req['requirement_id'],
                            'equation',
                            constraint_data['constraint_name'],
                            constraint_data['constraint_description'],
                            'equation',
                            constraint_data['equation_expression'],
                            json.dumps(constraint_data['equation_parameters']),
                            'high'
                        ))
                        
                        added_count += 1
                        print(f"✅ Added equation constraint to {req_id}: {constraint_data['constraint_name']}")
                        
                    except Exception as e:
                        print(f"❌ Failed to add constraint to {req_id}: {e}")
                else:
                    print(f"⚠️  No equation constraint defined for {req_id}")
            
            conn.commit()
            print(f"\n✅ Successfully added {added_count} equation constraints")
            return True
    
    except Exception as e:
        conn.rollback()
        print(f"❌ Error adding equation constraints: {e}")
        return False
    finally:
        conn.close()

def main():
    """Main interactive menu."""
    print("🧹 ODRAS Requirements Test Tool")
    print("⚠️  WARNING: This tool performs HARD DELETE operations!")
    print("=" * 60)
    
    while True:
        print("\nOptions:")
        print("1. List all requirements")
        print("2. Delete specific requirement(s)")
        print("3. Delete all requirements for a project")
        print("4. Add 10 test requirements")
        print("5. Add equation constraints to requirements")
        print("6. Exit")
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == '1':
            print("\n🔍 Loading requirements...")
            requirements = list_all_requirements()
            display_requirements(requirements)
            
        elif choice == '2':
            requirements = list_all_requirements()
            if not requirements:
                continue
                
            display_requirements(requirements)
            
            while True:
                selection = input(f"\nEnter requirement number(s) to delete (1-{len(requirements)}, comma-separated, or 'back'): ").strip()
                if selection.lower() == 'back':
                    break
                
                try:
                    indices = [int(x.strip()) - 1 for x in selection.split(',')]
                    if all(0 <= i < len(requirements) for i in indices):
                        selected_reqs = [requirements[i] for i in indices]
                        
                        print("\n⚠️  You are about to DELETE the following requirements:")
                        for req in selected_reqs:
                            print(f"  - {req['requirement_identifier']}: {req['requirement_title']}")
                        
                        confirm = input("\nType 'DELETE' to confirm: ").strip()
                        if confirm == 'DELETE':
                            deleted_count = 0
                            for req in selected_reqs:
                                if delete_requirement(req['requirement_id'], req['requirement_identifier']):
                                    deleted_count += 1
                            print(f"\n✅ Successfully deleted {deleted_count}/{len(selected_reqs)} requirements")
                        else:
                            print("❌ Operation cancelled")
                        break
                    else:
                        print("❌ Invalid selection. Please enter valid numbers.")
                except ValueError:
                    print("❌ Invalid format. Please enter numbers separated by commas.")
        
        elif choice == '3':
            requirements = list_all_requirements()
            if not requirements:
                continue
            
            # Get unique projects
            projects = {}
            for req in requirements:
                if req['project_id'] not in projects:
                    projects[req['project_id']] = {
                        'name': req['project_name'] or 'Unknown',
                        'count': 0
                    }
                projects[req['project_id']]['count'] += 1
            
            if not projects:
                print("📝 No projects with requirements found.")
                continue
            
            print(f"\n📁 Projects with requirements:")
            project_list = list(projects.items())
            for i, (project_id, info) in enumerate(project_list, 1):
                print(f"{i}. {info['name']} ({info['count']} requirements)")
            
            selection = input(f"\nSelect project number (1-{len(project_list)}) or 'back': ").strip()
            if selection.lower() == 'back':
                continue
            
            try:
                project_idx = int(selection) - 1
                if 0 <= project_idx < len(project_list):
                    project_id, project_info = project_list[project_idx]
                    
                    print(f"\n⚠️  You are about to DELETE ALL {project_info['count']} requirements from project '{project_info['name']}'")
                    confirm = input("\nType 'DELETE ALL' to confirm: ").strip()
                    
                    if confirm == 'DELETE ALL':
                        delete_all_requirements_for_project(project_id, project_info['name'])
                    else:
                        print("❌ Operation cancelled")
                else:
                    print("❌ Invalid selection.")
            except ValueError:
                print("❌ Invalid format. Please enter a number.")
        
        elif choice == '4':
            print("\n📝 Adding test requirements...")
            add_test_requirements()
            
        elif choice == '5':
            print("\n📊 Adding equation constraints...")
            add_equation_constraints_to_requirements()
            
        elif choice == '6':
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice. Please select 1-6.")

def run_batch_cleanup(force=False):
    """Run batch cleanup - delete all requirements."""
    print("🧹 ODRAS Requirements Cleanup Tool - BATCH MODE")
    print("⚠️  WARNING: This will delete ALL requirements!")
    print("=" * 60)
    
    requirements = list_all_requirements()
    if not requirements:
        print("📝 No requirements found in the database.")
        return
    
    print(f"Found {len(requirements)} requirements to delete:")
    for req in requirements:
        print(f"  - {req['requirement_identifier']}: {req['requirement_title'][:50]}...")
    
    if force:
        print("\n🔥 FORCE MODE: Deleting all requirements without confirmation...")
        deleted_count = 0
        for req in requirements:
            if delete_requirement(req['requirement_id'], req['requirement_identifier']):
                deleted_count += 1
        print(f"\n✅ Successfully deleted {deleted_count}/{len(requirements)} requirements")
    else:
        try:
            confirm = input(f"\n⚠️  Type 'DELETE ALL {len(requirements)} REQUIREMENTS' to confirm: ").strip()
            if confirm == f'DELETE ALL {len(requirements)} REQUIREMENTS':
                deleted_count = 0
                for req in requirements:
                    if delete_requirement(req['requirement_id'], req['requirement_identifier']):
                        deleted_count += 1
                print(f"\n✅ Successfully deleted {deleted_count}/{len(requirements)} requirements")
            else:
                print("❌ Operation cancelled")
        except EOFError:
            print("\n❌ Non-interactive mode detected. Use 'force' flag to delete without confirmation.")
            print("Example: python scripts/requirements_test.py batch force")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == 'batch':
            force = len(sys.argv) > 2 and sys.argv[2] == 'force'
            run_batch_cleanup(force=force)
        elif sys.argv[1] == 'add':
            print("🧹 ODRAS Requirements Test Tool - ADD MODE")
            print("=" * 60)
            add_test_requirements()
        elif sys.argv[1] == 'add-constraints':
            print("🧹 ODRAS Requirements Test Tool - ADD CONSTRAINTS MODE")
            print("=" * 60)
            add_equation_constraints_to_requirements()
        else:
            print("❌ Invalid command. Use: batch, batch force, add, or add-constraints")
    else:
        main()
