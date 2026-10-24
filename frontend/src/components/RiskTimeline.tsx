import { useEffect, useRef, useState } from "react";
import type { SimEvent } from "../api/types";
import type { FleetPoint, TelemetryPoint } from "../hooks/useSimulation";

export interface AgentRun {
  tick: number;
  device: string;
  findings: number;
  status: string;
}

type Kind = "attack" | "defence" | "findings";
interface Marker { tick: number; kind: Kind; label: string; detail: string }

const COLOR: Record<Kind, string> = { attack: "#ef4444", defence: "#22c55e", findings: "#a78bfa" };
const TEXT: Record<Kind, string> = { attack: "#fca5a5", defence: "#86efac", findings: "#c4b5fd" };

function actionName(message: string): string {
  const m = message.match(/^(?:Injected|Applied|Blocked:)\s+(.+?)\s+on\s/);
  return m ? m[1] : message;
}

/** Merge events that happen at the same tick into one marker, e.g. "Hybrid ML-KEM ×9". */
function buildMarkers(events: SimEvent[], runs: AgentRun[], t0: number): Marker[] {
  const groups = new Map<string, { tick: number; kind: Kind; names: Map<string, number>; messages: string[] }>();
  for (const e of events) {
    if (e.tick < t0 || (e.level !== "danger" && e.level !== "success")) continue;
    const kind: Kind = e.level === "danger" ? "attack" : "defence";
    const key = `${e.tick}|${kind}`;
    const g = groups.get(key) ?? { tick: e.tick, kind, names: new Map<string, number>(), messages: [] as string[] };
    const n = actionName(e.message);
    g.names.set(n, (g.names.get(n) ?? 0) + 1);
    g.messages.push(e.message);
    groups.set(key, g);
  }
  const out: Marker[] = [...groups.values()].map((g) => {
    const parts = [...g.names.entries()].map(([n, c]) => (c > 1 ? `${n} ×${c}` : n));
    const label = parts.length > 1 ? `${parts[0]} +${parts.length - 1}` : parts[0];
    return { tick: g.tick, kind: g.kind, label, detail: g.messages.join("\n") };
  });
  for (const r of runs) {
    if (r.tick < t0) continue;
    out.push({ tick: r.tick, kind: "findings", label: `${r.findings} findings · ${r.device}`, detail: `Agents assessed ${r.device}: ${r.findings} finding(s), ${r.status}` });
  }
  return out.sort((a, b) => a.tick - b.tick);
}

function useSize<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => setSize({ w: Math.round(e.contentRect.width), h: Math.round(e.contentRect.height) }));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return { ref, ...size };
}

/**
 * Issue timeline rendered at true pixel size (no stretched text): fleet mean risk (area), selected-device
 * risk (line), open issues per tick (bars), and de-duplicated markers for attacks, defences and agent findings,
 * with labels placed in non-overlapping lanes.
 */
export function RiskTimeline({ fleet, device, deviceId, events, runs }: {
  fleet: FleetPoint[];
  device: TelemetryPoint[];
  deviceId?: string;
  events: SimEvent[];
  runs: AgentRun[];
}) {
  const { ref, w: W, h: H } = useSize<HTMLDivElement>();
  const ready = W > 50 && H > 40 && fleet.length >= 2;

  let body = null;
  if (ready) {
    const LANES = 3, LANE_H = 13;
    const PAD_L = 30, PAD_R = 10, PAD_B = 16, PAD_T = LANES * LANE_H + 8;
    const t0 = fleet[0].tick, t1 = Math.max(fleet[fleet.length - 1].tick, t0 + 1);
    const x = (t: number) => PAD_L + ((t - t0) / (t1 - t0)) * (W - PAD_L - PAD_R);
    const y = (v: number) => PAD_T + (1 - v / 100) * (H - PAD_T - PAD_B);
    const maxIssues = Math.max(4, ...fleet.map((p) => p.issues));
    const barW = Math.max(2, ((W - PAD_L - PAD_R) / Math.max(1, t1 - t0)) * 0.55);
    const meanLine = fleet.map((p, i) => `${i ? "L" : "M"}${x(p.tick).toFixed(1)},${y(p.mean).toFixed(1)}`).join(" ");
    const meanArea = `${meanLine} L${x(fleet[fleet.length - 1].tick)},${y(0)} L${x(fleet[0].tick)},${y(0)} Z`;
    const devLine = device.filter((p) => p.tick >= t0).map((p, i) => `${i ? "L" : "M"}${x(p.tick).toFixed(1)},${y(p.risk).toFixed(1)}`).join(" ");

    // greedy lane assignment so labels never overlap
    const laneEnd = Array(LANES).fill(-Infinity);
    const markers = buildMarkers(events, runs, t0).map((m) => {
      const mx = x(m.tick);
      const text = m.label.length > 30 ? `${m.label.slice(0, 29)}…` : m.label;
      const width = text.length * 5.6 + 14;
      const flip = mx + width > W - PAD_R;
      const start = flip ? mx - width : mx;
      let lane = laneEnd.findIndex((end) => start >= end + 6);
      const hidden = lane === -1;
      if (lane === -1) lane = LANES - 1;
      if (!hidden) laneEnd[lane] = flip ? mx + 8 : mx + width;
      return { ...m, mx, text, lane, hidden };
    });

    body = (
      <svg width={W} height={H} data-testid="risk-timeline" role="img" aria-label="Issue timeline">
        <defs>
          <linearGradient id="riskFill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.30" />
            <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        {[0, 50, 100].map((v) => (
          <g key={v}>
            <line x1={PAD_L} x2={W - PAD_R} y1={y(v)} y2={y(v)} stroke="#16213a" />
            <text x={PAD_L - 6} y={y(v) + 3} fontSize="10" fill="#64748b" textAnchor="end">{v}</text>
          </g>
        ))}
        {fleet.map((p) => p.issues > 0 && (
          <rect key={p.tick} x={x(p.tick) - barW / 2} width={barW} rx="1.5" y={y((p.issues / maxIssues) * 100)}
            height={y(0) - y((p.issues / maxIssues) * 100)} fill="#f59e0b" opacity="0.38" data-testid="issue-bar">
            <title>{`tick ${p.tick}: ${p.issues} open issue(s)`}</title>
          </rect>
        ))}
        <path d={meanArea} fill="url(#riskFill)" />
        <path d={meanLine} fill="none" stroke="#38bdf8" strokeWidth="1.8" strokeLinejoin="round" />
        {devLine && <path d={devLine} fill="none" stroke="#f472b6" strokeWidth="2" strokeLinejoin="round" />}
        {markers.map((m, i) => {
          const ly = 4 + m.lane * LANE_H;
          return (
            <g key={`${m.kind}-${m.tick}-${i}`} data-testid={`marker-${m.kind === "attack" ? "danger" : m.kind === "defence" ? "success" : "findings"}`}>
              <title>{`tick ${m.tick}\n${m.detail}`}</title>
              <line x1={m.mx} x2={m.mx} y1={ly + 6} y2={y(0)} stroke={COLOR[m.kind]} strokeWidth="1.2" strokeDasharray={m.kind === "findings" ? undefined : "3 3"} opacity="0.85" />
              {m.kind === "findings"
                ? <rect x={m.mx - 4} y={ly + 2} width="8" height="8" transform={`rotate(45 ${m.mx} ${ly + 6})`} fill={COLOR[m.kind]} />
                : <circle cx={m.mx} cy={ly + 6} r="4" fill={COLOR[m.kind]} />}
              {!m.hidden && (m.mx + m.text.length * 5.6 + 14 > W - PAD_R
                ? <text x={m.mx - 7} y={ly + 9.5} fontSize="10.5" fontWeight="600" fill={TEXT[m.kind]} textAnchor="end">{m.text}</text>
                : <text x={m.mx + 7} y={ly + 9.5} fontSize="10.5" fontWeight="600" fill={TEXT[m.kind]}>{m.text}</text>)}
            </g>
          );
        })}
        <text x={W - PAD_R} y={H - 3} fontSize="9.5" fill="#64748b" textAnchor="end">tick {t0} → {t1}{deviceId ? ` · pink = ${deviceId}` : ""}</text>
      </svg>
    );
  }

  return (
    <div ref={ref} style={{ width: "100%", height: "100%", minHeight: 0 }}>
      {body ?? <div className="timeline-empty">Collecting live data…</div>}
    </div>
  );
}
