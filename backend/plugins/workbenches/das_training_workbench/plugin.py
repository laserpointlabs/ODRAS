"""
DAS Training Workbench Plugin

Plugin wrapper for DAS Training Workbench functionality.
Note: API routes are registered directly in startup/routers.py for now.
This plugin structure can be expanded later for full plugin system integration.
"""

from typing import Any, Dict
from fastapi import FastAPI

from ...interfaces.workbench_plugin import WorkbenchPlugin
from ...manifest import PluginManifest
from ....services.config import Settings
from ....services.db import DatabaseService


class DASTrainingWorkbenchPlugin(WorkbenchPlugin):
    """DAS Training Workbench plugin."""
    
    def __init__(self, manifest: PluginManifest):
        """Initialize plugin."""
        super().__init__(manifest)
        self.router = None  # Routes registered directly in routers.py
    
    async def initialize(
        self,
        app: FastAPI,
        settings: Settings,
        db: DatabaseService,
        **kwargs
    ) -> None:
        """
        Initialize the workbench plugin.
        
        Note: API routes are registered directly in startup/routers.py.
        This method can be expanded later for plugin-based registration.
        """
        # Plugin initialization - routes already registered in routers.py
        pass
    
    async def shutdown(self) -> None:
        """Shutdown the workbench plugin."""
        # Cleanup if needed
        pass
    
    def get_frontend_config(self) -> Dict[str, Any]:
        """Get frontend configuration for this workbench."""
        return {
            "panel_id": "das_training_workbench",
            "panel_title": "DAS Training",
            "icon": "school",  # or appropriate icon identifier
            "shortcut": "F11",  # Keyboard shortcut
            "position": "right",  # Panel position
            "size": {"width": 800, "height": 600},
            "dependencies": ["das_training_workbench.js"],
        }
