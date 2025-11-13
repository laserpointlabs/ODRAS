#!/usr/bin/env python3
"""
RAG Verification Test Report Generator

Tests ModularRAGService with various questions and generates a readable report.
"""

import httpx
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any


BASE_URL = "http://localhost:8000"
TEST_USER = "das_service"
TEST_PASSWORD = "das_service_2024!"


class RAGTestReporter:
    """Generate test report for RAG functionality."""
    
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.token: str = ""
        self.project_id: str = ""
    
    async def authenticate(self, client: httpx.AsyncClient) -> bool:
        """Authenticate and get token."""
        try:
            response = await client.post(
                f"{BASE_URL}/api/auth/login",
                json={"username": TEST_USER, "password": TEST_PASSWORD}
            )
            if response.status_code == 200:
                self.token = response.json()["token"]
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    async def get_or_create_project(self, client: httpx.AsyncClient) -> bool:
        """Get existing project or create new one."""
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            # Try to get existing projects
            response = await client.get(f"{BASE_URL}/api/projects", headers=headers)
            if response.status_code == 200:
                projects = response.json()
                if isinstance(projects, list) and len(projects) > 0:
                    self.project_id = projects[0]["project_id"]
                    print(f"✓ Using existing project: {self.project_id}")
                    return True
                elif isinstance(projects, dict) and "projects" in projects:
                    if projects["projects"]:
                        self.project_id = projects["projects"][0]["project_id"]
                        print(f"✓ Using existing project: {self.project_id}")
                        return True
            
            # Create new project
            response = await client.post(
                f"{BASE_URL}/api/projects",
                json={"name": f"RAG Test Project {datetime.now().strftime('%Y%m%d_%H%M%S')}"},
                headers=headers
            )
            if response.status_code == 200:
                self.project_id = response.json()["project"]["project_id"]
                print(f"✓ Created new project: {self.project_id}")
                return True
            else:
                print(f"❌ Failed to create project: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Project error: {e}")
            return False
    
    async def upload_test_knowledge(self, client: httpx.AsyncClient) -> bool:
        """Upload test knowledge documents to the project."""
        headers = {"Authorization": f"Bearer {self.token}"}
        
        test_documents = [
            {
                "filename": "odras_overview.txt",
                "content": """
ODRAS - Ontology-Driven Requirements Analysis System

ODRAS is a comprehensive system for managing requirements, ontologies, and knowledge in engineering projects. 
The system provides multiple workbenches for different aspects of requirements engineering.

Key Features:
- Requirements Workbench: Extract, manage, and analyze requirements from documents
- Ontology Workbench: Visual ontology editing and management
- Knowledge Workbench: Document management and RAG-based knowledge search
- Conceptualizer Workbench: System architecture visualization
- DAS (Digital Assistant System): AI-powered assistance for requirements work

The system uses SQL-first storage with vector mirroring for efficient knowledge retrieval.
ModularRAGService provides flexible retrieval-augmented generation capabilities.
""",
                "doc_type": "requirements"
            },
            {
                "filename": "safety_requirements.txt",
                "content": """
Safety Requirements and Considerations

All systems must comply with the following safety requirements:

1. System Reliability: The system must maintain 99.9% uptime availability
2. Data Security: All data must be encrypted at rest and in transit
3. Access Control: Role-based access control must be implemented
4. Audit Logging: All system actions must be logged for audit purposes
5. Backup and Recovery: Daily backups with 30-day retention period

Safety considerations include:
- Fail-safe mechanisms for critical operations
- Input validation to prevent injection attacks
- Rate limiting to prevent abuse
- Monitoring and alerting for system health
""",
                "doc_type": "requirements"
            },
            {
                "filename": "technical_specifications.txt",
                "content": """
Technical Specifications

System Architecture:
- Backend: Python FastAPI with PostgreSQL database
- Vector Storage: Qdrant for semantic search
- RAG System: ModularRAGService with hybrid retrieval
- Frontend: HTML/JavaScript single-page application

Performance Requirements:
- API response time: < 2 seconds for standard queries
- RAG query processing: < 3 seconds
- Concurrent users: Support up to 100 simultaneous users
- Database: PostgreSQL 14+ with connection pooling

Integration Requirements:
- RESTful API with OpenAPI documentation
- Authentication via JWT tokens
- Support for multiple embedding models
- Plugin architecture for extensibility
""",
                "doc_type": "specifications"
            },
            {
                "filename": "compliance_requirements.txt",
                "content": """
Compliance Requirements

The system must comply with the following standards and regulations:

1. Data Privacy: GDPR compliance for user data protection
2. Security Standards: NIST Cybersecurity Framework alignment
3. Accessibility: WCAG 2.1 AA compliance for web interfaces
4. Documentation: ISO/IEC 25010 software quality standards

Compliance verification includes:
- Regular security audits
- Privacy impact assessments
- Accessibility testing
- Documentation reviews

All compliance requirements must be documented and tracked through the requirements workbench.
""",
                "doc_type": "requirements"
            },
            {
                "filename": "system_architecture.txt",
                "content": """
System Architecture Overview

ODRAS follows a modular plugin-based architecture:

Core Components:
- Plugin System: Hot-swappable workbenches and services
- RAG Engine: ModularRAGService with abstract interfaces
- Database Layer: SQL-first storage with vector mirroring
- API Gateway: FastAPI with router registration

Architecture Principles:
- Separation of concerns: Each workbench is independent
- Dependency injection: Services can be swapped for testing
- Event-driven: Components communicate via event bus
- Scalable: Horizontal scaling support for all components

The system is designed for extensibility, allowing new workbenches and features to be added without modifying core code.
""",
                "doc_type": "architecture"
            }
        ]
        
        print(f"\n📚 Uploading {len(test_documents)} test documents...")
        uploaded_count = 0
        
        for doc in test_documents:
            try:
                # Create file-like object
                import io
                file_content = doc["content"].strip().encode('utf-8')
                files = {
                    "file": (doc["filename"], io.BytesIO(file_content), "text/plain")
                }
                
                # Upload document via files API (which auto-processes for knowledge)
                response = await client.post(
                    f"{BASE_URL}/api/files/upload",
                    files=files,
                    data={
                        "project_id": self.project_id,
                        "process_for_knowledge": "true",
                        "document_type": doc.get("doc_type", "requirements")
                    },
                    headers=headers,
                    timeout=60.0  # Longer timeout for processing
                )
                
                if response.status_code in [200, 201]:
                    uploaded_count += 1
                    print(f"  ✓ Uploaded: {doc['filename']}")
                else:
                    print(f"  ⚠️  Failed to upload {doc['filename']}: {response.status_code}")
                    
            except Exception as e:
                print(f"  ❌ Error uploading {doc['filename']}: {e}")
        
        if uploaded_count > 0:
            print(f"\n✓ Successfully uploaded {uploaded_count}/{len(test_documents)} documents")
            print("⏳ Waiting 10 seconds for document processing and chunking...")
            await asyncio.sleep(10)  # Wait for ingestion and chunking to complete
            return True
        else:
            print("⚠️  No documents uploaded")
            return False
    
    async def test_rag_query(
        self,
        client: httpx.AsyncClient,
        question: str,
        description: str = "",
        max_chunks: int = 10,
        similarity_threshold: float = 0.3
    ) -> Dict[str, Any]:
        """Test a RAG query and return results."""
        headers = {"Authorization": f"Bearer {self.token}"}
        
        test_result = {
            "question": question,
            "description": description,
            "timestamp": datetime.now().isoformat(),
            "status": "pending",
            "response": "",
            "chunks_found": 0,
            "sources": [],
            "error": None,
            "response_time_ms": 0
        }
        
        try:
            import time
            start_time = time.time()
            
            response = await client.post(
                f"{BASE_URL}/api/knowledge/query",
                json={
                    "question": question,
                    "project_id": self.project_id,
                    "max_chunks": max_chunks,
                    "similarity_threshold": similarity_threshold
                },
                headers=headers,
                timeout=30.0
            )
            
            response_time = (time.time() - start_time) * 1000
            test_result["response_time_ms"] = round(response_time, 2)
            
            if response.status_code == 200:
                data = response.json()
                test_result["status"] = "success"
                test_result["response"] = data.get("response", "")
                test_result["chunks_found"] = data.get("chunks_found", 0)
                test_result["sources"] = data.get("sources", [])
                test_result["confidence"] = data.get("confidence", "unknown")
            else:
                test_result["status"] = "error"
                test_result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"
                
        except Exception as e:
            test_result["status"] = "error"
            test_result["error"] = str(e)
        
        return test_result
    
    def generate_report(self) -> str:
        """Generate formatted test report."""
        report = []
        report.append("=" * 80)
        report.append("RAG MODULARIZATION VERIFICATION TEST REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Project ID: {self.project_id}")
        report.append(f"Total Tests: {len(self.results)}")
        report.append("")
        
        # Summary
        successful = sum(1 for r in self.results if r["status"] == "success")
        failed = sum(1 for r in self.results if r["status"] == "error")
        total_chunks = sum(r["chunks_found"] for r in self.results)
        avg_response_time = sum(r["response_time_ms"] for r in self.results) / len(self.results) if self.results else 0
        
        report.append("SUMMARY")
        report.append("-" * 80)
        report.append(f"✅ Successful Queries: {successful}/{len(self.results)}")
        report.append(f"❌ Failed Queries: {failed}/{len(self.results)}")
        report.append(f"📊 Total Chunks Retrieved: {total_chunks}")
        report.append(f"⏱️  Average Response Time: {avg_response_time:.2f} ms")
        report.append("")
        
        # Detailed Results
        report.append("DETAILED TEST RESULTS")
        report.append("=" * 80)
        report.append("")
        
        for i, result in enumerate(self.results, 1):
            report.append(f"TEST {i}: {result['description'] or 'No description'}")
            report.append("-" * 80)
            report.append(f"Question: {result['question']}")
            report.append(f"Status: {result['status'].upper()}")
            report.append(f"Response Time: {result['response_time_ms']} ms")
            report.append(f"Chunks Found: {result['chunks_found']}")
            
            if result['status'] == 'success':
                report.append(f"Confidence: {result.get('confidence', 'unknown')}")
                report.append("")
                report.append("Response:")
                response_text = result['response']
                # Wrap long responses
                if len(response_text) > 500:
                    report.append(response_text[:500] + "...")
                    report.append(f"[Response truncated - full length: {len(response_text)} characters]")
                else:
                    report.append(response_text)
                
                if result['sources']:
                    report.append("")
                    report.append(f"Sources ({len(result['sources'])}):")
                    for j, source in enumerate(result['sources'][:5], 1):  # Show first 5
                        asset_id = source.get('asset_id', 'unknown')
                        title = source.get('title', 'Unknown')
                        # API returns 'relevance_score', fallback to 'score' for backward compatibility
                        score = source.get('relevance_score') or source.get('score', 0)
                        report.append(f"  {j}. Asset: {asset_id} ({title}), Score: {score:.3f}")
                    if len(result['sources']) > 5:
                        report.append(f"  ... and {len(result['sources']) - 5} more sources")
            else:
                report.append("")
                report.append(f"Error: {result['error']}")
            
            report.append("")
            report.append("")
        
        # Conclusion
        report.append("=" * 80)
        report.append("CONCLUSION")
        report.append("-" * 80)
        if successful == len(self.results):
            report.append("✅ ALL TESTS PASSED - ModularRAGService is working correctly!")
        elif successful > 0:
            report.append(f"⚠️  PARTIAL SUCCESS - {successful}/{len(self.results)} tests passed")
            report.append("Some queries may not have matching knowledge in the database.")
        else:
            report.append("❌ ALL TESTS FAILED - Please check system configuration")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    async def run_tests(self):
        """Run all test queries."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Authenticate
            print("🔐 Authenticating...")
            if not await self.authenticate(client):
                return False
            
            # Get or create project
            print("📁 Setting up project...")
            if not await self.get_or_create_project(client):
                return False
            
            # Upload test knowledge
            await self.upload_test_knowledge(client)
            
            # Test queries
            test_queries = [
                {
                    "question": "What is ODRAS?",
                    "description": "General system question"
                },
                {
                    "question": "What are the main requirements?",
                    "description": "Requirements query"
                },
                {
                    "question": "Tell me about the project",
                    "description": "Project context query"
                },
                {
                    "question": "What safety considerations are mentioned?",
                    "description": "Safety-related query"
                },
                {
                    "question": "What are the technical specifications?",
                    "description": "Technical specifications query"
                },
                {
                    "question": "Summarize the key documents",
                    "description": "Summary query"
                },
                {
                    "question": "What compliance requirements exist?",
                    "description": "Compliance query"
                },
                {
                    "question": "Describe the system architecture",
                    "description": "Architecture query"
                }
            ]
            
            print(f"\n🧪 Running {len(test_queries)} test queries...\n")
            
            for i, query_info in enumerate(test_queries, 1):
                print(f"Test {i}/{len(test_queries)}: {query_info['question']}")
                result = await self.test_rag_query(
                    client,
                    query_info["question"],
                    query_info["description"]
                )
                self.results.append(result)
                
                # Show quick status
                if result["status"] == "success":
                    print(f"  ✅ Success - {result['chunks_found']} chunks, {result['response_time_ms']:.0f}ms")
                else:
                    print(f"  ❌ Failed - {result.get('error', 'Unknown error')}")
            
            return True


async def main():
    """Main test execution."""
    print("=" * 80)
    print("RAG MODULARIZATION VERIFICATION TEST")
    print("=" * 80)
    print()
    
    reporter = RAGTestReporter()
    
    if await reporter.run_tests():
        # Generate report
        report = reporter.generate_report()
        
        # Print to console
        print("\n" + report)
        
        # Save to file
        report_file = f"RAG_TEST_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, "w") as f:
            f.write(report)
        
        print(f"\n📄 Report saved to: {report_file}")
        print("=" * 80)
    else:
        print("\n❌ Test execution failed. Please check system status.")


if __name__ == "__main__":
    asyncio.run(main())
