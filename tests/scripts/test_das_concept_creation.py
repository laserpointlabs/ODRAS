#!/usr/bin/env python3
"""
Debug script to test DAS concept creation directly in database
"""

import json
import uuid
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone

# Test configuration
PROJECT_ID = "1ec70631-7032-4959-ac23-3a206899177c"
ONTOLOGY_GRAPH = "https://xma-adt.usnc.mil/odras/core/1ec70631-7032-4959-ac23-3a206899177c/ontologies/bseo-a"
TEST_CONCEPTS = {
    "Component": [
        {"name": "Flight Control Computer", "confidence": 0.9, "rationale": "Primary flight control system"},
        {"name": "GPS Navigation Unit", "confidence": 0.85, "rationale": "Position and navigation hardware"}
    ],
    "Process": [
        {"name": "Flight Path Execution", "confidence": 0.8, "rationale": "Process to execute autonomous flight"}
    ]
}

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        user="postgres", 
        password="password",
        database="odras",
        port=5432
    )

def generate_concept_individual_id(cursor, table_id: str, class_name: str, ontology_name: str) -> str:
    """Test the concept ID generation logic"""
    try:
        print(f"🔍 Generating concept ID for {class_name} in {ontology_name}")
        
        # Get next available number for this class in this ontology
        pattern = f"^{ontology_name}-.*-[0-9]+$"
        print(f"   Pattern: {pattern}")
        
        cursor.execute("""
            SELECT instance_name FROM individual_instances 
            WHERE table_id = %s AND class_name = %s
            AND instance_name ~ %s
            ORDER BY instance_name DESC
            LIMIT 1
        """, (table_id, class_name, pattern))
        
        last_instance = cursor.fetchone()
        print(f"   Last instance: {last_instance}")
        
        if last_instance:
            # Extract number from last instance (e.g., "bseo.a-comp-005" -> 5)
            parts = last_instance["instance_name"].split('-')
            if len(parts) >= 3 and parts[-1].isdigit():
                last_num = int(parts[-1])
                next_num = last_num + 1
            else:
                next_num = 1
        else:
            next_num = 1
        
        # Format: bseo.a-comp-001, bseo.a-proc-001, etc.
        class_abbrev = class_name.lower()[:4]  # "component" -> "comp", "process" -> "proc"
        concept_id = f"{ontology_name}-{class_abbrev}-{next_num:03d}"
        
        print(f"   Generated ID: {concept_id}")
        return concept_id
        
    except Exception as e:
        print(f"❌ Error generating concept ID: {e}")
        return f"{ontology_name}-{class_name.lower()}-{uuid.uuid4().hex[:6]}"

def main():
    print("🚀 Testing DAS concept creation directly")
    print("=" * 50)
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Get the table_id for BSEO.A
            cursor.execute("""
                SELECT table_id FROM individual_tables_config 
                WHERE project_id = %s AND graph_iri = %s
            """, (PROJECT_ID, ONTOLOGY_GRAPH))
            
            table_record = cursor.fetchone()
            if not table_record:
                print("❌ No Individual Tables config found for BSEO.A")
                return
            
            table_id = table_record["table_id"]
            print(f"✅ Found table_id: {table_id}")
            
            # Test concept creation
            user_id = "d58b9fd9-cdae-42c6-bfaa-ef95fa2914a0"  # das_service user
            created_count = 0
            
            for class_name, concepts in TEST_CONCEPTS.items():
                print(f"\n🔍 Creating concepts for {class_name}:")
                
                for concept in concepts:
                    try:
                        # Generate concept ID
                        concept_id = generate_concept_individual_id(cursor, table_id, class_name, "bseo.a")
                        
                        # Create concept properties
                        concept_properties = {
                            "name": concept["name"],
                            "dasGenerated": True,
                            "sourceRequirement": "bseo.a-001",
                            "confidence": concept.get("confidence", 0.8),
                            "rationale": concept.get("rationale", f"DAS concept for {class_name}"),
                            "conceptType": "das_concept",
                            "generatedAt": datetime.now().isoformat()
                        }
                        
                        instance_id = str(uuid.uuid4())
                        instance_uri = f"{ONTOLOGY_GRAPH}#{concept_id}"
                        
                        print(f"   Creating: {concept_id} -> {concept['name']}")
                        
                        cursor.execute("""
                            INSERT INTO individual_instances (
                                instance_id, table_id, class_name, instance_name,
                                instance_uri, properties, source_type,
                                validation_status, created_by, created_at, updated_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            instance_id, table_id, class_name, concept_id,
                            instance_uri, json.dumps(concept_properties), "das_generated",
                            "valid", user_id, datetime.now(timezone.utc), datetime.now(timezone.utc)
                        ))
                        
                        created_count += 1
                        print(f"   ✅ Created: {concept_id}")
                        
                    except Exception as e:
                        print(f"   ❌ Failed to create {concept['name']}: {e}")
            
            # Commit changes
            conn.commit()
            
            # Verify results
            print(f"\n🎯 Created {created_count} concept individuals")
            
            # Check database
            cursor.execute("""
                SELECT class_name, instance_name, properties->>'name' as concept_name
                FROM individual_instances 
                WHERE table_id = %s AND source_type = 'das_generated'
                ORDER BY class_name, instance_name
            """, (table_id,))
            
            concepts = cursor.fetchall()
            print(f"✅ Verification: Found {len(concepts)} DAS concepts in database:")
            
            for concept in concepts:
                print(f"   - {concept['class_name']}: {concept['instance_name']} -> {concept['concept_name']}")
            
            return len(concepts) > 0
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ DAS concept creation working!")
    else:
        print("\n❌ DAS concept creation failed!")
