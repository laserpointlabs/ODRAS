import json
from typing import Dict, List, Optional

import httpx


class PersonaManager:
    """Service for managing LLM personas and prompts."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")

    async def get_active_personas(self) -> List[Dict]:
        """Get all active personas from the API."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/personas")
                if response.status_code == 200:
                    data = response.json()
                    return [p for p in data.get("personas", []) if p.get("is_active", True)]
                else:
                    return []
        except Exception as e:
            print(f"Error fetching personas: {e}")
            return []

    async def get_active_prompts(self) -> List[Dict]:
        """Get all active prompts from the API."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/prompts")
                if response.status_code == 200:
                    data = response.json()
                    return [p for p in data.get("prompts", []) if p.get("is_active", True)]
                else:
                    return []
        except Exception as e:
            print(f"Error fetching prompts: {e}")
            return []

    async def create_persona(self, persona: Dict) -> Optional[Dict]:
        """Create a new persona."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.base_url}/api/personas",
                    json=persona,
                    headers={"Content-Type": "application/json"},
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"Error creating persona: {response.status_code}")
                    return None
        except Exception as e:
            print(f"Error creating persona: {e}")
            return None

    async def update_persona(self, persona_id: str, persona: Dict) -> Optional[Dict]:
        """Update an existing persona."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.put(
                    f"{self.base_url}/api/personas/{persona_id}",
                    json=persona,
                    headers={"Content-Type": "application/json"},
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"Error updating persona: {response.status_code}")
                    return None
        except Exception as e:
            print(f"Error updating persona: {e}")
            return None

    async def delete_persona(self, persona_id: str) -> bool:
        """Delete a persona."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.delete(f"{self.base_url}/api/personas/{persona_id}")
                return response.status_code == 200
        except Exception as e:
            print(f"Error deleting persona: {e}")
            return False

    async def test_prompt(self, prompt_id: str, test_variables: Dict) -> Optional[Dict]:
        """Test a prompt with sample variables."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.base_url}/api/prompts/{prompt_id}/test",
                    json=test_variables,
                    headers={"Content-Type": "application/json"},
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"Error testing prompt: {response.status_code}")
                    return None
        except Exception as e:
            print(f"Error testing prompt: {e}")
            return None

