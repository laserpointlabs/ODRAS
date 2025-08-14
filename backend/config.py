"""
Configuration constants and settings for the ODRAS application.
"""
from typing import List, Dict

# Camunda configuration
CAMUNDA_BASE_URL = "http://localhost:8080"
CAMUNDA_REST_API = f"{CAMUNDA_BASE_URL}/engine-rest"

# Default personas configuration
DEFAULT_PERSONAS: List[Dict] = [
    {
        "id": "extractor",
        "name": "Extractor",
        "description": "You extract ontology-grounded entities from requirements.",
        "system_prompt": "You are an expert requirements analyst. Your role is to extract ontology-grounded entities from requirements text. Return ONLY JSON conforming to the provided schema.",
        "is_active": True
    },
    {
        "id": "reviewer",
        "name": "Reviewer", 
        "description": "You validate and correct extracted JSON to fit the schema strictly.",
        "system_prompt": "You are a quality assurance specialist. Your role is to validate and correct extracted JSON to ensure it strictly conforms to the provided schema. Return ONLY JSON conforming to the schema.",
        "is_active": True
    }
]

# Default prompts configuration
DEFAULT_PROMPTS: List[Dict] = [
    {
        "id": "default_analysis",
        "name": "Default Analysis",
        "description": "Default prompt for requirement analysis",
        "prompt_template": "Analyze the following requirement and extract key information:\n\nRequirement: {requirement_text}\nCategory: {category}\nSource: {source_file}\nIteration: {iteration}\n\nPlease provide:\n1. Extracted entities (Components, Interfaces, Functions, Processes, Conditions)\n2. Constraints and dependencies\n3. Performance requirements\n4. Quality attributes\n5. Confidence level (0.0-1.0)\n\nFormat your response as JSON.",
        "variables": ["requirement_text", "category", "source_file", "iteration"],
        "is_active": True
    }
]

# Application metadata
APP_TITLE = "ODRAS API"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "Ontology-Driven Requirements Analysis System API"
