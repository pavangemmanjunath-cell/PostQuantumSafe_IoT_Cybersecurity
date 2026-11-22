import sim from "../../../../benchmarks/results/attack_simulation.json";

interface AttackAgg {
  label: string;
  layer: string;
  detected_by: string[];
  blocked_by: string[];
  runs: number;
  exploitable_runs: number;
  preconditions_absent_runs: number;
  preconditions_absent_devices: string[];
  detection_rate: number;
  flagged_after_attack_rate: number;
  undetected_devices: string[];
  mean_delta_pq_risk_score: number;
  mean_delta_tippss_min: number;
  status_worsened_rate: number;
  mitigation_restored_status_rate: number;
  reinjection_blocked_rate: number;
  new_finding_types: string[];
}
interface Step { step: string; fleet_status: string; mean_pq_risk_score: number; safe: number; at_risk: number; unsafe: number; drill_device_status: string; drill_device_pq_risk_score: number }

const pc = (x: number) => `${Math.round(100 * x)}%`;
const Status = ({ s }: { s: string }) => <span className={`pill status-${s}`}>{s.replace("_", " ")}</span>;

/** E11 (supplementary, not reported in the paper) — attacker-versus-defender measurement on the hospital-ward simulator. */
export function AttackSimulationSection() {
  const attacks = sim.attacks as unknown as Record<string, AttackAgg>;
  const s = sim.summary;
  const traj = sim.kill_chain.trajectory as Step[];

  return (
    <div className="stack">
      <section className="card" data-testid="attack-results">
        <div className="card-h">
          <span className="h">E11 · Attack simulation on the {sim.template_label} template (supplementary, not reported in the paper)</span>
          <span className="pill">seeds {sim.seeds.join(", ")} · {sim.devices.length} devices · {Object.keys(attacks).length} attacks · {sim.date}</span>
        </div>
        <div className="kpi-strip">
          <div className="kpi-card"><div className="label">Runs (device × attack × seed)</div><div className="value">{s.runs}</div><div className="hint2">{s.exploitable_runs} with the precondition present · {s.preconditions_absent_runs} not exploitable</div></div>
          <div className="kpi-card"><div className="label">Detected (new finding from the expected agent)</div><div className="value" data-testid="attack-detected">{s.detected_exploitable_runs}/{s.exploitable_runs}</div><div className="hint2">{s.undetected_exploitable_runs} undetected: HNDL capture on devices already flagged at baseline</div></div>
          <div className="kpi-card"><div className="label">Re-injection blocked after mitigation</div><div className="value">{s.reinjection_blocked_exploitable_runs}/{s.exploitable_runs}</div><div className="hint2">per the simulator's mitigation model</div></div>
          <div className="kpi-card"><div className="label">ICU Q-Day drill (fleet)</div><div className="value">{traj[0].mean_pq_risk_score.toFixed(0)} → {traj[traj.length - 1].mean_pq_risk_score.toFixed(0)}</div><div className="hint2">mean PQ score, {traj[0].unsafe} → {traj[traj.length - 1].unsafe} devices UNSAFE</div></div>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table className="t mini" data-testid="attack-table">
            <thead>
              <tr><th>Attack</th><th>Layer</th><th>Exploitable / absent</th><th>Detected</th><th>Any finding after</th><th>Mean ΔS</th><th>Status worsened</th><th>Mitigation restores</th><th>Re-injection blocked</th><th>Detector → mitigation</th><th>Not detected on</th></tr>
            </thead>
            <tbody>
              {Object.entries(attacks).map(([id, a]) => (
                <tr key={id}>
                  <td><span className="mono">{id}</span><div className="xs muted">{a.label}</div></td>
                  <td>{a.layer}</td><td>{a.exploitable_runs} / {a.preconditions_absent_runs}</td>
                  <td><strong>{pc(a.detection_rate)}</strong></td><td>{pc(a.flagged_after_attack_rate)}</td>
                  <td>{a.mean_delta_pq_risk_score >= 0 ? "+" : ""}{a.mean_delta_pq_risk_score.toFixed(1)}</td>
                  <td>{pc(a.status_worsened_rate)}</td><td>{pc(a.mitigation_restored_status_rate)}</td><td>{pc(a.reinjection_blocked_rate)}</td>
                  <td className="xs">{a.detected_by.join(", ")} → {a.blocked_by.join(", ")}</td>
                  <td className="xs">{a.undetected_devices.length ? a.undetected_devices.join(", ") : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="page-sub">
          "Detected" requires a new finding from the agent the catalogue names for the attack, compared with the device's baseline; "any finding after" counts
          devices that were already flagged for the same precondition. ΔS is the change of the PQ risk score, which is cryptography-only by design, so
          network, AI and identity attacks mostly change the environment status and pillar scores instead. {sim.caveat}
        </p>
      </section>

      <section className="card" data-testid="kill-chain">
        <div className="card-h"><span className="h">ICU Q-Day drill replayed on {sim.kill_chain.drill_device} (seed {sim.kill_chain.seed})</span><span className="pill">fleet of {sim.devices.length} devices</span></div>
        <div style={{ overflowX: "auto" }}>
          <table className="t mini">
            <thead><tr><th>Step</th><th>Fleet status</th><th>Mean PQ score</th><th>SAFE / AT_RISK / UNSAFE</th><th>Drill device</th></tr></thead>
            <tbody>
              {traj.map((t) => (
                <tr key={t.step}>
                  <td className="mono">{t.step}</td><td><Status s={t.fleet_status} /></td><td>{t.mean_pq_risk_score.toFixed(1)}</td>
                  <td>{t.safe} / {t.at_risk} / {t.unsafe}</td><td>{t.drill_device_pq_risk_score} <Status s={t.drill_device_status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="page-sub">Same step order as the web application's drill ({sim.kill_chain.source}). The "respond" step applies the catalogue mitigations; the resulting SAFE status is a configuration-consistency result, not evidence of real-world protection.</p>
      </section>
    </div>
  );
}
