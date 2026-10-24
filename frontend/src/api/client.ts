import type {
  AgentInfo,
  AssessmentResult,
  FleetReport,
  Health,
  ScenarioInfo,
  SimCatalog,
  SimDevice,
  SimSnapshot,
  ToolInfo,
} from "./types";

const BASE = "/api/v1";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  health: () => request<Health>("/health"),
  agents: () => request<AgentInfo[]>("/agents"),
  tools: () => request<ToolInfo[]>("/tools"),
  callTool: (name: string, args: Record<string, unknown>) =>
    request<{ tool: string; summary: string; result: unknown }>(`/tools/${encodeURIComponent(name)}`, json(args)),
  scenarios: () => request<ScenarioInfo[]>("/scenarios"),
  scenario: (id: string) => request<ScenarioInfo>(`/scenarios/${id}`),
  assess: (payload: unknown) => request<AssessmentResult>("/assessments", json(payload)),
  upload: (form: FormData) => request<AssessmentResult>("/uploads/assess", { method: "POST", body: form }),
  reportUrl: (id: string) => `${BASE}/assessments/${id}/report.pdf`,

  simCatalog: () => request<SimCatalog>("/simulations/catalog"),
  createSim: (template: string, seed: number, data_source = "synthetic") =>
    request<SimSnapshot>("/simulations", json({ template, seed, data_source })),
  inject: (sid: string, device_id: string, attack: string) =>
    request<{ event: { message: string; blocked?: boolean }; device: SimDevice }>(`/simulations/${sid}/attacks`, json({ device_id, attack })),
  clearAttack: (sid: string, device_id: string, attack: string) =>
    request<{ device: SimDevice }>(`/simulations/${sid}/attacks/${device_id}/${attack}`, { method: "DELETE" }),
  mitigate: (sid: string, mitigation: string, device_id: string | null) =>
    request<{ snapshot: SimSnapshot }>(`/simulations/${sid}/mitigations`, json({ mitigation, device_id })),
  applyPlan: (sid: string, action_mitigations: { mitigation: string | null | undefined; device_id: string | null | undefined }[]) =>
    request<{ snapshot: SimSnapshot; events: { message: string }[] }>(`/simulations/${sid}/apply-plan`, json({ action_mitigations })),
  setAssumptions: (sid: string, migration_years: number, years_to_crqc: number) =>
    request<SimSnapshot>(`/simulations/${sid}/assumptions`, json({ migration_years, years_to_crqc })),
  assessFleet: (sid: string, budget_usd: number, max_downtime_hrs: number) =>
    request<FleetReport>(`/simulations/${sid}/assess`, json({ budget_usd, max_downtime_hrs })),
  fleetReportUrl: (sid: string) => `${BASE}/simulations/${sid}/report.pdf`,
};

export function wsUrl(path: string): string {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}${BASE}${path}`;
}
