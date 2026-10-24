import { ChevronRight } from "lucide-react";
import type { SimCatalog, SimDevice } from "../api/types";

/** A root cause shared by several devices, with the defence that removes it. */
export interface CoreIssue {
  id: string;
  title: string;
  why: string;
  severity: "critical" | "high" | "medium";
  devices: SimDevice[];
  fix: string | null; // mitigation id
}

export function coreIssues(devices: SimDevice[]): CoreIssue[] {
  const attacked = devices.filter((d) => d.active_attacks.length > 0 || d.live.status === "alert");
  return [
    {
      id: "attacks", title: "Active attacks & alerts", severity: "critical" as const, fix: null,
      why: "Devices currently under a simulated attack or raising live alerts.",
      devices: attacked,
    },
    {
      id: "hndl", title: "Data exposed before Q-Day", severity: "critical" as const, fix: "enable_hybrid_mlkem",
      why: "Data lifetime + migration time exceeds the assumed years to Q-Day while key exchange is classical (Mosca).",
      devices: devices.filter((d) => d.live.hndl_exposed),
    },
    {
      id: "kex", title: "Classical key exchange", severity: "high" as const, fix: "enable_hybrid_mlkem",
      why: "ECDHE / RSA key establishment is breakable by Shor's algorithm — root cause of harvest-now-decrypt-later.",
      devices: devices.filter((d) => !d.live.kex_pq),
    },
    {
      id: "sig", title: "Classical device certificates", severity: "high" as const, fix: "pq_certificates",
      why: "ECDSA / RSA certificates can be forged once a quantum computer exists — device identity is at risk.",
      devices: devices.filter((d) => !d.live.sig_pq),
    },
  ];
}

export function topIssue(d: SimDevice, catalog: SimCatalog | null): string {
  if (d.active_attacks.length) return catalog?.attacks.find((a) => a.id === d.active_attacks[0])?.label ?? d.active_attacks[0];
  if (d.live.alerts.length) return d.live.alerts[0].replaceAll("_", " ");
  if (d.live.hndl_exposed) return "HNDL-exposed data";
  if (!d.live.kex_pq) return "Classical key exchange";
  if (!d.live.sig_pq) return "Classical certificate";
  return "—";
}

export function CoreIssuesTable({ issues, onOpen }: { issues: CoreIssue[]; onOpen: (id: string) => void }) {
  return (
    <div className="card" data-testid="core-issues">
      <div className="card-h"><span className="h">Core issues</span><span className="xs faint">fleet root causes</span></div>
      <table className="t mini">
        <tbody>
          {issues.map((i) => (
            <tr key={i.id} className={`clickable ${i.devices.length ? "" : "muted-row"}`} onClick={() => onOpen(i.id)} data-testid={`core-${i.id}`} title={i.why}>
              <td><span className={`sev sev-${i.devices.length ? i.severity : "info"}`}>{i.devices.length}</span></td>
              <td>{i.title}</td>
              <td className="chev"><ChevronRight size={14} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AffectedDevicesTable({ devices, catalog, selected, onOpen }: {
  devices: SimDevice[]; catalog: SimCatalog | null; selected?: string; onOpen: (id: string) => void;
}) {
  const rows = [...devices].sort((a, b) => b.live.risk - a.live.risk);
  return (
    <div className="card affected" data-testid="affected-devices">
      <div className="card-h"><span className="h">Affected devices</span><span className="xs faint">by live risk</span></div>
      <table className="t mini">
        <thead><tr><th>Device</th><th>Risk</th><th>Issue</th></tr></thead>
        <tbody>
          {rows.map((d) => (
            <tr key={d.id} className={`clickable ${selected === d.id ? "sel" : ""}`} onClick={() => onOpen(d.id)} data-testid={`affected-${d.id}`}>
              <td className="mono"><span className={`dot ${d.live.status === "alert" ? "bad" : d.live.status === "warning" ? "warn" : "ok"}`} /> {d.id}</td>
              <td className={`mono ${d.live.risk > 50 ? "status-UNSAFE" : d.live.risk > 25 ? "status-AT_RISK" : "status-SAFE"}`}>{d.live.risk}</td>
              <td className="xs muted ellipsis">{topIssue(d, catalog)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
