#!/usr/bin/env python3
"""
CQ/MT Workbench Demo Data Seeder

Creates a demo project with microtheories, sample triples, and competency questions
to demonstrate the test-driven ontology development workflow.

Usage:
    python scripts/seed_cqmt_demo.py
    
Requirements:
    - ODRAS services must be running (PostgreSQL, Fuseki, ODRAS API)
    - das_service user must exist in the database
"""

import asyncio
import json
import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.db import DatabaseService
from backend.services.config import Settings
from backend.services.cqmt_service import CQMTService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CQMTDemoSeeder:
    """Seeds demo data for CQ/MT Workbench testing and demonstration."""
    
    def __init__(self):
        self.settings = Settings()
        self.db_service = DatabaseService(self.settings)
        self.cqmt_service = CQMTService(self.db_service, self.settings.fuseki_url)
        self.demo_project_id = None
        self.demo_user_id = None
        self.baseline_mt_iri = None
        self.empty_mt_iri = None
    
    async def seed_all(self):
        """Run the complete demo seeding process."""
        try:
            logger.info("🌱 Starting CQ/MT Workbench demo data seeding...")
            
            # Step 1: Find or create demo user (das_service)
            await self.ensure_demo_user()
            
            # Step 2: Create demo project
            await self.create_demo_project()
            
            # Step 3: Create microtheories with sample data
            await self.create_demo_microtheories()
            
            # Step 4: Populate baseline MT with sample triples
            await self.populate_sample_triples()
            
            # Step 5: Create demo competency questions
            await self.create_demo_cqs()
            
            # Step 6: Run CQs to demonstrate pass/fail
            await self.run_demo_cqs()
            
            logger.info("✅ Demo data seeding completed successfully!")
            await self.print_summary()
            
        except Exception as e:
            logger.error(f"❌ Demo seeding failed: {e}")
            raise
    
    async def ensure_demo_user(self):
        """Ensure das_service user exists for testing."""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                # Check if das_service user exists
                cur.execute(
                    "SELECT user_id FROM users WHERE username = %s",
                    ("das_service",)
                )
                user = cur.fetchone()
                
                if user:
                    self.demo_user_id = str(user[0])
                    logger.info(f"✓ Using existing das_service user: {self.demo_user_id}")
                else:
                    # Create das_service user
                    import uuid
                    demo_user_uuid = uuid.uuid4()
                    self.demo_user_id = str(demo_user_uuid)
                    cur.execute("""
                        INSERT INTO users (user_id, username, display_name, is_active, is_admin)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        str(demo_user_uuid), "das_service", "DAS Service Account", True, False
                    ))
                    conn.commit()
                    logger.info(f"✓ Created das_service user: {self.demo_user_id}")
        finally:
            self.db_service._return(conn)
    
    async def create_demo_project(self):
        """Create a demo project for CQ/MT testing."""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                # Check if demo project already exists
                cur.execute(
                    "SELECT project_id FROM projects WHERE name = %s",
                    ("CQ/MT Demo",)
                )
                existing = cur.fetchone()
                
                if existing:
                    self.demo_project_id = str(existing[0])
                    logger.info(f"✓ Using existing demo project: {self.demo_project_id}")
                else:
                    # Create demo project
                    import uuid
                    demo_project_uuid = uuid.uuid4()
                    self.demo_project_id = str(demo_project_uuid)
                    cur.execute("""
                        INSERT INTO projects (project_id, name, description, status, created_by)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        str(demo_project_uuid),
                        "CQ/MT Demo",
                        "Demonstration project for test-driven ontology development using Competency Questions and Microtheories",
                        "active",
                        self.demo_user_id
                    ))
                    
                    # Add user as project member
                    cur.execute("""
                        INSERT INTO project_members (user_id, project_id, role)
                        VALUES (%s, %s, %s)
                    """, (self.demo_user_id, self.demo_project_id, "admin"))
                
                # Ensure das_service is a member of existing project
                if existing:
                    # Check if user is already a member
                    cur.execute("""
                        SELECT 1 FROM project_members 
                        WHERE user_id = %s AND project_id = %s
                    """, (self.demo_user_id, self.demo_project_id))
                    
                    if not cur.fetchone():
                        # Add as member if not already
                        cur.execute("""
                            INSERT INTO project_members (user_id, project_id, role)
                            VALUES (%s, %s, %s)
                        """, (self.demo_user_id, self.demo_project_id, "admin"))
                        logger.info(f"✓ Added das_service as member of existing project")
                        conn.commit()
                    
                    conn.commit()
                    logger.info(f"✓ Created demo project: {self.demo_project_id}")
        finally:
            self.db_service._return(conn)
    
    async def create_demo_microtheories(self):
        """Create demo microtheories for testing."""
        logger.info("📊 Creating demo microtheories...")
        
        # Check if microtheories already exist for this project
        existing_mts = self.cqmt_service.list_microtheories(self.demo_project_id)
        if existing_mts["success"] and len(existing_mts["data"]) > 0:
            logger.info("✓ Found existing microtheories, using them:")
            for mt in existing_mts["data"]:
                logger.info(f"  • {mt['label']}: {mt['iri']} ({mt['triple_count']} triples)")
                if mt["label"] == "Baseline":
                    self.baseline_mt_iri = mt["iri"]
                elif mt["label"] == "Empty Test":
                    self.empty_mt_iri = mt["iri"]
            
            # Create missing MTs if needed
            if not self.baseline_mt_iri:
                baseline_result = self.cqmt_service.create_microtheory(
                    project_id=self.demo_project_id,
                    label="Baseline",
                    iri=None,  # Auto-generate
                    clone_from=None,
                    set_default=True,
                    created_by=self.demo_user_id
                )
                if not baseline_result["success"]:
                    raise Exception(f"Failed to create baseline MT: {baseline_result['error']}")
                self.baseline_mt_iri = baseline_result["data"]["iri"]
            
            if not self.empty_mt_iri:
                empty_result = self.cqmt_service.create_microtheory(
                    project_id=self.demo_project_id,
                    label="Empty Test",
                    iri=None,  # Auto-generate
                    clone_from=None,
                    set_default=False,
                    created_by=self.demo_user_id
                )
                if not empty_result["success"]:
                    raise Exception(f"Failed to create empty MT: {empty_result['error']}")
                self.empty_mt_iri = empty_result["data"]["iri"]
            
            return
        
        # 1. Create baseline microtheory with data
        baseline_result = self.cqmt_service.create_microtheory(
            project_id=self.demo_project_id,
            label="Baseline",
            iri=None,  # Auto-generate
            clone_from=None,
            set_default=True,
            created_by=self.demo_user_id
        )
        
        if not baseline_result["success"]:
            raise Exception(f"Failed to create baseline MT: {baseline_result['error']}")
        
        self.baseline_mt_iri = baseline_result["data"]["iri"]
        logger.info(f"✓ Created baseline microtheory: {self.baseline_mt_iri}")
        
        # 2. Create empty microtheory for testing failure cases
        empty_result = self.cqmt_service.create_microtheory(
            project_id=self.demo_project_id,
            label="Empty Test",
            iri=None,  # Auto-generate
            clone_from=None,
            set_default=False,
            created_by=self.demo_user_id
        )
        
        if not empty_result["success"]:
            raise Exception(f"Failed to create empty MT: {empty_result['error']}")
        
        self.empty_mt_iri = empty_result["data"]["iri"]
        logger.info(f"✓ Created empty microtheory: {self.empty_mt_iri}")
    
    async def populate_sample_triples(self):
        """Add sample triples to the baseline microtheory."""
        logger.info("📝 Populating baseline microtheory with sample triples...")
        
        # Sample aviation domain triples
        sample_triples = [
            # Aircraft types
            ("http://example.org/aircraft/f16", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://example.org/ontology/Aircraft"),
            ("http://example.org/aircraft/f16", "http://www.w3.org/2000/01/rdf-schema#label", "F-16 Fighting Falcon"),
            ("http://example.org/aircraft/f16", "http://example.org/ontology/hasRole", "http://example.org/ontology/Fighter"),
            
            ("http://example.org/aircraft/c130", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://example.org/ontology/Aircraft"),
            ("http://example.org/aircraft/c130", "http://www.w3.org/2000/01/rdf-schema#label", "C-130 Hercules"),
            ("http://example.org/aircraft/c130", "http://example.org/ontology/hasRole", "http://example.org/ontology/Transport"),
            
            ("http://example.org/aircraft/a10", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://example.org/ontology/Aircraft"),
            ("http://example.org/aircraft/a10", "http://www.w3.org/2000/01/rdf-schema#label", "A-10 Thunderbolt II"),
            ("http://example.org/aircraft/a10", "http://example.org/ontology/hasRole", "http://example.org/ontology/AttackAircraft"),
            
            # Aircraft roles/categories
            ("http://example.org/ontology/Fighter", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://example.org/ontology/AircraftRole"),
            ("http://example.org/ontology/Fighter", "http://www.w3.org/2000/01/rdf-schema#label", "Fighter Aircraft"),
            
            ("http://example.org/ontology/Transport", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://example.org/ontology/AircraftRole"),
            ("http://example.org/ontology/Transport", "http://www.w3.org/2000/01/rdf-schema#label", "Transport Aircraft"),
            
            ("http://example.org/ontology/AttackAircraft", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://example.org/ontology/AircraftRole"),
            ("http://example.org/ontology/AttackAircraft", "http://www.w3.org/2000/01/rdf-schema#label", "Attack Aircraft"),
            
            # Ontology classes
            ("http://example.org/ontology/Aircraft", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://www.w3.org/2002/07/owl#Class"),
            ("http://example.org/ontology/Aircraft", "http://www.w3.org/2000/01/rdf-schema#label", "Aircraft"),
            
            ("http://example.org/ontology/AircraftRole", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://www.w3.org/2002/07/owl#Class"),
            ("http://example.org/ontology/AircraftRole", "http://www.w3.org/2000/01/rdf-schema#label", "Aircraft Role"),
            
            # Properties
            ("http://example.org/ontology/hasRole", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://www.w3.org/2002/07/owl#ObjectProperty"),
            ("http://example.org/ontology/hasRole", "http://www.w3.org/2000/01/rdf-schema#label", "has role"),
            ("http://example.org/ontology/hasRole", "http://www.w3.org/2000/01/rdf-schema#domain", "http://example.org/ontology/Aircraft"),
            ("http://example.org/ontology/hasRole", "http://www.w3.org/2000/01/rdf-schema#range", "http://example.org/ontology/AircraftRole"),
        ]
        
        # Insert triples using SPARQL runner
        result = self.cqmt_service.runner.insert_sample_triples(self.baseline_mt_iri, sample_triples)
        
        if not result["success"]:
            raise Exception(f"Failed to insert sample triples: {result['error']}")
        
        # Verify triple count
        count_result = self.cqmt_service.runner.count_triples_in_graph(self.baseline_mt_iri)
        if count_result["success"]:
            logger.info(f"✓ Inserted {count_result['count']} triples into baseline microtheory")
        else:
            logger.warning("Could not verify triple count")
    
    async def create_demo_cqs(self):
        """Create demo competency questions."""
        logger.info("❓ Creating demo competency questions...")
        
        # Check if CQs already exist for this project
        existing_cqs = self.cqmt_service.get_cqs(self.demo_project_id)
        if existing_cqs["success"] and len(existing_cqs["data"]) > 0:
            logger.info("✓ Found existing competency questions, skipping creation:")
            for cq in existing_cqs["data"]:
                logger.info(f"  • {cq['cq_name']}: {cq['status']}")
            return
        
        demo_cqs = [
            {
                "cq_name": "List All Aircraft",
                "problem_text": "What aircraft are defined in the system? This should return all aircraft instances with their labels.",
                "sparql_text": """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ex: <http://example.org/ontology/>

SELECT ?aircraft ?label WHERE {
    ?aircraft rdf:type ex:Aircraft .
    ?aircraft rdfs:label ?label .
}
ORDER BY ?label""",
                "contract_json": {
                    "require_columns": ["aircraft", "label"],
                    "min_rows": 1
                },
                "status": "active"
            },
            
            {
                "cq_name": "Fighter Aircraft Only",
                "problem_text": "Which aircraft are specifically fighter aircraft? This should return only aircraft with the Fighter role.",
                "sparql_text": """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ex: <http://example.org/ontology/>

SELECT ?aircraft ?label WHERE {
    ?aircraft rdf:type ex:Aircraft .
    ?aircraft rdfs:label ?label .
    ?aircraft ex:hasRole ex:Fighter .
}
ORDER BY ?label""",
                "contract_json": {
                    "require_columns": ["aircraft", "label"],
                    "min_rows": 1,
                    "max_latency_ms": 1000
                },
                "status": "active"
            },
            
            {
                "cq_name": "Aircraft Roles Summary",
                "problem_text": "What are the different aircraft roles defined in the system? This should list all aircraft role types.",
                "sparql_text": """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ex: <http://example.org/ontology/>

SELECT ?role ?label WHERE {
    ?role rdf:type ex:AircraftRole .
    ?role rdfs:label ?label .
}
ORDER BY ?label""",
                "contract_json": {
                    "require_columns": ["role", "label"],
                    "min_rows": 1
                },
                "status": "active"
            },
            
            {
                "cq_name": "Missing Aircraft Properties",
                "problem_text": "Do we have any aircraft without assigned roles? This CQ should fail initially to demonstrate gap analysis.",
                "sparql_text": """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ex: <http://example.org/ontology/>

SELECT ?aircraft ?label WHERE {
    ?aircraft rdf:type ex:Aircraft .
    ?aircraft rdfs:label ?label .
    FILTER NOT EXISTS { ?aircraft ex:hasRole ?role }
}""",
                "contract_json": {
                    "require_columns": ["aircraft", "label"],
                    "min_rows": 0
                },
                "status": "active"
            },
            
            {
                "cq_name": "Helicopter Aircraft",
                "problem_text": "Which aircraft are helicopters? This CQ will initially fail because we don't have helicopter data, demonstrating the test-driven approach.",
                "sparql_text": """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ex: <http://example.org/ontology/>

SELECT ?helicopter ?label WHERE {
    ?helicopter rdf:type ex:Aircraft .
    ?helicopter rdfs:label ?label .
    ?helicopter ex:hasRole ex:Helicopter .
}""",
                "contract_json": {
                    "require_columns": ["helicopter", "label"],
                    "min_rows": 1
                },
                "status": "draft"
            }
        ]
        
        for cq_data in demo_cqs:
            result = self.cqmt_service.create_or_update_cq(
                project_id=self.demo_project_id,
                cq_data=cq_data,
                created_by=self.demo_user_id
            )
            
            if result["success"]:
                logger.info(f"✓ Created CQ: {cq_data['cq_name']}")
            else:
                logger.error(f"❌ Failed to create CQ '{cq_data['cq_name']}': {result['error']}")
    
    async def run_demo_cqs(self):
        """Run all demo CQs to create initial run history."""
        logger.info("🚀 Running demo CQs to create initial results...")
        
        # Get all CQs for the project
        cqs_result = self.cqmt_service.get_cqs(self.demo_project_id)
        if not cqs_result["success"]:
            logger.error(f"Failed to get CQs: {cqs_result['error']}")
            return
        
        cqs = cqs_result["data"]
        
        for cq in cqs:
            cq_id = cq["id"]
            cq_name = cq["cq_name"]
            
            # Run in baseline MT (should mostly pass)
            logger.info(f"  Running '{cq_name}' in baseline MT...")
            baseline_result = self.cqmt_service.run_cq(
                cq_id=cq_id,
                mt_iri=self.baseline_mt_iri,
                params={},
                executed_by=self.demo_user_id
            )
            
            if baseline_result["success"]:
                status = "✓ PASS" if baseline_result["pass"] else "✗ FAIL"
                reason = f" ({baseline_result['reason']})" if not baseline_result["pass"] else ""
                logger.info(f"    Baseline: {status}{reason}")
            else:
                logger.error(f"    Baseline: ERROR - {baseline_result['error']}")
            
            # Run in empty MT (should mostly fail)
            logger.info(f"  Running '{cq_name}' in empty MT...")
            empty_result = self.cqmt_service.run_cq(
                cq_id=cq_id,
                mt_iri=self.empty_mt_iri,
                params={},
                executed_by=self.demo_user_id
            )
            
            if empty_result["success"]:
                status = "✓ PASS" if empty_result["pass"] else "✗ FAIL"
                reason = f" ({empty_result['reason']})" if not empty_result["pass"] else ""
                logger.info(f"    Empty: {status}{reason}")
            else:
                logger.error(f"    Empty: ERROR - {empty_result['error']}")
    
    async def print_summary(self):
        """Print a summary of what was created."""
        logger.info("\n" + "="*60)
        logger.info("🎯 CQ/MT Demo Data Summary")
        logger.info("="*60)
        
        logger.info(f"Project: CQ/MT Demo ({self.demo_project_id})")
        logger.info(f"User: das_service ({self.demo_user_id})")
        
        # Count microtheories
        mt_result = self.cqmt_service.list_microtheories(self.demo_project_id)
        if mt_result["success"]:
            logger.info(f"Microtheories: {len(mt_result['data'])}")
            for mt in mt_result["data"]:
                default_marker = " (DEFAULT)" if mt["is_default"] else ""
                logger.info(f"  • {mt['label']}: {mt['triple_count']} triples{default_marker}")
        
        # Count CQs
        cq_result = self.cqmt_service.get_cqs(self.demo_project_id)
        if cq_result["success"]:
            total_cqs = len(cq_result["data"])
            active_cqs = len([cq for cq in cq_result["data"] if cq["status"] == "active"])
            passing_cqs = len([cq for cq in cq_result["data"] if cq["last_run_status"] is True])
            failing_cqs = len([cq for cq in cq_result["data"] if cq["last_run_status"] is False])
            
            logger.info(f"Competency Questions: {total_cqs} total, {active_cqs} active")
            logger.info(f"Recent Results: {passing_cqs} passing, {failing_cqs} failing")
            
            for cq in cq_result["data"]:
                if cq["last_run_status"] is not None:
                    status = "✓ PASS" if cq["last_run_status"] else "✗ FAIL"
                    logger.info(f"  • {cq['cq_name']}: {status}")
        
        logger.info("\n🌐 Access the CQ/MT Workbench:")
        logger.info("URL: http://localhost:8000/cqmt-workbench.html")
        logger.info("Login: das_service / das_service_2024!")
        logger.info("Project: CQ/MT Demo")
        
        logger.info("\n📚 Next Steps:")
        logger.info("1. Open the CQ/MT Workbench in your browser")
        logger.info("2. Select the 'CQ/MT Demo' project")
        logger.info("3. Explore the CQs tab to see competency questions")
        logger.info("4. Run CQs against different microtheories")
        logger.info("5. Try the Ontology Workbench to add missing terms")
        logger.info("6. Return to re-run CQs and see improvements")


async def main():
    """Main entry point for the seeder."""
    print("🌱 CQ/MT Workbench Demo Data Seeder")
    print("This will create demo data for testing the CQ/MT Workbench")
    print("")
    
    # Check if services are running
    print("Checking ODRAS services...")
    
    try:
        seeder = CQMTDemoSeeder()
        await seeder.seed_all()
        
        print("\n✅ Demo data seeding completed successfully!")
        print("You can now test the CQ/MT Workbench with realistic data.")
        
    except Exception as e:
        print(f"\n❌ Demo seeding failed: {e}")
        print("Please ensure ODRAS services are running:")
        print("  docker-compose up -d")
        print("  ./odras.sh start")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
