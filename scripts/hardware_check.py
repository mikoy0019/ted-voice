"""Inspect the machine before installing or running the offline voice engine.

Usage:
    python scripts/hardware_check.py            # human-readable report
    python scripts/hardware_check.py --json     # machine-readable report
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from offline_voice.audio import find_ffmpeg  # noqa: E402
from offline_voice.paths import env_home_mismatch, home  # noqa: E402


def _run(cmd: list[str]) -> str | None:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def python_versions() -> list[str]:
    out = _run(["py", "-0p"]) if platform.system() == "Windows" else None
    if out:
        return [line.strip() for line in out.splitlines() if line.strip()]
    return [f"{platform.python_version()} {sys.executable}"]


def nvidia_gpus() -> list[dict]:
    out = _run(["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version",
                "--format=csv,noheader,nounits"])
    gpus = []
    for line in (out or "").splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 4:
            gpus.append({"name": parts[0], "vram_total_mb": int(float(parts[1])),
                         "vram_free_mb": int(float(parts[2])), "driver": parts[3]})
    if gpus:
        header = _run(["nvidia-smi"]) or ""
        for line in header.splitlines():
            if "CUDA Version" in line:
                cuda = line.split("CUDA Version:")[1].split("|")[0].strip()
                for g in gpus:
                    g["driver_cuda_version"] = cuda
    return gpus


def torch_info() -> dict:
    try:
        import torch
    except Exception as e:  # torch not installed yet
        return {"installed": False, "error": str(e).splitlines()[0]}
    info = {"installed": True, "version": torch.__version__, "cuda_build": torch.version.cuda,
            "cuda_available": torch.cuda.is_available()}
    if info["cuda_available"]:
        info["device"] = torch.cuda.get_device_name(0)
        free, total = torch.cuda.mem_get_info()
        info["vram_free_mb"] = free // 2**20
        info["vram_total_mb"] = total // 2**20
    return info


def cpu_name() -> str:
    if platform.system() == "Windows":
        try:
            import winreg

            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            return winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        except OSError:
            pass
    return platform.processor()


def memory() -> dict:
    try:
        import psutil

        vm = psutil.virtual_memory()
        return {"total_gb": round(vm.total / 2**30, 1), "available_gb": round(vm.available / 2**30, 2)}
    except Exception:
        return {}


def pip_check() -> str:
    r = subprocess.run([sys.executable, "-m", "pip", "check"], capture_output=True, text=True)
    return r.stdout.strip() or r.stderr.strip()


def build_report() -> dict:
    disk = shutil.disk_usage(home())
    ffmpeg = find_ffmpeg()
    gpus = nvidia_gpus()
    mem = memory()
    report = {
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "machine": platform.machine(),
        "cpu": f"{cpu_name()} ({os.cpu_count()} threads)",
        "python_running": f"{platform.python_version()} ({sys.executable})",
        "python_installed": python_versions(),
        "nvidia_gpus": gpus,
        "torch": torch_info(),
        "memory": mem,
        "disk_free_gb": round(disk.free / 2**30, 1),
        "ffmpeg": ffmpeg,
        "ffmpeg_on_path": shutil.which("ffmpeg"),
        "pip_check": pip_check(),
        "home": str(home()),
        "warnings": [],
    }
    w = report["warnings"]
    if mismatch := env_home_mismatch():
        w.append(mismatch)
    if not gpus:
        w.append("No NVIDIA GPU detected: inference will run on CPU (Kokoro is fast enough on CPU).")
    elif gpus[0]["vram_free_mb"] < 1500:
        w.append(f"Only {gpus[0]['vram_free_mb']} MB VRAM free. Close other GPU apps or set device=cpu.")
    if mem and mem.get("available_gb", 99) < 1.5:
        w.append(f"Only {mem['available_gb']} GB RAM available. Close other apps; generation will be slow "
                 "while Windows pages memory to disk.")
    if report["disk_free_gb"] < 5:
        w.append("Less than 5 GB free disk space; model + PyTorch need about 4 GB.")
    if not ffmpeg:
        w.append("FFmpeg not found: MP3 export and video muxing will not work until it is installed.")
    elif not report["ffmpeg_on_path"]:
        w.append("FFmpeg is only available inside the venv (imageio-ffmpeg). Video projects that call "
                 "'ffmpeg' directly need it on PATH: winget install Gyan.FFmpeg")
    if report["pip_check"] and "No broken requirements" not in report["pip_check"]:
        w.append("pip check reports dependency conflicts (see pip_check).")

    report["recommendation"] = (
        "Kokoro-82M (Apache-2.0 code and weights): ~330 MB checkpoint, <1 GB VRAM, real-time on CPU, "
        "commercial use allowed. Both voices share this single engine."
    )
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="print JSON")
    ap.add_argument("--save", action="store_true", help="also write config/hardware_report.json")
    args = ap.parse_args()
    report = build_report()
    if args.save:
        (home() / "config").mkdir(exist_ok=True)
        (home() / "config" / "hardware_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    print("OfflineVoice hardware check")
    print("=" * 60)
    for key in ("os", "cpu", "python_running"):
        print(f"{key:16}: {report[key]}")
    print(f"{'python versions':16}: " + "; ".join(report["python_installed"]))
    for g in report["nvidia_gpus"]:
        print(f"{'nvidia gpu':16}: {g['name']}  VRAM {g['vram_free_mb']}/{g['vram_total_mb']} MB free  "
              f"driver {g['driver']}  CUDA {g.get('driver_cuda_version', '?')}")
    t = report["torch"]
    print(f"{'pytorch':16}: " + (f"{t['version']} (CUDA build {t['cuda_build']}, cuda available: "
                                 f"{t['cuda_available']})" if t["installed"] else "not installed"))
    m = report["memory"]
    if m:
        print(f"{'ram':16}: {m['available_gb']} GB available of {m['total_gb']} GB")
    print(f"{'disk free':16}: {report['disk_free_gb']} GB at {report['home']}")
    print(f"{'ffmpeg':16}: {report['ffmpeg'] or 'NOT FOUND'}")
    print(f"{'pip check':16}: {report['pip_check']}")
    print(f"{'recommendation':16}: {report['recommendation']}")
    for warning in report["warnings"]:
        print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
