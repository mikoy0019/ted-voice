"""Load and validate settings.json, voices.json and the two voice profiles."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .paths import home, resolve_home_path

VOICE_IDS = ("voice_1", "voice_2")
SUPPORTED_ENGINES = ("kokoro",)
VOICE_TYPES = ("preset", "preset_blend", "reference_clone")


class ConfigError(Exception):
    """Raised when configuration is missing or invalid."""


def _read_json(path: Path) -> dict:
    if not path.is_file():
        raise ConfigError(f"Missing config file: {path}")
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in {path}: {e}") from e


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    tmp.replace(path)


def settings_path() -> Path:
    return home() / "config" / "settings.json"


def voices_path() -> Path:
    return home() / "config" / "voices.json"


@dataclass
class Settings:
    engine: str
    device: str
    models_dir: Path
    output_dir: Path
    cache_dir: Path
    sample_rate: int
    default_format: str
    mp3_bitrate: str
    seed: int | None
    max_segment_chars: int
    sentence_pause_ms: int
    paragraph_pause_ms: int
    target_rms_dbfs: float
    peak_ceiling_dbfs: float
    ffmpeg_path: str
    block_network: bool
    segment_retries: int
    raw: dict = field(repr=False, default_factory=dict)


def load_settings() -> Settings:
    d = _read_json(settings_path())
    seg = d.get("segmentation", {})
    loud = d.get("loudness", {})
    try:
        s = Settings(
            engine=d["engine"],
            # OFFLINE_VOICE_DEVICE=cpu lets a caller avoid the GPU (e.g. while rendering video) without editing config.
            device=os.environ.get("OFFLINE_VOICE_DEVICE", "").strip().lower() or d.get("device", "auto"),
            models_dir=resolve_home_path(d.get("models_dir", "models")),
            output_dir=resolve_home_path(d.get("output_dir", "output")),
            cache_dir=resolve_home_path(d.get("cache_dir", "output/.segments")),
            sample_rate=int(d.get("sample_rate", 24000)),
            default_format=d.get("default_format", "mp3").lower(),
            mp3_bitrate=d.get("mp3_bitrate", "192k"),
            seed=d.get("seed"),
            max_segment_chars=int(seg.get("max_chars", 260)),
            sentence_pause_ms=int(seg.get("sentence_pause_ms", 250)),
            paragraph_pause_ms=int(seg.get("paragraph_pause_ms", 650)),
            target_rms_dbfs=float(loud.get("target_rms_dbfs", -20.0)),
            peak_ceiling_dbfs=float(loud.get("peak_ceiling_dbfs", -1.0)),
            ffmpeg_path=d.get("ffmpeg_path", "") or "",
            block_network=bool(d.get("offline", {}).get("block_network", True)),
            segment_retries=int(d.get("segment_retries", 1)),
            raw=d,
        )
    except KeyError as e:
        raise ConfigError(f"settings.json is missing required key {e}") from e
    if s.engine not in SUPPORTED_ENGINES:
        raise ConfigError(f"settings.json engine '{s.engine}' is not supported (supported: {SUPPORTED_ENGINES})")
    if s.device not in ("auto", "cuda", "cpu"):
        raise ConfigError(f"settings.json device must be auto, cuda or cpu (got '{s.device}')")
    if s.default_format not in ("mp3", "wav"):
        raise ConfigError("settings.json default_format must be mp3 or wav")
    return s


@dataclass
class VoiceProfile:
    id: str
    name: str
    engine: str
    voice_type: str
    preset_file: Path | None
    preset_recipe: dict[str, float]
    reference_audio: Path | None
    reference_transcript: Path | None
    language: str
    lang_code: str
    speed: float
    seed: int | None
    default: bool
    offline_ready: bool
    config_path: Path
    raw: dict = field(repr=False, default_factory=dict)

    @property
    def label(self) -> str:
        return f"{self.id} ({self.name})"


def voice_config_path(voice_id: str) -> Path:
    return home() / "voices" / voice_id / "voice_config.json"


def load_profile(voice_id: str) -> VoiceProfile:
    if voice_id not in VOICE_IDS:
        raise ConfigError(f"Unknown voice '{voice_id}'. Valid voices: {', '.join(VOICE_IDS)}")
    path = voice_config_path(voice_id)
    d = _read_json(path)
    preset = d.get("preset") or {}
    try:
        return VoiceProfile(
            id=d["id"],
            name=d["name"],
            engine=d["engine"],
            voice_type=d.get("voice_type", "preset"),
            preset_file=resolve_home_path(preset.get("file")),
            preset_recipe={k: float(v) for k, v in (preset.get("recipe") or {}).items()},
            reference_audio=resolve_home_path(d.get("reference_audio")),
            reference_transcript=resolve_home_path(d.get("reference_transcript")),
            language=d.get("language", "en-us"),
            lang_code=d.get("lang_code", "a"),
            speed=float(d.get("speed", 1.0)),
            seed=d.get("seed"),
            default=bool(d.get("default", False)),
            offline_ready=bool(d.get("offline_ready", False)),
            config_path=path,
            raw=d,
        )
    except KeyError as e:
        raise ConfigError(f"{path} is missing required key {e}") from e


def load_profiles() -> dict[str, VoiceProfile]:
    return {vid: load_profile(vid) for vid in VOICE_IDS}


def default_voice_id(profiles: dict[str, VoiceProfile] | None = None) -> str:
    profiles = profiles or load_profiles()
    defaults = [p.id for p in profiles.values() if p.default]
    if len(defaults) != 1:
        raise ConfigError(f"Exactly one voice must have \"default\": true (found {defaults or 'none'})")
    return defaults[0]


def save_profile_fields(voice_id: str, **updates: Any) -> None:
    path = voice_config_path(voice_id)
    d = _read_json(path)
    d.update(updates)
    write_json(path, d)


def set_default_voice(voice_id: str) -> None:
    if voice_id not in VOICE_IDS:
        raise ConfigError(f"Unknown voice '{voice_id}'")
    for vid in VOICE_IDS:
        save_profile_fields(vid, default=(vid == voice_id))


def profile_problems(p: VoiceProfile, settings: Settings) -> list[str]:
    """Static validation of a profile. Returns a list of human-readable problems."""
    problems: list[str] = []
    if p.engine != settings.engine:
        problems.append(f"{p.id}: engine '{p.engine}' differs from settings engine '{settings.engine}'")
    if p.voice_type not in VOICE_TYPES:
        problems.append(f"{p.id}: voice_type must be one of {VOICE_TYPES}")
    if not (0.5 <= p.speed <= 2.0):
        problems.append(f"{p.id}: speed {p.speed} outside 0.5-2.0")
    if p.voice_type in ("preset", "preset_blend"):
        if p.preset_file is None:
            problems.append(f"{p.id}: preset.file is not set")
        elif not p.preset_file.is_file():
            problems.append(f"{p.id}: voice file not found: {p.preset_file}")
        if p.voice_type == "preset_blend":
            if not p.preset_recipe:
                problems.append(f"{p.id}: preset_blend needs a preset.recipe")
            elif abs(sum(p.preset_recipe.values()) - 1.0) > 1e-3:
                problems.append(f"{p.id}: preset.recipe weights must sum to 1.0")
    if p.voice_type == "reference_clone":
        if p.reference_audio is None or not p.reference_audio.is_file():
            problems.append(f"{p.id}: reference_audio missing")
        if p.reference_transcript is None or not p.reference_transcript.is_file():
            problems.append(f"{p.id}: reference_transcript missing")
        elif not p.reference_transcript.read_text(encoding="utf-8").strip():
            problems.append(f"{p.id}: reference_transcript is empty")
    return problems


def load_routing() -> dict:
    return _read_json(voices_path())
