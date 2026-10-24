import type { Health } from "../api/types";

export function AboutPage({ health }: { health: Health | null }) {
  return (
    <div className="stack" style={{ maxWidth: 980 }}>
      <div className="notice" data-testid="research-status">
        <strong>Research status: early-stage concept.</strong> This software is a thought-process prototype shared to invite discussion,
        reproduction and improvement. Detection rules are transparent heuristics, remediation costs are illustrative placeholders,
        and all bundled data is synthetic. It is not a certified security assessment, not a compliance attestation and must not be
        used for clinical decision-making.
      </div>
      <div className="cols-2">
        <div className="panel">
          <div className="panel-h"><h3>What it does</h3></div>
          <div className="panel-b small stack">
            <div>• 14 cooperating agents assess one system or a whole IoT fleet across the IEEE 2933-2024 TIPPSS pillars
              (Trust, Identity, Privacy, Protection, Safety, Security).</div>
            <div>• Post-quantum identification classifies every primitive against NIST FIPS 203/204/205 and the NIST IR 8547 draft
              transition timeline, and evaluates harvest-now-decrypt-later exposure with Mosca's inequality.</div>
            <div>• QIRO plans remediation under budget and downtime limits (simulated annealing + local search), and reports its gap to
              the exact optimum where computable.</div>
            <div>• Every result is explainable: evidence per finding, exact score attribution, counterfactuals and full agent traces.</div>
            <div>• The fleet simulator injects quantum-layer, network, identity and AI attacks and lets you test defences.</div>
          </div>
        </div>
        <div className="panel">
          <div className="panel-h"><h3>Runtime</h3></div>
          <div className="panel-b small stack">
            <div>Backend version: <span className="mono">{health?.version ?? "unreachable"}</span></div>
            <div>Narrative LLM: <span className="mono">{health ? (health.llm.provider === "none" ? "none (deterministic template)" : `${health.llm.provider} · ${health.llm.model}`) : "—"}</span></div>
            <div>Live online tools: <span className="mono">{health?.online_tools_enabled ? "enabled" : "disabled"}</span></div>
            <div className="hint">Configure an LLM through <span className="mono">.env</span> (LLM_PROVIDER, LLM_MODEL, LLM_BASE_URL, LLM_API_KEY).
              The LLM only phrases the narrative from redacted aggregates — it never decides the verdict.</div>
          </div>
        </div>
      </div>
      <div className="panel">
        <div className="panel-h"><h3>Author & citation</h3></div>
        <div className="panel-b small stack">
          <div>Pavan Manjunath · ORCID <a href="https://orcid.org/0000-0002-2694-8807" target="_blank" rel="noreferrer">0000-0002-2694-8807</a></div>
          <div>Repository: <a href="https://github.com/pavangemmanjunath-cell/PostQuantumSafe_IoT_Cybersecurity" target="_blank" rel="noreferrer">PostQuantumSafe_IoT_Cybersecurity</a> · contributions welcome (see CONTRIBUTING.md).</div>
          <div>Software DOI (all versions): <a href="https://doi.org/10.5281/zenodo.23618135" target="_blank" rel="noreferrer">10.5281/zenodo.23618135</a></div>
          <div>Cite via the repository's <span className="mono">CITATION.cff</span> ("Cite this repository" on GitHub). Licensed under Apache-2.0.</div>
          <div className="hint">Datasets referenced for evaluation (CICIoMT2024, Synthea) are not redistributed; see datasets/README.md for sources and licences.</div>
        </div>
      </div>
    </div>
  );
}
