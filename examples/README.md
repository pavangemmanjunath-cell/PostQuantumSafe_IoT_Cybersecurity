# Examples

All examples use synthetic data, run offline and are deterministic.

| Example | What it shows | Command |
|---|---|---|
| `assess_scenario.py` | In-process assessment: verdict, explanation, PQ identification, QIRO plan | `python examples/assess_scenario.py` |
| CLI | Built-in scenario to PDF + JSON | `safeguard-pq assess --scenario legacy_worst_case --pdf report.pdf --json result.json` |
| REST | Assess via HTTP (backend running) | `curl -X POST http://127.0.0.1:8000/api/v1/assessments -H "content-type: application/json" -d @request.json` |
| Upload | Synthetic SYN-flood capture | `curl -F file=@datasets/samples/synthetic_syn_flood.csv -F tls_profile=legacy http://127.0.0.1:8000/api/v1/uploads/assess` |
| Tool API | Classify an algorithm | `curl -X POST http://127.0.0.1:8000/api/v1/tools/pqc.classify_algorithm -H "content-type: application/json" -d "{\"name\":\"X25519MLKEM768\"}"` |
| `paper/worked_example_gateway.json` | The worked example of the journal paper (Section III; Listing 1 of the original draft): infusion-pump gateway, TLS 1.2, ECDHE-P256, ECDSA-P256, 25-year records, 60,000 USD / 12 h | `safeguard-pq assess --file examples/paper/worked_example_gateway.json` (expected: UNSAFE, PQ score 46, 5 findings, QIRO 2 actions) |
| `paper/e2_infusion_pump_conditions.json` | Inputs of paper experiment E2: the legacy infusion-pump gateway, its six attack conditions and the countermeasures | `python benchmarks/paper_experiments.py --only e2` |

Install first: `pip install -e "backend[dev]"`. All paper experiments E1–E5 with their inputs and the numbers the
paper states: `python benchmarks/paper_experiments.py` (see [docs/reproducibility.md](../docs/reproducibility.md)).
The paper's worked example is the Section III gateway above, not the built-in ICU gateway scenario
`icu_gateway_critical`.
