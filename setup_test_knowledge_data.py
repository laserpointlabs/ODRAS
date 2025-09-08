#!/usr/bin/env python3
"""
Complete test data setup script for ODRAS Knowledge Management.

This script creates:
1. A test project for jdehart
2. Meaningful test documents
3. Knowledge assets from those documents
4. Tests RAG functionality

Run this to set up a complete test environment.
"""
import asyncio
import httpx
import time
import json

# Test documents with meaningful content
TEST_DOCUMENTS = {
    "navigation_system_requirements.md": """# Navigation System Requirements

## 1. Functional Requirements

### 1.1 Core Navigation Functions
- **REQ-NAV-001**: The navigation system SHALL provide real-time position tracking with accuracy within 3 meters
- **REQ-NAV-002**: The system SHALL support waypoint navigation with automatic route calculation
- **REQ-NAV-003**: The system SHALL provide turn-by-turn guidance with voice prompts
- **REQ-NAV-004**: The system SHALL support multiple coordinate systems (WGS84, UTM, local grid)

### 1.2 User Interface Requirements  
- **REQ-UI-001**: The navigation interface SHALL display current position, heading, and speed
- **REQ-UI-002**: The system SHALL provide a map view with zoom levels from 1:100 to 1:50000
- **REQ-UI-003**: The interface SHALL support both day and night display modes
- **REQ-UI-004**: All critical navigation information SHALL be visible within 2 seconds of system startup

### 1.3 Data Management
- **REQ-DATA-001**: The system SHALL store route history for the last 30 days
- **REQ-DATA-002**: Waypoint data SHALL be persistent across power cycles
- **REQ-DATA-003**: The system SHALL support import/export of route data in GPX format

## 2. Performance Requirements

### 2.1 Response Time
- Position updates: <= 1 second
- Route calculation: <= 5 seconds for routes up to 100km
- Map rendering: <= 2 seconds for any zoom level

### 2.2 Accuracy
- Position accuracy: 3 meters CEP (Circular Error Probable)
- Heading accuracy: ±2 degrees
- Speed accuracy: ±0.1 m/s

## 3. Safety Requirements

### 3.1 Critical Functions
- **REQ-SAFETY-001**: Navigation system failures SHALL NOT affect primary vehicle systems
- **REQ-SAFETY-002**: The system SHALL provide audible alerts for critical navigation events
- **REQ-SAFETY-003**: Emergency stop functionality SHALL be available within 1 button press

## 4. Environmental Requirements

- Operating temperature: -20°C to +60°C
- Humidity: 5% to 95% non-condensing
- Vibration resistance: MIL-STD-810G
- Water resistance: IP65 rating required
""",
    "safety_protocols.md": """# Safety Protocols and Procedures

## 1. Pre-Operation Safety Checks

### 1.1 System Verification
1. **Power Systems Check**
   - Verify all power connections are secure
   - Check battery levels are above 80%
   - Test backup power systems functionality

2. **Navigation Equipment Check**
   - Confirm GPS signal lock (minimum 4 satellites)
   - Verify compass calibration within ±1 degree
   - Test emergency beacon functionality

3. **Communication Systems**
   - Radio check with control station
   - Verify emergency communication channels
   - Test data link connectivity

### 1.2 Environmental Assessment
- Check weather conditions and forecasts
- Assess visibility conditions (minimum 500m required)
- Verify operational area is clear of obstacles
- Confirm no-fly zones and restricted areas

## 2. Operational Safety Procedures

### 2.1 Normal Operations
- Maintain continuous monitoring of all systems
- Report position updates every 15 minutes
- Monitor fuel/power consumption rates
- Maintain safe separation distances (minimum 100m)

### 2.2 Emergency Procedures

#### 2.2.1 System Failure Response
1. **Primary Navigation Failure**
   - Switch to backup navigation system immediately
   - Report failure to control station
   - Return to base using predetermined safe route
   - Do not continue mission without primary navigation

2. **Communication Loss**
   - Follow predetermined communication recovery procedures
   - Return to designated rally point
   - Activate emergency beacon if no contact within 30 minutes

3. **Power System Emergency**
   - Implement power conservation measures immediately
   - Disable non-essential systems
   - Execute emergency landing/return procedure
   - Activate emergency locator beacon

## 3. Maintenance Safety

### 3.1 Routine Maintenance
- All maintenance SHALL be performed by certified personnel only
- Use proper lockout/tagout procedures during maintenance
- Verify all safety systems after maintenance completion
- Document all maintenance activities in system logs

### 3.2 Safety Equipment Requirements
- Personal protective equipment (PPE) required for all personnel
- Emergency first aid kit available at all times  
- Fire suppression equipment tested monthly
- Emergency communication devices for all personnel

## 4. Risk Assessment Matrix

| Risk Level | Probability | Impact | Mitigation Required |
|------------|-------------|---------|-------------------|
| Critical   | High       | Severe  | Immediate action required |
| High       | Medium     | Major   | Action required within 24 hours |
| Medium     | Low        | Moderate| Action required within 1 week |
| Low        | Very Low   | Minor   | Monitor and review monthly |

## 5. Training Requirements

### 5.1 Personnel Certification
- All operators MUST complete 40-hour safety training program
- Annual recertification required
- Emergency procedure drills conducted quarterly
- Specialized equipment training as required

### 5.2 Competency Assessment
- Written examination with minimum 85% pass rate
- Practical demonstration of emergency procedures
- Medical fitness assessment annually
- Background security clearance for sensitive operations
""",
    "technical_specifications.md": """# Technical Specifications

## 1. System Architecture

### 1.1 Hardware Components
- **Primary Processor**: ARM Cortex-A78 quad-core, 2.5 GHz
- **Memory**: 16 GB DDR4 RAM, 512 GB NVMe SSD storage
- **Display**: 15.6" 1920x1080 sunlight-readable LCD touchscreen
- **GPS Receiver**: Multi-constellation GNSS (GPS, GLONASS, Galileo, BeiDou)

### 1.2 Communication Interfaces
- **Radio**: VHF/UHF dual-band transceiver, 136-174 MHz / 400-520 MHz
- **Data Link**: 4G LTE cellular modem with failover to satellite
- **Local Connectivity**: Wi-Fi 802.11ac, Bluetooth 5.2, Ethernet 1000BASE-T
- **Serial Interfaces**: 4x RS-232, 2x RS-485, CAN bus interface

### 1.3 Sensor Integration
- **Inertial Measurement Unit**: 9-axis IMU with gyroscopes, accelerometers, magnetometers
- **Environmental Sensors**: Temperature, humidity, barometric pressure
- **Optical Sensors**: Daylight/infrared cameras with object detection capability

## 2. Software Specifications

### 2.1 Operating System
- **Base OS**: Linux Ubuntu 22.04 LTS (real-time kernel)
- **Container Runtime**: Docker Engine for application isolation
- **Database**: PostgreSQL 14.x for mission data storage
- **Message Queue**: Redis for inter-process communication

### 2.2 Navigation Software Stack
- **Core Navigation**: Custom C++ navigation engine with real-time processing
- **Mapping Framework**: OpenStreetMap integration with custom tile server
- **Route Planning**: A* algorithm implementation with multi-criteria optimization
- **Sensor Fusion**: Extended Kalman Filter for position/velocity estimation

### 2.3 User Interface
- **Framework**: React-based web interface with responsive design
- **Graphics**: WebGL-accelerated map rendering
- **Real-time Updates**: WebSocket communication for live data feeds
- **Accessibility**: WCAG 2.1 AA compliant interface design

## 3. Performance Specifications

### 3.1 Processing Performance
- **CPU Utilization**: Maximum 80% under normal load
- **Memory Usage**: Maximum 12 GB under normal operations
- **Storage I/O**: Minimum 500 MB/s sequential read/write performance
- **Network Throughput**: Minimum 10 Mbps data rate for mission-critical applications

### 3.2 Real-time Requirements
- **Position Update Rate**: 10 Hz minimum, 50 Hz preferred
- **Sensor Data Processing**: Maximum 20ms latency from sensor to display
- **Command Response Time**: Maximum 100ms for user interface interactions
- **Emergency Response**: Maximum 50ms for safety-critical alerts

## 4. Interface Specifications

### 4.1 External System Interfaces
- **Command & Control**: MIL-STD-1553 bus interface for military applications
- **Payload Integration**: Custom API for sensor/payload data integration
- **Ground Station**: TCP/IP based telemetry and command interface
- **Legacy Systems**: Protocol converters for older equipment integration

### 4.2 Data Formats
- **Position Data**: NMEA 0183 standard messages
- **Map Data**: GeoJSON format for vector data, GeoTIFF for raster
- **Mission Plans**: XML-based mission planning format
- **Log Data**: JSON-structured logging with timestamp precision to microseconds

## 5. Security Specifications

### 5.1 Data Protection
- **Encryption**: AES-256 encryption for all stored sensitive data
- **Communication Security**: TLS 1.3 for all network communications
- **Authentication**: Multi-factor authentication with PKI certificates
- **Access Control**: Role-based access control (RBAC) with audit logging

### 5.2 Cybersecurity Compliance
- **Standards Compliance**: NIST Cybersecurity Framework
- **Vulnerability Management**: Automated security scanning and patch management
- **Incident Response**: 24/7 security monitoring and response procedures
- **Data Backup**: Encrypted backup with 3-2-1 backup strategy implementation
""",
}


class TestDataSetup:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.jdehart_token = None
        self.admin_token = None
        self.test_project_id = None

    async def authenticate_users(self):
        """Authenticate both admin and jdehart users"""
        print("🔐 Step 1: Authenticating users...")

        async with httpx.AsyncClient(timeout=30) as client:
            # Authenticate jdehart
            jdehart_response = await client.post(
                f"{self.base_url}/api/auth/login",
                json={"username": "jdehart", "password": "jdehart"},
            )

            if jdehart_response.status_code != 200:
                raise Exception(
                    f"jdehart authentication failed: {jdehart_response.status_code}"
                )

            self.jdehart_token = jdehart_response.json()["token"]
            print("✅ jdehart authenticated")

            # Authenticate admin
            admin_response = await client.post(
                f"{self.base_url}/api/auth/login",
                json={"username": "admin", "password": "admin"},
            )

            if admin_response.status_code != 200:
                raise Exception(
                    f"Admin authentication failed: {admin_response.status_code}"
                )

            self.admin_token = admin_response.json()["token"]
            print("✅ admin authenticated")

    async def get_default_project(self):
        """Get the Default Project instead of creating a new one"""
        print("\n📁 Step 2: Getting Default Project...")

        async with httpx.AsyncClient(timeout=30) as client:
            # Get all projects for the user
            response = await client.get(
                f"{self.base_url}/api/projects",
                headers={"Authorization": f"Bearer {self.jdehart_token}"},
            )

            if response.status_code == 200:
                data = response.json()
                projects = data.get("projects", [])

                # Find the Default Project
                for project in projects:
                    if project.get("name") == "Default Project":
                        self.test_project_id = project["project_id"]
                        print(f"✅ Using Default Project (ID: {self.test_project_id})")
                        return True

                print("❌ Default Project not found")
                return False
            else:
                print(
                    f"❌ Failed to get projects: {response.status_code} - {response.text}"
                )
                return False

    async def upload_test_documents(self):
        """Upload test documents to the project"""
        print(f"\n📄 Step 3: Uploading test documents...")

        uploaded_files = []

        async with httpx.AsyncClient(timeout=60) as client:
            for filename, content in TEST_DOCUMENTS.items():
                print(f"   📤 Uploading {filename}...")

                # Determine document type from filename
                doc_type = (
                    "requirements"
                    if "requirements" in filename
                    else (
                        "safety"
                        if "safety" in filename
                        else "specifications" if "spec" in filename else "documentation"
                    )
                )

                # Prepare form data
                files = {"file": (filename, content.encode("utf-8"), "text/markdown")}

                data = {
                    "project_id": self.test_project_id,
                    "tags": json.dumps(
                        {
                            "docType": doc_type,
                            "status": "active",
                            "testDocument": True,
                            "domain": (
                                "navigation"
                                if "navigation" in filename
                                else "safety" if "safety" in filename else "technical"
                            ),
                        }
                    ),
                    "process_for_knowledge": "true",
                    "embedding_model": "all-MiniLM-L6-v2",
                    "chunking_strategy": "hybrid",
                }

                response = await client.post(
                    f"{self.base_url}/api/files/upload",
                    headers={"Authorization": f"Bearer {self.jdehart_token}"},
                    files=files,
                    data=data,
                )

                if response.status_code == 200:
                    result = response.json()
                    file_id = result.get("file_id")
                    message = result.get("message", "")

                    print(f"   ✅ {filename} uploaded successfully (ID: {file_id})")
                    if "knowledge asset" in message:
                        print(f"      🧠 Knowledge processing initiated!")

                    uploaded_files.append(
                        {"filename": filename, "file_id": file_id, "doc_type": doc_type}
                    )
                else:
                    print(
                        f"   ❌ Failed to upload {filename}: {response.status_code} - {response.text}"
                    )

        return uploaded_files

    async def wait_for_processing(self, max_wait_seconds=120):
        """Wait for knowledge processing to complete"""
        print(
            f"\n⏳ Step 4: Waiting for knowledge processing (max {max_wait_seconds}s)..."
        )

        start_time = time.time()

        async with httpx.AsyncClient(timeout=30) as client:
            while (time.time() - start_time) < max_wait_seconds:
                # Check knowledge assets
                response = await client.get(
                    f"{self.base_url}/api/knowledge/assets",
                    headers={"Authorization": f"Bearer {self.jdehart_token}"},
                )

                if response.status_code == 200:
                    data = response.json()
                    assets = data.get("assets", [])

                    if assets:
                        completed_assets = [
                            a for a in assets if a.get("status") == "active"
                        ]
                        processing_assets = [
                            a
                            for a in assets
                            if a.get("status") in ["processing", "pending"]
                        ]

                        print(
                            f"   📊 Assets: {len(completed_assets)} completed, {len(processing_assets)} processing"
                        )

                        if (
                            len(completed_assets) >= len(TEST_DOCUMENTS)
                            and len(processing_assets) == 0
                        ):
                            print(
                                f"   ✅ All {len(completed_assets)} knowledge assets processed successfully!"
                            )
                            return True
                    else:
                        print("   ⏳ No knowledge assets found yet...")
                else:
                    print(f"   ⚠️ Failed to check assets: {response.status_code}")

                await asyncio.sleep(5)

            print(f"   ⚠️ Timeout waiting for processing completion")
            return False

    async def test_rag_functionality(self):
        """Test RAG functionality with the created knowledge base"""
        print(f"\n🧠 Step 5: Testing RAG functionality...")

        test_queries = [
            "What are the navigation system requirements?",
            "What safety procedures should be followed?",
            "What are the technical specifications for the processor?",
            "What is the required position accuracy?",
            "Describe the emergency procedures",
        ]

        async with httpx.AsyncClient(timeout=60) as client:
            for i, question in enumerate(test_queries):
                print(f"\n   🔍 Test Query {i+1}: '{question}'")

                response = await client.post(
                    f"{self.base_url}/api/knowledge/query",
                    headers={"Authorization": f"Bearer {self.jdehart_token}"},
                    json={
                        "question": question,
                        "project_id": self.test_project_id,
                        "response_style": "comprehensive",
                        "max_chunks": 3,
                        "similarity_threshold": 0.4,
                        "include_metadata": True,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    success = data.get("success", False)
                    chunks_found = data.get("chunks_found", 0)
                    confidence = data.get("confidence", "unknown")

                    if success and chunks_found > 0:
                        response_text = data.get("response", "")
                        preview = (
                            response_text[:150] + "..."
                            if len(response_text) > 150
                            else response_text
                        )

                        print(
                            f"   ✅ SUCCESS: {chunks_found} sources, {confidence} confidence"
                        )
                        print(f"      Response: {preview}")

                        # Show sources
                        sources = data.get("sources", [])
                        if sources:
                            print(f"      📚 Sources:")
                            for j, source in enumerate(sources[:2]):
                                title = source.get("title", "Unknown")
                                doc_type = source.get("document_type", "unknown")
                                relevance = int(source.get("relevance_score", 0) * 100)
                                print(
                                    f"         {j+1}. {title} ({doc_type}) - {relevance}% relevant"
                                )
                    else:
                        print(f"   ❌ FAILED: {chunks_found} chunks found")
                        if "error" in data:
                            print(f"      Error: {data['error']}")
                else:
                    print(
                        f"   ❌ Query failed: {response.status_code} - {response.text}"
                    )

                # Small delay between queries
                await asyncio.sleep(1)

        print(f"\n🎉 RAG testing completed!")

    async def show_final_summary(self):
        """Show final summary of created test data"""
        print(f"\n📊 Final Summary:")
        print(f"=" * 60)

        async with httpx.AsyncClient(timeout=30) as client:
            # Get knowledge assets
            response = await client.get(
                f"{self.base_url}/api/knowledge/assets",
                headers={"Authorization": f"Bearer {self.jdehart_token}"},
            )

            if response.status_code == 200:
                data = response.json()
                assets = data.get("assets", [])

                print(f"🧠 Knowledge Assets Created: {len(assets)}")
                total_chunks = 0
                for asset in assets:
                    stats = asset.get("processing_stats", {})
                    chunks = stats.get("chunk_count", 0)
                    tokens = stats.get("token_count", 0)
                    title = asset.get("title", "Unknown")
                    doc_type = asset.get("document_type", "unknown")

                    print(
                        f"   • {title} ({doc_type}): {chunks} chunks, {tokens} tokens"
                    )
                    total_chunks += chunks

                print(f"📊 Total Chunks: {total_chunks}")

        print(f"\n🎯 Test Environment Ready!")
        print(f"   Project: Default Project ({self.test_project_id})")
        print(f"   User: jdehart (password: jdehart)")
        print(f"   Documents: {len(TEST_DOCUMENTS)} technical documents processed")
        print(f"   URL: http://localhost:8000/app#wb=knowledge")
        print(f"\n💡 Try asking questions like:")
        print(f"   • 'What are the navigation system requirements?'")
        print(f"   • 'What safety procedures should be followed?'")
        print(f"   • 'What are the technical specifications?'")


async def main():
    """Main setup function"""
    print("🚀 ODRAS Knowledge Management Test Data Setup")
    print("=" * 60)
    print("This script will create a complete test environment with:")
    print("• Test project for jdehart user")
    print("• Technical documents with real requirements")
    print("• Knowledge assets with vector embeddings")
    print("• RAG functionality testing")
    print()

    setup = TestDataSetup()

    try:
        # Step 1: Authenticate users
        await setup.authenticate_users()

        # Step 2: Get Default Project
        if not await setup.get_default_project():
            return False

        # Step 3: Upload test documents
        uploaded_files = await setup.upload_test_documents()
        if not uploaded_files:
            print("❌ No files uploaded successfully")
            return False

        # Step 4: Wait for processing
        if not await setup.wait_for_processing():
            print("⚠️ Processing may not be complete, but continuing with tests...")

        # Step 5: Test RAG functionality
        await setup.test_rag_functionality()

        # Step 6: Show summary
        await setup.show_final_summary()

        return True

    except Exception as e:
        print(f"❌ Setup failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
