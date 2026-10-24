import { useState } from "react";
import type { AgentInfo } from "../api/types";
import type { AgentLiveMap } from "../hooks/useAssessmentStream";

/** Compact live view of the agents: progress bar + one chip per agent; click a chip for its reasoning and tool calls. */
export function AgentPipeline({ agents, live, dense = false }: { agents: AgentInfo[]; live: AgentLiveMap; dense?: boolean }) {
  const [open, setOpen] = useState<string | null>(null);
  const done = Object.values(live).filter((a) => ["completed", "skipped", "failed"].includes(a.status)).length;
  const running = agents.find((a) => live[a.id]?.status === "running");
  const sel = open ? agents.find((a) => a.id === open) : undefined;
  const s = open ? live[open] : undefined;

  if (dense) {
    return (
      <div data-testid="agent-pipeline">
        <div className="stepper-head">
          <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{running ? running.title : done ? "Assessment complete" : "Idle"}</span>
          <span data-testid="agents-done">{done}/{agents.length} done</span>
        </div>
        <div className="agent-dots">
          {agents.map((a) => {
            const st = live[a.id]?.status ?? "pending";
            return <div key={a.id} className={`agent-dot ${st}`} title={`${a.title}: ${st}`} data-testid={`agent-${a.id}`} data-status={st} />;
          })}
        </div>
      </div>
    );
  }
  return (
    <div data-testid="agent-pipeline">
      <div className="stepper-head">
        <span>{running ? <>Running: <strong style={{ color: "var(--text)" }}>{running.title}</strong></> : done ? "Agents finished — click an agent to see its reasoning" : "Agents idle"}</span>
        <span data-testid="agents-done">{done}/{agents.length} done</span>
      </div>
      <div className="progress"><span style={{ width: `${agents.length ? (done / agents.length) * 100 : 0}%` }} /></div>
      <div className="chips">
        {agents.map((a) => {
          const st = live[a.id]?.status ?? "pending";
          const n = live[a.id]?.findings.length ?? 0;
          return (
            <button key={a.id} className={`chip ${st} ${open === a.id ? "open" : ""}`} data-testid={`agent-${a.id}`} data-status={st}
              title={a.description} onClick={() => setOpen(open === a.id ? null : a.id)}>
              <span className="sdot" />{a.title}{n > 0 && <span className="n">{n}</span>}
            </button>
          );
        })}
      </div>
      {sel && (
        <div className="agent-panel">
          <div style={{ color: "var(--text)", fontWeight: 600 }}>{sel.title}</div>
          <div className="xs faint">{sel.description}</div>
          {s?.notes.length ? <ul>{s.notes.map((t, i) => <li key={i}>{t}</li>)}</ul> : <div className="xs" style={{ marginTop: 6 }}>No activity yet.</div>}
          {!!s?.tools.length && (
            <div className="xs mono" style={{ marginTop: 6 }}>
              {s.tools.map((t, i) => <div key={i}>→ {t.tool}: {t.summary}</div>)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
