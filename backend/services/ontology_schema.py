REQUIREMENT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://example.com/schemas/requirement.schema.json",
    "type": "object",
    "required": ["id", "text", "state", "originates_from"],
    "properties": {
        "id": {"type": "string"},
        "text": {"type": "string"},
        "state": {"enum": ["Draft", "Reviewed", "Approved"]},
        "priority": {"type": "string"},
        "risk_level": {"type": "string"},
        "originates_from": {"type": "string"},
        "constrained_by": {"type": "array", "items": {"type": "string"}},
        "satisfied_by": {"type": "array", "items": {"type": "string"}},
        "verified_by": {"type": "array", "items": {"type": "string"}},
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "type", "label"],
                "properties": {
                    "id": {"type": "string"},
                    "type": {"enum": ["Component", "Interface", "Process", "Function", "Condition"]},
                    "label": {"type": "string"}
                }
            }
        },
        "relationships": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["source", "target", "type"],
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "type": {"type": "string"}
                }
            }
        }
    }
}




