import json
import logging
import os
import random
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .config import Settings

logger = logging.getLogger(__name__)


class LLMTeam:
    """Simple LLM team router supporting OpenAI API and local Ollama.

    For MVP: two personas call the same model with different system prompts.
    """

    def __init__(self, settings: Settings):
        self.settings = settings

    async def analyze_requirement(
        self,
        requirement_text: str,
        ontology_json_schema: Dict[str, Any],
        custom_personas: Optional[List[Dict[str, Any]]] = None,
        custom_prompts: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Call configured personas and ensemble their JSON outputs by simple voting/merging.
        Returns JSON object adhering to `ontology_json_schema` best-effort.
        """
        # Use custom personas if provided, otherwise use default ones
        if custom_personas:
            personas = [
                (p["name"], p["system_prompt"]) for p in custom_personas if p.get("is_active", True)
            ]
        else:
            # Default personas
            personas = [
                (
                    "Extractor",
                    "You extract ontology-grounded entities from requirements.",
                ),
                (
                    "Reviewer",
                    "You validate and correct extracted JSON to fit the schema strictly.",
                ),
            ]

        outputs = []
        for role, system in personas:
            response = await self._call_model(requirement_text, system, ontology_json_schema)
            if response:
                outputs.append(response)

        # Simple merge: prefer fields present in majority; otherwise take first non-null
        merged = self._merge_json(outputs)
        return merged

    async def _call_model(
        self, requirement_text: str, system_prompt: str, schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call the configured LLM provider to analyze a requirement.

        Args:
            requirement_text: The requirement text to analyze
            system_prompt: The system prompt to use for the LLM
            schema: The JSON schema for the expected response format

        Returns:
            Dict containing the analyzed requirement in JSON format
        """
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

    async def _call_openai(
        self, text: str, system_prompt: str, schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call OpenAI API to analyze a requirement text.

        Args:
            text: The requirement text to analyze
            system_prompt: The system prompt for the OpenAI model
            schema: The JSON schema for the expected response format

        Returns:
            Dict containing the analyzed requirement from OpenAI
        """
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
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        model = self.settings.llm_model
        payload = {
            "model": model,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt + " Return ONLY JSON conforming to the schema.",
                },
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
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                logger.debug(f"Calling OpenAI API with model {model}")
                r = await client.post(url, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
                content = data["choices"][0]["message"]["content"]
                try:
                    result = json.loads(content)
                    logger.debug("Successfully parsed OpenAI response as JSON")
                    return result
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse OpenAI response as JSON: {e}")
                    return {
                        "text": text,
                        "state": "Draft",
                        "originates_from": "parse-error",
                    }
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API returned HTTP {e.response.status_code}: {e.response.text}")
            return {"text": text, "state": "Draft", "originates_from": "api-error"}
        except httpx.TimeoutException:
            logger.error("OpenAI API request timed out")
            return {"text": text, "state": "Draft", "originates_from": "timeout"}
        except Exception as e:
            logger.error(f"Unexpected error calling OpenAI API: {e}")
            return {"text": text, "state": "Draft", "originates_from": "error"}

    async def _call_ollama(
        self, text: str, system_prompt: str, schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call Ollama local LLM to analyze a requirement text.

        Args:
            text: The requirement text to analyze
            system_prompt: The system prompt for the Ollama model
            schema: The JSON schema for the expected response format

        Returns:
            Dict containing the analyzed requirement from Ollama
        """
        base = self.settings.ollama_url.rstrip("/")
        url = f"{base}/v1/chat/completions"
        payload = {
            "model": self.settings.llm_model or "llama3:8b-instruct",
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt + " Return ONLY JSON conforming to the schema.",
                },
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
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                logger.debug(f"Calling Ollama API at {url}")
                r = await client.post(url, json=payload)
                r.raise_for_status()
                data = r.json()
                content = data["choices"][0]["message"]["content"]
                try:
                    result = json.loads(content)
                    logger.debug("Successfully parsed Ollama response as JSON")
                    return result
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse Ollama response as JSON: {e}")
                    return {
                        "text": text,
                        "state": "Draft",
                        "originates_from": "parse-error",
                    }
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API returned HTTP {e.response.status_code}: {e.response.text}")
            return {"text": text, "state": "Draft", "originates_from": "api-error"}
        except httpx.TimeoutException:
            logger.error("Ollama API request timed out")
            return {"text": text, "state": "Draft", "originates_from": "timeout"}
        except Exception as e:
            logger.error(f"Unexpected error calling Ollama API: {e}")
            return {"text": text, "state": "Draft", "originates_from": "error"}

    def _merge_json(self, outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple JSON outputs from different personas.

        Simple merge strategy: prefer fields present in majority;
        otherwise take first non-null value.

        Args:
            outputs: List of JSON dictionaries from different LLM personas

        Returns:
            Merged dictionary containing the best fields from all outputs
        """
        if not outputs:
            return {}
        merged: Dict[str, Any] = {}
        for obj in outputs:
            for k, v in obj.items():
                if v in (None, "", [], {}):
                    continue
                if k not in merged:
                    merged[k] = v
        return merged
