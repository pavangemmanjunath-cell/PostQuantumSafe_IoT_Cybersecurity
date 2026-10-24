from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from safeguard_pq.api.app import create_app
from safeguard_pq.config import Settings
from safeguard_pq.domain.models import AssessmentResult
from safeguard_pq.orchestrator import AssessmentPipeline
from safeguard_pq.scenarios import get_scenario

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, llm_provider="none", online_tools_enabled=False)


@pytest.fixture
def client(settings: Settings) -> TestClient:
    with TestClient(create_app(settings)) as c:
        yield c


def assess(payload: dict[str, Any], settings: Settings | None = None) -> AssessmentResult:
    s = settings or Settings(_env_file=None)
    return asyncio.run(AssessmentPipeline(s).run(_validate(payload)))


def _validate(payload: dict[str, Any]):
    from safeguard_pq.domain.models import AssessmentRequest

    return AssessmentRequest.model_validate(payload)


def scenario_request(scenario_id: str) -> dict[str, Any]:
    s = get_scenario(scenario_id)
    assert s is not None, scenario_id
    return json.loads(json.dumps(s["request"]))


def types(result: AssessmentResult, agent: str | None = None) -> list[str]:
    return [f.type for f in result.findings if agent is None or f.agent == agent]
