"""Audio assembly, normalization and export (WAV / MP3 via FFmpeg)."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf


class AudioError(Exception):
    pass


def find_ffmpeg(configured: str = "") -> str | None:
    """Configured path > ffmpeg on PATH > ffmpeg bundled with imageio-ffmpeg in the venv."""
    if configured:
        p = Path(configured)
        return str(p) if p.is_file() else None
    on_path = shutil.which("ffmpeg")
    if on_path:
        return on_path
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def db_to_amp(db: float) -> float:
    return float(10 ** (db / 20.0))


def rms_dbfs(audio: np.ndarray) -> float:
    if audio.size == 0:
        return -120.0
    rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))))
    return 20 * np.log10(max(rms, 1e-9))


def trim_silence(audio: np.ndarray, sr: int, threshold_db: float = -45.0, keep_ms: int = 30) -> np.ndarray:
    """Trim leading/trailing silence only, keeping a little padding so word edges stay natural."""
    if audio.size == 0:
        return audio
    frame = max(1, int(sr * 0.01))
    n = len(audio) // frame
    if n == 0:
        return audio
    frames = audio[: n * frame].reshape(n, frame)
    levels = 20 * np.log10(np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1)) + 1e-9)
    voiced = np.where(levels > threshold_db)[0]
    if voiced.size == 0:
        return audio
    keep = int(sr * keep_ms / 1000)
    start = max(0, voiced[0] * frame - keep)
    end = min(len(audio), (voiced[-1] + 1) * frame + keep)
    return audio[start:end]


def fade_edges(audio: np.ndarray, sr: int, ms: int = 8) -> np.ndarray:
    n = min(len(audio) // 2, int(sr * ms / 1000))
    if n <= 0:
        return audio
    out = audio.copy()
    ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)
    out[:n] *= ramp
    out[-n:] *= ramp[::-1]
    return out


def assemble(pieces: list[tuple[np.ndarray, int]], sr: int) -> np.ndarray:
    """Concatenate (audio, pause_after_ms) pieces with silence between them."""
    parts: list[np.ndarray] = []
    for audio, pause_ms in pieces:
        parts.append(fade_edges(trim_silence(audio.astype(np.float32), sr), sr))
        if pause_ms > 0:
            parts.append(np.zeros(int(sr * pause_ms / 1000), dtype=np.float32))
    if not parts:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(parts)


def normalize(audio: np.ndarray, target_rms_dbfs: float = -20.0, peak_ceiling_dbfs: float = -1.0) -> np.ndarray:
    """Bring speech to a consistent loudness without ever exceeding the peak ceiling (no clipping)."""
    if audio.size == 0:
        return audio
    peak = float(np.max(np.abs(audio)))
    if peak < 1e-6:
        return audio
    gain = db_to_amp(target_rms_dbfs - rms_dbfs(audio))
    ceiling = db_to_amp(peak_ceiling_dbfs)
    if peak * gain > ceiling:
        gain = ceiling / peak
    return (audio * gain).astype(np.float32)


def write_audio(audio: np.ndarray, sr: int, output: Path, ffmpeg: str | None, mp3_bitrate: str = "192k") -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    fmt = output.suffix.lower()
    if fmt == ".wav":
        sf.write(str(output), audio, sr, subtype="PCM_16")
        return output
    if fmt != ".mp3":
        raise AudioError(f"Unsupported output format '{fmt}'. Use .mp3 or .wav")
    if not ffmpeg:
        raise AudioError("MP3 export needs FFmpeg. Run setup.bat, install FFmpeg, or write a .wav instead.")
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "narration.wav"
        sf.write(str(wav), audio, sr, subtype="PCM_16")
        cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav),
               "-codec:a", "libmp3lame", "-b:a", mp3_bitrate, str(output)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise AudioError(f"FFmpeg MP3 encode failed: {r.stderr.strip()}")
    return output


def read_audio(path: Path, ffmpeg: str | None = None, sr: int | None = None) -> tuple[np.ndarray, int]:
    """Read WAV/FLAC directly; decode anything else (MP3, M4A...) through FFmpeg. Returns mono float32."""
    try:
        if sr is None:
            data, rate = sf.read(str(path), dtype="float32", always_2d=True)
            return data.mean(axis=1), rate
    except Exception:
        pass
    if not ffmpeg:
        raise AudioError(f"Cannot decode {path.name} without FFmpeg")
    rate = sr or 44100
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", str(rate),
           "-f", "f32le", "-"]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise AudioError(f"FFmpeg could not decode {path}: {r.stderr.decode(errors='ignore').strip()}")
    return np.frombuffer(r.stdout, dtype=np.float32).copy(), rate


def speech_stats(audio: np.ndarray, sr: int) -> dict:
    """Simple checks that a file contains audible speech rather than silence or noise bursts."""
    frame = max(1, int(sr * 0.02))
    n = len(audio) // frame
    if n == 0:
        return {"duration_s": 0.0, "rms_dbfs": -120.0, "active_ratio": 0.0, "peak": 0.0, "audible": False}
    frames = audio[: n * frame].reshape(n, frame)
    levels = 20 * np.log10(np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1)) + 1e-9)
    active = float(np.mean(levels > -40.0))
    stats = {
        "duration_s": round(len(audio) / sr, 3),
        "rms_dbfs": round(rms_dbfs(audio), 2),
        "active_ratio": round(active, 3),
        "peak": round(float(np.max(np.abs(audio))), 4),
    }
    stats["audible"] = bool(stats["duration_s"] > 0.3 and stats["rms_dbfs"] > -45 and active > 0.2)
    return stats


def ffmpeg_can_decode(path: Path, ffmpeg: str | None) -> tuple[bool, str]:
    if not ffmpeg:
        return False, "FFmpeg not found"
    r = subprocess.run([ffmpeg, "-hide_banner", "-v", "error", "-i", str(path), "-f", "null", "-"],
                       capture_output=True, text=True)
    return r.returncode == 0 and not r.stderr.strip(), r.stderr.strip()
