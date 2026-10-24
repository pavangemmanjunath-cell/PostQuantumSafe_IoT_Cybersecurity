import { useCallback, useEffect, useRef, useState } from "react";
import { api, wsUrl } from "../api/client";
import type { SimEvent, SimSnapshot } from "../api/types";

const HISTORY = 60;

export interface TelemetryPoint {
  tick: number;
  syn: number;
  rate: number;
  udp: number;
  risk: number;
}

export interface FleetPoint {
  tick: number;
  mean: number;
  max: number;
  issues: number;
}

/** Owns one simulation: creation, the live WebSocket stream, event log, per-device and fleet risk history. */
export function useSimulation(template: string, seed: number, paused: boolean) {
  const [snapshot, setSnapshot] = useState<SimSnapshot | null>(null);
  const [events, setEvents] = useState<SimEvent[]>([]);
  const [history, setHistory] = useState<Record<string, TelemetryPoint[]>>({});
  const [fleetHistory, setFleetHistory] = useState<FleetPoint[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const createdKey = useRef<string | null>(null);

  const ingest = useCallback((snap: SimSnapshot) => {
    setSnapshot(snap);
    if (snap.events.length) {
      setEvents((prev) => {
        const seen = new Set(prev.map((e) => e.seq));
        return [...snap.events.filter((e) => !seen.has(e.seq)).reverse(), ...prev].slice(0, 300);
      });
    }
    setHistory((prev) => {
      const next = { ...prev };
      for (const d of snap.devices) {
        const f = d.live.features;
        const arr = next[d.id] ?? [];
        const point = { tick: snap.tick, syn: f.syn_ratio ?? 0, rate: f.rate_mean ?? 0, udp: f.udp_ratio ?? 0, risk: d.live.risk ?? 0 };
        next[d.id] = [...arr.filter((p) => p.tick !== snap.tick), point].sort((p, q) => p.tick - q.tick).slice(-HISTORY);
      }
      return next;
    });
    setFleetHistory((prev) => {
      const risks = snap.devices.map((d) => d.live.risk ?? 0);
      const issues = snap.devices.reduce((n, d) => n + d.active_attacks.length + (d.live.alerts?.length ?? 0), 0);
      const point = { tick: snap.tick, mean: risks.reduce((a, b) => a + b, 0) / Math.max(1, risks.length), max: Math.max(0, ...risks), issues };
      return [...prev.filter((p) => p.tick !== snap.tick), point].sort((p, q) => p.tick - q.tick).slice(-HISTORY);
    });
  }, []);

  const create = useCallback(async () => {
    setError(null);
    setEvents([]);
    setHistory({});
    setFleetHistory([]);
    try {
      ingest(await api.createSim(template, seed));
    } catch (e) {
      setError((e as Error).message);
    }
  }, [template, seed, ingest]);

  useEffect(() => {
    const key = `${template}:${seed}`;
    if (createdKey.current === key) return; // StrictMode double-invocation guard
    createdKey.current = key;
    void create();
  }, [template, seed, create]);

  const simId = snapshot?.id;
  useEffect(() => {
    if (!simId || paused) return;
    const ws = new WebSocket(wsUrl(`/simulations/${simId}/stream?interval_ms=1000`));
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setError("Live stream disconnected — is the backend running?");
    ws.onmessage = (m) => ingest(JSON.parse(m.data) as SimSnapshot);
    return () => ws.close();
  }, [simId, paused, ingest]);

  return { snapshot, setSnapshot: ingest, events, history, fleetHistory, connected, error, recreate: create };
}
