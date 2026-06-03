# TIPPSS SafeGuard-PQ

**Agentic Post-Quantum Cybersecurity Benchmark for Clinical Edge IoT and AI Healthcare Systems**

> Built in 5 days for the IEEE SA Cybersecurity Hackathon 2026.

---

## What is this?

Hospitals run hundreds of connected devices — infusion pumps, patient monitors, AI diagnostic tools — all transmitting sensitive data over encrypted networks. Today's encryption (RSA, ECDSA, AES-128) will be broken by future quantum computers within 10–15 years.

**TIPPSS SafeGuard-PQ** automatically scans a healthcare system's configuration and AI prompt logs, checks them against the new NIST post-quantum standards (FIPS 203/204/205), and outputs a prioritised remediation plan that fits the hospital's budget and downtime limits.

It does three things no existing tool does together:

| Step | What happens |
|------|-------------|
| **Detect** | 10 specialist agents scan TLS crypto, IoT device identities, EHR AI prompts, and secret exposure |
| **Benchmark** | Results are scored against NIST FIPS 203/204/205 and mapped to the IEEE 2933-2024 TIPPSS framework |
| **Prioritise** | QIRO (our novel Quantum-Inspired Remediation Optimizer) picks the best set of fixes within your budget using simulated annealing |

---

## Key Terms (plain English)

| Term | Meaning |
|------|---------|
| **TIPPSS** | Trust · Identity · Privacy · Protection · Safety · Security — the IEEE 2933-2024 framework for clinical IoT security |
| **Post-Quantum (PQ)** | Cryptography that stays secure even against quantum computers |
| **NIST FIPS 203/204/205** | The US government's new post-quantum crypto standards (ML-KEM, ML-DSA, SLH-DSA) |
| **QIRO** | Our Quantum-Inspired Remediation Optimizer — runs on a normal CPU using simulated annealing to find the cheapest set of fixes with the highest risk reduction |
| **n8n** | An open-source workflow automation tool (like Zapier for developers) that runs the 10-agent pipeline |
| **Streamlit** | A Python library that turns a script into an interactive web dashboard |

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Your Browser  (localhost:8501)                 │
│  Streamlit Dashboard                            │
│  • Scenario selector + sliders                 │
│  • Verdict banner (red → green)                │
│  • PQ Risk Gauge  |  TIPPSS Spider chart       │
│  • Findings table                              │
│  • QIRO phased migration plan                  │
└──────────────────────┬──────────────────────────┘
                       │ HTTP POST (JSON payload)
                       ▼
┌─────────────────────────────────────────────────┐
│  n8n  (localhost:5678, Docker)                  │
│                                                 │
│  Agent 1  →  Data Parser                       │
│  Agent 2  →  Crypto Inventory (TLS check)      │
│  Agent 3  →  PQ Benchmark (FIPS 203/204/205)   │
│  Agent 4  →  Clinical Privacy (PHI detection)  │
│  Agent 5  →  Device Identity (cert check)      │
│  Agent 6  →  Prompt Injection Detection        │
│  Agent 7  →  Secret Exposure Scanner          │
│  Agent 8  →  Safety Risk (unsafe AI commands) │
│  Agent 9  →  TIPPSS Mapping                   │
│  Agent 10 →  QIRO Optimizer (simulated anneal)│
│                                                 │
│  IF score > 75 → Claude Sonnet 4.6 report      │
└──────────────────────┬──────────────────────────┘
                       │ HTTPS (critical cases only)
                       ▼
┌─────────────────────────────────────────────────┐
│  Anthropic Claude API                           │
│  Generates executive remediation report         │
│  for the hospital CISO                          │
└─────────────────────────────────────────────────┘
```

---

## Files in this repository

| File | Purpose |
|------|---------|
| `dashboard.py` | Streamlit web dashboard — all charts and UI |
| `test_scenarios.json` | 4 pre-built test cases (Critical → Safe) for demo |
| `requirements.txt` | Python dependencies |
| `run.bat` | Windows one-click launcher |
| `run.sh` | Mac / Linux launcher |
| `.gitignore` | Keeps secrets and the venv out of git |

---

## Prerequisites

Before you start, make sure you have:

- **Python 3.10 or newer** — [download here](https://www.python.org/downloads/) (tick "Add Python to PATH" during install)
- **Docker Desktop** — [download here](https://www.docker.com/products/docker-desktop/)
- **n8n container** running on port 5678 with the TIPPSS v3 workflow imported and **toggled Active**
- **Anthropic API key** entered in the "Claude API: Generate Report" n8n node (only needed for Critical-risk cases)

---

## Quick Start — Windows

### Step 1 — Download the code

Clone this repository or download and unzip it:

```
git clone https://github.com/<your-username>/TIPPSS-SafeGuard-PQ.git
cd TIPPSS-SafeGuard-PQ
```

### Step 2 — Double-click `run.bat`

A terminal window will open and automatically:
1. Create a Python virtual environment (`venv/` folder)
2. Install all dependencies (~30 seconds on first run)
3. Launch the dashboard at **http://localhost:8501**

Subsequent runs skip the install and start in seconds.

> **If you see a pip upgrade error** on older Python versions, the launcher already handles this by calling `python -m pip install --upgrade pip` instead of `pip install --upgrade pip`. If it still fails, right-click `run.bat` → "Run as administrator".

### Step 3 — Use the dashboard

1. In the left sidebar, pick **"ICU-GW-01 (Critical Risk)"**
2. Leave budget and downtime sliders at their defaults
3. Click **Run Assessment**
4. Watch the dashboard show a red Critical verdict, TIPPSS spider chart, findings table, and QIRO migration plan
5. Switch to **"NEXTGEN-EDGE-GW (PQ Safe)"** and run again — it goes green

---

## Quick Start — Mac / Linux

```bash
chmod +x run.sh
./run.sh
```

Same behaviour: creates venv, installs deps, opens http://localhost:8501.

---

## Dashboard Sections Explained

### 1. Verdict Banner
A full-width coloured card at the top.

| Score | Colour | Verdict |
|-------|--------|---------|
| 0–25 | Green | Safe |
| 26–50 | Yellow | Partially Safe |
| 51–75 | Orange | Not Post-Quantum Safe |
| 76–100 | Red | Critical Quantum Risk |

### 2. PQ Risk Gauge
A semicircle gauge (0–100) with a needle showing the weighted risk score. The score is calculated from 6 categories: classical key exchange, deprecated TLS, data lifetime exposure, device identity, secrets, and migration status.

### 3. TIPPSS Spider Chart
A radar / spider chart with 6 axes — one per TIPPSS pillar. A fully-filled polygon means all 6 pillars score 100 (safe). Missing corners expose which security dimension needs work.

### 4. Findings Table
Every issue detected by the 10 agents, sortable by severity. Icons: 🔴 Critical · 🟠 High · 🟡 Medium · 🟢 Low.

### 5. QIRO Migration Plan ⭐ (Novel Contribution)
- **4 metric cards** — how many actions selected, total cost, total downtime, total risk reduction
- **Horizontal bar chart** — actions ranked by risk reduction
- **3-phase plan** — Phase 1 (0–6 mo) · Phase 2 (6–18 mo) · Phase 3 (18–36 mo)
- **Algorithm details expander** — mentions Simulated Annealing (Kirkpatrick 1983), QUBO formulation, iteration count, final temperature

### 6. Claude Executive Report
For systems scoring > 75, Claude Sonnet 4.6 writes a 400-word narrative for the hospital CISO covering the verdict, top 3 priority actions, NIST migration recommendations, and the phased timeline.

### 7. Raw JSON (expandable)
The full n8n pipeline response — useful for judges who want to see the data behind the charts.

---

## Upload Your Own Data (Advanced)

In the sidebar you can upload a CSV file instead of using a built-in test case. Two formats are supported:

| Format | How to get it |
|--------|--------------|
| **Synthea `patients.csv`** | Run [Synthea](https://github.com/synthetichealth/synthea) locally to generate synthetic patient records |
| **CICIoMT2024 `*.pcap.csv`** | Download the [CIC IoMT 2024 dataset](https://www.unb.ca/cic/datasets/iomt-dataset-2024.html) from UNB |

The dashboard auto-detects the CSV type, samples up to 100 rows, and builds an n8n payload automatically.

---

## How the QIRO Optimizer Works

QIRO frames remediation as a **constrained binary optimisation problem**:

- Each finding maps to a remediation action (x = 0 = skip, x = 1 = apply)
- **Objective**: maximise risk reduction + PQC urgency + safety criticality + TIPPSS weight
- **Constraints**: total cost ≤ budget, total downtime ≤ max allowed
- **Penalty**: large cost added when constraints are violated

This is equivalent to a **QUBO (Quadratic Unconstrained Binary Optimization)** problem, the same class of problem targeted by quantum annealers like D-Wave. QIRO solves it on a classical CPU using **Simulated Annealing** (Kirkpatrick et al., 1983) with a geometric cooling schedule (α = 0.995) and Metropolis-Hastings acceptance.

> **Important**: QIRO runs on a normal CPU. It is *quantum-inspired*, not quantum hardware.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Cannot reach n8n at http://localhost:5678` | n8n Docker container is stopped — restart it in Docker Desktop |
| Nothing loads at `localhost:8501` | Wait 10 seconds after the terminal says "Starting dashboard..." |
| `qiro_optimization` missing from response | Wrong workflow version imported — re-import the v3 JSON |
| `401 Unauthorized` in n8n logs | Claude API key is wrong — re-copy from console.anthropic.com |
| `402 Payment Required` | Add credit at Anthropic Console → Settings → Billing |
| Dashboard stuck on "Running..." | Open n8n Executions tab to see which agent failed |
| pip upgrade error on first run | Right-click `run.bat` → "Run as administrator" |
| `venv` creation fails | Delete the `venv/` folder and run `run.bat` again |

---

## Standards and References

| Standard | Description |
|----------|-------------|
| **NIST FIPS 203** | ML-KEM (Kyber) — post-quantum key encapsulation |
| **NIST FIPS 204** | ML-DSA (Dilithium) — post-quantum digital signatures |
| **NIST FIPS 205** | SLH-DSA (SPHINCS+) — stateless hash-based signatures |
| **IEEE 2933-2024** | Clinical IoT Trust framework (TIPPSS pillars) |
| **OWASP LLM Top-10** | Prompt injection and LLM risk patterns |
| **Kirkpatrick et al., 1983** | Simulated Annealing — *Science* 220(4598) |

---

## Recommended Demo (3 Minutes)

| Time | Action |
|------|--------|
| 0:00–0:30 | Show the empty dashboard and explain the honest disclaimer banner |
| 0:30–1:30 | Run **"ICU-GW-01 (Critical Risk)"** — red verdict, risk gauge at 78, spider chart with gaps |
| 1:30–2:30 | Scroll to QIRO — show 5 of 12 actions selected, $78K of $100K budget, 3-phase plan |
| 2:30–3:00 | Switch to **"NEXTGEN-EDGE-GW (PQ Safe)"** — green verdict, fully-filled spider, QIRO selects 0 actions |

---

## Honest Framing

This is a **5-day hackathon prototype**. When asked by judges:

- It uses **synthetic data only** — no real hospital networks or patient records were tested
- QIRO runs on a **classical CPU** — not a quantum computer or QPU
- Scoring weights are **heuristic** defaults; cost/downtime figures are illustrative
- We benchmark systems *against* NIST PQ standards; we do not modify the standards

---

## Contributing / Running Locally Without Docker

If you want to run without n8n (for development), the dashboard will show an error when you click "Run Assessment" because it can't reach localhost:5678. You can test the UI by returning mock JSON from a local Flask server — see `test_scenarios.json` for the expected response shape.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*© 2026 TIPPSS SafeGuard-PQ Team · IEEE SA Cybersecurity Hackathon 2026*
