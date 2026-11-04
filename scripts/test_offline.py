"""Offline verification: generate with both voices while all outbound network access is blocked.

    python scripts/test_offline.py
    python scripts/test_offline.py --long      # also narrate a ~5-minute script with Voice 1

Every non-loopback socket connect and DNS lookup is intercepted for the whole process, so any
attempt to reach ElevenLabs, Hugging Face or anything else fails the test. Also records memory,
VRAM and inference time. Writes output/offline_test_report.json.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from offline_voice import offline_guard  # noqa: E402

offline_guard.install(block=True)  # before torch / kokoro / huggingface_hub are imported

from offline_voice.audio import ffmpeg_can_decode, find_ffmpeg  # noqa: E402
from offline_voice.paths import home  # noqa: E402

SAMPLES = {
    "voice_1": ("Space exploration began with a simple question: what is out there? Over the next few minutes, "
                "we'll follow the people who decided to find out."),
    "voice_2": "Here are five amazing facts about artificial intelligence. Number one will surprise you!",
}

LONG_PARAGRAPH = (
    "For most of human history, the night sky was a mystery we could only look at. Then, in the space of a single "
    "lifetime, we learned to leave the planet, walk on the Moon, and send machines to the edge of the solar system. "
    "Each step depended on the one before it, and each one was harder than it looked from the outside. "
    "Engineers had to invent new materials, new ways to navigate, and new ways to keep people alive in a place that "
    "does not want them there. Some of those solutions came from careful planning. Others came from late nights, "
    "failed tests, and stubborn curiosity.\n\n"
)


def rss_mb() -> float:
    import psutil

    return psutil.Process().memory_info().rss / 2**20


def peak_mb() -> float | None:
    import psutil

    info = psutil.Process().memory_info()
    peak = getattr(info, "peak_wset", None)
    return round(peak / 2**20, 1) if peak else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--long", action="store_true", help="add a ~5 minute long-form test")
    args = ap.parse_args()

    from offline_voice.generator import generate

    out_dir = home() / "output" / "offline_test"
    report: dict = {"network_blocked": True, "results": [], "rss_start_mb": round(rss_mb(), 1)}
    jobs = [(vid, text, out_dir / f"{vid}_offline.mp3") for vid, text in SAMPLES.items()]
    jobs.append(("voice_2", SAMPLES["voice_2"], out_dir / "voice_2_offline.wav"))
    if args.long:
        jobs.append(("voice_1", LONG_PARAGRAPH * 9, out_dir / "voice_1_long.mp3"))

    ffmpeg = find_ffmpeg()
    failed = False
    for vid, text, out in jobs:
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.reset_peak_memory_stats()
        except Exception:
            torch = None
        t0 = time.perf_counter()
        entry: dict = {"voice": vid, "output": str(out), "chars": len(text)}
        try:
            r = generate(text, vid, out, use_cache=False, progress=lambda _m: None)
            ok, err = ffmpeg_can_decode(Path(r.output), ffmpeg)
            entry.update(duration_s=r.duration_s, elapsed_s=r.elapsed_s, rtf=r.realtime_factor, device=r.device,
                         audible=r.stats["audible"], rms_dbfs=r.stats["rms_dbfs"], ffmpeg_decodes=ok)
            if torch is not None and torch.cuda.is_available():
                entry["vram_peak_mb"] = round(torch.cuda.max_memory_allocated() / 2**20, 1)
            entry["pass"] = bool(r.stats["audible"] and ok)
        except Exception as e:
            entry.update(error=f"{type(e).__name__}: {e}", elapsed_s=round(time.perf_counter() - t0, 2), **{"pass": False})
        failed |= not entry["pass"]
        report["results"].append(entry)
        status = "PASS" if entry["pass"] else "FAIL"
        detail = entry.get("error") or (f"{entry['duration_s']}s audio in {entry['elapsed_s']}s "
                                        f"(RTF {entry['rtf']}, {entry['device']})")
        print(f"{status} {vid} -> {out.name}: {detail}")

    report["blocked_network_attempts"] = list(offline_guard.blocked_attempts)
    report["rss_end_mb"] = round(rss_mb(), 1)
    report["peak_working_set_mb"] = peak_mb()
    if offline_guard.blocked_attempts:
        failed = True
        print(f"FAIL network: {len(offline_guard.blocked_attempts)} outbound attempt(s) were blocked: "
              f"{offline_guard.blocked_attempts[:5]}")
    else:
        print("PASS network: no outbound connection attempts")
    print(f"memory: RSS {report['rss_end_mb']} MB, peak working set {report['peak_working_set_mb']} MB")
    out_dir.mkdir(parents=True, exist_ok=True)
    (home() / "output" / "offline_test_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
