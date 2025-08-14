import json
import os
import random
import time
from typing import Dict, List, Tuple

import httpx

from .config import Settings


class LLMTeam:
    """Simple LLM team router supporting OpenAI API and local Ollama.

    For MVP: two personas call the same model with different system prompts.
    """

    def __init__(self, settings: Settings):
        self.settings = settings

    async def analyze_requirement(
        self,
        requirement_text: str,
        ontology_json_schema: dict,
        custom_personas: List[Dict] = None,
        custom_prompts: List[Dict] = None,
    ) -> Dict:
        """Call configured personas and ensemble their JSON outputs by simple voting/merging.
        Returns JSON object adhering to `ontology_json_schema` best-effort.
        """
        # Use custom personas if provided, otherwise use default ones
        if custom_personas:
            personas = [(p["name"], p["system_prompt"]) for p in custom_personas if p.get("is_active", True)]
        else:
            # Default personas
            personas = [
                ("Extractor", "You extract ontology-grounded entities from requirements."),
                ("Reviewer", "You validate and correct extracted JSON to fit the schema strictly."),
            ]

        outputs = []
        for role, system in personas:
            response = await self._call_model(requirement_text, system, ontology_json_schema)
            if response:
                outputs.append(response)

        # Simple merge: prefer fields present in majority; otherwise take first non-null
        merged = self._merge_json(outputs)
        return merged

    async def _call_model(self, requirement_text: str, system_prompt: str, schema: dict) -> Dict:
        provider = self.settings.llm_provider.lower()
        if provider == "openai":
            return await self._call_openai(requirement_text, system_prompt, schema)
        elif provider == "ollama":
            return await self._call_ollama(requirement_text, system_prompt, schema)
        else:
            # Fallback: echo stub to enable end-to-end dev without keys
            return {
                "id": f"req-{int(time.time()*1000)}",
                "text": requirement_text,
                "state": "Draft",
                "originates_from": "unknown",
            }

    async def _call_openai(self, text: str, system_prompt: str, schema: dict) -> Dict:
        api_key = self.settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            # No key in dev: return stub
            return {
                "id": f"no-key-{int(time.time()*1000)}",
                "text": text,
                "state": "Draft",
                "originates_from": "dev",
            }

        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        model = self.settings.llm_model
        payload = {
            "model": model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt + " Return ONLY JSON conforming to the schema."},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "task": "Extract ontology-grounded JSON for requirement",
                            "schema": schema,
                            "requirement": text,
                        }
                    ),
                },
            ],
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            try:
                return json.loads(content)
            except Exception:
                return {"text": text, "state": "Draft", "originates_from": "parse-error"}

    async def _call_ollama(self, text: str, system_prompt: str, schema: dict) -> Dict:
        base = self.settings.ollama_url.rstrip("/")
        url = f"{base}/v1/chat/completions"
        payload = {
            "model": self.settings.llm_model or "llama3:8b-instruct",
            "messages": [
                {"role": "system", "content": system_prompt + " Return ONLY JSON conforming to the schema."},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "task": "Extract ontology-grounded JSON for requirement",
                            "schema": schema,
                            "requirement": text,
                        }
                    ),
                },
            ],
            "temperature": 0.2,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            try:
                return json.loads(content)
            except Exception:
                return {"text": text, "state": "Draft", "originates_from": "parse-error"}

    def _merge_json(self, outputs: List[Dict]) -> Dict:
        if not outputs:
            return {}
        merged: Dict = {}
        for obj in outputs:
            for k, v in obj.items():
                if v in (None, "", [], {}):
                    continue
                if k not in merged:
                    merged[k] = v
        return merged
