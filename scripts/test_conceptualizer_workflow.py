#!/usr/bin/env python3
"""
Test script for Conceptualizer Workbench workflow
- Sets up Individual Tables for BSEO.A
- Injects UAS requirements 
- Tests conceptualization API
"""

import json
import uuid
import asyncio
import httpx
from datetime import datetime, timezone

# Test configuration
BASE_URL = "http://localhost:8000"
PROJECT_ID = "1ec70631-7032-4959-ac23-3a206899177c"
ONTOLOGY_GRAPH = "https://xma-adt.usnc.mil/odras/core/1ec70631-7032-4959-ac23-3a206899177c/ontologies/bseo-a"
USERNAME = "das_service"
PASSWORD = "das_service_2024!"

# UAS Requirements from simple_system_requirements.md
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
    },
    {
        "name": "Real-time Telemetry",
        "text": "The system SHALL provide real-time telemetry data including position, altitude, heading, battery status, and airspeed.",
        "id": "UAS-REQ-006"
    },
    {
        "name": "Flight Endurance",
        "text": "The UAS SHALL achieve a minimum flight endurance of 25 minutes with standard payload.",
        "id": "UAS-REQ-007"
    },
    {
        "name": "Position Hold Accuracy",
        "text": "The system MUST maintain position hold accuracy within 2 meters horizontal under wind conditions up to 15 knots.",
        "id": "UAS-REQ-008"
    }
]

async def authenticate() -> str:
    """Authenticate and get JWT token"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": USERNAME, "password": PASSWORD}
        )
        response.raise_for_status()
        return response.json()["token"]

async def setup_individual_tables(token: str) -> str:
    """Set up Individual Tables for BSEO.A"""
    print("🔍 Setting up Individual Tables for BSEO.A...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # First check if tables already exist
        try:
            response = await client.get(
                f"{BASE_URL}/api/individuals/{PROJECT_ID}/tables",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                tables = response.json().get("tables", [])
                
                # Check if BSEO.A table exists
                for table in tables:
                    if table.get("graph_iri") == ONTOLOGY_GRAPH:
                        print(f"✅ Individual Tables already exist for BSEO.A (table_id: {table['table_id']})")
                        return table["table_id"]
        except:
            pass
        
        # Create Individual Tables configuration
        ontology_structure = {
            "name": "BSEO.A Ontology",
            "classes": [
                {
                    "name": "Requirement",
                    "comment": "Statement of need or obligation imposed on a system.",
                    "dataProperties": [
                        {"name": "Text", "range": "string", "comment": "Requirement text description"},
                        {"name": "ID", "range": "string", "comment": "Unique requirement identifier"}
                    ]
                },
                {
                    "name": "Component",
                    "comment": "Physical or logical part of the system with defined interfaces.",
                    "dataProperties": [
                        {"name": "CAD Model", "range": "string", "comment": "CAD model reference"}
                    ]
                },
                {
                    "name": "Process",
                    "comment": "Activity performed by Components to produce effects."
                },
                {
                    "name": "Function",
                    "comment": "Intended capability realized by Processes."
                },
                {
                    "name": "Constraint",
                    "comment": "Limitation that restricts design or operation."
                },
                {
                    "name": "Interface",
                    "comment": "Defined boundary where Components interact."
                }
            ]
        }
        
        response = await client.post(
            f"{BASE_URL}/api/individuals/{PROJECT_ID}/individuals/create-tables",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "graph_iri": ONTOLOGY_GRAPH,
                "ontology_label": "BSEO.A",
                "ontology_structure": ontology_structure
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            table_id = result.get("table_id")
            print(f"✅ Individual Tables created for BSEO.A (table_id: {table_id})")
            return table_id
        else:
            error = response.json()
            print(f"❌ Failed to create Individual Tables: {error}")
            raise Exception(f"Failed to create Individual Tables: {error}")

async def inject_requirements(token: str, table_id: str) -> int:
    """Inject UAS requirements into BSEO.A Individual Tables"""
    print(f"🔍 Injecting {len(UAS_REQUIREMENTS)} UAS requirements...")
    
    successful = 0
    async with httpx.AsyncClient(timeout=30.0) as client:
        for req in UAS_REQUIREMENTS:
            try:
                response = await client.post(
                    f"{BASE_URL}/api/individuals/{PROJECT_ID}/individuals/Requirement",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "name": req["name"],
                        "properties": {
                            "Text": req["text"],
                            "ID": req["id"]
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Created: {req['name']} (URI: {result.get('individual_uri', 'unknown')})")
                    successful += 1
                else:
                    error = response.json()
                    print(f"❌ Failed: {req['name']} - {error.get('detail', 'Unknown error')}")
                    
            except Exception as e:
                print(f"❌ Exception for {req['name']}: {e}")
    
    print(f"🎯 Requirements injection: {successful}/{len(UAS_REQUIREMENTS)} successful")
    return successful

async def test_conceptualizer_api(token: str) -> bool:
    """Test the Conceptualizer API to load root individuals"""
    print("🔍 Testing Conceptualizer API...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Test root individuals endpoint
            response = await client.get(
                f"{BASE_URL}/api/configurations/{PROJECT_ID}/ontologies/bseo-a/root-individuals",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                configurations = data.get("configurations", [])
                root_classes = data.get("root_classes", [])
                
                print(f"✅ Conceptualizer API working:")
                print(f"   - Root classes: {root_classes}")
                print(f"   - Root individuals: {len(configurations)}")
                
                for config in configurations:
                    print(f"   - {config['class_name']}: {config['name']} (ID: {config['config_id']})")
                
                return len(configurations) > 0
            else:
                error = response.json()
                print(f"❌ Conceptualizer API failed: {error}")
                return False
                
        except Exception as e:
            print(f"❌ Conceptualizer API exception: {e}")
            return False

async def main():
    """Main test workflow"""
    print("🚀 Starting Conceptualizer Workbench Test")
    print("=" * 50)
    
    try:
        # Step 1: Authenticate
        print("Step 1: Authenticating...")
        token = await authenticate()
        print(f"✅ Authenticated as {USERNAME}")
        
        # Step 2: Setup Individual Tables
        print("\nStep 2: Setting up Individual Tables...")
        table_id = await setup_individual_tables(token)
        
        # Step 3: Inject Requirements
        print("\nStep 3: Injecting UAS requirements...")
        successful_reqs = await inject_requirements(token, table_id)
        
        if successful_reqs == 0:
            print("❌ No requirements were injected successfully - cannot proceed")
            return
        
        # Step 4: Test Conceptualizer API
        print("\nStep 4: Testing Conceptualizer API...")
        conceptualizer_working = await test_conceptualizer_api(token)
        
        # Summary
        print("\n" + "=" * 50)
        print("🎯 TEST SUMMARY:")
        print(f"   ✅ Individual Tables: {'✓' if table_id else '✗'}")
        print(f"   ✅ Requirements: {successful_reqs}/{len(UAS_REQUIREMENTS)} injected")
        print(f"   ✅ Conceptualizer API: {'✓' if conceptualizer_working else '✗'}")
        
        if conceptualizer_working:
            print("\n🚀 Ready for DAS conceptualization testing!")
            print("   Next: Navigate to Conceptualizer Workbench → select BSEO.A → test visualization")
        else:
            print("\n❌ Setup incomplete - check errors above")
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
