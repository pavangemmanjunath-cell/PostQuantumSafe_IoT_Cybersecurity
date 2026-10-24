import { useEffect, useState } from "react";
import { api } from "./api/client";
import type { AgentInfo, Health } from "./api/types";
import { AboutPage } from "./pages/AboutPage";
import { AgentsPage } from "./pages/AgentsPage";
import { LabPage } from "./pages/LabPage";
import { SimulationPage } from "./pages/SimulationPage";
import { WhyPage } from "./pages/WhyPage";

type Tab = "simulation" | "lab" | "why" | "agents" | "about";
const TABS: [Tab, string][] = [
  ["simulation", "Simulation"],
  ["lab", "Assessment"],
  ["why", "Why Post-Quantum"],
  ["agents", "Agents & Tools"],
  ["about", "About"],
];

function initialTab(): Tab {
  const h = window.location.hash.replace("#", "") as Tab;
  return TABS.some(([t]) => t === h) ? h : "simulation";
}

export default function App() {
  const [tab, setTab] = useState<Tab>(initialTab);
  const [health, setHealth] = useState<Health | null>(null);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    const load = () =>
      Promise.all([api.health(), api.agents()])
        .then(([h, a]) => { setHealth(h); setAgents(a); setOffline(false); })
        .catch(() => setOffline(true));
    void load();
    const t = window.setInterval(load, 15000);
    return () => window.clearInterval(t);
  }, []);

  const go = (t: Tab) => { setTab(t); window.location.hash = t; window.scrollTo(0, 0); };

  return (
    <div className={`app ${tab === "simulation" ? "app-fill" : ""}`}>
      <header className="topbar">
        <div className="brand">
          <svg className="brand-mark" viewBox="0 0 64 64" aria-hidden><path d="M32 4 8 13v17c0 15 10 26 24 30 14-4 24-15 24-30V13Z" fill="#0ea5e9" /><path d="M22 33l7 7 14-15" stroke="#fff" strokeWidth="5" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>
          <div>
            <div className="brand-title">TIPPSS SafeGuard-PQ</div>
            <div className="brand-sub">Post-Quantum Simulation Tool</div>
          </div>
        </div>
        <nav className="tabs">
          {TABS.map(([t, label]) => (
            <button key={t} className={`tab ${tab === t ? "active" : ""}`} onClick={() => go(t)} data-testid={`tab-${t}`}>{label}</button>
          ))}
        </nav>
        <div className="topbar-right">
          <span className="pill" data-testid="backend-status" title={health ? `LLM: ${health.llm.provider}` : undefined}>
            <span className={`dot ${offline ? "bad" : health ? "ok" : ""}`} />{offline ? "API offline" : health ? `v${health.version}` : "connecting…"}
          </span>
          <span className="pill" style={{ borderColor: "#92400e", color: "#fcd34d" }}>Research prototype</span>
        </div>
      </header>

      <main className="main">
        {offline && <div className="error" style={{ marginBottom: 14 }}>Cannot reach the API. Start the backend: <span className="mono">safeguard-pq serve</span>.</div>}
        {tab === "simulation" && <SimulationPage agents={agents} />}
        {tab === "lab" && <LabPage agents={agents} />}
        {tab === "why" && <WhyPage />}
        {tab === "agents" && <AgentsPage agents={agents} />}
        {tab === "about" && <AboutPage health={health} />}
      </main>

      {tab !== "simulation" && <footer className="footer">
        <span>© 2026 Pavan Manjunath · Apache-2.0</span>
        <span>NIST FIPS 203/204/205 · NIST IR 8547 (draft) · IEEE 2933-2024</span>
        <span>Synthetic data · not for clinical decision-making</span>
      </footer>}
    </div>
  );
}
