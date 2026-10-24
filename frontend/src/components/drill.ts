/**
 * Use case: "ICU Q-Day drill".
 *
 * A hospital ICU ward runs infusion pumps, ECG monitors, an imaging gateway and a clinical AI
 * assistant. Most devices still use classical public-key cryptography and keep patient data for
 * 15–30 years. The drill walks through the post-quantum risk lifecycle at a high level —
 * record now, weaken, Q-Day, AI misuse — then shows the SafeGuard agents detecting it and the
 * defences that remove the risk. All actions run against the synthetic simulator only.
 */

export type Actor = "analyst" | "adversary";

export interface DrillAction {
  inject?: { device: string; attack: string }[];
  mitigate?: { mitigation: string; device: string | null }[];
  qday?: { years_to_crqc: number; migration_years: number };
  assess?: string;
  select?: string;
}

export interface DrillStep {
  id: string;
  stage: string;
  actor: Actor;
  title: string;
  text: string;
  layer: string;
  action?: DrillAction;
}

export const DRILL_TEMPLATE = "hospital_ward";

export const DRILL: DrillStep[] = [
  {
    id: "baseline", stage: "Baseline", actor: "analyst", layer: "Fleet inventory",
    title: "Know the ward",
    text: "Nine devices online. Six still rely on classical key exchange and signatures (ECDHE / ECDSA / RSA).",
    action: { select: "PUMP-ICU-A12", qday: { years_to_crqc: 10, migration_years: 5 } },
  },
  {
    id: "capture", stage: "Record now", actor: "adversary", layer: "Network link (passive)",
    title: "Encrypted traffic is recorded",
    text: "Infusion-pump sessions are stored for later. Nothing breaks today — the risk is future decryption.",
    action: { inject: [{ device: "PUMP-ICU-A12", attack: "hndl_capture" }] },
  },
  {
    id: "weaken", stage: "Weaken", actor: "adversary", layer: "Transport · TLS key exchange",
    title: "Imaging gateway falls back to classical",
    text: "The hybrid ML-KEM share is dropped because classical-only groups are still accepted.",
    action: { inject: [{ device: "PACS-GW-01", attack: "pq_strip" }], select: "PACS-GW-01" },
  },
  {
    id: "qday", stage: "Q-Day", actor: "adversary", layer: "Device identity · certificate key",
    title: "Assume a quantum computer in 6 years",
    text: "Long-lived data becomes exposed (Mosca) and classical device certificates can be forged.",
    action: { qday: { years_to_crqc: 6, migration_years: 5 }, inject: [{ device: "ECG-ICU-007", attack: "cert_spoof" }], select: "ECG-ICU-007" },
  },
  {
    id: "ai", stage: "AI misuse", actor: "adversary", layer: "Application · AI assistant",
    title: "AI asked to switch off ML-KEM",
    text: "A prompt instructs the clinical AI assistant to disable post-quantum key exchange.",
    action: { inject: [{ device: "AI-ASSIST-01", attack: "pq_downgrade_prompt" }], select: "AI-ASSIST-01" },
  },
  {
    id: "detect", stage: "Detect", actor: "analyst", layer: "14 SafeGuard agents",
    title: "Agents assess the ECG monitor",
    text: "Crypto inventory, PQ identification, identity and AI agents explain what is wrong and what to fix first.",
    action: { select: "ECG-ICU-007", assess: "ECG-ICU-007" },
  },
  {
    id: "respond", stage: "Respond", actor: "analyst", layer: "Crypto policy · certificates · AI guardrails",
    title: "Roll out post-quantum defences",
    text: "Hybrid ML-KEM, ML-DSA certificates, PQ-only policy, re-authentication and a prompt firewall across the ward.",
    action: {
      mitigate: [
        { mitigation: "enable_hybrid_mlkem", device: null },
        { mitigation: "pq_certificates", device: null },
        { mitigation: "pq_policy_pinning", device: null },
        { mitigation: "device_reauth", device: null },
        { mitigation: "prompt_firewall", device: null },
      ],
    },
  },
  {
    id: "verify", stage: "Verify", actor: "analyst", layer: "14 SafeGuard agents",
    title: "Agents re-assess",
    text: "Now post-quantum ready. Sessions recorded before the migration stay exposed — which is why migration must finish before Q-Day.",
    action: { select: "ECG-ICU-007", assess: "ECG-ICU-007" },
  },
];
