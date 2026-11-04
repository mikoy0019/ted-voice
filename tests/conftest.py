import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from offline_voice import offline_guard  # noqa: E402

# Block the network for the whole test session, before kokoro / huggingface_hub get imported.
offline_guard.install(block=True)


def engine_ready() -> bool:
    try:
        from offline_voice.config import load_profiles, load_settings
        from offline_voice.engines import get_engine

        settings = load_settings()
        if get_engine(settings).missing_files():
            return False
        return all(p.preset_file and p.preset_file.is_file() for p in load_profiles().values())
    except Exception:
        return False


requires_engine = pytest.mark.skipif(not engine_ready(), reason="offline model not installed (run setup.bat)")
