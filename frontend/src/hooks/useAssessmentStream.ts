import { useCallback, useRef, useState } from "react";
import { wsUrl } from "../api/client";
import type { AgentStatus, AssessmentResult, Finding, StreamEvent } from "../api/types";

export interface AgentLive {
  status: AgentStatus;
  notes: string[];
  tools: { tool: string; summary: string }[];
  findings: Finding[];
  durationMs?: number;
}

export type AgentLiveMap = Record<string, AgentLive>;

const empty = (): AgentLive => ({ status: "pending", notes: [], tools: [], findings: [] });

/** Runs an assessment over the WebSocket API and exposes every agent step as it happens. */
export function useAssessmentStream() {
  const [agents, setAgents] = useState<AgentLiveMap>({});
  const [result, setResult] = useState<AssessmentResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const update = (id: string, fn: (a: AgentLive) => AgentLive) =>
    setAgents((prev) => ({ ...prev, [id]: fn(prev[id] ?? empty()) }));

  const run = useCallback((message: Record<string, unknown>, paceMs = 160): Promise<AssessmentResult> => {
    wsRef.current?.close();
    setAgents({});
    setResult(null);
    setError(null);
    setRunning(true);
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(wsUrl("/ws/assessments"));
      wsRef.current = ws;
      let done = false;
      ws.onopen = () => ws.send(JSON.stringify({ ...message, pace_ms: paceMs }));
      ws.onmessage = (msg) => {
        const e = JSON.parse(msg.data) as StreamEvent & { stages?: string[][] };
        switch (e.type) {
          case "run_started": {
            const init: AgentLiveMap = {};
            e.stages?.flat().forEach((id) => (init[id] = empty()));
            setAgents(init);
            break;
          }
          case "agent_started":
            update(e.agent!, (a) => ({ ...a, status: "running" }));
            break;
          case "agent_note":
            update(e.agent!, (a) => ({ ...a, notes: [...a.notes, e.text ?? ""] }));
            break;
          case "tool_called":
            update(e.agent!, (a) => ({ ...a, tools: [...a.tools, { tool: e.tool ?? "", summary: e.summary ?? "" }] }));
            break;
          case "finding":
            update(e.agent!, (a) => ({ ...a, findings: [...a.findings, e.finding!] }));
            break;
          case "agent_completed":
            update(e.agent!, (a) => ({ ...a, status: (e.status as AgentStatus) ?? "completed", durationMs: e.duration_ms }));
            break;
          case "result":
            done = true;
            setResult(e.result!);
            setRunning(false);
            resolve(e.result!);
            break;
          case "error":
            done = true;
            setError(e.detail ?? "assessment failed");
            setRunning(false);
            reject(new Error(e.detail));
            break;
        }
      };
      ws.onerror = () => {
        if (!done) {
          setError("Cannot reach the backend WebSocket. Is the API running on port 8000?");
          setRunning(false);
          reject(new Error("websocket error"));
        }
      };
      ws.onclose = () => {
        if (!done) setRunning(false);
      };
    });
  }, []);

  const reset = useCallback(() => {
    setAgents({});
    setResult(null);
    setError(null);
  }, []);

  return { agents, result, running, error, run, reset, setResult };
}
