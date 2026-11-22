import scal from "../../../../benchmarks/results/qiro_scalability.json";

interface MethodStats { optimal_share: number; mean_gap_pct: number; p95_gap_pct: number; max_gap_pct: number; mean_runtime_ms: number | null; max_runtime_ms: number | null }
interface SizeBlock {
  instances: number;
  instances_with_nonzero_ilp_optimum: number;
  methods: Record<string, MethodStats> & { ilp: { mean_runtime_ms: number; max_runtime_ms: number; statuses: Record<string, number> } };
  runtime_ratio_heuristic_over_ilp: number;
  iterations_run: number;
}

const METHODS: [string, string][] = [
  ["greedy", "Greedy only"],
  ["annealing", "Greedy + annealing"],
  ["greedy_local_search", "Greedy + local search"],
  ["annealing_local_search", "Shipped (greedy + annealing + local search)"],
];
const pct = (x: number) => `${(100 * x).toFixed(0)}%`;
const f = (x: number | null, d = 2) => (x === null || x === undefined ? "—" : x.toFixed(d));

/** E8 — optimizer quality and runtime on larger instances against an integer-programming (HiGHS) reference. */
export function ScalabilitySection() {
  const bySize = scal.by_size as unknown as Record<string, SizeBlock>;
  const byTau = scal.by_tau as unknown as Record<string, SizeBlock>;
  const sizes = Object.keys(bySize).map(Number).sort((a, b) => a - b);
  const largest = bySize[String(sizes[sizes.length - 1])];
  const shippedLargest = largest.methods.annealing_local_search;
  const check = scal.small_check;

  return (
    <div className="stack">
      <section className="card" data-testid="scalability-results">
        <div className="card-h">
          <span className="h">E8 · Scalability versus an integer-programming reference</span>
          <span className="pill">{scal.solver} · seed {scal.seed} · {scal.date}</span>
        </div>
        <div className="kpi-strip">
          <div className="kpi-card"><div className="label">ILP cross-check (n ≤ 14)</div><div className="value" data-testid="ilp-crosscheck">{check.agreeing}/{check.instances}</div><div className="hint2">ILP optimum equals the exhaustive optimum (tolerance {check.tolerance})</div></div>
          <div className="kpi-card"><div className="label">Shipped planner, n = {sizes[sizes.length - 1]}</div><div className="value">{pct(shippedLargest.optimal_share)} optimal</div><div className="hint2">mean gap {f(shippedLargest.mean_gap_pct, 3)}% · max {f(shippedLargest.max_gap_pct, 2)}%</div></div>
          <div className="kpi-card"><div className="label">Runtime, n = {sizes[sizes.length - 1]}</div><div className="value">{f(shippedLargest.mean_runtime_ms, 0)} ms</div><div className="hint2">ILP {f(largest.methods.ilp.mean_runtime_ms, 0)} ms · ratio {f(largest.runtime_ratio_heuristic_over_ilp, 2)}×</div></div>
          <div className="kpi-card"><div className="label">Instances</div><div className="value">{scal.total_instances}</div><div className="hint2">{sizes.map((n) => `n=${n}: ${bySize[String(n)].instances}`).join(" · ")}</div></div>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table className="t mini" data-testid="scalability-table">
            <thead>
              <tr><th>n</th><th>Method</th><th>Optimal</th><th>Mean gap</th><th>p95 gap</th><th>Max gap</th><th>Mean runtime</th></tr>
            </thead>
            <tbody>
              {sizes.map((n) => {
                const b = bySize[String(n)];
                return [
                  ...METHODS.map(([key, label]) => {
                    const m = b.methods[key];
                    return (
                      <tr key={`${n}-${key}`}>
                        <td>{n}</td><td>{label}</td><td>{pct(m.optimal_share)}</td><td>{f(m.mean_gap_pct, 3)}%</td>
                        <td>{f(m.p95_gap_pct, 3)}%</td><td>{f(m.max_gap_pct, 2)}%</td><td>{f(m.mean_runtime_ms, 2)}{m.mean_runtime_ms === null ? "" : " ms"}</td>
                      </tr>
                    );
                  }),
                  <tr key={`${n}-ilp`} className="faint">
                    <td>{n}</td><td>ILP reference (HiGHS)</td><td>100% (proven)</td><td>0</td><td>0</td><td>0</td><td>{f(b.methods.ilp.mean_runtime_ms, 2)} ms</td>
                  </tr>,
                ];
              })}
            </tbody>
          </table>
        </div>
        <p className="page-sub">
          Gap = 100 · (f<sub>ILP</sub> − f<sub>method</sub>) / f<sub>ILP</sub>. Budgets and downtime are τ · Σ cost and τ · Σ downtime with τ ∈ {"{"}0.25, 0.5, 0.75{"}"}.
          Annealing is not timed separately (it is a stage inside the shipped pipeline). Runtimes are single-machine wall-clock measurements. {scal.caveat}
        </p>
      </section>

      <section className="card" data-testid="scalability-tau">
        <div className="card-h"><span className="h">Effect of constraint tightness τ (all sizes pooled)</span></div>
        <div style={{ overflowX: "auto" }}>
          <table className="t mini">
            <thead><tr><th>τ</th><th>Instances</th><th>Greedy optimal</th><th>Shipped optimal</th><th>Shipped mean gap</th><th>Shipped max gap</th></tr></thead>
            <tbody>
              {Object.entries(byTau).map(([tau, b]) => (
                <tr key={tau}>
                  <td>{tau}</td><td>{b.instances}</td><td>{pct(b.methods.greedy.optimal_share)}</td>
                  <td>{pct(b.methods.annealing_local_search.optimal_share)}</td>
                  <td>{f(b.methods.annealing_local_search.mean_gap_pct, 3)}%</td><td>{f(b.methods.annealing_local_search.max_gap_pct, 2)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
