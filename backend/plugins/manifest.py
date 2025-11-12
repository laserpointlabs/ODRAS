"""
Plugin Manifest System

Handles plugin metadata, configuration, and validation.
"""

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, validator


class PluginManifest(BaseModel):
    """
    Plugin manifest containing metadata and configuration.
    
    This is loaded from manifest.yaml files in plugin directories.
    """
    
    # Core metadata
    id: str = Field(..., description="Unique plugin identifier")
    name: str = Field(..., description="Human-readable plugin name")
    version: str = Field(..., description="Plugin version (semver)")
    type: str = Field(..., description="Plugin type: workbench, das_engine, worker, middleware")
    description: str = Field(default="", description="Plugin description")
    author: str = Field(default="ODRAS Team", description="Plugin author")
    license: str = Field(default="MIT", description="License")
    homepage: Optional[str] = Field(default=None, description="Homepage URL")
    
    # Dependencies
    dependencies: List[str] = Field(default_factory=list, description="Plugin dependencies")
    python_requires: Optional[str] = Field(default=None, description="Python version requirement")
    odras_api_version: Optional[str] = Field(default=None, description="ODRAS API version requirement")
    
    # API configuration
    api_prefix: Optional[str] = Field(default=None, description="API prefix for this plugin")
    enabled: bool = Field(default=True, description="Whether plugin is enabled")
    
    # Configuration schema
    config_schema: Optional[Dict[str, Any]] = Field(default=None, description="Configuration schema")
    default_config: Optional[Dict[str, Any]] = Field(default=None, description="Default configuration")
    
    # Security and isolation
    trusted: bool = Field(default=False, description="Whether plugin is trusted")
    sandbox_enabled: bool = Field(default=True, description="Whether sandboxing is enabled")
    max_memory_mb: Optional[int] = Field(default=None, description="Maximum memory limit (MB)")
    max_execution_time_sec: Optional[int] = Field(default=None, description="Maximum execution time (seconds)")
    
    # Health and monitoring
    health_check_endpoint: Optional[str] = Field(default=None, description="Health check endpoint")
    metrics_enabled: bool = Field(default=False, description="Whether metrics are enabled")
    
    # Frontend configuration (for workbenches)
    frontend_config: Optional[Dict[str, Any]] = Field(default=None, description="Frontend configuration")
    
    @validator("type")
    def validate_type(cls, v):
        """Validate plugin type"""
        valid_types = ["workbench", "das_engine", "worker", "middleware"]
        if v not in valid_types:
            raise ValueError(f"Invalid plugin type: {v}. Must be one of {valid_types}")
        return v
    
    @validator("version")
    def validate_version(cls, v):
        """Basic semver validation"""
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError(f"Invalid version format: {v}. Must be semver (e.g., 1.2.3)")
        try:
            [int(p) for p in parts]
        except ValueError:
            raise ValueError(f"Invalid version format: {v}. Version parts must be integers")
        return v
    
    class Config:
        """Pydantic config"""
        extra = "allow"  # Allow extra fields for extensibility


def load_manifest(manifest_path: Path) -> PluginManifest:
    """
    Load plugin manifest from YAML file.
    
    Args:
        manifest_path: Path to manifest.yaml file
        
    Returns:
        PluginManifest instance
        
    Raises:
        FileNotFoundError: If manifest file doesn't exist
        ValueError: If manifest is invalid
    """
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}")
    
    with open(manifest_path, "r") as f:
        data = yaml.safe_load(f)
    
    if not data:
        raise ValueError(f"Empty manifest file: {manifest_path}")
    
    try:
        return PluginManifest(**data)
    except Exception as e:
        raise ValueError(f"Invalid manifest file {manifest_path}: {e}")


def find_manifest(plugin_dir: Path) -> Optional[Path]:
    """
    Find manifest.yaml in plugin directory.
    
    Args:
        plugin_dir: Plugin directory path
        
    Returns:
        Path to manifest.yaml if found, None otherwise
    """
    manifest_path = plugin_dir / "manifest.yaml"
    if manifest_path.exists():
        return manifest_path
    return None

