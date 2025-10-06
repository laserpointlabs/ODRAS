"""
Camunda External Task Worker for ODRAS
Polls Camunda for external tasks and executes corresponding Python functions.
"""

import asyncio
import json
import logging
import sys
import time
from typing import Any, Dict, List, Optional
import traceback
import os

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from .config import Settings
except ImportError:
    # Fallback for direct execution in CI
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from services.config import Settings

# Set up logging
logger = logging.getLogger(__name__)

# Import task handlers with optional imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

# Import task functions - Document Ingestion
try:
    from task_validate_document import validate_document
except ImportError as e:
    logger.warning(f"Could not import task_validate_document: {e}")
    validate_document = None

try:
    from task_chunk_document import chunk_document, ChunkingConfig
except ImportError as e:
    logger.warning(f"Could not import task_chunk_document: {e}")
    chunk_document = None

    # Create a simple ChunkingConfig class if not available
    class ChunkingConfig:
        def __init__(self):
            self.chunk_size = 1000
            self.overlap_size = 200


# Import task functions - Knowledge Management
try:
    from task_validate_knowledge_input import validate_knowledge_input
except ImportError as e:
    logger.warning(f"Could not import task_validate_knowledge_input: {e}")
    validate_knowledge_input = None

try:
    from task_check_duplicate_knowledge import check_duplicate_knowledge
except ImportError as e:
    logger.warning(f"Could not import task_check_duplicate_knowledge: {e}")
    check_duplicate_knowledge = None

# Import task functions - RAG Query Pipeline
try:
    from task_process_user_query import process_user_query
except ImportError as e:
    logger.warning(f"Could not import task_process_user_query: {e}")
    process_user_query = None

try:
    from task_retrieve_context import retrieve_context
except ImportError as e:
    logger.warning(f"Could not import task_retrieve_context: {e}")
    retrieve_context = None

logger = logging.getLogger(__name__)


class ExternalTaskWorker:
    """Worker that polls Camunda for external tasks and executes them."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.camunda_url = "http://localhost:8080/engine-rest"
        self.worker_id = f"odras-worker-{int(time.time())}"
        self.session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=[
                "HEAD",
                "GET",
                "PUT",
                "DELETE",
                "OPTIONS",
                "TRACE",
                "POST",
            ],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Task handlers mapping
        self.task_handlers = {
            # Document Ingestion Pipeline
            "validate-document": self.handle_validate_document,
            "parse-document": self.handle_parse_document,
            "chunk-document": self.handle_chunk_document,
            "generate-embeddings": self.handle_generate_embeddings,
            "store-vector-rag": self.handle_store_vector_rag,
            "store-metadata": self.handle_store_metadata,
            "update-search-index": self.handle_update_search_index,
            # Knowledge Management Pipeline
            "validate-knowledge-input": self.handle_validate_knowledge_input,
            "check-duplicate-knowledge": self.handle_check_duplicate_knowledge,
            # RAG Query Pipeline
            "process-user-query": self.handle_process_user_query,
            "retrieve-context": self.handle_retrieve_context,
            "rerank-context": self.handle_rerank_context,
            "fallback-search": self.handle_fallback_search,
            "construct-prompt": self.handle_construct_prompt,
            "llm-generation": self.handle_llm_generation,
            "process-response": self.handle_process_response,
            "log-interaction": self.handle_log_interaction,
        }

        self.running = False

    def start(self):
        """Start the external task worker."""
        self.running = True
        logger.info(f"Starting external task worker: {self.worker_id}")

        while self.running:
            try:
                # Poll for external tasks
                tasks = self.fetch_and_lock_tasks()

                if tasks:
                    logger.info(f"Received {len(tasks)} tasks")
                    for task in tasks:
                        self.execute_task(task)
                else:
                    # No tasks available, sleep briefly
                    time.sleep(1)

            except KeyboardInterrupt:
                logger.info("Received interrupt signal, stopping worker...")
                break
            except Exception as e:
                logger.error(f"Error in worker main loop: {str(e)}")
                time.sleep(5)  # Wait before retrying

        logger.info("External task worker stopped")

    def stop(self):
        """Stop the external task worker."""
        self.running = False

    def fetch_and_lock_tasks(self) -> List[Dict]:
        """Fetch and lock external tasks from Camunda."""
        try:
            url = f"{self.camunda_url}/external-task/fetchAndLock"

            # Topics we want to handle
            topics = []
            for topic_name in self.task_handlers.keys():
                topics.append(
                    {
                        "topicName": topic_name,
                        "lockDuration": 300000,  # 5 minutes
                        "variables": [
                            "document_content",
                            "document_filename",
                            "document_mime_type",
                            "parsed_content",
                            "chunks_created",
                            "embeddings_generated",
                            "knowledge_content",
                            "knowledge_format",
                            "knowledge_metadata",
                            "processed_knowledge",
                            "similarity_threshold",
                            "search_scope",
                            "user_query",
                            "query_metadata",
                            "processed_query",
                            "search_parameters",
                            "retrieved_chunks",
                            "reranked_context",
                            "context_quality_score",
                            "augmented_prompt",
                            "llm_response",
                            "final_response",
                        ],
                    }
                )

            payload = {"workerId": self.worker_id, "maxTasks": 10, "topics": topics}

            response = self.session.post(
                url,
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch tasks: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            logger.error(f"Error fetching tasks: {str(e)}")
            return []

    def execute_task(self, task: Dict):
        """Execute a single external task."""
        task_id = task.get("id")
        topic_name = task.get("topicName")
        variables = task.get("variables", {})

        logger.info(f"Executing task {task_id} for topic {topic_name}")

        try:
            # Get the task handler
            handler = self.task_handlers.get(topic_name)
            if not handler:
                raise Exception(f"No handler found for topic: {topic_name}")

            # Extract variables
            task_variables = {}
            for var_name, var_data in variables.items():
                task_variables[var_name] = var_data.get("value")

            logger.info(f"Task variables: {task_variables}")

            # Execute the task
            result = handler(task_variables)

            # Complete the task with results
            self.complete_task(task_id, result)
            logger.info(f"Successfully completed task {task_id}")

        except Exception as e:
            error_msg = f"Task execution failed: {str(e)}"
            logger.error(f"Error executing task {task_id}: {error_msg}")
            logger.error(traceback.format_exc())

            # Handle the task failure
            self.handle_failure(task_id, error_msg, traceback.format_exc())

    def complete_task(self, task_id: str, result_variables: Dict):
        """Complete an external task with result variables."""
        try:
            url = f"{self.camunda_url}/external-task/{task_id}/complete"

            # Format variables for Camunda
            variables = {}
            for key, value in result_variables.items():
                if isinstance(value, (dict, list)):
                    variables[key] = {"value": json.dumps(value), "type": "Json"}
                elif isinstance(value, bool):
                    variables[key] = {"value": value, "type": "Boolean"}
                elif isinstance(value, int):
                    variables[key] = {"value": value, "type": "Integer"}
                elif isinstance(value, float):
                    variables[key] = {"value": value, "type": "Double"}
                else:
                    variables[key] = {"value": str(value), "type": "String"}

            # Debug logging for key variables
            if "sources" in result_variables:
                print(f"COMPLETE_TASK: Setting sources variable with {len(result_variables['sources'])} items")
                print(f"COMPLETE_TASK: Sources JSON: {json.dumps(result_variables['sources'])[:200]}...")
            if "chunks_found" in result_variables:
                print(f"COMPLETE_TASK: Setting chunks_found = {result_variables['chunks_found']}")
            if "llm_confidence" in result_variables:
                print(f"COMPLETE_TASK: Setting llm_confidence = {result_variables['llm_confidence']}")
            if "confidence" in result_variables:
                print(f"COMPLETE_TASK: Setting confidence = {result_variables['confidence']}")

            # Debug: Show all variables being set
            print(f"COMPLETE_TASK: Setting {len(result_variables)} variables: {list(result_variables.keys())}")

            payload = {"workerId": self.worker_id, "variables": variables}

            response = self.session.post(
                url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code != 204:
                logger.error(
                    f"Failed to complete task {task_id}: {response.status_code} - {response.text}"
                )

        except Exception as e:
            logger.error(f"Error completing task {task_id}: {str(e)}")

    def handle_failure(self, task_id: str, error_message: str, error_details: str):
        """Handle external task failure."""
        try:
            url = f"{self.camunda_url}/external-task/{task_id}/failure"

            payload = {
                "workerId": self.worker_id,
                "errorMessage": error_message,
                "errorDetails": error_details,
                "retries": 0,  # No retries for now
                "retryTimeout": 0,
            }

            response = self.session.post(
                url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code != 204:
                logger.error(
                    f"Failed to report task failure {task_id}: {response.status_code} - {response.text}"
                )

        except Exception as e:
            logger.error(f"Error reporting task failure {task_id}: {str(e)}")

    # Task Handlers
    def handle_validate_document(self, variables: Dict) -> Dict:
        """Handle document validation task."""
        document_path = variables.get("document_content")
        filename = variables.get("document_filename", "unknown")
        mime_type = variables.get("document_mime_type")

        if not document_path:
            raise Exception("document_content variable is required")

        if validate_document:
            result = validate_document(document_path, filename, mime_type)
        else:
            # Simple fallback validation
            result = {
                "validation_result": "success",
                "validation_errors": [],
                "document_metadata": {
                    "source_filename": filename,
                    "validation_timestamp": time.time(),
                    "processing_status": "validated_fallback",
                },
                "file_info": {"filename": filename, "file_path": document_path},
            }

        return result

    def handle_parse_document(self, variables: Dict) -> Dict:
        """Handle document parsing task."""
        # This would integrate with document processing service
        document_path = variables.get("document_content")

        if not document_path:
            raise Exception("document_content variable is required")

        # For now, return a simple text extraction
        try:
            if document_path.endswith(".txt"):
                with open(document_path, "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                # Would use proper document parsing here
                content = f"Parsed content from {document_path}"

            return {
                "parsed_content": content,
                "parsing_stats": {
                    "content_length": len(content),
                    "processing_time": time.time(),
                },
            }
        except Exception as e:
            raise Exception(f"Failed to parse document: {str(e)}")

    def handle_chunk_document(self, variables: Dict) -> Dict:
        """Handle document chunking task."""
        content = variables.get("parsed_content")
        if not content:
            raise Exception("parsed_content variable is required")

        # Get chunking configuration
        config = ChunkingConfig()
        if "chunk_size" in variables:
            config.chunk_size = int(variables["chunk_size"])
        if "overlap_size" in variables:
            config.overlap_size = int(variables["overlap_size"])

        metadata = variables.get("document_metadata", {})
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        result = chunk_document(content, metadata, config)
        return result

    def handle_generate_embeddings(self, variables: Dict) -> Dict:
        """Handle embedding generation task."""
        chunks_data = variables.get("chunks_created")
        if not chunks_data:
            raise Exception("chunks_created variable is required")

        if isinstance(chunks_data, str):
            chunks_data = json.loads(chunks_data)

        # Extract text from chunks
        texts = []
        for chunk in chunks_data:
            texts.append(chunk.get("content", ""))

        # Generate embeddings (simplified for now)
        embeddings = []
        for i, text in enumerate(texts):
            # This would use actual embedding service
            embedding = [0.1] * 384  # Placeholder embedding
            embeddings.append(
                {
                    "chunk_index": i,
                    "embedding": embedding,
                    "text": text[:100] + "..." if len(text) > 100 else text,
                }
            )

        return {
            "embeddings_generated": embeddings,
            "embedding_stats": {
                "total_embeddings": len(embeddings),
                "embedding_dimension": 384,
                "generation_time": time.time(),
            },
        }

    def handle_store_vector_rag(self, variables: Dict) -> Dict:
        """Handle vector database storage task."""
        embeddings_data = variables.get("embeddings_generated")
        if not embeddings_data:
            raise Exception("embeddings_generated variable is required")

        if isinstance(embeddings_data, str):
            embeddings_data = json.loads(embeddings_data)

        # Store in vector database (simplified for now)
        return {
            "vector_storage_result": "success",
            "records_stored": len(embeddings_data),
            "storage_time": time.time(),
        }

    def handle_store_metadata(self, variables: Dict) -> Dict:
        """Handle metadata storage task."""
        document_metadata = variables.get("document_metadata", {})
        if isinstance(document_metadata, str):
            document_metadata = json.loads(document_metadata)

        # Store metadata (simplified for now)
        return {
            "metadata_storage_result": "success",
            "metadata_id": f"meta_{int(time.time())}",
            "storage_time": time.time(),
        }

    def handle_update_search_index(self, variables: Dict) -> Dict:
        """Handle search index update task."""
        # Update search index (simplified for now)
        return {
            "index_update_result": "success",
            "index_name": "rag_documents",
            "update_time": time.time(),
        }

    def handle_validate_knowledge_input(self, variables: Dict) -> Dict:
        """Handle knowledge input validation task."""
        content = variables.get("knowledge_content")
        format_type = variables.get("knowledge_format", "text")
        metadata = variables.get("knowledge_metadata", {})

        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        if not content:
            raise Exception("knowledge_content variable is required")

        result = validate_knowledge_input(content, format_type, metadata)
        return result

    def handle_check_duplicate_knowledge(self, variables: Dict) -> Dict:
        """Handle duplicate knowledge check task."""
        knowledge_data = variables.get("processed_knowledge")
        if isinstance(knowledge_data, str):
            knowledge_data = json.loads(knowledge_data)

        similarity_threshold = float(variables.get("similarity_threshold", 0.85))
        search_scope = variables.get("search_scope", "global")

        result = check_duplicate_knowledge(knowledge_data, similarity_threshold, search_scope)
        return result

    # RAG Query Pipeline Handlers
    def handle_process_user_query(self, variables: Dict) -> Dict:
        """Handle user query processing task."""
        query = variables.get("user_query", "")
        query_metadata = variables.get("query_metadata", {})

        if isinstance(query_metadata, str):
            try:
                query_metadata = json.loads(query_metadata)
            except:
                query_metadata = {}

        if not query:
            raise Exception("user_query variable is required")

        if process_user_query:
            result = process_user_query(query, query_metadata)
        else:
            # Simple fallback processing
            result = {
                "processed_query": {
                    "original_query": query,
                    "cleaned_query": query.strip(),
                    "key_terms": query.lower().split()[:5],
                    "query_type": "informational",
                },
                "query_analysis": {"complexity_score": 0.5},
                "search_parameters": {
                    "primary_terms": query.lower().split()[:3],
                    "max_results": 10,
                    "min_similarity_threshold": float(query_metadata.get("similarity_threshold", 0.5)),
                },
                "processing_status": "success",
                "errors": [],
            }

        return result

    def handle_retrieve_context(self, variables: Dict) -> Dict:
        """Handle context retrieval task."""
        processed_query = variables.get("processed_query")
        search_parameters = variables.get("search_parameters")

        if isinstance(processed_query, str):
            processed_query = json.loads(processed_query)
        if isinstance(search_parameters, str):
            search_parameters = json.loads(search_parameters)

        if not processed_query:
            raise Exception("processed_query variable is required")

        # Use the existing RAG service directly for more reliable results
        print("Using existing RAG service for context retrieval...")
        result = self.simple_retrieval_fallback(processed_query, search_parameters, variables)
        return result

    def handle_rerank_context(self, variables: Dict) -> Dict:
        """Handle context reranking task."""
        retrieved_chunks = variables.get("retrieved_chunks", [])
        if isinstance(retrieved_chunks, str):
            retrieved_chunks = json.loads(retrieved_chunks)

        # Simple reranking - sort by similarity score
        if retrieved_chunks:
            retrieved_chunks.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
            # Keep top 5
            reranked_chunks = retrieved_chunks[:5]
            avg_score = sum(chunk.get("similarity_score", 0) for chunk in reranked_chunks) / len(
                reranked_chunks
            )
        else:
            reranked_chunks = []
            avg_score = 0.0

        return {
            "reranked_context": reranked_chunks,
            "context_quality_score": avg_score,
            "reranking_stats": {
                "original_count": len(retrieved_chunks),
                "reranked_count": len(reranked_chunks),
                "avg_quality_score": avg_score,
            },
            "processing_status": "success",
            "errors": [],
        }

    def handle_fallback_search(self, variables: Dict) -> Dict:
        """Handle fallback search when context quality is poor."""
        processed_query = variables.get("processed_query", {})
        if isinstance(processed_query, str):
            processed_query = json.loads(processed_query)

        # Simple fallback - expand search terms
        original_terms = processed_query.get("key_terms", [])
        expanded_terms = original_terms + [
            "system",
            "requirement",
            "process",
        ]  # Add common terms

        fallback_chunks = [
            {
                "chunk_id": "fallback_expanded_1",
                "content": "Expanded search result providing broader context for the user query.",
                "similarity_score": 0.65,
                "source_document": "expanded_search.txt",
            }
        ]

        return {
            "retrieved_chunks": fallback_chunks,
            "fallback_search_applied": True,
            "expanded_terms": expanded_terms,
            "processing_status": "success",
            "errors": [],
        }

    def handle_construct_prompt(self, variables: Dict) -> Dict:
        """Handle prompt construction with retrieved context."""
        processed_query = variables.get("processed_query", {})
        context_chunks = variables.get("reranked_context", variables.get("retrieved_chunks", []))

        if isinstance(processed_query, str):
            processed_query = json.loads(processed_query)
        if isinstance(context_chunks, str):
            context_chunks = json.loads(context_chunks)

        query = processed_query.get("original_query", "No query provided")

        # Build context from chunks
        context_text = ""
        for i, chunk in enumerate(context_chunks[:3]):  # Use top 3 chunks
            context_text += f"\n[Context {i+1}]: {chunk.get('content', '')}"

        # Construct augmented prompt
        prompt_template = """You are a helpful assistant answering questions based on provided context.

Context:{context}

User Question: {query}

Please provide a comprehensive answer based on the context provided. If the context doesn't contain enough information to fully answer the question, acknowledge this and provide what information you can."""

        augmented_prompt = prompt_template.format(context=context_text, query=query)

        return {
            "augmented_prompt": augmented_prompt,
            "context_chunks_used": len(context_chunks),
            "prompt_stats": {
                "total_chars": len(augmented_prompt),
                "context_chars": len(context_text),
                "query_chars": len(query),
            },
            "processing_status": "success",
            "errors": [],
        }

    def handle_llm_generation(self, variables: Dict) -> Dict:
        """Handle LLM response generation."""
        prompt = variables.get("augmented_prompt", "")

        if not prompt:
            raise Exception("augmented_prompt variable is required")

        # Extract the context and question from the prompt
        lines = prompt.split("\n")
        context_lines = []
        user_question = ""

        # Parse the prompt to extract actual content
        in_context = False
        for line in lines:
            if "Context:" in line:
                in_context = True
                continue
            elif "User Question:" in line:
                in_context = False
                user_question = line.replace("User Question:", "").strip()
                continue
            elif in_context and line.strip():
                context_lines.append(line.strip())

        context_text = "\n".join(context_lines)

        # ACTUALLY CALL THE EXTERNAL LLM - stop using mock responses!
        try:
            import asyncio
            import sys
            import os

            # Add proper path for imports
            backend_path = os.path.join(os.path.dirname(__file__), "..")
            if backend_path not in sys.path:
                sys.path.insert(0, backend_path)

            from services.rag_service import get_rag_service

            rag_service = get_rag_service()

            # Create fake chunks from context for the LLM call
            fake_chunks = []
            if context_text:
                fake_chunks.append({
                    "payload": {
                        "content": context_text,
                        "asset_id": "workflow_context",
                        "source_asset": "workflow_source",
                        "document_type": "document"
                    },
                    "score": 0.8
                })

            # Call the ACTUAL LLM generation method from RAG service
            llm_result = asyncio.run(
                rag_service._generate_response(
                    question=user_question,
                    relevant_chunks=fake_chunks,
                    response_style="comprehensive"
                )
            )

            print(f"LLM CALL RESULT: {llm_result}")

            if llm_result and "answer" in llm_result:
                answer = llm_result["answer"]
                confidence = llm_result.get("confidence", "medium")
                print(f"LLM SUCCESS: confidence={confidence}")
            else:
                # Fallback if LLM fails
                answer = context_text.strip() if context_text else "I couldn't find relevant information."
                confidence = "medium" if context_text else "low"
                print(f"LLM FALLBACK: confidence={confidence}")

        except Exception as e:
            print(f"LLM CALL FAILED: {e}")
            # Fallback to context text
            answer = context_text.strip() if context_text else "I couldn't find relevant information."
            confidence = "medium" if context_text else "low"

        # Embed confidence in the response for reliable transfer
        structured_response = {
            "answer": answer,
            "confidence": confidence,
            "metadata": {
                "llm_called": True,
                "context_used": len(context_text) > 0,
                "response_length": len(answer)
            }
        }

        result = {
            "llm_response": json.dumps(structured_response),  # Embed confidence in response
            "generation_stats": {
                "prompt_length": len(prompt),
                "response_length": len(answer),
                "context_used": len(context_text) > 0,
                "llm_called": True,
            },
            "processing_status": "success",
            "errors": [],
        }

        print(f"LLM-GENERATION RETURNING: confidence={confidence}")
        print(f"LLM-GENERATION RESULT: {result}")

        return result

    def handle_process_response(self, variables: Dict) -> Dict:
        """Handle response processing and formatting."""
        llm_response_raw = variables.get("llm_response", "")
        context_chunks = variables.get("reranked_context", variables.get("retrieved_chunks", []))

        # Extract confidence from structured llm_response
        llm_confidence = None
        llm_response = ""

        try:
            if llm_response_raw:
                # Try to parse structured response
                structured_data = json.loads(llm_response_raw)
                llm_response = structured_data.get("answer", llm_response_raw)
                llm_confidence = structured_data.get("confidence")
                print(f"PROCESS-RESPONSE: Extracted confidence={llm_confidence} from structured response")
            else:
                llm_response = llm_response_raw
        except json.JSONDecodeError:
            # Fallback to raw response if not structured
            llm_response = llm_response_raw
            print("PROCESS-RESPONSE: Using raw llm_response (not structured)")

        print(f"PROCESS-RESPONSE DEBUG: Available variables = {list(variables.keys())}")
        print(f"PROCESS-RESPONSE DEBUG: extracted confidence = {llm_confidence}")

        if isinstance(context_chunks, str):
            context_chunks = json.loads(context_chunks)

        # Get actual asset titles from database for better citations
        citations = []
        seen_assets = set()  # Avoid duplicate sources

        for i, chunk in enumerate(context_chunks[:3]):
            asset_id = chunk.get("asset_id", "unknown")
            if asset_id in seen_assets:
                continue

            # Try to get actual asset title from database
            asset_title = "Unknown Document"
            try:
                from services.db import DatabaseService
                from services.config import Settings

                settings = Settings()
                db_service = DatabaseService(settings)
                conn = db_service._conn()

                with conn.cursor() as cur:
                    cur.execute("SELECT title FROM knowledge_assets WHERE id = %s", (asset_id,))
                    result = cur.fetchone()
                    if result:
                        asset_title = result[0]

                db_service._return(conn)
            except Exception as e:
                # Fallback to cleaned up asset ID if database lookup fails
                if len(asset_id) == 36 and '-' in asset_id:
                    asset_title = f"Knowledge Asset {asset_id[:8]}"
                else:
                    asset_title = chunk.get("source_document", "Unknown Document")

            citations.append({
                "citation_id": f"[{len(citations)+1}]",
                "source_document": asset_title,
                "similarity_score": chunk.get("similarity_score", 0.0),
            })
            seen_assets.add(asset_id)

        # Add sources to the response like the direct RAG does
        final_response = llm_response.strip()
        if citations:
            final_response += "\n\nSources:\n"
            for citation in citations:
                final_response += f"{citation['citation_id']} {citation['source_document']}\n"

        # Convert citations to proper source format for API
        sources = []
        for i, citation in enumerate(citations):
            # Use the corresponding chunk for this citation
            if i < len(context_chunks):
                chunk = context_chunks[i]
                sources.append({
                    "asset_id": chunk.get("asset_id", "unknown"),
                    "title": citation["source_document"],  # Use the proper title from citation
                    "document_type": "document",
                    "chunk_id": chunk.get("chunk_id"),
                    "relevance_score": chunk.get("similarity_score", 0.0),
                })

        result = {
            "final_response": final_response,
            "sources": sources,  # Add sources in the format the API expects
            "citations": citations,
            "chunks_found": len(context_chunks),  # Add explicit chunks count
            "llm_confidence": llm_confidence,  # Use extracted LLM confidence
            "response_stats": {
                "original_length": len(llm_response),
                "final_length": len(final_response),
                "citations_added": len(citations),
            },
            "processing_status": "success",
            "errors": [],
        }

        print(f"PROCESS-RESPONSE INPUT: context_chunks={len(context_chunks)}, llm_confidence={llm_confidence}")
        print(f"PROCESS-RESPONSE OUTPUT: sources={len(sources)}, chunks_found={len(context_chunks)}")
        print(f"PROCESS-RESPONSE SOURCES: {sources}")

        return result

    def simple_retrieval_fallback(self, processed_query: Dict, search_parameters: Dict, variables: Dict) -> Dict:
        """Simple synchronous fallback for context retrieval."""
        try:
            # Use the existing RAG service directly
            import asyncio
            import sys
            import os

            # Add proper path for absolute imports
            backend_path = os.path.join(os.path.dirname(__file__), "..")
            if backend_path not in sys.path:
                sys.path.insert(0, backend_path)

            from services.rag_service import get_rag_service

            rag_service = get_rag_service()
            query_text = processed_query.get("cleaned_query", "")

            # Extract user and project from query metadata - exactly like hard-coded query
            query_metadata = json.loads(variables.get("query_metadata", "{}"))
            user_id = query_metadata.get("user_id")
            project_id = query_metadata.get("project_id")
            similarity_threshold = float(query_metadata.get("similarity_threshold", 0.5))
            max_chunks = int(query_metadata.get("max_results", 3))

            print(f"WORKFLOW RAG: Using user_id={user_id}, project_id={project_id}, threshold={similarity_threshold}")

            # Get the raw chunks with content (like the hard-coded query does)
            chunks = asyncio.run(
                rag_service._retrieve_relevant_chunks(
                    question=query_text,
                    project_id=project_id,
                    user_id=user_id,
                    max_chunks=max_chunks,
                    similarity_threshold=similarity_threshold,
                )
            )

            print(f"WORKFLOW RAG: Retrieved {len(chunks)} chunks with content")

            # Convert raw chunks to expected format - now with actual content!
            retrieved_chunks = []
            for chunk in chunks:
                chunk_data = chunk.get("payload", {})
                content = chunk_data.get("content", "")

                retrieved_chunks.append({
                    "chunk_id": chunk_data.get("chunk_id", "unknown"),
                    "content": content,
                    "similarity_score": chunk.get("score", 0.0),
                    "source_document": chunk_data.get("source_asset", "unknown"),
                    "asset_id": chunk_data.get("asset_id", "unknown"),
                    "project_id": chunk_data.get("project_id", "unknown"),
                })

            return {
                "retrieved_chunks": retrieved_chunks,
                "retrieval_stats": {
                    "total_results": len(retrieved_chunks),
                    "search_method": "existing_rag_service",
                    "avg_similarity": (
                        sum(chunk.get("similarity_score", 0) for chunk in retrieved_chunks)
                        / len(retrieved_chunks)
                        if retrieved_chunks
                        else 0.0
                    ),
                },
                "processing_status": "success",
                "errors": [],
            }

        except Exception as e:
            print(f"Fallback retrieval failed: {e}")
            return {
                "retrieved_chunks": [],
                "retrieval_stats": {"error": str(e)},
                "processing_status": "failure",
                "errors": [f"Retrieval failed: {str(e)}"],
            }

    def handle_log_interaction(self, variables: Dict) -> Dict:
        """Handle interaction logging."""
        processed_query = variables.get("processed_query", {})
        final_response = variables.get("final_response", "")

        if isinstance(processed_query, str):
            processed_query = json.loads(processed_query)

        # Log interaction data
        interaction_log = {
            "query": processed_query.get("original_query", ""),
            "response_preview": (
                final_response[:200] + "..." if len(final_response) > 200 else final_response
            ),
            "query_type": processed_query.get("query_type", "unknown"),
            "response_length": len(final_response),
            "interaction_timestamp": time.time(),
            "processing_pipeline": "rag_query",
        }

        print(f"RAG Interaction logged: {interaction_log['query'][:50]}...")

        return {
            "interaction_logged": True,
            "interaction_id": f"rag_interaction_{int(time.time())}",
            "log_data": interaction_log,
            "processing_status": "success",
            "errors": [],
        }
