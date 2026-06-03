"""
TIPPSS SafeGuard-PQ — Unit Test Runner
=======================================
Reads test_cases.json, posts each payload to n8n, saves
every result as a timestamped JSON in test_outputs/unit_tests/,
and writes a CSV + JSON summary.

Usage:
    python run_tests.py
    python run_tests.py --url http://localhost:5678/webhook/tippss-assessment
"""

import argparse
import json
import pathlib
import sys
import time
from datetime import datetime

import requests

# ---------------------------------------------------------------------------
N8N_URL      = "http://localhost:5678/webhook/tippss-assessment"
TESTS_FILE   = pathlib.Path(__file__).parent / "test_cases.json"
OUTPUT_DIR   = pathlib.Path(__file__).parent / "test_outputs" / "unit_tests"
TIMEOUT_SECS = 120
# ---------------------------------------------------------------------------


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def post_to_n8n(payload: dict, url: str) -> tuple[dict | None, str]:
    try:
        resp = requests.post(url, json=payload, timeout=TIMEOUT_SECS)
        resp.raise_for_status()
        return resp.json(), "ok"
    except requests.exceptions.ConnectionError:
        return None, "CONNECTION_ERROR: n8n not reachable at " + url
    except requests.exceptions.Timeout:
        return None, f"TIMEOUT after {TIMEOUT_SECS}s"
    except requests.exceptions.HTTPError as e:
        return None, f"HTTP_ERROR: {e}"
    except Exception as e:
        return None, f"ERROR: {e}"


def evaluate(tc: dict, result: dict) -> tuple[bool, list[str]]:
    """Check result against expected values; return (passed, list_of_issues)."""
    issues = []
    score    = result.get("pq_risk_score", 0)
    verdict  = result.get("verdict", "")
    findings = result.get("findings", [])
    qiro     = result.get("qiro_optimization", {})

    ev = tc.get("expected_verdict_type", "any")
    if ev == "critical"       and score < tc.get("expected_min_score", 0):
        issues.append(f"Score {score} < expected min {tc.get('expected_min_score')}")
    if ev == "safe"           and score > tc.get("expected_max_score", 100):
        issues.append(f"Score {score} > expected max {tc.get('expected_max_score')}")

    if "expected_min_findings" in tc and len(findings) < tc["expected_min_findings"]:
        issues.append(f"Findings {len(findings)} < expected min {tc['expected_min_findings']}")
    if "expected_max_findings" in tc and len(findings) > tc["expected_max_findings"]:
        issues.append(f"Findings {len(findings)} > expected max {tc['expected_max_findings']}")

    if tc.get("expected_phi_finding"):
        types = {f.get("type") for f in findings}
        if not types & {"medical_record_number", "patient_identifier", "sensitive_diagnosis", "email"}:
            issues.append("Expected PHI finding not detected")

    if tc.get("expected_secret_finding"):
        types = {f.get("agent") for f in findings}
        if "secret_exposure" not in types:
            issues.append("Expected secret_exposure finding not detected")

    if tc.get("expected_safety_finding"):
        types = {f.get("agent") for f in findings}
        if "safety_risk" not in types:
            issues.append("Expected safety_risk finding not detected")

    if "expected_qiro_cost_max" in tc:
        cost = qiro.get("total_cost_usd", 999_999_999)
        if cost > tc["expected_qiro_cost_max"]:
            issues.append(f"QIRO cost ${cost:,} exceeds budget constraint ${tc['expected_qiro_cost_max']:,}")

    return (len(issues) == 0), issues


def run_tests(url: str):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not TESTS_FILE.exists():
        print(f"[ERROR] test_cases.json not found at {TESTS_FILE}")
        sys.exit(1)

    test_cases = json.loads(TESTS_FILE.read_text(encoding="utf-8"))
    run_ts     = _ts()
    summary    = []

    print(f"\n{'='*70}")
    print(f"  TIPPSS SafeGuard-PQ — Unit Test Suite")
    print(f"  n8n URL : {url}")
    print(f"  Tests   : {len(test_cases)}")
    print(f"  Run ID  : {run_ts}")
    print(f"{'='*70}\n")

    for tc in test_cases:
        tid   = tc["test_id"]
        tname = tc["test_name"]
        print(f"  [{tid}] {tname} ... ", end="", flush=True)

        t0     = time.time()
        result, error = post_to_n8n(tc["payload"], url)
        elapsed = round(time.time() - t0, 2)

        if result is None:
            print(f"FAIL  ({error})")
            row = {
                "test_id":                tid,
                "test_name":              tname,
                "description":            tc.get("description",""),
                "expected_verdict_type":  tc.get("expected_verdict_type",""),
                "verdict":                "N/A",
                "pq_risk_score":          "N/A",
                "findings_count":         "N/A",
                "qiro_selected_actions":  "N/A",
                "qiro_total_cost_usd":    "N/A",
                "qiro_total_downtime_hrs":"N/A",
                "elapsed_s":              elapsed,
                "passed":                 False,
                "issues":                 error,
                "output_json_file":       "N/A",
            }
            summary.append(row)
            continue

        passed, issues = evaluate(tc, result)
        status = "PASS" if passed else "FAIL"

        # Save individual result
        out_name = f"{tid}_{tname}_{run_ts}_result.json"
        out_path = OUTPUT_DIR / out_name
        out_path.write_text(json.dumps({
            "meta": {
                "test_id": tid, "test_name": tname,
                "run_ts": run_ts, "elapsed_s": elapsed,
                "passed": passed, "issues": issues,
            },
            "payload": tc["payload"],
            "result":  result,
        }, indent=2, ensure_ascii=False), encoding="utf-8")

        score    = result.get("pq_risk_score", "?")
        verdict  = result.get("verdict", "?")
        nf       = result.get("findings_count", 0)
        qiro     = result.get("qiro_optimization", {})
        n_act    = qiro.get("selection_count", 0)
        q_cost   = qiro.get("total_cost_usd", 0)
        q_down   = qiro.get("total_downtime_hrs", 0)

        print(f"{status}  score={score}  verdict={verdict}  findings={nf}  qiro_actions={n_act}  ({elapsed}s)")
        if not passed:
            for iss in issues:
                print(f"          ⚠ {iss}")

        summary.append({
            "test_id":                tid,
            "test_name":              tname,
            "description":            tc.get("description",""),
            "expected_verdict_type":  tc.get("expected_verdict_type",""),
            "verdict":                verdict,
            "pq_risk_score":          score,
            "findings_count":         nf,
            "qiro_selected_actions":  n_act,
            "qiro_total_cost_usd":    q_cost,
            "qiro_total_downtime_hrs":q_down,
            "elapsed_s":              elapsed,
            "passed":                 passed,
            "issues":                 "; ".join(issues) if issues else "",
            "output_json_file":       out_name,
        })

    # Save summary CSV
    try:
        import csv
        csv_path = OUTPUT_DIR / f"unit_test_summary_{run_ts}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(summary[0].keys()) if summary else [])
            writer.writeheader()
            writer.writerows(summary)
        print(f"\n  CSV summary → {csv_path}")
    except Exception as e:
        print(f"\n  [WARN] Could not write CSV: {e}")

    # Save summary JSON
    json_path = OUTPUT_DIR / f"unit_test_summary_{run_ts}.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"  JSON summary → {json_path}")

    passed_n = sum(1 for r in summary if r["passed"])
    total_n  = len(summary)
    print(f"\n{'='*70}")
    print(f"  Results: {passed_n}/{total_n} passed")
    print(f"{'='*70}\n")

    return passed_n == total_n


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TIPPSS unit test runner")
    parser.add_argument("--url", default=N8N_URL, help="n8n webhook URL")
    args = parser.parse_args()
    ok = run_tests(args.url)
    sys.exit(0 if ok else 1)
