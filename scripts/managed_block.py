"""Validate managed marker pairs before reads or writes."""
from __future__ import annotations


def bounds(text: str, begin: str, end: str):
    starts, ends = text.count(begin), text.count(end)
    if starts == ends == 0:
        return None
    if starts != 1 or ends != 1 or text.index(begin) >= text.index(end):
        raise ValueError("malformed managed block: expected exactly one ordered begin/end pair")
    return text.index(begin), text.index(end) + len(end)


def replace(text: str, block: str, begin: str, end: str) -> str:
    span = bounds(text, begin, end)
    if span is None:
        return text + ("\n\n" if text and not text.endswith("\n") else "\n" if text else "") + block + "\n"
    start, stop = span
    return text[:start] + block + text[stop:]
