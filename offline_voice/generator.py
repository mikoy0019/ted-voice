"""Offline narration pipeline: segment -> synthesize (cached) -> assemble -> normalize -> export."""

from __future__ import annotations

import hashlib
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
import soundfile as sf

from . import offline_guard
from .audio import assemble, find_ffmpeg, normalize, speech_stats, write_audio
from .config import ConfigError, Settings, VoiceProfile, load_profile, load_settings, profile_problems
from .engines import get_engine
from .engines.base import Engine
from .text import segment_script


class GenerationError(Exception):
    pass


@dataclass
class GenerationResult:
    output: str
    voice_id: str
    voice_name: str
    format: str
    duration_s: float
    segments: int
    segments_from_cache: int
    elapsed_s: float
    realtime_factor: float
    device: str
    stats: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


_ENGINE: Engine | None = None


def shared_engine(settings: Settings) -> Engine:
    """One engine instance per process, shared by both voices (no duplicate model loads)."""
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = get_engine(settings)
    return _ENGINE


def _stderr(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _segment_key(engine: Engine, profile: VoiceProfile, text: str, seed: int | None) -> str:
    parts = [engine.fingerprint(), engine.voice_fingerprint(profile), profile.lang_code,
             f"{profile.speed:.3f}", str(seed), text]
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:24]


def generate(text: str, voice_id: str, output: Path, seed: int | None = None, use_cache: bool = True,
             progress: Callable[[str], None] = _stderr, profile: VoiceProfile | None = None) -> GenerationResult:
    """Narrate text with a configured voice. `profile` overrides the stored profile (used for auditions)."""
    settings = load_settings()
    offline_guard.install(block=settings.block_network)

    profile = profile or load_profile(voice_id)
    problems = profile_problems(profile, settings)
    if problems:
        raise ConfigError("Voice profile is not usable:\n  " + "\n  ".join(problems))
    if not profile.offline_ready:
        progress(f"[offline-voice] note: {profile.label} has not passed validate_voice.py yet")

    segments = segment_script(text, settings.max_segment_chars, settings.sentence_pause_ms,
                              settings.paragraph_pause_ms)
    if not segments:
        raise GenerationError("The script is empty after cleaning; nothing to narrate.")

    fmt = output.suffix.lower().lstrip(".")
    if fmt not in ("mp3", "wav"):
        raise GenerationError(f"Output must end in .mp3 or .wav (got '{output.name}')")
    ffmpeg = find_ffmpeg(settings.ffmpeg_path)
    if fmt == "mp3" and not ffmpeg:
        raise GenerationError("MP3 output needs FFmpeg, which was not found. Use a .wav output or run setup.bat.")

    engine = shared_engine(settings)
    seed = seed if seed is not None else (profile.seed if profile.seed is not None else settings.seed)
    t0 = time.perf_counter()
    progress(f"[offline-voice] loading {engine.name} for {profile.label}")
    engine.load()
    progress(f"[offline-voice] device={engine.device}, {len(segments)} segment(s)")

    cache_dir = settings.cache_dir / profile.id
    cache_dir.mkdir(parents=True, exist_ok=True)
    pieces: list[tuple[np.ndarray, int]] = []
    from_cache = 0
    failures: list[str] = []
    for seg in segments:
        key = _segment_key(engine, profile, seg.text, seed)
        cached = cache_dir / f"{key}.wav"
        if use_cache and cached.is_file():
            audio, _ = sf.read(str(cached), dtype="float32")
            from_cache += 1
            progress(f"[{seg.index + 1}/{len(segments)}] cached")
        else:
            audio = None
            for attempt in range(settings.segment_retries + 1):
                try:
                    audio = engine.synthesize(seg.text, profile, seed)
                    break
                except (ConfigError, offline_guard.NetworkBlockedError):
                    raise
                except Exception as e:  # keep going so finished segments are cached for the re-run
                    progress(f"[{seg.index + 1}/{len(segments)}] attempt {attempt + 1} failed: {e}")
            if audio is None:
                failures.append(f"segment {seg.index + 1}: {seg.text[:70]!r}")
                continue
            sf.write(str(cached), audio, engine.sample_rate, subtype="FLOAT")
            progress(f"[{seg.index + 1}/{len(segments)}] {len(audio) / engine.sample_rate:.1f}s")
        pieces.append((audio, seg.pause_after_ms))

    if failures:
        raise GenerationError(f"{len(failures)} segment(s) failed; completed segments are cached, so re-running "
                              "only regenerates the failed ones:\n  " + "\n  ".join(failures))

    audio = normalize(assemble(pieces, engine.sample_rate), settings.target_rms_dbfs, settings.peak_ceiling_dbfs)
    output = output.resolve()
    write_audio(audio, engine.sample_rate, output, ffmpeg, settings.mp3_bitrate)
    elapsed = time.perf_counter() - t0
    duration = len(audio) / engine.sample_rate
    return GenerationResult(
        output=str(output), voice_id=profile.id, voice_name=profile.name, format=fmt,
        duration_s=round(duration, 2), segments=len(segments), segments_from_cache=from_cache,
        elapsed_s=round(elapsed, 2), realtime_factor=round(elapsed / duration, 3) if duration else 0.0,
        device=engine.device, stats=speech_stats(audio, engine.sample_rate),
    )
