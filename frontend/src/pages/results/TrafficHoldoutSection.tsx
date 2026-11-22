import { useState } from "react";
import synthetic from "../../../../benchmarks/results/traffic_rules_holdout.json";
import cicP1 from "../../../../benchmarks/results/traffic_rules_holdout_cic_p1.json";
import cicP2 from "../../../../benchmarks/results/traffic_rules_holdout_cic_p2.json";

interface Metrics { precision: number; recall: number; f1: number; fpr: number }
interface Series {
  windows: number;
  confusion: { tp: number; fp: number; tn: number; fn: number };
  metrics: Metrics;
  bootstrap?: { ci95: Record<string, [number, number]> };
  per_class?: Record<string, { label: string; windows: number; flagged: number; rate: number; rate_meaning: string; wilson95: [number, number]; target_rule?: string; target_rule_rate?: number }>;
}
interface Run {
  protocol: string;
  data_source: string;
  development_source?: string;
  evaluation_source?: string;
  window_rows: number;
  results: { shipped_thresholds: Series; tuned_thresholds: Series; baselines: Record<string, Series> };
  tuning: { factors: number[]; rules: Record<string, { shipped: number[]; tuned: number[]; changed: boolean; dev_f1_tuned?: number; status?: string }> };
  caveat: string;
}

const RUNS: { id: string; label: string; run: Run }[] = [
  { id: "p1", label: "P1 · cross-source (synthetic dev → CICIoMT2024 test)", run: cicP1 as unknown as Run },
  { id: "p2", label: "P2 · temporal split within CICIoMT2024 test captures", run: cicP2 as unknown as Run },
  { id: "syn", label: "Synthetic train → synthetic test (protocol demonstration)", run: synthetic as unknown as Run },
];
const BASELINE_LABEL: Record<string, string> = {
  majority_class: "Majority class", rate_p99_benign: "Rate > benign p99 (dev)", tot_size_p1_p99_band_benign: "Packet size outside benign p1–p99 (dev)",
};
const pc = (x: number, d = 1) => `${(100 * x).toFixed(d)}%`;
const ci = (s: Series, m: keyof Metrics) => (s.bootstrap?.ci95[m] ? ` [${pc(s.bootstrap.ci95[m][0])}, ${pc(s.bootstrap.ci95[m][1])}]` : "");

/** E10 — traffic rules evaluated on windows that were not used for threshold selection. */
export function TrafficHoldoutSection() {
  const [id, setId] = useState("p1");
  const { run } = RUNS.find((r) => r.id === id) ?? RUNS[0];
  const series: [string, Series, boolean][] = [
    ["Shipped thresholds (not held-out on CIC data)", run.results.shipped_thresholds, false],
    ["Tuned on development split (held-out)", run.results.tuned_thresholds, true],
    ...Object.entries(run.results.baselines).map(([k, v]): [string, Series, boolean] => [`Baseline: ${BASELINE_LABEL[k] ?? k}`, v, false]),
  ];
  const tuned = run.results.tuned_thresholds;
  const changedRules = Object.entries(run.tuning.rules).filter(([, r]) => r.changed);

  return (
    <div className="stack">
      <section className="card" data-testid="holdout-results">
        <div className="card-h">
          <span className="h">E10 · Held-out evaluation of the traffic rules</span>
          <select value={id} onChange={(e) => setId(e.target.value)} data-testid="holdout-protocol">
            {RUNS.map((r) => <option key={r.id} value={r.id}>{r.label}</option>)}
          </select>
        </div>
        <div className="xs muted" style={{ marginBottom: 8 }}>
          Protocol <span className="mono">{run.protocol}</span> · development: {run.development_source ?? "—"} · evaluation: {run.evaluation_source ?? run.data_source} · {run.window_rows}-row windows
        </div>
        <div className="kpi-strip">
          <div className="kpi-card"><div className="label">Held-out F1 (tuned thresholds)</div><div className="value" data-testid="holdout-f1">{pc(tuned.metrics.f1)}</div><div className="hint2">95% bootstrap CI{ci(tuned, "f1")}</div></div>
          <div className="kpi-card"><div className="label">Held-out recall</div><div className="value">{pc(tuned.metrics.recall)}</div><div className="hint2">CI{ci(tuned, "recall")}</div></div>
          <div className="kpi-card"><div className="label">Held-out false-positive rate</div><div className="value">{pc(tuned.metrics.fpr)}</div><div className="hint2">CI{ci(tuned, "fpr")}</div></div>
          <div className="kpi-card"><div className="label">Test windows</div><div className="value">{tuned.windows}</div><div className="hint2">tp {tuned.confusion.tp} · fp {tuned.confusion.fp} · tn {tuned.confusion.tn} · fn {tuned.confusion.fn}</div></div>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table className="t mini" data-testid="holdout-table">
            <thead><tr><th>Predictor</th><th>Held-out?</th><th>Precision</th><th>Recall</th><th>F1</th><th>FPR</th></tr></thead>
            <tbody>
              {series.map(([name, s, held]) => (
                <tr key={name}>
                  <td>{name}</td><td>{held ? "yes" : name.startsWith("Baseline") ? "yes (fitted on dev)" : "no"}</td>
                  <td>{pc(s.metrics.precision)}<span className="xs muted">{ci(s, "precision")}</span></td>
                  <td>{pc(s.metrics.recall)}<span className="xs muted">{ci(s, "recall")}</span></td>
                  <td>{pc(s.metrics.f1)}<span className="xs muted">{ci(s, "f1")}</span></td>
                  <td>{pc(s.metrics.fpr)}<span className="xs muted">{ci(s, "fpr")}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="page-sub">
          Tuning: each rule's thresholds are multiplied by factors from {"{"}{run.tuning.factors.join(", ")}{"}"} on the development windows only (rule structure unchanged);
          {changedRules.length ? ` ${changedRules.length} rule(s) changed: ${changedRules.map(([k]) => k).join(", ")}.` : " no rule changed from the shipped thresholds."} {run.caveat}
        </p>
      </section>

      {tuned.per_class && (
        <section className="card" data-testid="holdout-per-class">
          <div className="card-h"><span className="h">Per-class rates on the held-out windows (tuned thresholds)</span><span className="pill">Wilson 95% intervals</span></div>
          <div style={{ overflowX: "auto" }}>
            <table className="t mini">
              <thead><tr><th>Class</th><th>Label</th><th>Windows</th><th>Flagged</th><th>Rate</th><th>Wilson 95%</th><th>Target rule</th><th>Target-rule rate</th></tr></thead>
              <tbody>
                {Object.entries(tuned.per_class).map(([cls, c]) => (
                  <tr key={cls}>
                    <td className="mono">{cls}</td><td>{c.label}</td><td>{c.windows}</td><td>{c.flagged}</td>
                    <td>{pc(c.rate)} <span className="xs muted">({c.rate_meaning.replaceAll("_", " ")})</span></td>
                    <td>[{pc(c.wilson95[0])}, {pc(c.wilson95[1])}]</td>
                    <td className="mono">{c.target_rule ?? "—"}</td><td>{c.target_rule_rate !== undefined ? pc(c.target_rule_rate) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
