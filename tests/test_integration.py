"""Call the generator the way Claude Code / Codex / other projects do: as a CLI from another folder."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import ROOT, requires_engine
from offline_voice.audio import find_ffmpeg

pytestmark = requires_engine

GENERATE_PY = ROOT / "scripts" / "generate_voice.py"
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
PY = str(VENV_PY if VENV_PY.is_file() else Path(sys.executable))


def run(args, cwd, env=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=env, timeout=600)


@pytest.fixture()
def project(tmp_path):
    p = tmp_path / "Other Project With Spaces"
    p.mkdir()
    (p / "script.txt").write_text("This narration was requested from a different project folder.", encoding="utf-8")
    return p


def test_cli_from_another_project_prints_absolute_path(project):
    r = run([PY, str(GENERATE_PY), "--voice", "voice_1", "--input", "script.txt", "--output", "out/narration.mp3"],
            cwd=project)
    assert r.returncode == 0, r.stderr
    lines = r.stdout.strip().splitlines()
    assert len(lines) == 1
    out = Path(lines[0])
    assert out.is_absolute() and out.is_file()
    assert out == (project / "out" / "narration.mp3").resolve()


@pytest.mark.skipif(os.name != "nt", reason="Windows launchers")
def test_generate_bat_from_powershell_via_offline_voice_home(project):
    """How Codex (PowerShell) calls it: spaces in both the install path and the arguments."""
    env = dict(os.environ, OFFLINE_VOICE_HOME=str(ROOT))
    cmd = ('& "$env:OFFLINE_VOICE_HOME\\generate.bat" --voice voice_2 --text "Hello from PowerShell." '
           '--output "reel voice.wav"; exit $LASTEXITCODE')
    r = run(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd], cwd=project, env=env)
    assert r.returncode == 0, r.stderr
    assert (project / "reel voice.wav").is_file()


def _git_bash():
    git = shutil.which("git")
    if not git:
        return None
    for candidate in (Path(git).parents[1] / "bin" / "bash.exe", Path(git).parents[1] / "usr" / "bin" / "bash.exe"):
        if candidate.is_file():
            return str(candidate)
    return None


@pytest.mark.skipif(os.name != "nt" or _git_bash() is None, reason="needs Git Bash")
def test_generate_sh_from_git_bash(project):
    """How Claude Code (Git Bash) calls it."""
    env = dict(os.environ, OFFLINE_VOICE_HOME=str(ROOT))
    r = run([_git_bash(), "-c", '"$OFFLINE_VOICE_HOME/generate.sh" --voice voice_1 --text "Hello from bash." '
                                '--output "narr bash.mp3"'], cwd=project, env=env)
    assert r.returncode == 0, r.stderr
    assert (project / "narr bash.mp3").is_file()


def test_json_result_and_request_routing(project):
    r = run([PY, str(GENERATE_PY), "--request", "Create a 60-second Facebook Reel using Voice 2",
             "--text", "Quick test.", "--output", "r.wav", "--json"], cwd=project)
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["voice_id"] == "voice_2" and Path(data["output"]).is_file() and data["stats"]["audible"]


def test_invalid_voice_exit_code(project):
    r = run([PY, str(GENERATE_PY), "--voice", "voice_7", "--text", "x", "--output", "x.mp3"], cwd=project)
    assert r.returncode == 2
    assert "Unknown voice" in r.stderr


def test_missing_script_exit_code(project):
    r = run([PY, str(GENERATE_PY), "--voice", "voice_1", "--input", "nope.txt", "--output", "x.mp3"], cwd=project)
    assert r.returncode == 2


def test_ffmpeg_can_mux_narration_into_video(project):
    r = run([PY, str(GENERATE_PY), "--voice", "voice_1", "--text", "Muxing test.", "--output", "n.mp3"], cwd=project)
    assert r.returncode == 0, r.stderr
    ffmpeg = find_ffmpeg()
    video = project / "final video.mp4"
    m = run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=320x240:r=25",
             "-i", r.stdout.strip(), "-shortest", "-c:v", "libx264", "-c:a", "aac", str(video)], cwd=project)
    assert m.returncode == 0, m.stderr
    assert video.is_file() and video.stat().st_size > 1000
