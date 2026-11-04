"""Kokoro-82M backend (Apache-2.0 code and weights), loaded strictly from local files."""

from __future__ import annotations

import hashlib
import sys
import warnings
from pathlib import Path

import numpy as np

from ..config import Settings, VoiceProfile
from .base import Engine, EngineUnavailable

REPO_ID = "hexgrad/Kokoro-82M"
MODEL_FILE = "kokoro-v1_0.pth"
CONFIG_FILE = "config.json"

# Harmless deprecation notices from Kokoro's model code; they would otherwise clutter agent output.
for _pattern in (r"dropout option adds dropout", r"`torch\.nn\.utils\.weight_norm` is deprecated",
                 r"`torch\.jit\.script` is deprecated"):
    warnings.filterwarnings("ignore", message=_pattern)


def kokoro_dir(settings: Settings) -> Path:
    return settings.models_dir / "kokoro"


def base_voice_path(settings: Settings, name: str) -> Path:
    return kokoro_dir(settings) / "voices" / f"{name}.pt"


class KokoroEngine(Engine):
    name = "kokoro"
    sample_rate = 24000
    supported_voice_types = ("preset", "preset_blend")

    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.dir = kokoro_dir(settings)
        self.model = None
        self._pipelines: dict = {}
        self._voices: dict = {}

    def missing_files(self) -> list[str]:
        missing = [str(self.dir / f) for f in (CONFIG_FILE, MODEL_FILE) if not (self.dir / f).is_file()]
        try:
            import spacy.util

            if not spacy.util.is_package("en_core_web_sm"):
                missing.append("spaCy model en_core_web_sm (pip package)")
        except ImportError:
            missing.append("python package: spacy / misaki[en]")
        try:
            import kokoro  # noqa: F401
        except ImportError:
            missing.append("python package: kokoro")
        return missing

    def fingerprint(self) -> str:
        pth = self.dir / MODEL_FILE
        stat = pth.stat() if pth.is_file() else None
        try:
            from importlib.metadata import version

            kv = version("kokoro")
        except Exception:
            kv = "?"
        return f"kokoro-{kv}:{MODEL_FILE}:{stat.st_size if stat else 0}"

    def voice_fingerprint(self, profile: VoiceProfile) -> str:
        if profile.preset_file and profile.preset_file.is_file():
            return hashlib.sha256(profile.preset_file.read_bytes()).hexdigest()[:16]
        return ""

    def _pick_device(self) -> str:
        import torch

        wanted = self.settings.device
        if wanted == "cpu":
            return "cpu"
        if torch.cuda.is_available():
            if wanted == "cuda":
                return "cuda"
            free, _ = torch.cuda.mem_get_info()
            if free >= 700 * 2**20:
                return "cuda"
            print(f"[offline-voice] only {free // 2**20} MB VRAM free; using CPU", file=sys.stderr)
            return "cpu"
        if wanted == "cuda":
            raise EngineUnavailable("settings.json requests device=cuda but CUDA is not available")
        return "cpu"

    def load(self) -> None:
        if self.model is not None:
            return
        self.ensure_available()
        import torch
        from kokoro import KModel

        self.device = self._pick_device()
        self.model = KModel(repo_id=REPO_ID, config=str(self.dir / CONFIG_FILE),
                            model=str(self.dir / MODEL_FILE)).to(self.device).eval()
        torch.set_grad_enabled(False)

    def _move_to_cpu(self) -> None:
        import torch

        print("[offline-voice] GPU out of memory; continuing on CPU", file=sys.stderr)
        self.model = self.model.to("cpu")
        self.device = "cpu"
        self._pipelines.clear()
        torch.cuda.empty_cache()

    def _pipeline(self, lang_code: str):
        if lang_code not in self._pipelines:
            from kokoro import KPipeline

            self._pipelines[lang_code] = KPipeline(lang_code=lang_code, repo_id=REPO_ID, model=self.model)
        return self._pipelines[lang_code]

    def _voice_pack(self, profile: VoiceProfile):
        import torch

        key = str(profile.preset_file)
        if key not in self._voices:
            if not profile.preset_file or not profile.preset_file.is_file():
                raise EngineUnavailable(f"{profile.id}: voice file not found: {profile.preset_file}")
            self._voices[key] = torch.load(str(profile.preset_file), map_location="cpu", weights_only=True).float()
        return self._voices[key]

    def synthesize(self, text: str, profile: VoiceProfile, seed: int | None) -> np.ndarray:
        import torch

        self.load()
        if profile.voice_type not in self.supported_voice_types:
            raise EngineUnavailable(f"Kokoro cannot use voice_type '{profile.voice_type}'")
        pack = self._voice_pack(profile)

        def run() -> np.ndarray:
            if seed is not None:
                torch.manual_seed(seed)
                if self.device == "cuda":
                    torch.cuda.manual_seed_all(seed)
            chunks = []
            with torch.inference_mode():
                for result in self._pipeline(profile.lang_code)(text, voice=pack, speed=profile.speed,
                                                                split_pattern=None):
                    if result.audio is not None:
                        chunks.append(result.audio.detach().float().cpu().numpy())
            if not chunks:
                raise RuntimeError(f"Kokoro produced no audio for: {text[:80]!r}")
            return np.concatenate(chunks).astype(np.float32)

        try:
            return run()
        except torch.cuda.OutOfMemoryError:
            self._move_to_cpu()
            return run()


def blend_voices(settings: Settings, recipe: dict[str, float], out_path: Path) -> Path:
    """Create an original voicepack as a weighted average of Kokoro's built-in voicepacks."""
    import torch

    total = sum(recipe.values())
    if total <= 0:
        raise ValueError("Blend weights must be positive")
    mix = None
    for name, weight in recipe.items():
        path = base_voice_path(settings, name)
        if not path.is_file():
            raise EngineUnavailable(f"Base voice '{name}' not found at {path} (run scripts/download_models.py)")
        pack = torch.load(str(path), map_location="cpu", weights_only=True).float()
        mix = pack * (weight / total) if mix is None else mix + pack * (weight / total)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(mix.contiguous(), str(out_path))
    return out_path
