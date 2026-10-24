"""Discrete-time IoT fleet simulator with attack injection and mitigations.

Each tick every device emits a batch of synthetic flow-feature rows (CICIoMT
column names) into a rolling window. Injected attacks change telemetry,
crypto configuration, device identity, logs or AI prompts; mitigations harden
the configuration and block matching attacks. Any device can be handed to the
multi-agent pipeline at any time via :meth:`Simulation.to_request`.

Data sources:
* ``synthetic`` (default): seeded random generator, no files needed.
* ``replay``: rows streamed from user-downloaded CICIoMT2024 CSV files in
  ``REPLAY_DATA_DIR`` (not redistributed with this project).
"""

from __future__ import annotations

import csv
import random
import time
import uuid
import zlib
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..domain.models import AssessmentRequest
from ..knowledge import patterns, traffic_rules
from ..knowledge import pqc_catalog as pq
from ..knowledge.redaction import redact
from . import catalog as cat
from .fakes import fake_aws_key_id, fake_stripe_key

WINDOW_ROWS = 100
ROWS_PER_TICK = 20
PREFILL_ROWS = 60


class SimulationError(Exception):
    pass


@dataclass
class Device:
    id: str
    kind: str
    label: str
    zone: str
    position: tuple[float, float]
    domain: str
    has_ai: bool
    shape: str
    base_rate: float
    tls: dict[str, Any]
    data_lifetime_years: float
    prompts: list[str]
    cert_present: bool = True
    auth_status: str = "passed"
    failed_login_count: int = 0
    debug_log: str = ""
    active_attacks: list[str] = field(default_factory=list)
    mitigations: list[str] = field(default_factory=list)
    snapshots: dict[str, dict[str, Any]] = field(default_factory=dict)
    window: deque = field(default_factory=lambda: deque(maxlen=WINDOW_ROWS))
    last_assessment: dict[str, Any] | None = None

    @property
    def network_attacks(self) -> list[str]:
        return [a for a in self.active_attacks if cat.ATTACKS[a].traffic is not None]


class ReplaySource:
    def __init__(self, directory: str | Path, max_rows: int = 3000) -> None:
        self.dir = Path(directory)
        self.max_rows = max_rows
        self._cache: dict[str, list[dict[str, str]]] = {}
        self._cursor: dict[tuple[str, str], int] = {}

    def available(self, regime: str) -> bool:
        return self._file(regime) is not None

    def _file(self, regime: str) -> Path | None:
        token = cat.REPLAY_FILES.get(regime)
        if not token or not self.dir.is_dir():
            return None
        return next((p for p in sorted(self.dir.glob("*.csv")) if token.lower() in p.name.lower()), None)

    def rows(self, device_id: str, regime: str, n: int) -> list[dict[str, str]] | None:
        path = self._file(regime)
        if path is None:
            return None
        if regime not in self._cache:
            with path.open(newline="", encoding="utf-8", errors="replace") as fh:
                reader = csv.DictReader(fh)
                self._cache[regime] = [r for _, r in zip(range(self.max_rows), reader, strict=False)]
        data = self._cache[regime]
        if not data:
            return None
        key = (device_id, regime)
        start = self._cursor.get(key, zlib.crc32(device_id.encode()) % len(data))
        out = [data[(start + i) % len(data)] for i in range(n)]
        self._cursor[key] = (start + n) % len(data)
        return out


class Simulation:
    def __init__(self, template: str = "hospital_ward", seed: int = 7, data_source: str = "synthetic",
                 replay_dir: str | None = None) -> None:
        if template not in cat.TEMPLATES:
            raise SimulationError(f"unknown template '{template}'")
        if data_source not in ("synthetic", "replay"):
            raise SimulationError("data_source must be 'synthetic' or 'replay'")
        self.id = uuid.uuid4().hex[:10]
        self.template = cat.TEMPLATES[template]
        self.seed = seed
        self.rng = random.Random(seed)
        self.tick = 0
        self.created_at = datetime.now(UTC).isoformat()
        self.last_step = 0.0
        self.events: deque[dict[str, Any]] = deque(maxlen=300)
        self._event_seq = 0
        self.data_source = data_source
        self.replay = ReplaySource(replay_dir) if data_source == "replay" and replay_dir else None
        if data_source == "replay" and self.replay is None:
            raise SimulationError("replay data source requires REPLAY_DATA_DIR to be configured")
        self.assumptions: dict[str, float] = {"migration_years": 5.0, "years_to_crqc": 10.0}
        self.devices: OrderedDict[str, Device] = OrderedDict()
        for did, kind, zone, pos in self.template.devices:
            p = cat.PROFILES[kind]
            self.devices[did] = Device(
                id=did, kind=kind, label=p.label, zone=zone, position=pos, domain=p.domain, has_ai=p.has_ai, shape=p.shape,
                base_rate=p.base_rate, tls=dict(p.tls), data_lifetime_years=p.data_lifetime_years, prompts=list(p.prompts),
            )
        for d in self.devices.values():
            self._fill(d, PREFILL_ROWS)
        self._log("info", None, f"Simulation started: {self.template.label} ({len(self.devices)} devices, {data_source} data).")

    # ------------------------------------------------------------------ telemetry

    def _gen_row(self, d: Device, params: dict[str, Any]) -> dict[str, float]:
        r = self.rng
        tcp = 1.0 if r.random() < params["tcp"] else 0.0
        flag = lambda p: 1.0 if (tcp and r.random() < p) else 0.0  # noqa: E731
        size_mu, size_sd = params["size"]
        hdr_mu, hdr_sd = params["header"]
        rate = params.get("rate") or d.base_rate
        return {
            "syn_flag_number": flag(params["syn"]), "ack_flag_number": flag(params["ack"]),
            "rst_flag_number": flag(params["rst"]), "fin_flag_number": flag(params["fin"]),
            "TCP": tcp, "UDP": 1.0 - tcp,
            "Rate": max(0.0, r.lognormvariate(0, 0.35) * rate),
            "Tot size": max(40.0, r.gauss(size_mu, size_sd)),
            "Header_Length": max(20.0, r.gauss(hdr_mu, hdr_sd)),
        }

    def _fill(self, d: Device, n: int) -> None:
        net = d.network_attacks
        regime = self.rng.choice(net) if net else "benign"
        if self.replay:
            rows = self.replay.rows(d.id, regime, n)
            if rows is not None:
                d.window.extend(rows)
                return
        for _ in range(n):
            a = self.rng.choice(net) if net else None
            params = cat.ATTACKS[a].traffic if a else cat.BENIGN_TRAFFIC
            d.window.append(self._gen_row(d, params))  # type: ignore[arg-type]

    def step(self) -> None:
        self.tick += 1
        self.last_step = time.monotonic()
        for d in self.devices.values():
            self._fill(d, ROWS_PER_TICK)

    # ------------------------------------------------------------------ attacks & mitigations

    def device(self, device_id: str) -> Device:
        try:
            return self.devices[device_id]
        except KeyError as exc:
            raise SimulationError(f"unknown device '{device_id}'") from exc

    def inject(self, device_id: str, attack_id: str) -> dict[str, Any]:
        d = self.device(device_id)
        if attack_id not in cat.ATTACKS:
            raise SimulationError(f"unknown attack '{attack_id}'")
        a = cat.ATTACKS[attack_id]
        if a.requires_ai and not d.has_ai:
            raise SimulationError(f"{a.label} requires an AI-enabled device; {d.label} has no AI assistant")
        if attack_id in d.active_attacks:
            return self._log("warning", d.id, f"{a.label} already active on {d.id}.")
        blockers = [m for m in a.blocked_by if m in d.mitigations and attack_id != "hndl_capture"]
        if blockers:
            return self._log("success", d.id, f"Blocked: {a.label} on {d.id} prevented by "
                                              f"{', '.join(cat.MITIGATIONS[m].label for m in blockers)}.", attack=attack_id, blocked=True)

        if attack_id == "cert_spoof" and pq.is_pq_safe(d.tls.get("cert_signature_algo")):
            return self._log("success", d.id, f"Blocked: {a.label} on {d.id} — certificate uses "
                                              f"{d.tls.get('cert_signature_algo')}, which Shor's algorithm cannot break.",
                             attack=attack_id, blocked=True)
        snap: dict[str, Any] = {}

        def setf(key: str, value: Any) -> None:
            if key not in snap:
                snap[key] = (d.tls.get(key) if key in d.tls or key in pq_fields else getattr(d, key))
            if key in pq_fields:
                d.tls[key] = value
            else:
                setattr(d, key, value)

        pq_fields = {"tls_version", "key_exchange", "cert_signature_algo", "cert_key_algo", "symmetric_cipher", "hash"}
        note = ""
        if attack_id == "tls_downgrade":
            setf("tls_version", "TLS1.0"), setf("key_exchange", "RSA"), setf("hash", "SHA-1")
        elif attack_id == "pq_strip":
            if pq.is_pq_safe(d.tls.get("key_exchange")):
                setf("key_exchange", "ECDHE-P256")
            else:
                note = " (no PQ share present — session was already classical)"
        elif attack_id == "hndl_capture":
            setf("data_lifetime_years", max(d.data_lifetime_years, 25))
            if pq.is_pq_safe(d.tls.get("key_exchange")):
                note = " — captured sessions are protected by ML-KEM key establishment"
        elif attack_id == "cert_spoof":
            setf("cert_signature_algo", "ECDSA-P256"), setf("cert_present", False), setf("auth_status", "failed")
            setf("failed_login_count", d.failed_login_count + 6)
        elif attack_id == "secret_leak":
            setf("debug_log", f"{d.debug_log} upload ok key={fake_stripe_key()} aws_key_id={fake_aws_key_id()}".strip())
        elif attack_id in cat.ATTACK_PROMPTS:
            setf("prompts", [*d.prompts, cat.ATTACK_PROMPTS[attack_id]])
        elif attack_id == "arp_spoofing":
            setf("failed_login_count", d.failed_login_count + 3)

        d.snapshots[attack_id] = snap
        d.active_attacks.append(attack_id)
        if a.traffic is not None:
            d.window.clear()
            self._fill(d, PREFILL_ROWS)
        return self._log("danger", d.id, f"Injected {a.label} on {d.id}{note}.", attack=attack_id)

    def clear_attack(self, device_id: str, attack_id: str) -> dict[str, Any]:
        d = self.device(device_id)
        if attack_id not in d.active_attacks:
            raise SimulationError(f"attack '{attack_id}' is not active on {device_id}")
        self._revert(d, attack_id)
        return self._log("info", d.id, f"Cleared {cat.ATTACKS[attack_id].label} on {d.id}.", attack=attack_id)

    def _revert(self, d: Device, attack_id: str) -> None:
        snap = d.snapshots.pop(attack_id, {})
        for key, old in snap.items():
            if key in d.tls or key in ("tls_version", "key_exchange", "cert_signature_algo", "cert_key_algo", "symmetric_cipher", "hash"):
                d.tls[key] = old
            elif key == "prompts":
                injected = cat.ATTACK_PROMPTS.get(attack_id)
                d.prompts = [p for p in d.prompts if p != injected]
            else:
                setattr(d, key, old)
        d.active_attacks.remove(attack_id)
        if cat.ATTACKS[attack_id].traffic is not None:
            d.window.clear()
            self._fill(d, PREFILL_ROWS)

    def mitigate(self, device_id: str | None, mitigation_id: str) -> list[dict[str, Any]]:
        if mitigation_id not in cat.MITIGATIONS:
            raise SimulationError(f"unknown mitigation '{mitigation_id}'")
        targets = [self.device(device_id)] if device_id else list(self.devices.values())
        m = cat.MITIGATIONS[mitigation_id]
        events = []
        for d in targets:
            if m.layer == "ai" and not d.has_ai:
                if device_id:
                    raise SimulationError(f"{m.label} applies to AI-enabled devices only")
                continue
            if mitigation_id in d.mitigations:
                continue
            cleared = [a for a in d.active_attacks if a != "hndl_capture" and (
                mitigation_id in cat.ATTACKS[a].blocked_by or (mitigation_id == "device_reauth" and a == "cert_spoof"))]
            for a in cleared:
                self._revert(d, a)
            d.tls.update(m.config)
            for a in list(d.active_attacks):  # config overrides drop stale attack snapshots
                d.snapshots.get(a, {}).update({k: v for k, v in m.config.items() if k in d.snapshots.get(a, {})})
            if mitigation_id == "device_reauth":
                d.auth_status, d.cert_present, d.failed_login_count = "passed", True, 0
            elif mitigation_id == "pq_certificates":
                d.cert_present = True
            elif mitigation_id == "secret_rotation":
                d.debug_log = ""
            elif mitigation_id == "phi_redaction":
                d.prompts = [redact(p) for p in d.prompts]
            elif mitigation_id == "prompt_firewall":
                d.prompts = [p for p in d.prompts if not any(r.pattern.search(p) for r in patterns.INJECTION_RULES)]
            elif mitigation_id == "clinician_approval_gate":
                d.prompts = [p for p in d.prompts if not any(r.pattern.search(p) for r in patterns.UNSAFE_RULES)]
            d.mitigations.append(mitigation_id)
            suffix = f"; cleared {', '.join(cat.ATTACKS[a].label for a in cleared)}" if cleared else ""
            events.append(self._log("success", d.id, f"Applied {m.label} on {d.id}{suffix}.", mitigation=mitigation_id))
        return events

    def set_assumptions(self, migration_years: float, years_to_crqc: float) -> dict[str, Any]:
        if not (0 <= migration_years <= 50 and 0 <= years_to_crqc <= 100):
            raise SimulationError("migration_years must be 0-50 and years_to_crqc 0-100")
        self.assumptions = {"migration_years": float(migration_years), "years_to_crqc": float(years_to_crqc)}
        return self._log("info", None, f"Q-Day assumptions set: CRQC in {years_to_crqc:g} years, migration takes {migration_years:g} years.")

    def hndl_exposed(self, d: Device) -> bool:
        """Mosca: confidentiality at risk if data lifetime + migration time > years to CRQC and key exchange is classical."""
        if pq.is_pq_safe(d.tls.get("key_exchange")):
            return False
        return d.data_lifetime_years + self.assumptions["migration_years"] > self.assumptions["years_to_crqc"]

    # ------------------------------------------------------------------ views

    def live_status(self, d: Device) -> dict[str, Any]:
        feats = traffic_rules.features_from_rows(d.window) if len(d.window) >= 30 else {}
        alerts = [r["type"] for r in traffic_rules.evaluate(feats) if r["hit"]] if feats else []
        text = "\n".join([*d.prompts, d.debug_log])
        for rules in (patterns.INJECTION_RULES, patterns.PHI_RULES, patterns.UNSAFE_RULES, patterns.SECRET_RULES):
            alerts += [r.type for r in rules if r.pattern.search(text)]
        if d.auth_status == "failed":
            alerts.append("authentication_failed")
        kex_safe = pq.is_pq_safe(d.tls.get("key_exchange"))
        sig_safe = pq.is_pq_safe(d.tls.get("cert_signature_algo"))
        readiness = "PQ-ready" if kex_safe and sig_safe else "Partial" if kex_safe or sig_safe else "Vulnerable"
        deprecated = pq.classify(d.tls.get("tls_version")).quantum_status == pq.DEPRECATED
        if alerts or deprecated:
            status = "alert"
        elif not kex_safe or not d.cert_present or "hndl_capture" in d.active_attacks and not kex_safe:
            status = "warning"
        else:
            status = "ok"
        hndl = self.hndl_exposed(d)
        risk = {"PQ-ready": 0, "Partial": 15, "Vulnerable": 30}[readiness] + (25 if hndl else 0) + (20 if deprecated else 0)
        risk = min(100, risk + 15 * len(set(alerts)) + (10 if not d.cert_present else 0))
        return {
            "status": status, "alerts": sorted(set(alerts)), "pq_readiness": readiness, "hndl_exposed": hndl, "risk": risk, "kex_pq": kex_safe, "sig_pq": sig_safe,
            "features": {k: round(v, 4) for k, v in feats.items() if k in ("syn_ratio", "rst_ratio", "udp_ratio", "rate_mean", "tot_size_mean")},
        }

    def device_view(self, d: Device) -> dict[str, Any]:
        return {
            "id": d.id, "kind": d.kind, "label": d.label, "zone": d.zone, "position": list(d.position), "domain": d.domain,
            "has_ai": d.has_ai, "shape": d.shape, "tls": d.tls | {"data_lifetime_years": d.data_lifetime_years},
            "cert_present": d.cert_present, "auth_status": d.auth_status, "failed_login_count": d.failed_login_count,
            "active_attacks": list(d.active_attacks), "mitigations": list(d.mitigations),
            "prompt_count": len(d.prompts), "live": self.live_status(d), "last_assessment": d.last_assessment,
        }

    def snapshot(self, since_event: int = 0) -> dict[str, Any]:
        return {
            "id": self.id, "template": self.template.id, "template_label": self.template.label, "domain": self.template.domain,
            "seed": self.seed, "tick": self.tick, "data_source": self.data_source, "created_at": self.created_at,
            "assumptions": dict(self.assumptions),
            "devices": [self.device_view(d) for d in self.devices.values()],
            "events": [e for e in self.events if e["seq"] > since_event],
        }

    def to_request(self, device_id: str, budget_usd: float = 100_000, max_downtime_hrs: float = 40) -> AssessmentRequest:
        d = self.device(device_id)
        return AssessmentRequest.model_validate({
            "system_id": d.id,
            "domain": d.domain,
            "scenario_summary": f"{d.label} in {d.zone} — simulation {self.id}, tick {self.tick}, {self.data_source} telemetry.",
            "tls_config": d.tls | {"data_lifetime_years": d.data_lifetime_years},
            "iot_traffic": {"dataset_family": "simulation", "source": self.data_source, "window": list(d.window),
                            "rows_sampled": len(d.window)},
            "ai_prompt_logs": list(d.prompts) if d.has_ai else None,
            "device_logs": [{"device_id": d.id, "cert_present": d.cert_present, "auth_status": d.auth_status,
                             "failed_login_count": d.failed_login_count, **({"debug_log": d.debug_log} if d.debug_log else {})}],
            "constraints": {"budget_usd": budget_usd, "max_downtime_hrs": max_downtime_hrs},
            "assumptions": dict(self.assumptions),
            "seed": self.seed,
        })

    def _log(self, level: str, device_id: str | None, message: str, **extra: Any) -> dict[str, Any]:
        self._event_seq += 1
        e = {"seq": self._event_seq, "tick": self.tick, "ts": datetime.now(UTC).isoformat(), "level": level,
             "device_id": device_id, "message": message, **extra}
        self.events.append(e)
        return e


class SimulationStore:
    def __init__(self, capacity: int = 20) -> None:
        self.capacity = capacity
        self._items: OrderedDict[str, Simulation] = OrderedDict()

    def add(self, sim: Simulation) -> Simulation:
        self._items[sim.id] = sim
        while len(self._items) > self.capacity:
            self._items.popitem(last=False)
        return sim

    def get(self, sim_id: str) -> Simulation:
        try:
            return self._items[sim_id]
        except KeyError as exc:
            raise SimulationError(f"unknown simulation '{sim_id}'") from exc


def catalog_view() -> dict[str, Any]:
    return {
        "templates": [{"id": t.id, "label": t.label, "domain": t.domain, "device_count": len(t.devices)} for t in cat.TEMPLATES.values()],
        "attacks": [{"id": a.id, "label": a.label, "layer": a.layer, "description": a.description,
                     "surface": cat.SURFACES.get(a.id, ""), "detected_by": list(a.detected_by),
                     "blocked_by": list(a.blocked_by), "requires_ai": a.requires_ai} for a in cat.ATTACKS.values()],
        "mitigations": [{"id": m.id, "label": m.label, "layer": m.layer, "description": m.description} for m in cat.MITIGATIONS.values()],
        "data_sources": ["synthetic", "replay"],
    }
