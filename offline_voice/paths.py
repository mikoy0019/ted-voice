"""Locate the OfflineVoice home folder and resolve configured paths."""

from __future__ import annotations

import os
from pathlib import Path

# The package always runs from inside its home folder, so the home is derived from
# this file rather than from OFFLINE_VOICE_HOME. That variable exists for *callers*
# (other projects, Claude Code, Codex) to find the generator.
HOME = Path(__file__).resolve().parents[1]


def home() -> Path:
    return HOME


def resolve_home_path(value: str | os.PathLike | None) -> Path | None:
    """Resolve a configured path: absolute stays absolute, relative is relative to HOME."""
    if value is None or str(value).strip() == "":
        return None
    p = Path(os.path.expandvars(os.path.expanduser(str(value))))
    return p if p.is_absolute() else (HOME / p)


def resolve_user_path(value: str | os.PathLike) -> Path:
    """Resolve a path given on the command line: relative to the caller's working directory."""
    p = Path(os.path.expandvars(os.path.expanduser(str(value))))
    return p if p.is_absolute() else (Path.cwd() / p)


def env_home_mismatch() -> str | None:
    """Return a warning if OFFLINE_VOICE_HOME points somewhere other than this install."""
    env = os.environ.get("OFFLINE_VOICE_HOME")
    if not env:
        return None
    try:
        if Path(env).expanduser().resolve() != HOME.resolve():
            return f"OFFLINE_VOICE_HOME={env} does not match this install at {HOME}"
    except OSError:
        return f"OFFLINE_VOICE_HOME={env} is not a valid path"
    return None
