# Kaplan Meier Estimator

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Reference Guidelines & Standards:** `Standard Clinical Formulations & ISO/IEC Quality Frameworks`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

Kaplan-Meier Survival Estimator

Real implementation of:
  - Survival function: S(t) = Π(ti≤t) (1 - di/ni)
  - Censored data handling
  - Median survival time (S(t) = 0.5)
  - Confidence intervals (log-log / Greenwood method)
  - Log-rank test for comparing two curves
  - Hazard rate estimation
  - Nelson-Aalen cumulative hazard

Pure Python stdlib — no external dependencies.

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Analytical Functions

- **`kaplan_meier()`**: Compute the Kaplan-Meier survival estimate.

Parameters
----------
times : list of float
    Observed times (event or censoring).
events : list of int
    Event indicators: 1 = event (death), 0 = censored.

Returns
-------
dict with keys:
    times       – unique event times (where events occur)
    survival    – S(t) at each event time
    at_risk     – number at risk just before each event time
    deaths      – number of events at each event time
    censored    – number censored at each event time
    median      – median survival time (or None)
    nelson_aalen – Nelson-Aalen cumulative hazard at each event time
    greenwood_var – Greenwood variance of S(t) at each event time
    ci_lower    – lower 95% CI (log-log method)
    ci_upper    – upper 95% CI (log-log method)
- **`median_survival()`**: Return the median survival time, or None if not reached.
- **`hazard_rate()`**: Compute the hazard rate at each event time.
h(ti) = di / (ni * Δti)  where Δti = ti - t_{i-1}
- **`nelson_aalen()`**: Return Nelson-Aalen cumulative hazard at each event time.
- **`log_rank_test()`**: Log-rank test comparing two survival curves.

Returns
-------
dict with keys:
    statistic : chi-square test statistic
    p_value   : p-value (approximation using chi-square with 1 df)
    z_score   : z-score (signed)

---

## 📐 Mathematical Formulation

**Survival function** — product-limit estimator:

```
S(t) = ∏(ti ≤ t) (1 - di/ni)
```

where `di` is the number of events at time `ti` and `ni` is the number at risk just before `ti`.

**Nelson-Aalen cumulative hazard:**

```
H(t) = Σ(di/ni)
```

**Greenwood variance of S(t):**

```
Var(S(t)) = S(t)² · Σ di/(ni·(ni - di))
```

**Log-log 95% confidence interval** — transform via `g = ln(-ln(S(t)))`, compute `se(g)`, then map back:

```
CI = exp(-exp(g ± 1.96 · se(g)))
```

**Log-rank test** — compares two groups using the hypergeometric variance of observed minus expected events across all unique event times, yielding a chi-square statistic (1 df) and signed z-score.

---

## 💻 CLI Quickstart & Usage

The CLI is structured as subcommands:

```bash
# Analyze a single group (table output)
python cli.py analyze --time 1 2 3 4 5 --event 1 0 1 1 0

# Analyze with JSON output
python cli.py analyze --time 1 2 3 4 5 --event 1 0 1 1 0 --json

# Log-rank test comparing two groups
python cli.py compare --time1 1 2 3 4 --event1 1 0 1 1 --time2 2 3 4 5 --event2 0 1 1 0

# Hazard rates at each event time
python cli.py hazard --time 1 2 3 4 5 --event 1 0 1 1 0

# Batch CSV processing (columns: time, event, [group])
python cli.py batch --input sample.csv --output results.csv
```

### CSV Input Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `time` | Observation time (event or censoring) | Required |
| `event` | Event indicator: 1 = event, 0 = censored | Required |
| `group` | Group label for log-rank comparison | Optional |

The `time` and `event` column names are auto-detected (aliases: `survival_time`, `days`, `months`, `status`, `censored`, etc.). When a `group` column is present with exactly two groups, a log-rank test is appended to the output.

### Agent & Audit Commands

```bash
# Run a supervisor audit task
python cli.py audit --task-id T1 --primary 29.4 --descriptor DISCORDANT_ANOMALY --critical

# Query the air-gapped reasoning adapter
python cli.py chat "Explain survival analysis assumptions"

# Verify HMAC-SHA256 audit trail integrity
python cli.py verify-audit

# Start the FastAPI REST server
python cli.py serve --host 0.0.0.0 --port 8000
```

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py 1000
```

---

## 🐳 Container Deployment

```bash
docker build -t kaplan-meier-estimator .
docker run -p 8000:8000 kaplan-meier-estimator
```
