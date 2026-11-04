"""Local, rule-based voice selection. No AI or network calls are involved."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .config import VOICE_IDS, ConfigError, default_voice_id, load_profiles, load_routing

_NUMBER_WORDS = {"1": "voice_1", "one": "voice_1", "2": "voice_2", "two": "voice_2"}
_EXPLICIT = re.compile(r"\bvoice[\s_#-]*(1|2|one|two)\b", re.IGNORECASE)


@dataclass
class Selection:
    voice_id: str
    reason: str
    content_type: str | None = None


def _normalize_content_type(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def select_voice(voice: str | None = None, content_type: str | None = None, request: str | None = None) -> Selection:
    """Pick a voice. Priority: explicit voice > voice named in request > content type > default."""
    profiles = load_profiles()

    if voice:
        key = voice.strip().lower()
        if key in VOICE_IDS:
            return Selection(key, "explicit --voice")
        for p in profiles.values():
            if p.name.lower() == key:
                return Selection(p.id, f"explicit voice name '{p.name}'")
        raise ConfigError(f"Unknown voice '{voice}'. Use voice_1, voice_2, or a voice name: "
                          + ", ".join(p.name for p in profiles.values()))

    routing = load_routing()
    rules = routing.get("routing", [])

    if request:
        m = _EXPLICIT.search(request)
        if m:
            return Selection(_NUMBER_WORDS[m.group(1).lower()], f"request names '{m.group(0)}'")
        for p in profiles.values():
            if re.search(rf"\b{re.escape(p.name)}\b", request, re.IGNORECASE):
                return Selection(p.id, f"request names voice '{p.name}'")
        if re.search(r"\bdefault voice\b", request, re.IGNORECASE):
            return Selection(default_voice_id(profiles), "request asks for the default voice")

    if content_type:
        wanted = _normalize_content_type(content_type)
        for rule in rules:
            if _normalize_content_type(rule["content_type"]) == wanted:
                return Selection(rule["voice"], f"content type '{rule['content_type']}' rule", rule["content_type"])
        raise ConfigError(f"Unknown content type '{content_type}'. Known: "
                          + ", ".join(r["content_type"] for r in rules))

    if request:
        text = request.lower()
        for rule in rules:
            for kw in rule.get("keywords", []):
                if re.search(rf"\b{re.escape(kw.lower())}\b", text):
                    return Selection(rule["voice"], f"request matches '{kw}' -> {rule['content_type']}",
                                     rule["content_type"])

    return Selection(default_voice_id(profiles), "configured default voice")
