"""Built-in demonstration scenarios (synthetic)."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any

from .simulation.fakes import fill_placeholders


@lru_cache
def load_scenarios() -> list[dict[str, Any]]:
    raw = resources.files("safeguard_pq.data").joinpath("scenarios.json").read_text(encoding="utf-8")
    return json.loads(fill_placeholders(raw))


def get_scenario(scenario_id: str) -> dict[str, Any] | None:
    return next((s for s in load_scenarios() if s["id"] == scenario_id), None)
