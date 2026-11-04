"""Generate narration fully offline with Voice 1 or Voice 2.

Examples:
    python scripts/generate_voice.py --voice voice_1 --text "Welcome to today's video." --output output/video_1.mp3
    python scripts/generate_voice.py --voice voice_2 --input script.txt --output narration.wav
    python scripts/generate_voice.py --input script.txt --output narration.mp3            # default voice
    python scripts/generate_voice.py --content-type tiktok --input script.txt --output reel.mp3
    python scripts/generate_voice.py --request "Create a Facebook Reel using Voice 2" --input s.txt --output r.mp3
    python scripts/generate_voice.py --which --content-type documentary                   # just print the voice

On success the absolute output path is the ONLY line printed to stdout (progress goes to stderr),
or a JSON object when --json is given. Exit codes: 0 ok, 1 generation failed, 2 bad input/config,
3 offline model files missing.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from offline_voice.config import ConfigError, load_settings  # noqa: E402
from offline_voice.paths import resolve_user_path  # noqa: E402
from offline_voice.routing import select_voice  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--text", help="text to narrate")
    src.add_argument("--input", help="UTF-8 script file to narrate")
    ap.add_argument("--voice", help="voice_1, voice_2, or a voice name (overrides everything else)")
    ap.add_argument("--content-type", help="e.g. youtube_long_form, documentary, tiktok, facebook_reels")
    ap.add_argument("--request", help="the user's request text; 'Voice 1/2' or content keywords pick the voice")
    ap.add_argument("--output", help="output .mp3 or .wav (relative to the current directory)")
    ap.add_argument("--seed", type=int, help="override the voice's generation seed")
    ap.add_argument("--no-cache", action="store_true", help="regenerate every segment")
    ap.add_argument("--json", action="store_true", help="print a JSON result instead of just the path")
    ap.add_argument("--which", action="store_true", help="only print which voice would be used")
    args = ap.parse_args()

    try:
        selection = select_voice(args.voice, args.content_type, args.request)
    except ConfigError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    if args.which:
        from offline_voice.config import load_profile

        p = load_profile(selection.voice_id)
        info = {"voice_id": p.id, "name": p.name, "reason": selection.reason, "content_type": selection.content_type}
        print(json.dumps(info) if args.json else f"{p.id} ({p.name}) - {selection.reason}")
        return 0

    if args.text is not None:
        text = args.text
    elif args.input:
        path = resolve_user_path(args.input)
        if not path.is_file():
            print(f"ERROR: script file not found: {path}", file=sys.stderr)
            return 2
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            print(f"ERROR: {path} is not valid UTF-8 text", file=sys.stderr)
            return 2
    else:
        print("ERROR: provide --text or --input", file=sys.stderr)
        return 2
    if not text.strip():
        print("ERROR: the script is empty", file=sys.stderr)
        return 2

    if args.output:
        output = resolve_user_path(args.output)
    else:
        settings = load_settings()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = settings.output_dir / f"{stamp}_{selection.voice_id}.{settings.default_format}"

    print(f"[offline-voice] voice: {selection.voice_id} ({selection.reason})", file=sys.stderr)

    from offline_voice.engines.base import EngineUnavailable
    from offline_voice.generator import GenerationError, generate

    try:
        result = generate(text, selection.voice_id, output, seed=args.seed, use_cache=not args.no_cache)
    except EngineUnavailable as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 3
    except ConfigError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except GenerationError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: generation failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    if not result.stats.get("audible"):
        print(f"ERROR: output does not contain audible speech: {result.stats}", file=sys.stderr)
        return 1
    print(f"[offline-voice] {result.duration_s}s of audio in {result.elapsed_s}s "
          f"(RTF {result.realtime_factor}, {result.device})", file=sys.stderr)
    print(json.dumps(result.to_dict(), indent=2) if args.json else result.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
