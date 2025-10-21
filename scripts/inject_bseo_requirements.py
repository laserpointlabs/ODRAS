#!/usr/bin/env python3
"""
Direct database injection of BSEO.A requirements for Conceptualizer testing
Bypasses the Individual Tables API which may not be fully implemented
"""

import json
import uuid
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone

# Configuration
PROJECT_ID = "1ec70631-7032-4959-ac23-3a206899177c"
ONTOLOGY_GRAPH = "https://xma-adt.usnc.mil/odras/core/1ec70631-7032-4959-ac23-3a206899177c/ontologies/bseo-a"

# Database connection
def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        user="postgres", 
        password="password",
        database="odras",
        port=5432
    )

# UAS Requirements
UAS_REQUIREMENTS = [
    {
        "name": "Autonomous Flight Capability",
        "text": "The UAS SHALL provide autonomous flight capability using Global Positioning System (GPS) waypoint navigation.",
        "id": "UAS-REQ-001"
    },
    {
        "name": "Manual Override Control", 
        "text": "The system MUST support manual override control via ground control station at all times during flight.",
        "id": "UAS-REQ-002"
    },
    {
        "name": "Return to Home",
        "text": "The UAS SHALL automatically return to home location when commanded or upon loss of communication signal.",
        "id": "UAS-REQ-003"
    },
    {
        "name": "Mission Definition",
        "text": "The system SHALL allow operators to define flight missions with waypoints, altitude, speed, and sensor activation points.",
        "id": "UAS-REQ-004"
    },
    {
        "name": "Stable Hover Capability",
        "text": "The UAS MUST be capable of maintaining stable hover at altitudes between 10 and 400 feet Above Ground Level (AGL).",
        "id": "UAS-REQ-005"
    }
]

def main():
    print("🚀 Injecting BSEO.A requirements directly into database")
    print("=" * 60)
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Step 0: Get a valid user ID
            print("Step 0: Getting valid user for database constraints...")
            cursor.execute("SELECT user_id FROM public.users WHERE username = 'das_service' LIMIT 1")
            user_result = cursor.fetchone()
            
            if not user_result:
                print("❌ No das_service user found - creating placeholder")
                user_id = str(uuid.uuid4())
                # This might fail, but we'll try anyway
            else:
                user_id = str(user_result["user_id"])
                print(f"✅ Using das_service user: {user_id}")
            
            # Step 1: Create or get Individual Tables config
            print("Step 1: Setting up Individual Tables configuration...")
            
            # Check if config exists
            cursor.execute("""
                SELECT table_id FROM individual_tables_config 
                WHERE project_id = %s AND graph_iri = %s
            """, (PROJECT_ID, ONTOLOGY_GRAPH))
            
            existing = cursor.fetchone()
            
            if existing:
                table_id = existing["table_id"]
                print(f"✅ Found existing Individual Tables config: {table_id}")
            else:
                # Create new config
                table_id = str(uuid.uuid4())
                
                ontology_structure = {
                    "name": "BSEO.A Ontology",
                    "classes": [
                        {
                            "name": "Requirement",
                            "comment": "Statement of need or obligation imposed on a system.",
                            "dataProperties": [
                                {"name": "Text", "range": "string", "comment": "Requirement text description"},
                                {"name": "ID", "range": "string", "comment": "Requirement identifier"}
                            ]
                        },
                        {"name": "Component", "comment": "Physical or logical part of the system"},
                        {"name": "Process", "comment": "Activity performed by Components"},
                        {"name": "Function", "comment": "Intended capability realized by Processes"},
                        {"name": "Constraint", "comment": "Limitation that restricts design or operation"},
                        {"name": "Interface", "comment": "Defined boundary where Components interact"}
                    ]
                }
                
                try:
                    cursor.execute("""
                        INSERT INTO individual_tables_config (
                            table_id, project_id, graph_iri, ontology_label, ontology_structure,
                            created_by, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        table_id, PROJECT_ID, ONTOLOGY_GRAPH, "BSEO.A",
                        json.dumps(ontology_structure),
                        user_id,
                        datetime.now(timezone.utc),
                        datetime.now(timezone.utc)
                    ))
                    
                    print(f"✅ Created Individual Tables config: {table_id}")
                except Exception as e:
                    print(f"❌ Failed to create config, trying without foreign key: {e}")
                    # Try without created_by foreign key
                    cursor.execute("""
                        INSERT INTO individual_tables_config (
                            table_id, project_id, graph_iri, ontology_label, ontology_structure,
                            created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        table_id, PROJECT_ID, ONTOLOGY_GRAPH, "BSEO.A",
                        json.dumps(ontology_structure),
                        datetime.now(timezone.utc),
                        datetime.now(timezone.utc)
                    ))
                    print(f"✅ Created Individual Tables config without user ref: {table_id}")
            
            # Step 2: Generate ODRAS-style individual IDs and inject requirements
            print(f"\nStep 2: Generating ODRAS individual IDs and injecting requirements...")
            
            # Get next available number for BSEO.A individuals
            cursor.execute("""
                SELECT instance_name FROM individual_instances 
                WHERE table_id = %s AND class_name = 'Requirement'
                AND instance_name ~ '^bseo\.a-[0-9]+$'
                ORDER BY instance_name DESC
                LIMIT 1
            """, (table_id,))
            
            last_instance = cursor.fetchone()
            if last_instance:
                # Extract number from last instance (e.g., "bseo.a-005" -> 5)
                last_num = int(last_instance["instance_name"].split('-')[-1])
                next_num = last_num + 1
            else:
                next_num = 1
            
            successful = 0
            for i, req in enumerate(UAS_REQUIREMENTS):
                try:
                    # Generate ODRAS-style individual ID
                    individual_id = f"bseo.a-{next_num + i:03d}"  # bseo.a-001, bseo.a-002, etc.
                    
                    instance_id = str(uuid.uuid4())
                    instance_uri = f"{ONTOLOGY_GRAPH}#{individual_id}"
                    
                    # Store ALL properties in the dynamic properties field
                    properties = {
                        "Text": req["text"],  # Local data property from BSEO.A
                        "ID": req["id"],      # Local data property from BSEO.A  
                        # Future: imported properties would also go here
                        "displayName": req["name"]  # Human-readable name stored as property
                    }
                    
                    cursor.execute("""
                        INSERT INTO individual_instances (
                            instance_id, table_id, class_name, instance_name,
                            instance_uri, properties, source_type,
                            created_by, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        instance_id, table_id, "Requirement", individual_id,  # instance_name = system ID
                        instance_uri, json.dumps(properties), "manual",
                        user_id, datetime.now(timezone.utc), datetime.now(timezone.utc)
                    ))
                    
                    print(f"✅ Injected: {individual_id} -> {req['name']} ({req['id']})")
                    successful += 1
                    
                except Exception as e:
                    print(f"❌ Failed to inject {req['name']}: {e}")
            
            # Commit all changes
            conn.commit()
            
            # Step 3: Verify results
            print(f"\nStep 3: Verifying injection results...")
            cursor.execute("""
                SELECT class_name, instance_name, properties
                FROM individual_instances 
                WHERE table_id = %s
                ORDER BY created_at
            """, (table_id,))
            
            instances = cursor.fetchall()
            
            print(f"✅ Verification: Found {len(instances)} requirement instances in database:")
            for instance in instances:
                props = instance["properties"] if isinstance(instance["properties"], dict) else json.loads(instance["properties"])
                print(f"   - {instance['instance_name']} ({props.get('ID', 'no-id')})")
            
            print("\n" + "=" * 60)
            print("🎯 DATABASE INJECTION COMPLETE!")
            print(f"✅ Individual Tables config: {table_id}")
            print(f"✅ Requirements injected: {successful}/{len(UAS_REQUIREMENTS)}")
            print(f"✅ Total instances in DB: {len(instances)}")
            print("\n🚀 Ready to test Conceptualizer Workbench!")
            print("   Next: Refresh browser and navigate to Conceptualizer → select BSEO.A")
            
            return successful > 0
            
    except Exception as e:
        print(f"❌ Database injection failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ SUCCESS: Requirements are ready for conceptualization!")
    else:
        print("\n❌ FAILURE: Could not set up requirements for testing")
