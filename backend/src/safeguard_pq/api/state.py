"""Process-local application state (in-memory; nothing is written to disk)."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field

from ..config import Settings
from ..domain.models import AssessmentResult
from ..orchestrator import AssessmentPipeline
from ..simulation import SimulationStore


class AssessmentStore:
    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self._items: OrderedDict[str, AssessmentResult] = OrderedDict()

    def put(self, result: AssessmentResult) -> None:
        self._items[result.assessment_id] = result
        self._items.move_to_end(result.assessment_id)
        while len(self._items) > self.capacity:
            self._items.popitem(last=False)

    def get(self, assessment_id: str) -> AssessmentResult | None:
        return self._items.get(assessment_id)

    def recent(self, limit: int = 20) -> list[AssessmentResult]:
        return list(reversed(self._items.values()))[:limit]


@dataclass
class AppState:
    settings: Settings
    pipeline: AssessmentPipeline
    assessments: AssessmentStore
    simulations: SimulationStore = field(default_factory=SimulationStore)
    fleet_reports: dict[str, dict] = field(default_factory=dict)
