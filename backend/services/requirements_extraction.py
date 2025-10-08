"""
Requirements Extraction Service.

Advanced requirements extraction engine that builds on the existing document processing
infrastructure to extract and classify requirements and constraints from documents.

Features:
- Configurable keyword and pattern-based extraction
- Requirement type classification (functional, performance, safety, etc.)
- Constraint extraction (thresholds, objectives, KPCs, KPPs)
- Context-aware extraction with source traceability
- Integration with existing metadata extraction service
"""

import logging
import re
import json
import uuid
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from datetime import datetime
from dataclasses import dataclass, field
from collections import Counter, defaultdict
from enum import Enum

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize, sent_tokenize
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

from .config import Settings
from .metadata_extraction import MetadataExtractionService, DocumentMetadata

logger = logging.getLogger(__name__)


class RequirementType(Enum):
    """Standard requirement types based on systems engineering best practices."""
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    PERFORMANCE = "performance"
    SAFETY = "safety"
    SECURITY = "security"
    INTERFACE = "interface"
    OPERATIONAL = "operational"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"


class ConstraintType(Enum):
    """Standard constraint types for requirements analysis."""
    THRESHOLD = "threshold"
    OBJECTIVE = "objective"
    KPC = "kpc"  # Key Performance Criterion
    KPP = "kpp"  # Key Performance Parameter
    DESIGN = "design"
    INTERFACE = "interface"
    ENVIRONMENTAL = "environmental"


@dataclass
class ExtractedRequirement:
    """Structured representation of an extracted requirement."""
    text: str
    requirement_type: RequirementType
    confidence: float
    context: str
    source_section: Optional[str] = None
    source_page: Optional[int] = None
    source_line: Optional[int] = None
    identifier: Optional[str] = None
    title: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    priority: str = "medium"
    keywords: List[str] = field(default_factory=list)
    constraints: List['ExtractedConstraint'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedConstraint:
    """Structured representation of an extracted constraint."""
    name: str
    description: str
    constraint_type: ConstraintType
    value_type: str  # numeric, range, enumeration, boolean, text
    numeric_value: Optional[float] = None
    numeric_unit: Optional[str] = None
    range_min: Optional[float] = None
    range_max: Optional[float] = None
    range_unit: Optional[str] = None
    text_value: Optional[str] = None
    enumeration_values: Optional[List[str]] = None
    confidence: float = 0.0
    context: str = ""
    measurement_method: Optional[str] = None
    tolerance: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionConfig:
    """Configuration for requirements extraction engine."""
    # Keyword patterns for different requirement types
    functional_keywords: List[str] = field(default_factory=lambda: [
        "shall", "must", "will", "should", "function", "operate", "perform"
    ])
    performance_keywords: List[str] = field(default_factory=lambda: [
        "performance", "speed", "accuracy", "throughput", "latency", "response time",
        "efficiency", "capacity", "bandwidth", "rate"
    ])
    safety_keywords: List[str] = field(default_factory=lambda: [
        "safety", "hazard", "risk", "fail-safe", "emergency", "fault", "protection"
    ])
    security_keywords: List[str] = field(default_factory=lambda: [
        "security", "encryption", "authentication", "authorization", "access control",
        "secure", "protected", "vulnerability"
    ])
    constraint_keywords: List[str] = field(default_factory=lambda: [
        "threshold", "objective", "minimum", "maximum", "limit", "range", "between",
        "at least", "no more than", "not exceed", "greater than", "less than"
    ])
    
    # Regex patterns for structured extraction
    requirement_patterns: List[str] = field(default_factory=lambda: [
        r"\b[A-Z]+-[0-9]+\b",  # REQ-001, SYS-001
        r"\bREQ-[0-9]+\b",     # REQ-001
        r"\b[0-9]+\.[0-9]+\.[0-9]+\b",  # 3.2.1
        r"\b[A-Z]{2,4}-[0-9]{3,4}\b"    # GPS-001, COMM-1234
    ])
    constraint_patterns: List[str] = field(default_factory=lambda: [
        r"\b(minimum|maximum|at least|no more than|between)\s+[0-9]+(?:\.[0-9]+)?\b",
        r"\b[0-9]+(?:\.[0-9]+)?\s*(m|ft|kg|lb|sec|min|hr|hz|mhz|ghz|mb|gb|tb)\b",
        r"\b±\s*[0-9]+(?:\.[0-9]+)?\s*%?\b",
        r"\b[0-9]+(?:\.[0-9]+)?\s*to\s*[0-9]+(?:\.[0-9]+)?\b"
    ])
    
    # Processing options
    ignore_case: bool = True
    min_confidence: float = 0.7
    extract_context: bool = True
    context_window_size: int = 100
    extract_constraints: bool = True
    
    # Document type specific settings
    document_types: List[str] = field(default_factory=lambda: [
        "requirements", "specification", "sow", "cdd", "icd"
    ])
    section_filters: List[str] = field(default_factory=list)  # Only extract from specific sections


@dataclass
class ExtractionResult:
    """Results from requirements extraction process."""
    requirements: List[ExtractedRequirement]
    constraints: List[ExtractedConstraint]
    document_metadata: DocumentMetadata
    processing_stats: Dict[str, Any]
    extraction_config: ExtractionConfig
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class RequirementsExtractionEngine:
    """Advanced requirements extraction engine with configurable patterns and ML-based classification."""
    
    def __init__(self, settings: Settings = None, metadata_service: MetadataExtractionService = None):
        """Initialize the requirements extraction engine."""
        self.settings = settings or Settings()
        self.metadata_service = metadata_service or MetadataExtractionService(settings)
        
        # Enhanced requirement patterns
        self.requirement_markers = {
            RequirementType.FUNCTIONAL: [
                r"\b(?:shall|must|will)\s+(?:be\s+able\s+to\s+)?(?:provide|perform|execute|support|enable)",
                r"\b(?:function|functionality|operation|capability)\b",
                r"\b(?:user|system|component)\s+(?:shall|must|will)\b"
            ],
            RequirementType.PERFORMANCE: [
                r"\b(?:shall|must)\s+(?:achieve|maintain|support|provide).{0,50}(?:speed|rate|throughput|bandwidth)",
                r"\b(?:response\s+time|processing\s+time|latency)\b",
                r"\b(?:accuracy|precision|efficiency|capacity)\b.{0,20}(?:shall|must|will)"
            ],
            RequirementType.SAFETY: [
                r"\b(?:safety|hazard|risk|emergency|fault).{0,30}(?:shall|must|will)\b",
                r"\b(?:fail-safe|fault-tolerant|emergency\s+shutdown)\b",
                r"\b(?:shall|must)\s+(?:not\s+)?(?:cause|create|result\s+in).{0,30}(?:hazard|danger|harm)"
            ],
            RequirementType.SECURITY: [
                r"\b(?:security|secure|protection|encrypted?)\b.{0,30}(?:shall|must|will)\b",
                r"\b(?:authentication|authorization|access\s+control)\b",
                r"\b(?:shall|must)\s+(?:protect|secure|encrypt|authenticate)\b"
            ],
            RequirementType.INTERFACE: [
                r"\b(?:interface|connection|communication|protocol)\b.{0,30}(?:shall|must|will)\b",
                r"\b(?:shall|must)\s+(?:communicate|interface|connect)\s+(?:with|to)\b",
                r"\b(?:api|protocol|format|standard)\b.{0,20}(?:shall|must|will)"
            ]
        }
        
        # Constraint detection patterns
        self.constraint_patterns = {
            ConstraintType.THRESHOLD: [
                r"\b(?:threshold|limit|boundary)\s*:?\s*([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z/%]+)?\b",
                r"\b(?:minimum|maximum|min|max)\s+(?:of\s+)?([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z/%]+)?\b"
            ],
            ConstraintType.OBJECTIVE: [
                r"\b(?:objective|goal|target)\s*:?\s*([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z/%]+)?\b",
                r"\b(?:desired|preferred|optimal)\s+(?:value|level|rate)\s*:?\s*([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z/%]+)?\b"
            ],
            ConstraintType.KPC: [
                r"\b(?:kpc|key\s+performance\s+criterion)\s*:?\s*(.*?)(?:\.|$)",
                r"\b(?:critical\s+performance|performance\s+criterion)\b"
            ],
            ConstraintType.KPP: [
                r"\b(?:kpp|key\s+performance\s+parameter)\s*:?\s*(.*?)(?:\.|$)",
                r"\b(?:performance\s+parameter|key\s+parameter)\b"
            ]
        }
        
        # Units recognition
        self.units_patterns = {
            "time": r"\b(seconds?|minutes?|hours?|days?|ms|sec|min|hr|μs|ns)\b",
            "distance": r"\b(meters?|feet|inches?|yards?|miles?|kilometers?|m|ft|in|yd|mi|km|mm|cm)\b",
            "weight": r"\b(grams?|kilograms?|pounds?|ounces?|tons?|g|kg|lb|oz|t)\b",
            "frequency": r"\b(hertz|hz|khz|mhz|ghz|cycles?\s+per\s+second)\b",
            "data": r"\b(bytes?|bits?|kb|mb|gb|tb|pb|kbps|mbps|gbps)\b",
            "temperature": r"\b(celsius|fahrenheit|kelvin|°c|°f|°k)\b",
            "voltage": r"\b(volts?|millivolts?|v|mv)\b",
            "current": r"\b(amperes?|amps?|milliamps?|a|ma)\b",
            "power": r"\b(watts?|kilowatts?|w|kw|mw)\b",
            "pressure": r"\b(psi|pascals?|bar|atm|pa|kpa|mpa)\b",
            "percentage": r"\b%|percent(?:age)?\b"
        }
        
        logger.info("Requirements extraction engine initialized")
    
    def extract_requirements_from_document(
        self,
        document_text: str,
        config: ExtractionConfig = None,
        document_filename: str = "",
        project_id: str = ""
    ) -> ExtractionResult:
        """Extract requirements and constraints from document text."""
        start_time = datetime.now()
        config = config or ExtractionConfig()
        
        logger.info(f"Starting requirements extraction from document: {document_filename}")
        
        try:
            # First, get basic document metadata
            doc_metadata = self.metadata_service.extract_comprehensive_metadata(document_text)
            
            # Split document into sections for better context extraction
            sections = self._split_into_sections(document_text)
            
            # Extract requirements from each section
            all_requirements = []
            all_constraints = []
            
            for section_num, (section_title, section_text) in enumerate(sections):
                # Skip sections if filters are specified
                if config.section_filters and not any(
                    filter_text.lower() in section_title.lower() 
                    for filter_text in config.section_filters
                ):
                    continue
                
                section_requirements = self._extract_requirements_from_section(
                    section_text, section_title, config, section_num + 1
                )
                all_requirements.extend(section_requirements)
                
                if config.extract_constraints:
                    section_constraints = self._extract_constraints_from_section(
                        section_text, section_title, config, section_num + 1
                    )
                    all_constraints.extend(section_constraints)
            
            # Post-process and deduplicate
            all_requirements = self._post_process_requirements(all_requirements, config)
            all_constraints = self._post_process_constraints(all_constraints, config)
            
            # Calculate processing statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            processing_stats = {
                "processing_time_seconds": processing_time,
                "requirements_extracted": len(all_requirements),
                "constraints_extracted": len(all_constraints),
                "sections_processed": len(sections),
                "high_confidence_requirements": len([r for r in all_requirements if r.confidence >= 0.8]),
                "medium_confidence_requirements": len([r for r in all_requirements if 0.6 <= r.confidence < 0.8]),
                "low_confidence_requirements": len([r for r in all_requirements if r.confidence < 0.6]),
            }
            
            result = ExtractionResult(
                requirements=all_requirements,
                constraints=all_constraints,
                document_metadata=doc_metadata,
                processing_stats=processing_stats,
                extraction_config=config
            )
            
            logger.info(f"Requirements extraction completed: {len(all_requirements)} requirements, "
                       f"{len(all_constraints)} constraints in {processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Error during requirements extraction: {str(e)}")
            return ExtractionResult(
                requirements=[],
                constraints=[],
                document_metadata=DocumentMetadata(
                    word_count=0, sentence_count=0, paragraph_count=0, avg_sentence_length=0.0,
                    requirements=[], systems=[], keywords=[], domain=None,
                    quality_score=0.0, document_type="unknown", confidence_score=0.0,
                    extracted_at=datetime.now(), extraction_method="failed", processing_time_ms=0
                ),
                processing_stats={"processing_time_seconds": 0, "error": str(e)},
                extraction_config=config,
                errors=[str(e)]
            )
    
    def _split_into_sections(self, text: str) -> List[Tuple[str, str]]:
        """Split document into logical sections based on headers."""
        sections = []
        current_section = ""
        current_title = "Introduction"
        
        lines = text.split('\n')
        
        for line in lines:
            # Detect section headers (various formats)
            header_match = re.match(r'^(\d+(?:\.\d+)*\.?\s+.*)|^([A-Z][A-Z\s]{10,})|^(#{1,6}\s+.*)', line.strip())
            
            if header_match and len(line.strip()) > 0 and len(current_section.strip()) > 50:
                # Save previous section
                if current_section.strip():
                    sections.append((current_title, current_section))
                
                # Start new section
                current_title = line.strip()
                current_section = ""
            else:
                current_section += line + "\n"
        
        # Add final section
        if current_section.strip():
            sections.append((current_title, current_section))
        
        # If no sections found, treat entire document as one section
        if not sections:
            sections = [("Document", text)]
        
        return sections
    
    def _extract_requirements_from_section(
        self,
        section_text: str,
        section_title: str,
        config: ExtractionConfig,
        section_number: int
    ) -> List[ExtractedRequirement]:
        """Extract requirements from a document section."""
        requirements = []
        
        # Split into sentences for requirement-level extraction
        sentences = sent_tokenize(section_text) if NLTK_AVAILABLE else section_text.split('.')
        
        for sentence_idx, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(sentence) < 20:  # Skip very short sentences
                continue
            
            # Check if sentence contains requirement indicators
            requirement_score, req_type = self._classify_requirement_sentence(sentence, config)
            
            if requirement_score >= config.min_confidence:
                # Extract potential identifier
                identifier = self._extract_requirement_identifier(sentence)
                
                # Extract context
                context = self._extract_context(sentences, sentence_idx, config.context_window_size) if config.extract_context else sentence
                
                # Classify category/subcategory
                category, subcategory = self._classify_requirement_category(sentence)
                
                # Extract keywords that triggered the match
                keywords = self._extract_matching_keywords(sentence, config)
                
                requirement = ExtractedRequirement(
                    text=sentence,
                    requirement_type=req_type,
                    confidence=requirement_score,
                    context=context,
                    source_section=section_title,
                    source_line=sentence_idx + 1,
                    identifier=identifier,
                    category=category,
                    subcategory=subcategory,
                    keywords=keywords,
                    metadata={
                        "section_number": section_number,
                        "sentence_index": sentence_idx,
                        "extraction_method": "pattern_ml_hybrid"
                    }
                )
                
                requirements.append(requirement)
        
        return requirements
    
    def _extract_constraints_from_section(
        self,
        section_text: str,
        section_title: str,
        config: ExtractionConfig,
        section_number: int
    ) -> List[ExtractedConstraint]:
        """Extract constraints from a document section."""
        constraints = []
        
        # Look for constraint patterns in the text
        for constraint_type, patterns in self.constraint_patterns.items():
            for pattern in patterns:
                flags = re.IGNORECASE if config.ignore_case else 0
                matches = re.finditer(pattern, section_text, flags)
                
                for match in matches:
                    constraint = self._parse_constraint_match(
                        match, constraint_type, section_text, section_title, section_number
                    )
                    if constraint:
                        constraints.append(constraint)
        
        # Extract numeric constraints with units
        numeric_constraints = self._extract_numeric_constraints(
            section_text, section_title, section_number
        )
        constraints.extend(numeric_constraints)
        
        return constraints
    
    def _classify_requirement_sentence(self, sentence: str, config: ExtractionConfig) -> Tuple[float, RequirementType]:
        """Classify a sentence as a requirement and determine its type."""
        max_confidence = 0.0
        best_type = RequirementType.FUNCTIONAL
        
        sentence_lower = sentence.lower()
        
        # Check for modal verbs (shall, must, will, should)
        modal_score = 0.0
        if re.search(r'\b(shall|must)\b', sentence_lower):
            modal_score = 0.9
        elif re.search(r'\b(will|should)\b', sentence_lower):
            modal_score = 0.7
        elif re.search(r'\b(may|might|could)\b', sentence_lower):
            modal_score = 0.4
        
        # Check requirement type patterns
        for req_type, patterns in self.requirement_markers.items():
            type_score = 0.0
            
            for pattern in patterns:
                if re.search(pattern, sentence_lower):
                    type_score = max(type_score, 0.8)
            
            # Check for type-specific keywords
            type_keywords = {
                RequirementType.FUNCTIONAL: config.functional_keywords,
                RequirementType.PERFORMANCE: config.performance_keywords,
                RequirementType.SAFETY: config.safety_keywords,
                RequirementType.SECURITY: config.security_keywords,
            }
            
            if req_type in type_keywords:
                for keyword in type_keywords[req_type]:
                    if keyword.lower() in sentence_lower:
                        type_score = max(type_score, 0.6)
            
            # Combine modal and type scores
            combined_score = modal_score * 0.4 + type_score * 0.6
            
            if combined_score > max_confidence:
                max_confidence = combined_score
                best_type = req_type
        
        # Boost confidence if sentence has good requirement structure
        if self._has_requirement_structure(sentence):
            max_confidence = min(max_confidence + 0.1, 1.0)
        
        return max_confidence, best_type
    
    def _has_requirement_structure(self, sentence: str) -> bool:
        """Check if sentence has typical requirement structure."""
        sentence_lower = sentence.lower()
        
        # Check for subject-modal-action structure
        structure_patterns = [
            r'\b(?:the\s+)?(?:system|component|user|interface)\s+(?:shall|must|will)\s+\w+',
            r'\b(?:shall|must|will)\s+(?:be\s+)?(?:able\s+to\s+)?(?:provide|perform|support|maintain)',
            r'\b\w+\s+(?:shall|must|will)\s+(?:not\s+)?(?:exceed|be\s+less\s+than|be\s+greater\s+than)'
        ]
        
        return any(re.search(pattern, sentence_lower) for pattern in structure_patterns)
    
    def _extract_requirement_identifier(self, sentence: str) -> Optional[str]:
        """Extract requirement identifier from sentence."""
        # Check for common ID patterns
        id_patterns = [
            r'\b([A-Z]+-[0-9]+)\b',
            r'\b(REQ-[0-9]+)\b',
            r'\b([A-Z]{2,4}-[0-9]{3,4})\b',
            r'\b([0-9]+\.[0-9]+\.[0-9]+)\b'
        ]
        
        for pattern in id_patterns:
            match = re.search(pattern, sentence)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_context(self, sentences: List[str], target_idx: int, window_size: int) -> str:
        """Extract context around a target sentence."""
        start_idx = max(0, target_idx - window_size // 2)
        end_idx = min(len(sentences), target_idx + window_size // 2 + 1)
        
        context_sentences = sentences[start_idx:end_idx]
        return ' '.join(context_sentences)
    
    def _classify_requirement_category(self, sentence: str) -> Tuple[Optional[str], Optional[str]]:
        """Classify requirement into category and subcategory."""
        sentence_lower = sentence.lower()
        
        # Category mapping based on domain keywords
        category_keywords = {
            "Navigation": ["navigation", "gps", "position", "location", "coordinates", "waypoint"],
            "Communication": ["communication", "radio", "transmit", "receive", "signal", "frequency"],
            "Power": ["power", "battery", "electrical", "voltage", "current", "energy"],
            "Safety": ["safety", "hazard", "emergency", "fault", "fail-safe", "protection"],
            "Performance": ["performance", "speed", "accuracy", "efficiency", "throughput"],
            "Interface": ["interface", "connection", "protocol", "api", "format"],
            "Display": ["display", "screen", "indicator", "visual", "gui", "hmi"],
            "Control": ["control", "command", "operate", "manual", "automatic"],
            "Maintenance": ["maintenance", "service", "repair", "diagnostic", "test"]
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in sentence_lower for keyword in keywords):
                return category, None  # Could implement subcategory logic
        
        return None, None
    
    def _extract_matching_keywords(self, sentence: str, config: ExtractionConfig) -> List[str]:
        """Extract keywords that triggered the requirement match."""
        sentence_lower = sentence.lower()
        keywords = []
        
        # Check all keyword lists
        all_keywords = (
            config.functional_keywords + config.performance_keywords +
            config.safety_keywords + config.security_keywords +
            config.constraint_keywords
        )
        
        for keyword in all_keywords:
            if keyword.lower() in sentence_lower:
                keywords.append(keyword)
        
        return list(set(keywords))  # Remove duplicates
    
    def _parse_constraint_match(
        self,
        match: re.Match,
        constraint_type: ConstraintType,
        section_text: str,
        section_title: str,
        section_number: int
    ) -> Optional[ExtractedConstraint]:
        """Parse a regex match into a structured constraint."""
        full_match = match.group(0)
        groups = match.groups()
        
        # Extract context around the match
        match_start = match.start()
        match_end = match.end()
        context_start = max(0, match_start - 100)
        context_end = min(len(section_text), match_end + 100)
        context = section_text[context_start:context_end]
        
        constraint = ExtractedConstraint(
            name=self._generate_constraint_name(full_match, constraint_type),
            description=full_match,
            constraint_type=constraint_type,
            value_type="text",  # Will be refined below
            confidence=0.7,
            context=context
        )
        
        # Try to extract numeric values
        if groups and len(groups) >= 1:
            value_str = groups[0]
            if value_str:
                try:
                    numeric_value = float(value_str)
                    constraint.numeric_value = numeric_value
                    constraint.value_type = "numeric"
                    
                    # Extract unit if present
                    if len(groups) >= 2 and groups[1]:
                        constraint.numeric_unit = groups[1]
                    else:
                        # Look for unit in the surrounding context
                        unit = self._extract_unit_from_context(context)
                        if unit:
                            constraint.numeric_unit = unit
                            
                except ValueError:
                    constraint.text_value = value_str
                    constraint.value_type = "text"
        
        return constraint
    
    def _extract_numeric_constraints(
        self,
        section_text: str,
        section_title: str,
        section_number: int
    ) -> List[ExtractedConstraint]:
        """Extract numeric constraints with units from text."""
        constraints = []
        
        # Pattern for numeric values with units and context
        numeric_pattern = r'(?:minimum|maximum|min|max|at least|no more than|between|±|tolerance|accuracy|precision)[\s:]*([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z/%]+)?'
        
        matches = re.finditer(numeric_pattern, section_text, re.IGNORECASE)
        
        for match in matches:
            value_str = match.group(1)
            unit_str = match.group(2) if match.group(2) else None
            
            try:
                numeric_value = float(value_str)
                
                # Determine constraint type based on context
                context_before = section_text[max(0, match.start() - 50):match.start()]
                constraint_type = self._infer_constraint_type(context_before)
                
                constraint = ExtractedConstraint(
                    name=f"Numeric constraint: {match.group(0)}",
                    description=match.group(0),
                    constraint_type=constraint_type,
                    value_type="numeric",
                    numeric_value=numeric_value,
                    numeric_unit=unit_str,
                    confidence=0.6,
                    context=section_text[max(0, match.start() - 100):min(len(section_text), match.end() + 100)]
                )
                
                constraints.append(constraint)
                
            except ValueError:
                continue
        
        return constraints
    
    def _infer_constraint_type(self, context: str) -> ConstraintType:
        """Infer constraint type from surrounding context."""
        context_lower = context.lower()
        
        if any(word in context_lower for word in ["threshold", "limit", "boundary"]):
            return ConstraintType.THRESHOLD
        elif any(word in context_lower for word in ["objective", "goal", "target"]):
            return ConstraintType.OBJECTIVE
        elif "kpc" in context_lower or "key performance criterion" in context_lower:
            return ConstraintType.KPC
        elif "kpp" in context_lower or "key performance parameter" in context_lower:
            return ConstraintType.KPP
        else:
            return ConstraintType.DESIGN  # Default
    
    def _generate_constraint_name(self, match_text: str, constraint_type: ConstraintType) -> str:
        """Generate a descriptive name for a constraint."""
        base_name = constraint_type.value.replace('_', ' ').title()
        
        # Try to extract a more specific name from the match
        if len(match_text) < 50:
            return f"{base_name}: {match_text}"
        else:
            return f"{base_name}: {match_text[:47]}..."
    
    def _extract_unit_from_context(self, context: str) -> Optional[str]:
        """Extract measurement unit from context."""
        for unit_type, pattern in self.units_patterns.items():
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                return match.group(0).lower()
        return None
    
    def _post_process_requirements(
        self,
        requirements: List[ExtractedRequirement],
        config: ExtractionConfig
    ) -> List[ExtractedRequirement]:
        """Post-process and deduplicate extracted requirements."""
        # Remove duplicates based on text similarity
        unique_requirements = []
        seen_texts = set()
        
        for req in requirements:
            # Simple deduplication based on normalized text
            normalized_text = re.sub(r'\s+', ' ', req.text.lower().strip())
            if normalized_text not in seen_texts:
                seen_texts.add(normalized_text)
                unique_requirements.append(req)
        
        # Sort by confidence and source location
        unique_requirements.sort(key=lambda x: (-x.confidence, x.source_section or "", x.source_line or 0))
        
        return unique_requirements
    
    def _post_process_constraints(
        self,
        constraints: List[ExtractedConstraint],
        config: ExtractionConfig
    ) -> List[ExtractedConstraint]:
        """Post-process and deduplicate extracted constraints."""
        # Simple deduplication
        unique_constraints = []
        seen_descriptions = set()
        
        for constraint in constraints:
            if constraint.description not in seen_descriptions:
                seen_descriptions.add(constraint.description)
                unique_constraints.append(constraint)
        
        # Sort by confidence
        unique_constraints.sort(key=lambda x: -x.confidence)
        
        return unique_constraints


def get_requirements_extraction_engine(settings: Settings = None) -> RequirementsExtractionEngine:
    """Factory function to get requirements extraction engine instance."""
    return RequirementsExtractionEngine(settings)


# Example usage and testing
if __name__ == "__main__":
    # Test the extraction engine
    engine = RequirementsExtractionEngine()
    
    sample_text = """
    3.1 Navigation Requirements
    
    REQ-001: The GPS navigation system shall provide position accuracy of ±3 meters.
    The system must maintain this accuracy under normal operating conditions.
    
    REQ-002: The navigation system shall update position data at a rate of 10 Hz minimum.
    Performance objective: Target update rate should be 20 Hz for optimal operation.
    
    3.2 Safety Requirements
    
    REQ-003: The system shall implement fail-safe mechanisms in case of GPS signal loss.
    Emergency threshold: Position uncertainty shall not exceed 10 meters.
    
    KPC-001: Critical performance criterion - Navigation accuracy must be maintained
    within 95% confidence interval during flight operations.
    """
    
    result = engine.extract_requirements_from_document(sample_text)
    
    print(f"Extracted {len(result.requirements)} requirements:")
    for req in result.requirements:
        print(f"  {req.identifier or 'UNID'}: {req.text[:100]}... "
              f"(Type: {req.requirement_type.value}, Confidence: {req.confidence:.2f})")
    
    print(f"\nExtracted {len(result.constraints)} constraints:")
    for constraint in result.constraints:
        print(f"  {constraint.name}: {constraint.description[:100]}... "
              f"(Type: {constraint.constraint_type.value}, Confidence: {constraint.confidence:.2f})")
