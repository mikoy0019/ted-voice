import pytest

from offline_voice.config import ConfigError, default_voice_id
from offline_voice.routing import select_voice


@pytest.mark.parametrize("request_text, expected", [
    ("Create a 60-second Facebook Reel about artificial intelligence using Voice 2.", "voice_2"),
    ("Create a 5-minute YouTube documentary about space exploration using Voice 1.", "voice_1"),
    ("Create a Facebook Reel using voice one", "voice_1"),           # explicit voice beats content keywords
    ("Make a TikTok about cats", "voice_2"),
    ("Make a YouTube Short about the ocean", "voice_2"),
    ("Write a documentary about whales", "voice_1"),
    ("Make an educational explainer on batteries", "voice_1"),
    ("Make a promo for my bakery", "voice_2"),
    ("Make an educational TikTok", "voice_2"),                        # platform rules sit above genre rules
])
def test_request_routing(request_text, expected):
    assert select_voice(request=request_text).voice_id == expected


def test_default_voice_phrase():
    sel = select_voice(request="Create three short videos using my default voice.")
    assert sel.voice_id == default_voice_id()


def test_unmatched_request_uses_default():
    assert select_voice(request="Narrate this paragraph").voice_id == default_voice_id()


@pytest.mark.parametrize("content_type, expected", [
    ("youtube_long_form", "voice_1"), ("Documentary", "voice_1"), ("educational", "voice_1"),
    ("storytelling", "voice_1"), ("facebook reels", "voice_2"), ("tiktok", "voice_2"),
    ("youtube-shorts", "voice_2"), ("promotional", "voice_2"),
])
def test_content_type_table(content_type, expected):
    assert select_voice(content_type=content_type).voice_id == expected


def test_explicit_voice_overrides_content_type():
    assert select_voice("voice_1", content_type="tiktok").voice_id == "voice_1"


def test_unknown_content_type_is_rejected():
    with pytest.raises(ConfigError):
        select_voice(content_type="podcast_ads_xyz")
