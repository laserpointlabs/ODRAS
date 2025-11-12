"""
Plugin Interfaces

Defines abstract base classes for all plugin types.
"""

from .base import Plugin, PluginType
from .workbench_plugin import WorkbenchPlugin
from .das_plugin import DASEnginePlugin
from .worker_plugin import WorkerPlugin

__all__ = [
    "Plugin",
    "PluginType",
    "WorkbenchPlugin",
    "DASEnginePlugin",
    "WorkerPlugin",
]

