"""Plugin discovery and lifecycle management.

Discovery convention: plugins_dir contains one subdirectory per plugin, each
with a plugin.py exposing a module-level `PLUGIN` (class or factory). A
failing plugin logs a warning and is skipped.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path

from plugins.base import Plugin, PluginContext

logger = logging.getLogger(__name__)


class PluginLoader:
    """Loads plugins from disk and drives their lifecycle."""

    def __init__(self) -> None:
        """Create an empty loader."""
        self._plugins: dict[str, Plugin] = {}

    def discover(self, plugins_dir: str | Path, context: PluginContext) -> list[str]:
        """Scan plugins_dir and set up every valid plugin.

        Args:
            plugins_dir: Root directory containing one subdir per plugin.
            context: PluginContext handed to each plugin's setup().

        Returns:
            Names of successfully loaded plugins.
        """
        root = Path(plugins_dir)
        if not root.is_dir():
            logger.warning("plugins_dir %s does not exist; skipping discovery", root)
            return []
        loaded: list[str] = []
        for child in sorted(root.iterdir()):
            plugin_py = child / "plugin.py"
            if not plugin_py.is_file():
                continue
            plugin = self._load_module_plugin(child.name, plugin_py)
            if plugin is None:
                continue
            try:
                plugin.setup(context)
                self._plugins[plugin.name] = plugin
                loaded.append(plugin.name)
                logger.info("plugin loaded: %s", plugin.name)
            except Exception as exc:  # noqa: BLE001 - isolation by design
                logger.warning("plugin %s setup failed: %s", child.name, exc)
        return loaded

    def _load_module_plugin(self, hint: str, plugin_py: Path) -> Plugin | None:
        """Import plugin.py and instantiate its PLUGIN symbol.

        Args:
            hint: Directory name, used as unique module name prefix.
            plugin_py: Path to the plugin module file.

        Returns:
            Plugin instance, or None when the module has no usable PLUGIN.
        """
        module_name = f"agent_loop_plugin_{hint}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, plugin_py)
            if spec is None or spec.loader is None:
                return None
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            factory = getattr(module, "PLUGIN", None)
            if factory is None:
                logger.warning("plugin %s: no PLUGIN symbol found", hint)
                return None
            return factory() if isinstance(factory, type) else factory
        except Exception as exc:  # noqa: BLE001 - isolation by design
            logger.warning("plugin %s import failed: %s", hint, exc)
            return None

    def plugins(self) -> list[Plugin]:
        """Return all loaded plugins."""
        return list(self._plugins.values())

    def teardown_all(self) -> None:
        """Tear down every plugin, isolating individual failures."""
        for plugin in self._plugins.values():
            try:
                plugin.teardown()
            except Exception as exc:  # noqa: BLE001
                logger.warning("plugin %s teardown failed: %s", plugin.name, exc)
        self._plugins.clear()
