# Limitations

## Scientific limitations
- The PQ risk score's weights and severity points are design choices inherited from the prototype, not calibrated.
- Mosca's inequality depends on a single, highly uncertain CRQC-arrival assumption supplied by the user.
- No comparative evaluation against other tools or expert-produced plans exists yet.

## Data limitations
- All bundled data is synthetic. Scenario identities are fictional.
- Traffic thresholds were set on the CICIoMT2024 test split and evaluated on the same split; ARP spoofing and malformed
  MQTT have only 17 windows each.

## Model limitations
- Regex detectors miss paraphrases, other languages and obfuscation, and can flag benign text.
- The "ARP spoofing" rule detects a protocol-mix signature of that capture, not ARP spoofing as such.
- No trained ML model is included.

## Generalisation limitations
- Device profiles, crypto defaults and remediation templates are illustrative, not vendor- or hospital-specific.
- Traffic features assume CICIoMT2024 column semantics.

## Computational limitations
- Exact optimum is computed only for ≤ 14 actions; larger plans (e.g. fleet plans) report no gap.
- Single-process, in-memory server.

## Security / privacy considerations
- No authentication; run locally only.
- Inputs may contain sensitive data if users supply real logs — redaction is pattern-based and not guaranteed complete.
  Use synthetic or de-identified data.
- Optional LLM and openFDA calls send data off-host (redacted aggregates / search terms only) and are off by default.

## Deployment limitations
- Not designed or tested for production, clinical or regulated environments.
- Assessments do not scan live systems; they evaluate supplied configuration.

## Areas requiring further validation
- Held-out evaluation of traffic rules; evaluation on other IoMT datasets.
- Usefulness of explanations and plans with practitioners.
- Cost/downtime estimates from real migration projects.
- Behaviour of the replay data source with full CICIoMT2024 files.
