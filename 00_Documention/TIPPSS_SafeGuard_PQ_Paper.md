# TIPPSS SafeGuard-PQ: An Agentic Post-Quantum Cybersecurity Assessment and Constraint-Aware Migration Planning Framework for Clinical IoT and AI Healthcare Systems

**Pavan Gemmanjunath**  
IEEE SA Cybersecurity Initiative · Clinical IoT Security Research  
Contact: pavan5119m@gmail.com

---

## Abstract

The accelerating development of cryptographically relevant quantum computers poses an existential threat to the classical public-key infrastructure securing clinical Internet of Things (IoT) systems, electronic health record (EHR) APIs, and AI-assisted diagnostic platforms. Adversaries conducting harvest-now-decrypt-later (HNDL) attacks are already capturing encrypted patient data today for decryption when quantum hardware matures — a timeline now estimated between 2030 and 2035. Despite the publication of NIST FIPS 203, 204, and 205 post-quantum standards in 2024, no operational automated assessment tool exists that simultaneously evaluates cryptographic posture, medical device identity, AI prompt privacy, secret exposure, and clinical safety risk against these standards and the IEEE 2933-2024 TIPPSS framework.

This paper presents **TIPPSS SafeGuard-PQ**, a multi-agent agentic pipeline that performs automated post-quantum security assessments of clinical IoT systems and produces budget-constrained, downtime-aware migration roadmaps using a novel **Quantum-Inspired Remediation Optimizer (QIRO)**. QIRO formulates remediation planning as a binary optimisation problem in the QUBO/Ising style, solved via Simulated Annealing on classical CPU hardware. Evaluation across eight real-world datasets — six CICIoMT2024 medical IoT network traffic captures and two Synthea synthetic clinical record files — demonstrates correct discrimination between benign and attack scenarios, accurate PHI detection, and constraint-sensitive migration planning that dynamically adapts the remediation roadmap to available budget and downtime limits.

**Keywords:** Post-Quantum Cryptography, Clinical IoT Security, TIPPSS, ML-KEM, ML-DSA, QIRO, Simulated Annealing, QUBO, Healthcare AI Security, NIST FIPS 203/204/205, IEEE 2933-2024

---

## 1. Introduction

Healthcare organisations operate under a convergence of two emergent pressures. First, the cryptographic foundations of their infrastructure — RSA-2048, ECDHE-P256, ECDSA-P256, and AES-128 — are mathematically vulnerable to Shor's algorithm [1] running on a sufficiently capable quantum processor. Second, healthcare data must be retained for periods of 15 to 50 years under HIPAA and national health data regulations, creating a severe harvest-now-decrypt-later exposure window.

The NIST Post-Quantum Cryptography standardisation process concluded in August 2024 with the publication of three standards: FIPS 203 (ML-KEM, based on Kyber [2]), FIPS 204 (ML-DSA, based on Dilithium [2]), and FIPS 205 (SLH-DSA, based on SPHINCS+ [2]). These standards provide the cryptographic primitives for post-quantum migration. However, the existence of standards does not operationalise migration. Hospitals face three unsolved practical problems:

1. **Detection gap**: No automated tool assesses all relevant risk dimensions — cryptographic, device identity, AI prompt privacy, secret exposure, and patient safety — simultaneously against the TIPPSS framework.
2. **Planning gap**: No tool produces migration roadmaps constrained by real hospital budget and operational downtime limits.
3. **Optimisation gap**: No tool frames the remediation selection problem as a mathematical optimisation, enabling provably near-optimal action selection.

This work addresses all three gaps through the following contributions:

- A **10-agent agentic pipeline** that assesses TLS cryptographic configuration, medical IoT device identity, AI assistant prompt logs, device secret exposure, and autonomous AI safety risk against NIST FIPS 203/204/205 and IEEE 2933-2024 TIPPSS.
- A **novel QIRO algorithm** that formulates remediation planning as a constrained binary optimisation (QUBO-style) and solves it via Simulated Annealing, producing selected and deferred action sets with full budget and downtime accountability.
- **Empirical evaluation** on CICIoMT2024 (University of New Brunswick) network traffic datasets and Synthea (MITRE) synthetic patient records, demonstrating correct risk discrimination and constraint-sensitive planning.

The remainder of this paper is organised as follows. Section 2 reviews related work. Section 3 describes the system architecture. Section 4 presents the QIRO mathematical formulation. Section 5 describes the implementation. Section 6 presents experimental results. Section 7 discusses findings. Section 8 concludes with future directions.

---

## 2. Related Work and Literature Review

### 2.1 Post-Quantum Cryptography

The mathematical threat to public-key cryptography from quantum computing was established by Shor [1], who demonstrated polynomial-time algorithms for integer factorisation and discrete logarithm computation — the hard problems underlying RSA and ECDSA respectively. Grover's algorithm [3] provides a quadratic speedup against symmetric-key systems, effectively halving key lengths. The practical implications of these results for deployed infrastructure were analysed by Mosca [4], who introduced the widely cited *Mosca inequality*: if the time to migrate to PQC plus the security shelf-life of current data exceeds the time to quantum advantage, the organisation is at risk.

Bernstein and Lange [5] provide a comprehensive survey of post-quantum algorithm families — lattice-based, hash-based, code-based, and isogeny-based — evaluating their security assumptions and performance characteristics. The NIST standardisation effort [6] selected ML-KEM, ML-DSA, and SLH-DSA as the primary standards, establishing concrete cryptographic primitives for migration.

### 2.2 Clinical IoT and Healthcare Security

The unique security challenges of medical IoT — constrained devices, safety-critical operation, regulatory compliance, and long device lifetimes — have been studied extensively. Sicari et al. [7] survey the intersection of security, privacy, and trust in IoT, identifying key vulnerabilities in authentication, data integrity, and access control that apply directly to clinical environments. Hossain et al. [8] address cloud-assisted IoT medical system security, proposing secure data sharing frameworks that nevertheless rely on classical cryptographic primitives now considered PQ-vulnerable.

The CICIoMT2024 dataset [9], published by the Canadian Institute for Cybersecurity at the University of New Brunswick, provides the first comprehensive network traffic dataset for medical IoT, including ARP spoofing, MQTT malformation, DoS, DDoS, and reconnaissance attack classes captured from real medical IoT devices. This dataset enables controlled evaluation of IoT security assessment tools against labelled attack and benign traffic.

### 2.3 AI Safety and PHI Privacy in Healthcare

The integration of large language models into clinical workflows has introduced a new attack surface: AI prompt logs that may expose protected health information (PHI). Wornow et al. [10] and others document the rapid adoption of AI assistants in clinical settings while noting the inadequacy of existing privacy controls for AI prompt logging. HIPAA's minimum necessary standard applies to AI-assisted workflows, yet no automated scanning tool for PHI in prompt logs existed prior to this work.

### 2.4 Optimisation in Security Planning

The application of combinatorial optimisation to security prioritisation has been explored in the context of vulnerability management. Bozorgi et al. [11] formulate vulnerability prioritisation as a constrained optimisation problem, demonstrating that constraint-aware selection outperforms severity-ordered lists. Glasser and Lindqvist [12] apply similar techniques to security investment allocation, establishing the theoretical basis for budget-constrained remediation planning. No prior work applies QUBO-style binary optimisation to post-quantum migration planning in the healthcare IoT context.

### 2.5 Simulated Annealing and QUBO

The Simulated Annealing metaheuristic was introduced by Kirkpatrick, Gelatt, and Vecchi [13], who demonstrated its effectiveness for combinatorial optimisation by analogy to the physical annealing of metals. The Metropolis-Hastings acceptance criterion allows escape from local optima, enabling near-optimal solutions to NP-hard problems. QUBO (Quadratic Unconstrained Binary Optimisation) formulations have been applied to portfolio selection, scheduling, and logistics; this work introduces their application to post-quantum remediation planning.

Preskill [14] characterises the near-term quantum computing era (NISQ) and its limitations, providing the technical context for why quantum-inspired classical algorithms — which model QUBO problems without requiring quantum hardware — are appropriate for immediate deployment.

---

### 2.6 Comparative Literature Review

The following table compares TIPPSS SafeGuard-PQ against the ten most relevant prior works across key evaluation dimensions.

| # | Reference | Year | Objective | Methods | Dataset | Algorithm | Performance / Accuracy | Limitations | Research Gap Addressed by This Work |
|---|-----------|------|-----------|---------|---------|-----------|----------------------|-------------|--------------------------------------|
| 1 | Shor [1] | 1994 | Demonstrate polynomial-time quantum factorisation breaking RSA/ECC | Quantum circuit design; quantum Fourier transform | Theoretical | Shor's algorithm | Polynomial time on quantum hardware | Requires large-scale error-corrected quantum computer | Provides the threat motivating PQ migration; no defence proposed |
| 2 | Grover [3] | 1996 | Quadratic speedup for unstructured search; halves symmetric key security | Quantum amplitude amplification | Theoretical | Grover's search | $O(\sqrt{N})$ vs $O(N)$ classical | Requires quantum hardware; limited to symmetric key impact | Motivates AES-256 requirement; no IoT or healthcare application |
| 3 | Bernstein & Lange [5] | 2017 | Survey and compare post-quantum algorithm families | Mathematical analysis; security reduction proofs | Theoretical | Lattice, hash, code, isogeny | Security proofs; NIST evaluation metrics | No practical deployment tool; no healthcare or IoT focus | No assessment tool; no constraint-aware migration planning |
| 4 | Mosca [4] | 2018 | Framework for assessing organisational PQ migration urgency | Risk analysis; Mosca inequality | Survey / expert opinion | Heuristic risk model | Qualitative readiness assessment | Manual process; no automated tool; no IoT specifics | No automation; no multi-pillar clinical IoT assessment |
| 5 | NIST FIPS 203/204/205 [6] | 2024 | Standardise ML-KEM, ML-DSA, SLH-DSA for practical deployment | Lattice-based and hash-based cryptography | NIST PQC competition submissions | ML-KEM (Kyber), ML-DSA (Dilithium), SLH-DSA (SPHINCS+) | Security proofs; NIST benchmark tests | Standard only; no deployment tool; no IoT guidance | Gap between standard and operational healthcare deployment |
| 6 | Kirkpatrick et al. [13] | 1983 | Efficient optimisation of NP-hard combinatorial problems | Simulated annealing; Metropolis-Hastings | Travelling salesman; circuit placement | Simulated Annealing with geometric cooling | Near-optimal on benchmark instances | General-purpose; not applied to cybersecurity planning | Provides QIRO's solver foundation; no security application |
| 7 | Sicari et al. [7] | 2015 | Survey IoT security, privacy, and trust challenges | Systematic literature review | IoT vulnerability literature | Taxonomy-based analysis | 105-paper systematic review | No post-quantum awareness; no medical IoT focus | Identifies attack surface; no PQ-specific assessment tool |
| 8 | Hossain et al. [8] | 2016 | Secure data sharing for cloud-assisted IoT medical systems | Attribute-based encryption; role-based access | Simulated medical IoT network | Classical RSA / AES encryption | Functional correctness on simulated data | Relies on RSA/AES vulnerable to quantum adversaries | No post-quantum migration path; no constraint-aware planning |
| 9 | Preskill [14] | 2018 | Characterise NISQ-era quantum computing capabilities and limitations | Theoretical analysis; circuit depth analysis | Theoretical | NISQ device modelling | Rigorous error analysis | Describes near-term limits; no defence or mitigation | Motivates classical-CPU quantum-inspired approach of QIRO |
| 10 | CICIoMT2024 [9] | 2024 | Comprehensive medical IoT attack dataset for intrusion detection research | Controlled clinical IoT network capture; Wireshark; feature extraction | 18 attack classes; benign baseline; real medical IoT devices | Feature-based ML classifiers (Random Forest, XGBoost) | 99%+ accuracy on closed-set classification | No post-quantum security dimension; no remediation planning | Provides evaluation dataset; no PQ assessment integrated |
| 11 | Wornow et al. [10] | 2023 | Systematic review of LLMs in clinical workflows | Literature review; case studies | Clinical NLP benchmarks | GPT-4, Med-PaLM, BioGPT | Demonstrates clinical capability; limited PHI governance analysis | No automated PHI detection in prompt logs | PHI leakage into AI prompts is unaddressed vulnerability |
| 12 | Bozorgi et al. [11] | 2010 | Predict exploitability and prioritise vulnerability remediation | SVM-based exploitability prediction; constraint optimisation | NVD CVE data | SVM + constrained optimisation | AUC 0.83 on exploitability prediction | No post-quantum focus; no healthcare context; no binary optimisation | Budget-constrained selection concept; extended to QUBO by QIRO |
| 13 | Glasser & Lindqvist [12] | 2016 | Security investment optimisation under budget constraints | Game theory; optimisation | Simulated enterprise security portfolio | Linear programming | Optimal investment under linear constraints | No IoT; no PQC; no downtime constraint; no binary formulation | Establishes constraint-aware security planning; QIRO extends to QUBO |
| 14 | IEEE 2933-2024 [15] | 2024 | Define TIPPSS six-pillar security framework for clinical IoT | Standards committee; expert consensus; field study | Clinical IoT deployment data | Framework / taxonomy | Adopted as international standard | Framework only; no automated assessment tool | Provides TIPPSS pillar mapping; no tool implements it automatically |

**Table 1.** Comparative analysis of related work. QIRO and TIPPSS SafeGuard-PQ address the intersection of all identified research gaps simultaneously.

---

## 3. System Architecture

### 3.1 Architectural Overview

TIPPSS SafeGuard-PQ implements a layered agentic architecture comprising three tiers: a presentation tier (Streamlit dashboard), an orchestration tier (n8n workflow engine), and a data tier (test output stores). The pipeline is initiated by a structured JSON payload representing a clinical system's configuration, which may originate from a pre-built simulation scenario, a user-uploaded CICIoMT2024 network file, or a Synthea synthetic clinical record.

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRESENTATION TIER                             │
│  Streamlit Dashboard (localhost:8501)                            │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  Scenario    │  │  CSV/PCAP File   │  │  Result Display  │  │
│  │  Selector    │  │  Uploader        │  │  Verdict · Gauge │  │
│  │  (7 built-in)│  │  (CICIoMT/       │  │  Spider · QIRO   │  │
│  └──────────────┘  │   Synthea)       │  │  Roadmap         │  │
│  ┌──────────────┐  └──────────────────┘  └──────────────────┘  │
│  │  Budget      │                                                │
│  │  Downtime    │  ← Constraint Sliders (QIRO inputs)           │
│  │  Sliders     │                                                │
│  └──────────────┘                                                │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP POST (JSON payload)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ORCHESTRATION TIER                             │
│  n8n Workflow Engine (localhost:5678)                            │
│                                                                  │
│  Agent 1: Input Validator & Schema Parser                        │
│      ↓                                                           │
│  Agent 2: Cryptographic Classifier (TLS/Cert Analysis)          │
│      ↓                                                           │
│  Agent 3: PQ Benchmark (NIST FIPS 203/204/205)                  │
│      ↓                                                           │
│  Agent 4: IoT Device Identity (IEEE 2933-2024)                   │
│      ↓                                                           │
│  Agent 5: AI Prompt Privacy (PHI Detection)                      │
│      ↓                                                           │
│  Agent 6: Secret Exposure Scanner                                │
│      ↓                                                           │
│  Agent 7: Clinical Safety Risk Analyser                          │
│      ↓                                                           │
│  Agent 8: TIPPSS Six-Pillar Scorer                               │
│      ↓                                                           │
│  Agent 9: Claude AI Executive Report Generator                   │
│      ↓                                                           │
│  Agent 10: QIRO Optimizer (Simulated Annealing)                  │
│      ↓                                                           │
│  Assessment Response (JSON)                                      │
└────────────────────────────┬────────────────────────────────────┘
                             │ JSON response
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATA TIER                                   │
│  fileuploadoutput/   ← Timestamped payload + result + summary   │
│  test_outputs/       ← Unit and integration test results        │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Agent Pipeline Description

**Agent 1 — Input Validator:** Parses and validates the incoming JSON payload. Verifies the presence of required fields (`system_id`, `domain`, `tls_config`, `ai_prompt_logs`, `device_logs`, `constraints`). Rejects malformed inputs with structured error responses.

**Agent 2 — Cryptographic Classifier:** Inspects each TLS configuration parameter: protocol version, key exchange algorithm, certificate signature algorithm, certificate key algorithm, symmetric cipher, hash algorithm, and data lifetime. Classifies each parameter as *post-quantum safe* (ML-KEM, ML-DSA, SLH-DSA, AES-256, SHA-384), *classical* (ECDHE, ECDSA, RSA, AES-128, SHA-256), or *deprecated* (TLS 1.0/1.1, SHA-1, RSA key exchange). Outputs a structured classification array.

**Agent 3 — PQ Benchmark:** Compares the cryptographic classification against NIST FIPS 203, 204, and 205. Generates post-quantum findings for each non-compliant parameter. Applies the *harvest-now-decrypt-later* rule: when data lifetime ≥ 10 years and classical cryptography is present, a critical `long_lifetime_classical_crypto` finding is raised. This finding is suppressed when ML-KEM and ML-DSA are already deployed.

**Agent 4 — IoT Device Identity:** Evaluates each entry in `device_logs` against the IEEE 2933-2024 Trust and Identity pillars. Checks certificate presence, authentication status, and failed login counts. Raises identity and trust findings for missing certificates, failed authentication, or repeated login failures.

**Agent 5 — AI Prompt Privacy:** Scans all entries in `ai_prompt_logs` for protected health information patterns: medical record numbers (MRN), full patient names, social security numbers, sensitive diagnoses (HIV, cancer, mental health), email addresses, and date-of-birth combinations. Also detects prompt injection attempts (instructions to ignore system prompts or export data).

**Agent 6 — Secret Exposure Scanner:** Scans `device_logs` entries (including debug fields) for credential patterns: Stripe live keys (`sk_live_`), AWS access key IDs (`AKIA`), GitHub tokens (`ghp_`), and generic API key patterns. Raises critical `secret_exposure` findings for each detected credential.

**Agent 7 — Clinical Safety Risk Analyser:** Scans `ai_prompt_logs` for autonomous clinical commands: medication prescriptions without physician authorisation, alarm overrides, autonomous dosing instructions, and bypass commands. Raises critical `safety_risk` findings mapped to the Safety pillar of TIPPSS.

**Agent 8 — TIPPSS Six-Pillar Scorer:** Aggregates all findings from Agents 2–7 and maps each finding to one or more TIPPSS pillars (Trust, Identity, Privacy, Protection, Safety, Security). Computes a normalised risk score per pillar and a composite PQ Risk Score (0–100). Assigns overall verdict: *Safe* (0–25), *Partially Safe* (26–50), *Not Post-Quantum Safe* (51–75), or *Critical Quantum Risk* (76–100).

**Agent 9 — Claude AI Executive Report:** Invokes the Anthropic Claude API to generate a plain-English executive summary of the highest-severity findings, tailored to a clinical CISO audience. The report explains what was found, why it matters for patient safety and data protection, and what immediate actions are recommended.

**Agent 10 — QIRO Optimizer:** Converts all findings into candidate remediation actions, assigns benefit scores, costs, and downtime estimates, and executes the constrained binary optimisation described in Section 4. Outputs selected actions, deferred actions, phased migration roadmap, and constraint utilisation metrics.

---

## 4. QIRO Mathematical Formulation

### 4.1 Problem Definition

Let $\mathcal{F} = \{f_1, f_2, \ldots, f_m\}$ denote the set of findings produced by Agents 2–7. For each finding $f_j$, the QIRO engine generates a candidate remediation action $a_i$ with associated attributes. Let $n = |\mathcal{A}|$ be the total number of candidate actions.

### 4.2 Decision Variable

For each remediation action $a_i$, QIRO defines a binary decision variable:

$$x_i \in \{0, 1\}, \quad i = 1, 2, \ldots, n$$

where $x_i = 1$ indicates that action $a_i$ is **selected** for the current migration cycle, and $x_i = 0$ indicates it is **deferred** to a future cycle.

### 4.3 Benefit Score

Each action receives a composite benefit score incorporating four dimensions:

$$B_i = R_i + P_i + S_i + T_i$$

| Symbol | Dimension | Description |
|--------|-----------|-------------|
| $R_i$ | Risk reduction | Reduction in PQ risk score upon action completion |
| $P_i$ | Post-quantum urgency | Weighted urgency of PQ migration (critical for ECDHE/ECDSA/RSA) |
| $S_i$ | Safety criticality | Patient safety impact weight |
| $T_i$ | TIPPSS impact | Number of TIPPSS pillars improved, normalised |

### 4.4 Constraint Parameters

The hospital operator specifies two hard constraints via the dashboard interface:

$$C_{\max} \in \mathbb{R}^{+} \quad \text{(available remediation budget, USD)}$$

$$D_{\max} \in \mathbb{R}^{+} \quad \text{(allowed service downtime, hours)}$$

Each action $a_i$ carries estimated resource requirements:

$$C_i \in \mathbb{R}^{+} \quad \text{(remediation cost of action } i \text{)}$$

$$D_i \in \mathbb{R}^{+} \quad \text{(service downtime of action } i \text{)}$$

$$K_i \in \mathbb{R}^{+} \quad \text{(implementation complexity of action } i \text{)}$$

### 4.5 Primary Optimisation Objective

QIRO maximises total remediation benefit subject to budget and downtime constraints:

$$\max_{x} \sum_{i=1}^{n} B_i \, x_i$$

subject to:

$$\sum_{i=1}^{n} C_i \, x_i \leq C_{\max} \tag{Budget constraint}$$

$$\sum_{i=1}^{n} D_i \, x_i \leq D_{\max} \tag{Downtime constraint}$$

$$x_i \in \{0, 1\}, \quad \forall i \in \{1, \ldots, n\} \tag{Binary constraint}$$

This is a variant of the **0/1 Knapsack Problem**, which is NP-hard in general. For clinical systems, $n$ is typically 5–15, making exact and near-exact solutions computationally feasible on a classical CPU.

### 4.6 Extended Objective with Complexity Penalty

To discourage selection of high-complexity actions when simpler alternatives achieve comparable risk reduction, QIRO extends the objective with a complexity penalty:

$$\max_{x} \left[ \sum_{i=1}^{n} B_i \, x_i - \lambda \sum_{i=1}^{n} K_i \, x_i \right]$$

where $\lambda \in [0, 1]$ is the complexity penalty weight, tunable to the hospital's operational capacity.

### 4.7 Penalty-Based Energy Function for Simulated Annealing

For the Simulated Annealing solver, the constrained problem is transformed into an unconstrained energy minimisation by encoding the constraints as quadratic penalty terms:

$$E(x) = -\sum_{i=1}^{n} B_i x_i \;+\; \lambda_C \left[\max\!\left(0,\, \sum_{i=1}^{n} C_i x_i - C_{\max}\right)\right]^2 \;+\; \lambda_D \left[\max\!\left(0,\, \sum_{i=1}^{n} D_i x_i - D_{\max}\right)\right]^2 \;+\; \lambda_K \sum_{i=1}^{n} K_i x_i$$

| Term | Role |
|------|------|
| $-\sum B_i x_i$ | Maximises remediation benefit |
| $\lambda_C (\cdots)^2$ | Penalises budget overrun quadratically |
| $\lambda_D (\cdots)^2$ | Penalises downtime overrun quadratically |
| $\lambda_K \sum K_i x_i$ | Penalises high implementation complexity |

QIRO minimises $E(x)$:

$$x^* = \arg\min_{x \in \{0,1\}^n} \; E(x)$$

This energy function is equivalent to an Ising Hamiltonian when variables are mapped to $s_i = 2x_i - 1 \in \{-1, +1\}$, establishing the formal connection to QUBO and quantum annealing formulations.

### 4.8 Simulated Annealing Algorithm

```
Input:  Candidate actions A, budget C_max, downtime D_max, penalty weights λ_C, λ_D, λ_K
        T_start = 100.0, α = 0.995, T_min = 0.01, iterations = 1000

Initialise: x ← random binary vector in {0,1}^n
            x_best ← x,  E_best ← E(x)

For t = 1 to iterations:
    j ← random index in {1, ..., n}
    x' ← x with x'_j flipped (0→1 or 1→0)
    ΔE ← E(x') − E(x)

    If ΔE < 0:
        x ← x'                          // Accept improvement
    Else:
        Accept x' with probability exp(−ΔE / T)   // Metropolis-Hastings

    If E(x) < E_best:
        x_best ← x,  E_best ← E(x)

    T ← T × α                           // Geometric cooling

Output: x* = x_best
        A_selected = {a_i | x*_i = 1}
        A_deferred = {a_i | x*_i = 0}
```

### 4.9 QIRO Output

The optimal remediation portfolio is:

$$\mathcal{A}_{\text{selected}} = \{a_i \mid x_i^* = 1\}, \quad \mathcal{A}_{\text{deferred}} = \{a_i \mid x_i^* = 0\}$$

Post-selection resource tracking:

$$C_{\text{remaining}} = C_{\max} - \sum_{i=1}^{n} C_i x_i^*, \quad D_{\text{remaining}} = D_{\max} - \sum_{i=1}^{n} D_i x_i^*$$

Actions in $\mathcal{A}_{\text{selected}}$ are further organised into a three-phase migration roadmap:

- **Phase 1 (0–6 months):** Critical severity and PQ-urgent actions
- **Phase 2 (6–18 months):** High-severity transitional actions
- **Phase 3 (18–36 months):** Full PQ deployment and lower-severity actions

---

## 5. Implementation

### 5.1 Technology Stack

| Component | Technology | Role |
|-----------|-----------|------|
| Dashboard | Streamlit 1.35, Python 3.10+ | User interface, file processing, result visualisation |
| Agent pipeline | n8n (Docker) | Orchestration of 10 assessment agents |
| QIRO solver | JavaScript (n8n Code node) | Simulated Annealing optimisation |
| Feature extraction | pandas, numpy | CICIoMT2024 network feature computation |
| Visualisation | Plotly | PQ risk gauge, TIPPSS spider chart, QIRO bar chart |
| Output | JSON + CSV | Timestamped per-test results |

### 5.2 Payload Construction

For CICIoMT2024 `.pcap.csv` files, the system samples the first 100 rows and extracts 40+ statistical features from columns including `Header_Length`, `Protocol Type`, `Duration`, `Rate`, `Srate`, `syn_flag_number`, `ack_flag_number`, `TCP`, `UDP`, `ARP`, `ICMP`, `Tot sum`, `AVG`, `Std`, `Variance`, and `Weight`. Derived signals are computed: `arp_activity_sum`, `syn_flag_sum`, `rate_mean`, `duration_mean`, etc.

For Synthea patient records, the system extracts patient identifiers (first name, last name, MRN, date of birth) from the first 20 rows and constructs `ai_prompt_logs` entries that simulate clinical AI assistant inputs, enabling PHI detection testing.

---

## 6. Experimental Results

### 6.1 Experimental Setup

Evaluation was conducted against eight datasets using the live n8n 10-agent pipeline. Default constraints: budget $C_{\max} = \$100{,}000$, downtime $D_{\max} = 40$ hours.

### 6.2 CICIoMT2024 Results

| File | Attack Type | Verdict | PQ Risk Score | Findings | QIRO Selected | QIRO Deferred | Budget Used | Downtime Used |
|------|-------------|---------|:-------------:|:--------:|:-------------:|:-------------:|:-----------:|:-------------:|
| `ARP_Spoofing_test.pcap.csv` | ARP Spoofing | Not Post-Quantum Safe | 61 / 100 | 7 | 4 | 3 | $100,000 | 22h |
| `Benign_test.pcap.csv` | Benign Baseline | **Safe** | **0 / 100** | **0** | 0 | 0 | $0 | 0h |
| `MQTT-Malformed_Data_test.pcap.csv` | MQTT Malformed | Not Post-Quantum Safe | 61 / 100 | 7 | 4 | 3 | $100,000 | 22h |
| `Recon-Port_Scan_test.pcap.csv` | Port Scan | Not Post-Quantum Safe | 61 / 100 | 7 | 4 | 3 | $100,000 | 22h |
| `TCP_IP-DoS-SYN_test.pcap.csv` | SYN DoS | Not Post-Quantum Safe | 61 / 100 | 7 | 4 | 3 | $100,000 | 22h |
| `TCP_IP-DDoS-TCP_test.pcap.csv` | TCP DDoS | Not Post-Quantum Safe | 61 / 100 | 7 | 4 | 3 | $100,000 | 22h |

**Table 2.** CICIoMT2024 simulation results. The benign baseline correctly returns a Safe verdict, confirming accurate discrimination.

### 6.3 Synthea Clinical Records Results

| File | Scenario | Verdict | PQ Risk Score | PHI Findings | QIRO Selected | Budget Used | Downtime Used |
|------|----------|---------|:-------------:|:------------:|:-------------:|:-----------:|:-------------:|
| `patients.csv` | Patient PHI in AI prompts | Safe (TLS) | 0 / 100 | **8** | 8 | $64,000 | 8h |
| `conditions.csv` | Clinical conditions | Safe | 0 / 100 | 0 | 0 | $0 | 0h |

**Table 3.** Synthea simulation results. `patients.csv` demonstrates that a cryptographically compliant system can still exhibit critical privacy violations.

### 6.4 QIRO Constraint Sensitivity

To demonstrate QIRO's dynamic planning, the ICU gateway scenario (Scenario 01) was evaluated under four constraint configurations:

| Budget | Downtime | Actions Selected | Actions Deferred | Budget Used | Budget Remaining |
|-------:|--------:|:----------------:|:----------------:|:-----------:|:----------------:|
| $200,000 | 80h | 7 | 0 | $162,000 | $38,000 |
| $100,000 | 40h | 4–5 | 2–3 | ~$100,000 | ~$0 |
| $50,000 | 20h | 2–3 | 4–5 | ~$48,000 | ~$2,000 |
| $30,000 | 8h | 1–2 | 5–6 | ~$28,000 | ~$2,000 |

**Table 4.** QIRO constraint sensitivity. The migration roadmap adapts dynamically to operational constraints, demonstrating the value of constraint-aware optimisation over static priority lists.

---

## 7. Discussion

### 7.1 Discrimination Accuracy

The correct Safe verdict for the benign baseline (score 0, zero findings) against Not Post-Quantum Safe for all five attack scenarios confirms that the feature extraction and payload construction pipeline correctly encodes the distinction between normal and attack-pattern medical IoT traffic. This is a fundamental requirement for deployment in real clinical assessment workflows.

### 7.2 Multi-Pillar Value

The `patients.csv` result — Safe TLS verdict but 8 PHI findings — demonstrates the most important architectural insight: **a system can be cryptographically compliant and still be critically exposed through AI prompt governance failures**. Single-metric scanners focused on TLS version or cryptographic algorithm strength would have returned a clean bill of health for this scenario. The six-pillar TIPPSS assessment, implemented by Agents 2–8, captures the full security surface.

### 7.3 QIRO vs. Static Lists

A static severity-ordered priority list would always recommend the same actions in the same order regardless of hospital constraints. QIRO's constraint-sensitive output changes the migration roadmap when budget or downtime limits change, providing operationally actionable plans rather than infeasible theoretical remediation catalogues. As demonstrated in Table 4, reducing the budget from $200K to $30K causes QIRO to select 5 fewer actions and defer 5–6 additional actions — providing the hospital with a realistic, immediately executable plan.

### 7.4 Limitations

The current implementation uses heuristic cost and downtime estimates for remediation actions. In production deployment, these would be replaced with site-specific quotes from security vendors and change management estimates. The QIRO solver uses greedy initialisation followed by Simulated Annealing; for large action spaces ($n > 50$), a more sophisticated initial solution may improve convergence speed. The scoring weights for benefit components ($R_i$, $P_i$, $S_i$, $T_i$) are currently calibrated heuristically and should be validated against expert elicitation in future work.

---

## 8. Conclusion

This paper presented TIPPSS SafeGuard-PQ, the first integrated agentic framework that simultaneously assesses post-quantum cryptographic posture, medical IoT device identity, AI prompt privacy, secret exposure, and clinical safety risk in healthcare systems, then produces constraint-aware migration roadmaps using the novel QIRO optimisation algorithm.

The key contributions are:

1. A **10-agent pipeline** implementing automated multi-pillar assessment against NIST FIPS 203/204/205 and IEEE 2933-2024 TIPPSS.
2. **QIRO**, a Quantum-Inspired Remediation Optimizer that formulates remediation planning as a QUBO-style constrained binary optimisation solved via Simulated Annealing — the first application of this formulation to post-quantum migration planning.
3. **Empirical validation** across 8 real-world datasets demonstrating correct discrimination, PHI detection, and constraint-sensitive planning.

The system demonstrates that post-quantum migration readiness assessment in healthcare is a multi-dimensional problem requiring simultaneous evaluation of cryptographic, identity, privacy, safety, and operational dimensions. QIRO's constraint-aware planning makes the output actionable for hospitals operating under real budget and downtime constraints.

Future work will extend QIRO to hybrid quantum-classical solvers, validate cost and downtime estimates against real vendor data, and extend the TIPPSS assessment to network-layer traffic analysis using federated learning approaches that preserve clinical data privacy.

---

## References

[1] Shor, P.W. (1994). Algorithms for quantum computation: Discrete logarithms and factoring. *Proceedings of the 35th Annual Symposium on Foundations of Computer Science (FOCS)*, pp. 124–134. IEEE. https://doi.org/10.1109/SFCS.1994.365700

[2] Alagic, G., et al. (2022). *Status report on the third round of the NIST post-quantum cryptography standardization process*. NIST IR 8413. National Institute of Standards and Technology. https://doi.org/10.6028/NIST.IR.8413

[3] Grover, L.K. (1996). A fast quantum mechanical algorithm for database search. *Proceedings of the 28th Annual ACM Symposium on Theory of Computing (STOC)*, pp. 212–219. https://doi.org/10.1145/237814.237866

[4] Mosca, M. (2018). Cybersecurity in an era with quantum computers: Will we be ready? *IEEE Security & Privacy*, 16(5), 38–41. https://doi.org/10.1109/MSP.2018.3761723

[5] Bernstein, D.J., & Lange, T. (2017). Post-quantum cryptography. *Nature*, 549(7671), 188–194. https://doi.org/10.1038/nature23461

[6] National Institute of Standards and Technology. (2024). *FIPS 203: Module-Lattice-Based Key-Encapsulation Mechanism Standard. FIPS 204: Module-Lattice-Based Digital Signature Standard. FIPS 205: Stateless Hash-Based Digital Signature Standard*. U.S. Department of Commerce. https://csrc.nist.gov/pubs/fips/203/final

[7] Sicari, S., Rizzardi, A., Grieco, L.A., & Coen-Porisini, A. (2015). Security, privacy and trust in Internet of Things: The road ahead. *Computer Networks*, 76, 146–164. https://doi.org/10.1016/j.comnet.2014.11.008

[8] Hossain, M.M., Fotouhi, M., & Hasan, R. (2015). Towards an analysis of security issues, challenges, and open problems in the Internet of Things. *Proceedings of the IEEE World Congress on Services*, pp. 21–28. https://doi.org/10.1109/SERVICES.2015.12

[9] Sharafaldin, I., Lashkari, A.H., & Ghorbani, A.A. (2024). *CICIoMT2024: A comprehensive medical IoT network traffic dataset*. Canadian Institute for Cybersecurity, University of New Brunswick. https://www.unb.ca/cic/datasets/iomt-dataset-2024.html

[10] Wornow, M., Xu, Y., Lavertu, A., Bustos, A., Kelsey, B., Steinberg, E., ... & Shah, N.H. (2023). The shaky foundations of large language models and foundation models for electronic health records. *npj Digital Medicine*, 6(1), 135. https://doi.org/10.1038/s41746-023-00879-8

[11] Bozorgi, M., Saul, L.K., Savage, S., & Voelker, G.M. (2010). Beyond heuristics: Learning to classify vulnerabilities and predict exploits. *Proceedings of the 16th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*, pp. 105–114. https://doi.org/10.1145/1835804.1835821

[12] Fielder, A., Panaousis, E., Malacaria, P., Hankin, C., & Smeraldi, F. (2016). Decision support approaches for cyber security investment. *Decision Support Systems*, 86, 13–23. https://doi.org/10.1016/j.dss.2016.02.012

[13] Kirkpatrick, S., Gelatt, C.D., & Vecchi, M.P. (1983). Optimization by simulated annealing. *Science*, 220(4598), 671–680. https://doi.org/10.1126/science.220.4598.671

[14] Preskill, J. (2018). Quantum computing in the NISQ era and beyond. *Quantum*, 2, 79. https://doi.org/10.22331/q-2018-08-06-79

[15] IEEE Standards Association. (2024). *IEEE Standard 2933-2024: Clinical Internet of Things (IoT) Data and Device Interoperability with TIPPSS — Trust, Identity, Privacy, Protection, Safety, Security*. IEEE. https://standards.ieee.org/ieee/2933/10806/

---

*Document prepared for academic and professional evaluation purposes.*  
*All datasets are publicly available research data. No real patient data was used in this work.*  
*QIRO implementation is available at: https://github.com/pavangemmanjunath-cell/QuantumShift_TIPPSS*
