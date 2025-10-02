"""
DAS2 Core Engine - Simple Digital Assistant ✅ CURRENT ACTIVE VERSION

This is the CURRENT and RECOMMENDED DAS Core Engine implementation.
Use this for all new development and projects.

✅ Simple, clean architecture - NO complex intelligence layers
✅ Straightforward workflow:
   1. Collect project_thread context
   2. Collect RAG context
   3. Send ALL to LLM with user question
   4. Return response with sources

✅ Easy to debug and maintain
✅ Better performance than DAS1
✅ Direct context + LLM approach - no bullshit

⚠️ DO NOT USE DASCoreEngine (backend/services/das_core_engine.py) - it's deprecated
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .config import Settings
from .rag_service import RAGService
from .project_thread_manager import ProjectThreadManager, ProjectEventType

logger = logging.getLogger(__name__)


@dataclass
class DAS2Response:
    """Simple DAS2 response"""
    message: str
    sources: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.sources is None:
            self.sources = []
        if self.metadata is None:
            self.metadata = {}


class DAS2CoreEngine:
    """
    DAS2 - Dead Simple Digital Assistant

    Does exactly what you want:
    - Collects ALL context (project thread, RAG, conversation)
    - Builds ONE prompt with everything
    - Sends to LLM
    - Returns response with sources

    NO intelligence layers, NO complex logic, NO bullshit.
    """

    def __init__(self, settings: Settings, rag_service: RAGService, project_manager, db_service=None):
        self.settings = settings
        self.rag_service = rag_service
        self.project_manager = project_manager  # Now SqlFirstThreadManager
        self.db_service = db_service

        # Check if we're using SQL-first thread manager
        self.sql_first_threads = hasattr(project_manager, 'get_project_context')
        if self.sql_first_threads:
            logger.info("DAS2 initialized with SQL-first thread manager")
        else:
            logger.warning("DAS2 using legacy thread manager - consider upgrading")

        logger.info("DAS2 Core Engine initialized - SIMPLE APPROACH")

    async def process_message(
        self,
        project_id: str,
        message: str,
        user_id: str,
        project_thread_id: Optional[str] = None
    ) -> DAS2Response:
        """
        Process message with ALL context sent to LLM
        Simple and direct - no complex logic
        """
        try:
            print(f"DAS2_DEBUG: Starting process_message for project {project_id}")

            # 1. Get project thread context using SQL-first approach
            if self.sql_first_threads:
                # Use SQL-first thread manager
                project_context = await self.project_manager.get_project_context(project_id)
                if "error" in project_context:
                    return DAS2Response(
                        message="DAS2 is not available for this project. Project threads are created when projects are created.",
                        metadata={"error": "no_project_thread", "project_id": project_id}
                    )

                project_thread = project_context["project_thread"]
                conversation_history = project_context["conversation_history"]
                recent_events = project_context["recent_events"]

                print(f"DAS2_DEBUG: Found SQL-first project thread {project_thread['project_thread_id']}")
                print(f"DAS2_DEBUG: Loaded {len(conversation_history)} conversations, {len(recent_events)} events from SQL")
            else:
                # Legacy fallback (vector-based)
                if project_thread_id:
                    project_thread = await self.project_manager.get_project_thread(project_thread_id)
                else:
                    project_thread = await self.project_manager.get_project_thread_by_project_id(project_id)

                if not project_thread:
                    return DAS2Response(
                        message="DAS2 is not available for this project. Project threads are created when projects are created.",
                        metadata={"error": "no_project_thread", "project_id": project_id}
                    )

                conversation_history = getattr(project_thread, 'conversation_history', [])
                recent_events = getattr(project_thread, 'project_events', [])

                print(f"DAS2_DEBUG: Found legacy project thread {project_thread.project_thread_id}")

            # 2. Get RAG context (knowledge + sources) - DYNAMIC RAG MODE
            print(f"DAS2_DEBUG: Getting RAG configuration...")

            # Get the current RAG configuration from the database
            import httpx
            from datetime import datetime

            async with httpx.AsyncClient() as client:
                # First get an auth token
                auth_response = await client.post(
                    "http://localhost:8000/api/auth/login",
                    json={"username": "das_service", "password": "das_service_2024!"},
                    timeout=10.0
                )
                auth_data = auth_response.json()
                auth_token = auth_data.get("token")

                # Get RAG configuration
                rag_config_response = await client.get(
                    "http://localhost:8000/api/rag-config",
                    headers={"Authorization": f"Bearer {auth_token}"},
                    timeout=10.0
                )
                rag_config = rag_config_response.json()
                rag_implementation = rag_config.get("rag_implementation", "hardcoded")

                print(f"DAS2_DEBUG: RAG implementation: {rag_implementation}")
                print(f"🚀 DAS QUERY START: RAG Mode = {rag_implementation.upper()} | Project = {project_id} | User = {user_id}")

                if rag_implementation == "bpmn":
                    print(f"🔵 DAS RAG: Using BPMN WORKFLOW for question: '{message[:50]}{'...' if len(message) > 50 else ''}'")
                    # Use BPMN workflow
                    rag_response = await client.post(
                        "http://localhost:8000/api/knowledge/query-workflow",
                        headers={"Authorization": f"Bearer {auth_token}"},
                        json={
                            "question": message,
                            "project_id": project_id,
                            "response_style": "comprehensive"
                        },
                        timeout=30.0
                    )
                    print(f"🔵 DAS RAG: BPMN workflow completed with status: {rag_response.status_code}")
                    rag_response = rag_response.json()
                    print(f"🔵 DAS RAG: BPMN response - model_used: {rag_response.get('model_used', 'unknown')}, provider: {rag_response.get('provider', 'unknown')}")
                else:
                    print(f"🟡 DAS RAG: Using HARDCODED RAG for question: '{message[:50]}{'...' if len(message) > 50 else ''}'")
                    # Use hardcoded RAG
                    rag_response = await self.rag_service.query_knowledge_base(
                        question=message,
                        project_id=project_id,
                        user_id=user_id,
                        max_chunks=5,
                        similarity_threshold=0.3,
                        include_metadata=True,
                        response_style="comprehensive"
                    )
                    print(f"🟡 DAS RAG: Hardcoded RAG completed - chunks_found: {rag_response.get('chunks_found', 0)}")

            print(f"DAS2_DEBUG: RAG returned {rag_response.get('chunks_found', 0)} chunks")

            # 3. Build COMPLETE context for LLM
            context_sections = []

            # Conversation history (from SQL, not vectors)
            if conversation_history:
                context_sections.append("CONVERSATION HISTORY:")
                for conv in conversation_history[-10:]:  # Last 10 messages
                    role = conv.get("role", "")
                    content = conv.get("content", "")
                    if role and content:
                        if role == "user":
                            context_sections.append(f"User: {content}")
                        elif role == "assistant":
                            context_sections.append(f"DAS: {content}")
                        context_sections.append("")

            # Project context (including project name)
            context_sections.append("PROJECT CONTEXT:")

            # Get comprehensive project details
            project_details = None
            if self.db_service:
                try:
                    project_details = self.db_service.get_project_comprehensive(project_id)
                    print(f"DAS2_DEBUG: Retrieved comprehensive project details: {project_details}")
                except Exception as e:
                    logger.warning(f"Could not retrieve comprehensive project details for {project_id}: {e}")
                    print(f"DAS2_DEBUG: Comprehensive query failed: {e}")
                    # Fallback to basic project details
                    try:
                        project_details = self.db_service.get_project(project_id)
                        print(f"DAS2_DEBUG: Retrieved basic project details: {project_details}")
                    except Exception as e2:
                        logger.warning(f"Could not retrieve basic project details for {project_id}: {e2}")
                        print(f"DAS2_DEBUG: Basic query also failed: {e2}")
            else:
                print("DAS2_DEBUG: No db_service available!")

            if project_details:
                context_sections.append(f"Project: {project_details.get('name', 'Unknown')} (ID: {project_id})")

                if project_details.get('description'):
                    context_sections.append(f"Description: {project_details.get('description')}")

                if project_details.get('domain'):
                    context_sections.append(f"Domain: {project_details.get('domain')}")

                # Creator information
                if project_details.get('created_by_username'):
                    creator_name = project_details.get('created_by_username')
                    context_sections.append(f"Created by: {creator_name}")

                # Timestamps
                if project_details.get('created_at'):
                    context_sections.append(f"Created: {project_details.get('created_at')}")
                if project_details.get('updated_at'):
                    context_sections.append(f"Last updated: {project_details.get('updated_at')}")

                # Namespace information
                if project_details.get('namespace_name'):
                    context_sections.append(f"Namespace: {project_details.get('namespace_name')} ({project_details.get('namespace_path', 'N/A')})")
                    if project_details.get('namespace_description'):
                        context_sections.append(f"Namespace description: {project_details.get('namespace_description')}")
                    if project_details.get('namespace_status'):
                        context_sections.append(f"Namespace status: {project_details.get('namespace_status')}")

                # Project URI
                if project_details.get('project_uri'):
                    context_sections.append(f"Project URI: {project_details.get('project_uri')}")
            else:
                context_sections.append(f"Project ID: {project_id} (details unavailable)")

            # Project thread metadata (SQL-first)
            if self.sql_first_threads:
                context_sections.append(f"Workbench: {project_thread.get('current_workbench', 'unknown')}")
                if project_thread.get('goals'):
                    context_sections.append(f"Goals: {project_thread['goals']}")
                context_sections.append("")

                # Project events from SQL (not vectors)
                if recent_events:
                    context_sections.append("RECENT PROJECT ACTIVITY:")
                    for event in recent_events[-10:]:  # Last 10 events from SQL
                        event_type = event.get("event_type", "")
                        semantic_summary = event.get("semantic_summary", "")
                        event_data = event.get("event_data", {})
                        created_at = event.get("created_at", "")

                        # Use semantic summary if available, otherwise build from event data
                        if semantic_summary:
                            # Add timestamp for context
                            if created_at:
                                try:
                                    from datetime import datetime
                                    if isinstance(created_at, str):
                                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                                    else:
                                        dt = created_at
                                    time_str = dt.strftime("%H:%M")
                                    context_sections.append(f"• [{time_str}] {semantic_summary}")
                                except:
                                    context_sections.append(f"• {semantic_summary}")
                            else:
                                context_sections.append(f"• {semantic_summary}")
                        else:
                            # Build summary from event data
                            action = event_data.get("semantic_action", event_data.get("action", event_type))
                            context_sections.append(f"• {event_type}: {action}")
                    context_sections.append("")
                else:
                    context_sections.append("RECENT PROJECT ACTIVITY:")
                    context_sections.append("• No project events captured yet")
                    context_sections.append("")
            else:
                # Legacy vector-based approach
                context_sections.append(f"Workbench: {getattr(project_thread, 'current_workbench', 'unknown')}")
                if hasattr(project_thread, 'project_goals') and project_thread.project_goals:
                    context_sections.append(f"Goals: {project_thread.project_goals}")
                if hasattr(project_thread, 'active_ontologies') and project_thread.active_ontologies:
                    context_sections.append(f"Ontologies: {', '.join(project_thread.active_ontologies)}")
                context_sections.append("")

                # Legacy project events from vectors
                project_events = getattr(project_thread, 'project_events', [])
                if project_events:
                    context_sections.append("RECENT PROJECT ACTIVITY:")
                    for event in project_events[-10:]:  # Last 10 events
                        event_type = event.get("event_type", "")
                        summary = event.get("summary", "")
                        context_sections.append(f"• {event_type}: {summary}")
                    context_sections.append("")
                else:
                    context_sections.append("RECENT PROJECT ACTIVITY:")
                    context_sections.append("• No project events captured yet")
                    context_sections.append("")

            # Knowledge/RAG context
            if rag_response.get("success") and rag_response.get("chunks_found", 0) > 0:
                context_sections.append("KNOWLEDGE FROM DOCUMENTS:")
                context_sections.append(rag_response.get("response", ""))

                sources = rag_response.get("sources", [])
                if sources:
                    context_sections.append("Sources:")
                    for i, source in enumerate(sources, 1):
                        title = source.get("title", "Unknown")
                        doc_type = source.get("document_type", "document")
                        context_sections.append(f"{i}. {title} ({doc_type})")
                context_sections.append("")

            # 4. Build final prompt with EVERYTHING
            full_context = "\n".join(context_sections)

            print(f"\n🔍 DAS2 CONTEXT SECTIONS BUILT:")
            print(f"Total sections: {len(context_sections)}")
            for i, section in enumerate(context_sections[:10]):  # Show first 10 lines
                print(f"  {i+1}: {section[:100]}{'...' if len(section) > 100 else ''}")

            prompt = f"""You are DAS, a digital assistant for this project. Answer using ALL provided context.

IMPORTANT: Always prioritize CURRENT PROJECT CONTEXT over conversation history. If there are conflicts between conversation history and current project facts, use the current project facts.

{full_context}

USER QUESTION: {message}

Answer naturally using the context above. PRIORITY ORDER:
1. CURRENT PROJECT CONTEXT (always authoritative)
2. KNOWLEDGE FROM DOCUMENTS (factual information)
3. CONVERSATION HISTORY (for reference only, may contain outdated info)

Be helpful and conversational."""

            print("\n" + "="*80)
            print("🤖 DAS2 PROMPT TO LLM")
            print("="*80)
            print(f"Project ID: {project_id}")
            print(f"User Message: {message}")
            print(f"RAG Chunks Found: {rag_response.get('chunks_found', 0)}")
            # Use SQL-first data for debug output
            if self.sql_first_threads:
                print(f"Conversation History Entries: {len(conversation_history)}")
                print(f"Project Events: {len(recent_events)}")
            else:
                print(f"Conversation History Entries: {len(getattr(project_thread, 'conversation_history', []))}")
                print(f"Project Events: {len(getattr(project_thread, 'project_events', []))}")
            print("-"*80)
            print("FULL PROMPT:")
            print("-"*80)
            print(prompt)
            print("="*80)

            # 5. Call LLM directly (simple HTTP call, not through LLMTeam)
            response_text = await self._call_llm_directly(prompt)

            print("\n" + "="*80)
            print("🤖 DAS2 LLM RESPONSE")
            print("="*80)
            print(response_text)
            print("="*80 + "\n")

            # 6. Save conversation with complete context for debugging
            conversation_entry = {
                "timestamp": datetime.now().isoformat(),
                "user_message": message,
                "das_response": response_text,
                "prompt_context": prompt,  # Full prompt sent to LLM for debugging
                "rag_context": {
                    "chunks_found": rag_response.get("chunks_found", 0),
                    "sources": rag_response.get("sources", []),
                    "success": rag_response.get("success", False)
                },
                "project_context": {
                    "project_id": project_id,
                    "project_name": project_details.get('name') if project_details else None,
                    "has_comprehensive_details": project_details is not None
                },
                "thread_metadata": {
                    "conversation_length": len(conversation_history) if self.sql_first_threads else len(getattr(project_thread, 'conversation_history', [])),
                    "project_events_count": len(recent_events) if self.sql_first_threads else len(getattr(project_thread, 'project_events', []))
                }
            }
            # Store conversation entry (SQL-first handles this automatically)
            if not self.sql_first_threads:
                # Only needed for legacy system
                project_thread.conversation_history.append(conversation_entry)
                await self.project_manager._persist_project_thread(project_thread)
            else:
                # SQL-first already stored the conversation in store_conversation_message above
                logger.debug("Conversation already stored in SQL-first approach")

            # 7. Capture event
            if self.sql_first_threads:
                project_thread_id = project_thread.get('project_thread_id')
            else:
                project_thread_id = getattr(project_thread, 'project_thread_id', None)

            if project_thread_id and self.sql_first_threads:
                await self.project_manager.capture_event(
                    project_thread_id=project_thread_id,
                    project_id=project_id,
                    user_id=user_id,
                    event_type="das_question",  # String instead of enum for SQL-first
                    event_data={
                        "message": message,
                        "response": response_text[:100],
                        "sources_count": len(rag_response.get("sources", []))
                    }
                )

            # 8. Store conversation with rich debugging context (SQL-first)
            if self.sql_first_threads:
                try:
                    project_thread_id = project_thread.get('project_thread_id')
                    print(f"💾 DAS2_DEBUG: Starting conversation storage...")
                    print(f"   Thread ID: {project_thread_id}")
                    print(f"   User message length: {len(message)}")
                    print(f"   Assistant response length: {len(response_text)}")
                    print(f"   Prompt length: {len(prompt)}")

                    if project_thread_id:
                        # Prepare rich context for Thread Manager workbench
                        rag_context = {
                            "chunks_found": rag_response.get("chunks_found", 0),
                            "sources": rag_response.get("sources", []),
                            "model_used": rag_response.get("model_used", "unknown"),
                            "provider": rag_response.get("provider", "unknown"),
                            "success": rag_response.get("success", False)
                        }

                        project_context = {
                            "project_id": project_id,
                            "project_name": project_details.get('name') if project_details else None,
                            "domain": project_details.get('domain') if project_details else None,
                            "workbench": project_thread.get('current_workbench', 'unknown')
                        }

                        thread_metadata = {
                            "conversation_length": len(conversation_history),
                            "project_events_count": len(recent_events),
                            "sql_first": True,
                            "das_engine": "DAS2"
                        }

                        print(f"💾 DAS2_DEBUG: Storing USER message...")
                        # Store user message with rich metadata
                        user_msg_id = await self.project_manager.store_conversation_message(
                            project_thread_id=project_thread_id,
                            role="user",
                            content=message,
                            metadata={
                                "das_engine": "DAS2",
                                "timestamp": datetime.now().isoformat(),
                                "project_context": project_context,
                                "thread_metadata": thread_metadata
                            }
                        )
                        print(f"💾 DAS2_DEBUG: Stored USER message: {user_msg_id[:8]}...")

                        print(f"💾 DAS2_DEBUG: Storing ASSISTANT message...")
                        print(f"   Response text: {response_text[:100]}...")
                        print(f"   Prompt context length: {len(prompt)}")

                        # Store assistant response with complete debugging context
                        assistant_msg_id = await self.project_manager.store_conversation_message(
                            project_thread_id=project_thread_id,
                            role="assistant",
                            content=response_text,
                            metadata={
                                "das_engine": "DAS2",
                                "timestamp": datetime.now().isoformat(),
                                "prompt_context": prompt,  # FULL PROMPT for debugging
                                "rag_context": rag_context,
                                "project_context": project_context,
                                "thread_metadata": thread_metadata,
                                "processing_time": 0.0  # Will be calculated properly later
                            }
                        )
                        print(f"💾 DAS2_DEBUG: Stored ASSISTANT message: {assistant_msg_id[:8]}...")

                        print(f"💾 DAS2_DEBUG: Conversation storage COMPLETE")
                        print(f"   User: {user_msg_id[:8]}...")
                        print(f"   Assistant: {assistant_msg_id[:8]}...")
                        print(f"   Thread: {project_thread_id[:8]}...")

                    else:
                        print(f"❌ DAS2_DEBUG: No project_thread_id for storage!")

                except Exception as e:
                    print(f"❌ DAS2_DEBUG: Conversation storage FAILED: {e}")
                    logger.warning(f"Failed to store DAS2 conversation in SQL: {e}")
                    import traceback
                    traceback.print_exc()

            # 9. Return with sources (put sources in metadata for frontend compatibility)
            return DAS2Response(
                message=response_text,
                sources=rag_response.get("sources", []),
                metadata={
                    "chunks_found": rag_response.get("chunks_found", 0),
                    "confidence": "medium",
                    "project_id": project_id,
                    "project_thread_id": project_thread.get('project_thread_id') if self.sql_first_threads else getattr(project_thread, 'project_thread_id', 'unknown'),
                    "sources": rag_response.get("sources", []),  # Add sources here for frontend
                    "sql_first": self.sql_first_threads
                }
            )

        except Exception as e:
            logger.error(f"DAS2 error: {e}")
            return DAS2Response(
                message=f"Sorry, I encountered an error: {str(e)}",
                metadata={"error": str(e)}
            )

    async def _call_llm_directly(self, prompt: str) -> str:
        """Call LLM directly via HTTP - no complex infrastructure"""
        try:
            import httpx

            # Determine LLM URL based on provider (same logic as LLMTeam)
            if self.settings.llm_provider == "ollama":
                base_url = self.settings.ollama_url.rstrip("/")
                llm_url = f"{base_url}/v1/chat/completions"
            else:  # openai
                llm_url = "https://api.openai.com/v1/chat/completions"

            payload = {
                "model": self.settings.llm_model,
                "messages": [
                    {"role": "system", "content": "You are DAS, a helpful digital assistant."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }

            headers = {"Content-Type": "application/json"}
            if hasattr(self.settings, 'openai_api_key') and self.settings.openai_api_key:
                headers["Authorization"] = f"Bearer {self.settings.openai_api_key}"

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(llm_url, json=payload, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    logger.error(f"LLM call failed: {response.status_code} - {response.text}")
                    return "I couldn't generate a response due to an LLM error."

        except Exception as e:
            logger.error(f"Direct LLM call failed: {e}")
            return f"I couldn't call the LLM: {str(e)}"
