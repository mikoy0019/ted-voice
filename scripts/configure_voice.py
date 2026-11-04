"""Design and edit the two permanent voices (name, sound, speed, default).

Each voice is an ORIGINAL voicepack: a weighted blend of Kokoro-82M's Apache-2.0 base voices,
chosen to match a character description. No real person's voice is cloned.

    python scripts/configure_voice.py --build                         # (re)build voice.pt for both voices
    python scripts/configure_voice.py --audition voice_1              # render candidate blends to listen to
    python scripts/configure_voice.py --voice voice_1 --blend am_michael:0.55,am_puck:0.45
    python scripts/configure_voice.py --voice voice_2 --name "Tessa" --speed 1.1
    python scripts/configure_voice.py --voice voice_2 --set-default
    python scripts/configure_voice.py --show
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from offline_voice.config import (VOICE_IDS, ConfigError, load_profile, load_profiles, load_routing,  # noqa: E402
                                  load_settings, save_profile_fields, set_default_voice, write_json)
from offline_voice.engines.kokoro_engine import base_voice_path, blend_voices  # noqa: E402
from offline_voice.paths import home  # noqa: E402

# Candidate blends per character, auditioned with --audition. Candidate 1 is the shipped default.
CANDIDATES = {
    "voice_1": [
        {"am_michael": 0.55, "am_puck": 0.45},
        {"am_puck": 0.7, "am_michael": 0.3},
        {"am_michael": 0.5, "am_puck": 0.25, "am_fenrir": 0.25},
        {"am_michael": 0.6, "am_eric": 0.4},
    ],
    "voice_2": [
        {"af_bella": 0.6, "af_heart": 0.4},
        {"af_bella": 0.8, "af_sky": 0.2},
        {"af_heart": 0.5, "af_bella": 0.3, "af_nova": 0.2},
        {"af_bella": 0.5, "af_aoede": 0.3, "af_heart": 0.2},
    ],
}

AUDITION_TEXT = {
    "voice_1": ("Hey, welcome back. Today we're digging into something I've been curious about for a while. "
                "It sounds complicated at first, but stick with me, because once it clicks, it's actually "
                "pretty simple."),
    "voice_2": ("Okay, you guys are not ready for this! Here are three things you didn't know about your phone, "
                "and number two is honestly wild. Let's get into it!"),
}


def parse_recipe(text: str) -> dict[str, float]:
    recipe: dict[str, float] = {}
    for part in text.split(","):
        name, _, weight = part.strip().partition(":")
        if not name:
            continue
        recipe[name.strip()] = float(weight) if weight else 1.0
    total = sum(recipe.values())
    if total <= 0:
        raise ConfigError("Blend weights must be positive")
    return {k: round(v / total, 4) for k, v in recipe.items()}


def write_metadata(voice_id: str, recipe: dict[str, float]) -> None:
    profile = load_profile(voice_id)
    meta_path = home() / "voices" / voice_id / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
    el = load_routing().get("elevenlabs", {}).get(voice_id) or meta.get("elevenlabs_reference")
    meta.update({
        "voice_id": voice_id,
        "name": profile.name,
        "origin": "original_blend",
        "method": "Weighted average of Kokoro-82M built-in voicepacks; no speaker recordings involved.",
        "recipe": recipe,
        "updated": date.today().isoformat(),
        "cloned_from_real_person": False,
        "licenses": {"engine_code": "Apache-2.0 (kokoro)", "model_weights": "Apache-2.0 (hexgrad/Kokoro-82M)",
                     "base_voicepacks": "Apache-2.0 (hexgrad/Kokoro-82M/voices)"},
        "authorization": {
            "required": False,
            "reason": "This voice does not reproduce any third-party voice. ElevenLabs voices are referenced "
                      "for character description only.",
        },
    })
    if el:
        meta["elevenlabs_reference"] = el
    write_json(meta_path, meta)


def build(voice_id: str, recipe: dict[str, float] | None = None) -> Path:
    settings = load_settings()
    profile = load_profile(voice_id)
    recipe = recipe or profile.preset_recipe
    out = home() / "voices" / voice_id / "voice.pt"
    blend_voices(settings, recipe, out)
    preset = dict(profile.raw.get("preset") or {})
    preset.update({"file": f"voices/{voice_id}/voice.pt", "recipe": recipe})
    changed = recipe != profile.preset_recipe
    save_profile_fields(voice_id, voice_type="preset_blend", preset=preset,
                        **({"offline_ready": False} if changed else {}))
    write_metadata(voice_id, recipe)
    print(f"{voice_id}: built {out} from {recipe}")
    return out


def audition(voice_id: str) -> None:
    from dataclasses import replace

    from offline_voice.generator import generate

    settings = load_settings()
    base = load_profile(voice_id)
    out_dir = home() / "voices" / voice_id / "samples"
    out_dir.mkdir(parents=True, exist_ok=True)
    text = AUDITION_TEXT[voice_id]
    for i, recipe in enumerate(CANDIDATES[voice_id], start=1):
        missing = [n for n in recipe if not base_voice_path(settings, n).is_file()]
        if missing:
            print(f"candidate {i}: skipped, base voices missing: {missing}")
            continue
        pack = blend_voices(settings, recipe, out_dir / f"candidate_{i}.pt")
        candidate = replace(base, preset_file=pack, preset_recipe=recipe)
        result = generate(text, voice_id, out_dir / f"candidate_{i}.mp3", use_cache=False,
                          progress=lambda _m: None, profile=candidate)
        recipe_txt = ",".join(f"{k}:{v}" for k, v in recipe.items())
        print(f"candidate {i}: {result.output}\n    to use it: python scripts/configure_voice.py "
              f"--voice {voice_id} --blend {recipe_txt}")


def show() -> None:
    for p in load_profiles().values():
        print(f"{p.id}: {p.name}{'  [default]' if p.default else ''}  speed={p.speed}  "
              f"offline_ready={p.offline_ready}\n    {p.raw.get('description', '')}\n    recipe={p.preset_recipe}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build", action="store_true", help="build voice.pt for both voices from their recipes")
    ap.add_argument("--audition", choices=VOICE_IDS, help="render candidate blends to voices/<id>/samples/")
    ap.add_argument("--voice", choices=VOICE_IDS, help="voice to edit")
    ap.add_argument("--blend", help="new recipe, e.g. am_michael:0.55,am_puck:0.45")
    ap.add_argument("--name")
    ap.add_argument("--role")
    ap.add_argument("--description")
    ap.add_argument("--speed", type=float)
    ap.add_argument("--set-default", action="store_true")
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    try:
        if args.build:
            for vid in VOICE_IDS:
                build(vid)
        if args.audition:
            audition(args.audition)
        if args.voice:
            edits = {k: v for k, v in (("name", args.name), ("role", args.role),
                                       ("description", args.description), ("speed", args.speed)) if v is not None}
            if edits:
                save_profile_fields(args.voice, **edits)
                print(f"{args.voice}: updated {', '.join(edits)}")
            if args.blend:
                build(args.voice, parse_recipe(args.blend))
            elif edits:
                write_metadata(args.voice, load_profile(args.voice).preset_recipe)
            if args.set_default:
                set_default_voice(args.voice)
                print(f"{args.voice} is now the default voice")
        if args.show or not (args.build or args.audition or args.voice):
            show()
    except ConfigError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
