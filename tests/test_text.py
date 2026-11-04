from offline_voice.text import segment_script, split_sentences


def words(text):
    return text.split()


def test_order_preserved_and_no_words_cut():
    script = ("First sentence here. Second one follows! Is this the third? Yes.\n\n"
              "A new paragraph starts. " + "This clause keeps going, and going, and going, " * 12 + "until it ends.")
    segs = segment_script(script, max_chars=120)
    assert words(" ".join(s.text for s in segs)) == words(script)
    assert all(len(s.text) <= 120 for s in segs)
    assert [s.index for s in segs] == list(range(len(segs)))


def test_abbreviations_and_initials_do_not_split():
    s = split_sentences("Dr. Smith met J. Watson at 5 p.m. on Main St. today. They talked.")
    assert s == ["Dr. Smith met J. Watson at 5 p.m. on Main St. today.", "They talked."]


def test_pauses_paragraph_vs_sentence_and_final():
    script = ("One. " * 80).strip() + "\n\nTwo paragraph."
    segs = segment_script(script, max_chars=100, sentence_pause_ms=200, paragraph_pause_ms=700)
    assert segs[-1].pause_after_ms == 0
    para_breaks = [s for s in segs if s.pause_after_ms == 700]
    assert len(para_breaks) == 1
    assert all(s.pause_after_ms in (0, 200, 700) for s in segs)


def test_long_word_runs_split_at_spaces():
    script = " ".join(["word"] * 400)  # no punctuation at all
    segs = segment_script(script, max_chars=100)
    assert all(len(s.text) <= 100 for s in segs)
    assert words(" ".join(s.text for s in segs)) == words(script)


def test_empty_and_whitespace_scripts():
    assert segment_script("") == []
    assert segment_script("  \n\n ﻿ ") == []


def test_unicode_script():
    segs = segment_script("Café owners love crème brûlée. “Quotes” work too… Right?")
    assert "Café" in segs[0].text
    assert words(" ".join(s.text for s in segs))[-1] == "Right?"
