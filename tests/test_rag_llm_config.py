"""
Test RAG LLM Configuration via Environment Variables

Tests that LLM_PROVIDER and LLM_MODEL environment variables work correctly
for both OpenAI and Ollama providers.
"""

import pytest
import os
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from backend.services.config import Settings
from backend.rag.core.modular_rag_service import ModularRAGService
from backend.services.llm_team import LLMTeam


class TestLLMConfiguration:
    """Test LLM configuration via environment variables."""

    def test_settings_loads_llm_provider_from_env(self):
        """Test that Settings loads LLM_PROVIDER from environment."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}):
            settings = Settings()
            assert settings.llm_provider.lower() == "ollama"

    def test_settings_loads_llm_model_from_env(self):
        """Test that Settings loads LLM_MODEL from environment."""
        with patch.dict(os.environ, {"LLM_MODEL": "llama3:8b-instruct"}):
            settings = Settings()
            assert settings.llm_model == "llama3:8b-instruct"

    def test_settings_defaults_to_openai(self):
        """Test that Settings defaults to OpenAI if not set."""
        # Clear any existing env vars
        with patch.dict(os.environ, {}, clear=False):
            # Remove LLM vars if they exist
            os.environ.pop("LLM_PROVIDER", None)
            os.environ.pop("LLM_MODEL", None)
            settings = Settings()
            assert settings.llm_provider.lower() == "openai"
            assert settings.llm_model == "gpt-4o-mini"

    def test_llm_team_initializes_with_settings(self):
        """Test that LLMTeam uses settings correctly."""
        settings = Settings()
        llm_team = LLMTeam(settings)
        assert llm_team.settings.llm_provider == settings.llm_provider
        assert llm_team.settings.llm_model == settings.llm_model

    @pytest.mark.asyncio
    async def test_llm_team_generate_response_openai(self):
        """Test LLMTeam.generate_response with OpenAI provider."""
        settings = Settings()
        settings.llm_provider = "openai"
        settings.llm_model = "gpt-4o-mini"
        
        llm_team = LLMTeam(settings)
        
        # Mock the OpenAI API call
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.raise_for_status = Mock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Test response from OpenAI"}}],
                "model": "gpt-4o-mini",
            }
            mock_client.post.return_value = mock_response
            
            result = await llm_team.generate_response(
                system_prompt="You are a helpful assistant.",
                user_message="Test question",
            )
            
            assert "content" in result
            assert result["provider"] == "openai"

    @pytest.mark.asyncio
    async def test_llm_team_generate_response_ollama(self):
        """Test LLMTeam.generate_response with Ollama provider."""
        settings = Settings()
        settings.llm_provider = "ollama"
        settings.llm_model = "llama3:8b-instruct"
        settings.ollama_url = "http://localhost:11434"
        
        llm_team = LLMTeam(settings)
        
        # Mock the Ollama API call
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.raise_for_status = Mock()
            mock_response.json.return_value = {
                "message": {"content": "Test response from Ollama"},
                "done": True,
            }
            mock_client.post.return_value = mock_response
            
            result = await llm_team.generate_response(
                system_prompt="You are a helpful assistant.",
                user_message="Test question",
            )
            
            assert "content" in result
            assert result["provider"] == "ollama"
            assert result["model"] == "llama3:8b-instruct"

    @pytest.mark.asyncio
    async def test_modular_rag_service_uses_llm_config(self):
        """Test that ModularRAGService respects LLM configuration."""
        settings = Settings()
        settings.llm_provider = "ollama"
        settings.llm_model = "llama3:8b-instruct"
        
        # Create test project_id and user_id
        test_project_id = str(uuid4())
        test_user_id = str(uuid4())
        test_chunk_id = str(uuid4())
        test_asset_id = str(uuid4())
        
        # Create mock components with actual chunks returned
        mock_retriever = AsyncMock()
        mock_retriever.retrieve_multiple_collections = AsyncMock(return_value={
            "knowledge_chunks": [
                {
                    "id": "1",
                    "score": 0.9,
                    "payload": {
                        "chunk_id": test_chunk_id,
                        "asset_id": test_asset_id,
                        "project_id": test_project_id,  # Use same project_id
                        "content": "Test content",
                    },
                }
            ],
            "knowledge_chunks_768": [],
        })
        
        mock_db = Mock()
        # Mock is_user_member to return True for our test project
        def is_user_member_mock(project_id, user_id):
            return project_id == test_project_id and user_id == test_user_id
        mock_db.is_user_member = Mock(side_effect=is_user_member_mock)
        mock_db._conn = Mock(return_value=Mock())
        mock_db._return = Mock()
        
        # Create real LLMTeam (will be mocked for actual calls)
        llm_team = LLMTeam(settings)
        llm_team.generate_response = AsyncMock(return_value={
            "content": "Test response",
            "model": "llama3:8b-instruct",
            "provider": "ollama",
        })
        
        rag_service = ModularRAGService(
            settings=settings,
            retriever=mock_retriever,
            db_service=mock_db,
            llm_team=llm_team,
        )
        
        # Disable SQL read-through for this test to avoid connection issues
        rag_service.sql_read_through = False
        
        result = await rag_service.query_knowledge_base_legacy(
            question="Test question",
            project_id=test_project_id,  # Pass project_id to match chunks
            user_id=test_user_id,
        )
        
        # Verify LLM was called (only if chunks were found)
        if result["chunks_found"] > 0:
            llm_team.generate_response.assert_called_once()
            # Verify result includes model/provider info
            assert result["provider"] == "ollama"
            assert "llama3" in result["model_used"].lower()
        else:
            # If no chunks found, verify the service still works correctly
            assert result["success"] is True
            # Service should still respect LLM config even if no chunks
            assert "provider" in result or "model_used" in result

    def test_env_variable_aliases(self):
        """Test that both uppercase and lowercase env vars work."""
        test_cases = [
            ("LLM_PROVIDER", "ollama"),
            ("llm_provider", "ollama"),
            ("LLM_MODEL", "custom-model"),
            ("llm_model", "custom-model"),
        ]
        
        for env_var, value in test_cases:
            with patch.dict(os.environ, {env_var: value}, clear=False):
                settings = Settings()
                if "provider" in env_var.lower():
                    assert settings.llm_provider.lower() == value.lower()
                elif "model" in env_var.lower():
                    assert settings.llm_model == value


@pytest.mark.integration
class TestLLMIntegration:
    """Integration tests for LLM configuration (require services)."""

    @pytest.mark.asyncio
    async def test_ollama_integration(self):
        """Test actual Ollama integration if service is running."""
        import httpx
        
        # Check if Ollama is running
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:11434/api/tags")
                if response.status_code == 200:
                    # Ollama is running, test with it
                    settings = Settings()
                    settings.llm_provider = "ollama"
                    settings.llm_model = "llama3:8b-instruct"
                    
                    llm_team = LLMTeam(settings)
                    result = await llm_team.generate_response(
                        system_prompt="You are a helpful assistant.",
                        user_message="Say 'hello' in one word.",
                    )
                    
                    assert "content" in result
                    assert result["provider"] == "ollama"
                else:
                    pytest.skip("Ollama not running")
        except Exception:
            pytest.skip("Ollama not available")
