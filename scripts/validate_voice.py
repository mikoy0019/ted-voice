"""Validate voice profiles and mark them offline-ready after a successful offline test generation.

    python scripts/validate_voice.py                   # validate both voices (generates a short test clip each)
    python scripts/validate_voice.py --voice voice_2
    python scripts/validate_voice.py --static          # config/file checks only, no audio generation
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from offline_voice import offline_guard  # noqa: E402

offline_guard.install(block=True)  # before kokoro / huggingface_hub are imported

from offline_voice.audio import ffmpeg_can_decode, find_ffmpeg  # noqa: E402
from offline_voice.config import (VOICE_IDS, ConfigError, default_voice_id, load_profile, load_profiles,  # noqa: E402
                                  load_settings, profile_problems, save_profile_fields)
from offline_voice.engines import get_engine  # noqa: E402
from offline_voice.paths import home  # noqa: E402

TEST_TEXT = "This is a quick offline voice check. If you can hear this clearly, the voice is ready."


def validate(voice_id: str, generate_audio: bool) -> list[str]:
    settings = load_settings()
    profile = load_profile(voice_id)
    problems = profile_problems(profile, settings)
    engine = get_engine(settings)
    if profile.voice_type not in engine.supported_voice_types:
        problems.append(f"{voice_id}: engine {engine.name} does not support voice_type {profile.voice_type}")
    problems += [f"{voice_id}: missing {m}" for m in engine.missing_files()]
    if problems or not generate_audio:
        return problems

    from offline_voice.generator import generate

    out = home() / "output" / f"_validate_{voice_id}.wav"
    result = generate(TEST_TEXT, voice_id, out, use_cache=False, progress=lambda _m: None)
    if not result.stats.get("audible"):
        problems.append(f"{voice_id}: test audio is not audible speech: {result.stats}")
    ok, err = ffmpeg_can_decode(Path(result.output), find_ffmpeg(settings.ffmpeg_path))
    if not ok:
        problems.append(f"{voice_id}: FFmpeg could not decode the output: {err}")
    if offline_guard.blocked_attempts:
        problems.append(f"{voice_id}: network access was attempted: {offline_guard.blocked_attempts}")
    print(f"{voice_id}: generated {result.duration_s}s in {result.elapsed_s}s on {result.device} -> {result.output}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--voice", choices=VOICE_IDS)
    ap.add_argument("--static", action="store_true", help="skip test generation")
    args = ap.parse_args()

    try:
        profiles = load_profiles()
        default = default_voice_id(profiles)
    except ConfigError as e:
        print(f"FAIL: {e}")
        return 2
    print(f"Voices: " + ", ".join(f"{p.id}={p.name}" for p in profiles.values()) + f"; default={default}")

    failed = False
    for vid in [args.voice] if args.voice else list(VOICE_IDS):
        try:
            problems = validate(vid, generate_audio=not args.static)
        except Exception as e:
            problems = [f"{vid}: {type(e).__name__}: {e}"]
        if problems:
            failed = True
            if not args.static:
                save_profile_fields(vid, offline_ready=False)
            print(f"FAIL {vid}:\n  " + "\n  ".join(problems))
        else:
            if not args.static:
                save_profile_fields(vid, offline_ready=True)
            print(f"PASS {vid}" + (" (static checks only)" if args.static else " - offline_ready=true"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
