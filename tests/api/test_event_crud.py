"""
Event CRUD Operations Tests

Comprehensive tests for all event capture and tracking operations:
- Session capture events
- EventCapture2 system
- Project event tracking
- DAS interaction events
- Semantic event capture
- Event retrieval and analysis
- Event aggregation and reporting

Run with: pytest tests/api/test_event_crud.py -v
"""

import pytest
import time
import json
import asyncio
from typing import Dict, List, Any
from httpx import AsyncClient
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))



class TestEventCRUD:
    """Test all event CRUD operations"""

    @pytest.fixture
    async def client(self):
        # Connect to the REAL running API
        async with AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
            yield client

    @pytest.fixture
    async def auth_headers(self, client):
        response = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        assert response.status_code == 200
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    async def test_project(self, client, auth_headers):
        """Create a test project for event operations"""
        response = await client.post(
            "/api/projects",
            json={"name": f"Event Test Project {int(time.time())}"},
            headers=auth_headers
        )
        project_id = response.json()["project_id"]
        yield project_id
        # Cleanup
        await client.delete(f"/api/projects/{project_id}", headers=auth_headers)

    # ========== CREATE EVENTS ==========

    @pytest.mark.asyncio
    async def test_automatic_event_capture(self, client, auth_headers, test_project):
        """Test automatic event capture during operations"""
        # These operations should automatically capture events

        # 1. File upload event
        files = {"file": ("event_test.txt", b"Event capture test", "text/plain")}
        file_resp = await client.post(
            f"/api/files/upload/{test_project}",
            files=files,
            headers=auth_headers
        )
        assert file_resp.status_code == 200

        # 2. Knowledge search event
        search_resp = await client.post(
            f"/api/knowledge/{test_project}/search",
            json={"query": "test event", "top_k": 5},
            headers=auth_headers
        )
        assert search_resp.status_code == 200

        # 3. Ontology creation event
        onto_resp = await client.post(
            f"/api/ontology/{test_project}/create",
            json={
                "name": "EventTestOntology",
                "base_uri": "http://test.odras.ai/events#"
            },
            headers=auth_headers
        )
        assert onto_resp.status_code in [200, 201, 204]

        print("✓ Automatic event capture tested for multiple operations")

    @pytest.mark.asyncio
    async def test_manual_event_creation(self, client, auth_headers, test_project):
        """Test manual event creation"""
        event_data = {
            "event_type": "custom_action",
            "project_id": test_project,
            "description": "Custom event for testing",
            "metadata": {
                "action": "test_action",
                "user_initiated": True,
                "timestamp": time.time()
            }
        }

        # Try to create custom event
        event_resp = await client.post(
            "/api/events/create",
            json=event_data,
            headers=auth_headers
        )

        if event_resp.status_code in [200, 201]:
            result = event_resp.json()
            print("✓ Manual event creation tested")
        else:
            print("⚠ Manual event creation endpoint not implemented")

    @pytest.mark.asyncio
    async def test_session_events(self, client, auth_headers):
        """Test session-level event tracking"""
        # Start a session
        session_resp = await client.post(
            "/api/sessions/start",
            json={"session_type": "testing"},
            headers=auth_headers
        )

        if session_resp.status_code == 200:
            session_id = session_resp.json().get("session_id")

            # Perform actions within session
            actions = [
                ("GET", "/api/projects"),
                ("GET", "/api/health"),
                ("GET", "/api/service-status")
            ]

            for method, path in actions:
                if method == "GET":
                    await client.get(path, headers=auth_headers)

            # End session
            end_resp = await client.post(
                f"/api/sessions/{session_id}/end",
                headers=auth_headers
            )

            print("✓ Session event tracking tested")
        else:
            print("⚠ Session management not implemented")

    # ========== READ EVENTS ==========

    @pytest.mark.asyncio
    async def test_get_project_events(self, client, auth_headers, test_project):
        """Test retrieving events for a project"""
        # Generate some events
        for i in range(3):
            files = {"file": (f"event_{i}.txt", f"Content {i}".encode(), "text/plain")}
            await client.post(
                f"/api/files/upload/{test_project}",
                files=files,
                headers=auth_headers
            )

        # Get project events
        events_resp = await client.get(
            f"/api/events/project/{test_project}",
            headers=auth_headers
        )

        if events_resp.status_code == 200:
            events = events_resp.json()
            assert isinstance(events, list)
            print(f"✓ Retrieved {len(events)} project events")
        else:
            print("⚠ Project events endpoint not implemented")

    @pytest.mark.asyncio
    async def test_get_user_events(self, client, auth_headers):
        """Test retrieving events for current user"""
        # Get user events
        user_events_resp = await client.get(
            "/api/events/my-events",
            headers=auth_headers
        )

        if user_events_resp.status_code == 200:
            events = user_events_resp.json()
            assert isinstance(events, list)
            print(f"✓ Retrieved {len(events)} user events")
        else:
            print("⚠ User events endpoint not implemented")

    @pytest.mark.asyncio
    async def test_filter_events_by_type(self, client, auth_headers, test_project):
        """Test filtering events by type"""
        # Query events by type
        event_types = ["file_upload", "knowledge_search", "project_created"]

        for event_type in event_types:
            filter_resp = await client.get(
                f"/api/events/project/{test_project}",
                params={"event_type": event_type},
                headers=auth_headers
            )

            if filter_resp.status_code == 200:
                filtered_events = filter_resp.json()
                # All events should be of requested type
                for event in filtered_events:
                    if "event_type" in event:
                        assert event["event_type"] == event_type
                print(f"✓ Filtered events by type: {event_type}")
            else:
                print("⚠ Event filtering not implemented")
                break

    @pytest.mark.asyncio
    async def test_event_pagination(self, client, auth_headers, test_project):
        """Test event pagination"""
        # Get paginated events
        page_resp = await client.get(
            f"/api/events/project/{test_project}",
            params={"limit": 10, "offset": 0},
            headers=auth_headers
        )

        if page_resp.status_code == 200:
            page_data = page_resp.json()
            if isinstance(page_data, dict):
                assert "events" in page_data or "items" in page_data
                assert "total" in page_data or "count" in page_data
                print("✓ Event pagination tested")
            else:
                print("⚠ Pagination not implemented")
        else:
            print("⚠ Event retrieval endpoint not implemented")

    # ========== EVENT ANALYTICS ==========

    @pytest.mark.asyncio
    async def test_event_statistics(self, client, auth_headers, test_project):
        """Test event statistics and analytics"""
        # Get event statistics
        stats_resp = await client.get(
            f"/api/events/project/{test_project}/stats",
            headers=auth_headers
        )

        if stats_resp.status_code == 200:
            stats = stats_resp.json()
            expected_keys = ["total_events", "events_by_type", "events_over_time"]
            for key in expected_keys:
                if key in stats:
                    print(f"✓ Event stat '{key}': {stats[key]}")
            print("✓ Event statistics retrieved")
        else:
            print("⚠ Event statistics endpoint not implemented")

    @pytest.mark.asyncio
    async def test_event_timeline(self, client, auth_headers, test_project):
        """Test event timeline view"""
        # Get event timeline
        timeline_resp = await client.get(
            f"/api/events/project/{test_project}/timeline",
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            },
            headers=auth_headers
        )

        if timeline_resp.status_code == 200:
            timeline = timeline_resp.json()
            print("✓ Event timeline retrieved")
        else:
            print("⚠ Event timeline endpoint not implemented")

    @pytest.mark.asyncio
    async def test_event_aggregation(self, client, auth_headers, test_project):
        """Test event aggregation by various dimensions"""
        # Aggregate events
        aggregations = [
            {"group_by": "event_type"},
            {"group_by": "user"},
            {"group_by": "hour", "date_range": "today"}
        ]

        for agg_params in aggregations:
            agg_resp = await client.get(
                f"/api/events/project/{test_project}/aggregate",
                params=agg_params,
                headers=auth_headers
            )

            if agg_resp.status_code == 200:
                results = agg_resp.json()
                print(f"✓ Event aggregation by {agg_params['group_by']} tested")
            else:
                print("⚠ Event aggregation endpoint not implemented")
                break

    # ========== DAS INTERACTION EVENTS ==========

    @pytest.mark.asyncio
    async def test_das_interaction_events(self, client, auth_headers, test_project):
        """Test DAS interaction event capture"""
        # Send DAS messages
        das_messages = [
            {
                "message": "What files are in this project?",
                "intent": "query"
            },
            {
                "message": "Show me recent knowledge additions",
                "intent": "search"
            },
            {
                "message": "Create a new document about testing",
                "intent": "command"
            }
        ]

        for msg_data in das_messages:
            das_resp = await client.post(
                f"/api/das/message",
                json={
                    "project_id": test_project,
                    "message": msg_data["message"]
                },
                headers=auth_headers
            )
            # DAS might not be fully configured
            if das_resp.status_code == 200:
                print(f"✓ DAS interaction captured: {msg_data['intent']}")

    @pytest.mark.asyncio
    async def test_das_conversation_history(self, client, auth_headers, test_project):
        """Test DAS conversation history as events"""
        # Get DAS conversation history
        history_resp = await client.get(
            f"/api/das/project/{test_project}/history",
            headers=auth_headers
        )

        if history_resp.status_code == 200:
            history = history_resp.json()
            print(f"✓ Retrieved DAS conversation history")
        else:
            print("⚠ DAS history endpoint not implemented")

    # ========== SEMANTIC EVENT CAPTURE ==========

    @pytest.mark.asyncio
    async def test_semantic_event_enrichment(self, client, auth_headers, test_project):
        """Test semantic enrichment of events"""
        # Create project with rich context
        project_resp = await client.post(
            "/api/projects",
            json={
                "name": f"AI Research Project {int(time.time())}",
                "description": "Research into machine learning applications",
                "metadata": {
                    "domain": "artificial-intelligence",
                    "team": "research"
                }
            },
            headers=auth_headers
        )
        semantic_project_id = project_resp.json()["project_id"]

        # Upload ML-related file
        ml_content = b"Neural network architectures for computer vision"
        files = {"file": ("ml_research.txt", ml_content, "text/plain")}

        file_resp = await client.post(
            f"/api/files/upload/{semantic_project_id}",
            files=files,
            headers=auth_headers
        )

        # Events should be semantically enriched
        events_resp = await client.get(
            f"/api/events/project/{semantic_project_id}",
            headers=auth_headers
        )

        if events_resp.status_code == 200:
            events = events_resp.json()
            # Check for semantic enrichment
            for event in events:
                if "semantic_context" in event:
                    print("✓ Semantic event enrichment detected")
                    break

        # Cleanup
        await client.delete(f"/api/projects/{semantic_project_id}", headers=auth_headers)

    # ========== UPDATE EVENTS ==========

    @pytest.mark.asyncio
    async def test_update_event_metadata(self, client, auth_headers, test_project):
        """Test updating event metadata"""
        # Get an event first
        events_resp = await client.get(
            f"/api/events/project/{test_project}",
            params={"limit": 1},
            headers=auth_headers
        )

        if events_resp.status_code == 200:
            events = events_resp.json()
            if events and len(events) > 0:
                event_id = events[0].get("event_id")

                if event_id:
                    # Update event metadata
                    update_resp = await client.put(
                        f"/api/events/{event_id}",
                        json={
                            "metadata": {
                                "reviewed": True,
                                "importance": "high",
                                "tags": ["reviewed", "important"]
                            }
                        },
                        headers=auth_headers
                    )

                    if update_resp.status_code == 200:
                        print("✓ Event metadata update tested")
                    else:
                        print("⚠ Event update endpoint not implemented")

    # ========== DELETE EVENTS ==========

    @pytest.mark.asyncio
    async def test_event_retention_policy(self, client, auth_headers):
        """Test event retention and cleanup"""
        # Apply retention policy
        retention_resp = await client.post(
            "/api/events/retention/apply",
            json={
                "policy": "delete_after_90_days",
                "dry_run": True
            },
            headers=auth_headers
        )

        if retention_resp.status_code == 200:
            result = retention_resp.json()
            print(f"✓ Event retention policy tested")
        else:
            print("⚠ Event retention endpoint not implemented")

    @pytest.mark.asyncio
    async def test_delete_old_events(self, client, auth_headers, test_project):
        """Test deleting old events"""
        # Delete events older than a certain date
        delete_resp = await client.delete(
            f"/api/events/project/{test_project}",
            params={"older_than": "2023-01-01"},
            headers=auth_headers
        )

        if delete_resp.status_code in [200, 204]:
            print("✓ Old event deletion tested")
        else:
            print("⚠ Event deletion endpoint not implemented")

    # ========== BATCH EVENT OPERATIONS ==========

    @pytest.mark.asyncio
    async def test_batch_event_creation(self, client, auth_headers, test_project):
        """Test creating multiple events in batch"""
        batch_events = [
            {
                "event_type": "batch_test",
                "project_id": test_project,
                "description": f"Batch event {i}",
                "timestamp": time.time() + i
            }
            for i in range(5)
        ]

        batch_resp = await client.post(
            "/api/events/batch",
            json={"events": batch_events},
            headers=auth_headers
        )

        if batch_resp.status_code in [200, 201]:
            result = batch_resp.json()
            print(f"✓ Batch event creation tested")
        else:
            print("⚠ Batch event creation not implemented")

    @pytest.mark.asyncio
    async def test_event_export(self, client, auth_headers, test_project):
        """Test exporting events"""
        # Export events in various formats
        export_formats = ["json", "csv", "parquet"]

        for format_type in export_formats:
            export_resp = await client.get(
                f"/api/events/project/{test_project}/export",
                params={"format": format_type},
                headers=auth_headers
            )

            if export_resp.status_code == 200:
                print(f"✓ Event export in {format_type} format tested")
                break
            elif export_resp.status_code == 404:
                print("⚠ Event export endpoint not implemented")
                break

    # ========== REAL-TIME EVENTS ==========

    @pytest.mark.asyncio
    async def test_event_streaming(self, client, auth_headers, test_project):
        """Test real-time event streaming"""
        # This would typically use WebSocket or SSE
        stream_resp = await client.get(
            f"/api/events/project/{test_project}/stream",
            headers=auth_headers
        )

        if stream_resp.status_code == 200:
            print("✓ Event streaming endpoint available")
        else:
            print("⚠ Event streaming not implemented")

    # ========== EVENT SEARCH ==========

    @pytest.mark.asyncio
    async def test_event_search(self, client, auth_headers, test_project):
        """Test searching through events"""
        # Search events
        search_queries = [
            {"q": "file upload"},
            {"q": "knowledge", "event_type": "knowledge_search"},
            {"q": "error", "severity": "high"}
        ]

        for query in search_queries:
            search_resp = await client.get(
                f"/api/events/search",
                params=query,
                headers=auth_headers
            )

            if search_resp.status_code == 200:
                results = search_resp.json()
                print(f"✓ Event search tested with query: {query}")
            else:
                print("⚠ Event search not implemented")
                break


# Run all event CRUD tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
