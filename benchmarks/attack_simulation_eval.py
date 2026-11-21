"""Attacker-vs-defender evaluation on the simulated hospital fleet.

    python benchmarks/attack_simulation_eval.py --template hospital_ward --seeds 7,11,23 \\
        --out benchmarks/results/attack_simulation.json

For every attack of the simulator catalogue and every device of the template on which it applies
(AI attacks: AI-enabled devices only), with a fresh ``Simulation`` per (seed, device, attack):

1. baseline assessment of the device by the multi-agent pipeline (offline settings, no LLM report):
   S0 = pq_risk_score, status0 = environment status, the set of (agent, finding type) pairs;
2. ``sim.inject(device, attack)``, two simulator ticks, reassessment (S1, status1). The attack counts as
   *detected* when an agent listed in ``Attack.detected_by`` produced at least one finding type that was
   absent at baseline; ``flagged_after_attack`` additionally accepts findings that already existed;
3. every mitigation in ``Attack.blocked_by`` is applied to the device (``sim.mitigate``), two ticks,
   reassessment (S2, status2);
4. the same attack is injected again: *blocked* when the simulator refuses it; for the passive
   ``hndl_capture`` (never refused by design) blocked means the key exchange is PQ-safe after mitigation.

Attacks whose preconditions are absent on a device are recorded as ``preconditions_absent`` and excluded
from the rates: ``hndl_capture`` against a PQ/hybrid key exchange (nothing to decrypt later), ``pq_strip``
without a PQ key share (session already classical) and any attack the simulator refuses at injection
(``cert_spoof`` against an ML-DSA certificate). The ``kill_chain`` block replays the ICU Q-Day drill of the
web UI (frontend/src/components/drill.ts, same step order) and records the fleet-level trajectory after
every step via ``simulation.fleet.assess_fleet``.

Everything is synthetic: the fleet, the telemetry and the attack effects are modelled by the simulator;
detections are configuration and telemetry-rule checks; "blocked" reflects the simulator's mitigation
model, not a real adversary. The output contains no timestamps or random identifiers, so re-running with
the same seeds reproduces the file.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import platform
import statistics
import sys
from collections import Counter
from collections.abc import Iterable, Sequence
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

from safeguard_pq import __version__  # noqa: E402
from safeguard_pq.config import Settings  # noqa: E402
from safeguard_pq.knowledge import pqc_catalog as pq  # noqa: E402
from safeguard_pq.orchestrator import AssessmentPipeline  # noqa: E402
from safeguard_pq.simulation import Simulation, SimulationError  # noqa: E402
from safeguard_pq.simulation import catalog as cat  # noqa: E402
from safeguard_pq.simulation.fleet import assess_fleet  # noqa: E402

STATUS_RANK = {"SAFE": 0, "AT_RISK": 1, "UNSAFE": 2}
TICKS_BETWEEN_PHASES = 2  # simulator ticks (20 telemetry rows each) between inject / mitigate and the reassessment
BUDGET_USD, MAX_DOWNTIME_HRS = 100_000, 40

# Mirrors frontend/src/components/drill.ts (DRILL / DRILL_TEMPLATE): same devices, attacks, mitigations and order.
# The UI runs: select -> set Q-Day assumptions -> inject(s) -> mitigate(s) -> assess, per step. Keep in sync by hand.
DRILL_TEMPLATE = "hospital_ward"
DRILL_DEVICE = "ECG-ICU-007"  # the device the UI drill hands to the agents in its Detect / Verify steps
DRILL_STEPS: list[dict[str, Any]] = [
    {"id": "baseline", "stage": "Baseline", "actor": "analyst", "select": "PUMP-ICU-A12",
     "qday": {"migration_years": 5, "years_to_crqc": 10}},
    {"id": "capture", "stage": "Record now", "actor": "adversary", "inject": [("PUMP-ICU-A12", "hndl_capture")]},
    {"id": "weaken", "stage": "Weaken", "actor": "adversary", "inject": [("PACS-GW-01", "pq_strip")], "select": "PACS-GW-01"},
    {"id": "qday", "stage": "Q-Day", "actor": "adversary", "qday": {"migration_years": 5, "years_to_crqc": 6},
     "inject": [("ECG-ICU-007", "cert_spoof")], "select": "ECG-ICU-007"},
    {"id": "ai", "stage": "AI misuse", "actor": "adversary", "inject": [("AI-ASSIST-01", "pq_downgrade_prompt")],
     "select": "AI-ASSIST-01"},
    {"id": "detect", "stage": "Detect", "actor": "analyst", "select": DRILL_DEVICE, "assess": DRILL_DEVICE},
    {"id": "respond", "stage": "Respond", "actor": "analyst",
     "mitigate": ["enable_hybrid_mlkem", "pq_certificates", "pq_policy_pinning", "device_reauth", "prompt_firewall"]},
    {"id": "verify", "stage": "Verify", "actor": "analyst", "select": DRILL_DEVICE, "assess": DRILL_DEVICE},
]


def offline_settings() -> Settings:
    return Settings(_env_file=None, llm_provider="none", online_tools_enabled=False)


def make_pipeline(settings: Settings | None = None) -> AssessmentPipeline:
    return AssessmentPipeline(settings or offline_settings())


async def assess_device(sim: Simulation, device_id: str, pipeline: AssessmentPipeline) -> dict[str, Any]:
    req = sim.to_request(device_id)
    req.options.llm_report = False
    res = await pipeline.run(req)
    live = sim.live_status(sim.device(device_id))
    return {
        "status": res.environment_status, "pq_risk_score": res.pq_risk_score, "verdict": res.verdict,
        "pq_readiness": res.pq_posture.get("readiness"),
        "tippss_min": min(v["score"] for v in res.tippss_scores.values()),
        "findings_count": res.findings_count, "live_risk": live["risk"], "live_status": live["status"],
        "types": {(f.agent, f.type) for f in res.findings},
    }


def _snapshot(a: dict[str, Any]) -> dict[str, Any]:
    keys = ("status", "pq_risk_score", "pq_readiness", "tippss_min", "findings_count", "live_risk")
    return {k: a[k] for k in keys}


def _tagged(types: Iterable[tuple[str, str]]) -> list[str]:
    return [f"{agent}:{ftype}" for agent, ftype in sorted(types)]


def precondition_gap(sim: Simulation, device_id: str, attack_id: str) -> str | None:
    """Reason why the attack cannot have an effect on this device, or None when it is exploitable."""
    d = sim.device(device_id)
    kex = d.tls.get("key_exchange")
    if attack_id == "hndl_capture" and pq.is_pq_safe(kex):
        return f"key exchange {kex} is PQ-safe: recorded sessions cannot be decrypted later"
    if attack_id == "pq_strip" and not pq.is_pq_safe(kex):
        return f"no PQ key share to strip: key exchange {kex} is already classical"
    return None


def applicable_devices(template: cat.FleetTemplate, attack: cat.Attack) -> list[str]:
    return [did for did, kind, _, _ in template.devices if not attack.requires_ai or cat.PROFILES[kind].has_ai]


async def run_one(seed: int, device_id: str, attack_id: str, template: str = "hospital_ward",
                  pipeline: AssessmentPipeline | None = None) -> dict[str, Any]:
    """Baseline -> attack -> defence -> re-injection for one (seed, device, attack) on a fresh simulation."""
    pipeline = pipeline or make_pipeline()
    attack = cat.ATTACKS[attack_id]
    sim = Simulation(template=template, seed=seed)
    base = await assess_device(sim, device_id, pipeline)

    gap = precondition_gap(sim, device_id, attack_id)
    ev = sim.inject(device_id, attack_id)
    if ev.get("blocked"):
        gap = gap or f"blocked at injection: {ev['message']}"
    for _ in range(TICKS_BETWEEN_PHASES):
        sim.step()
    after = await assess_device(sim, device_id, pipeline)
    new_types = sorted(after["types"] - base["types"])
    detected = any(agent in attack.detected_by for agent, _ in new_types)
    flagged_after = any(agent in attack.detected_by for agent, _ in after["types"])

    applied: list[str] = []
    skipped: list[dict[str, str]] = []
    for m in attack.blocked_by:
        try:
            sim.mitigate(device_id, m)
            applied.append(m)
        except SimulationError as exc:
            skipped.append({"mitigation": m, "reason": str(exc)})
    for _ in range(TICKS_BETWEEN_PHASES):
        sim.step()
    post = await assess_device(sim, device_id, pipeline)

    d = sim.device(device_id)
    attack_active = attack_id in d.active_attacks
    if attack_id == "hndl_capture":
        blocked = bool(pq.is_pq_safe(d.tls.get("key_exchange")))
        reinjection = ("hndl_capture is passive and is never refused by the simulator; blocked := key exchange "
                       f"PQ-safe after mitigation ({d.tls.get('key_exchange')})")
    else:
        ev2 = sim.inject(device_id, attack_id)
        blocked = bool(ev2.get("blocked"))
        reinjection = ev2["message"]
    exploitable = gap is None
    return {
        "seed": seed, "device": device_id, "device_kind": d.kind, "attack": attack_id,
        "outcome": "exploitable" if exploitable else "preconditions_absent", "precondition_note": gap,
        "injection_event": ev["message"],
        "baseline": _snapshot(base), "after_attack": _snapshot(after), "after_mitigation": _snapshot(post),
        "delta_pq_risk_score": after["pq_risk_score"] - base["pq_risk_score"],
        "delta_tippss_min": after["tippss_min"] - base["tippss_min"],
        "delta_live_risk": after["live_risk"] - base["live_risk"],
        "status_worsened": STATUS_RANK[after["status"]] > STATUS_RANK[base["status"]],
        "new_finding_types": _tagged(new_types),
        "detected": detected,
        "flagged_after_attack": flagged_after,
        "attack_succeeded_undetected": exploitable and not detected,
        "mitigations_applied": applied, "mitigations_skipped": skipped,
        "finding_types_removed_by_mitigation": _tagged(after["types"] - post["types"]),
        "mitigation_restored_status": STATUS_RANK[post["status"]] <= STATUS_RANK[base["status"]],
        "mitigation_restored_score": post["pq_risk_score"] <= base["pq_risk_score"],
        "attack_active_after_mitigation": attack_active,
        "reinjection_blocked": blocked, "reinjection_event": reinjection,
    }


# ----------------------------------------------------------------------------- aggregation


def _rate(num: int, den: int) -> float | None:
    return round(num / den, 4) if den else None


def _mean(values: Sequence[float]) -> float | None:
    return round(statistics.fmean(values), 3) if values else None


def aggregate_by_attack(runs: Sequence[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for attack_id in cat.ATTACKS:
        rs = [r for r in runs if r["attack"] == attack_id]
        if not rs:
            continue
        ex = [r for r in rs if r["outcome"] == "exploitable"]
        a = cat.ATTACKS[attack_id]
        out[attack_id] = {
            "label": a.label, "layer": a.layer, "detected_by": list(a.detected_by), "blocked_by": list(a.blocked_by),
            "runs": len(rs), "devices": sorted({r["device"] for r in rs}),
            "exploitable_runs": len(ex), "preconditions_absent_runs": len(rs) - len(ex),
            "preconditions_absent_devices": sorted({r["device"] for r in rs if r["outcome"] != "exploitable"}),
            "detection_rate": _rate(sum(r["detected"] for r in ex), len(ex)),
            "flagged_after_attack_rate": _rate(sum(r["flagged_after_attack"] for r in ex), len(ex)),
            "undetected_exploitable_runs": sum(r["attack_succeeded_undetected"] for r in ex),
            "undetected_devices": sorted({r["device"] for r in ex if not r["detected"]}),
            "mean_delta_pq_risk_score": _mean([r["delta_pq_risk_score"] for r in ex]),
            "mean_delta_tippss_min": _mean([r["delta_tippss_min"] for r in ex]),
            "mean_delta_live_risk": _mean([r["delta_live_risk"] for r in ex]),
            "status_worsened_rate": _rate(sum(r["status_worsened"] for r in ex), len(ex)),
            "baseline_status_counts": dict(sorted(Counter(r["baseline"]["status"] for r in ex).items())),
            "after_attack_status_counts": dict(sorted(Counter(r["after_attack"]["status"] for r in ex).items())),
            "after_mitigation_status_counts": dict(sorted(Counter(r["after_mitigation"]["status"] for r in ex).items())),
            "mitigation_restored_status_rate": _rate(sum(r["mitigation_restored_status"] for r in ex), len(ex)),
            "mitigation_restored_score_rate": _rate(sum(r["mitigation_restored_score"] for r in ex), len(ex)),
            "reinjection_blocked_rate": _rate(sum(r["reinjection_blocked"] for r in ex), len(ex)),
            "reinjection_not_blocked_devices": sorted({r["device"] for r in ex if not r["reinjection_blocked"]}),
            "attack_active_after_mitigation_runs": sum(r["attack_active_after_mitigation"] for r in ex),
            "new_finding_types": sorted({t for r in ex for t in r["new_finding_types"]}),
            "mitigations_skipped": sorted({s["mitigation"] for r in rs for s in r["mitigations_skipped"]}),
        }
    return out


def aggregate_by_attack_device(runs: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for key in dict.fromkeys((r["attack"], r["device"]) for r in runs):
        rs = [r for r in runs if (r["attack"], r["device"]) == key]
        ex = [r for r in rs if r["outcome"] == "exploitable"]
        rows.append({
            "attack": key[0], "device": key[1], "device_kind": rs[0]["device_kind"], "seeds": [r["seed"] for r in rs],
            "outcome": rs[0]["outcome"], "precondition_note": rs[0]["precondition_note"],
            "exploitable_runs": len(ex), "detected_runs": sum(r["detected"] for r in ex),
            "baseline_status": Counter(r["baseline"]["status"] for r in rs).most_common(1)[0][0],
            "after_attack_status": Counter(r["after_attack"]["status"] for r in rs).most_common(1)[0][0],
            "after_mitigation_status": Counter(r["after_mitigation"]["status"] for r in rs).most_common(1)[0][0],
            "mean_delta_pq_risk_score": _mean([r["delta_pq_risk_score"] for r in ex]),
            "mean_delta_tippss_min": _mean([r["delta_tippss_min"] for r in ex]),
            "mean_delta_live_risk": _mean([r["delta_live_risk"] for r in ex]),
            "mitigation_restored_status_runs": sum(r["mitigation_restored_status"] for r in ex),
            "reinjection_blocked_runs": sum(r["reinjection_blocked"] for r in ex),
            "new_finding_types": sorted({t for r in ex for t in r["new_finding_types"]}),
            "consistent_across_seeds": len({(r["detected"], r["after_attack"]["status"], r["reinjection_blocked"],
                                             r["delta_pq_risk_score"]) for r in rs}) == 1,
        })
    return rows


# ----------------------------------------------------------------------------- kill chain (UI drill replay)


async def kill_chain(seed: int, pipeline: AssessmentPipeline, template: str = DRILL_TEMPLATE) -> dict[str, Any]:
    sim = Simulation(template=template, seed=seed)
    steps = []
    for st in DRILL_STEPS:
        actions: list[str] = []
        events: list[str] = []
        if "qday" in st:
            q = st["qday"]
            ev = sim.set_assumptions(q["migration_years"], q["years_to_crqc"])
            actions.append(f"set_assumptions(migration_years={q['migration_years']}, years_to_crqc={q['years_to_crqc']})")
            events.append(ev["message"])
        for device_id, attack_id in st.get("inject", []):
            ev = sim.inject(device_id, attack_id)
            actions.append(f"inject {attack_id} on {device_id}")
            events.append(ev["message"])
        for m in st.get("mitigate", []):
            evs = sim.mitigate(None, m)
            actions.append(f"mitigate {m} fleet-wide ({len(evs)} device(s))")
            events.extend(e["message"] for e in evs)
        if "assess" in st:
            actions.append(f"assess {st['assess']}")
        for _ in range(TICKS_BETWEEN_PHASES):
            sim.step()
        fleet = await assess_fleet(sim, pipeline, BUDGET_USD, MAX_DOWNTIME_HRS)
        drill = await assess_device(sim, DRILL_DEVICE, pipeline)
        steps.append({
            "id": st["id"], "stage": st["stage"], "actor": st["actor"], "actions": actions, "events": events,
            "fleet": {"environment_status": fleet["environment_status"], "counts": fleet["counts"],
                      "mean_pq_risk_score": fleet["mean_pq_risk_score"], "fleet_pillars": fleet["fleet_pillars"]},
            "devices": {d["device_id"]: {"status": d["environment_status"], "pq_risk_score": d["pq_risk_score"],
                                         "pq_readiness": d["pq_readiness"], "findings_count": d["findings_count"],
                                         "top_issues": d["top_issues"], "active_attacks": d["active_attacks"]}
                        for d in fleet["devices"]},
            "drill_device": {"id": DRILL_DEVICE, **_snapshot(drill), "finding_types": _tagged(drill["types"])},
        })
    return {"seed": seed, "steps": steps}


def trajectory(chain: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"step": s["id"], "fleet_status": s["fleet"]["environment_status"], "mean_pq_risk_score": s["fleet"]["mean_pq_risk_score"],
             **{k.lower(): v for k, v in s["fleet"]["counts"].items()},
             "drill_device_status": s["drill_device"]["status"], "drill_device_pq_risk_score": s["drill_device"]["pq_risk_score"]}
            for s in chain["steps"]]


# ----------------------------------------------------------------------------- orchestration


async def run_all(seeds: Sequence[int], template_id: str, attack_ids: Sequence[str], device_filter: set[str] | None,
                  skip_kill_chain: bool) -> dict[str, Any]:
    pipeline = make_pipeline()
    template = cat.TEMPLATES[template_id]
    runs: list[dict[str, Any]] = []
    for attack_id in attack_ids:
        attack = cat.ATTACKS[attack_id]
        for device_id in applicable_devices(template, attack):
            if device_filter and device_id not in device_filter:
                continue
            for seed in seeds:
                runs.append(await run_one(seed, device_id, attack_id, template_id, pipeline))

    kill: dict[str, Any] = {}
    if skip_kill_chain:
        kill = {"skipped": "disabled by --skip-kill-chain"}
    elif template_id != DRILL_TEMPLATE:
        kill = {"skipped": f"the UI drill is defined for template '{DRILL_TEMPLATE}' only"}
    else:
        chains = [await kill_chain(seed, pipeline, template_id) for seed in seeds]
        first = chains[0]
        traj = trajectory(first)
        kill = {
            "source": "frontend/src/components/drill.ts (DRILL), replayed with the same device/attack/mitigation order",
            "drill_device": DRILL_DEVICE, "seed": first["seed"], "ticks_between_steps": TICKS_BETWEEN_PHASES,
            "fleet_scoring": "simulation.fleet.assess_fleet (per-device pipeline runs; mean pq_risk_score, worst status, "
                             "min pillar scores)",
            "trajectory": traj,
            "other_seeds_identical_trajectory": {str(c["seed"]): trajectory(c) == traj for c in chains[1:]},
            "steps": first["steps"],
        }

    return {
        "benchmark": f"attack_simulation_{template_id}",
        "software_version": __version__,
        "date": date.today().isoformat(),
        "python": platform.python_version(),
        "seeds": list(seeds),
        "template": template_id,
        "template_label": template.label,
        "devices": [{"id": did, "kind": kind, "zone": zone, "has_ai": cat.PROFILES[kind].has_ai,
                     "key_exchange": cat.PROFILES[kind].tls["key_exchange"],
                     "cert_signature_algo": cat.PROFILES[kind].tls["cert_signature_algo"],
                     "data_lifetime_years": cat.PROFILES[kind].data_lifetime_years} for did, kind, zone, _ in template.devices],
        "attack_filter": list(attack_ids) if len(attack_ids) != len(cat.ATTACKS) else None,
        "device_filter": sorted(device_filter) if device_filter else None,
        "summary": {
            "runs": len(runs),
            "exploitable_runs": sum(r["outcome"] == "exploitable" for r in runs),
            "preconditions_absent_runs": sum(r["outcome"] != "exploitable" for r in runs),
            "detected_exploitable_runs": sum(r["detected"] for r in runs if r["outcome"] == "exploitable"),
            "undetected_exploitable_runs": sum(r["attack_succeeded_undetected"] for r in runs),
            "reinjection_blocked_exploitable_runs": sum(r["reinjection_blocked"] for r in runs if r["outcome"] == "exploitable"),
        },
        "attacks": aggregate_by_attack(runs),
        "attack_device_table": aggregate_by_attack_device(runs),
        "runs": runs,
        "kill_chain": kill,
        "method": {
            "unit": "one fresh Simulation(template, seed) per (seed, device, attack); attacks that require an AI assistant "
                    "run on AI-enabled devices only",
            "assessment": "safeguard_pq.orchestrator.AssessmentPipeline.run(sim.to_request(device)) with llm_report=False, "
                          "llm_provider=none, online tools disabled; S = pq_risk_score (0-100, crypto-only by design), "
                          "status = environment_status (SAFE < AT_RISK < UNSAFE), tippss_min = lowest TIPPSS pillar score, "
                          "live_risk = the simulator's own 0-100 live risk (includes telemetry alerts)",
            "phases": f"baseline -> inject -> {TICKS_BETWEEN_PHASES} ticks -> reassess -> apply every mitigation in "
                      f"Attack.blocked_by -> {TICKS_BETWEEN_PHASES} ticks -> reassess -> re-inject the same attack",
            "detected": "at least one (agent, finding type) pair produced after the attack by an agent in Attack.detected_by "
                        "that was absent at baseline; flagged_after_attack also accepts findings already present at baseline",
            "preconditions_absent": "hndl_capture on a PQ/hybrid key exchange; pq_strip without a PQ key share; any injection "
                                    "the simulator refuses (e.g. cert_spoof on ML-DSA certificates); excluded from all rates",
            "reinjection_blocked": "the simulator refused the second injection (a mitigation in blocked_by is present); "
                                   "hndl_capture: key exchange PQ-safe after mitigation",
            "status_worsened": "STATUS_RANK[status after attack] > STATUS_RANK[baseline status]",
            "mitigation_restored_status": "STATUS_RANK[status after mitigation] <= STATUS_RANK[baseline status]",
            "kill_chain": "replay of the UI drill (frontend/src/components/drill.ts) with fleet-level assessment after each step",
            "determinism": "no timestamps or random identifiers are recorded; seeds fix telemetry and the optimizer",
        },
        "caveat": (
            "Synthetic simulator (safeguard_pq.simulation): the fleet, telemetry, attack effects and mitigations are modelled, "
            "not observed. Detections are configuration and telemetry-rule checks performed by the assessment agents, so "
            "detection rates measure whether the agents react to the simulator's modelled effects, not detection of real "
            "attacks. 'Blocked' reflects the simulator's mitigation model (a mitigation listed in the attack's blocked_by "
            "prevents re-injection), not the behaviour of a real adversary. pq_risk_score is crypto-only by design, so "
            "network, AI and identity attacks mostly change environment status, TIPPSS pillars and the live risk rather "
            "than the PQ score; devices that are UNSAFE at baseline because of classical crypto cannot get a worse status."
        ),
    }


def print_summary(result: dict[str, Any]) -> None:
    s = result["summary"]
    print(f"\n{result['template_label']}: {s['runs']} runs ({s['exploitable_runs']} exploitable, "
          f"{s['preconditions_absent_runs']} preconditions absent); detected {s['detected_exploitable_runs']}, "
          f"undetected {s['undetected_exploitable_runs']}, re-injection blocked {s['reinjection_blocked_exploitable_runs']}")
    print(f"{'attack':20s} {'expl':>4s} {'n/a':>4s} {'detect':>7s} {'dS':>6s} {'dTIPPSS':>8s} {'worse':>6s} {'restore':>8s} "
          f"{'blocked':>8s}  undetected devices")
    for aid, a in result["attacks"].items():
        print(f"{aid:20s} {a['exploitable_runs']:4d} {a['preconditions_absent_runs']:4d} {_f(a['detection_rate']):>7s} "
              f"{_f(a['mean_delta_pq_risk_score']):>6s} {_f(a['mean_delta_tippss_min']):>8s} {_f(a['status_worsened_rate']):>6s} "
              f"{_f(a['mitigation_restored_status_rate']):>8s} {_f(a['reinjection_blocked_rate']):>8s}  {a['undetected_devices']}")
    kc = result["kill_chain"]
    if "trajectory" in kc:
        print(f"\nkill chain (seed {kc['seed']}): " + " -> ".join(
            f"{t['step']}:{t['fleet_status']}/{t['mean_pq_risk_score']}" for t in kc["trajectory"]))


def _f(v: float | None) -> str:
    return "n/a" if v is None else f"{v:g}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--template", default="hospital_ward")
    ap.add_argument("--seeds", default="7,11,23", help="comma-separated simulator seeds")
    ap.add_argument("--attacks", default=None, help="comma-separated attack ids (default: every attack in the catalogue)")
    ap.add_argument("--devices", default=None, help="comma-separated device ids (default: every applicable device)")
    ap.add_argument("--skip-kill-chain", action="store_true")
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "results" / "attack_simulation.json")
    args = ap.parse_args(argv)

    if args.template not in cat.TEMPLATES:
        print(f"unknown template '{args.template}'; choose from {sorted(cat.TEMPLATES)}", file=sys.stderr)
        return 2
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    attack_ids = [a.strip() for a in args.attacks.split(",")] if args.attacks else list(cat.ATTACKS)
    unknown = [a for a in attack_ids if a not in cat.ATTACKS]
    if unknown or not seeds:
        print(f"unknown attack(s) {unknown} or no seeds; attacks: {sorted(cat.ATTACKS)}", file=sys.stderr)
        return 2
    device_filter = {d.strip() for d in args.devices.split(",")} if args.devices else None
    template_devices = {did for did, _, _, _ in cat.TEMPLATES[args.template].devices}
    if device_filter and not device_filter <= template_devices:
        print(f"unknown device(s) {sorted(device_filter - template_devices)}; devices: {sorted(template_devices)}", file=sys.stderr)
        return 2

    result = asyncio.run(run_all(seeds, args.template, attack_ids, device_filter, args.skip_kill_chain))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print_summary(result)
    print(f"\nWritten: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
