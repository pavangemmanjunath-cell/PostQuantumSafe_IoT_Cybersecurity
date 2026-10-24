"""Typed request / result contracts shared by agents, API and reports."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["critical", "high", "medium", "low", "info"]
PILLARS: tuple[str, ...] = ("Trust", "Identity", "Privacy", "Protection", "Safety", "Security")
EnvironmentStatus = Literal["SAFE", "AT_RISK", "UNSAFE"]


# --------------------------------------------------------------------------- inputs


class TLSConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    tls_version: str | None = None
    key_exchange: str | None = None
    cert_signature_algo: str | None = None
    cert_key_algo: str | None = None
    symmetric_cipher: str | None = None
    hash: str | None = None
    data_lifetime_years: float | None = Field(default=None, ge=0, le=200)


class Constraints(BaseModel):
    budget_usd: float = Field(default=100_000, ge=0)
    max_downtime_hrs: float = Field(default=40, ge=0)


class Assumptions(BaseModel):
    """Explicit, user-adjustable assumptions for Mosca's inequality (informational only)."""

    migration_years: float = Field(default=5, ge=0, le=50, description="Assumed time to complete PQ migration.")
    years_to_crqc: float = Field(
        default=10,
        ge=0,
        le=100,
        description="Assumed years until a cryptographically relevant quantum computer exists. Highly uncertain.",
    )


class RunOptions(BaseModel):
    disabled_agents: list[str] = Field(default_factory=list)
    llm_report: bool = True
    pace_ms: int = Field(default=0, ge=0, le=2000, description="Presentation delay between agent events (UI demo only).")


class AssessmentRequest(BaseModel):
    """One system (gateway, device, AI service) to assess."""

    model_config = ConfigDict(extra="allow")

    system_id: str | None = None
    domain: str = "healthcare"
    scenario_summary: str | None = None
    source_file: str | None = None
    tls_config: TLSConfig | None = None
    iot_traffic: dict[str, Any] | None = None
    ehr_records: dict[str, Any] | None = None
    ai_prompt_logs: list[Any] | str | dict[str, Any] | None = None
    device_logs: list[Any] | dict[str, Any] | None = None
    constraints: Constraints = Field(default_factory=Constraints)
    assumptions: Assumptions = Field(default_factory=Assumptions)
    options: RunOptions = Field(default_factory=RunOptions)
    seed: int | None = None


# --------------------------------------------------------------------------- outputs


class Evidence(BaseModel):
    source: str = Field(description="Where in the input the evidence was found, e.g. 'ai_prompt_logs[1]'.")
    rule: str = Field(description="Rule or knowledge-base entry that fired.")
    observed: str | None = Field(default=None, description="Redacted excerpt of the observed value.")
    reference: str | None = Field(default=None, description="Standard or source supporting the rule.")


class Finding(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = ""
    agent: str
    severity: Severity
    type: str
    detail: str
    tippss_mapping: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class ToolCall(BaseModel):
    tool: str
    arguments: dict[str, Any]
    result_summary: str
    duration_ms: float


class AgentTrace(BaseModel):
    agent: str
    title: str
    status: Literal["completed", "skipped", "failed"]
    started_at: str
    duration_ms: float
    notes: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    finding_ids: list[str] = Field(default_factory=list)
    error: str | None = None


class AssessmentResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    assessment_id: str
    system_id: str
    timestamp: str
    domain: str
    version: str
    environment_status: EnvironmentStatus
    environment_reasons: list[str]
    verdict: str
    pq_risk_score: int
    findings_count: int
    findings: list[Finding]
    tippss_scores: dict[str, dict[str, Any]]
    category_breakdown: dict[str, float]
    weights: dict[str, float]
    crypto_inventory: list[dict[str, Any]]
    pq_posture: dict[str, Any]
    qiro_optimization: dict[str, Any]
    explanation: dict[str, Any]
    report: dict[str, Any]
    trace: list[AgentTrace]
    metadata: dict[str, Any]
