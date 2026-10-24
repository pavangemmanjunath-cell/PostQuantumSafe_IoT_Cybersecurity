import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { AgentInfo, AssessmentResult, ScenarioInfo } from "../api/types";
import { AgentPipeline } from "../components/AgentPipeline";
import { ResultView } from "../components/ResultView";
import { Panel } from "../components/ui";
import { useAssessmentStream, type AgentLiveMap } from "../hooks/useAssessmentStream";

export function traceToLive(r: AssessmentResult): AgentLiveMap {
  const byId = Object.fromEntries(r.findings.map((f) => [f.id, f]));
  return Object.fromEntries(
    r.trace.map((t) => [t.agent, {
      status: t.status, notes: t.notes, durationMs: t.duration_ms,
      tools: t.tool_calls.map((c) => ({ tool: c.tool, summary: c.result_summary })),
      findings: t.finding_ids.map((id) => byId[id]).filter(Boolean),
    }]),
  );
}

export function LabPage({ agents }: { agents: AgentInfo[] }) {
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([]);
  const [selected, setSelected] = useState("icu_gateway_critical");
  const [text, setText] = useState("");
  const [budget, setBudget] = useState(100_000);
  const [downtime, setDowntime] = useState(40);
  const [mode, setMode] = useState<"scenario" | "upload">("scenario");
  const [file, setFile] = useState<File | null>(null);
  const [tlsProfile, setTlsProfile] = useState("none");
  const [localError, setLocalError] = useState<string | null>(null);
  const [uploadLive, setUploadLive] = useState<AgentLiveMap | null>(null);
  const stream = useAssessmentStream();

  useEffect(() => { api.scenarios().then(setScenarios).catch((e) => setLocalError(e.message)); }, []);
  useEffect(() => {
    api.scenario(selected).then((s) => {
      const req = s.request as { constraints?: { budget_usd: number; max_downtime_hrs: number } };
      setText(JSON.stringify(s.request, null, 2));
      if (req.constraints) { setBudget(req.constraints.budget_usd); setDowntime(req.constraints.max_downtime_hrs); }
    });
  }, [selected]);

  const run = async () => {
    setLocalError(null);
    setUploadLive(null);
    try {
      if (mode === "upload") {
        if (!file) return setLocalError("Choose a CSV file first.");
        const form = new FormData();
        form.append("file", file);
        form.append("tls_profile", tlsProfile);
        form.append("budget_usd", String(budget));
        form.append("max_downtime_hrs", String(downtime));
        stream.reset();
        const r = await api.upload(form);
        stream.setResult(r);
        setUploadLive(traceToLive(r));
        return;
      }
      const payload = JSON.parse(text);
      payload.constraints = { budget_usd: budget, max_downtime_hrs: downtime };
      await stream.run({ request: payload });
    } catch (e) {
      setLocalError(e instanceof SyntaxError ? `Invalid JSON: ${e.message}` : (e as Error).message);
    }
  };

  const current = scenarios.find((s) => s.id === selected);

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <div className="page-title">Assessment</div>
          <div className="page-sub">Run the 14 agents on one system and get a verdict, explanation and remediation plan.</div>
        </div>
      </div>

      <Panel title="Input" right={
        <div className="row">
          <button className={`btn btn-sm ${mode === "scenario" ? "btn-primary" : ""}`} onClick={() => setMode("scenario")}>Scenario</button>
          <button className={`btn btn-sm ${mode === "upload" ? "btn-primary" : ""}`} onClick={() => setMode("upload")} data-testid="mode-upload">CSV upload</button>
        </div>
      }>
        <div className="toolbar">
          {mode === "scenario" ? (
            <select value={selected} onChange={(e) => setSelected(e.target.value)} style={{ minWidth: 330 }} data-testid="scenario-select">
              {scenarios.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
            </select>
          ) : (
            <>
              <input type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files?.[0] ?? null)} data-testid="file-input" />
              <select value={tlsProfile} onChange={(e) => setTlsProfile(e.target.value)} title="Crypto profile of the capture point">
                <option value="none">Crypto: unknown</option>
                <option value="legacy">Crypto: legacy TLS 1.2</option>
                <option value="modern_classical">Crypto: TLS 1.3 classical</option>
                <option value="hybrid">Crypto: hybrid ML-KEM</option>
                <option value="pq_ready">Crypto: PQ-ready</option>
              </select>
            </>
          )}
          <label className="row small muted">Budget $<input type="number" min={0} step={5000} value={budget} onChange={(e) => setBudget(Number(e.target.value))} style={{ width: 110 }} data-testid="budget" /></label>
          <label className="row small muted">Downtime h<input type="number" min={0} value={downtime} onChange={(e) => setDowntime(Number(e.target.value))} style={{ width: 70 }} /></label>
          <button className="btn btn-primary" onClick={run} disabled={stream.running} data-testid="run-assessment">
            {stream.running ? "Running…" : "▶ Run assessment"}
          </button>
        </div>
        {mode === "scenario" && current && <div className="hint" style={{ marginTop: 8 }}>{current.summary}</div>}
        {mode === "scenario" && (
          <details style={{ marginTop: 8 }}>
            <summary>Advanced: edit request JSON</summary>
            <textarea value={text} onChange={(e) => setText(e.target.value)} rows={12} spellCheck={false} style={{ width: "100%" }} data-testid="request-json" />
          </details>
        )}
        {(localError || stream.error) && <div className="error" style={{ marginTop: 8 }}>{localError ?? stream.error}</div>}
      </Panel>

      <Panel title="Agents"><AgentPipeline agents={agents} live={uploadLive ?? stream.agents} /></Panel>

      {stream.result ? <ResultView r={stream.result} /> : (
        <div className="panel"><div className="empty">Choose a scenario or upload a CSV, then run the assessment.</div></div>
      )}
    </div>
  );
}
