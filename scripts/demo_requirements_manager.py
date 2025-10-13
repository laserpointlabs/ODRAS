#!/usr/bin/env python3
"""
Demo Requirements Manager Script

This script manages individual requirements for clean ODRAS demonstrations.
It can clean out all individuals and inject fresh requirements for testing.

Usage:
    python demo_requirements_manager.py clean                                    # Clean all individuals
    python demo_requirements_manager.py inject simple                           # Inject 5 requirements (default)
    python demo_requirements_manager.py inject simple --count 1                 # Inject just 1 requirement
    python demo_requirements_manager.py inject compact --ontology bseo-v1       # Inject to bseo-v1 ontology
    python demo_requirements_manager.py inject compact --ontology BSEO_V1 --class Requirement --count 1  # Inject 1 to custom ontology/class
    python demo_requirements_manager.py reset simple --ontology bseo-a          # Clean + inject 5 requirements
    python demo_requirements_manager.py status                                  # Show current individual counts
    
Note: --ontology matches the suffix of the graph IRI (e.g., 'bseo-v1d' for .../ontologies/bseo-v1d)
      --class defaults to 'Requirement' if not specified
      --count defaults to 5 (all requirements) but can be set to 1 for single requirement
"""

import argparse
import os
import sys
import re
import json
from datetime import datetime
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres', 
    'password': 'password',  # From docker-compose.yml
    'database': 'odras'
}

# Requirements data sets (defaults)
REQUIREMENTS_DATA = {
    'simple': {
        'file': 'data/simple_system_requirements.md',
        'description': 'Simple System Requirements (Narrative Format)'
    },
    'compact': {
        'file': 'data/req_example.md', 
        'description': 'Compact UAS Requirements (Structured Format)'
    }
}

# Available ontologies mapping  
ONTOLOGY_MAP = {
    'bseo.a': {
        'iri': 'https://xma-adt.usnc.mil/odras/core/1ec70631-7032-4959-ac23-3a206899177c/ontologies/bseo-a',
        'default_class': 'Requirement',
        'prefix': 'bseo.a'
    },
    'base': {
        'iri': 'https://xma-adt.usnc.mil/odras/core/1ec70631-7032-4959-ac23-3a206899177c/ontologies/base',
        'default_class': 'A', 
        'prefix': 'base'
    },
    'bseo.b': {
        'iri': 'https://xma-adt.usnc.mil/odras/core/1ec70631-7032-4959-ac23-3a206899177c/ontologies/bseo-b',
        'default_class': 'Requirement',
        'prefix': 'bseo.b'
    },
    'bseo.applied': {
        'iri': 'https://xma-adt.usnc.mil/odras/core/1ec70631-7032-4959-ac23-3a206899177c/ontologies/bseo-applied',
        'default_class': 'Requirement', 
        'prefix': 'bseo.applied'
    }
}

class DemoRequirementsManager:
    def __init__(self):
        self.connection = None
        
    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            self.connection = psycopg2.connect(**DB_CONFIG)
            print("✅ Connected to ODRAS database")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            sys.exit(1)
            
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            print("🔐 Database connection closed")
            
    def get_status(self):
        """Show current individual counts"""
        print("\n📊 Current Individual Counts:")
        print("=" * 50)
        
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        
        # Show available ontologies
        cursor.execute("""
            SELECT label, graph_iri 
            FROM ontologies_registry 
            ORDER BY label
        """)
        ontologies = cursor.fetchall()
        
        if ontologies:
            print("\n🗂️  Available Ontologies:")
            for ont in ontologies:
                ontology_suffix = ont['graph_iri'].split('/')[-1]
                print(f"  - {ont['label']}: {ontology_suffix}")
        
        # Total individuals
        cursor.execute("SELECT COUNT(*) as count FROM individual_instances")
        result = cursor.fetchone()
        total = result['count'] if result else 0
        print(f"\n📦 Total Individuals: {total}")
        
        # By ontology 
        cursor.execute("""
            SELECT itc.graph_iri, COUNT(*) as count
            FROM individual_instances ii 
            JOIN individual_tables_config itc ON ii.table_id = itc.table_id 
            GROUP BY itc.graph_iri 
            ORDER BY count DESC
        """)
        ontology_counts = cursor.fetchall()
        
        if ontology_counts:
            print("\nBy Ontology (with individuals):")
            for row in ontology_counts:
                # Try to get the label from ontologies_registry
                cursor.execute("""
                    SELECT label FROM ontologies_registry 
                    WHERE graph_iri = %s
                """, (row['graph_iri'],))
                label_result = cursor.fetchone()
                label = label_result['label'] if label_result else row['graph_iri'].split('/')[-1]
                ontology_suffix = row['graph_iri'].split('/')[-1]
                print(f"  {label} ({ontology_suffix}): {row['count']}")
            
        # By class
        cursor.execute("""
            SELECT class_name, COUNT(*) as count
            FROM individual_instances 
            GROUP BY class_name 
            ORDER BY count DESC
        """)
        class_counts = cursor.fetchall()
        
        print("\nBy Class:")
        for row in class_counts:
            print(f"  {row['class_name']}: {row['count']}")
            
        # DAS-generated individuals
        cursor.execute("""
            SELECT COUNT(*) as count FROM individual_instances 
            WHERE properties::jsonb ? 'dasGenerated'
        """)
        result = cursor.fetchone()
        das_count = result['count'] if result else 0
        print(f"\nDAS-Generated: {das_count}")
        
        # Configurations
        cursor.execute(
            "SELECT COUNT(*) as count FROM configurations WHERE das_metadata IS NOT NULL"
        )
        result = cursor.fetchone()
        config_count = result['count'] if result else 0
        print(f"DAS Configurations: {config_count}")
        
        cursor.close()
        
    def clean_all(self):
        """Clean out all individuals and configurations"""
        print("\n🧹 Cleaning all individuals and configurations...")
        
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        
        # Get counts before deletion
        cursor.execute("SELECT COUNT(*) as count FROM configurations WHERE das_metadata IS NOT NULL")
        result = cursor.fetchone()
        config_count = result['count'] if result else 0
        
        cursor.execute("SELECT COUNT(*) as count FROM individual_instances")
        result = cursor.fetchone()
        individual_count = result['count'] if result else 0
        
        # Clean DAS configurations first
        cursor.execute("DELETE FROM configurations WHERE das_metadata IS NOT NULL")
        
        # Clean all individuals
        cursor.execute("DELETE FROM individual_instances")
        
        # Commit changes
        self.connection.commit()
        cursor.close()
        
        print(f"✅ Deleted {individual_count} individuals")
        print(f"✅ Deleted {config_count} DAS configurations")
        print("🎯 Database cleaned for fresh demo")
        
    def extract_requirements_from_markdown(self, file_path, req_type, prefix, max_count=5):
        """Extract requirements from markdown file"""
        print(f"\n📋 Extracting requirements from {file_path} (limit: {max_count})...")
        
        if not os.path.exists(file_path):
            print(f"❌ Requirements file not found: {file_path}")
            return []
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        requirements = []
        
        if req_type == 'compact':
            # Extract compact format requirements (each line is a requirement)
            lines = content.strip().split('\n')
            req_num = 1
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and len(line) > 20:  # Skip headers and short lines
                    requirements.append({
                        'id': f"{prefix}-{req_num:03d}",
                        'name': f"Requirement {req_num:03d}",
                        'text': line,
                        'source': f'Compact Requirements Format ({prefix})'
                    })
                    req_num += 1
                    
                    # Stop after reaching max_count
                    if req_num > max_count:
                        break
                    
        elif req_type == 'simple':
            # Extract narrative format requirements (lines with SHALL/MUST)
            lines = content.split('\n')
            req_num = 1
            
            # Look for requirements keywords
            req_patterns = [
                r'.*SHALL\s+.*',
                r'.*MUST\s+.*', 
                r'.*REQUIRED.*'
            ]
            
            for line in lines:
                line = line.strip()
                if line and any(re.search(pattern, line, re.IGNORECASE) for pattern in req_patterns):
                    # Clean up the requirement text
                    clean_text = re.sub(r'^[#\-\*\s]*', '', line)  # Remove markdown formatting
                    if len(clean_text) > 20:  # Ensure substantial content
                        requirements.append({
                            'id': f"{prefix}-{req_num:03d}",
                            'name': f"System Requirement {req_num:03d}",
                            'text': clean_text,
                            'source': f'Simple System Requirements ({prefix})'
                        })
                        req_num += 1
                        
                        # Stop after reaching max_count
                        if req_num > max_count:
                            break
                        
        print(f"✅ Extracted {len(requirements)} requirements")
        return requirements
        
    def inject_requirements(self, req_type, ontology_name='bseo-a', class_name='Requirement', count=5):
        """Inject requirements as individuals"""
        if req_type not in REQUIREMENTS_DATA:
            print(f"❌ Unknown requirements type: {req_type}")
            print(f"Available types: {list(REQUIREMENTS_DATA.keys())}")
            return
            
        req_config = REQUIREMENTS_DATA[req_type]
        
        # Query database to find matching ontology
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        
        # Try to find ontology in ontologies_registry by label or graph_iri suffix
        cursor.execute("""
            SELECT id, project_id, graph_iri, label 
            FROM ontologies_registry 
            WHERE LOWER(label) = LOWER(%s) 
               OR graph_iri ILIKE %s 
               OR graph_iri ILIKE %s
            ORDER BY id DESC
            LIMIT 1
        """, (ontology_name, f'%/{ontology_name}', f'%/{ontology_name.lower()}'))
        
        ontology_record = cursor.fetchone()
        
        if not ontology_record:
            print(f"❌ No ontology found matching: {ontology_name}")
            print("\nAvailable ontologies:")
            cursor.execute("SELECT label, graph_iri FROM ontologies_registry ORDER BY label")
            for row in cursor.fetchall():
                ontology_suffix = row['graph_iri'].split('/')[-1]
                print(f"  - {row['label']}: {ontology_suffix} → {row['graph_iri']}")
            cursor.close()
            return
            
        target_ontology = ontology_record['graph_iri']
        project_id = ontology_record['project_id']
        target_class = class_name
        target_prefix = ontology_name.replace('_', '-').replace('.', '-').lower()
        
        # Check if individual_tables_config exists for this ontology, create if not
        cursor.execute("""
            SELECT table_id, project_id, graph_iri 
            FROM individual_tables_config 
            WHERE graph_iri = %s
        """, (target_ontology,))
        
        table_config = cursor.fetchone()
        
        if not table_config:
            # Create individual_tables_config entry for this ontology with proper structure
            print(f"📝 Creating individual table configuration for {ontology_name}...")
            
            # Define BSEO-style ontology structure with classes and object properties
            ontology_structure = {
                "name": f"{ontology_record['label']} Ontology",
                "classes": [
                    {
                        "name": "Requirement",
                        "comment": "Statement of need or obligation imposed on a system.",
                        "dataProperties": [
                            {"name": "Text", "range": "string", "comment": "Requirement text description"},
                            {"name": "ID", "range": "string", "comment": "Requirement identifier"}
                        ],
                        "objectProperties": [
                            {"name": "has_constraint", "range": "Constraint", "minCount": 0, "maxCount": None, "comment": "Links a requirement to its constraints"},
                            {"name": "specifies", "range": "Component", "minCount": 1, "maxCount": None, "comment": "Indicates components required to fulfill the requirement"}
                        ]
                    },
                    {
                        "name": "Component",
                        "comment": "Physical or logical part of the system",
                        "objectProperties": [
                            {"name": "has_interface", "range": "Interface", "minCount": 1, "maxCount": None, "comment": "Declares an exposed or required interface"},
                            {"name": "performs", "range": "Process", "minCount": 1, "maxCount": None, "comment": "States an activity a Component executes"}
                        ]
                    },
                    {
                        "name": "Process",
                        "comment": "Activity performed by Components",
                        "objectProperties": [
                            {"name": "realizes", "range": "Function", "minCount": 1, "maxCount": None, "comment": "Binds an activity to the capability it delivers"},
                            {"name": "requires", "range": "Component", "minCount": 1, "maxCount": None, "comment": "Indicates component needed for the process"},
                            {"name": "enabled_by", "range": "Component", "minCount": 0, "maxCount": None, "comment": "Component that enables this process"}
                        ]
                    },
                    {
                        "name": "Function",
                        "comment": "Intended capability realized by Processes",
                        "objectProperties": [
                            {"name": "specifically_depends_upon", "range": "Component", "minCount": 1, "maxCount": None, "comment": "Concrete components required for the function"}
                        ]
                    },
                    {"name": "Constraint", "comment": "Limitation that restricts design or operation"},
                    {"name": "Interface", "comment": "Defined boundary where Components interact"}
                ]
            }
            
            cursor.execute("""
                INSERT INTO individual_tables_config (
                    project_id, 
                    graph_iri, 
                    ontology_label, 
                    ontology_structure
                )
                VALUES (%s, %s, %s, %s)
                RETURNING table_id
            """, (project_id, target_ontology, ontology_record['label'], json.dumps(ontology_structure)))
            result = cursor.fetchone()
            table_id = result['table_id']
            self.connection.commit()
            print(f"✅ Created table configuration with BSEO structure (table_id: {table_id})")
        else:
            table_id = table_config['table_id']
        
        print(f"\n🚀 Injecting {req_config['description']}...")
        print(f"📍 Target Ontology: {ontology_record['label']} ({ontology_name})")
        print(f"📍 Target Class: {target_class}")
        print(f"📍 Full IRI: {target_ontology}")
        
        cursor.close()
        
        # Extract requirements
        requirements = self.extract_requirements_from_markdown(req_config['file'], req_type, target_prefix, count)
        
        if not requirements:
            print("❌ No requirements found to inject")
            return
            
        # Create new cursor for insertions
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        
        # Insert requirements as individuals
        inserted = 0
        for req in requirements:
            try:
                # Generate instance URI
                instance_uri = f"{target_ontology}#{req['id']}"
                
                cursor.execute("""
                    INSERT INTO individual_instances (
                        table_id, class_name, instance_name, instance_uri,
                        properties, source_type
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    table_id,
                    target_class, 
                    req['id'],
                    instance_uri,
                    json.dumps({
                        'Text': req['text'],           # Requirement text (BSEO data property)
                        'ID': req['id'],               # Requirement ID (BSEO data property)
                        'displayName': req['name']     # Human-readable name (used by conceptualizer)
                    }),
                    'manual'
                ))
                inserted += 1
                print(f"  ✅ {req['id']}: {req['name'][:50]}...")
                
            except Exception as e:
                print(f"  ❌ Failed to insert {req['id']}: {e}")
                
        # Commit changes
        self.connection.commit()
        cursor.close()
        
        print(f"\n🎯 Successfully injected {inserted} requirements")
        print(f"📍 Ontology: {ontology_name} ({target_ontology.split('/')[-1]})")
        print(f"📍 Class: {target_class}")
        print("🎪 Ready for DAS conceptualization!")

def main():
    parser = argparse.ArgumentParser(
        description="Demo Requirements Manager for ODRAS Testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python demo_requirements_manager.py status
  python demo_requirements_manager.py clean  
  python demo_requirements_manager.py inject simple                                   # Inject 5 requirements
  python demo_requirements_manager.py inject simple --count 1                         # Inject 1 requirement
  python demo_requirements_manager.py inject compact --ontology bseo-v1d --count 1
  python demo_requirements_manager.py inject simple --ontology BSEO_V1 --class Requirement --count 5
  python demo_requirements_manager.py reset compact --ontology bseo-applied
        """
    )
    
    parser.add_argument('command', 
                       choices=['clean', 'inject', 'reset', 'status'],
                       help='Command to execute')
    parser.add_argument('dataset', 
                       nargs='?',
                       choices=['simple', 'compact'],
                       help='Requirements dataset (required for inject/reset)')
    parser.add_argument('--ontology', 
                       default='bseo-a',
                       help='Target ontology name - matches the ontology suffix in graph IRI (e.g., bseo-a, bseo-v1, BSEO_V1)')
    parser.add_argument('--class', 
                       dest='class_name',
                       default='Requirement',
                       help='Target class name (default: Requirement)')
    parser.add_argument('--count',
                       type=int,
                       default=5,
                       choices=[1, 5],
                       help='Number of requirements to inject: 1 for single requirement, 5 for all (default: 5)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.command in ['inject', 'reset'] and not args.dataset:
        print("❌ Dataset required for inject/reset commands")
        parser.print_help()
        sys.exit(1)
        
    # Initialize manager
    manager = DemoRequirementsManager()
    manager.connect()
    
    try:
        if args.command == 'status':
            manager.get_status()
            
        elif args.command == 'clean':
            manager.clean_all()
            
        elif args.command == 'inject':
            manager.inject_requirements(args.dataset, args.ontology, args.class_name, args.count)
            
        elif args.command == 'reset':
            manager.clean_all()
            manager.inject_requirements(args.dataset, args.ontology, args.class_name, args.count)
            
    except Exception as e:
        print(f"❌ Operation failed: {e}")
        sys.exit(1)
        
    finally:
        manager.disconnect()
        
    print("\n🏆 Demo requirements management complete!")

if __name__ == "__main__":
    # Change to ODRAS directory
    script_dir = Path(__file__).parent
    odras_dir = script_dir.parent
    os.chdir(odras_dir)
    
    main()
