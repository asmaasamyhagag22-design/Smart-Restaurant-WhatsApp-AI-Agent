"""PII redaction (docs §10) — runs before any text reaches the LLM.

Regex hot path covering card numbers, national IDs, emails and phone numbers.
Redacted tokens are mapped back at render time via :func:`restore`. (spaCy NER
is the documented production upgrade for free-text addresses/names.)
"""
from __future__ import annotations

import re

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("CARD", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
    ("NID", re.compile(r"\b\d{14}\b")),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("PHONE", re.compile(r"(?<!\w)\+?\d[\d -]{8,}\d(?!\w)")),
]


def redact(text: str) -> tuple[str, dict[str, str]]:
    """Return ``(redacted_text, {token: original})``."""
    mapping: dict[str, str] = {}
    counter = {"n": 0}
    out = text

    for label, pattern in _PATTERNS:
        def _repl(m: re.Match[str], _label: str = label) -> str:
            counter["n"] += 1
            token = f"[{_label}_{counter['n']}]"
            mapping[token] = m.group(0)
            return token

        out = pattern.sub(_repl, out)

    return out, mapping


def restore(text: str, mapping: dict[str, str]) -> str:
    for token, original in mapping.items():
        text = text.replace(token, original)
    return text
