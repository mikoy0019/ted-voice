"""Import an AUTHORISED voice recording as a voice's reference audio.

    python scripts/import_voice.py --voice voice_1 --input recording_1.mp3 ^
        --transcript recording_1.txt --authorization "My own voice, recorded 2026-10-08"

Supported inputs: WAV, MP3, FLAC, M4A. Pipeline: validate -> decode -> inspect duration and
sample rate -> convert to 24 kHz mono -> gentle loudness normalisation -> trim leading/trailing
silence only -> save voices/<voice>/reference.wav (+ transcript.txt) -> record authorisation.

Only import recordings you own or have explicit permission to reproduce. The --authorization
statement is stored as a record; it is not proof of legal permission.

Note: the installed engine (Kokoro-82M) uses designed voicepacks and cannot clone from reference
audio. Imported references are stored for a cloning-capable engine; the voice keeps using its
voicepack until you switch it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402

from offline_voice.audio import (AudioError, find_ffmpeg, normalize, read_audio, speech_stats,  # noqa: E402
                                 trim_silence)
from offline_voice.config import VOICE_IDS, load_settings, save_profile_fields, write_json  # noqa: E402
from offline_voice.paths import home, resolve_user_path  # noqa: E402

SUPPORTED = {".wav", ".mp3", ".flac", ".m4a"}
TARGET_SR = 24000
MIN_S, IDEAL_MIN_S, IDEAL_MAX_S, MAX_S = 3.0, 6.0, 30.0, 90.0


def probe_rate(path: Path) -> int | None:
    try:
        return sf.info(str(path)).samplerate
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--voice", required=True, choices=VOICE_IDS)
    ap.add_argument("--input", required=True, help="recording (.wav .mp3 .flac .m4a)")
    tr = ap.add_mutually_exclusive_group()
    tr.add_argument("--transcript", help="text file with exactly what is said in the recording")
    tr.add_argument("--transcript-text", help="transcript given inline")
    ap.add_argument("--authorization", required=True,
                    help="how you are authorised to reproduce this voice (stored as a record)")
    args = ap.parse_args()

    src = resolve_user_path(args.input)
    if not src.is_file():
        print(f"ERROR: input not found: {src}", file=sys.stderr)
        return 2
    if src.suffix.lower() not in SUPPORTED:
        print(f"ERROR: unsupported format {src.suffix}; use {', '.join(sorted(SUPPORTED))}", file=sys.stderr)
        return 2
    if len(args.authorization.strip()) < 10:
        print("ERROR: describe your authorisation in a sentence (e.g. 'My own voice').", file=sys.stderr)
        return 2

    settings = load_settings()
    ffmpeg = find_ffmpeg(settings.ffmpeg_path)
    try:
        audio, sr = read_audio(src, ffmpeg, sr=TARGET_SR)
    except AudioError as e:
        print(f"ERROR: could not decode {src.name}: {e}", file=sys.stderr)
        return 2
    original_rate = probe_rate(src)
    duration = len(audio) / sr
    print(f"decoded {src.name}: {duration:.1f}s, source sample rate {original_rate or 'unknown'} Hz")
    if duration < MIN_S:
        print(f"ERROR: recording is {duration:.1f}s; at least {MIN_S:.0f}s of clean speech is needed.", file=sys.stderr)
        return 2
    if duration > MAX_S:
        print(f"ERROR: recording is {duration:.0f}s; trim it to a clean {IDEAL_MIN_S:.0f}-{IDEAL_MAX_S:.0f}s clip.",
              file=sys.stderr)
        return 2
    if not IDEAL_MIN_S <= duration <= IDEAL_MAX_S:
        print(f"warning: {IDEAL_MIN_S:.0f}-{IDEAL_MAX_S:.0f}s works best for most cloning engines")
    if original_rate and original_rate < 16000:
        print(f"warning: source is {original_rate} Hz; low sample rates reduce clone quality")

    clip = trim_silence(audio, sr, threshold_db=-50.0, keep_ms=150)
    peak = float(np.max(np.abs(clip))) if clip.size else 0.0
    if peak >= 0.999:
        print("warning: the recording appears to clip; a cleaner take will clone better")
    clip = normalize(clip, target_rms_dbfs=-20.0, peak_ceiling_dbfs=-1.0)
    stats = speech_stats(clip, sr)
    if not stats["audible"]:
        print(f"ERROR: the recording does not look like audible speech: {stats}", file=sys.stderr)
        return 2

    if args.transcript:
        tpath = resolve_user_path(args.transcript)
        if not tpath.is_file():
            print(f"ERROR: transcript not found: {tpath}", file=sys.stderr)
            return 2
        transcript = tpath.read_text(encoding="utf-8-sig").strip()
    else:
        transcript = (args.transcript_text or "").strip()
    if transcript:
        words = len(transcript.split())
        wps = words / stats["duration_s"]
        if not 0.8 <= wps <= 5.0:
            print(f"warning: transcript has {words} words for {stats['duration_s']}s of audio ({wps:.1f} words/s); "
                  "check it matches the recording exactly")
    else:
        print("warning: no transcript given; engines that need one (e.g. F5-style) will refuse this reference")

    voice_dir = home() / "voices" / args.voice
    ref = voice_dir / "reference.wav"
    sf.write(str(ref), clip, sr, subtype="PCM_16")
    tfile = voice_dir / "transcript.txt"
    tfile.write_text(transcript + "\n" if transcript else "", encoding="utf-8")
    save_profile_fields(args.voice, reference_audio=f"voices/{args.voice}/reference.wav",
                        reference_transcript=f"voices/{args.voice}/transcript.txt")

    meta_path = voice_dir / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
    meta.setdefault("authorization_log", []).append({
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "statement": args.authorization.strip(),
        "note": "Self-declared by the user. Stored as a record; not proof of legal permission.",
        "source_file": src.name,
        "source_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
        "reference_duration_s": stats["duration_s"],
    })
    write_json(meta_path, meta)

    print(f"saved {ref} ({stats['duration_s']}s, {sr} Hz mono, {stats['rms_dbfs']} dBFS RMS)")
    print(f"saved {tfile}")
    print("The installed Kokoro engine cannot clone from reference audio, so this voice keeps using its "
          "designed voicepack. The reference is stored for a cloning-capable engine.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
