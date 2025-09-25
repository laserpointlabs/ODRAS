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

    def __init__(self, settings: Settings, rag_service: RAGService, project_manager: ProjectThreadManager, db_service=None):
        self.settings = settings
        self.rag_service = rag_service
        self.project_manager = project_manager
        self.db_service = db_service

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

            # 1. Get project thread context
            if project_thread_id:
                project_thread = await self.project_manager.get_project_thread(project_thread_id)
            else:
                project_thread = await self.project_manager.get_project_thread_by_project_id(project_id)

            if not project_thread:
                return DAS2Response(
                    message="DAS2 is not available for this project. Project threads are created when projects are created.",
                    metadata={"error": "no_project_thread", "project_id": project_id}
                )

            print(f"DAS2_DEBUG: Found project thread {project_thread.project_thread_id}")

            # 2. Get RAG context (knowledge + sources)
            rag_response = await self.rag_service.query_knowledge_base(
                question=message,
                project_id=project_id,
                user_id=user_id,
                max_chunks=5,
                similarity_threshold=0.3,
                include_metadata=True,
                response_style="comprehensive"
            )

            print(f"DAS2_DEBUG: RAG returned {rag_response.get('chunks_found', 0)} chunks")

            # 3. Build COMPLETE context for LLM
            context_sections = []

            # Conversation history
            if project_thread.conversation_history:
                context_sections.append("CONVERSATION HISTORY:")
                for conv in project_thread.conversation_history[-10:]:  # Last 10
                    user_msg = conv.get("user_message", "")
                    das_resp = conv.get("das_response", "")
                    if user_msg:
                        context_sections.append(f"User: {user_msg}")
                    if das_resp:
                        context_sections.append(f"DAS: {das_resp}")
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

            context_sections.append(f"Workbench: {project_thread.current_workbench or 'unknown'}")
            if project_thread.project_goals:
                context_sections.append(f"Goals: {project_thread.project_goals}")
            if project_thread.active_ontologies:
                context_sections.append(f"Ontologies: {', '.join(project_thread.active_ontologies)}")
            context_sections.append("")

            # Project events (ALL context comes from here - no hard-coded calls)
            if project_thread.project_events:
                context_sections.append("RECENT PROJECT ACTIVITY:")
                for event in project_thread.project_events[-10:]:  # Last 10 events
                    event_type = event.get("event_type", "")
                    summary = event.get("summary", "")
                    semantic_summary = event.get("key_data", {}).get("semantic_summary", "")
                    event_timestamp = event.get("timestamp", "")

                    # Use rich summary from EventCapture2 if available (includes user attribution)
                    if semantic_summary:
                        # Add timestamp for context
                        if event_timestamp:
                            try:
                                from datetime import datetime
                                dt = datetime.fromisoformat(event_timestamp.replace('Z', '+00:00'))
                                time_str = dt.strftime("%H:%M")
                                context_sections.append(f"• [{time_str}] {semantic_summary}")
                            except:
                                context_sections.append(f"• {semantic_summary}")
                        else:
                            context_sections.append(f"• {semantic_summary}")
                    elif summary:
                        context_sections.append(f"• {event_type}: {summary}")
                    else:
                        context_sections.append(f"• {event_type}: event")
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
            print(f"Conversation History Entries: {len(project_thread.conversation_history)}")
            print(f"Project Events: {len(project_thread.project_events)}")
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
                    "conversation_length": len(project_thread.conversation_history),
                    "project_events_count": len(project_thread.project_events)
                }
            }
            project_thread.conversation_history.append(conversation_entry)
            await self.project_manager._persist_project_thread(project_thread)

            # 7. Capture event
            await self.project_manager.capture_project_event(
                project_id=project_id,
                project_thread_id=project_thread.project_thread_id,
                user_id=user_id,
                event_type=ProjectEventType.DAS_QUESTION,
                event_data={
                    "message": message,
                    "response": response_text[:100],
                    "sources_count": len(rag_response.get("sources", []))
                }
            )

            # 8. Return with sources (put sources in metadata for frontend compatibility)
            return DAS2Response(
                message=response_text,
                sources=rag_response.get("sources", []),
                metadata={
                    "chunks_found": rag_response.get("chunks_found", 0),
                    "confidence": "medium",
                    "project_id": project_id,
                    "project_thread_id": project_thread.project_thread_id,
                    "sources": rag_response.get("sources", [])  # Add sources here for frontend
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
