from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import logging

from .config import Settings
from .file_storage import FileStorageService
from .embeddings import EmbeddingService
from .persistence import PersistenceLayer

logger = logging.getLogger(__name__)


@dataclass
class ChunkingParams:
    strategy: str = "semantic"  # semantic|fixed (semantic is best-effort)
    sizeTokens: int = 350
    overlapTokens: int = 50
    respectHeadings: bool = True
    joinShortParagraphs: bool = True
    splitCodeBlocks: bool = True


@dataclass
class EmbeddingParams:
    modelId: str = "simple-hasher"
    normalize: bool = True
    batchSize: int = 64
    config: Optional[Dict[str, Any]] = None


class IngestionWorker:
    """Enhanced ingestion worker: parse → chunk → embed → index → tag update."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or Settings()
        self.storage = FileStorageService(self.settings)
        self.embedding_service = EmbeddingService()
        self.persistence = PersistenceLayer(self.settings)

    async def ingest_files(self, file_ids: List[str], params: Dict[str, Any]) -> Dict[str, Any]:
        """Process multiple files with chunking and embedding.

        Returns:
            Processing results with success/failure counts
        """
        chunking = self._parse_chunking_params(
            params.get("chunking") if isinstance(params, dict) else None
        )
        embedding = self._parse_embedding_params(
            params.get("embedding") if isinstance(params, dict) else None
        )

        results = []
        successful = 0
        failed = 0

        for file_id in file_ids or []:
            try:
                # Mark as processing
                try:
                    await self.storage.update_file_tags(file_id, {"status": "processing"})
                except Exception:
                    pass

                result = await self._process_one(
                    file_id=file_id, chunking=chunking, embedding=embedding
                )

                if result["success"]:
                    successful += 1
                    # Mark as embedded on success
                    try:
                        await self.storage.update_file_tags(file_id, {"status": "embedded"})
                    except Exception:
                        pass
                else:
                    failed += 1
                    # Mark as failed
                    try:
                        await self.storage.update_file_tags(file_id, {"status": "failed"})
                    except Exception:
                        pass

                results.append({"file_id": file_id, **result})

            except Exception as e:
                failed += 1
                logger.error(f"Failed to process file {file_id}: {e}")
                results.append(
                    {
                        "file_id": file_id,
                        "success": False,
                        "error": str(e),
                        "chunks_created": 0,
                        "embeddings_created": 0,
                    }
                )
                # Mark as failed
                try:
                    await self.storage.update_file_tags(file_id, {"status": "failed"})
                except Exception:
                    pass

        return {
            "success": True,
            "total_files": len(file_ids or []),
            "successful": successful,
            "failed": failed,
            "results": results,
            "chunking_params": chunking.__dict__,
            "embedding_params": embedding.__dict__,
        }

    async def _process_one(
        self, file_id: str, chunking: ChunkingParams, embedding: EmbeddingParams
    ) -> Dict[str, Any]:
        """Process a single file and return detailed results."""
        try:
            meta = await self.storage.get_file_metadata(file_id)
            if not meta:
                return {
                    "success": False,
                    "error": "File metadata not found",
                    "chunks_created": 0,
                    "embeddings_created": 0,
                }

            obj = await self.storage.retrieve_file(file_id)
            if not obj or "content" not in obj:
                return {
                    "success": False,
                    "error": "File content not found",
                    "chunks_created": 0,
                    "embeddings_created": 0,
                }

            content_bytes: bytes = obj["content"]
            filename: str = meta.get("filename") or f"file_{file_id}"

            # Extract text
            text = self._extract_text(content_bytes, filename)
            if not text:
                return {
                    "success": False,
                    "error": "No text content extracted",
                    "chunks_created": 0,
                    "embeddings_created": 0,
                }

            # Create chunks
            chunks = self._chunk_text(text, chunking)
            if not chunks:
                return {
                    "success": False,
                    "error": "No chunks created",
                    "chunks_created": 0,
                    "embeddings_created": 0,
                }

            logger.info(f"Created {len(chunks)} chunks for file {file_id}")

            # Generate embeddings
            try:
                embedder = self.embedding_service.get_embedder(
                    embedding.modelId, embedding.config or {}
                )

                # Process in batches to handle large files
                chunk_texts = [c for c, _ in chunks]
                embeddings = []

                batch_size = embedding.batchSize
                for i in range(0, len(chunk_texts), batch_size):
                    batch = chunk_texts[i : i + batch_size]
                    batch_embeddings = embedder.embed(batch)
                    embeddings.extend(batch_embeddings)

                logger.info(
                    f"Generated {len(embeddings)} embeddings for file {file_id} using model {embedding.modelId}"
                )

            except Exception as e:
                logger.error(f"Embedding generation failed for file {file_id}: {e}")
                return {
                    "success": False,
                    "error": f"Embedding failed: {str(e)}",
                    "chunks_created": len(chunks),
                    "embeddings_created": 0,
                }

            # Prepare payloads for vector store
            payloads = []
            tags = meta.get("tags") or {}
            for idx, (ctext, _off) in enumerate(chunks):
                payloads.append(
                    {
                        "id": f"{file_id}_{idx}",
                        "file_id": file_id,
                        "chunk_index": idx,
                        "text": ctext,
                        "doc_type": tags.get("docType"),
                        "status": tags.get("status"),
                        "source_filename": filename,
                        "embedding_model": embedding.modelId,
                        "chunk_params": chunking.__dict__,
                        "token_count": len(ctext.split()),  # Rough estimate
                    }
                )

            # Upsert into vector store
            try:
                self.persistence.upsert_vector_records(embeddings=embeddings, payloads=payloads)
                logger.info(f"Successfully stored {len(payloads)} vectors for file {file_id}")
            except Exception as e:
                logger.error(f"Vector store upsert failed for file {file_id}: {e}")
                return {
                    "success": False,
                    "error": f"Vector store failed: {str(e)}",
                    "chunks_created": len(chunks),
                    "embeddings_created": len(embeddings),
                }

            return {
                "success": True,
                "chunks_created": len(chunks),
                "embeddings_created": len(embeddings),
                "model_used": embedding.modelId,
                "text_length": len(text),
            }

        except Exception as e:
            logger.error(f"Unexpected error processing file {file_id}: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "chunks_created": 0,
                "embeddings_created": 0,
            }

    def _parse_chunking_params(self, raw: Optional[Dict[str, Any]]) -> ChunkingParams:
        if not isinstance(raw, dict):
            return ChunkingParams()
        return ChunkingParams(
            strategy=str(raw.get("strategy", "semantic")),
            sizeTokens=int(raw.get("sizeTokens", 350)),
            overlapTokens=int(raw.get("overlapTokens", 50)),
            respectHeadings=bool(raw.get("respectHeadings", True)),
            joinShortParagraphs=bool(raw.get("joinShortParagraphs", True)),
            splitCodeBlocks=bool(raw.get("splitCodeBlocks", True)),
        )

    def _parse_embedding_params(self, raw: Optional[Dict[str, Any]]) -> EmbeddingParams:
        if not isinstance(raw, dict):
            return EmbeddingParams()
        return EmbeddingParams(
            modelId=str(raw.get("modelId", "simple-hasher")),
            normalize=bool(raw.get("normalize", True)),
            batchSize=int(raw.get("batchSize", 64)),
            config=raw.get("config"),
        )

    def _extract_text(self, content: bytes, filename: str) -> str:
        name = (filename or "").lower()
        if name.endswith(".pdf"):
            try:
                from pdfminer.high_level import extract_text as pdf_extract_text

                # pdfminer works on file-like objects; write to memory
                import io

                return pdf_extract_text(io.BytesIO(content)) or ""
            except Exception:
                pass
        # CSV and text-like
        try:
            return content.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _chunk_text(self, text: str, p: ChunkingParams) -> List[Tuple[str, int]]:
        # Approximate tokens→chars conversion (1 token ≈ 4 chars)
        size_chars = max(100, p.sizeTokens * 4)
        overlap_chars = max(0, p.overlapTokens * 4)

        # Semantic-ish: split by double newline into paragraphs, keep headings with following paragraph
        paragraphs = [s.strip() for s in text.split("\n\n") if s.strip()]
        merged: List[str] = []
        if p.joinShortParagraphs:
            buf = ""
            for para in paragraphs:
                if len(para) < 120:
                    buf = (buf + "\n\n" + para).strip()
                else:
                    if buf:
                        merged.append(buf)
                        buf = ""
                    merged.append(para)
            if buf:
                merged.append(buf)
        else:
            merged = paragraphs

        full = "\n\n".join(merged) if p.respectHeadings else text
        chunks: List[Tuple[str, int]] = []
        start = 0
        n = len(full)
        while start < n:
            end = min(n, start + size_chars)
            chunk = full[start:end]
            chunks.append((chunk, start))
            if end >= n:
                break
            # Overlap
            start = max(0, end - overlap_chars)
            if start == 0 and end == n:
                break
        return chunks
