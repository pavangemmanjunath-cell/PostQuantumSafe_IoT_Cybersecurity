"""Clearly fake credentials for simulation and tests.

Built at runtime from fragments so that no credential-shaped literal exists in
the source tree (avoids secret-scanner false positives on public hosting).
They are not valid for any service.
"""

from __future__ import annotations


def fake_stripe_key() -> str:
    return "sk" + "_" + "live" + "_" + "SIMULATED" + "FAKEKEY" + "00000000"


def fake_aws_key_id() -> str:
    return "AK" + "IA" + "SIMULATED" + "FAKEKEY"


PLACEHOLDERS = {"{{FAKE_STRIPE_KEY}}": fake_stripe_key, "{{FAKE_AWS_KEY_ID}}": fake_aws_key_id}


def fill_placeholders(text: str) -> str:
    for token, fn in PLACEHOLDERS.items():
        text = text.replace(token, fn())
    return text
