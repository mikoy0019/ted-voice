"""Download everything offline inference needs (run once by setup.bat; needs internet).

    python scripts/download_models.py           # download missing files
    python scripts/download_models.py --verify  # only check that everything is present

Downloads into the configured models_dir:
  * Kokoro-82M config + checkpoint (hexgrad/Kokoro-82M, Apache-2.0)
  * Kokoro English base voicepacks (used to design the two original voices)
  * spaCy en_core_web_sm (English text processing used by Kokoro's G2P)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from offline_voice.config import load_settings  # noqa: E402
from offline_voice.engines.kokoro_engine import CONFIG_FILE, MODEL_FILE, REPO_ID, kokoro_dir  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def spacy_model_present() -> bool:
    try:
        import spacy.util

        return spacy.util.is_package("en_core_web_sm")
    except ImportError:
        return False


def download(target: Path) -> None:
    from huggingface_hub import HfApi, hf_hub_download

    target.mkdir(parents=True, exist_ok=True)
    files = [CONFIG_FILE, MODEL_FILE]
    repo_files = HfApi().list_repo_files(REPO_ID)
    # American (a*) and British (b*) English voicepacks.
    files += sorted(f for f in repo_files if f.startswith("voices/") and f.endswith(".pt")
                    and Path(f).name[:1] in ("a", "b"))
    for f in files:
        dest = target / f
        if dest.is_file() and dest.stat().st_size > 0:
            continue
        print(f"downloading {REPO_ID}/{f}")
        hf_hub_download(repo_id=REPO_ID, filename=f, local_dir=str(target))
    manifest = {
        "repo_id": REPO_ID,
        "license": "Apache-2.0",
        "files": {f: {"bytes": (target / f).stat().st_size} for f in files},
        "model_sha256": sha256(target / MODEL_FILE),
    }
    (target / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if not spacy_model_present():
        print("installing spaCy en_core_web_sm")
        subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)


def verify(target: Path) -> list[str]:
    missing = [str(target / f) for f in (CONFIG_FILE, MODEL_FILE) if not (target / f).is_file()]
    if not list((target / "voices").glob("*.pt")):
        missing.append(str(target / "voices" / "*.pt"))
    if not spacy_model_present():
        missing.append("spaCy en_core_web_sm")
    return missing


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    target = kokoro_dir(load_settings())
    if not args.verify:
        download(target)
    missing = verify(target)
    if missing:
        print("MISSING:\n  " + "\n  ".join(missing), file=sys.stderr)
        return 3
    print(f"All offline model files present in {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
