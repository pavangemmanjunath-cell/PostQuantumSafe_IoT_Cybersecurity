# Formulas, constants and instance generators (Release 3)

This appendix gives the exact benefit formula, the rounding rule, the gap formula, the instance-generation
distributions and the energy function that is actually minimised (relevant to the term "quantum-inspired"). Every
formula below is transcribed from the code (file names in parentheses) so the paper can cite them verbatim.

## 1. Pillar scores (`agents/scoring.py`)

For each pillar *k* ∈ {Trust, Identity, Privacy, Protection, Safety, Security}:

```
P_k = max(0, 100 − Σ_{f ∈ F : k ∈ pillars(f)} d(sev_f)),   d = {critical: 25, high: 15, medium: 8, low: 3, info: 0}
```

## 2. PQ risk score and verdict (`agents/scoring.py`)

Each finding raised by the crypto, PQ, identity and secret agents belongs to one category *c*:

| Category `c` | Weight `w_c` | Findings |
|---|---|---|
| pkc | 0.30 | classical key exchange / signature / certificate key, weak hash, weak symmetric cipher, pq_migration_required, mosca_hndl_exposure |
| tls | 0.20 | deprecated_tls_version |
| lifetime | 0.20 | long_lifetime_classical_crypto |
| identity | 0.15 | missing_certificate, authentication_failed |
| secrets | 0.10 | every secret pattern |
| migration | 0.05 | 75 if no PQ key exchange or signature is detected, else 0 |

The category is assigned by `category_of`: `deprecated_tls_version` → tls, `long_lifetime_classical_crypto` →
lifetime, every other finding of the crypto-inventory and PQ-identification agents → pkc. Mosca's medium finding
`mosca_hndl_exposure` (section 4) is therefore scored under pkc; only the critical lifetime override feeds the
lifetime category. Because the Mosca finding is raised only together with a high classical public-key finding
(`v_pkc` ≥ 75), it never changes `S`; it deducts pillar points (Privacy, Protection).

```
v_c = max_{f ∈ F_c} pts(sev_f),   pts = {critical: 100, high: 75, medium: 50, low: 25}
S   = round_half_up( Σ_c w_c · v_c ),   round_half_up(x) = ⌊x + 0.5⌋          (JavaScript Math.round semantics)
verdict(S): S ≤ 25 Safe · 25 < S ≤ 50 Partially Safe · 50 < S ≤ 75 Not Post-Quantum Safe · S > 75 Critical Quantum Risk
```

## 3. Environment status — the single SAFE rule (`agents/scoring.py: environment_status`)

```
UNSAFE   if  ∃ critical finding  or  S > 50
AT_RISK  else if  ∃ high/medium finding  or  S > 25  or  no tls_config was supplied
SAFE     otherwise  (no finding across the evaluated controls on the supplied evidence, and S ≤ 25)
```

SAFE therefore means "no finding of severity ≥ medium on the supplied evidence and S ≤ 25". A system whose
cryptographic configuration was not supplied is never SAFE (it is AT_RISK with the reason "PQ safety is unverified").
This replaces earlier, self-contradictory wording.

## 4. Mosca's inequality `M` and the lifetime override `P` (`agents/crypto.py`, `tools/builtin.py`)

With data lifetime *x* (years), migration time *y* and years to a CRQC *z* (both operator assumptions):

```
M : at_risk  ⇔  x + y > z
P : lifetime override  ⇔  x ≥ L  and classical key exchange and a classical primitive is present   (L = 10 y by default)
```

If `P` holds, the critical finding `long_lifetime_classical_crypto` is raised; else if `M` holds, the medium finding
`mosca_hndl_exposure` is raised. `M` is always reported in the PQ posture (`pq_posture.mosca`) independently of `P`.
`L` is an explicit assumption since Release 3 (`assumptions.lifetime_threshold_years`) and is swept in experiment E7.

## 5. Action benefit and value density (`optimizer/qiro.py: build_actions`)

For finding *i* with template *t(i)* (base risk reduction *r_t*, cost *C_i*, downtime *D_i*, complexity *K_i*):

```
B_i = round_half_up(r_t · m_sev)  +  25·[i is a PQ finding]  +  20·[Safety ∈ pillars(i)]  +  round_half_up(10 · Σ_{k ∈ pillars(i)} ω_k)
m_sev = {critical: 1.5, high: 1.0, medium: 0.6, low: 0.3};   ω_Privacy = 1.2, ω_Safety = 1.4, ω_k = 1.0 otherwise
density_i = B_i / max(1, C_i / 1000 + 2·D_i + K_i)                     (greedy ordering key)
```

"PQ finding" = raised by the PQ-identification agent or of type classical_key_exchange, classical_signature,
classical_certificate_key, deprecated_tls_version, weak_hash, long_lifetime_classical_crypto, pq_migration_required,
mosca_hndl_exposure. All rounding in the framework is half-up (`js_round`).

## 6. The optimisation problem and the energy that is minimised (`optimizer/qiro.py`)

```
maximise   f(x) = Σ_i (B_i − ½ K_i) x_i − pen(x)                      x_i ∈ {0, 1}
pen(x)   = 100 · max(0, (Σ_i C_i x_i − B) / 1000) + 100 · max(0, Σ_i D_i x_i − D)
```

The annealer (`iterations = min(3000, 200 + 80 n)`, `T_0 = 100`, cooling 0.995, single-bit flips, Metropolis
acceptance `exp(Δ/T)`) **accepts only feasible neighbours**, so `pen(x) = 0` on every visited state and the problem
solved is the two-constraint 0/1 knapsack `max Σ (B_i − ½ K_i) x_i s.t. Σ C_i x_i ≤ B, Σ D_i x_i ≤ D`. The energy
is `H(x) = −f(x)`. It is linear in `x`, i.e. an Ising/QUBO form with zero quadratic couplings and a penalty that is
never active; there is no quadratic penalty term and no quantum hardware or quantum-circuit simulation. **We
therefore recommend that the paper describes QIRO as "simulated annealing with a deterministic local-search polish
(historically named quantum-inspired)" and does not claim a QUBO formulation.** Local search: best-improvement over
feasible add / drop / swap moves until no move improves `f`.

## 7. Optimality gap (`benchmarks/qiro_optimality.py`, `benchmarks/qiro_scalability.py`)

```
gap(method) = 100 · (f* − f_method) / f*,   f* = exhaustive optimum (n ≤ 14) or ILP optimum (HiGHS; n = 20…200)
```

Instances with `f* = 0` are excluded and counted. "Solved optimally" means `gap ≤ 1e-9`.

## 8. Projected and reassessed scores (`agents/explain.py`, `optimizer/reassess.py`)

```
S_proj  = S(F \ F_sel)            findings whose action was selected are removed; PQ-detected flag re-derived
S_reass = S( pipeline( apply_plan(request, plan) ) )   the plan's mitigations are applied to the configuration and the
                                                       detection + scoring stages are re-run
```

`apply_plan` applies the catalogue mitigation of each selected action (`simulation/catalog.py: MITIGATIONS`) to the
request: TLS fields, device-log fields, prompt filtering and redaction. Network mitigations (rate limiting,
segmentation) have no configuration-level effect and are reported as *unmodelled*, so traffic findings remain in
`S_reass`.

## 9. Synthetic instance generators

| Experiment | n | Finding type | Severity | Pillars | Budget B | Downtime D |
|---|---|---|---|---|---|---|
| E4 (`qiro_optimality.py`) | U{3, …, 14} | uniform over the 42 catalogue templates | U{critical, high, medium, low} | random subset of size U{1, 2, 3} of the 6 pillars | U{20 000, 50 000, 100 000} USD | U{4, 10, 40} h |
| E8 (`qiro_scalability.py`) | fixed ∈ {20, 50, 100, 200} | same | same | same | τ · Σ C_i, τ ∈ U{0.25, 0.5, 0.75} | τ · Σ D_i |

Catalogue ranges (`knowledge/remediation.py`, 42 templates): cost 4 000 – 50 000 USD, downtime 1 – 12 h, complexity
2 – 9, base risk reduction 15 – 45. The instance generator seed is 0; the optimizer seed for instance *k* is *k*.
Assessments of the ten scenarios use the optimizer default seed 2026 (`QIRO_DEFAULT_SEED`).

## 10. Software versions and commands

Python 3.13.5 on Windows 11; package versions are pinned by `backend/pyproject.toml` (`fastapi`, `pydantic`,
`reportlab`) and the optional `benchmark` extra (`highspy` for the ILP reference, `matplotlib` for figures). One
command per experiment is listed in the [reproducibility guide](../reproducibility.md#paper-experiment--command--artifact).
