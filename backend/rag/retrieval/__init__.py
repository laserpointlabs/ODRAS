"""
Retrieval Module for RAG

Provides abstract and concrete retriever implementations.
"""

from .retriever import Retriever
from .vector_retriever import VectorRetriever

__all__ = ["Retriever", "VectorRetriever"]

