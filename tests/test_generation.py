"""Real audio generation with the installed offline engine (skipped until setup.bat has run)."""

import random
from pathlib import Path

import pytest

from conftest import requires_engine
from offline_voice import offline_guard
from offline_voice.audio import ffmpeg_can_decode, find_ffmpeg, read_audio, speech_stats

pytestmark = requires_engine

LONG_SCRIPT = ("The history of flight is a story of patience. People watched birds for thousands of years "
               "before anyone built a machine that could follow them. Early attempts failed, sometimes "
               "badly, but every failure taught the next inventor something useful.\n\n") * 6


@pytest.fixture(scope="module")
def gen():
    from offline_voice.generator import generate

    return generate


def test_voice_1_generates_wav(gen, tmp_path):
    r = gen("Welcome to today's video.", "voice_1", tmp_path / "v1.wav", use_cache=False, progress=lambda m: None)
    assert Path(r.output).is_file() and r.format == "wav"
    audio, sr = read_audio(Path(r.output))
    assert speech_stats(audio, sr)["audible"]


def test_voice_2_generates_mp3(gen, tmp_path):
    r = gen("Here are five amazing facts.", "voice_2", tmp_path / "v2.mp3", use_cache=False, progress=lambda m: None)
    assert Path(r.output).is_file() and r.format == "mp3"
    ok, err = ffmpeg_can_decode(Path(r.output), find_ffmpeg())
    assert ok, err
    assert r.stats["audible"]


def test_two_voices_sound_different(gen, tmp_path):
    import numpy as np

    text = "This sentence is read by both voices."
    a = gen(text, "voice_1", tmp_path / "a.wav", progress=lambda m: None)
    b = gen(text, "voice_2", tmp_path / "b.wav", progress=lambda m: None)
    xa, _ = read_audio(Path(a.output))
    xb, _ = read_audio(Path(b.output))
    n = min(len(xa), len(xb))
    assert len(xa) != len(xb) or not np.allclose(xa[:n], xb[:n], atol=1e-3)


def test_long_script_and_segment_cache(gen, tmp_path):
    out = tmp_path / "long.mp3"
    first = gen(LONG_SCRIPT, "voice_1", out, use_cache=False, progress=lambda m: None)
    assert first.segments >= 6
    assert first.duration_s > 60
    assert first.stats["audible"]
    again = gen(LONG_SCRIPT, "voice_1", out, use_cache=True, progress=lambda m: None)
    assert again.segments_from_cache == again.segments
    assert abs(again.duration_s - first.duration_s) < 0.05


def test_failed_segment_is_reported_and_resume_only_redoes_it(gen, tmp_path, monkeypatch):
    from offline_voice import generator
    from offline_voice.config import load_settings

    script = "First part of the story. " * 12 + "\n\nThe POISON paragraph fails once.\n\n" + "Final words here. " * 12
    engine = generator.shared_engine(load_settings())
    real = engine.synthesize
    calls = []

    def flaky(text, profile, seed):
        calls.append(text)
        if "POISON" in text:
            raise RuntimeError("simulated engine crash")
        return real(text, profile, seed)

    monkeypatch.setattr(engine, "synthesize", flaky)
    seed = random.randint(10**6, 10**9)  # fresh seed => fresh cache keys, nothing reused from earlier runs
    with pytest.raises(generator.GenerationError, match="1 segment"):
        gen(script, "voice_1", tmp_path / "r.wav", seed=seed, progress=lambda m: None)

    calls.clear()
    monkeypatch.setattr(engine, "synthesize", lambda t, p, s: (calls.append(t), real(t, p, s))[1])
    r = gen(script, "voice_1", tmp_path / "r.wav", seed=seed, progress=lambda m: None)
    assert len(calls) == 1 and "POISON" in calls[0]  # only the failed segment was regenerated
    assert r.segments_from_cache == r.segments - 1


def test_generation_makes_no_network_attempts(gen, tmp_path):
    gen("Offline check.", "voice_2", tmp_path / "o.wav", use_cache=False, progress=lambda m: None)
    assert offline_guard.blocked_attempts == []
