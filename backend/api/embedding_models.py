"""
Embedding Model Management API endpoints for ODRAS
Provides REST API for managing embedding models and configurations.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field

from ..services.embeddings import EmbeddingService, EmbeddingModel, EmbeddingProvider
from ..services.config import Settings
from ..services.auth import get_user

logger = logging.getLogger(__name__)


# Pydantic models for request/response validation
class EmbeddingModelResponse(BaseModel):
    id: str
    provider: str
    name: str
    version: str
    dimensions: int
    max_input_tokens: int
    normalize_default: bool
    status: str = "active"
    config: Optional[Dict[str, Any]] = None


class CreateEmbeddingModelRequest(BaseModel):
    id: str = Field(..., description="Unique model identifier")
    provider: str = Field(..., description="Provider name")
    name: str = Field(..., description="Model name")
    version: str = Field(default="1.0", description="Model version")
    dimensions: int = Field(..., description="Embedding dimensions")
    max_input_tokens: int = Field(..., description="Maximum input tokens")
    normalize_default: bool = Field(
        default=True, description="Whether to normalize embeddings by default"
    )
    config: Optional[Dict[str, Any]] = Field(default=None, description="Additional configuration")


class UpdateEmbeddingModelRequest(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    dimensions: Optional[int] = None
    max_input_tokens: Optional[int] = None
    normalize_default: Optional[bool] = None
    status: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class EmbeddingTestRequest(BaseModel):
    model_id: str
    texts: List[str] = Field(..., min_items=1, max_items=10)
    config: Optional[Dict[str, Any]] = None


class EmbeddingTestResponse(BaseModel):
    success: bool
    model_id: str
    embeddings_count: int
    dimensions: int
    processing_time_ms: float
    error: Optional[str] = None


class ListModelsResponse(BaseModel):
    success: bool
    models: List[EmbeddingModelResponse]
    total_count: int


# Create router
router = APIRouter(prefix="/api/embedding-models", tags=["embedding-models"])


def get_embedding_service() -> EmbeddingService:
    """Dependency to get EmbeddingService instance."""
    return EmbeddingService()


@router.get("/", response_model=ListModelsResponse)
async def list_embedding_models(
    embedding_service: EmbeddingService = Depends(get_embedding_service),
):
    """
    List all available embedding models.

    Returns:
        List of embedding models with their metadata
    """
    try:
        models = embedding_service.list_models()

        model_responses = []
        for model in models:
            model_responses.append(
                EmbeddingModelResponse(
                    id=model.id,
                    provider=model.provider.value,
                    name=model.name,
                    version=model.version,
                    dimensions=model.dimensions,
                    max_input_tokens=model.max_input_tokens,
                    normalize_default=model.normalize_default,
                    status=model.status,
                    config=model.config,
                )
            )

        return ListModelsResponse(
            success=True, models=model_responses, total_count=len(model_responses)
        )

    except Exception as e:
        logger.error(f"Failed to list embedding models: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")


@router.get("/{model_id}", response_model=EmbeddingModelResponse)
async def get_embedding_model(
    model_id: str,
    embedding_service: EmbeddingService = Depends(get_embedding_service),
):
    """
    Get details of a specific embedding model.

    Args:
        model_id: Unique model identifier

    Returns:
        Embedding model details
    """
    try:
        model = embedding_service.get_model(model_id)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

        return EmbeddingModelResponse(
            id=model.id,
            provider=model.provider.value,
            name=model.name,
            version=model.version,
            dimensions=model.dimensions,
            max_input_tokens=model.max_input_tokens,
            normalize_default=model.normalize_default,
            status=model.status,
            config=model.config,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get embedding model {model_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get model: {str(e)}")


@router.post("/", response_model=EmbeddingModelResponse)
async def create_embedding_model(
    body: CreateEmbeddingModelRequest,
    user=Depends(get_user),
    authorization: Optional[str] = Header(None),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
):
    """
    Create a new embedding model.

    Args:
        body: Model creation request

    Returns:
        Created model details
    """
    # Require auth for model creation
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # Check if model already exists
        existing = embedding_service.get_model(body.id)
        if existing:
            raise HTTPException(status_code=400, detail=f"Model {body.id} already exists")

        # Validate provider
        try:
            provider = EmbeddingProvider(body.provider)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid provider: {body.provider}")

        # Create model
        model = EmbeddingModel(
            id=body.id,
            provider=provider,
            name=body.name,
            version=body.version,
            dimensions=body.dimensions,
            max_input_tokens=body.max_input_tokens,
            normalize_default=body.normalize_default,
            config=body.config,
        )

        embedding_service.add_model(model)

        return EmbeddingModelResponse(
            id=model.id,
            provider=model.provider.value,
            name=model.name,
            version=model.version,
            dimensions=model.dimensions,
            max_input_tokens=model.max_input_tokens,
            normalize_default=model.normalize_default,
            status=model.status,
            config=model.config,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create embedding model: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create model: {str(e)}")


@router.put("/{model_id}", response_model=EmbeddingModelResponse)
async def update_embedding_model(
    model_id: str,
    body: UpdateEmbeddingModelRequest,
    user=Depends(get_user),
    authorization: Optional[str] = Header(None),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
):
    """
    Update an existing embedding model.

    Args:
        model_id: Model identifier
        body: Model update request

    Returns:
        Updated model details
    """
    # Require auth for model updates
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # Check if model exists
        model = embedding_service.get_model(model_id)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

        # Prepare updates
        updates = {}
        if body.name is not None:
            updates["name"] = body.name
        if body.version is not None:
            updates["version"] = body.version
        if body.dimensions is not None:
            updates["dimensions"] = body.dimensions
        if body.max_input_tokens is not None:
            updates["max_input_tokens"] = body.max_input_tokens
        if body.normalize_default is not None:
            updates["normalize_default"] = body.normalize_default
        if body.status is not None:
            updates["status"] = body.status
        if body.config is not None:
            updates["config"] = body.config

        # Apply updates
        success = embedding_service.update_model(model_id, updates)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update model")

        # Return updated model
        updated_model = embedding_service.get_model(model_id)
        return EmbeddingModelResponse(
            id=updated_model.id,
            provider=updated_model.provider.value,
            name=updated_model.name,
            version=updated_model.version,
            dimensions=updated_model.dimensions,
            max_input_tokens=updated_model.max_input_tokens,
            normalize_default=updated_model.normalize_default,
            status=updated_model.status,
            config=updated_model.config,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update embedding model {model_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update model: {str(e)}")


@router.delete("/{model_id}")
async def delete_embedding_model(
    model_id: str,
    user=Depends(get_user),
    authorization: Optional[str] = Header(None),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
):
    """
    Delete an embedding model.

    Args:
        model_id: Model identifier

    Returns:
        Deletion result
    """
    # Require auth for model deletion
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        success = embedding_service.delete_model(model_id)
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Model {model_id} not found or cannot be deleted",
            )

        return {"success": True, "message": f"Model {model_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete embedding model {model_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete model: {str(e)}")


@router.post("/test", response_model=EmbeddingTestResponse)
async def test_embedding_model(
    body: EmbeddingTestRequest,
    embedding_service: EmbeddingService = Depends(get_embedding_service),
):
    """
    Test an embedding model with sample texts.

    Args:
        body: Test request with model ID and sample texts

    Returns:
        Test results including embeddings count and performance metrics
    """
    try:
        import time

        start_time = time.time()

        # Get embedder
        embedder = embedding_service.get_embedder(body.model_id, body.config or {})

        # Generate embeddings
        embeddings = embedder.embed(body.texts)

        end_time = time.time()
        processing_time_ms = (end_time - start_time) * 1000

        return EmbeddingTestResponse(
            success=True,
            model_id=body.model_id,
            embeddings_count=len(embeddings),
            dimensions=len(embeddings[0]) if embeddings else 0,
            processing_time_ms=processing_time_ms,
        )

    except Exception as e:
        logger.error(f"Failed to test embedding model {body.model_id}: {e}")
        return EmbeddingTestResponse(
            success=False,
            model_id=body.model_id,
            embeddings_count=0,
            dimensions=0,
            processing_time_ms=0.0,
            error=str(e),
        )


@router.get("/{model_id}/info")
async def get_model_info(
    model_id: str,
    embedding_service: EmbeddingService = Depends(get_embedding_service),
):
    """
    Get runtime information about a model (loaded status, etc.).

    Args:
        model_id: Model identifier

    Returns:
        Model runtime information
    """
    try:
        embedder = embedding_service.get_embedder(model_id)
        model_info = embedder.get_model_info()

        return {"success": True, "model_id": model_id, "info": model_info}

    except Exception as e:
        logger.error(f"Failed to get model info for {model_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get model info: {str(e)}")
