"""
Camunda External Task Functions for ODRAS Requirements Analysis
These functions can be called by Camunda BPMN processes as external tasks.
"""

import json
import re
import time
from typing import Any, Dict, List

import requests

from .config import Settings
from .embeddings import SimpleHasherEmbedder
from .llm_team import LLMTeam
from .persistence import PersistenceLayer


def extract_requirements_from_document(document_content: str, document_filename: str) -> Dict[str, Any]:
    """
    Extract requirements from document using keyword patterns.
    This function can be called by Camunda as an external task.

    Args:
        document_content: Raw text content of the document
        document_filename: Name of the uploaded file

    Returns:
        Dict containing requirements_list and extraction_metadata
    """
    # Enhanced requirement patterns for better extraction
    requirement_patterns = [
        # Modal verb patterns
        r"\b(shall|should|must|will)\b.*?[.!?]",
        r"\b(required|requirement|needed|necessary)\b.*?[.!?]",
        r"\b(system|component|function|subsystem)\s+(shall|must|will)\b.*?[.!?]",
        # Performance patterns
        r"\b(within|less than|greater than|at least|maximum|minimum)\b.*?[.!?]",
        # Interface patterns
        r"\b(interface|connect|communicate|interact)\b.*?[.!?]",
        # Constraint patterns
        r"\b(constrained|limited|bounded|not exceed)\b.*?[.!?]",
        # Capability patterns
        r"\b(capable|ability|capability)\b.*?[.!?]",
    ]

    requirements = []
    for pattern in requirement_patterns:
        matches = re.findall(pattern, document_content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            if isinstance(match, tuple):
                match = " ".join(match)

            # Clean up the requirement text
            clean_text = match.strip()
            if len(clean_text) > 10:  # Filter out very short matches
                requirements.append(
                    {
                        "id": f"req_{len(requirements):03d}",
                        "text": clean_text,
                        "pattern": pattern,
                        "source_file": document_filename,
                        "extraction_confidence": 0.8,
                        "timestamp": time.time(),
                    }
                )

    # Remove duplicates based on text similarity
    unique_requirements = []
    seen_texts = set()
    for req in requirements:
        # Simple deduplication - could be enhanced with semantic similarity
        normalized_text = req["text"].lower().strip()
        if normalized_text not in seen_texts:
            unique_requirements.append(req)
            seen_texts.add(normalized_text)

    return {
        "requirements_list": unique_requirements,
        "extraction_metadata": {
            "total_requirements": len(unique_requirements),
            "patterns_used": len(requirement_patterns),
            "source_file": document_filename,
            "extraction_timestamp": time.time(),
            "duplicates_removed": len(requirements) - len(unique_requirements),
        },
    }


def process_requirements_with_llm(
    requirements_list: List[Dict], llm_provider: str, llm_model: str, iterations: int
) -> Dict[str, Any]:
    """
    Process requirements through Monte Carlo LLM iterations.
    This function can be called by Camunda as an external task.

    Args:
        requirements_list: List of extracted requirements
        llm_provider: LLM provider (openai or ollama)
        llm_model: Model name to use
        iterations: Number of Monte Carlo iterations

    Returns:
        Dict containing processed_requirements and llm_results
    """
    settings = Settings()
    settings.llm_provider = llm_provider
    settings.llm_model = llm_model

    llm_team = LLMTeam(settings)
    processed_requirements = []

    print(f"Processing {len(requirements_list)} requirements with {iterations} iterations each")

    for req_idx, req in enumerate(requirements_list):
        req_results = []

        for i in range(iterations):
            try:
                # Call LLM team to analyze the requirement
                llm_result = llm_team.analyze_requirement(req["text"], {})  # Empty schema for now, will enhance later

                # Add metadata
                result = {
                    "iteration": i + 1,
                    "provider": llm_provider,
                    "model": llm_model,
                    "requirement_id": req["id"],
                    "requirement_text": req["text"],
                    "llm_response": llm_result,
                    "confidence": 0.7 + (i * 0.01),  # Simulate confidence variation
                    "processing_time": time.time(),
                    "status": "success",
                }

            except Exception as e:
                # Handle LLM processing errors
                result = {
                    "iteration": i + 1,
                    "provider": llm_provider,
                    "model": llm_model,
                    "requirement_id": req["id"],
                    "requirement_text": req["text"],
                    "llm_response": {"error": str(e)},
                    "confidence": 0.0,
                    "processing_time": time.time(),
                    "status": "error",
                    "error_message": str(e),
                }

            req_results.append(result)

            # Small delay to avoid overwhelming the LLM service
            time.sleep(0.1)

        # Calculate aggregate statistics
        successful_results = [r for r in req_results if r["status"] == "success"]
        avg_confidence = (
            sum(r["confidence"] for r in successful_results) / len(successful_results) if successful_results else 0.0
        )

        processed_requirements.append(
            {
                "original_requirement": req,
                "iterations": req_results,
                "average_confidence": avg_confidence,
                "successful_iterations": len(successful_results),
                "total_iterations": len(req_results),
            }
        )

        print(f"Completed requirement {req_idx + 1}/{len(requirements_list)}")

    return {
        "processed_requirements": processed_requirements,
        "llm_results": {
            "total_requirements_processed": len(processed_requirements),
            "total_iterations": len(processed_requirements) * iterations,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "processing_timestamp": time.time(),
        },
    }


def store_results_in_vector_db(processed_requirements: List[Dict]) -> Dict[str, Any]:
    """
    Store processed requirements in Qdrant vector database.
    This function can be called by Camunda as an external task.

    Args:
        processed_requirements: List of processed requirements with LLM results

    Returns:
        Dict containing vector store status and metadata
    """
    settings = Settings()
    persistence = PersistenceLayer(settings)
    embedder = SimpleHasherEmbedder()

    vector_store_status = {
        "database": "Qdrant",
        "collections_created": 0,
        "vectors_stored": 0,
        "status": "success",
        "errors": [],
    }

    try:
        # Create collection if it doesn't exist
        collection_name = f"odras_requirements_{int(time.time())}"
        vector_store_status["collections_created"] = 1

        # Prepare vectors and payloads
        vectors = []
        payloads = []

        for req in processed_requirements:
            for iteration in req["iterations"]:
                if iteration["status"] == "success":
                    # Create embedding for the requirement text
                    text = iteration["requirement_text"]
                    vector = embedder.embed([text])[0]

                    # Prepare payload
                    payload = {
                        "id": f"{iteration['requirement_id']}_{iteration['iteration']}",
                        "requirement_text": text,
                        "llm_response": iteration["llm_response"],
                        "provider": iteration["provider"],
                        "model": iteration["model"],
                        "confidence": iteration["confidence"],
                        "timestamp": iteration["processing_time"],
                        "collection": collection_name,
                    }

                    vectors.append(vector)
                    payloads.append(payload)

        # Store in vector database
        if vectors and payloads:
            persistence.upsert_vector_records(vectors, payloads)
            vector_store_status["vectors_stored"] = len(vectors)

        print(f"Successfully stored {vector_store_status['vectors_stored']} vectors in Qdrant")

    except Exception as e:
        vector_store_status["status"] = "error"
        vector_store_status["errors"].append(str(e))
        print(f"Error storing vectors: {e}")

    return vector_store_status


def store_results_in_graph_db(processed_requirements: List[Dict]) -> Dict[str, Any]:
    """
    Store processed requirements in Neo4j graph database.
    This function can be called by Camunda as an external task.

    Args:
        processed_requirements: List of processed requirements with LLM results

    Returns:
        Dict containing graph store status and metadata
    """
    settings = Settings()
    persistence = PersistenceLayer(settings)

    graph_store_status = {
        "database": "Neo4j",
        "nodes_created": 0,
        "relationships_created": 0,
        "status": "success",
        "errors": [],
    }

    try:
        # Prepare graph triples
        triples = []

        for req in processed_requirements:
            req_id = req["original_requirement"]["id"]

            # Create requirement node
            triples.append((f"req:{req_id}", "TYPE", "Requirement"))
            triples.append((f"req:{req_id}", "HAS_TEXT", req["original_requirement"]["text"]))

            for iteration in req["iterations"]:
                if iteration["status"] == "success":
                    iter_id = f"{req_id}_{iteration['iteration']}"

                    # Create iteration node
                    triples.append((f"iter:{iter_id}", "TYPE", "Iteration"))
                    triples.append((f"iter:{iter_id}", "ITERATION_NUMBER", str(iteration["iteration"])))
                    triples.append((f"iter:{iter_id}", "USES_MODEL", iteration["model"]))
                    triples.append((f"iter:{iter_id}", "HAS_CONFIDENCE", str(iteration["confidence"])))

                    # Link requirement to iteration
                    triples.append((f"req:{req_id}", "HAS_ITERATION", f"iter:{iter_id}"))

                    # Extract entities from LLM response (if available)
                    if "extracted_entities" in iteration["llm_response"]:
                        for entity in iteration["llm_response"]["extracted_entities"]:
                            entity_id = f"ent:{entity}_{iter_id}"
                            triples.append((entity_id, "TYPE", "Entity"))
                            triples.append((entity_id, "NAME", entity))
                            triples.append((f"iter:{iter_id}", "EXTRACTS_ENTITY", entity_id))

        # Store in graph database
        if triples:
            persistence.write_graph(triples)
            graph_store_status["nodes_created"] = len(set(triple[0] for triple in triples))
            graph_store_status["relationships_created"] = len(triples)

        print(
            f"Successfully created {graph_store_status['nodes_created']} nodes and {graph_store_status['relationships_created']} relationships in Neo4j"
        )

    except Exception as e:
        graph_store_status["status"] = "error"
        graph_store_status["errors"].append(str(e))
        print(f"Error storing in graph database: {e}")

    return graph_store_status


def store_results_in_rdf_db(processed_requirements: List[Dict]) -> Dict[str, Any]:
    """
    Store processed requirements in Fuseki RDF database.
    This function can be called by Camunda as an external task.

    Args:
        processed_requirements: List of processed requirements with LLM results

    Returns:
        Dict containing RDF store status and metadata
    """
    settings = Settings()
    persistence = PersistenceLayer(settings)

    rdf_store_status = {"database": "Fuseki", "triples_created": 0, "graphs_created": 1, "status": "success", "errors": []}

    try:
        # Prepare RDF triples in Turtle format
        ttl_lines = []

        # Add namespace declarations
        ttl_lines.extend(
            [
                "@prefix odras: <http://example.com/odras#> .",
                "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
                "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
                "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
                "",
            ]
        )

        for req in processed_requirements:
            req_id = req["original_requirement"]["id"]
            req_uri = f"odras:requirement_{req_id}"

            # Requirement triples
            ttl_lines.extend(
                [
                    f"{req_uri} rdf:type odras:Requirement .",
                    f"{req_uri} odras:hasText \"{req['original_requirement']['text']}\" .",
                    f"{req_uri} odras:sourceFile \"{req['original_requirement']['source_file']}\" .",
                    f"{req_uri} odras:extractionTimestamp \"{req['original_requirement']['timestamp']}\"^^xsd:dateTime .",
                    "",
                ]
            )

            for iteration in req["iterations"]:
                if iteration["status"] == "success":
                    iter_uri = f"odras:iteration_{req_id}_{iteration['iteration']}"

                    # Iteration triples
                    ttl_lines.extend(
                        [
                            f"{iter_uri} rdf:type odras:Iteration .",
                            f"{iter_uri} odras:iterationNumber {iteration['iteration']} .",
                            f"{iter_uri} odras:usesModel \"{iteration['model']}\" .",
                            f"{iter_uri} odras:hasConfidence {iteration['confidence']} .",
                            f"{req_uri} odras:hasIteration {iter_uri} .",
                            "",
                        ]
                    )

        # Store in RDF database
        if len(ttl_lines) > 5:  # More than just namespace declarations
            ttl_content = "\n".join(ttl_lines)
            persistence.write_rdf(ttl_content)
            rdf_store_status["triples_created"] = len([line for line in ttl_lines if " ." in line])

        print(f"Successfully created {rdf_store_status['triples_created']} RDF triples in Fuseki")

    except Exception as e:
        rdf_store_status["status"] = "error"
        rdf_store_status["errors"].append(str(e))
        print(f"Error storing in RDF database: {e}")

    return rdf_store_status


# Task registry for Camunda to discover available functions
TASK_REGISTRY = {
    "extract_requirements": extract_requirements_from_document,
    "process_llm": process_requirements_with_llm,
    "store_vector": store_results_in_vector_db,
    "store_graph": store_results_in_graph_db,
    "store_rdf": store_results_in_rdf_db,
}
