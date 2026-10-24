"""Text extraction helpers that preserve the v0 prototype's semantics."""

from __future__ import annotations

import json
from typing import Any


def js_stringify(value: Any) -> str:
    """Equivalent of JavaScript JSON.stringify for plain JSON data."""
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def prompt_text(p: Any, *, stringify_objects: bool) -> str:
    """Prompt entries may be strings or objects with ``prompt``/``text``."""
    if isinstance(p, str):
        return p
    if isinstance(p, dict):
        t = p.get("prompt") or p.get("text")
        if t:
            return str(t)
    return js_stringify(p) if stringify_objects else ""
