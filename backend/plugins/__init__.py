"""
ODRAS Plugin System

Provides plugin infrastructure for workbenches, DAS engines, workers, and middleware.
"""

from .interfaces.base import Plugin, PluginType
from .interfaces.workbench_plugin import WorkbenchPlugin
from .interfaces.das_plugin import DASEnginePlugin
from .interfaces.worker_plugin import WorkerPlugin
from .registry import PluginRegistry
from .loader import PluginLoader
from .manifest import PluginManifest, load_manifest

__all__ = [
    "Plugin",
    "PluginType",
    "WorkbenchPlugin",
    "DASEnginePlugin",
    "WorkerPlugin",
    "PluginRegistry",
    "PluginLoader",
    "PluginManifest",
    "load_manifest",
]

