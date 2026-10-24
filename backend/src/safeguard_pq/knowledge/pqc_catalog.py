"""Post-quantum identification knowledge base.

Classifies a cryptographic primitive / protocol name into a quantum-threat
status. The classification follows publicly documented positions:

* NIST FIPS 203 (ML-KEM), FIPS 204 (ML-DSA), FIPS 205 (SLH-DSA), August 2024.
* NIST IR 8547 (initial public draft, Nov 2024): proposed transition timeline
  deprecating quantum-vulnerable public-key algorithms (112-bit) after 2030 and
  disallowing them after 2035.
* Shor's algorithm breaks RSA, finite-field DH and elliptic-curve schemes;
  Grover's algorithm gives at most a quadratic speed-up against symmetric keys
  and hashes.
* RFC 8996 deprecates TLS 1.0 and TLS 1.1.

This is a rule table, not a cryptanalysis engine. Unknown names are reported
as ``unknown`` rather than guessed.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

# quantum_status values
VULNERABLE = "quantum_vulnerable"  # broken by Shor on a CRQC
WEAKENED = "grover_weakened"  # security margin reduced; still acceptable per NIST
RESISTANT = "quantum_resistant"
HYBRID = "hybrid_pq"  # classical + PQ combined; resistant if the PQ component holds
CLASSICALLY_BROKEN = "classically_broken"
DEPRECATED = "deprecated_protocol"
CANDIDATE = "pq_candidate"  # selected by NIST, standard not yet final
TRANSITIONAL = "transitional_protocol"  # not deprecated, but cannot negotiate standardised PQ groups
UNKNOWN = "unknown"

PQ_SAFE_STATUSES = {RESISTANT, HYBRID}


@dataclass(frozen=True)
class Primitive:
    key: str
    display: str
    kind: str  # kem | key_exchange | signature | symmetric | hash | protocol
    quantum_status: str
    quantum_attack: str | None
    replacement: str | None
    references: tuple[str, ...]
    notes: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["references"] = list(self.references)
        return d


_FIPS203 = "NIST FIPS 203 (ML-KEM)"
_FIPS204 = "NIST FIPS 204 (ML-DSA)"
_FIPS205 = "NIST FIPS 205 (SLH-DSA)"
_IR8547 = "NIST IR 8547 ipd (PQC transition timeline, draft)"

_RULES: list[tuple[str, Primitive]] = [
    # --- hybrid groups (checked before pure classical / pure PQ)
    (
        r"(X25519|X448|SECP256R1|SECP384R1|P256|P384).*(MLKEM|KYBER)|(MLKEM|KYBER).*(X25519|X448|P256|P384)",
        Primitive(
            "hybrid_mlkem", "Hybrid ECDHE + ML-KEM", "key_exchange", HYBRID, None,
            "Keep hybrid during transition; move to pure ML-KEM when policy allows.",
            (_FIPS203, "IETF draft-ietf-tls-ecdhe-mlkem"),
            "Resistant to quantum key recovery as long as the ML-KEM component is secure.",
        ),
    ),
    (r"MLKEM|KYBER", Primitive("ml_kem", "ML-KEM", "kem", RESISTANT, None, None, (_FIPS203,))),
    (r"MLDSA|DILITHIUM", Primitive("ml_dsa", "ML-DSA", "signature", RESISTANT, None, None, (_FIPS204,))),
    (r"SLHDSA|SPHINCS", Primitive("slh_dsa", "SLH-DSA", "signature", RESISTANT, None, None, (_FIPS205,))),
    (
        r"FNDSA|FALCON",
        Primitive(
            "fn_dsa", "FN-DSA (Falcon)", "signature", CANDIDATE, None, None,
            ("NIST draft FIPS 206 (FN-DSA)",), "Selected by NIST; final standard pending.",
        ),
    ),
    (
        r"^HQC",
        Primitive(
            "hqc", "HQC", "kem", CANDIDATE, None, None,
            ("NIST PQC 4th-round selection (2025)",), "Selected as a backup KEM; standard pending.",
        ),
    ),
    # --- classical public-key (Shor)
    (
        r"ECDHE|ECDH|X25519|X448",
        Primitive(
            "ecdh", "ECDH / ECDHE", "key_exchange", VULNERABLE, "Shor",
            "Hybrid X25519 + ML-KEM-768 first, then ML-KEM-768", (_FIPS203, _IR8547),
        ),
    ),
    (
        r"ECDSA|EDDSA|ED25519|ED448",
        Primitive(
            "ecdsa", "ECDSA / EdDSA", "signature", VULNERABLE, "Shor",
            "ML-DSA-65 (or SLH-DSA for long-lived roots of trust)", (_FIPS204, _FIPS205, _IR8547),
        ),
    ),
    (
        r"^(FF)?DHE?(\d|$)|^DH\b|^DHE",
        Primitive(
            "ffdh", "Finite-field Diffie-Hellman", "key_exchange", VULNERABLE, "Shor",
            "ML-KEM-768", (_FIPS203, _IR8547),
        ),
    ),
    (
        r"RSA",
        Primitive(
            "rsa", "RSA", "key_exchange", VULNERABLE, "Shor",
            "ML-KEM-768 (key establishment) + ML-DSA-65 (signatures)", (_FIPS203, _FIPS204, _IR8547),
        ),
    ),
    (
        r"^ECC|^EC$|^ECP",
        Primitive("ecc", "Elliptic-curve cryptography", "key_exchange", VULNERABLE, "Shor",
                  "ML-KEM-768 + ML-DSA-65", (_FIPS203, _FIPS204)),
    ),
    # --- symmetric (Grover)
    (
        r"AES128",
        Primitive(
            "aes128", "AES-128", "symmetric", WEAKENED, "Grover",
            "AES-256 for long-lived data (optional hardening)",
            ("NIST IR 8547 ipd", "NSA CNSA 2.0"),
            "NIST considers AES-128 acceptable; CNSA 2.0 requires AES-256.",
        ),
    ),
    (r"AES(192|256)", Primitive("aes256", "AES-192/256", "symmetric", RESISTANT, "Grover (adequate margin)", None, ("NIST IR 8547 ipd",))),
    (r"CHACHA20", Primitive("chacha20", "ChaCha20-Poly1305", "symmetric", RESISTANT, "Grover (adequate margin)", None, ("RFC 8439",))),
    (
        r"3DES|DESEDE|TRIPLEDES|^DES",
        Primitive("3des", "Triple-DES", "symmetric", CLASSICALLY_BROKEN, None, "AES-256-GCM", ("NIST SP 800-131A Rev. 2",)),
    ),
    # --- hashes
    (
        r"^(HMAC)?SHA1$|^SHA1WITH|^MD5",
        Primitive("weak_hash", "SHA-1 / MD5", "hash", CLASSICALLY_BROKEN, None, "SHA-384 / SHA-512", ("NIST SP 800-131A Rev. 2",)),
    ),
    (r"SHA(224|256)$|SHA3(224|256)", Primitive("sha256", "SHA-2/3 (256-bit)", "hash", WEAKENED, "Grover/BHT (adequate margin)", "SHA-384 for long-lived signatures", ("NIST IR 8547 ipd",))),
    (r"SHA(384|512)|SHA3(384|512)|SHAKE", Primitive("sha384", "SHA-2/3 (384/512-bit)", "hash", RESISTANT, None, None, ("NIST IR 8547 ipd",))),
    # --- protocols
    (r"^SSL", Primitive("ssl", "SSL", "protocol", DEPRECATED, None, "TLS 1.3", ("RFC 7568", "RFC 6176"))),
    (r"^TLSV?1?(0|1)$|^TLSV?1(\.)?(0|1)$", Primitive("tls_legacy", "TLS 1.0 / 1.1", "protocol", DEPRECATED, None, "TLS 1.3", ("RFC 8996",))),
    (
        r"^TLSV?12$",
        Primitive(
            "tls12", "TLS 1.2", "protocol", TRANSITIONAL, None, "TLS 1.3 (required for hybrid ML-KEM groups)",
            ("RFC 8446", "IETF draft-ietf-tls-ecdhe-mlkem"),
            "Not deprecated, but standardised hybrid PQ key exchange targets TLS 1.3.",
        ),
    ),
    (r"^TLSV?13$", Primitive("tls13", "TLS 1.3", "protocol", RESISTANT, None, None, ("RFC 8446",), "Protocol itself is fine; PQ safety depends on the negotiated group.")),
]

_COMPILED = [(re.compile(p), prim) for p, prim in _RULES]


def normalize(name: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(name).upper())


def classify(name: str | None) -> Primitive:
    if not name:
        return Primitive("none", "not supplied", "unknown", UNKNOWN, None, None, ())
    n = normalize(name)
    for rx, prim in _COMPILED:
        if rx.search(n):
            return prim
    return Primitive("unknown", str(name), "unknown", UNKNOWN, None, None, (), "Not in knowledge base.")


def is_pq_safe(name: str | None) -> bool:
    return classify(name).quantum_status in PQ_SAFE_STATUSES


def is_quantum_vulnerable(name: str | None) -> bool:
    return classify(name).quantum_status == VULNERABLE


def catalog() -> list[dict]:
    return [prim.to_dict() | {"pattern": p} for p, prim in _RULES]
