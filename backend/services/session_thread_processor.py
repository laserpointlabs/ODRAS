"""
Session Thread Processor - Background service to process events and embed session threads

Processes events from Redis queues and embeds completed session threads for DAS intelligence.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from .config import Settings
from .session_thread_service import SessionThreadService
from .llm_team import LLMTeam

logger = logging.getLogger(__name__)


class SessionThreadProcessor:
    """
    Background processor for session thread events and embedding
    """

    def __init__(self, settings: Settings, redis_client, session_thread_service: SessionThreadService):
        self.settings = settings
        self.redis = redis_client
        self.session_thread_service = session_thread_service
        self.llm_team = LLMTeam(settings)
        self.processing = False

        # Configuration
        self.events_per_summary = 15  # Start with 15 events per summary
        self.summary_check_interval = 30  # Check for summarization every 30 seconds

    async def start_processing(self):
        """Start background processing of session events"""
        self.processing = True
        logger.info("Session thread processor started")

        # Start processing tasks
        tasks = [
            asyncio.create_task(self._process_api_events()),
            asyncio.create_task(self._process_session_events()),
            asyncio.create_task(self._process_semantic_events()),
            asyncio.create_task(self._check_for_summarization()),
            asyncio.create_task(self._embed_completed_threads())
        ]

        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Session thread processor error: {e}")
        finally:
            self.processing = False

    async def _process_api_events(self):
        """Process API events from middleware"""
        while self.processing:
            try:
                # Get API events from middleware
                event_data = await self.redis.brpop("api_events", timeout=1)

                if event_data:
                    event_json = event_data[1]
                    event = json.loads(event_json)

                    # Add to appropriate session thread
                    session_thread_id = event.get("session_thread_id")
                    if session_thread_id:
                        await self.session_thread_service.add_event_to_thread(
                            session_thread_id=session_thread_id,
                            event_type=event.get("event_type", "api_call"),
                            event_data=event.get("event_data", {})
                        )

                    logger.debug(f"Processed API event: {event.get('event_type')}")

            except Exception as e:
                logger.error(f"Error processing API events: {e}")
                await asyncio.sleep(1)

    async def _process_session_events(self):
        """Process session events (DAS interactions, etc.)"""
        while self.processing:
            try:
                # Get session events
                event_data = await self.redis.brpop("session_events", timeout=1)

                if event_data:
                    event_json = event_data[1]
                    event = json.loads(event_json)

                    # These are already processed by the session thread service
                    # Just log for monitoring
                    logger.debug(f"Session event processed: {event.get('event_type')}")

            except Exception as e:
                logger.error(f"Error processing session events: {e}")
                await asyncio.sleep(1)

    async def _check_for_summarization(self):
        """Check if any session threads need summarization"""
        while self.processing:
            try:
                # Check all active session threads
                session_keys = await self.redis.keys("session_thread:*")

                for key in session_keys:
                    session_data = await self.redis.get(key)
                    if session_data:
                        session = json.loads(session_data)

                        # Check if thread needs summarization
                        if await self._should_summarize_thread(session):
                            await self._summarize_thread_events(session)

                await asyncio.sleep(self.summary_check_interval)

            except Exception as e:
                logger.error(f"Error checking for summarization: {e}")
                await asyncio.sleep(30)

    async def _should_summarize_thread(self, session: Dict[str, Any]) -> bool:
        """Determine if a session thread should be summarized"""
        events = session.get("events", [])

        # Summarize if we have enough events
        if len(events) >= self.events_per_summary:
            return True

        # Summarize if thread has been inactive for a while
        if session.get("status") == "ended":
            return True

        return False

    async def _summarize_thread_events(self, session: Dict[str, Any]):
        """Summarize recent events in a session thread using LLM"""
        try:
            session_thread_id = session["session_thread_id"]
            events = session.get("events", [])

            if not events:
                return

            # Prepare events for LLM summarization
            events_text = self._format_events_for_llm(events)

            # Use LLM to create summary
            summary_prompt = f"""
Summarize this ODRAS work session activity:

User: {session.get('username')}
Session Goals: {session.get('session_goals', 'Not specified')}
Project: {session.get('project_id', 'Not specified')}

Events:
{events_text}

Create a concise summary of what the user accomplished in this session. Focus on:
1. Key actions taken (ontologies created, files uploaded, analyses run)
2. Progress toward session goals
3. Patterns or workflows followed
4. Any issues or successes

Keep summary under 200 words and make it searchable for future DAS queries.
"""

            # Generate summary using LLM team
            llm_response = await self.llm_team.analyze_requirement(
                requirement_text=summary_prompt,
                ontology_json_schema={"type": "object"},
                custom_personas=[{
                    "name": "Session Summarizer",
                    "system_prompt": "You are an expert at summarizing user work sessions. Create concise, searchable summaries.",
                    "is_active": True
                }]
            )

            if llm_response and "analysis" in llm_response:
                summary = llm_response["analysis"]

                # Add summary to session thread
                summary_event = {
                    "event_id": f"summary_{int(time.time())}",
                    "timestamp": datetime.now().isoformat(),
                    "event_type": "session_summary",
                    "event_data": {
                        "summary": summary,
                        "events_summarized": len(events),
                        "summary_method": "llm_generated"
                    }
                }

                # Update session with summary
                session["events"].append(summary_event)
                session["status"] = "summarized"

                # Update in Redis
                await self.redis.set(
                    f"session_thread:{session_thread_id}",
                    json.dumps(session),
                    ex=86400
                )

                # Queue for embedding
                await self.redis.lpush("threads_to_embed", session_thread_id)

                logger.info(f"Summarized session thread {session_thread_id} with {len(events)} events")

        except Exception as e:
            logger.error(f"Error summarizing thread events: {e}")

    def _format_events_for_llm(self, events: List[Dict[str, Any]]) -> str:
        """Format events for LLM summarization"""
        formatted_events = []

        for event in events[-self.events_per_summary:]:  # Last N events
            event_type = event.get("event_type", "unknown")
            event_data = event.get("event_data", {})
            timestamp = event.get("timestamp", "")

            if event_type == "user_message":
                formatted_events.append(f"[{timestamp}] User asked: {event_data.get('message', '')}")
            elif event_type == "das_response":
                formatted_events.append(f"[{timestamp}] DAS responded: {event_data.get('response', '')[:100]}...")
            elif event_type == "project_created":
                formatted_events.append(f"[{timestamp}] Created project: {event_data.get('name', 'unknown')}")
            elif event_type == "ontology_class_created":
                formatted_events.append(f"[{timestamp}] Created ontology class: {event_data.get('class_name', 'unknown')}")
            elif event_type == "file_uploaded":
                formatted_events.append(f"[{timestamp}] Uploaded file: {event_data.get('filename', 'unknown')}")
            else:
                formatted_events.append(f"[{timestamp}] {event_type}: {str(event_data)[:100]}")

        return "\n".join(formatted_events)

    async def _embed_completed_threads(self):
        """Embed completed session threads in vector collection"""
        while self.processing:
            try:
                # Get threads to embed
                thread_data = await self.redis.brpop("threads_to_embed", timeout=1)

                if thread_data:
                    session_thread_id = thread_data[1].decode('utf-8')

                    # Embed the thread
                    success = await self.session_thread_service.embed_session_thread(session_thread_id)

                    if success:
                        logger.info(f"Embedded session thread {session_thread_id}")
                    else:
                        logger.warning(f"Failed to embed session thread {session_thread_id}")

            except Exception as e:
                logger.error(f"Error embedding threads: {e}")
                await asyncio.sleep(1)

    def stop_processing(self):
        """Stop background processing"""
        self.processing = False
        logger.info("Session thread processor stopped")


    async def _process_semantic_events(self):
        """Process semantic events from middleware"""
        while self.processing:
            try:
                # Get semantic events from middleware
                event_data = await self.redis.brpop("semantic_events", timeout=1)

                if event_data:
                    event_json = event_data[1]
                    event = json.loads(event_json)

                    # Convert semantic event to session thread event
                    await self._process_semantic_event(event)
                    logger.debug(f"Processed semantic event: {event.get('semantic_action')}")

            except Exception as e:
                logger.error(f"Error processing semantic events: {e}")
                await asyncio.sleep(1)

    async def _process_semantic_event(self, event: Dict[str, Any]):
        """Convert semantic event to session thread event and store"""
        try:
            username = event.get("username")
            if not username:
                return

            # Get or create active session thread for this user
            session_thread_id = await self._get_or_create_user_session_thread(username)

            # Convert semantic event to session thread event
            thread_event = {
                "event_id": event.get("event_id"),
                "timestamp": event.get("timestamp"),
                "event_type": self._map_semantic_to_thread_event_type(event),
                "event_data": {
                    "semantic_action": event.get("semantic_action"),
                    "context": event.get("context", {}),
                    "metadata": event.get("metadata", {}),
                    "response_time": event.get("response_time"),
                    "success": event.get("success", True)
                }
            }

            # Add to session thread
            await self.session_thread_service.add_event_to_thread(
                session_thread_id=session_thread_id,
                event_type=thread_event["event_type"],
                event_data=thread_event["event_data"]
            )

            logger.debug(f"Added semantic event to session thread {session_thread_id}: {thread_event['event_type']}")

        except Exception as e:
            logger.error(f"Error processing semantic event: {e}")

    async def _get_or_create_user_session_thread(self, username: str) -> str:
        """Get or create active session thread for user"""
        try:
            # Check for active session thread in Redis
            active_session_key = f"active_session:{username}"
            session_thread_id = await self.redis.get(active_session_key)

            if session_thread_id:
                # Check if session thread still exists
                existing_thread = await self.session_thread_service.get_session_thread(session_thread_id.decode())
                if existing_thread:
                    return session_thread_id.decode()

            # Create new session thread
            new_thread = await self.session_thread_service.create_session_thread(
                username=username,
                session_goals="User work session"
            )

            # Store as active session
            await self.redis.set(active_session_key, new_thread.session_thread_id, ex=86400)  # 24 hours

            logger.info(f"Created new session thread {new_thread.session_thread_id} for user {username}")
            return new_thread.session_thread_id

        except Exception as e:
            logger.error(f"Error getting/creating session thread for {username}: {e}")
            # Fallback to a default session thread ID
            import time
            return f"session_{username}_{int(time.time())}"

    def _map_semantic_to_thread_event_type(self, event: Dict[str, Any]) -> str:
        """Map semantic event types to session thread event types"""
        metadata_type = event.get("metadata", {}).get("type", "")

        mapping = {
            "ontology_layout": "ontology_layout_modified",
            "ontology_save": "ontology_saved",
            "project_create": "project_created",
            "project_update": "project_updated",
            "file_upload": "file_uploaded",
            "file_delete": "file_deleted",
            "knowledge_search": "knowledge_searched",
            "knowledge_create": "knowledge_created",
            "workflow_start": "workflow_started",
            "das_chat": "das_interaction",
            "das_session_start": "das_session_started"
        }

        return mapping.get(metadata_type, "api_call")


# Global processor instance
thread_processor: Optional[SessionThreadProcessor] = None


async def start_session_thread_processor(settings: Settings, redis_client, session_thread_service):
    """Start the background session thread processor"""
    global thread_processor
    thread_processor = SessionThreadProcessor(settings, redis_client, session_thread_service)

    # Start processing in background
    asyncio.create_task(thread_processor.start_processing())
    logger.info("Session thread processor started in background")





