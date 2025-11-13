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
        logger.info(f"LLMTeam initialized with provider={settings.llm_provider}, model={settings.llm_model}")

    async def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Generate a text response using the configured LLM provider.

        This is a simpler method than analyze_requirement - it's designed for
        RAG-style conversational responses, not JSON extraction.

        Args:
            system_prompt: System prompt for the LLM
            user_message: User's question/message
            context: Optional context/knowledge to include
            temperature: Temperature for response generation (0.0-1.0)

        Returns:
            Dict with 'content' (response text) and 'model' (model used)
        """
        provider = self.settings.llm_provider.lower()
        model = self.settings.llm_model

        if provider == "openai":
            return await self._generate_openai_response(
                system_prompt=system_prompt,
                user_message=user_message,
                context=context,
                temperature=temperature,
                model=model,
            )
        elif provider == "ollama":
            return await self._generate_ollama_response(
                system_prompt=system_prompt,
                user_message=user_message,
                context=context,
                temperature=temperature,
                model=model,
            )
        else:
            logger.warning(f"Unknown LLM provider: {provider}, using stub response")
            return {
                "content": f"[Stub] Response to: {user_message}",
                "model": "stub",
                "provider": provider,
            }

    async def _generate_openai_response(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate response using OpenAI API."""
        api_key = self.settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("No OpenAI API key found, returning stub response")
            return {
                "content": "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.",
                "model": model or "gpt-4o-mini",
                "provider": "openai",
            }

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add context if provided
        if context:
            messages.append({
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {user_message}",
            })
        else:
            messages.append({"role": "user", "content": user_message})

        payload = {
            "model": model or self.settings.llm_model,
            "messages": messages,
            "temperature": temperature,
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                logger.debug(f"Calling OpenAI API with model {model or self.settings.llm_model}")
                r = await client.post(url, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
                content = data["choices"][0]["message"]["content"]
                
                return {
                    "content": content,
                    "model": data.get("model", model or self.settings.llm_model),
                    "provider": "openai",
                    "usage": data.get("usage", {}),
                }
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API returned HTTP {e.response.status_code}: {e.response.text}")
            return {
                "content": f"Error calling OpenAI API: {e.response.status_code}",
                "model": model or self.settings.llm_model,
                "provider": "openai",
            }
        except httpx.TimeoutException:
            logger.error("OpenAI API request timed out")
            return {
                "content": "OpenAI API request timed out. Please try again.",
                "model": model or self.settings.llm_model,
                "provider": "openai",
            }
        except Exception as e:
            logger.error(f"Unexpected error calling OpenAI API: {e}")
            return {
                "content": f"Error generating response: {str(e)}",
                "model": model or self.settings.llm_model,
                "provider": "openai",
            }

    async def _generate_ollama_response(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate response using local Ollama API."""
        base = self.settings.ollama_url.rstrip("/")
        url = f"{base}/api/chat"

        # Build messages for Ollama
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add context if provided
        if context:
            messages.append({
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {user_message}",
            })
        else:
            messages.append({"role": "user", "content": user_message})

        payload = {
            "model": model or self.settings.llm_model or "llama3:8b-instruct",
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=120) as client:  # Longer timeout for local models
                logger.debug(f"Calling Ollama API at {url} with model {payload['model']}")
                r = await client.post(url, json=payload)
                r.raise_for_status()
                data = r.json()
                
                # Ollama returns response in 'message.content'
                content = data.get("message", {}).get("content", "")
                
                return {
                    "content": content,
                    "model": payload["model"],
                    "provider": "ollama",
                    "done": data.get("done", True),
                }
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API returned HTTP {e.response.status_code}: {e.response.text}")
            return {
                "content": f"Error calling Ollama API: {e.response.status_code}. Make sure Ollama is running and the model is available.",
                "model": payload.get("model", "unknown"),
                "provider": "ollama",
            }
        except httpx.TimeoutException:
            logger.error("Ollama API request timed out")
            return {
                "content": "Ollama API request timed out. The model may be too slow or Ollama may not be running.",
                "model": payload.get("model", "unknown"),
                "provider": "ollama",
            }
        except Exception as e:
            logger.error(f"Unexpected error calling Ollama API: {e}")
            return {
                "content": f"Error generating response: {str(e)}",
                "model": payload.get("model", "unknown"),
                "provider": "ollama",
            }

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
        for output in outputs:
            for key, value in output.items():
                if value is not None:
                    if key not in merged:
                        merged[key] = value
                    elif isinstance(value, dict) and isinstance(merged[key], dict):
                        merged[key] = {**merged[key], **value}
        return merged
