"""Split narration scripts into speakable segments at natural boundaries."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Abbreviations that end in a period but do not end a sentence.
_ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc", "e.g", "i.e", "inc", "ltd",
    "co", "corp", "no", "fig", "approx", "dept", "est", "u.s", "u.k", "a.m", "p.m", "jan", "feb",
    "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec", "mt", "ft",
}

_SENTENCE_END = re.compile(r"([.!?…]+[\"'”’)\]]*)(\s+)")


@dataclass
class Segment:
    index: int
    text: str
    pause_after_ms: int


def clean_script(text: str) -> str:
    text = text.replace("﻿", "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_sentences(paragraph: str) -> list[str]:
    sentences: list[str] = []
    start = 0
    for m in _SENTENCE_END.finditer(paragraph):
        end = m.end(1)
        candidate = paragraph[start:end]
        last_word = re.findall(r"([A-Za-z.]+)[.]+[\"'”’)\]]*$", candidate)
        if last_word and last_word[0].lower().rstrip(".") in _ABBREVIATIONS:
            continue
        # A single capital letter followed by a period is usually an initial ("J. Smith").
        if re.search(r"(^|\s)[A-Z]\.$", candidate):
            continue
        sentences.append(candidate.strip())
        start = m.end()
    tail = paragraph[start:].strip()
    if tail:
        sentences.append(tail)
    return [s for s in (x.strip() for x in sentences) if s]


def _split_long(sentence: str, max_chars: int) -> list[str]:
    """Split an over-long sentence at clause punctuation, then at word boundaries. Never cuts words."""
    if len(sentence) <= max_chars:
        return [sentence]
    parts: list[str] = []
    clauses = re.split(r"(?<=[,;:—–])\s+", sentence)
    buf = ""
    for clause in clauses:
        if len(clause) > max_chars:
            if buf:
                parts.append(buf)
                buf = ""
            words = clause.split(" ")
            for w in words:
                if buf and len(buf) + 1 + len(w) > max_chars:
                    parts.append(buf)
                    buf = w
                else:
                    buf = f"{buf} {w}" if buf else w
            continue
        if buf and len(buf) + 1 + len(clause) > max_chars:
            parts.append(buf)
            buf = clause
        else:
            buf = f"{buf} {clause}" if buf else clause
    if buf:
        parts.append(buf)
    return parts


def segment_script(text: str, max_chars: int = 260, sentence_pause_ms: int = 250,
                   paragraph_pause_ms: int = 650) -> list[Segment]:
    """Return ordered segments. Short neighbouring sentences are grouped up to max_chars."""
    text = clean_script(text)
    if not text:
        return []
    segments: list[Segment] = []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    for p_index, paragraph in enumerate(paragraphs):
        paragraph = re.sub(r"\s*\n\s*", " ", paragraph)
        pieces: list[str] = []
        for sentence in split_sentences(paragraph):
            pieces.extend(_split_long(sentence, max_chars))
        # Group short sentences so the engine gets natural context, without exceeding max_chars.
        grouped: list[str] = []
        for piece in pieces:
            if grouped and len(grouped[-1]) + 1 + len(piece) <= max_chars:
                grouped[-1] = f"{grouped[-1]} {piece}"
            else:
                grouped.append(piece)
        for g_index, chunk in enumerate(grouped):
            last_in_paragraph = g_index == len(grouped) - 1
            is_final = last_in_paragraph and p_index == len(paragraphs) - 1
            pause = 0 if is_final else (paragraph_pause_ms if last_in_paragraph else sentence_pause_ms)
            segments.append(Segment(len(segments), chunk, pause))
    return segments
