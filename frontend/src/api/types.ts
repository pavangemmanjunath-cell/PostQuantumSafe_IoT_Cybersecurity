export type Severity = "critical" | "high" | "medium" | "low" | "info";
export type EnvStatus = "SAFE" | "AT_RISK" | "UNSAFE";
export type AgentStatus = "pending" | "running" | "completed" | "skipped" | "failed";

export interface Evidence {
  source: string;
  rule: string;
  observed?: string | null;
  reference?: string | null;
}

export interface Finding {
  id: string;
  agent: string;
  severity: Severity;
  type: string;
  detail: string;
  tippss_mapping: string[];
  evidence: Evidence[];
  device_id?: string | null;
}

export interface ToolCall {
  tool: string;
  arguments: Record<string, unknown>;
  result_summary: string;
  duration_ms: number;
}

export interface AgentTrace {
  agent: string;
  title: string;
  status: "completed" | "skipped" | "failed";
  duration_ms: number;
  notes: string[];
  tool_calls: ToolCall[];
  finding_ids: string[];
  error?: string | null;
}

export interface QiroAction {
  id: string;
  finding_id: string;
  finding_type: string;
  severity: Severity;
  device_id?: string | null;
  description: string;
  remediation: string;
  mitigation?: string | null;
  risk_reduction: number;
  cost_usd: number;
  downtime_hrs: number;
  pqc_urgency: number;
  safety_criticality: number;
  tippss_weight: number;
  optimization_benefit: number;
  priority_rank?: number;
  selection_reason?: string;
  reason?: string;
}

export interface Qiro {
  algorithm: string;
  status?: string;
  seed?: number;
  selected_actions: QiroAction[];
  excluded_actions: QiroAction[];
  selection_count: number;
  excluded_count: number;
  total_cost_usd: number;
  total_downtime_hrs: number;
  budget_constraint_usd: number;
  downtime_constraint_hrs: number;
  budget_utilization_pct: number;
  downtime_utilization_pct: number;
  constraint_explanation: string;
  migration_phase_plan: Record<string, QiroAction[]>;
  optimality?: {
    heuristic_objective: number;
    annealing_objective?: number;
    exact_objective: number | null;
    gap_pct: number | null;
    exact_solver: string;
  } | null;
}

export interface Attribution {
  category: string;
  label: string;
  value: number;
  weight: number;
  contribution: number;
  share_pct: number;
  driver_finding_ids: string[];
}

export interface Outcome {
  pq_risk_score: number;
  verdict: string;
  environment_status: EnvStatus;
  weakest_pillar: string;
  weakest_pillar_score: number;
}

export interface Counterfactual {
  scenario: string;
  removed_type?: string;
  before: Outcome;
  after: Outcome;
  delta_pq_score?: number;
}

export interface CryptoEntry {
  field: string;
  value: string;
  display: string;
  kind: string;
  quantum_status: string;
  quantum_attack?: string | null;
  replacement?: string | null;
  references: string[];
  notes?: string;
}

export interface AssessmentResult {
  assessment_id: string;
  system_id: string;
  timestamp: string;
  domain: string;
  version: string;
  environment_status: EnvStatus;
  environment_reasons: string[];
  verdict: string;
  pq_risk_score: number;
  findings_count: number;
  findings: Finding[];
  tippss_scores: Record<string, { score: number; finding_ids: string[] }>;
  category_breakdown: Record<string, number>;
  crypto_inventory: CryptoEntry[];
  pq_posture: {
    readiness: string;
    readiness_reason: string;
    hybrid?: boolean;
    advisories: string[];
    mosca?: { x_data_lifetime_years: number; y_migration_years: number; z_years_to_crqc: number; at_risk: boolean } | null;
    protect_until_year?: number | null;
    transition_reference?: string;
  };
  qiro_optimization: Qiro;
  explanation: {
    method: string;
    summary: string[];
    score_attribution: Attribution[];
    raw_score: number;
    counterfactuals: Counterfactual[];
    plan_projection: Counterfactual & { remaining_findings: string[] };
    findings: { finding_id: string; remediation?: { decision: string; reason?: string; action_id: string } | null }[];
    binding_constraint?: string | null;
  };
  report: { markdown: string; generator: string; llm_provider?: string | null; llm_model?: string | null; llm_error?: string | null };
  trace: AgentTrace[];
  metadata: Record<string, unknown> & { seed?: number; scenario_summary?: string | null; disclaimer?: string };
}

export interface AgentInfo {
  id: string;
  title: string;
  description: string;
  layer: string;
  stage: number;
  tools: string[];
  reads: string[];
  required: boolean;
  parallel_group: boolean;
}

export interface ToolInfo {
  name: string;
  description: string;
  category: string;
  online: boolean;
  parameters: { properties?: Record<string, { type: string }>; required?: string[] };
}

export interface ScenarioInfo {
  id: string;
  title: string;
  summary: string;
  story: string;
  origin: string;
  request?: Record<string, unknown>;
}

export interface Health {
  status: string;
  version: string;
  llm: { provider: string; model: string | null };
  online_tools_enabled: boolean;
  replay_data_available: boolean;
  agents: number;
  tools: number;
}

export interface LiveStatus {
  status: "ok" | "warning" | "alert";
  alerts: string[];
  pq_readiness: string;
  hndl_exposed: boolean;
  risk: number;
  kex_pq: boolean;
  sig_pq: boolean;
  features: Record<string, number>;
}

export interface SimDevice {
  id: string;
  kind: string;
  label: string;
  zone: string;
  position: [number, number];
  domain: string;
  has_ai: boolean;
  shape: string;
  tls: Record<string, string | number>;
  cert_present: boolean;
  auth_status: string;
  failed_login_count: number;
  active_attacks: string[];
  mitigations: string[];
  prompt_count: number;
  live: LiveStatus;
  last_assessment?: { assessment_id: string; environment_status: EnvStatus; pq_risk_score: number; findings_count: number; tick: number } | null;
}

export interface SimEvent {
  seq: number;
  tick: number;
  level: "info" | "warning" | "danger" | "success";
  device_id: string | null;
  message: string;
}

export interface SimSnapshot {
  id: string;
  template: string;
  template_label: string;
  domain: string;
  seed: number;
  tick: number;
  data_source: string;
  assumptions: { migration_years: number; years_to_crqc: number };
  devices: SimDevice[];
  events: SimEvent[];
}

export interface SimCatalog {
  templates: { id: string; label: string; domain: string; device_count: number }[];
  attacks: { id: string; label: string; layer: string; description: string; surface: string; detected_by: string[]; blocked_by: string[]; requires_ai: boolean }[];
  mitigations: { id: string; label: string; layer: string; description: string }[];
  data_sources: string[];
}

export interface FleetReport {
  simulation_id: string;
  template_label: string;
  tick: number;
  environment_status: EnvStatus;
  counts: Record<EnvStatus, number>;
  mean_pq_risk_score: number;
  fleet_pillars: Record<string, number>;
  devices: {
    device_id: string;
    label: string;
    zone: string;
    assessment_id: string;
    environment_status: EnvStatus;
    pq_risk_score: number;
    pq_readiness: string;
    findings_count: number;
    top_issues: string[];
    active_attacks: string[];
  }[];
  fleet_plan: Qiro;
}

export interface StreamEvent {
  type: string;
  agent?: string;
  title?: string;
  text?: string;
  tool?: string;
  summary?: string;
  status?: string;
  duration_ms?: number;
  finding_count?: number;
  finding?: Finding;
  result?: AssessmentResult;
  detail?: string;
}
