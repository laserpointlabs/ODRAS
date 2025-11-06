"""
Pytest configuration and shared fixtures for ODRAS tests.
"""
import pytest

# Make fixtures from test_rag_real_world_evaluation available to other test modules
pytest_plugins = ["tests.test_rag_real_world_evaluation"]


