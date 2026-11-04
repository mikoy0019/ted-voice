"""Engine interface shared by every local TTS backend."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from ..config import Settings, VoiceProfile


class EngineUnavailable(Exception):
    """Model files or dependencies are missing; the engine cannot run offline."""


class Engine(ABC):
    name: str = "base"
    sample_rate: int = 24000
    supported_voice_types: tuple[str, ...] = ()

    def __init__(self, settings: Settings):
        self.settings = settings
        self.device = "cpu"

    @abstractmethod
    def missing_files(self) -> list[str]:
        """Files that must exist locally for offline inference."""

    @abstractmethod
    def fingerprint(self) -> str:
        """Identifies model + engine version so cached audio is invalidated when they change."""

    @abstractmethod
    def load(self) -> None:
        """Load the model into memory (once per process)."""

    @abstractmethod
    def synthesize(self, text: str, profile: VoiceProfile, seed: int | None) -> np.ndarray:
        """Return mono float32 audio at self.sample_rate."""

    def voice_fingerprint(self, profile: VoiceProfile) -> str:
        return ""

    def ensure_available(self) -> None:
        missing = self.missing_files()
        if missing:
            raise EngineUnavailable("Offline model files are missing (run setup.bat):\n  " + "\n  ".join(missing))
