import { useEffect, useMemo, useState } from "react";
import { api } from "../../api/client";
import type { StandardsMap } from "../../api/types";
import { pretty } from "../../components/ui";

/** E12 (supplementary, not reported in the paper) — finding type → TIPPSS pillar(s) → deduction / score category → public reference (served by the API). */
export function StandardsMapSection() {
  const [map, setMap] = useState<StandardsMap | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [agent, setAgent] = useState<string>("all");

  useEffect(() => {
    let alive = true;
    api.standardsMap().then((m) => alive && setMap(m)).catch((e: Error) => alive && setError(e.message));
    return () => { alive = false; };
  }, []);

  const agents = useMemo(() => (map ? Array.from(new Set(map.rows.map((r) => r.agent))) : []), [map]);
  const rows = useMemo(() => (map ? map.rows.filter((r) => agent === "all" || r.agent === agent) : []), [map, agent]);

  if (error) {
    return <div className="error" data-testid="standards-offline">The standards map is served by the API (<span className="mono">GET /api/v1/standards-map</span>); start the backend to view it. ({error})</div>;
  }
  if (!map) return <div className="muted xs">Loading standards map…</div>;

  return (
    <div className="stack">
      <div className="notice" data-testid="standards-note">
        <strong>{map.standard}.</strong> {map.note}
      </div>

      <section className="card" data-testid="standards-coverage">
        <div className="card-h"><span className="h">Pillar coverage</span><span className="pill">{map.rows.length} finding types</span></div>
        <div className="kpi-strip">
          {Object.entries(map.pillar_coverage).map(([pillar, c]) => (
            <div className="kpi-card" key={pillar}>
              <div className="label">{pillar}</div>
              <div className="value">{c.finding_types}</div>
              <div className="hint2">{c.agents.map(pretty).join(", ")}</div>
            </div>
          ))}
        </div>
        <p className="page-sub">
          Pillar deductions by severity: {Object.entries(map.pillar_deductions).map(([k, v]) => `${k} −${v}`).join(" · ")}.
          PQ-score weights: {Object.entries(map.score_weights).map(([k, v]) => `${k} ${v.toFixed(2)}`).join(" · ")}.
        </p>
      </section>

      <section className="card">
        <div className="card-h">
          <span className="h">Traceability table</span>
          <label className="xs muted">Agent{" "}
            <select value={agent} onChange={(e) => setAgent(e.target.value)} data-testid="standards-agent-filter">
              <option value="all">all</option>
              {agents.map((a) => <option key={a} value={a}>{pretty(a)}</option>)}
            </select>
          </label>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table className="t mini" data-testid="standards-table">
            <thead>
              <tr>
                <th>Finding type</th><th>Agent</th><th>Severity</th><th>TIPPSS pillars (IEEE/UL 2933-2024)</th><th>Deduction</th>
                <th>Score category (weight)</th><th>Rationale</th><th>Public references</th><th>Technique</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.finding_type}>
                  <td className="mono">{r.finding_type}</td>
                  <td>{pretty(r.agent)}</td>
                  <td><span className={`sev sev-${r.severity}`}>{r.severity}</span></td>
                  <td>{r.pillars.join(", ")}</td>
                  <td>−{r.pillar_deduction}</td>
                  <td>{r.score_category ? `${r.score_category} (${r.score_weight?.toFixed(2)})` : "—"}</td>
                  <td className="xs">{r.rationale}</td>
                  <td className="xs">{r.references.map((x) => <div key={x.standard + x.ref}>{x.standard}: {x.ref}</div>)}</td>
                  <td className="xs">{r.attack_technique ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="page-sub">
          Clause numbers of IEEE/UL 2933-2024 are not publicly available; the mapping is at pillar level and does not imply conformance
          with the standard or any certification. Source: <span className="mono">knowledge/standards_map.py</span>.
        </p>
      </section>
    </div>
  );
}
