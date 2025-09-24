"""
DAS2 Core Engine - Simple Digital Assistant
NO complex intelligence layers, just:
1. Collect project_thread context
2. Collect RAG context
3. Send ALL to LLM with user question
4. Return response with sources
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

    def __init__(self, settings: Settings, rag_service: RAGService, project_manager: ProjectThreadManager):
        self.settings = settings
        self.rag_service = rag_service
        self.project_manager = project_manager

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

            # Project context
            context_sections.append("PROJECT CONTEXT:")
            context_sections.append(f"Project ID: {project_id}")
            context_sections.append(f"Workbench: {project_thread.current_workbench or 'unknown'}")
            if project_thread.project_goals:
                context_sections.append(f"Goals: {project_thread.project_goals}")
            if project_thread.active_ontologies:
                context_sections.append(f"Ontologies: {', '.join(project_thread.active_ontologies)}")
            context_sections.append("")

            # Project events
            if project_thread.project_events:
                context_sections.append("RECENT PROJECT ACTIVITY:")
                for event in project_thread.project_events[-5:]:  # Last 5
                    event_type = event.get("event_type", "")
                    summary = event.get("summary", "")
                    if event_type:
                        context_sections.append(f"{event_type}: {summary or 'No summary'}")
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

            prompt = f"""You are DAS, a digital assistant for this project. Answer using ALL provided context.

{full_context}

USER QUESTION: {message}

Answer naturally using any relevant context above. For "what did I ask" questions, use conversation history. For technical questions, use document knowledge. Be helpful and conversational."""

            print("DAS2_PROMPT:")
            print("="*50)
            print(prompt)
            print("="*50)

            # 5. Call LLM directly (simple HTTP call, not through LLMTeam)
            response_text = await self._call_llm_directly(prompt)

            print(f"DAS2_RESPONSE: {response_text}")

            # 6. Save conversation
            conversation_entry = {
                "timestamp": datetime.now().isoformat(),
                "user_message": message,
                "das_response": response_text
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

            # 8. Return with sources
            return DAS2Response(
                message=response_text,
                sources=rag_response.get("sources", []),
                metadata={
                    "chunks_found": rag_response.get("chunks_found", 0),
                    "confidence": "medium",
                    "project_id": project_id,
                    "project_thread_id": project_thread.project_thread_id
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
