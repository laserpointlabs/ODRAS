"""
Embedding Service for Knowledge Management.

Provides text embedding generation using various models including:
- Sentence Transformers (local)
- OpenAI embeddings (remote)
- Model management and caching
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import hashlib
import json
from datetime import datetime
import os

try:
    from sentence_transformers import SentenceTransformer
    import torch

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

from .config import Settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating and managing text embeddings.

    Supports multiple embedding models with automatic model management,
    caching, and batch processing capabilities.
    """

    def __init__(self, settings: Settings = None):
        """Initialize embedding service with configuration."""
        self.settings = settings or Settings()
        self.models = {}  # Cache loaded models
        self.model_configs = self._get_model_configurations()

        # Set up model cache directory
        self.cache_dir = getattr(self.settings, "embedding_cache_dir", "./models/embeddings")
        os.makedirs(self.cache_dir, exist_ok=True)

        logger.info("Embedding service initialized")

    def _get_model_configurations(self) -> Dict[str, Dict[str, Any]]:
        """
        Get supported embedding model configurations.

        Returns:
            Dictionary of model configurations
        """
        configs = {
            # Sentence Transformers models (local)
            "all-MiniLM-L6-v2": {
                "type": "sentence_transformer",
                "model_name": "all-MiniLM-L6-v2",
                "dimensions": 384,
                "max_tokens": 512,
                "description": "Fast, lightweight model good for general text",
                "available": SENTENCE_TRANSFORMERS_AVAILABLE,
            },
            "all-mpnet-base-v2": {
                "type": "sentence_transformer",
                "model_name": "all-mpnet-base-v2",
                "dimensions": 768,
                "max_tokens": 512,
                "description": "Higher quality model with larger dimensions",
                "available": SENTENCE_TRANSFORMERS_AVAILABLE,
            },
            "multi-qa-MiniLM-L6-cos-v1": {
                "type": "sentence_transformer",
                "model_name": "multi-qa-MiniLM-L6-cos-v1",
                "dimensions": 384,
                "max_tokens": 512,
                "description": "Optimized for question-answering and semantic search",
                "available": SENTENCE_TRANSFORMERS_AVAILABLE,
            },
            # OpenAI models (remote)
            "text-embedding-ada-002": {
                "type": "openai",
                "model_name": "text-embedding-ada-002",
                "dimensions": 1536,
                "max_tokens": 8192,
                "description": "OpenAI embedding model (requires API key)",
                "available": OPENAI_AVAILABLE
                and bool(getattr(self.settings, "openai_api_key", None)),
            },
            "text-embedding-3-small": {
                "type": "openai",
                "model_name": "text-embedding-3-small",
                "dimensions": 1536,
                "max_tokens": 8192,
                "description": "OpenAI embedding model v3 small (requires API key)",
                "available": OPENAI_AVAILABLE
                and bool(getattr(self.settings, "openai_api_key", None)),
            },
            "text-embedding-3-large": {
                "type": "openai",
                "model_name": "text-embedding-3-large",
                "dimensions": 3072,
                "max_tokens": 8192,
                "description": "OpenAI embedding model v3 large (requires API key)",
                "available": OPENAI_AVAILABLE
                and bool(getattr(self.settings, "openai_api_key", None)),
            },
        }

        return configs

    def list_available_models(self) -> List[Dict[str, Any]]:
        """
        List all available embedding models.

        Returns:
            List of model information dictionaries
        """
        available_models = []

        for model_id, config in self.model_configs.items():
            if config["available"]:
                available_models.append(
                    {
                        "model_id": model_id,
                        "type": config["type"],
                        "dimensions": config["dimensions"],
                        "max_tokens": config["max_tokens"],
                        "description": config["description"],
                        "loaded": model_id in self.models,
                    }
                )

        logger.info(f"Listed {len(available_models)} available embedding models")
        return available_models

    def load_model(self, model_id: str) -> bool:
        """
        Load an embedding model into memory.

        Args:
            model_id: Model identifier from configurations

        Returns:
            True if model loaded successfully
        """
        try:
            if model_id in self.models:
                logger.info(f"Model '{model_id}' already loaded")
                return True

            if model_id not in self.model_configs:
                logger.error(f"Unknown model ID: {model_id}")
                return False

            config = self.model_configs[model_id]

            if not config["available"]:
                logger.error(
                    f"Model '{model_id}' is not available (missing dependencies or configuration)"
                )
                return False

            if config["type"] == "sentence_transformer":
                logger.info(f"Loading SentenceTransformer model: {config['model_name']}")
                model = SentenceTransformer(config["model_name"], cache_folder=self.cache_dir)
                self.models[model_id] = {
                    "model": model,
                    "type": "sentence_transformer",
                    "config": config,
                }

            elif config["type"] == "openai":
                logger.info(f"Setting up OpenAI model: {config['model_name']}")
                # For OpenAI, we don't load anything - we'll use the API directly
                api_key = getattr(self.settings, "openai_api_key", None)
                if not api_key:
                    logger.error("OpenAI API key not configured")
                    return False

                self.models[model_id] = {
                    "model": None,  # No local model to load
                    "type": "openai",
                    "config": config,
                    "api_key": api_key,
                }

            else:
                logger.error(f"Unknown model type: {config['type']}")
                return False

            logger.info(f"Successfully loaded model: {model_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to load model '{model_id}': {str(e)}")
            return False

    def unload_model(self, model_id: str) -> bool:
        """
        Unload a model from memory.

        Args:
            model_id: Model identifier

        Returns:
            True if model was unloaded successfully
        """
        try:
            if model_id in self.models:
                del self.models[model_id]
                logger.info(f"Unloaded model: {model_id}")

                # Clear CUDA cache if using GPU
                if torch and torch.cuda.is_available():
                    torch.cuda.empty_cache()

                return True
            else:
                logger.warning(f"Model '{model_id}' was not loaded")
                return False

        except Exception as e:
            logger.error(f"Failed to unload model '{model_id}': {str(e)}")
            return False

    def generate_embeddings(
        self, texts: List[str], model_id: str = "all-MiniLM-L6-v2", batch_size: int = 32
    ) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed
            model_id: Embedding model to use
            batch_size: Batch size for processing

        Returns:
            List of embedding vectors (each as list of floats)
        """
        try:
            if not texts:
                return []

            # Ensure model is loaded
            if not self.load_model(model_id):
                raise RuntimeError(f"Failed to load model: {model_id}")

            model_info = self.models[model_id]
            config = model_info["config"]

            # Truncate texts if they exceed max tokens (rough approximation)
            max_chars = config["max_tokens"] * 4  # Rough char-to-token ratio
            truncated_texts = [
                text[:max_chars] if len(text) > max_chars else text for text in texts
            ]

            embeddings = []

            if model_info["type"] == "sentence_transformer":
                # Use SentenceTransformer
                model = model_info["model"]

                # Process in batches
                for i in range(0, len(truncated_texts), batch_size):
                    batch = truncated_texts[i : i + batch_size]
                    batch_embeddings = model.encode(
                        batch, convert_to_numpy=True, show_progress_bar=False
                    )
                    embeddings.extend([emb.tolist() for emb in batch_embeddings])

            elif model_info["type"] == "openai":
                # Use OpenAI API
                api_key = model_info["api_key"]
                client = openai.OpenAI(api_key=api_key)

                # Process in batches (OpenAI has rate limits)
                for i in range(0, len(truncated_texts), min(batch_size, 100)):  # OpenAI limit
                    batch = truncated_texts[i : i + min(batch_size, 100)]

                    response = client.embeddings.create(input=batch, model=config["model_name"])

                    batch_embeddings = [data.embedding for data in response.data]
                    embeddings.extend(batch_embeddings)

            else:
                raise RuntimeError(f"Unsupported model type: {model_info['type']}")

            logger.info(f"Generated {len(embeddings)} embeddings using model '{model_id}'")
            return embeddings

        except Exception as e:
            logger.error(f"Failed to generate embeddings with model '{model_id}': {str(e)}")
            raise RuntimeError(f"Embedding generation failed: {str(e)}")

    def generate_single_embedding(
        self, text: str, model_id: str = "all-MiniLM-L6-v2"
    ) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text string to embed
            model_id: Embedding model to use

        Returns:
            Embedding vector as list of floats
        """
        embeddings = self.generate_embeddings([text], model_id)
        return embeddings[0] if embeddings else []

    def compute_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float],
        similarity_type: str = "cosine",
    ) -> float:
        """
        Compute similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            similarity_type: Type of similarity (cosine, euclidean, dot)

        Returns:
            Similarity score
        """
        try:
            import numpy as np

            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            if similarity_type == "cosine":
                # Cosine similarity
                dot_product = np.dot(vec1, vec2)
                norm1 = np.linalg.norm(vec1)
                norm2 = np.linalg.norm(vec2)
                return float(dot_product / (norm1 * norm2)) if norm1 * norm2 != 0 else 0.0

            elif similarity_type == "euclidean":
                # Euclidean distance (converted to similarity)
                distance = np.linalg.norm(vec1 - vec2)
                return float(1 / (1 + distance))  # Convert distance to similarity

            elif similarity_type == "dot":
                # Dot product
                return float(np.dot(vec1, vec2))

            else:
                raise ValueError(f"Unknown similarity type: {similarity_type}")

        except Exception as e:
            logger.error(f"Failed to compute similarity: {str(e)}")
            return 0.0

    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific model.

        Args:
            model_id: Model identifier

        Returns:
            Model information dictionary or None if not found
        """
        if model_id not in self.model_configs:
            return None

        config = self.model_configs[model_id]

        return {
            "model_id": model_id,
            "type": config["type"],
            "model_name": config["model_name"],
            "dimensions": config["dimensions"],
            "max_tokens": config["max_tokens"],
            "description": config["description"],
            "available": config["available"],
            "loaded": model_id in self.models,
        }

    def get_default_model(self) -> str:
        """
        Get the default embedding model ID.

        Returns:
            Default model ID
        """
        # Try to find the first available model, preferring sentence transformers
        for model_id, config in self.model_configs.items():
            if config["available"] and config["type"] == "sentence_transformer":
                return model_id

        # Fallback to any available model
        for model_id, config in self.model_configs.items():
            if config["available"]:
                return model_id

        # No models available
        logger.warning("No embedding models available")
        return "all-MiniLM-L6-v2"  # Default fallback

    def health_check(self) -> Dict[str, Any]:
        """
        Check embedding service health.

        Returns:
            Health status information
        """
        try:
            available_models = self.list_available_models()
            loaded_models = list(self.models.keys())

            # Try to generate a test embedding
            test_successful = False
            if available_models:
                try:
                    default_model = self.get_default_model()
                    test_embedding = self.generate_single_embedding("test", default_model)
                    test_successful = len(test_embedding) > 0
                except:
                    pass

            return {
                "status": "healthy" if test_successful else "degraded",
                "available_models": len(available_models),
                "loaded_models": len(loaded_models),
                "default_model": self.get_default_model(),
                "test_embedding_successful": test_successful,
                "sentence_transformers_available": SENTENCE_TRANSFORMERS_AVAILABLE,
                "openai_available": OPENAI_AVAILABLE,
            }

        except Exception as e:
            logger.error(f"Embedding service health check failed: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}


# ========================================
# UTILITY FUNCTIONS
# ========================================


def get_embedding_service(settings: Settings = None) -> EmbeddingService:
    """Get configured embedding service instance."""
    return EmbeddingService(settings)


def batch_embed_texts(
    texts: List[str],
    model_id: str = "all-MiniLM-L6-v2",
    batch_size: int = 32,
    embedding_service: EmbeddingService = None,
) -> List[List[float]]:
    """
    Utility function to batch embed multiple texts.

    Args:
        texts: List of texts to embed
        model_id: Embedding model to use
        batch_size: Processing batch size
        embedding_service: Optional service instance

    Returns:
        List of embedding vectors
    """
    if embedding_service is None:
        embedding_service = get_embedding_service()

    return embedding_service.generate_embeddings(texts, model_id, batch_size)
