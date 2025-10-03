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

    def _serialize_project_details(self, project_details):
        """Convert project details to JSON-serializable format"""
        if not project_details:
            return None

        serialized = {}
        for key, value in project_details.items():
            if hasattr(value, 'isoformat'):  # datetime object
                serialized[key] = value.isoformat()
            else:
                serialized[key] = value
        return serialized

    def _build_context_aware_query(self, message: str, conversation_history: List[Dict]) -> str:
        """
        Build context-aware RAG query for consistency and better results

        Based on RAG best practices from:
        - Microsoft Advanced RAG Systems
        - RAG Advanced Techniques research
        """
        # Extract entities from recent conversation for context carryover
        entities_mentioned = set()
        recent_context = []

        if conversation_history:
            # Look at last 3 conversation pairs for context
            for conv in conversation_history[-3:]:
                user_msg = conv.get("user_message", "")
                das_response = conv.get("das_response", "")

                # Extract key entities (UAV names, specifications, etc.)
                for text in [user_msg, das_response]:
                    text_lower = text.lower()
                    if "quadcopter" in text_lower or "t4" in text_lower:
                        entities_mentioned.add("QuadCopter T4")
                    if "trivector" in text_lower or "vtol" in text_lower:
                        entities_mentioned.add("TriVector VTOL")
                    if "aeromapper" in text_lower or "x8" in text_lower:
                        entities_mentioned.add("AeroMapper X8")
                    if "skyeagle" in text_lower or "x500" in text_lower:
                        entities_mentioned.add("SkyEagle X500")

                # Build recent context summary
                if user_msg:
                    recent_context.append(f"Previous: {user_msg[:100]}")

        # Handle pronoun resolution
        message_lower = message.lower()
        enhanced_query = message

        if any(pronoun in message_lower for pronoun in ["its", "it", "that", "this"]):
            if entities_mentioned:
                # Add context for pronoun resolution
                entity_context = ", ".join(entities_mentioned)
                enhanced_query = f"{message} (referring to: {entity_context})"
            else:
                # If no clear context, add clarification request
                enhanced_query = f"{message} (context unclear - need specific entity)"

        # Handle comprehensive queries (tables, lists, summaries)
        if any(keyword in message_lower for keyword in ["table", "list", "all", "summary", "specifications"]):
            enhanced_query = f"COMPREHENSIVE: {message} (include all relevant information, not just top matches)"

        # Handle specific information requests (weight, specs, capacity, etc.)
        elif any(keyword in message_lower for keyword in ["weight", "capacity", "speed", "wingspan", "specifications", "specs"]):
            # Make specific queries more comprehensive to find detailed information
            enhanced_query = f"DETAILED: {message} (find specific technical information and specifications)"

        # Add recent conversation context ONLY for pronoun resolution, not general queries
        if any(pronoun in message_lower for pronoun in ["its", "it", "that", "this"]) and recent_context:
            context_summary = " | ".join(recent_context[-1:])  # Only last context item for pronouns
            enhanced_query = f"{enhanced_query} | Recent context: {context_summary}"

        return enhanced_query

    async def process_message_stream(
        self,
        project_id: str,
        message: str,
        user_id: str,
        project_thread_id: Optional[str] = None
    ):
        """
        Process message with streaming response
        Simple streaming implementation that stores both user and assistant messages
        """
        try:
            print(f"🚀 DAS2_STREAM_DEBUG: Starting streaming process_message for project {project_id}")
            logger.info(f"🚀 DAS2_STREAM_DEBUG: Starting streaming process_message for project {project_id}")

            # 1. Get project thread context (same as regular process_message)
            if self.sql_first_threads:
                project_context = await self.project_manager.get_project_context(project_id)
                if "error" in project_context:
                    yield {"type": "error", "message": "DAS2 is not available for this project. Project threads are created when projects are created."}
                    return

                project_thread = project_context["project_thread"]
                conversation_history = project_context["conversation_history"]
                recent_events = project_context["recent_events"]
                project_metadata = project_context.get("project_metadata", {})
            else:
                if project_thread_id:
                    project_thread = await self.project_manager.get_project_thread(project_thread_id)
                else:
                    project_thread = await self.project_manager.get_project_thread_by_project_id(project_id)

                if not project_thread:
                    yield {"type": "error", "message": "DAS2 is not available for this project. Project threads are created when projects are created."}
                    return

                conversation_history = getattr(project_thread, 'conversation_history', [])
                recent_events = getattr(project_thread, 'project_events', [])

            # 2. Store user message immediately
            if self.sql_first_threads:
                project_thread_id = project_thread.get('project_thread_id')
                if project_thread_id:
                    await self.project_manager.store_conversation_message(
                        project_thread_id=project_thread_id,
                        role="user",
                        content=message,
                        metadata={"das_engine": "DAS2", "timestamp": datetime.now().isoformat()}
                    )

            # 3. Get RAG context using current user's credentials for proper access
            import httpx
            async with httpx.AsyncClient() as client:
                # Use a service account token for RAG queries to ensure consistent access
                # TODO: This should be replaced with proper service-to-service auth
                auth_response = await client.post(
                    "http://localhost:8000/api/auth/login",
                    json={"username": "das_service", "password": "das_service_2024!"},
                    timeout=10.0
                )
                auth_data = auth_response.json()
                auth_token = auth_data.get("token")

                rag_config_response = await client.get(
                    "http://localhost:8000/api/rag-config",
                    headers={"Authorization": f"Bearer {auth_token}"},
                    timeout=10.0
                )
                rag_config = rag_config_response.json()
                rag_implementation = rag_config.get("rag_implementation", "hardcoded")

                # Enhanced RAG query with conversation context for consistency
                enhanced_query = self._build_context_aware_query(message, conversation_history)

                if rag_implementation == "bpmn":
                    rag_response = await client.post(
                        "http://localhost:8000/api/knowledge/query-workflow",
                        headers={"Authorization": f"Bearer {auth_token}"},
                        json={
                            "question": enhanced_query,
                            "project_id": project_id,
                            "response_style": "comprehensive"
                        },
                        timeout=30.0
                    )
                    rag_response = rag_response.json()
                else:
                    # Simple approach: Give LLM lots of context and let it decide
                    # Modern best practice with large context window models
                    if "DETAILED:" in enhanced_query or "COMPREHENSIVE:" in enhanced_query:
                        # For specific or comprehensive queries, provide maximum context
                        max_chunks = 20
                        threshold = 0.1  # Very low threshold for maximum coverage
                    else:
                        # Default: Still provide substantial context
                        max_chunks = 15
                        threshold = 0.2

                    rag_response = await self.rag_service.query_knowledge_base(
                        question=enhanced_query,
                        project_id=project_id,
                        user_id=user_id,
                        max_chunks=max_chunks,
                        similarity_threshold=threshold,
                        include_metadata=True,
                        response_style="comprehensive"
                    )

            # 3.5. Debug RAG response processing
            print(f"🔍 RAG_DEBUG_STREAM: Processing RAG response...")
            print(f"   Success: {rag_response.get('success', False)}")
            print(f"   Chunks found: {rag_response.get('chunks_found', 0)}")
            print(f"   Sources: {len(rag_response.get('sources', []))}")

            if rag_response.get("success") and rag_response.get("chunks_found", 0) > 0:
                rag_content = rag_response.get("response", "")
                print(f"🔍 RAG_DEBUG_STREAM: RAG content length: {len(rag_content)}")
                print(f"🔍 RAG_DEBUG_STREAM: RAG content preview: {rag_content[:300]}...")

                # Debug sources
                sources = rag_response.get("sources", [])
                for i, source in enumerate(sources):
                    print(f"   Source {i+1}: {source.get('title', 'Unknown')} ({source.get('document_type', 'document')}) - {source.get('relevance_score', 0):.3f}")

                # Check if specific content is in RAG response
                if "aeromapper" in rag_content.lower():
                    print(f"✅ RAG_DEBUG_STREAM: AeroMapper mentioned in RAG content")
                    if "20" in rag_content and "kg" in rag_content.lower():
                        print(f"✅ RAG_DEBUG_STREAM: AeroMapper weight (20 kg) found in RAG content")
                else:
                    print(f"❌ RAG_DEBUG_STREAM: AeroMapper NOT mentioned in RAG content")
            else:
                print(f"❌ RAG_DEBUG_STREAM: No RAG content - success: {rag_response.get('success')}, chunks: {rag_response.get('chunks_found', 0)}")

            # 4. Build context and call LLM with streaming
            context_sections = []

            # Add conversation history
            if conversation_history:
                context_sections.append("CONVERSATION HISTORY:")

                # Handle SQL-first formatted conversations (user_message/das_response pairs)
                if self.sql_first_threads and conversation_history and isinstance(conversation_history[0], dict) and 'user_message' in conversation_history[0]:
                    print(f"🔍 DAS2_STREAM_CONTEXT: Processing {len(conversation_history)} SQL-first conversation pairs")
                    for conv in conversation_history[-5:]:  # Last 5 conversation pairs
                        user_msg = conv.get("user_message", "")
                        das_response = conv.get("das_response", "")
                        if user_msg:
                            context_sections.append(f"User: {user_msg}")
                        if das_response:
                            context_sections.append(f"DAS: {das_response}")
                        context_sections.append("")
                else:
                    # Handle legacy format (individual role/content messages)
                    print(f"🔍 DAS2_STREAM_CONTEXT: Processing {len(conversation_history)} legacy conversation messages")
                    for conv in conversation_history[-10:]:
                        role = conv.get("role", "")
                        content = conv.get("content", "")
                        if role and content:
                            if role == "user":
                                context_sections.append(f"User: {content}")
                            elif role == "assistant":
                                context_sections.append(f"DAS: {content}")
                            context_sections.append("")

            # Add project context
            context_sections.append("PROJECT CONTEXT:")

            # Get comprehensive project details (same as non-streaming method)
            project_details = None
            if hasattr(self, 'db_service') and self.db_service:
                try:
                    project_details = self.db_service.get_project_comprehensive(project_id)
                    print(f"DAS2_STREAM_DEBUG: Retrieved project details: {bool(project_details)}")
                except Exception as e:
                    print(f"DAS2_STREAM_DEBUG: Failed to get project details: {e}")
            elif hasattr(self.project_manager, 'db_service') and self.project_manager.db_service:
                try:
                    project_details = self.project_manager.db_service.get_project_comprehensive(project_id)
                    print(f"DAS2_STREAM_DEBUG: Retrieved project details via project_manager: {bool(project_details)}")
                except Exception as e:
                    print(f"DAS2_STREAM_DEBUG: Failed to get project details via project_manager: {e}")
            else:
                print("DAS2_STREAM_DEBUG: No db_service available!")

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

            # Add comprehensive project metadata (streaming method)
            if project_metadata:
                # Files in project
                files = project_metadata.get('files', [])
                if files:
                    context_sections.append("PROJECT FILES:")
                    for file_info in files:
                        title = file_info.get('title', 'Unknown')
                        doc_type = file_info.get('document_type', 'document')
                        filename = file_info.get('filename', 'unknown')
                        context_sections.append(f"• {title} ({doc_type}) - {filename}")

                # Ontologies in project
                ontologies = project_metadata.get('ontologies', [])
                if ontologies:
                    context_sections.append("PROJECT ONTOLOGIES:")
                    for onto_info in ontologies:
                        label = onto_info.get('label', 'Unknown')
                        role = onto_info.get('role', 'unknown')
                        is_ref = " (reference)" if onto_info.get('is_reference') else ""
                        context_sections.append(f"• {label} ({role}){is_ref}")

                # Ontology classes
                classes = project_metadata.get('classes', [])
                if classes:
                    context_sections.append("ONTOLOGY CLASSES:")
                    for class_info in classes:
                        class_name = class_info.get('class_name', 'Unknown')
                        ontology = class_info.get('ontology', 'Unknown')
                        context_sections.append(f"• {class_name} (in {ontology})")

                context_sections.append("")

            # Add ALL project events - no filtering, no smart logic
            if recent_events:
                context_sections.append("RECENT PROJECT ACTIVITY:")
                for event in recent_events:  # ALL events
                    event_type = event.get("event_type", "")
                    semantic_summary = event.get("semantic_summary", "")
                    if semantic_summary:
                        context_sections.append(f"• {semantic_summary}")
                    else:
                        context_sections.append(f"• {event_type}")
                context_sections.append("")

            # Add RAG context with detailed debugging
            print(f"🔍 RAG_DEBUG: Processing RAG response...")
            print(f"   Success: {rag_response.get('success', False)}")
            print(f"   Chunks found: {rag_response.get('chunks_found', 0)}")
            print(f"   Sources: {len(rag_response.get('sources', []))}")

            if rag_response.get("success") and rag_response.get("chunks_found", 0) > 0:
                context_sections.append("KNOWLEDGE FROM DOCUMENTS:")
                rag_content = rag_response.get("response", "")
                context_sections.append(rag_content)

                # Debug what content is being provided to LLM
                print(f"🔍 RAG_DEBUG: RAG content length: {len(rag_content)}")
                print(f"🔍 RAG_DEBUG: RAG content preview: {rag_content[:200]}...")

                # Debug sources
                sources = rag_response.get("sources", [])
                for i, source in enumerate(sources):
                    print(f"   Source {i+1}: {source.get('title', 'Unknown')} ({source.get('document_type', 'document')}) - {source.get('relevance_score', 0):.3f}")

                # Check if AeroMapper is mentioned in the RAG content
                if "aeromapper" in rag_content.lower():
                    print(f"✅ RAG_DEBUG: AeroMapper mentioned in RAG content")
                else:
                    print(f"❌ RAG_DEBUG: AeroMapper NOT mentioned in RAG content")

                if "20" in rag_content and "kg" in rag_content.lower():
                    print(f"✅ RAG_DEBUG: Weight information (20 kg) found in RAG content")
                else:
                    print(f"❌ RAG_DEBUG: Weight information NOT found in RAG content")
            else:
                print(f"❌ RAG_DEBUG: No RAG content available - success: {rag_response.get('success')}, chunks: {rag_response.get('chunks_found', 0)}")

            full_context = "\n".join(context_sections)

            # VALIDATE CONTEXT BEFORE SENDING TO LLM
            print("🔍 CONTEXT_VALIDATION:")
            print(f"   Total context sections: {len(context_sections)}")
            print(f"   Total context length: {len(full_context)}")
            print(f"   Contains 'PROJECT FILES': {'PROJECT FILES' in full_context}")
            print(f"   Contains 'PROJECT ONTOLOGIES': {'PROJECT ONTOLOGIES' in full_context}")
            print(f"   Contains 'ONTOLOGY CLASSES': {'ONTOLOGY CLASSES' in full_context}")
            print(f"   Contains 'RECENT PROJECT ACTIVITY': {'RECENT PROJECT ACTIVITY' in full_context}")
            print(f"   Contains 'file_uploaded': {'file_uploaded' in full_context}")
            print(f"   Contains 'ontology_created': {'ontology_created' in full_context}")
            print(f"   Contains 'Class1': {'Class1' in full_context}")
            print(f"   Contains 'Class2': {'Class2' in full_context}")
            print("🔍 FULL CONTEXT BEING SENT TO LLM:")
            print("="*120)
            print(full_context)
            print("="*120)

            prompt = f"""You are DAS, a digital assistant for this project. Answer using ALL provided context.

IMPORTANT INSTRUCTIONS:
1. ALWAYS use the provided context as the authoritative source
2. If information is in the context, state it confidently
3. If information is NOT in the context, clearly say "I don't have that information in the current knowledge base"
4. For ambiguous pronouns (it, its, that) without clear context, ask for clarification: "Which [entity] are you referring to?"
5. For comprehensive queries (tables, lists), include ALL relevant information from context
6. For questions outside this project's domain, politely redirect: "I focus on this project's knowledge. For [topic], I'd recommend consulting relevant resources."
7. NEVER contradict previous responses - be consistent
8. When context is unclear or missing, ask specific clarifying questions rather than guessing

CONTEXT ANALYSIS:
- If the user asks about "it" or "its" and no clear entity was recently mentioned, ask for clarification
- If the user asks about topics not in the project context (like general knowledge), redirect to project focus
- If the context contains partial information, provide what's available and indicate what's missing

{full_context}

USER QUESTION: {message}

Answer naturally and consistently using the context above. Be helpful and conversational."""

            # 5. Stream LLM response and accumulate for storage
            full_response_content = ""
            async for chunk in self._call_llm_streaming(prompt):
                full_response_content += chunk  # Accumulate chunks
                yield {"type": "content", "content": chunk}

            # 6. Store assistant response (using accumulated content)
            if self.sql_first_threads and project_thread_id:
                await self.project_manager.store_conversation_message(
                    project_thread_id=project_thread_id,
                    role="assistant",
                    content=full_response_content,  # Use accumulated content
                    metadata={
                        "das_engine": "DAS2",
                        "timestamp": datetime.now().isoformat(),
                        "prompt_context": full_context,  # Store the full prompt for thread manager
                        "rag_context": {
                            "chunks_found": rag_response.get("chunks_found", 0),
                            "sources": rag_response.get("sources", [])
                        },
                        "project_context": {
                            "project_id": project_id,
                            "project_details": self._serialize_project_details(project_details)
                        },
                        "thread_metadata": {
                            "sql_first": True,
                            "conversation_pairs": len(conversation_history) if conversation_history else 0
                        }
                    }
                )

            # 7. Send completion signal with comprehensive debug metadata
            debug_metadata = {
                "rag_debug": {
                    "enhanced_query": enhanced_query,
                    "rag_success": rag_response.get("success", False),
                    "chunks_found": rag_response.get("chunks_found", 0),
                    "sources_count": len(rag_response.get("sources", [])),
                    "rag_content_length": len(rag_response.get("response", "")),
                    "rag_content_preview": rag_response.get("response", "")[:200] + "..." if len(rag_response.get("response", "")) > 200 else rag_response.get("response", ""),
                    "contains_aeromapper": "aeromapper" in rag_response.get("response", "").lower(),
                    "contains_weight_info": "20" in rag_response.get("response", "") and "kg" in rag_response.get("response", "").lower()
                },
                "context_debug": {
                    "conversation_pairs": len(conversation_history) if conversation_history else 0,
                    "project_details_available": project_details is not None,
                    "context_sections_count": len(context_sections),
                    "total_context_length": len(full_context)
                }
            }

            yield {
                "type": "done",
                "metadata": {
                    "sources": rag_response.get("sources", []),
                    "chunks_found": rag_response.get("chunks_found", 0),
                    "debug": debug_metadata  # Add comprehensive debug info
                }
            }

        except Exception as e:
            logger.error(f"DAS2 stream error: {e}")
            yield {"type": "error", "message": str(e)}

    async def _call_llm_streaming(self, prompt: str):
        """Call LLM with streaming response"""
        try:
            import httpx

            # Determine LLM URL based on provider
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
                "max_tokens": 1000,
                "stream": True
            }

            headers = {"Content-Type": "application/json"}
            if hasattr(self.settings, 'openai_api_key') and self.settings.openai_api_key:
                headers["Authorization"] = f"Bearer {self.settings.openai_api_key}"

            async with httpx.AsyncClient(timeout=120) as client:  # Increased timeout for OpenAI API
                async with client.stream("POST", llm_url, json=payload, headers=headers) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                try:
                                    data = json.loads(line[6:])
                                    if "choices" in data and len(data["choices"]) > 0:
                                        delta = data["choices"][0].get("delta", {})
                                        if "content" in delta:
                                            yield delta["content"]
                                except json.JSONDecodeError:
                                    continue
                    else:
                        yield f"Error: LLM call failed with status {response.status_code}"

        except Exception as e:
            logger.error(f"LLM streaming call failed: {e}")
            yield f"Error: {str(e)}"
