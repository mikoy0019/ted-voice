import pytest

from offline_voice.config import (VOICE_IDS, VOICE_TYPES, ConfigError, default_voice_id, load_profile, load_profiles,
                                  load_settings)
from offline_voice.routing import select_voice


def test_exactly_two_voice_profiles_exist():
    profiles = load_profiles()
    assert set(profiles) == {"voice_1", "voice_2"}
    for vid, p in profiles.items():
        assert p.id == vid
        assert p.config_path.is_file()


def test_both_profiles_are_well_formed():
    settings = load_settings()
    for p in load_profiles().values():
        assert p.engine == settings.engine
        assert p.voice_type in VOICE_TYPES
        assert p.name and p.name.strip()
        assert 0.5 <= p.speed <= 2.0
        assert p.lang_code == "a" and p.language == "en-us"
        if p.voice_type == "preset_blend":
            assert abs(sum(p.preset_recipe.values()) - 1.0) < 1e-3
            assert p.preset_file is not None


def test_voice_names_are_distinct():
    names = [p.name.lower() for p in load_profiles().values()]
    assert len(set(names)) == 2


def test_exactly_one_default_voice():
    assert default_voice_id() in VOICE_IDS


def test_default_selection_when_nothing_specified():
    assert select_voice().voice_id == default_voice_id()


def test_explicit_selection_by_id_and_name():
    assert select_voice("voice_2").voice_id == "voice_2"
    assert select_voice("VOICE_1").voice_id == "voice_1"
    name2 = load_profile("voice_2").name
    assert select_voice(name2).voice_id == "voice_2"


@pytest.mark.parametrize("bad", ["voice_3", "voice", "", "elevenlabs"])
def test_invalid_voice_identifiers_are_rejected(bad):
    with pytest.raises(ConfigError):
        if bad == "":
            load_profile(bad)
        else:
            select_voice(bad)


def test_load_profile_rejects_unknown_id():
    with pytest.raises(ConfigError):
        load_profile("voice_9")
