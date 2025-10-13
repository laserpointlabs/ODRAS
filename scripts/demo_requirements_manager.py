#!/usr/bin/env python3
"""
Demo Requirements Manager Script

This script manages individual requirements for clean ODRAS demonstrations.
It can clean out all individuals and inject fresh requirements for testing.

Usage:
    python demo_requirements_manager.py clean                    # Clean all individuals
    python demo_requirements_manager.py inject simple           # Inject simple_system_requirements.md to BSEO.A
    python demo_requirements_manager.py inject compact          # Inject req_example.md to BSEO.A
    python demo_requirements_manager.py inject compact --ontology base --class A  # Inject to different ontology/class
    python demo_requirements_manager.py reset simple            # Clean + inject simple requirements
    python demo_requirements_manager.py reset compact           # Clean + inject compact requirements  
    python demo_requirements_manager.py status                  # Show current individual counts
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
        
        # Total individuals
        cursor.execute("SELECT COUNT(*) as count FROM individual_instances")
        result = cursor.fetchone()
        total = result['count'] if result else 0
        print(f"Total Individuals: {total}")
        
        # By ontology 
        cursor.execute("""
            SELECT itc.graph_iri, COUNT(*) as count
            FROM individual_instances ii 
            JOIN individual_tables_config itc ON ii.table_id = itc.table_id 
            GROUP BY itc.graph_iri 
            ORDER BY count DESC
        """)
        ontology_counts = cursor.fetchall()
        
        print("\nBy Ontology:")
        for row in ontology_counts:
            ontology_name = row['graph_iri'].split('/')[-1] if '/' in row['graph_iri'] else row['graph_iri']
            print(f"  {ontology_name}: {row['count']}")
            
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
        
    def extract_requirements_from_markdown(self, file_path, req_type, prefix):
        """Extract requirements from markdown file"""
        print(f"\n📋 Extracting requirements from {file_path}...")
        
        if not os.path.exists(file_path):
            print(f"❌ Requirements file not found: {file_path}")
            return []
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        requirements = []
        
        if req_type == 'compact':
            # Extract compact format requirements (each line is a requirement) - LIMITED TO 5 FOR DEMO
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
                    
                    # DEMO LIMIT: Stop after 5 requirements for faster presentation
                    if req_num > 5:
                        break
                    
        elif req_type == 'simple':
            # Extract narrative format requirements (lines with SHALL/MUST) - LIMITED TO 5 FOR DEMO
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
                        
                        # DEMO LIMIT: Stop after 5 requirements for faster presentation
                        if req_num > 5:
                            break
                        
        print(f"✅ Extracted {len(requirements)} requirements")
        return requirements
        
    def inject_requirements(self, req_type, ontology_name='bseo.a', class_name=None):
        """Inject requirements as individuals"""
        if req_type not in REQUIREMENTS_DATA:
            print(f"❌ Unknown requirements type: {req_type}")
            print(f"Available types: {list(REQUIREMENTS_DATA.keys())}")
            return
            
        if ontology_name not in ONTOLOGY_MAP:
            print(f"❌ Unknown ontology: {ontology_name}")
            print(f"Available ontologies: {list(ONTOLOGY_MAP.keys())}")
            return
            
        req_config = REQUIREMENTS_DATA[req_type]
        onto_config = ONTOLOGY_MAP[ontology_name]
        
        # Use provided class name or ontology default
        target_class = class_name if class_name else onto_config['default_class']
        target_ontology = onto_config['iri']
        target_prefix = onto_config['prefix']
        
        print(f"\n🚀 Injecting {req_config['description']}...")
        print(f"📍 Target Ontology: {ontology_name} → {target_class} class")
        
        # Extract requirements
        requirements = self.extract_requirements_from_markdown(req_config['file'], req_type, target_prefix)
        
        if not requirements:
            print("❌ No requirements found to inject")
            return
            
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        
        # Get table configuration for the target ontology
        cursor.execute("""
            SELECT table_id, project_id, graph_iri 
            FROM individual_tables_config 
            WHERE graph_iri = %s
        """, (target_ontology,))
        table_config = cursor.fetchone()
        
        if not table_config:
            print(f"❌ No table configuration found for ontology: {target_ontology}")
            print("Available ontologies:")
            cursor.execute("SELECT graph_iri FROM individual_tables_config")
            for row in cursor.fetchall():
                ontology_name = row['graph_iri'].split('/')[-1]
                print(f"  - {ontology_name}: {row['graph_iri']}")
            cursor.close()
            return
            
        table_id = table_config['table_id']
        project_id = table_config['project_id']
        
        # Insert requirements as individuals
        inserted = 0
        for req in requirements:
            try:
                # Generate instance URI
                instance_uri = f"{target_ontology}#{req['id']}"
                
                cursor.execute("""
                    INSERT INTO individual_instances (
                        table_id, class_name, instance_name, instance_uri,
                        properties
                    ) VALUES (%s, %s, %s, %s, %s)
                """, (
                    table_id,
                    target_class, 
                    req['id'],
                    instance_uri,
                    json.dumps({
                        'Text': req['text'],           # Requirement text (matches table column)
                        'ID': req['id'],               # Requirement ID (matches table column)
                        'Title': req['name'],          # Requirement title (matches table column)
                        'Source': req['source'], 
                        'Created': datetime.now().isoformat(),
                        'Type': 'Root Requirement',
                        'DemoInjected': True,
                        'TargetOntology': ontology_name,
                        'TargetClass': target_class
                    })
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
  python demo_requirements_manager.py inject simple
  python demo_requirements_manager.py reset compact
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
                       default='bseo.a',
                       choices=list(ONTOLOGY_MAP.keys()),
                       help='Target ontology name (default: bseo.a)')
    parser.add_argument('--class', 
                       dest='class_name',
                       help='Target class name (default: use ontology default)')
    
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
            manager.inject_requirements(args.dataset, args.ontology, args.class_name)
            
        elif args.command == 'reset':
            manager.clean_all()
            manager.inject_requirements(args.dataset, args.ontology, args.class_name)
            
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
