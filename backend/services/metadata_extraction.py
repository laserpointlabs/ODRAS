"""
Metadata Extraction Service.

Extracts and enriches metadata from documents including:
- Entity extraction (requirements, systems, people)
- Keyword extraction and topic modeling
- Document classification and domain detection
- Quality scoring and validation
"""

import logging
from typing import Dict, List, Optional, Any, Set, Tuple
import re
from datetime import datetime
from dataclasses import dataclass
from collections import Counter

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize, sent_tokenize

    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

from .config import Settings

logger = logging.getLogger(__name__)


@dataclass
class DocumentMetadata:
    """Comprehensive document metadata structure."""

    # Content characteristics
    word_count: int
    sentence_count: int
    paragraph_count: int
    avg_sentence_length: float

    # Extracted entities
    requirements: List[str]
    systems: List[str]

    # Topics and keywords
    keywords: List[Tuple[str, float]]
    domain: Optional[str]

    # Quality metrics
    quality_score: float

    # Classification
    document_type: str
    confidence_score: float

    # Processing metadata
    extracted_at: datetime
    extraction_method: str
    processing_time_ms: int


class MetadataExtractionService:
    """Service for extracting comprehensive metadata from documents."""

    def __init__(self, settings: Settings = None):
        """Initialize metadata extraction service."""
        self.settings = settings or Settings()

        # Pattern matching for common entities
        self.requirement_patterns = [
            r"\b(?:REQ|REQUIREMENT)[_\-\s]*(\d+(?:\.\d+)*)\b",
            r"\b(?:shall|must|should)\b.*?(?=\.|\n|$)",
        ]

        self.system_patterns = [
            r"\b([A-Z][a-zA-Z\s]*(?:System|Controller|Module))\b",
            r"\b(GPS|Navigation|Communication|Sensor)\b",
        ]

        # Document type classification patterns
        self.document_type_patterns = {
            "requirements": [r"\b(?:requirement|shall|must)\b"],
            "specification": [r"\b(?:specification|design)\b"],
            "knowledge": [r"\b(?:guide|manual|procedure)\b"],
            "reference": [r"\b(?:standard|guideline)\b"],
        }

        # Basic stopwords
        self.stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        }

        logger.info("Metadata extraction service initialized")

    def extract_requirement_entities(self, text: str) -> List[str]:
        """Extract requirement identifiers and statements."""
        requirements = set()

        for pattern in self.requirement_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if match.groups():
                    req_id = match.group(1)
                    requirements.add(req_id.strip())
                else:
                    req_text = match.group(0).strip()
                    if len(req_text) < 200:
                        requirements.add(req_text)

        return list(requirements)

    def extract_system_entities(self, text: str) -> List[str]:
        """Extract system and component names."""
        systems = set()

        for pattern in self.system_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                system_name = match.group(1) if match.groups() else match.group(0)
                systems.add(system_name.strip())

        return list(systems)

    def extract_keywords(self, text: str, max_keywords: int = 20) -> List[Tuple[str, float]]:
        """Extract keywords using TF-IDF-like scoring."""
        if not text.strip():
            return []

        try:
            # Simple tokenization
            words = re.findall(r"\b\w+\b", text.lower())

            # Filter stopwords and short words
            filtered_words = [
                word
                for word in words
                if word not in self.stop_words and len(word) > 3 and not word.isdigit()
            ]

            # Count frequencies
            word_freq = Counter(filtered_words)

            # Calculate simple TF scores
            max_freq = max(word_freq.values()) if word_freq else 1
            keyword_scores = [
                (word, count / max_freq)
                for word, count in word_freq.most_common(max_keywords * 2)
                if count > 1
            ]

            # Sort by score and return top keywords
            keyword_scores.sort(key=lambda x: x[1], reverse=True)
            return keyword_scores[:max_keywords]

        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            return []

    def classify_document_type(self, text: str) -> Tuple[str, float]:
        """Classify document type with confidence score."""
        text_lower = text.lower()
        scores = {}

        for doc_type, patterns in self.document_type_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower))
                score += matches

            # Normalize score by text length
            text_length = len(text_lower.split())
            normalized_score = score / max(text_length / 1000, 1)
            scores[doc_type] = normalized_score

        if not scores:
            return "unknown", 0.0

        # Find best match
        best_type = max(scores.keys(), key=lambda x: scores[x])
        best_score = scores[best_type]

        # Convert to confidence (0-1)
        confidence = min(best_score / 10.0, 1.0)

        return best_type, confidence

    def calculate_quality_score(self, text: str, entities: Dict[str, List[str]]) -> float:
        """Calculate document quality score."""
        if not text.strip():
            return 0.0

        quality_score = 0.0
        words = text.split()
        word_count = len(words)

        # Length factor (optimal range 1000-10000 words)
        if 1000 <= word_count <= 10000:
            quality_score += 0.3
        elif word_count >= 500:
            quality_score += 0.2

        # Entity richness
        total_entities = sum(len(entity_list) for entity_list in entities.values())
        if total_entities > 0:
            quality_score += min(total_entities / 20.0, 0.3)

        # Structure indicators
        if re.search(r"^\d+\.", text, re.MULTILINE):
            quality_score += 0.2
        if re.search(r"^\s*[-*•]", text, re.MULTILINE):
            quality_score += 0.2

        return quality_score

    def extract_comprehensive_metadata(self, text: str) -> DocumentMetadata:
        """Extract comprehensive metadata from document text."""
        start_time = datetime.now()

        if not text or not text.strip():
            return DocumentMetadata(
                word_count=0,
                sentence_count=0,
                paragraph_count=0,
                avg_sentence_length=0.0,
                requirements=[],
                systems=[],
                keywords=[],
                domain=None,
                quality_score=0.0,
                document_type="unknown",
                confidence_score=0.0,
                extracted_at=datetime.now(),
                extraction_method="pattern_based",
                processing_time_ms=0,
            )

        logger.info("Starting comprehensive metadata extraction")

        # Basic text statistics
        words = text.split()
        sentences = text.split(".") if not NLTK_AVAILABLE else sent_tokenize(text)
        paragraphs = [p for p in text.split("\n\n") if p.strip()]

        word_count = len(words)
        sentence_count = len(sentences)
        paragraph_count = len(paragraphs)
        avg_sentence_length = word_count / max(sentence_count, 1)

        # Extract entities
        requirements = self.extract_requirement_entities(text)
        systems = self.extract_system_entities(text)

        # Extract keywords and classify
        keywords = self.extract_keywords(text)
        document_type, type_confidence = self.classify_document_type(text)

        # Calculate quality score
        all_entities = {"requirements": requirements, "systems": systems}
        quality_score = self.calculate_quality_score(text, all_entities)

        # Processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        metadata = DocumentMetadata(
            word_count=word_count,
            sentence_count=sentence_count,
            paragraph_count=paragraph_count,
            avg_sentence_length=avg_sentence_length,
            requirements=requirements[:50],
            systems=systems[:30],
            keywords=keywords,
            domain=None,  # TODO: Implement domain detection
            quality_score=quality_score,
            document_type=document_type,
            confidence_score=type_confidence,
            extracted_at=datetime.now(),
            extraction_method="nlp_pattern_hybrid",
            processing_time_ms=int(processing_time),
        )

        logger.info(f"Metadata extraction completed in {processing_time:.1f}ms")
        return metadata


def get_metadata_extraction_service(
    settings: Settings = None,
) -> MetadataExtractionService:
    """Get configured metadata extraction service instance."""
    return MetadataExtractionService(settings)
