"""Agent catalogue and execution plan.

Stages run in order; agents inside one stage are independent and run
concurrently. Findings from a stage are merged in the declared order, so
finding and action identifiers are deterministic.
"""

from __future__ import annotations

from .analysis import QIROAgent, RiskScoringAgent, TIPPSSMappingAgent
from .base import Agent
from .crypto import CryptoInventoryAgent, PQIdentificationAgent
from .detection import (
    ClinicalPrivacyAgent,
    DeviceIdentityAgent,
    PromptInjectionAgent,
    SafetyRiskAgent,
    SecretExposureAgent,
    TrafficAnomalyAgent,
)
from .explain import ExplainerAgent, ReporterAgent
from .intake import IntakeAgent

STAGES: list[list[type[Agent]]] = [
    [IntakeAgent],
    [CryptoInventoryAgent],
    [PQIdentificationAgent],
    [ClinicalPrivacyAgent, DeviceIdentityAgent, PromptInjectionAgent, SecretExposureAgent, SafetyRiskAgent, TrafficAnomalyAgent],
    [TIPPSSMappingAgent],
    [RiskScoringAgent],
    [QIROAgent],
    [ExplainerAgent],
    [ReporterAgent],
]

# Agents that cannot be disabled because later stages depend on their artifacts.
REQUIRED_AGENTS = {"intake", "pq_identification", "tippss_mapping", "risk_scoring", "qiro_optimizer", "explainer", "reporter"}


def all_agents() -> list[type[Agent]]:
    return [a for stage in STAGES for a in stage]


def describe_agents() -> list[dict]:
    out = []
    for i, stage in enumerate(STAGES):
        for a in stage:
            out.append({**a.spec.describe(), "stage": i, "parallel_group": len(stage) > 1, "required": a.spec.id in REQUIRED_AGENTS})
    return out
