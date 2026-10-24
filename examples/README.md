# Examples

All examples use synthetic data, run offline and are deterministic.

| Example | What it shows | Command |
|---|---|---|
| `assess_scenario.py` | In-process assessment: verdict, explanation, PQ identification, QIRO plan | `python examples/assess_scenario.py` |
| CLI | Built-in scenario to PDF + JSON | `safeguard-pq assess --scenario legacy_worst_case --pdf report.pdf --json result.json` |
| REST | Assess via HTTP (backend running) | `curl -X POST http://127.0.0.1:8000/api/v1/assessments -H "content-type: application/json" -d @request.json` |
| Upload | Synthetic SYN-flood capture | `curl -F file=@datasets/samples/synthetic_syn_flood.csv -F tls_profile=legacy http://127.0.0.1:8000/api/v1/uploads/assess` |
| Tool API | Classify an algorithm | `curl -X POST http://127.0.0.1:8000/api/v1/tools/pqc.classify_algorithm -H "content-type: application/json" -d "{\"name\":\"X25519MLKEM768\"}"` |

Install first: `pip install -e "backend[dev]"`.
