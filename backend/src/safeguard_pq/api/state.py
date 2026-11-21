"""Process-local application state (in-memory; nothing is written to disk)."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field

from ..config import Settings
from ..domain.models import AssessmentRequest, AssessmentResult
from ..orchestrator import AssessmentPipeline
from ..simulation import SimulationStore


class AssessmentStore:
    """Recent results, plus the request each one was run on so its plan can be reassessed later."""

    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self._items: OrderedDict[str, AssessmentResult] = OrderedDict()
        self._requests: dict[str, AssessmentRequest] = {}

    def put(self, result: AssessmentResult, request: AssessmentRequest | None = None) -> None:
        self._items[result.assessment_id] = result
        self._items.move_to_end(result.assessment_id)
        if request is not None:
            self._requests[result.assessment_id] = request.model_copy(deep=True)
        while len(self._items) > self.capacity:
            evicted, _ = self._items.popitem(last=False)
            self._requests.pop(evicted, None)

    def get(self, assessment_id: str) -> AssessmentResult | None:
        return self._items.get(assessment_id)

    def request_for(self, assessment_id: str) -> AssessmentRequest | None:
        return self._requests.get(assessment_id)

    def recent(self, limit: int = 20) -> list[AssessmentResult]:
        return list(reversed(self._items.values()))[:limit]


@dataclass
class AppState:
    settings: Settings
    pipeline: AssessmentPipeline
    assessments: AssessmentStore
    simulations: SimulationStore = field(default_factory=SimulationStore)
    fleet_reports: dict[str, dict] = field(default_factory=dict)
