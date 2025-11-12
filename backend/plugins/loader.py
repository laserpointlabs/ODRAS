"""
Plugin Loader

Handles plugin discovery, loading, and validation.
"""

import importlib.util
import logging
from pathlib import Path
from typing import List, Optional

from .interfaces.base import Plugin, PluginType
from .manifest import PluginManifest, find_manifest, load_manifest
from .registry import PluginRegistry

logger = logging.getLogger(__name__)


class PluginLoader:
    """
    Plugin loader for discovering and loading plugins from filesystem.
    
    Scans plugin directories and loads plugins based on manifest.yaml files.
    """
    
    def __init__(self, registry: Optional[PluginRegistry] = None):
        """
        Initialize plugin loader.
        
        Args:
            registry: Optional plugin registry (creates new one if not provided)
        """
        self.registry = registry or PluginRegistry()
    
    def discover_plugins(
        self,
        plugin_dirs: List[Path],
        plugin_type: Optional[PluginType] = None
    ) -> List[PluginManifest]:
        """
        Discover plugins in the given directories.
        
        Args:
            plugin_dirs: List of directories to scan for plugins
            plugin_type: Optional filter by plugin type
            
        Returns:
            List of discovered plugin manifests
        """
        manifests = []
        
        for plugin_dir in plugin_dirs:
            if not plugin_dir.exists():
                logger.warning(f"Plugin directory does not exist: {plugin_dir}")
                continue
            
            # Scan for manifest.yaml files
            for path in plugin_dir.rglob("manifest.yaml"):
                try:
                    manifest = load_manifest(path)
                    
                    # Filter by type if specified
                    if plugin_type and PluginType(manifest.type) != plugin_type:
                        continue
                    
                    manifests.append(manifest)
                    logger.debug(f"Discovered plugin: {manifest.id} at {path.parent}")
                    
                except Exception as e:
                    logger.error(f"Failed to load manifest at {path}: {e}")
                    continue
        
        return manifests
    
    def load_plugin(self, manifest: PluginManifest, manifest_path: Optional[Path] = None) -> Plugin:
        """
        Load a plugin from its manifest.
        
        Args:
            manifest: Plugin manifest
            manifest_path: Optional path to manifest.yaml file (used to find plugin directory)
            
        Returns:
            Plugin instance
            
        Raises:
            ImportError: If plugin module cannot be imported
            ValueError: If plugin class cannot be found or instantiated
        """
        # Determine plugin directory from manifest path
        if manifest_path:
            plugin_dir = manifest_path.parent
        else:
            # Fallback: try standard plugin directory structure
            plugin_dir = Path(f"backend/plugins/{manifest.type}s/{manifest.id}")
        
        # Try to find plugin.py in the plugin directory
        plugin_file = plugin_dir / "plugin.py"
        
        if not plugin_file.exists():
            raise FileNotFoundError(
                f"Plugin file not found for {manifest.id}. "
                f"Expected: {plugin_file}"
            )
        
        # Load plugin module
        spec = importlib.util.spec_from_file_location(
            f"{manifest.type}_{manifest.id}",
            plugin_file
        )
        
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not create module spec for {plugin_file}")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find plugin class (convention: {Name}Plugin)
        plugin_class_name = self._get_plugin_class_name(manifest)
        plugin_class = getattr(module, plugin_class_name, None)
        
        if plugin_class is None:
            # Try alternative naming conventions
            alternatives = [
                f"{manifest.id.replace('_', ' ').title().replace(' ', '')}Plugin",
                "Plugin",
                f"{manifest.type.title()}Plugin",
            ]
            for alt_name in alternatives:
                plugin_class = getattr(module, alt_name, None)
                if plugin_class:
                    break
        
        if plugin_class is None:
            raise ValueError(
                f"Plugin class not found in {plugin_file}. "
                f"Expected class name: {plugin_class_name} or one of {alternatives}"
            )
        
        # Instantiate plugin
        try:
            plugin = plugin_class(manifest)
            return plugin
        except Exception as e:
            raise ValueError(f"Failed to instantiate plugin {manifest.id}: {e}")
    
    def _get_plugin_class_name(self, manifest: PluginManifest) -> str:
        """
        Get expected plugin class name from manifest.
        
        Args:
            manifest: Plugin manifest
            
        Returns:
            Expected class name
        """
        # Convert plugin ID to class name
        # e.g., "requirements_workbench" -> "RequirementsWorkbenchPlugin"
        parts = manifest.id.split("_")
        class_name = "".join(word.capitalize() for word in parts) + "Plugin"
        return class_name
    
    def validate_plugin(self, plugin: Plugin) -> bool:
        """
        Validate a plugin instance.
        
        Args:
            plugin: Plugin instance to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check manifest
            if not plugin.manifest:
                logger.error(f"Plugin {plugin.plugin_id} has no manifest")
                return False
            
            # Check plugin type matches manifest
            if plugin.plugin_type != PluginType(plugin.manifest.type):
                logger.error(
                    f"Plugin {plugin.plugin_id} type mismatch: "
                    f"{plugin.plugin_type} != {PluginType(plugin.manifest.type)}"
                )
                return False
            
            # Type-specific validation
            if plugin.plugin_type == PluginType.WORKBENCH:
                if not hasattr(plugin, "get_frontend_config"):
                    logger.error(f"Workbench plugin {plugin.plugin_id} missing get_frontend_config")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Plugin validation failed for {plugin.plugin_id}: {e}")
            return False
    
    def load_all_plugins(
        self,
        plugin_dirs: List[Path],
        plugin_type: Optional[PluginType] = None
    ) -> List[Plugin]:
        """
        Discover and load all plugins from directories.
        
        Args:
            plugin_dirs: List of directories to scan
            plugin_type: Optional filter by plugin type
            
        Returns:
            List of loaded plugin instances
        """
        manifests = self.discover_plugins(plugin_dirs, plugin_type)
        plugins = []
        
        # Store manifest paths for loading
        manifest_paths = {}
        for plugin_dir in plugin_dirs:
            for path in plugin_dir.rglob("manifest.yaml"):
                try:
                    manifest = load_manifest(path)
                    manifest_paths[manifest.id] = path
                except Exception:
                    continue
        
        for manifest in manifests:
            try:
                manifest_path = manifest_paths.get(manifest.id)
                plugin = self.load_plugin(manifest, manifest_path)
                
                if not self.validate_plugin(plugin):
                    logger.warning(f"Plugin {manifest.id} failed validation, skipping")
                    continue
                
                plugins.append(plugin)
                logger.info(f"✅ Loaded plugin: {manifest.id}")
                
            except Exception as e:
                logger.error(f"Failed to load plugin {manifest.id}: {e}", exc_info=True)
                continue
        
        return plugins
