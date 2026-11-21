import qiro from "../../../benchmarks/results/qiro_optimality.json";
import traffic from "../../../benchmarks/results/traffic_rules_eval.json";

const percent = (value: number) => `${(value * 100).toFixed(1)}%`;

export function BenchmarksPage() {
  const qiroResult = qiro.annealing_plus_local_search;
  const trafficRows = traffic.results;

  return (
    <div className="stack" data-testid="benchmark-page">
      <div className="page-head">
        <div>
          <div className="page-title">Research results</div>
          <div className="page-sub">Reproducible optimizer benchmark and recorded traffic-rule evaluation.</div>
        </div>
      </div>

      <div className="notice" data-testid="benchmark-caveat">
        Simulations and rule-based findings are configuration-level research results, not evidence of clinical protection.
        The optimizer instances are synthetic. Traffic metrics come from a previously downloaded external test split;
        thresholds were selected after inspecting that same split, so they are not a generalization estimate.
      </div>

      <section className="card" data-testid="qiro-results">
        <div className="card-h">
          <span className="h">QIRO optimality vs. exhaustive search</span>
          <span className="pill">Seed 0 · {qiro.date} · Python {qiro.python}</span>
        </div>
        <div className="kpi-strip">
          <div className="kpi-card"><div className="label">Synthetic instances</div><div className="value">{qiro.instances_with_nonzero_optimum}</div></div>
          <div className="kpi-card"><div className="label">Optimal solutions</div><div className="value" data-testid="qiro-optimal-share">{percent(qiroResult.optimal_share)}</div></div>
          <div className="kpi-card"><div className="label">Mean optimality gap</div><div className="value">{qiroResult.mean_gap_pct.toFixed(4)}%</div></div>
          <div className="kpi-card"><div className="label">Mean runtime incl. exact solver</div><div className="value">{qiro.mean_optimize_ms_including_exact_solver.toFixed(2)} ms</div></div>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table className="t">
            <thead>
              <tr><th>Method</th><th>Optimal</th><th>Mean gap</th><th>95th percentile gap</th><th>Maximum gap</th></tr>
            </thead>
            <tbody>
              <tr>
                <td>Annealing only</td><td>{percent(qiro.annealing_only.optimal_share)}</td>
                <td>{qiro.annealing_only.mean_gap_pct.toFixed(4)}%</td>
                <td>{qiro.annealing_only.p95_gap_pct.toFixed(4)}%</td>
                <td>{qiro.annealing_only.max_gap_pct.toFixed(4)}%</td>
              </tr>
              <tr>
                <td>Annealing + local search</td><td>{percent(qiroResult.optimal_share)}</td>
                <td>{qiroResult.mean_gap_pct.toFixed(4)}%</td>
                <td>{qiroResult.p95_gap_pct.toFixed(4)}%</td>
                <td>{qiroResult.max_gap_pct.toFixed(4)}%</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="page-sub">{qiro.caveat} Runtime is hardware- and load-dependent; only the seeded objective metrics are intended to be reproducible.</p>
      </section>

      <section className="card" data-testid="traffic-results">
        <div className="card-h">
          <span className="h">Traffic-rule evaluation</span>
          <span className="pill">Recorded {traffic.date} · {traffic.window_rows}-row windows</span>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table className="t">
            <thead>
              <tr><th>Input file</th><th>Label</th><th>Windows</th><th>Flagged</th><th>Window flag rate</th><th>Metric</th></tr>
            </thead>
            <tbody>
              {trafficRows.map((row) => (
                <tr key={row.file}>
                  <td>{row.file}</td><td>{row.expected}</td><td>{row.windows}</td><td>{row.flagged_windows}</td>
                  <td>{percent(row.flag_rate)}</td><td>{row.metric === "false_positive_rate" ? "False-positive rate" : "Detection rate"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="page-sub">{traffic.caveat} The source dataset is not bundled. Download it separately to rerun this evaluation.</p>
      </section>
    </div>
  );
}
