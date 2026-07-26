"""Video plugin Protocol and in-process registry."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from shared.schemas.verification_job import VerificationJob
from shared.schemas.video_evidence import PluginResult


@runtime_checkable
class VideoPlugin(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def version(self) -> str: ...
    @property
    def capabilities(self) -> list[str]: ...

    def run(self, job: VerificationJob, frames: list[Any]) -> PluginResult: ...


@dataclass
class PluginRegistry:
    _plugins: dict[str, VideoPlugin] = field(default_factory=dict)

    def register(self, plugin: VideoPlugin) -> None:
        self._plugins[plugin.name] = plugin

    def get(self, name: str) -> VideoPlugin | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[dict[str, Any]]:
        return [
            {"name": p.name, "version": p.version, "capabilities": p.capabilities}
            for p in self._plugins.values()
        ]

    def resolve(self, names: list[str] | None) -> list[VideoPlugin]:
        """Return ordered list of plugins; raises ValueError for unknown names."""
        if names is None:
            return list(self._plugins.values())
        result: list[VideoPlugin] = []
        for name in names:
            plugin = self._plugins.get(name)
            if plugin is None:
                raise ValueError(f"Unknown plugin: '{name}'")
            result.append(plugin)
        return result


# Module-level singleton registry
_registry = PluginRegistry()


def get_registry() -> PluginRegistry:
    return _registry


def register_plugin(plugin: VideoPlugin) -> None:
    _registry.register(plugin)
