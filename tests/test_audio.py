import numpy as np
import pytest

from offline_voice.audio import (assemble, db_to_amp, ffmpeg_can_decode, find_ffmpeg, normalize, read_audio,
                                 speech_stats, write_audio)

SR = 24000


def fake_speech(seconds=2.0, seed=0):
    """Amplitude-modulated noise with gaps: crude stand-in for speech."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(SR * seconds)) / SR
    envelope = (np.sin(2 * np.pi * 3 * t) > -0.3).astype(np.float32)
    return (rng.normal(0, 0.1, t.size) * envelope).astype(np.float32)


def test_normalize_never_exceeds_ceiling():
    loud = fake_speech() * 20
    out = normalize(loud, target_rms_dbfs=-10, peak_ceiling_dbfs=-1.0)
    assert np.max(np.abs(out)) <= db_to_amp(-1.0) + 1e-6


def test_assemble_inserts_pauses():
    a, b = fake_speech(1.0, 1), fake_speech(1.0, 2)
    combined = assemble([(a, 500), (b, 0)], SR)
    # trimmed speech + 0.5 s pause; never longer than both inputs plus the pause
    assert len(combined) <= len(a) + len(b) + int(0.5 * SR)
    assert len(combined) >= int(0.5 * SR)


def test_silence_is_not_audible():
    assert speech_stats(np.zeros(SR * 2, dtype=np.float32), SR)["audible"] is False
    assert speech_stats(normalize(fake_speech()), SR)["audible"] is True


def test_wav_export_roundtrip(tmp_path):
    audio = normalize(fake_speech())
    out = write_audio(audio, SR, tmp_path / "x.wav", ffmpeg=None)
    back, sr = read_audio(out)
    assert sr == SR and abs(len(back) - len(audio)) <= 1


@pytest.mark.skipif(find_ffmpeg() is None, reason="FFmpeg not available")
def test_mp3_export_and_ffmpeg_can_consume(tmp_path):
    out = write_audio(normalize(fake_speech()), SR, tmp_path / "dir with spaces" / "x.mp3", find_ffmpeg())
    assert out.is_file() and out.stat().st_size > 1000
    ok, err = ffmpeg_can_decode(out, find_ffmpeg())
    assert ok, err


def test_unsupported_format_rejected(tmp_path):
    from offline_voice.audio import AudioError

    with pytest.raises(AudioError):
        write_audio(fake_speech(), SR, tmp_path / "x.ogg", find_ffmpeg())
