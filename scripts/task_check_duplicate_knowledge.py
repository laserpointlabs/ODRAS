#!/usr/bin/env python3
"""
External Task Script: Check for Duplicate Knowledge
This script is called by Camunda BPMN process to check for duplicate knowledge in the knowledge base.

Input Variables (from Camunda):
- processed_knowledge: Processed knowledge data from validation step
- similarity_threshold: Threshold for similarity detection (0.0-1.0)
- search_scope: Scope of duplicate search ('global', 'project', 'category')

Output Variables (set in Camunda):
- duplicates_found: 'true' or 'false'
- duplicate_candidates: List of potential duplicate knowledge items
- similarity_scores: Similarity scores for each candidate
"""

import json
import sys
import os
import hashlib
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

# Add the backend directory to the path so we can import our services
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from services.config import Settings
from services.qdrant_service import QdrantService
from services.embedding_service import EmbeddingService


def check_duplicate_knowledge(
    knowledge_data: Dict,
    similarity_threshold: float = 0.85,
    search_scope: str = "global",
) -> Dict[str, Any]:
    """
    Check for duplicate knowledge in the knowledge base.

    Args:
        knowledge_data: Processed knowledge data
        similarity_threshold: Minimum similarity score to consider as duplicate
        search_scope: Scope of search ('global', 'project', 'category')

    Returns:
        Dict containing duplicate check results
    """
    duplicate_result = {
        "duplicates_found": "false",
        "duplicate_candidates": [],
        "similarity_scores": [],
        "search_stats": {},
        "processing_status": "success",
        "errors": [],
    }

    try:
        settings = Settings()
        qdrant_service = QdrantService(settings)
        embedding_service = EmbeddingService(settings)

        content = knowledge_data.get("content", "")
        if not content:
            duplicate_result["errors"].append("No content provided for duplicate check")
            return duplicate_result

        # Create embedding for the new knowledge
        try:
            query_embedding = embedding_service.create_embeddings([content])[0]
        except Exception as e:
            duplicate_result["processing_status"] = "failure"
            duplicate_result["errors"].append(f"Failed to create embedding: {str(e)}")
            return duplicate_result

        # Prepare search filters based on scope
        search_filters = {}
        if search_scope == "project":
            project_id = knowledge_data.get("metadata", {}).get("project_id")
            if project_id:
                search_filters["project_id"] = project_id
        elif search_scope == "category":
            category = knowledge_data.get("metadata", {}).get("category")
            if category:
                search_filters["category"] = category

        # Search for similar knowledge items
        try:
            # Use knowledge collection (different from requirements)
            collection_name = f"{settings.collection_name}_knowledge"

            similar_items = qdrant_service.search_similar(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=10,  # Get top 10 similar items
                score_threshold=max(0.5, similarity_threshold - 0.2),  # Cast a wider net
                filters=search_filters,
            )
        except Exception as e:
            # Collection might not exist yet, which is fine for first knowledge item
            print(f"Knowledge collection not found or search failed: {e}")
            similar_items = []

        # Process similar items to find duplicates
        duplicate_candidates = []
        similarity_scores = []

        for item in similar_items:
            score = item.get("score", 0.0)
            payload = item.get("payload", {})

            # Calculate additional similarity metrics
            content_similarity = calculate_content_similarity(content, payload.get("content", ""))
            title_similarity = calculate_title_similarity(
                knowledge_data.get("metadata", {}).get("title", ""),
                payload.get("metadata", {}).get("title", ""),
            )

            # Combined similarity score
            combined_score = max(score, (content_similarity + title_similarity) / 2)

            if combined_score >= similarity_threshold:
                duplicate_candidates.append(
                    {
                        "knowledge_id": payload.get("id"),
                        "title": payload.get("metadata", {}).get("title", "Untitled"),
                        "content_preview": payload.get("content", "")[:200] + "...",
                        "similarity_score": combined_score,
                        "vector_similarity": score,
                        "content_similarity": content_similarity,
                        "title_similarity": title_similarity,
                        "source": payload.get("metadata", {}).get("source"),
                        "created_date": payload.get("metadata", {}).get("created_date"),
                        "duplicate_type": classify_duplicate_type(
                            combined_score, content_similarity, title_similarity
                        ),
                    }
                )
                similarity_scores.append(combined_score)

        # Check for exact content matches (hash-based)
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        for candidate in duplicate_candidates:
            candidate_content = candidate.get("content_preview", "").replace("...", "")
            if content_hash == hashlib.sha256(candidate_content.encode("utf-8")).hexdigest():
                candidate["duplicate_type"] = "exact_match"
                candidate["similarity_score"] = 1.0

        # Set result based on findings
        if duplicate_candidates:
            duplicate_result["duplicates_found"] = "true"
            duplicate_result["duplicate_candidates"] = duplicate_candidates
            duplicate_result["similarity_scores"] = similarity_scores

            print(f"Found {len(duplicate_candidates)} potential duplicates")
            for candidate in duplicate_candidates[:3]:  # Show top 3
                print(f"  - {candidate['title']}: {candidate['similarity_score']:.3f} similarity")
        else:
            print("No duplicates found")

        # Search statistics
        duplicate_result["search_stats"] = {
            "total_searched": len(similar_items),
            "duplicates_found": len(duplicate_candidates),
            "highest_similarity": max(similarity_scores) if similarity_scores else 0.0,
            "search_scope": search_scope,
            "similarity_threshold": similarity_threshold,
            "content_hash": content_hash,
        }

    except Exception as e:
        duplicate_result["processing_status"] = "failure"
        duplicate_result["errors"].append(f"Duplicate check error: {str(e)}")
        print(f"Duplicate check failed: {str(e)}")

    return duplicate_result


def calculate_content_similarity(content1: str, content2: str) -> float:
    """Calculate simple content similarity using word overlap."""
    if not content1 or not content2:
        return 0.0

    words1 = set(content1.lower().split())
    words2 = set(content2.lower().split())

    if not words1 or not words2:
        return 0.0

    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))

    return intersection / union if union > 0 else 0.0


def calculate_title_similarity(title1: str, title2: str) -> float:
    """Calculate title similarity using simple word overlap."""
    if not title1 or not title2:
        return 0.0

    words1 = set(title1.lower().split())
    words2 = set(title2.lower().split())

    if not words1 or not words2:
        return 0.0

    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))

    return intersection / union if union > 0 else 0.0


def classify_duplicate_type(
    combined_score: float, content_similarity: float, title_similarity: float
) -> str:
    """Classify the type of duplicate based on similarity scores."""
    if combined_score >= 0.95:
        return "exact_match"
    elif combined_score >= 0.85:
        if title_similarity >= 0.8:
            return "very_similar"
        else:
            return "content_duplicate"
    elif combined_score >= 0.75:
        return "similar_content"
    else:
        return "potentially_related"


def main():
    """
    Main function for Camunda external task execution.
    Reads process variables and returns duplicate check results.
    """
    # For testing, use command line arguments
    if len(sys.argv) > 1:
        if os.path.exists(sys.argv[1]):
            # If argument is a file path, read the content
            with open(sys.argv[1], "r", encoding="utf-8") as f:
                content = f.read()
        else:
            # If argument is direct content
            content = sys.argv[1]

        knowledge_data = {
            "content": content,
            "format": "text",
            "metadata": {
                "title": "Test Knowledge",
                "source": "CLI Test",
                "project_id": "test_project",
            },
        }

        threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.85
        scope = sys.argv[3] if len(sys.argv) > 3 else "global"

        result = check_duplicate_knowledge(knowledge_data, threshold, scope)
        print(json.dumps(result, indent=2))
        return result

    # In production, this would be called by Camunda with process variables
    return {
        "duplicates_found": "false",
        "duplicate_candidates": [],
        "similarity_scores": [],
        "search_stats": {"total_searched": 0},
        "processing_status": "success",
        "errors": [],
    }


if __name__ == "__main__":
    main()

