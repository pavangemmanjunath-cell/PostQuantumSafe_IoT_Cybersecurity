import reass from "../../../../benchmarks/results/plan_reassessment.json";

interface Plan {
  planner_mode: string;
  selected_action_ids: string[];
  total_cost_usd: number;
  total_downtime_hrs: number;
  summed_benefit: number;
  projected_pq_score: number;
  projected_status: string;
  reassessed_pq_score: number;
  reassessed_status: string;
  projection_error: number;
  remaining_finding_types: string[];
  applied_mitigations: string[];
  unmodelled_mitigations: string[];
}
interface System {
  scenario: string;
  candidate_actions: number;
  baseline: { pq_risk_score: number; environment_status: string; findings_count: number };
  plan_a: Plan;
  plan_b: Plan;
  exhaustive: {
    subsets_reassessed: number;
    plan_a_is_best_by_reassessment: boolean;
    plan_a_is_cheapest_best: boolean;
    plan_b_is_best_by_reassessment: boolean;
    plan_b_is_cheapest_best: boolean;
    independent_cost_model: { best_reassessed_pq_score: number; cheapest_best_subset: { cost_usd: number; action_ids: string[] } | null };
  };
}

const usd = (n: number) => `$${Math.round(n).toLocaleString("en-US")}`;
const Status = ({ s }: { s: string }) => <span className={`pill status-${s}`}>{s.replace("_", " ")}</span>;

/** E9 — summed benefit, projected score and reassessed score reported independently for every system. */
export function ReassessmentSection() {
  const systems = reass.systems as unknown as System[];
  const sum = reass.summary;
  const we = sum.worked_example;

  return (
    <div className="stack">
      <section className="card" data-testid="reassessment-results">
        <div className="card-h">
          <span className="h">E9 · Plan evaluation by reassessment</span>
          <span className="pill">seed {reass.seed} · {reass.date} · {sum.total_pipeline_runs_exhaustive} exhaustive pipeline runs</span>
        </div>
        <div className="kpi-strip">
          <div className="kpi-card"><div className="label">SAFE after plan A (independent actions)</div><div className="value" data-testid="reassess-safe-a">{sum.plan_a.safe_after_reassessment}/{sum.systems}</div><div className="hint2">{sum.plan_a.unsafe_after_reassessment} remain UNSAFE · {sum.systems_safe_at_baseline} SAFE at baseline</div></div>
          <div className="kpi-card"><div className="label">Mean |S_proj − S_reass|, plan A</div><div className="value">{sum.plan_a.mean_abs_projection_error.toFixed(1)}</div><div className="hint2">max {sum.plan_a.max_abs_projection_error}; equal in {sum.plan_a.systems_where_projected_equals_reassessed}/{sum.systems}</div></div>
          <div className="kpi-card"><div className="label">Mean |S_proj − S_reass|, plan B (root causes)</div><div className="value">{sum.plan_b.mean_abs_projection_error.toFixed(1)}</div><div className="hint2">max {sum.plan_b.max_abs_projection_error}; equal in {sum.plan_b.systems_where_projected_equals_reassessed}/{sum.systems}</div></div>
          <div className="kpi-card"><div className="label">Plan A best by reassessment</div><div className="value">{sum.plan_a.best_by_reassessment}/{sum.plan_a.exhaustively_checked}</div><div className="hint2">cheapest among best: {sum.plan_a.cheapest_best}/{sum.plan_a.exhaustively_checked}</div></div>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table className="t mini" data-testid="reassessment-table">
            <thead>
              <tr>
                <th>Scenario</th><th>n</th><th>Baseline</th>
                <th>Plan A cost</th><th>ΣB</th><th>S_proj</th><th>S_reass</th><th>Status</th>
                <th>Plan B cost</th><th>S_proj</th><th>S_reass</th><th>Status</th>
                <th>Best S_reass (exhaustive)</th><th>Plan A best / cheapest</th><th>Remaining after A</th>
              </tr>
            </thead>
            <tbody>
              {systems.map((s) => (
                <tr key={s.scenario}>
                  <td className="mono">{s.scenario}</td><td>{s.candidate_actions}</td>
                  <td>{s.baseline.pq_risk_score} <Status s={s.baseline.environment_status} /></td>
                  <td>{usd(s.plan_a.total_cost_usd)}</td><td>{s.plan_a.summed_benefit}</td><td>{s.plan_a.projected_pq_score}</td>
                  <td><strong>{s.plan_a.reassessed_pq_score}</strong></td><td><Status s={s.plan_a.reassessed_status} /></td>
                  <td>{usd(s.plan_b.total_cost_usd)}</td><td>{s.plan_b.projected_pq_score}</td>
                  <td><strong>{s.plan_b.reassessed_pq_score}</strong></td><td><Status s={s.plan_b.reassessed_status} /></td>
                  <td>{s.exhaustive.independent_cost_model.best_reassessed_pq_score}{s.exhaustive.independent_cost_model.cheapest_best_subset ? ` (cheapest ${usd(s.exhaustive.independent_cost_model.cheapest_best_subset.cost_usd)})` : ""}</td>
                  <td>{s.exhaustive.plan_a_is_best_by_reassessment ? "yes" : "no"} / {s.exhaustive.plan_a_is_cheapest_best ? "yes" : "no"}</td>
                  <td className="xs">{s.plan_a.remaining_finding_types.length ? s.plan_a.remaining_finding_types.join(", ") : "—"}{s.plan_a.unmodelled_mitigations.length ? ` (unmodelled: ${s.plan_a.unmodelled_mitigations.join(", ")})` : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="page-sub">
          S_proj assumes each selected action removes its finding; S_reass applies the plan's mitigations to the configuration and re-runs the
          detection and scoring stages. Plan B merges actions that share a mitigation (one fix removes several findings). "Best" compares against every
          feasible subset evaluated by reassessment (n ≤ {reass.exhaustive_max_n}). {reass.caveat}
        </p>
      </section>

      <section className="card" data-testid="worked-example">
        <div className="card-h"><span className="h">Worked example · {we.scenario}</span></div>
        <div className="kpi-strip">
          <div className="kpi-card"><div className="label">Plan A (shipped)</div><div className="value">{we.plan_a.reassessed_pq_score} <Status s={we.plan_a.reassessed_status} /></div><div className="hint2">{we.plan_a.selected_action_ids.join(", ")} · {usd(we.plan_a.total_cost_usd)} · ΣB {we.plan_a.summed_benefit} · S_proj {we.plan_a.projected_pq_score}</div></div>
          <div className="kpi-card"><div className="label">Is plan A best by reassessment?</div><div className="value">{we.plan_a_is_best_by_reassessment ? "yes" : "no"}</div><div className="hint2">cheapest best: {we.plan_a_is_cheapest_best ? "yes" : "no"}</div></div>
          <div className="kpi-card"><div className="label">Cheapest subset reaching the best S_reass</div><div className="value">{usd(we.cheapest_best_subset_independent.cost_usd)}</div><div className="hint2">{we.cheapest_best_subset_independent.action_ids.join(", ")} → {we.cheapest_best_subset_independent.mitigations.join(", ")}</div></div>
        </div>
      </section>
    </div>
  );
}
