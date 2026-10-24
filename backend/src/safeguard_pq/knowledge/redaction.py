"""Redaction helpers so evidence, logs, reports and LLM prompts never echo raw PHI or secrets."""

from __future__ import annotations

import re

from .patterns import PHI_RULES, SECRET_RULES

_MAX_EXCERPT = 120

# Names following a "patient name/id" label: mask the label's full name, not only the first token.
_NAME_AFTER_LABEL = re.compile(r"((?i:\bpatient\s+(?:name|id))[:\s]+)([A-Z][a-z'-]+(?:\s+[A-Z][a-z'-]+){0,3})")


def mask_token(value: str) -> str:
    """Keep the first two and last character so analysts can correlate without disclosure."""
    v = value.strip()
    if len(v) <= 4:
        return "*" * len(v)
    return f"{v[:2]}{'*' * min(len(v) - 3, 12)}{v[-1]}"


def redact(text: str) -> str:
    out = _NAME_AFTER_LABEL.sub(lambda m: f"{m.group(1)}[NAME:{mask_token(m.group(2))}]", str(text))
    for rule in [*SECRET_RULES, *PHI_RULES]:
        label = rule.type.upper()
        out = rule.pattern.sub(lambda m, label=label: f"[{label}:{mask_token(m.group(0))}]", out)
    return out


def excerpt(text: str, match: re.Match[str] | None = None, width: int = 40) -> str:
    """Redacted window around a match (or the start of the text)."""
    s = str(text)
    if match is not None:
        start, end = max(0, match.start() - width), min(len(s), match.end() + width)
        s = ("…" if start > 0 else "") + s[start:end] + ("…" if end < len(str(text)) else "")
    red = redact(s)
    return red if len(red) <= _MAX_EXCERPT else red[: _MAX_EXCERPT - 1] + "…"
