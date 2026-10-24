import {
  Activity as ActivityIcon, FileText, ListTree, Pause, Play, RotateCcw, ShieldCheck, Skull, Square, icons as lucideIcons,
} from "lucide-react";
import { lazy, Suspense, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api } from "../api/client";
import type { AgentInfo, FleetReport, SimCatalog } from "../api/types";
import { AgentPipeline } from "../components/AgentPipeline";
import { Sparkline } from "../components/charts/Charts";
import { DRILL, DRILL_TEMPLATE, type DrillStep } from "../components/drill";
import { DEVICE_ICON } from "../components/icons";
import { QiroPlan, ResultView } from "../components/ResultView";
import { AffectedDevicesTable, coreIssues, CoreIssuesTable } from "../components/FleetPanels";
import { RiskTimeline, type AgentRun } from "../components/RiskTimeline";
import { Kpi, pretty, usd } from "../components/ui";
import { useAssessmentStream } from "../hooks/useAssessmentStream";
import { useSimulation } from "../hooks/useSimulation";

const FleetScene = lazy(() => import("../components/FleetScene").then((m) => ({ default: m.FleetScene })));

type Overlay = null | "device" | "fleet" | "activity" | "report" | "core";
const GROUPS: [string, string][] = [["quantum", "Post-quantum attacks"], ["network", "Network attacks"], ["ai", "AI & data attacks"], ["identity", "Identity & secrets"]];
const QDAY_OPTIONS = [4, 6, 8, 10, 15, 20, 30];
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function DeviceIcon({ kind, size = 18 }: { kind: string; size?: number }) {
  const Icon = lucideIcons[(DEVICE_ICON[kind] ?? "Cpu") as keyof typeof lucideIcons];
  return <Icon size={size} />;
}

function OverlayPage({ title, icon, onClose, children, testId }: { title: string; icon?: ReactNode; onClose: () => void; children: ReactNode; testId?: string }) {
  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onClose]);
  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} data-testid={testId}>
        <div className="overlay-head"><h2>{icon}{title}</h2><button className="btn" onClick={onClose} data-testid="close-overlay">Close</button></div>
        {children}
      </div>
    </div>
  );
}

export function SimulationPage({ agents }: { agents: AgentInfo[] }) {
  const [template, setTemplate] = useState(DRILL_TEMPLATE);
  const [paused, setPaused] = useState(false);
  const [catalog, setCatalog] = useState<SimCatalog | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [attack, setAttack] = useState("hndl_capture");
  const [defence, setDefence] = useState("enable_hybrid_mlkem");
  const [overlay, setOverlay] = useState<Overlay>(null);
  const [fleet, setFleet] = useState<FleetReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [drillIdx, setDrillIdx] = useState<number | null>(null);
  const [drillRunning, setDrillRunning] = useState(false);
  const [assessing, setAssessing] = useState<string | null>(null);
  const [coreId, setCoreId] = useState<string>("kex");
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const stopRef = useRef(false);
  const sim = useSimulation(template, 7, paused);
  const stream = useAssessmentStream();

  useEffect(() => { api.simCatalog().then(setCatalog); }, []);
  useEffect(() => { setFleet(null); setNotice(null); setDrillIdx(null); setRuns([]); stream.reset(); }, [sim.snapshot?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const devices = sim.snapshot?.devices ?? [];
  const issues = useMemo(() => coreIssues(devices), [devices]);
  const result = stream.result;
  useEffect(() => {
    if (!result) return;
    setRuns((prev) => [...prev, { tick: sim.snapshot?.tick ?? 0, device: result.system_id, findings: result.findings_count, status: result.environment_status }]);
  }, [result]); // eslint-disable-line react-hooks/exhaustive-deps
  const openDevice = (id: string) => { setSelectedId(id); setOverlay("device"); };
  const selected = devices.find((d) => d.id === selectedId) ?? devices.find((d) => d.shape !== "hub") ?? null;
  const sid = sim.snapshot?.id;
  const qday = sim.snapshot?.assumptions.years_to_crqc ?? 10;
  const kpi = useMemo(() => ({
    ready: devices.filter((d) => d.live.pq_readiness === "PQ-ready").length,
    vulnerable: devices.filter((d) => d.live.pq_readiness === "Vulnerable").length,
    hndl: devices.filter((d) => d.live.hndl_exposed).length,
    attacks: devices.reduce((n, d) => n + d.active_attacks.length, 0),
  }), [devices]);

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setNotice(null);
    try { await fn(); } catch (e) { setNotice((e as Error).message); } finally { setBusy(false); }
  };
  const runAgents = async (deviceId: string) => {
    if (!sid) return;
    setAssessing(deviceId);
    try { await stream.run({ simulation_id: sid, device_id: deviceId }, 90); } catch { /* shown via stream.error */ } finally { setAssessing(null); }
  };
  const inject = () => selected && sid && act(async () => setNotice((await api.inject(sid, selected.id, attack)).event.message));
  const clear = (a: string) => selected && sid && act(async () => { await api.clearAttack(sid, selected.id, a); });
  const defend = () => selected && sid && act(async () => {
    const r = await api.mitigate(sid, defence, selected.id);
    sim.setSnapshot(r.snapshot);
    setNotice(r.snapshot.events.filter((e) => e.device_id === selected.id).at(-1)?.message ?? "Defence applied.");
  });
  const setQday = (years: number) => sid && act(async () => sim.setSnapshot(await api.setAssumptions(sid, 5, years)));

  const runDrill = async () => {
    if (!sid) return;
    stopRef.current = false;
    setDrillRunning(true);
    setNotice(null);
    try {
      for (let i = 0; i < DRILL.length; i++) {
        if (stopRef.current) break;
        setDrillIdx(i);
        const a = DRILL[i].action ?? {};
        if (a.select) setSelectedId(a.select);
        if (a.qday) sim.setSnapshot(await api.setAssumptions(sid, a.qday.migration_years, a.qday.years_to_crqc));
        for (const x of a.inject ?? []) await api.inject(sid, x.device, x.attack);
        for (const m of a.mitigate ?? []) sim.setSnapshot((await api.mitigate(sid, m.mitigation, m.device)).snapshot);
        if (a.assess) await runAgents(a.assess);
        await sleep(a.assess ? 1200 : 2600);
      }
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setDrillRunning(false);
    }
  };

  const allowedAttacks = catalog?.attacks.filter((a) => !a.requires_ai || selected?.has_ai) ?? [];
  const allowedDefences = catalog?.mitigations.filter((m) => (m.layer !== "ai" || selected?.has_ai) && !selected?.mitigations.includes(m.id)) ?? [];
  const attackInfo = catalog?.attacks.find((a) => a.id === attack);
  const step: DrillStep | null = drillIdx !== null ? DRILL[drillIdx] : null;
  const drillDone = drillIdx === DRILL.length - 1 && !drillRunning;

  return (
    <div className="sim-screen" data-testid="sim-screen">
      {/* ---------- top bar: title, 4 KPIs, controls */}
      <div className="sim-top">
        <div className="sim-title">
          <div>
            <div className="t1">{sim.snapshot?.template_label ?? "Simulation"}</div>
            <div className="t2"><span className={`dot ${sim.connected ? "ok" : "bad"}`} /> {sim.connected ? `live · tick ${sim.snapshot?.tick ?? 0}` : paused ? "paused" : "offline"}</div>
          </div>
        </div>
        <div className="mini-kpis" data-testid="sim-kpis">
          <div className={`mini-kpi ${kpi.ready === devices.length && devices.length ? "good" : ""}`}><span className="l">PQ-ready</span><span className="v">{kpi.ready}/{devices.length}</span></div>
          <div className={`mini-kpi ${kpi.vulnerable ? "warn" : "good"}`}><span className="l">Quantum-vulnerable</span><span className="v">{kpi.vulnerable}</span></div>
          <div className={`mini-kpi ${kpi.hndl ? "bad" : "good"}`} data-testid="kpi-hndl"><span className="l">HNDL-exposed</span><span className="v">{kpi.hndl}</span></div>
          <div className={`mini-kpi ${kpi.attacks ? "bad" : ""}`} data-testid="kpi-attacks"><span className="l">Active attacks</span><span className="v">{kpi.attacks}</span></div>
        </div>
        <div className="spacer" />
        <label className="row xs muted" title="Assumed years until a quantum computer can break RSA/ECC (Mosca's z)">
          Q-Day in
          <select value={qday} onChange={(e) => setQday(Number(e.target.value))} data-testid="qday-select">
            {QDAY_OPTIONS.map((y) => <option key={y} value={y}>{y} years</option>)}
          </select>
        </label>
        <select value={template} onChange={(e) => setTemplate(e.target.value)} data-testid="template-select" disabled={drillRunning}>
          {catalog?.templates.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
        </select>
        <button className="btn btn-sm" onClick={() => setPaused(!paused)} title={paused ? "Resume" : "Pause"} data-testid="pause">{paused ? <Play size={14} /> : <Pause size={14} />}</button>
        <button className="btn btn-sm" onClick={() => sim.recreate()} disabled={drillRunning} title="Reset simulation" data-testid="reset"><RotateCcw size={14} /></button>
        <button className="btn btn-sm" onClick={() => setOverlay("fleet")} data-testid="open-fleet"><ListTree size={14} /> Fleet report</button>
        <button className="btn btn-sm" onClick={() => setOverlay("activity")} data-testid="open-activity"><ActivityIcon size={14} /> Activity</button>
      </div>

      {/* ---------- main area */}
      <div className="sim-main">
        <div className="sim-side">
          <CoreIssuesTable issues={issues} onOpen={(id) => { setCoreId(id); setOverlay("core"); }} />
          <AffectedDevicesTable devices={devices} catalog={catalog} selected={selected?.id} onOpen={openDevice} />
        </div>
        <div className="sim-left">
          <div className="sim-scene">
            {step && (
              <div className="drill-bar" data-testid="drill-bar">
                <div className="drill-steps">
                  {DRILL.map((s, i) => (
                    <span key={s.id} className={`drill-step ${s.actor} ${i < (drillIdx ?? -1) ? "done" : ""} ${i === drillIdx ? "current" : ""}`}>
                      {s.actor === "adversary" ? <Skull size={11} /> : <ShieldCheck size={11} />}{s.stage}
                    </span>
                  ))}
                </div>
                <div className={`drill-card ${step.actor}`} data-testid="drill-card" data-step={step.id}>
                  <div className={`who ${step.actor}`}>{step.actor === "adversary" ? <Skull size={12} /> : <ShieldCheck size={12} />}
                    {step.actor === "adversary" ? "Adversary (simulated)" : "Security analyst · SafeGuard"} · step {drillIdx! + 1}/{DRILL.length}</div>
                  <div className="tt">{step.title}</div>
                  <div className="tx">{step.text}</div>
                  <div className="ly">Layer: {step.layer}</div>
                </div>
              </div>
            )}
            <div className="scene-legend2">
              <span><span className="dot ok" /> PQ-safe</span><span><span className="dot warn" /> quantum-vulnerable</span><span><span className="dot bad" /> under attack</span>
              <span style={{ color: "#c084fc" }}>— quantum-layer attack</span><span style={{ color: "#67e8f9" }}>— agents assessing</span>
            </div>
            <Suspense fallback={<div className="empty">Loading 3D scene…</div>}>
              {devices.length > 0 && <FleetScene devices={devices} selected={selected?.id ?? null} assessing={assessing} onSelect={setSelectedId} />}
            </Suspense>
          </div>
          <div className="card timeline-card">
            <div className="card-h" style={{ marginBottom: 2 }}><span className="h">Issue timeline</span><span className="legend-inline"><span><i style={{ background: "#38bdf8" }} />fleet risk</span><span><i style={{ background: "#f472b6" }} />selected device</span><span><i style={{ background: "#f59e0b" }} />open issues</span><span><i style={{ background: "#ef4444" }} />attack</span><span><i style={{ background: "#22c55e" }} />defence</span><span><i style={{ background: "#a78bfa" }} />agent findings</span></span></div>
            <RiskTimeline fleet={sim.fleetHistory} device={selected ? sim.history[selected.id] ?? [] : []} deviceId={selected?.id} events={sim.events} runs={runs} />
          </div>
        </div>

        <div className="sim-right">
          {/* use case */}
          <div className="card" data-testid="drill-panel">
            <div className="card-h"><span className="h"><Play size={13} /> Use case · ICU Q-Day drill</span>{drillDone && <span className="pill status-SAFE">done</span>}</div>
            <div className="xs muted">An ICU ward with long-lived patient data and classical crypto. Watch the post-quantum risk unfold, the agents detect it, and the defences remove it.</div>
            <div className="row" style={{ marginTop: 8 }}>
              {!drillRunning ? (
                <button className="btn btn-primary btn-sm" style={{ flex: 1 }} onClick={runDrill} disabled={!sid || template !== DRILL_TEMPLATE} data-testid="run-drill">
                  <Play size={14} /> {drillIdx === null ? "Run simulation" : "Run again"}
                </button>
              ) : (
                <button className="btn btn-sm" style={{ flex: 1 }} onClick={() => { stopRef.current = true; }} data-testid="stop-drill"><Square size={13} /> Stop after this step</button>
              )}
              {drillIdx !== null && !drillRunning && <button className="btn btn-sm" onClick={() => sim.recreate()} title="Reset ward"><RotateCcw size={14} /></button>}
            </div>
            {template !== DRILL_TEMPLATE && <div className="hint" style={{ marginTop: 6 }}>Switch to the Hospital ICU Ward to run the drill.</div>}
          </div>

          {/* selected device */}
          {selected && (
            <div className="card" data-testid="device-panel">
              <div className="dev-head">
                <div className={`dev-icon ${selected.live.status}`}><DeviceIcon kind={selected.kind} /></div>
                <select value={selected.id} onChange={(e) => setSelectedId(e.target.value)} data-testid="device-select">
                  {devices.map((d) => <option key={d.id} value={d.id}>{d.id} · {d.label}</option>)}
                </select>
              </div>
              <div className="kv tight">
                <span className="k">PQ readiness</span><span>{selected.live.pq_readiness}{selected.live.hndl_exposed && <span className="status-UNSAFE"> · HNDL-exposed</span>}</span>
                <span className="k">Key exchange</span><span className="mono">{String(selected.tls.key_exchange)}</span>
                <span className="k">Signature</span><span className="mono">{String(selected.tls.cert_signature_algo)}</span>
                <span className="k">Live risk</span><span><strong className={selected.live.risk > 50 ? "status-UNSAFE" : selected.live.risk > 25 ? "status-AT_RISK" : "status-SAFE"}>{selected.live.risk}</strong> / 100</span>
              </div>
              {(selected.active_attacks.length > 0 || selected.mitigations.length > 0) && (
                <div className="chips-x" style={{ marginTop: 8 }} data-testid="active-attacks">
                  {selected.active_attacks.map((a) => <span key={a} className="chip-x" onClick={() => clear(a)} title="Clear this attack">{catalog?.attacks.find((x) => x.id === a)?.label ?? pretty(a)} ×</span>)}
                  {selected.mitigations.slice(0, 4).map((m) => <span key={m} className="chip-x mit">⛨ {catalog?.mitigations.find((x) => x.id === m)?.label ?? pretty(m)}</span>)}
                  {selected.mitigations.length > 4 && <span className="chip-x mit">+{selected.mitigations.length - 4}</span>}
                </div>
              )}
              <div className="ctrl">
                <select value={attack} onChange={(e) => setAttack(e.target.value)} data-testid="attack-select" disabled={drillRunning}>
                  {GROUPS.map(([layer, label]) => (
                    <optgroup key={layer} label={label}>
                      {allowedAttacks.filter((a) => a.layer === layer).map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
                    </optgroup>
                  ))}
                </select>
                <button className="btn btn-danger btn-sm" onClick={inject} disabled={busy || drillRunning || !allowedAttacks.some((a) => a.id === attack)} data-testid="inject-btn">Inject</button>
              </div>
              {attackInfo && <div className="surface" title={attackInfo.description}>Lands on: {attackInfo.surface}</div>}
              <div className="ctrl">
                <select value={defence} onChange={(e) => setDefence(e.target.value)} data-testid="defence-select" disabled={drillRunning}>
                  {allowedDefences.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
                </select>
                <button className="btn btn-success btn-sm" onClick={defend} disabled={busy || drillRunning || !allowedDefences.some((m) => m.id === defence)} data-testid="defend-btn">Apply</button>
              </div>
              {notice && <div className="notice xs" style={{ marginTop: 8 }} data-testid="sim-notice">{notice}</div>}
              <div className="row" style={{ marginTop: 8 }}>
                <button className="btn btn-primary btn-sm" style={{ flex: 1 }} onClick={() => selected && runAgents(selected.id)} disabled={stream.running || drillRunning} data-testid="assess-device">
                  <ShieldCheck size={14} /> {stream.running ? "Agents running…" : "Run agents"}
                </button>
                <button className="btn btn-sm" onClick={() => setOverlay("device")} data-testid="open-device">Details</button>
              </div>
            </div>
          )}

          {/* agents */}
          <div className="card">
            <div className="card-h">
              <span className="h">Agents</span>
              {stream.result && <span className={`pill status-${stream.result.environment_status}`} data-testid="device-status">{stream.result.environment_status}</span>}
            </div>
            <AgentPipeline agents={agents} live={stream.agents} dense />
            {stream.result && (
              <div style={{ marginTop: 10 }}>
                <div className="kv tight" style={{ marginTop: 0 }}>
                  <span className="k">Device</span><span className="mono">{stream.result.system_id}</span>
                  <span className="k">PQ risk score</span><span><strong>{stream.result.pq_risk_score}</strong> / 100 · {stream.result.verdict}</span>
                  <span className="k">Findings</span><span>{stream.result.findings_count} · plan {stream.result.qiro_optimization.selection_count} actions</span>
                </div>
                {stream.result.findings.length > 0 && (
                  <div className="top-findings" data-testid="top-findings">
                    {[...stream.result.findings].sort((a, b) => ["critical", "high", "medium", "low", "info"].indexOf(a.severity) - ["critical", "high", "medium", "low", "info"].indexOf(b.severity))
                      .slice(0, 4).map((f) => (
                        <div key={f.id} className="tf"><span className={`sev sev-${f.severity}`}>{f.severity}</span><span>{pretty(f.type)}</span></div>
                      ))}
                  </div>
                )}
                <div className="row" style={{ marginTop: 8 }}>
                  <button className="btn btn-sm" style={{ flex: 1 }} onClick={() => setOverlay("report")} data-testid="open-report"><FileText size={13} /> Full report</button>
                  <a className="btn btn-sm btn-primary" style={{ flex: 1 }} href={api.reportUrl(stream.result.assessment_id)} download>⤓ PDF</a>
                </div>
              </div>
            )}
            {stream.error && <div className="error xs" style={{ marginTop: 6 }}>{stream.error}</div>}
          </div>
        </div>
      </div>

      {/* ---------- detail pages */}
      {overlay === "core" && (() => {
        const issue = issues.find((i) => i.id === coreId)!;
        const fixLabel = catalog?.mitigations.find((m) => m.id === issue.fix)?.label;
        return (
          <OverlayPage title={`Core issue · ${issue.title}`} onClose={() => setOverlay(null)} testId="overlay-core">
            <div className="stack">
              <div className="notice">{issue.why}</div>
              <div className="kpi-strip" style={{ marginBottom: 0 }}>
                <Kpi label="Affected devices" value={`${issue.devices.length} / ${devices.length}`} tone={issue.devices.length ? "UNSAFE" : "SAFE"} />
                <Kpi label="Severity" value={issue.severity} />
                <Kpi label="Recommended defence" value={fixLabel ?? "Investigate per device"} />
              </div>
              {issue.fix && issue.devices.length > 0 && (
                <div className="row">
                  <button className="btn btn-success" disabled={busy || drillRunning} data-testid="fix-core" onClick={() => sid && act(async () => {
                    for (const d of issue.devices) await api.mitigate(sid, issue.fix!, d.id).catch(() => undefined);
                    const a = sim.snapshot!.assumptions;
                    sim.setSnapshot(await api.setAssumptions(sid, a.migration_years, a.years_to_crqc));
                    setOverlay(null);
                  })}>⛨ Apply {fixLabel} to {issue.devices.length} device(s)</button>
                  <span className="xs faint">Then run the agents to verify.</span>
                </div>
              )}
              {issue.devices.length > 0 ? (
                <table className="t">
                  <thead><tr><th>Device</th><th>Type</th><th>Live risk</th><th>Key exchange</th><th>Signature</th><th>Active attacks</th></tr></thead>
                  <tbody>{issue.devices.map((d) => (
                    <tr key={d.id} className="clickable" onClick={() => openDevice(d.id)} data-testid={`core-device-${d.id}`}>
                      <td className="mono">{d.id}</td><td className="xs">{d.label}</td><td className="mono">{d.live.risk}</td>
                      <td className="mono xs">{String(d.tls.key_exchange)}</td><td className="mono xs">{String(d.tls.cert_signature_algo)}</td>
                      <td className="xs">{d.active_attacks.map((a) => catalog?.attacks.find((x) => x.id === a)?.label ?? a).join(", ") || "—"}</td>
                    </tr>
                  ))}</tbody>
                </table>
              ) : <div className="empty">No device is affected by this issue.</div>}
            </div>
          </OverlayPage>
        );
      })()}
      {overlay === "report" && stream.result && (
        <OverlayPage title={`Assessment · ${stream.result.system_id}`} onClose={() => setOverlay(null)} testId="overlay-report">
          <ResultView r={stream.result} />
        </OverlayPage>
      )}
      {overlay === "device" && selected && (
        <OverlayPage title={`${selected.id} · ${selected.label}`} icon={<DeviceIcon kind={selected.kind} size={20} />} onClose={() => setOverlay(null)} testId="overlay-device">
          <div className="cols-2">
            <div className="card">
              <div className="card-h"><span className="h">Configuration</span><span className="pill">{selected.zone}</span></div>
              <table className="t"><tbody>
                {Object.entries(selected.tls).map(([k, v]) => <tr key={k}><td className="xs muted">{pretty(k)}</td><td className="mono xs">{String(v)}</td></tr>)}
                <tr><td className="xs muted">certificate</td><td className="xs">{selected.cert_present ? "present" : "missing"}</td></tr>
                <tr><td className="xs muted">authentication</td><td className="xs">{selected.auth_status} · {selected.failed_login_count} failed logins</td></tr>
                <tr><td className="xs muted">AI assistant</td><td className="xs">{selected.has_ai ? `yes · ${selected.prompt_count} prompts` : "no"}</td></tr>
              </tbody></table>
            </div>
            <div className="card">
              <div className="card-h"><span className="h">Active attacks</span></div>
              {selected.active_attacks.length ? selected.active_attacks.map((a) => {
                const info = catalog?.attacks.find((x) => x.id === a);
                return <div key={a} style={{ marginBottom: 8 }}><strong className="small">{info?.label}</strong><div className="surface">Lands on: {info?.surface}</div><div className="xs muted">{info?.description}</div></div>;
              }) : <div className="xs faint">None.</div>}
              <div className="card-h" style={{ marginTop: 10 }}><span className="h">Telemetry</span></div>
              {(["risk", "syn", "rate", "udp"] as const).map((k) => (
                <div key={k}><div className="spread xs muted"><span>{{ risk: "Live risk", syn: "SYN flag ratio", rate: "Packet rate", udp: "UDP share" }[k]}</span>
                  <span className="mono">{(sim.history[selected.id]?.at(-1)?.[k] ?? 0).toFixed(k === "risk" ? 0 : 3)}</span></div>
                  <Sparkline values={(sim.history[selected.id] ?? []).map((p) => p[k])} color={k === "risk" ? "#f472b6" : "#38bdf8"} height={30} /></div>
              ))}
            </div>
          </div>
        </OverlayPage>
      )}
      {overlay === "activity" && (
        <OverlayPage title="Activity log" icon={<ActivityIcon size={20} />} onClose={() => setOverlay(null)} testId="overlay-activity">
          <div className="card log" style={{ maxHeight: "70vh" }} data-testid="event-log">
            {sim.events.map((e) => <div key={e.seq} className={e.level}>[tick {e.tick}] {e.message}</div>)}
          </div>
        </OverlayPage>
      )}
      {overlay === "fleet" && (
        <OverlayPage title="Fleet report" icon={<ListTree size={20} />} onClose={() => setOverlay(null)} testId="overlay-fleet">
          <div className="stack">
            <div className="row">
              <button className="btn btn-primary" onClick={() => sid && act(async () => setFleet(await api.assessFleet(sid, 250_000, 120)))} disabled={busy} data-testid="assess-fleet">
                {busy ? "Assessing all devices…" : "Assess all devices"}</button>
              <span className="xs faint">Runs the 14 agents on every device, then plans remediation under one shared budget ($250,000 · 120 h).</span>
            </div>
            {fleet && (
              <>
                <div className={`verdict slim ${fleet.environment_status}`} data-testid="fleet-verdict" data-status={fleet.environment_status}>
                  <div style={{ flex: 1 }}><div className="verdict-title">Is the environment safe? {fleet.environment_status === "SAFE" ? "Yes" : "No"} — {fleet.environment_status.replace("_", " ")}</div>
                    <div className="xs faint">tick {fleet.tick} · {fleet.template_label}</div></div>
                  <button className="btn btn-success" onClick={() => sid && act(async () => {
                    const r = await api.applyPlan(sid, fleet.fleet_plan.selected_actions.map((a) => ({ mitigation: a.mitigation, device_id: a.device_id })));
                    sim.setSnapshot(r.snapshot);
                    setNotice(`Applied ${r.events.length} defence step(s) from the plan.`);
                  })} disabled={busy || !fleet.fleet_plan.selected_actions.length} data-testid="apply-plan">⛨ Apply plan</button>
                  <a className="btn btn-primary" href={api.fleetReportUrl(fleet.simulation_id)} download data-testid="download-fleet-pdf">⤓ Fleet PDF</a>
                </div>
                {notice && <div className="notice" data-testid="fleet-notice">{notice}</div>}
                <div className="kpi-strip" style={{ marginBottom: 0 }}>
                  <Kpi label="Unsafe" value={fleet.counts.UNSAFE} tone={fleet.counts.UNSAFE ? "UNSAFE" : undefined} />
                  <Kpi label="At risk" value={fleet.counts.AT_RISK} tone={fleet.counts.AT_RISK ? "AT_RISK" : undefined} />
                  <Kpi label="Safe" value={fleet.counts.SAFE} tone="SAFE" />
                  <Kpi label="Plan" value={`${fleet.fleet_plan.selection_count} actions`} hint={usd(fleet.fleet_plan.total_cost_usd)} />
                </div>
                <table className="t">
                  <thead><tr><th>Device</th><th>Status</th><th>PQ score</th><th>PQ readiness</th><th>Findings</th><th>Top issue</th></tr></thead>
                  <tbody>{fleet.devices.map((d) => (
                    <tr key={d.device_id}><td className="mono xs">{d.device_id}</td><td className={`status-${d.environment_status} xs`}>{d.environment_status}</td>
                      <td className="mono">{d.pq_risk_score}</td><td className="xs">{d.pq_readiness}</td><td className="mono">{d.findings_count}</td>
                      <td className="xs muted">{d.top_issues[0] ? pretty(d.top_issues[0]) : "—"}</td></tr>
                  ))}</tbody>
                </table>
                <details><summary>Remediation plan</summary><QiroPlan q={fleet.fleet_plan} /></details>
              </>
            )}
          </div>
        </OverlayPage>
      )}
    </div>
  );
}
