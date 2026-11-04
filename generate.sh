#!/usr/bin/env bash
# Offline narration launcher for Git Bash (used by Claude Code on Windows).
# Same arguments as generate.bat, but safe when both this folder's path and the arguments contain
# spaces (cmd.exe mangles quoting in that case when a .bat is launched from bash).
#   "$OFFLINE_VOICE_HOME/generate.sh" --voice voice_1 --input script.txt --output narration.mp3
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$HERE/.venv/Scripts/python.exe"
[ -x "$PY" ] || PY="$HERE/.venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "ERROR: OfflineVoice is not installed. Run setup.bat first." >&2
  exit 3
fi
exec "$PY" "$HERE/scripts/generate_voice.py" "$@"
