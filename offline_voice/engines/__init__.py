"""Local synthesis engines. Both voices share one engine instance per process."""

from __future__ import annotations

from ..config import ConfigError, Settings
from .base import Engine


def get_engine(settings: Settings) -> Engine:
    if settings.engine == "kokoro":
        from .kokoro_engine import KokoroEngine

        return KokoroEngine(settings)
    raise ConfigError(f"No engine adapter for '{settings.engine}'")
