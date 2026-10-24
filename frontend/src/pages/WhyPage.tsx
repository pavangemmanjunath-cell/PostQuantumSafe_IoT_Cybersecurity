import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { SimCatalog } from "../api/types";
import { Kpi, Panel, pretty } from "../components/ui";

const LAYER_LABEL: Record<string, string> = { quantum: "Post-quantum", identity: "Identity & secrets", network: "Network", ai: "AI / data" };

const STEPS = [
  ["Inventory", "Know every algorithm in use — key exchange, signatures, ciphers, hashes.", "Crypto Inventory agent"],
  ["Prioritise", "Rank systems by data lifetime and exposure (harvest-now-decrypt-later, Mosca).", "PQ Identification agent · Q-Day what-if"],
  ["Protect confidentiality", "Move key exchange to hybrid X25519 + ML-KEM-768 (FIPS 203).", "Defence: Hybrid ML-KEM"],
  ["Protect authenticity", "Re-issue device certificates with ML-DSA (FIPS 204).", "Defence: ML-DSA certificates"],
  ["Prevent fallback", "Disable legacy TLS and classical-only groups; refuse downgrades, including AI-requested ones.", "Defence: PQ-only policy · prompt firewall"],
  ["Plan within constraints", "Sequence the work to fit budget and maintenance windows.", "QIRO planner"],
];

const REFS: [string, string][] = [
  ["NIST FIPS 203 — ML-KEM (2024)", "https://csrc.nist.gov/pubs/fips/203/final"],
  ["NIST FIPS 204 — ML-DSA (2024)", "https://csrc.nist.gov/pubs/fips/204/final"],
  ["NIST FIPS 205 — SLH-DSA (2024)", "https://csrc.nist.gov/pubs/fips/205/final"],
  ["NIST IR 8547 (initial public draft) — Transition to PQC standards", "https://csrc.nist.gov/pubs/ir/8547/ipd"],
  ["RFC 8446 — TLS 1.3 (incl. downgrade protection)", "https://www.rfc-editor.org/rfc/rfc8446"],
  ["RFC 8996 — Deprecating TLS 1.0 and 1.1", "https://www.rfc-editor.org/rfc/rfc8996"],
  ["IETF draft — Hybrid ECDHE-MLKEM key agreement for TLS 1.3", "https://datatracker.ietf.org/doc/draft-ietf-tls-ecdhe-mlkem/"],
  ["IEEE 2933-2024 — Clinical IoT data and device interoperability with TIPPSS", "https://standards.ieee.org/ieee/2933/10806/"],
  ["M. Mosca, Cybersecurity in an era with quantum computers: will we be ready? IEEE Security & Privacy, 2018", "https://doi.org/10.1109/MSP.2018.3761723"],
];

export function WhyPage() {
  const [catalog, setCatalog] = useState<SimCatalog | null>(null);
  useEffect(() => { api.simCatalog().then(setCatalog).catch(() => undefined); }, []);
  const mitigation = (id: string) => catalog?.mitigations.find((m) => m.id === id)?.label ?? pretty(id);

  return (
    <div className="stack" style={{ maxWidth: 1180 }} data-testid="why-page">
      <div className="page-head">
        <div>
          <div className="page-title">Why post-quantum security matters for connected healthcare</div>
          <div className="page-sub">What the threat is, why clinical IoT is exposed early, and what this tool simulates.</div>
        </div>
      </div>

      <div className="kpi-strip">
        <Kpi label="NIST PQC standards" value="2024" hint="FIPS 203 · 204 · 205 published" />
        <Kpi label="Proposed deprecation" value="2030" hint="quantum-vulnerable algorithms (NIST IR 8547, draft)" />
        <Kpi label="Proposed disallowance" value="2035" hint="NIST IR 8547, draft" />
        <Kpi label="Risk test" value="x + y > z" hint="data lifetime + migration time > years to Q-Day" />
      </div>

      <div className="cols-3">
        <Panel title="1 · The threat">
          <ul className="list-plain">
            <li><strong>Shor's algorithm</strong> on a cryptographically relevant quantum computer (CRQC) breaks RSA, Diffie-Hellman and elliptic-curve cryptography — today's key exchange and digital signatures.</li>
            <li><strong>Grover's algorithm</strong> only weakens symmetric keys and hashes; AES-256 and SHA-384 keep a comfortable margin.</li>
            <li>When a CRQC will exist is uncertain — so planning uses explicit assumptions rather than a date.</li>
          </ul>
        </Panel>
        <Panel title="2 · Harvest now, decrypt later">
          <ul className="list-plain">
            <li>Encrypted traffic can be <strong>recorded today</strong> and decrypted once a CRQC exists.</li>
            <li>Data that must stay confidential for many years is therefore <strong>already at risk</strong> if its key exchange is classical.</li>
            <li>Mosca's inequality: if <em>data lifetime + migration time &gt; time to Q-Day</em>, migration is overdue.</li>
          </ul>
        </Panel>
        <Panel title="3 · Why healthcare is exposed early">
          <ul className="list-plain">
            <li>Medical records are retained for long periods (requirements vary by jurisdiction).</li>
            <li>Clinical devices often stay in service for many years and are hard to patch or re-key.</li>
            <li>Compromise affects patient safety, not only privacy — the TIPPSS view (IEEE 2933-2024).</li>
            <li>AI assistants add a new path: prompts that ask an agent to weaken crypto.</li>
          </ul>
        </Panel>
      </div>

      <Panel title="4 · What this tool simulates" right={<span className="pill">live from the simulator catalogue</span>}>
        <table className="t" data-testid="why-attacks">
          <thead><tr><th>Layer</th><th>Simulation</th><th>What it models</th><th>Detected by</th><th>Stopped by</th></tr></thead>
          <tbody>
            {catalog?.attacks.map((a) => (
              <tr key={a.id}>
                <td><span className="tag">{LAYER_LABEL[a.layer] ?? a.layer}</span></td>
                <td style={{ fontWeight: 600, whiteSpace: "nowrap" }}>{a.label}</td>
                <td className="small muted">{a.description}</td>
                <td className="xs mono">{a.detected_by.join(", ")}</td>
                <td className="xs">{a.blocked_by.map(mitigation).join(", ")}</td>
              </tr>
            ))}
            <tr>
              <td><span className="tag">Post-quantum</span></td>
              <td style={{ fontWeight: 600 }}>Q-Day what-if</td>
              <td className="small muted">Change the assumed years until a CRQC and your migration time; devices are re-classified as HNDL-exposed using Mosca's inequality.</td>
              <td className="xs mono">pq_identification</td>
              <td className="xs">Hybrid ML-KEM key exchange</td>
            </tr>
          </tbody>
        </table>
      </Panel>

      <Panel title="5 · Migration path the tool follows">
        <div className="cols-3">
          {STEPS.map(([title, text, tool], i) => (
            <div key={title} className="kpi-card">
              <div className="label">Step {i + 1}</div>
              <div style={{ fontWeight: 600, margin: "4px 0" }}>{title}</div>
              <div className="small muted">{text}</div>
              <div className="xs" style={{ color: "var(--accent)", marginTop: 6 }}>{tool}</div>
            </div>
          ))}
        </div>
      </Panel>

      <div className="cols-2">
        <Panel title="Scope">
          <ul className="list-plain">
            <li>Assesses <strong>supplied configurations and telemetry</strong>; it does not scan or attack real systems.</li>
            <li>No quantum computer is used or emulated: quantum-era attacks are modelled by their <strong>effect</strong> on classical cryptography.</li>
            <li>All devices, patients and traffic in the simulator are synthetic.</li>
            <li>Research prototype — not a certified assessment and not for clinical decisions.</li>
          </ul>
        </Panel>
        <Panel title="References">
          <ul className="list-plain small">
            {REFS.map(([t, u]) => <li key={u}><a href={u} target="_blank" rel="noreferrer">{t}</a></li>)}
          </ul>
        </Panel>
      </div>
    </div>
  );
}
