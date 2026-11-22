import sens from "../../../../benchmarks/results/sensitivity_analysis.json";

interface Metrics {
  verdict_change_share: number;
  status_change_share: number;
  mean_abs_delta_score: number;
  max_abs_delta_score: number;
  spearman_rank_correlation: number | null;
  mean_plan_jaccard: number | null;
}
interface ByThreshold { pq_risk_score: number; verdict: string; environment_status: string; findings: number; long_lifetime_finding: boolean }

const num =(x: number | null, d = 2) => (x === null || x === undefined ? "—" : x.toFixed(d));

/** E7 — sensitivity of verdicts, scores and plans to the scoring constants (ten scenarios). */
export function SensitivitySection() {
  const designs = sens.designs;
  const rows: { design: string; config: string; m: Metrics }[] = [
    ...designs.S1_category_weights.map((e) => ({ design: "S1 category weights", config: e.config, m: e.metrics as Metrics })),
    ...designs.S2_severity_points.map((e) => ({ design: "S2 severity points", config: e.config, m: e.metrics as Metrics })),
    ...designs.S3_pillar_deductions.map((e) => ({ design: "S3 pillar deductions", config: e.config, m: e.metrics as Metrics })),
    ...designs.S4_lifetime_threshold.configs.map((e) => ({ design: "S4 lifetime threshold", config: e.config, m: e.metrics as Metrics })),
    ...designs.S5_optimizer_pillar_weights.map((e) => ({ design: "S5 optimizer pillar weights", config: e.config, m: e.metrics as Metrics })),
  ];
  const n = sens.scenarios.length;
  const maxStatus = Math.max(...rows.map((r) => r.m.status_change_share));
  const maxVerdict = Math.max(...rows.map((r) => r.m.verdict_change_share));
  const weightRows = rows.filter((r) => r.design.startsWith("S1"));
  const maxWeightDelta = Math.max(...weightRows.map((r) => r.m.max_abs_delta_score));
  const minSpearman = Math.min(...rows.map((r) => r.m.spearman_rank_correlation ?? 1));
  const ls = designs.S4_lifetime_threshold.thresholds_years as number[];

  return (
    <div className="stack">
      <section className="card" data-testid="sensitivity-results">
        <div className="card-h">
          <span className="h">E7 · Sensitivity of the scoring model</span>
          <span className="pill">{n} scenarios · seed {sens.assessment_seed} · {sens.date}</span>
        </div>
        <div className="kpi-strip">
          <div className="kpi-card"><div className="label">Status flips, any perturbation</div><div className="value" data-testid="sensitivity-max-status">{Math.round(maxStatus * n)}/{n}</div><div className="hint2">SAFE / AT_RISK / UNSAFE; worst configuration</div></div>
          <div className="kpi-card"><div className="label">Verdict flips, worst configuration</div><div className="value">{Math.round(maxVerdict * n)}/{n}</div><div className="hint2">4-level verdict; threshold crossings near 25 / 50 / 75</div></div>
          <div className="kpi-card"><div className="label">Max |ΔS|, category weights ±20 %</div><div className="value">{maxWeightDelta} pts</div><div className="hint2">one weight at a time, renormalised</div></div>
          <div className="kpi-card"><div className="label">Rank correlation (min over configs)</div><div className="value">{num(minSpearman, 3)}</div><div className="hint2">Spearman ρ between baseline and perturbed rankings</div></div>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table className="t mini" data-testid="sensitivity-table">
            <thead>
              <tr><th>Design</th><th>Configuration</th><th>Verdict changes</th><th>Status changes</th><th>Mean |ΔS|</th><th>Max |ΔS|</th><th>Spearman ρ</th><th>Plan Jaccard</th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.design + r.config}>
                  <td>{r.design}</td><td className="mono">{r.config}</td>
                  <td>{Math.round(r.m.verdict_change_share * n)}/{n}</td>
                  <td>{Math.round(r.m.status_change_share * n)}/{n}</td>
                  <td>{num(r.m.mean_abs_delta_score)}</td><td>{num(r.m.max_abs_delta_score, 0)}</td>
                  <td>{num(r.m.spearman_rank_correlation, 4)}</td><td>{num(r.m.mean_plan_jaccard, 4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="page-sub">
          Weights are scaled one at a time and renormalised (S1); severity points and pillar deductions are scaled together (S2, S3);
          S4 re-runs the whole pipeline with the lifetime threshold L; S5 re-runs the planner with scaled pillar weights.
          Plan Jaccard compares selected-action sets (— where plans are not recomputed). {sens.caveat}
        </p>
      </section>

      <section className="card" data-testid="lifetime-sweep">
        <div className="card-h"><span className="h">Ten-year rule sweep (S4): PQ score and status per scenario</span><span className="pill">L ∈ {"{"}{ls.join(", ")}{"}"} years</span></div>
        <div style={{ overflowX: "auto" }}>
          <table className="t mini">
            <thead>
              <tr><th>Scenario</th><th>Data lifetime</th>{ls.map((L) => <th key={L}>L = {L} y</th>)}</tr>
            </thead>
            <tbody>
              {designs.S4_lifetime_threshold.per_scenario.map((row) => {
                const bt = row.by_threshold as Record<string, ByThreshold>;
                return (
                  <tr key={row.scenario}>
                    <td className="mono">{row.scenario}</td><td>{row.data_lifetime_years} y</td>
                    {ls.map((L) => {
                      const c = bt[String(L)];
                      return <td key={L}><strong>{c.pq_risk_score}</strong> <span className={`pill status-${c.environment_status}`}>{c.environment_status}</span>{c.long_lifetime_finding ? " ·HNDL" : ""}</td>;
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="page-sub">·HNDL marks the critical long-lifetime finding being raised at that threshold. The default L = 10 column reproduces the baseline exactly.</p>
      </section>
    </div>
  );
}
