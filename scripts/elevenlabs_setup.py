"""One-time ElevenLabs utility: look up voices and record which ones Voice 1 / Voice 2 are modelled on.

This script is the ONLY part of OfflineVoice that talks to ElevenLabs. Offline narration never calls it.

Read-only commands (free, no credits used):
    python scripts/elevenlabs_setup.py --list                       # voices in your account
    python scripts/elevenlabs_setup.py --search "Mark"              # public Voice Library search
    python scripts/elevenlabs_setup.py --voice-1 VOICE_ID_1 --voice-2 VOICE_ID_2
    python scripts/elevenlabs_setup.py --show

Chargeable command (uses credits, refused unless you approve AND are authorised):
    python scripts/elevenlabs_setup.py --generate-reference voice_1 --text-file ref.txt ^
        --approve-credits --authorization "I own this voice (account owner)"

Important limits:
  * The API cannot export voice-model weights. A Voice ID is not a downloadable model.
  * Access to a public Voice Library voice is NOT permission to clone it. Library voices belong to
    their creators; this tool records them as *character references only*.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests  # noqa: E402

from offline_voice.config import VOICE_IDS, load_routing, voices_path, write_json  # noqa: E402
from offline_voice.paths import home  # noqa: E402

API = "https://api.elevenlabs.io"
TIMEOUT = 30


class ElevenLabsError(Exception):
    pass


def api_key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        env_file = home() / ".env"
        if env_file.is_file():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("ELEVENLABS_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        raise ElevenLabsError("ELEVENLABS_API_KEY is not set (environment variable or .env file).")
    return key


def _get(path: str, params: dict | None = None) -> dict:
    try:
        r = requests.get(f"{API}{path}", headers={"xi-api-key": api_key()}, params=params, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise ElevenLabsError(f"Network error calling ElevenLabs: {e}") from e
    if r.status_code == 401:
        raise ElevenLabsError("ElevenLabs rejected the API key (401). Check ELEVENLABS_API_KEY.")
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail")
        except ValueError:
            detail = r.text[:300]
        # Unknown voice IDs come back as 400 {"code": "voice_not_found"} rather than 404.
        if r.status_code == 404 or (isinstance(detail, dict) and detail.get("code") == "voice_not_found"):
            return {}
        raise ElevenLabsError(f"ElevenLabs API error {r.status_code} on {path}: {detail}")
    return r.json()


def account_voices() -> list[dict]:
    voices, token = [], None
    while True:
        params = {"page_size": 100}
        if token:
            params["next_page_token"] = token
        d = _get("/v2/voices", params)
        voices.extend(d.get("voices", []))
        token = d.get("next_page_token")
        if not d.get("has_more") or not token:
            return voices


def library_search(query: str, page_size: int = 30) -> list[dict]:
    return _get("/v1/shared-voices", {"search": query, "page_size": page_size}).get("voices", [])


def lookup_voice(voice_id: str) -> dict:
    """Find a voice in the account first, then in the public Voice Library."""
    d = _get(f"/v1/voices/{voice_id}")
    if d.get("voice_id") == voice_id:
        sharing = d.get("sharing") or {}
        return {
            "provider": "elevenlabs",
            "voice_id": voice_id,
            "name": d.get("name"),
            "source": "account",
            "category": d.get("category"),
            "is_owner": d.get("is_owner"),
            "description": d.get("description"),
            "labels": d.get("labels") or {},
            "library_owner_id": sharing.get("public_owner_id"),
        }
    for v in library_search(voice_id, page_size=10):
        if v.get("voice_id") == voice_id:
            return {
                "provider": "elevenlabs",
                "voice_id": voice_id,
                "name": v.get("name"),
                "source": "public_voice_library",
                "category": v.get("category"),
                "is_owner": False,
                "description": v.get("description"),
                "labels": {k: v.get(k) for k in ("gender", "age", "accent", "descriptive", "use_case", "language")
                           if v.get(k)},
                "library_owner_id": v.get("public_owner_id"),
            }
    raise ElevenLabsError(f"Voice {voice_id} was not found in your account or the public Voice Library.")


def cmd_list() -> None:
    voices = account_voices()
    print(f"{len(voices)} voices in your ElevenLabs account:\n")
    for v in voices:
        labels = ", ".join(f"{k}={val}" for k, val in (v.get("labels") or {}).items())
        print(f"{v['voice_id']}  {v['name']}  [{v.get('category')}]")
        if v.get("description"):
            print(f"    {v['description'].strip()}")
        if labels:
            print(f"    {labels}")


def cmd_search(query: str) -> None:
    voices = library_search(query)
    print(f"{len(voices)} public Voice Library results for '{query}' (character reference only):\n")
    for v in voices:
        print(f"{v['voice_id']}  {v['name']}  [{v.get('gender')}, {v.get('age')}, {v.get('accent')}, "
              f"{v.get('descriptive')}, {v.get('use_case')}]")
        if v.get("description"):
            print(f"    {v['description'].strip()}")


def cmd_select(selection: dict[str, str]) -> None:
    routing = load_routing()
    block = routing.setdefault("elevenlabs", {})
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for voice_slot, voice_id in selection.items():
        info = lookup_voice(voice_id)
        info["offline_ready"] = False  # an ElevenLabs voice itself can never run offline
        info["retrieved_at"] = now
        info["usage"] = ("authorised_for_local_reference" if info.get("is_owner")
                         else "character_reference_only")
        block[voice_slot] = info
        meta_path = home() / "voices" / voice_slot / "metadata.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
        meta["elevenlabs_reference"] = info
        write_json(meta_path, meta)
        print(f"{voice_slot}: {info['name']} ({voice_id}) from {info['source']} -> {info['usage']}")
        if not info.get("is_owner"):
            print("    You do not own this voice. It is stored as a character reference only and will not be "
                  "cloned. Your offline voice is an original voice designed to match this character.")
    write_json(voices_path(), routing)
    print(f"\nSaved to {voices_path()}")


def cmd_show() -> None:
    block = load_routing().get("elevenlabs", {})
    print(json.dumps(block, indent=2, ensure_ascii=False) if block else "No ElevenLabs voices selected yet.")


def cmd_generate_reference(voice_slot: str, text_file: Path, approve: bool, authorization: str | None) -> None:
    block = load_routing().get("elevenlabs", {})
    info = block.get(voice_slot)
    if not info:
        raise ElevenLabsError(f"Select a voice for {voice_slot} first (--{voice_slot.replace('_', '-')} ID).")
    if not info.get("is_owner"):
        raise ElevenLabsError(
            f"Refusing: {info['name']} is not owned by your account ({info['source']}). Public Voice Library access "
            "is not permission to reproduce a voice outside ElevenLabs. Get written permission from the voice "
            "owner, or use your own recorded voice with scripts/import_voice.py.")
    if not authorization:
        raise ElevenLabsError("Pass --authorization \"<how you are authorised>\" to record your basis for cloning.")
    text = text_file.read_text(encoding="utf-8").strip()
    if not approve:
        raise ElevenLabsError(f"This request would use about {len(text)} ElevenLabs credits. Re-run with "
                              "--approve-credits to confirm.")
    r = requests.post(f"{API}/v1/text-to-speech/{info['voice_id']}",
                      headers={"xi-api-key": api_key(), "accept": "audio/mpeg"},
                      params={"output_format": "mp3_44100_128"},
                      json={"text": text, "model_id": "eleven_multilingual_v2"}, timeout=120)
    if r.status_code >= 400:
        raise ElevenLabsError(f"Generation failed ({r.status_code}): {r.text[:300]}")
    out_dir = home() / "voices" / voice_slot
    audio_path = out_dir / "reference_source.mp3"
    audio_path.write_bytes(r.content)
    (out_dir / "reference_source.txt").write_text(text + "\n", encoding="utf-8")
    meta_path = out_dir / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
    meta.setdefault("authorization_log", []).append({
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "statement": authorization,
        "note": "Self-declared. A statement here is a record, not proof of legal permission.",
        "action": "generated reference_source.mp3 via ElevenLabs API",
    })
    write_json(meta_path, meta)
    print(f"Saved {audio_path}\nNext: python scripts/import_voice.py --voice {voice_slot} --input \"{audio_path}\" "
          f"--transcript \"{out_dir / 'reference_source.txt'}\" --authorization \"{authorization}\"")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="list voices in your account")
    ap.add_argument("--search", metavar="TEXT", help="search the public Voice Library")
    ap.add_argument("--voice-1", metavar="VOICE_ID", help="record the ElevenLabs voice Voice 1 is modelled on")
    ap.add_argument("--voice-2", metavar="VOICE_ID", help="record the ElevenLabs voice Voice 2 is modelled on")
    ap.add_argument("--show", action="store_true", help="show the saved ElevenLabs selection")
    ap.add_argument("--generate-reference", choices=VOICE_IDS, help="(chargeable) generate reference audio")
    ap.add_argument("--text-file", type=Path, help="text for --generate-reference")
    ap.add_argument("--approve-credits", action="store_true", help="confirm you accept the credit cost")
    ap.add_argument("--authorization", help="how you are authorised to reproduce this voice")
    args = ap.parse_args()

    try:
        if args.list:
            cmd_list()
        elif args.search:
            cmd_search(args.search)
        elif args.voice_1 or args.voice_2:
            selection = {k: v for k, v in (("voice_1", args.voice_1), ("voice_2", args.voice_2)) if v}
            cmd_select(selection)
        elif args.show:
            cmd_show()
        elif args.generate_reference:
            if not args.text_file:
                ap.error("--generate-reference needs --text-file")
            cmd_generate_reference(args.generate_reference, args.text_file, args.approve_credits, args.authorization)
        else:
            ap.print_help()
    except ElevenLabsError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
