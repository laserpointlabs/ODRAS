import hashlib
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class EmbeddingProvider(Enum):
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    OPENAI = "openai"
    COHERE = "cohere"
    HUGGINGFACE = "huggingface"
    SIMPLE_HASHER = "simple_hasher"  # For testing


@dataclass
class EmbeddingModel:
    id: str
    provider: EmbeddingProvider
    name: str
    version: str
    dimensions: int
    max_input_tokens: int
    normalize_default: bool
    status: str = "active"  # active|deprecated
    config: Optional[Dict[str, Any]] = None


class BaseEmbedder(ABC):
    """Base class for all embedding implementations."""

    def __init__(self, model: EmbeddingModel):
        self.model = model

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model."""
        pass


class SimpleHasherEmbedder(BaseEmbedder):
    """MVP placeholder embedder.
    Produces pseudo-embeddings via hashing for end-to-end dev without model deps.
    """

    def __init__(self, model: Optional[EmbeddingModel] = None):
        if model is None:
            model = EmbeddingModel(
                id="simple-hasher",
                provider=EmbeddingProvider.SIMPLE_HASHER,
                name="Simple Hasher",
                version="1.0",
                dimensions=384,
                max_input_tokens=8192,
                normalize_default=True,
            )
        super().__init__(model)

    def embed(self, texts: List[str]) -> List[List[float]]:
        embeddings: List[List[float]] = []
        for t in texts:
            vec = [0.0] * self.model.dimensions
            for i in range(self.model.dimensions):
                h = hashlib.sha256((t + str(i)).encode()).hexdigest()
                # Map first 8 hex chars to float in [0,1)
                val = int(h[:8], 16) / 0xFFFFFFFF
                vec[i] = float(val)
            if self.model.normalize_default:
                # Simple L2 normalization
                magnitude = sum(x**2 for x in vec) ** 0.5
                if magnitude > 0:
                    vec = [x / magnitude for x in vec]
            embeddings.append(vec)
        return embeddings

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "id": self.model.id,
            "provider": self.model.provider.value,
            "name": self.model.name,
            "dimensions": self.model.dimensions,
            "max_input_tokens": self.model.max_input_tokens,
        }


class SentenceTransformersEmbedder(BaseEmbedder):
    """Sentence Transformers embedder using HuggingFace models."""

    def __init__(self, model: EmbeddingModel):
        super().__init__(model)
        self._transformer = None

    def _get_transformer(self):
        """Lazy load the transformer to avoid startup delays."""
        if self._transformer is None:
            try:
                from sentence_transformers import SentenceTransformer
                import os

                # Use local cache to avoid downloading model metadata from HuggingFace
                cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models", "embeddings")
                self._transformer = SentenceTransformer(self.model.name, cache_folder=cache_dir)
                logger.info(f"Loaded SentenceTransformer model: {self.model.name}")
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. Run: pip install sentence-transformers"
                )
            except Exception as e:
                logger.error(f"Failed to load model {self.model.name}: {e}")
                raise
        return self._transformer

    def embed(self, texts: List[str]) -> List[List[float]]:
        transformer = self._get_transformer()

        # Encode texts
        embeddings = transformer.encode(
            texts,
            normalize_embeddings=self.model.normalize_default,
            show_progress_bar=False,
        )

        # Convert to list of lists
        return embeddings.tolist()

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "id": self.model.id,
            "provider": self.model.provider.value,
            "name": self.model.name,
            "dimensions": self.model.dimensions,
            "max_input_tokens": self.model.max_input_tokens,
            "loaded": self._transformer is not None,
        }


class OpenAIEmbedder(BaseEmbedder):
    """OpenAI embeddings using their API."""

    def __init__(self, model: EmbeddingModel, api_key: Optional[str] = None):
        super().__init__(model)
        self.api_key = api_key

    def embed(self, texts: List[str]) -> List[List[float]]:
        try:
            import openai

            if self.api_key:
                openai.api_key = self.api_key

            response = openai.embeddings.create(model=self.model.name, input=texts)

            embeddings = []
            for item in response.data:
                embeddings.append(item.embedding)

            return embeddings

        except ImportError:
            raise ImportError("openai not installed. Run: pip install openai")
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            raise

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "id": self.model.id,
            "provider": self.model.provider.value,
            "name": self.model.name,
            "dimensions": self.model.dimensions,
            "max_input_tokens": self.model.max_input_tokens,
            "requires_api_key": True,
        }


# Model Registry - predefined models
DEFAULT_EMBEDDING_MODELS = [
    EmbeddingModel(
        id="simple-hasher",
        provider=EmbeddingProvider.SIMPLE_HASHER,
        name="Simple Hasher",
        version="1.0",
        dimensions=384,
        max_input_tokens=8192,
        normalize_default=True,
    ),
    EmbeddingModel(
        id="all-MiniLM-L6-v2",
        provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
        name="sentence-transformers/all-MiniLM-L6-v2",
        version="1.0",
        dimensions=384,
        max_input_tokens=256,
        normalize_default=True,
    ),
    EmbeddingModel(
        id="all-mpnet-base-v2",
        provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
        name="sentence-transformers/all-mpnet-base-v2",
        version="1.0",
        dimensions=768,
        max_input_tokens=384,
        normalize_default=True,
    ),
    EmbeddingModel(
        id="text-embedding-3-small",
        provider=EmbeddingProvider.OPENAI,
        name="text-embedding-3-small",
        version="1.0",
        dimensions=1536,
        max_input_tokens=8191,
        normalize_default=True,
    ),
    EmbeddingModel(
        id="text-embedding-3-large",
        provider=EmbeddingProvider.OPENAI,
        name="text-embedding-3-large",
        version="1.0",
        dimensions=3072,
        max_input_tokens=8191,
        normalize_default=True,
    ),
]


class EmbeddingService:
    """Service to manage embedding models and create embedders."""

    def __init__(self):
        self._models = {model.id: model for model in DEFAULT_EMBEDDING_MODELS}
        self._embedders: Dict[str, BaseEmbedder] = {}

    def get_embedder(self, model_id: str, config: Optional[Dict[str, Any]] = None) -> BaseEmbedder:
        """Get or create an embedder instance for a model."""
        if model_id not in self._embedders:
            model = self.get_model(model_id)
            if not model:
                raise ValueError(f"Model {model_id} not found")

            embedder = self._create_embedder(model, config or {})
            self._embedders[model_id] = embedder

        return self._embedders[model_id]

    def _create_embedder(self, model: EmbeddingModel, config: Dict[str, Any]) -> BaseEmbedder:
        """Create an embedder instance based on the model provider."""
        if model.provider == EmbeddingProvider.SIMPLE_HASHER:
            return SimpleHasherEmbedder(model)
        elif model.provider == EmbeddingProvider.SENTENCE_TRANSFORMERS:
            return SentenceTransformersEmbedder(model)
        elif model.provider == EmbeddingProvider.OPENAI:
            api_key = config.get("openai_api_key") or config.get("api_key")
            return OpenAIEmbedder(model, api_key)
        else:
            raise ValueError(f"Unsupported provider: {model.provider}")

    def get_model(self, model_id: str) -> Optional[EmbeddingModel]:
        """Get model by ID."""
        return self._models.get(model_id)

    def list_models(self) -> List[EmbeddingModel]:
        """List all available models."""
        return list(self._models.values())

    def add_model(self, model: EmbeddingModel) -> None:
        """Add a new model to the registry."""
        self._models[model.id] = model

    def update_model(self, model_id: str, updates: Dict[str, Any]) -> bool:
        """Update model metadata."""
        if model_id not in self._models:
            return False

        model = self._models[model_id]
        for key, value in updates.items():
            if hasattr(model, key):
                setattr(model, key, value)

        # Clear cached embedder if model updated
        if model_id in self._embedders:
            del self._embedders[model_id]

        return True

    def delete_model(self, model_id: str) -> bool:
        """Delete a model from the registry."""
        if model_id not in self._models:
            return False

        # Don't allow deleting default models
        if model_id in ["simple-hasher", "all-MiniLM-L6-v2"]:
            return False

        del self._models[model_id]
        if model_id in self._embedders:
            del self._embedders[model_id]

        return True
