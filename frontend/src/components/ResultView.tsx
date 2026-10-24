import { useState } from "react";
import { api } from "../api/client";
import type { AssessmentResult, Finding, QiroAction } from "../api/types";
import { Gauge, Radar } from "./charts/Charts";
import { Markdown } from "./Markdown";
import { Kpi, Panel, pretty, Tabs, usd } from "./ui";

type ResultTab = "overview" | "pq" | "findings" | "xai" | "plan" | "report";

/** Six headline KPIs for one assessment. */
export function ResultKpis({ r }: { r: AssessmentResult }) {
  const critical = r.findings.filter((f) => f.severity === "critical").length;
  const [weakName, weak] = Object.entries(r.tippss_scores).reduce((m, [k, v]) => (v.score < m[1].score ? [k, v] : m), ["", { score: 101, finding_ids: [] as string[] }]);
  const q = r.qiro_optimization;
  return (
    <div className="kpi-strip">
      <Kpi label="Environment" value={r.environment_status.replace("_", " ")} tone={r.environment_status} hint={r.environment_status === "SAFE" ? "safe" : "not safe"} testId="kpi-status" />
      <Kpi label="PQ risk score" value={<>{r.pq_risk_score}<span className="faint small"> /100</span></>} hint={r.verdict} />
      <Kpi label="PQ readiness" value={r.pq_posture.readiness} hint={r.pq_posture.hybrid ? "hybrid key exchange" : `${r.crypto_inventory.length} primitives checked`} testId="pq-readiness" />
      <Kpi label="Findings" value={r.findings_count} hint={`${critical} critical`} />
      <Kpi label="Weakest pillar" value={weak.score < 100 ? `${weak.score}` : "100"} hint={weak.score < 100 ? weakName : "all six pillars at 100"} />
      <Kpi label="Remediation plan" value={`${q.selection_count} actions`} hint={`${usd(q.total_cost_usd)} · ${q.total_downtime_hrs}h`} />
    </div>
  );
}

export function VerdictBanner({ r }: { r: AssessmentResult }) {
  const safe = r.environment_status === "SAFE";
  return (
    <div className={`verdict slim ${r.environment_status}`} data-testid="verdict" data-status={r.environment_status}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="verdict-title">Is the environment safe? {safe ? "Yes" : "No"} — {r.environment_status.replace("_", " ")}</div>
        <div className="xs faint" style={{ marginTop: 3 }}>{r.system_id} · assessment {r.assessment_id} · v{r.version}</div>
      </div>
      <a className="btn btn-primary" href={api.reportUrl(r.assessment_id)} download data-testid="download-pdf">⤓ PDF report</a>
    </div>
  );
}

function FindingRow({ f, decision }: { f: Finding; decision?: { decision: string; reason?: string } | null }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <tr onClick={() => setOpen(!open)} style={{ cursor: "pointer" }} data-testid={`finding-${f.type}`}>
        <td><span className={`sev sev-${f.severity}`}>{f.severity}</span></td>
        <td><div style={{ fontWeight: 600 }}>{pretty(f.type)}</div><div className="xs muted">{f.detail}</div></td>
        <td className="xs muted">{f.tippss_mapping.join(", ")}</td>
        <td className="xs">{decision ? <span className={decision.decision === "selected" ? "status-SAFE" : "status-AT_RISK"}>{decision.decision}</span> : "—"}</td>
      </tr>
      {open && (
        <tr>
          <td colSpan={4}>
            {f.evidence.map((e, i) => (
              <div key={i} className="evidence">
                <div>{e.source} · {e.rule}</div>
                {e.observed && <div className="faint">observed: {e.observed}</div>}
                {e.reference && <div className="faint">ref: {e.reference}</div>}
              </div>
            ))}
          </td>
        </tr>
      )}
    </>
  );
}

export function QiroPlan({ q }: { q: AssessmentResult["qiro_optimization"] }) {
  const deviceCol = q.selected_actions.some((a) => a.device_id);
  const rows = (list: QiroAction[], deferred = false) => list.map((a) => (
    <tr key={a.id}>
      <td className="mono">{deferred ? "—" : a.priority_rank}</td>
      <td>{a.remediation}</td>
      {deviceCol && <td className="xs mono">{a.device_id}</td>}
      <td className="mono">{usd(a.cost_usd)}</td>
      <td className="mono">{a.downtime_hrs}h</td>
      {deferred && <td className="xs muted">{a.reason}</td>}
    </tr>
  ));
  return (
    <div className="stack">
      <div className="kpi-strip" style={{ marginBottom: 0 }}>
        <Kpi label="Actions selected" value={`${q.selection_count} / ${q.selection_count + q.excluded_count}`} />
        <Kpi label="Budget used" value={usd(q.total_cost_usd)} hint={`of ${usd(q.budget_constraint_usd)} (${q.budget_utilization_pct}%)`} />
        <Kpi label="Downtime used" value={`${q.total_downtime_hrs}h`} hint={`of ${q.downtime_constraint_hrs}h (${q.downtime_utilization_pct}%)`} />
        <Kpi label="Gap to optimum" value={q.optimality?.gap_pct == null ? "n/a" : `${q.optimality.gap_pct}%`} hint={q.optimality?.exact_objective == null ? "exact solver not run" : "exhaustive check"} />
      </div>
      {q.selected_actions.length > 0 ? (
        <table className="t">
          <thead><tr><th>#</th><th>Action</th>{deviceCol && <th>Device</th>}<th>Cost</th><th>Downtime</th></tr></thead>
          <tbody>{rows(q.selected_actions)}</tbody>
        </table>
      ) : <div className="empty">No remediation required.</div>}
      {q.excluded_actions.length > 0 && (
        <details>
          <summary>{q.excluded_actions.length} deferred action(s)</summary>
          <table className="t"><thead><tr><th /><th>Action</th>{deviceCol && <th>Device</th>}<th>Cost</th><th>Downtime</th><th>Reason</th></tr></thead>
            <tbody>{rows(q.excluded_actions, true)}</tbody></table>
        </details>
      )}
      <div className="hint">Costs and downtimes are illustrative placeholders.</div>
    </div>
  );
}

export function ResultView({ r }: { r: AssessmentResult }) {
  const [tab, setTab] = useState<ResultTab>("overview");
  const ex = r.explanation;
  const decisions = Object.fromEntries(ex.findings.map((f) => [f.finding_id, f.remediation]));
  const pillars = Object.fromEntries(Object.entries(r.tippss_scores).map(([k, v]) => [k, v.score]));
  const maxC = Math.max(...ex.score_attribution.map((a) => a.contribution), 1);
  const cfs = ex.counterfactuals.filter((c) => (c.delta_pq_score ?? 0) < 0).slice(0, 5);

  return (
    <div className="stack" data-testid="result-view">
      <VerdictBanner r={r} />
      <ResultKpis r={r} />
      <Tabs<ResultTab>
        active={tab}
        onChange={setTab}
        testPrefix="rtab"
        tabs={[
          { id: "overview", label: "Overview" },
          { id: "pq", label: "Post-Quantum" },
          { id: "findings", label: "Findings", count: r.findings_count },
          { id: "xai", label: "Explainability" },
          { id: "plan", label: "Remediation", count: r.qiro_optimization.selection_count },
          { id: "report", label: "Report" },
        ]}
      />

      {tab === "overview" && (
        <div className="cols-3">
          <Panel title="PQ risk"><div style={{ display: "grid", placeItems: "center" }}><Gauge value={r.pq_risk_score} label="post-quantum risk" /></div></Panel>
          <Panel title="TIPPSS pillars"><div style={{ display: "grid", placeItems: "center" }}><Radar scores={pillars} /></div></Panel>
          <Panel title="Why">
            <ul className="list-plain">{r.environment_reasons.map((x, i) => <li key={i}>{x}</li>)}</ul>
            {r.qiro_optimization.selected_actions.length > 0 && (
              <>
                <div className="layer-h" style={{ marginTop: 12 }}>First actions</div>
                <ol className="list-plain">{r.qiro_optimization.selected_actions.slice(0, 3).map((a) => <li key={a.id}>{a.remediation}</li>)}</ol>
              </>
            )}
          </Panel>
        </div>
      )}

      {tab === "pq" && (
        <Panel title="Cryptographic inventory" right={<span className="pill">{r.pq_posture.readiness}</span>}>
          {r.crypto_inventory.length ? (
            <table className="t">
              <thead><tr><th>Field</th><th>Value</th><th>Quantum status</th><th>Replacement</th></tr></thead>
              <tbody>
                {r.crypto_inventory.map((c) => (
                  <tr key={c.field}>
                    <td className="xs muted">{pretty(c.field)}</td>
                    <td className="mono">{c.value}</td>
                    <td className={`qs-${c.quantum_status}`}>{pretty(c.quantum_status)}{c.quantum_attack ? <span className="xs faint"> · {c.quantum_attack}</span> : null}</td>
                    <td className="xs">{c.replacement ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <div className="notice">No crypto configuration supplied — PQ posture unverified.</div>}
          {r.pq_posture.mosca && (
            <div className="small" style={{ marginTop: 10 }}>
              Mosca: {r.pq_posture.mosca.x_data_lifetime_years}y data + {r.pq_posture.mosca.y_migration_years}y migration vs {r.pq_posture.mosca.z_years_to_crqc}y to CRQC →{" "}
              <strong className={r.pq_posture.mosca.at_risk ? "status-UNSAFE" : "status-SAFE"}>{r.pq_posture.mosca.at_risk ? "at risk" : "within margin"}</strong>
            </div>
          )}
          <div className="hint" style={{ marginTop: 6 }}>{r.pq_posture.readiness_reason}</div>
        </Panel>
      )}

      {tab === "findings" && (
        <Panel title="Findings" right={<span className="xs faint">click a row for evidence</span>}>
          {r.findings.length ? (
            <table className="t" data-testid="findings">
              <thead><tr><th>Severity</th><th>Finding</th><th>Pillars</th><th>Plan</th></tr></thead>
              <tbody>{r.findings.map((f) => <FindingRow key={f.id} f={f} decision={decisions[f.id]} />)}</tbody>
            </table>
          ) : <div className="empty">No findings.</div>}
        </Panel>
      )}

      {tab === "xai" && (
        <div className="cols-2">
          <Panel title="Score attribution" right={<span className="pill">{ex.raw_score} → {r.pq_risk_score}</span>} testId="attribution">
            <div className="stack" style={{ gap: 10 }}>
              {ex.score_attribution.filter((a) => a.contribution > 0).map((a) => (
                <div key={a.category}>
                  <div className="spread small"><span>{a.label}</span><span className="mono">{a.contribution}</span></div>
                  <div className="bar"><span style={{ width: `${(a.contribution / maxC) * 100}%` }} /></div>
                </div>
              ))}
              {ex.score_attribution.every((a) => a.contribution === 0) && <div className="faint small">Score is zero — nothing to attribute.</div>}
            </div>
          </Panel>
          <Panel title="What if fixed?">
            <table className="t">
              <thead><tr><th>Fix</th><th>PQ score</th><th>Status</th></tr></thead>
              <tbody>
                {cfs.map((c) => (
                  <tr key={c.scenario}><td className="small">{pretty(c.removed_type ?? c.scenario)}</td><td className="mono">{c.before.pq_risk_score} → {c.after.pq_risk_score}</td><td className={`xs status-${c.after.environment_status}`}>{c.after.environment_status}</td></tr>
                ))}
                <tr><td className="small"><strong>Full QIRO plan</strong></td><td className="mono">{ex.plan_projection.before.pq_risk_score} → {ex.plan_projection.after.pq_risk_score}</td><td className={`xs status-${ex.plan_projection.after.environment_status}`}><strong>{ex.plan_projection.after.environment_status}</strong></td></tr>
              </tbody>
            </table>
          </Panel>
        </div>
      )}

      {tab === "plan" && <Panel title="Remediation plan · QIRO"><QiroPlan q={r.qiro_optimization} /></Panel>}

      {tab === "report" && (
        <Panel title="Executive narrative" right={<span className="pill">{r.report.generator}</span>}>
          <Markdown text={r.report.markdown} />
        </Panel>
      )}
    </div>
  );
}
