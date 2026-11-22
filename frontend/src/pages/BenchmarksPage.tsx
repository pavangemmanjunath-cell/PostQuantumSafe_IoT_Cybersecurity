import { useState } from "react";
import paperE1 from "../../../benchmarks/results/paper_e1_systems.json";
import paperE2 from "../../../benchmarks/results/paper_e2_attack_conditions.json";
import paperE3 from "../../../benchmarks/results/paper_e3_qday_sweep.json";
import paperE4 from "../../../benchmarks/results/paper_e4_budget_sweep.json";
import paperE5 from "../../../benchmarks/results/paper_e5_worked_example.json";
import qiro from "../../../benchmarks/results/qiro_optimality.json";
import traffic from "../../../benchmarks/results/traffic_rules_eval.json";
import { Tabs } from "../components/ui";
import { AttackSimulationSection } from "./results/AttackSimulationSection";
import { ReassessmentSection } from "./results/ReassessmentSection";
import { ScalabilitySection } from "./results/ScalabilitySection";
import { SensitivitySection } from "./results/SensitivitySection";
import { StandardsMapSection } from "./results/StandardsMapSection";
import { TrafficHoldoutSection } from "./results/TrafficHoldoutSection";

const percent = (value: number) => `${(value * 100).toFixed(1)}%`;

type Section = "overview" | "optimizer" | "scalability" | "sensitivity" | "reassessment" | "traffic" | "holdout" | "attacks" | "standards";

const SECTIONS: { id: Section; label: string }[] = [
  ["overview", "Overview"],
  ["optimizer", "Optimizer (E4)"],
  ["scalability", "Scalability vs ILP (E8)"],
  ["sensitivity", "Sensitivity (E7)"],
  ["reassessment", "Reassessment (E9)"],
  ["traffic", "Traffic rules, same split (E6)"],
  ["holdout", "Traffic rules, held-out (E10)"],
  ["attacks", "Attack simulation (E11, supplementary)"],
  ["standards", "Standards map (E12, supplementary)"],
].map(([id, label]) => ({ id: id as Section, label }));

/** paper_check summaries of the paper experiments E1–E5 (benchmarks/paper_experiments.py). */
const PAPER_CHECKS = [paperE1, paperE2, paperE3, paperE4, paperE5].map((p) => ({ id: p.paper_experiment, ...p.paper_check.summary }));

/** Research Results: every number shown here is read from a committed artifact in benchmarks/results/ or served by the API. */
export function BenchmarksPage() {
  const [section, setSection] = useState<Section>("overview");
  const qiroResult = qiro.annealing_plus_local_search;
  const benign = traffic.results.find((r) => r.expected === "benign");
  const paperMatched = PAPER_CHECKS.reduce((n, c) => n + c.matched, 0);
  const paperStated = PAPER_CHECKS.reduce((n, c) => n + c.stated_values, 0);

  return (
    <div className="stack" data-testid="benchmark-page">
      <div className="page-head">
        <div>
          <div className="page-title">Research results</div>
          <div className="page-sub">Recorded benchmark artifacts with their limitations. Experiment numbers E1–E10 follow the journal paper; E11 and E12 are supplementary (not reported in the paper).</div>
        </div>
      </div>

      <div className="notice" data-testid="benchmark-caveat">
        Simulations and rule-based findings are configuration-level research results, not evidence of clinical protection.
        The optimizer instances are synthetic. Traffic metrics come from a previously downloaded external test split;
        thresholds were selected after inspecting that same split, so they are not a generalization estimate.
      </div>

      <Tabs tabs={SECTIONS} active={section} onChange={setSection} testPrefix="results" />

      {section === "overview" && (
        <section className="card" data-testid="results-overview-card">
          <div className="card-h"><span className="h">Headline figures</span><span className="pill">artifacts in benchmarks/results/</span></div>
          <div className="kpi-strip">
            <div className="kpi-card"><div className="label">Paper numbers reproduced (E1–E5)</div><div className="value" data-testid="paper-check">{paperMatched}/{paperStated}</div><div className="hint2">{PAPER_CHECKS.map((c) => `${c.id} ${c.matched}/${c.stated_values}`).join(" · ")}</div></div>
            <div className="kpi-card"><div className="label">QIRO optimal solutions (E4)</div><div className="value" data-testid="qiro-optimal-share">{percent(qiroResult.optimal_share)}</div><div className="hint2">{qiro.instances_with_nonzero_optimum} synthetic instances · seed 0 · {qiro.date}</div></div>
            <div className="kpi-card"><div className="label">Mean optimality gap (E4)</div><div className="value">{qiroResult.mean_gap_pct.toFixed(4)}%</div><div className="hint2">max {qiroResult.max_gap_pct.toFixed(4)}%</div></div>
            <div className="kpi-card"><div className="label">Benign false-positive rate (E6)</div><div className="value">{benign ? percent(benign.flag_rate) : "—"}</div><div className="hint2">{benign?.windows ?? 0} windows · recorded {traffic.date} · optimistic</div></div>
            <div className="kpi-card"><div className="label">Finding types mapped (E12, supplementary)</div><div className="value">42</div><div className="hint2">pillar-level mapping to IEEE/UL 2933-2024</div></div>
          </div>
          <table className="t mini" data-testid="evidence-index">
            <thead><tr><th>Experiment</th><th>Question</th><th>Artifact</th></tr></thead>
            <tbody>
              <tr><td>E1–E5</td><td>Do the numbers the journal paper states for E1–E5 reproduce with the shipped software?</td><td className="mono">paper_e1_systems.json … paper_e5_worked_example.json</td></tr>
              <tr><td>E4</td><td>How close is the planner to the exact optimum on small instances (solver quality)?</td><td className="mono">qiro_optimality.json</td></tr>
              <tr><td>E6</td><td>How do the traffic rules behave on the CICIoMT2024 test split (same split as tuning)?</td><td className="mono">traffic_rules_eval.json</td></tr>
              <tr><td>E12 (supplementary, not reported in the paper)</td><td>Which pillar, deduction and public reference does each finding type map to?</td><td className="mono">GET /api/v1/standards-map</td></tr>
            </tbody>
          </table>
        </section>
      )}

      {section === "optimizer" && (
        <section className="card" data-testid="qiro-results">
          <div className="card-h">
            <span className="h">E4 · QIRO optimality vs. exhaustive search (solver quality)</span>
            <span className="pill">Seed 0 · {qiro.date} · Python {qiro.python}</span>
          </div>
          <div className="kpi-strip">
            <div className="kpi-card"><div className="label">Synthetic instances</div><div className="value">{qiro.instances_with_nonzero_optimum}</div></div>
            <div className="kpi-card"><div className="label">Optimal solutions</div><div className="value">{percent(qiroResult.optimal_share)}</div></div>
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
          <p className="page-sub">{qiro.caveat} Runtime is hardware- and load-dependent; only the seeded objective metrics are intended to be reproducible. Gap = 100 · (f* − f) / f* against the exhaustive optimum (n ≤ 14).</p>
        </section>
      )}

      {section === "traffic" && (
        <section className="card" data-testid="traffic-results">
          <div className="card-h">
            <span className="h">E6 · Traffic-rule evaluation (same split as threshold selection)</span>
            <span className="pill">Recorded {traffic.date} · {traffic.window_rows}-row windows</span>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table className="t">
              <thead>
                <tr><th>Input file</th><th>Label</th><th>Windows</th><th>Flagged</th><th>Window flag rate</th><th>Metric</th></tr>
              </thead>
              <tbody>
                {traffic.results.map((row) => (
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
      )}

      {section === "scalability" && <ScalabilitySection />}

      {section === "sensitivity" && <SensitivitySection />}

      {section === "reassessment" && <ReassessmentSection />}

      {section === "holdout" && <TrafficHoldoutSection />}

      {section === "attacks" && <AttackSimulationSection />}

      {section === "standards" && <StandardsMapSection />}
    </div>
  );
}
