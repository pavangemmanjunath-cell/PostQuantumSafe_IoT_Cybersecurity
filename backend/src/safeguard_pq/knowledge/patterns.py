"""Detection rule tables used by the privacy, injection, secret and safety agents.

The first entry group of each table reproduces the rules of the v0 prototype
exactly (same regular expressions, severities and TIPPSS mappings) so results
remain comparable. Entries marked ``added_in="0.1.0"`` are new.

These are heuristic pattern rules. They produce false positives and false
negatives and are not a substitute for a DLP or prompt-security product.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    type: str
    pattern: re.Pattern[str]
    severity: str
    description: str
    added_in: str = "0.0"


def _r(p: str, flags: int = 0) -> re.Pattern[str]:
    return re.compile(p, flags)


PHI_RULES: list[Rule] = [
    Rule("medical_record_number", _r(r"\bMRN[:\s-]*\d{4,}", re.I), "high", "Medical record number"),
    Rule("ssn", _r(r"\b\d{3}-\d{2}-\d{4}\b"), "high", "US social security number format"),
    Rule("patient_identifier", _r(r"\bpatient\s+(?:name|id)[:\s]+[A-Z][a-z]+", re.I), "high", "Patient name / id label"),
    Rule("email", _r(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", re.I), "high", "Email address"),
    Rule(
        "sensitive_diagnosis",
        _r(r"\b(?:HIV|AIDS|cancer|psychiatric|substance abuse)\s+(?:diagnosis|status|treatment|history)", re.I),
        "critical",
        "Sensitive diagnosis category",
    ),
]

INJECTION_RULES: list[Rule] = [
    Rule("instruction_override", _r(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)", re.I), "critical", "Instruction override"),
    Rule("role_manipulation", _r(r"(you are now|switch to|enable)\s+(admin|dan|developer|jailbreak)\s*(mode)?", re.I), "critical", "Role / mode manipulation"),
    Rule("system_prompt_extraction", _r(r"(repeat|show|reveal|print)\s+(your|the)\s+(system|initial|original)\s+prompt", re.I), "high", "System prompt extraction"),
    Rule("fake_system_message", _r(r"\[(system|admin|override|approved)[^\]]*\]", re.I), "critical", "Fake system / admin message"),
    Rule("fake_authorization", _r(r"(authentication|consent|hipaa|authorization)\s+(has been|is)\s+(waived|bypassed|completed)", re.I), "critical", "Fabricated authorization claim"),
    # --- added in 0.1.0
    Rule(
        "pq_downgrade_instruction",
        _r(
            r"(disable|turn off|remove|bypass)\s+(the\s+)?(ml-?kem|ml-?dsa|pqc|post[- ]quantum|hybrid)"
            r"|(fall\s*back|downgrade|revert)\s+to\s+(tls\s*1\.[01]|rsa|ecdhe|classical)"
            r"|use\s+(rsa|ecdhe|classical crypto(graphy)?)\s+only",
            re.I,
        ),
        "critical",
        "Instruction to weaken post-quantum protection (crypto downgrade via AI agent)",
        "0.1.0",
    ),
    Rule("delimiter_injection", _r(r"(</?\s*(system|assistant|instructions?)\s*>|###\s*(new\s+)?instructions?\b|<\|im_start\|>)", re.I), "high", "Chat-template / delimiter injection", "0.1.0"),
    Rule("tool_hijack", _r(r"\b(call|invoke|execute|run)\s+the\s+[\w.-]+\s+(tool|function)\s+(with|to)\b", re.I), "high", "Attempt to drive agent tool calls", "0.1.0"),
    Rule("encoded_payload", _r(r"\b(base64|decode)\b.{0,40}\b[A-Za-z0-9+/]{40,}={0,2}"), "medium", "Encoded payload smuggling", "0.1.0"),
]

SECRET_RULES: list[Rule] = [
    Rule("stripe_live_key", _r(r"sk[-_]live[-_][A-Za-z0-9]{20,}"), "critical", "Stripe live secret key"),
    Rule("aws_access_key", _r(r"AKIA[0-9A-Z]{16}"), "critical", "AWS access key id"),
    Rule("google_api_key", _r(r"AIza[0-9A-Za-z\-_]{35}"), "critical", "Google API key"),
    Rule("bearer_token", _r(r"Bearer\s+[A-Za-z0-9._\-+/]+={0,2}"), "high", "Bearer token"),
    Rule("private_key", _r(r"-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----"), "critical", "PEM private key"),
    # --- added in 0.1.0
    Rule("github_token", _r(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"), "critical", "GitHub token", "0.1.0"),
    Rule("slack_token", _r(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"), "high", "Slack token", "0.1.0"),
]

UNSAFE_RULES: list[Rule] = [
    Rule("autonomous_dosing", _r(r"(prescribe|administer|inject|give)\s+\d+\s*(mg|ml|mcg|units?)\s+(of\s+)?[a-z]+", re.I), "critical", "Autonomous medication dosing"),
    Rule("autonomous_discharge", _r(r"(auto[-_]?discharge|automatically discharge|discharge\s+without)", re.I), "critical", "Autonomous discharge"),
    Rule("clinician_bypass", _r(r"(don'?t wait for|skip|bypass)\s+(physician|doctor|clinician|nurse)\s+(sign[-\s]?off|approval|review)", re.I), "critical", "Clinician sign-off bypass"),
    Rule("alarm_override", _r(r"(override|silence|disable)\s+(the\s+)?(alarm|alert|warning)", re.I), "critical", "Clinical alarm override"),
    Rule("unauthorized_disclosure", _r(r"(disclose|share|send|email)\s+(patient|clinical|medical)\s+(record|data|info|details)\s+to", re.I), "critical", "Unauthorised disclosure"),
]

PHI_PILLARS = ["Privacy", "Protection", "Trust"]
INJECTION_PILLARS = ["Safety", "Security", "Trust"]
PQ_INJECTION_PILLARS = ["Security", "Protection", "Trust"]
SECRET_PILLARS = ["Protection", "Security"]
UNSAFE_PILLARS = ["Safety", "Trust"]


def rule_table(name: str) -> list[Rule]:
    return {"phi": PHI_RULES, "injection": INJECTION_RULES, "secrets": SECRET_RULES, "unsafe": UNSAFE_RULES}[name]


def describe(rules: list[Rule]) -> list[dict]:
    return [
        {"type": r.type, "severity": r.severity, "description": r.description, "added_in": r.added_in, "pattern": r.pattern.pattern}
        for r in rules
    ]
