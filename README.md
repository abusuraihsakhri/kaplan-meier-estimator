# Kaplan–Meier Survival Estimator

A survival-analysis toolkit for right-censored event-time data. It provides a standalone browser interface, a dependency-free Python statistical core, a CLI, and optional FastAPI endpoints.

## Browser application

Open the file web/index.html in a modern browser, or serve the directory:

~~~bash
python -m http.server 8080 --directory web
~~~

Open http://localhost:8080. CSV processing, charting and exports occur in the browser. The browser does not send datasets to a server. **Do not include patient identifiers.** A public GitHub Pages deployment is configured in .github/workflows/pages.yml and should be verified after deployment.

The interface supports:

- CSV import or paste (columns: time, event, and optional group; UTF-8, up to two groups).
- Product-limit Kaplan–Meier survival curves and censoring marks.
- Greenwood-based log–log 95% confidence limits.
- Median survival when the estimated probability first falls to 0.5 or below.
- Two-sided log-rank comparison for two independent groups.
- CSV export of event-time estimates (without original observation columns).

The event indicator is **1 = event** and **0 = right-censored**. Tied events are processed before censoring at the same observed time. Non-finite/negative times, invalid events, and missing required columns are rejected.

## Python CLI

Requires Python 3.10+. Install from the checkout:

~~~bash
python -m pip install -e .
kaplan-meier analyze --time 1 2 3 4 5 --event 1 0 1 1 0 --json
kaplan-meier compare --time1 1 2 3 --event1 1 1 0 --time2 2 3 4 --event2 0 1 1
kaplan-meier hazard --time 1 2 3 --event 1 0 1
kaplan-meier batch --input sample.csv --output results.csv
~~~

The core module kaplan_meier.py uses Python's standard library. Its public functions are kaplan_meier, median_survival, nelson_aalen, hazard_rate, log_rank_test, and process_csv. Batch export returns event-time summaries, not patient-level data.

## Statistical methods

The product-limit estimator is **S(t) = ∏ (1 − dᵢ/nᵢ)** over event times. At each event time, nᵢ is the at-risk set (including people censored at that time) and dᵢ is the event count.

Greenwood variance is **S(t)² Σ dᵢ/[nᵢ(nᵢ−dᵢ)]**. Confidence intervals use the complementary log–log transformation at nonboundary estimates, with a 95% standard normal quantile. At S(t) = 0 or 1, the implementation returns degenerate boundary intervals. Nelson–Aalen cumulative hazard is **Σ dᵢ/nᵢ**. Two-group log-rank testing uses the hypergeometric variance at pooled event times and a chi-square distribution with one degree of freedom. This is an unadjusted comparison; it does not address confounding or competing risks.

## REST API and Docker

~~~bash
kaplan-meier serve --host 127.0.0.1 --port 8000
# Or:
docker compose up --build
~~~

FastAPI exposes /api/kaplan-meier, /api/log-rank, /health, and interactive OpenAPI docs at /docs. Example request:

~~~bash
curl -X POST http://127.0.0.1:8000/api/kaplan-meier -H 'Content-Type: application/json' -d '{"times":[1,2,3,4],"events":[1,0,1,1]}'
~~~

When launched from a checkout or Docker, the server also serves the browser interface at /. Existing /api/audit, /api/chat, /api/audit/logs, and /metrics endpoints and agent CLI commands remain available, but the supervisory agents use generic demonstration rules and a deterministic mock reasoning adapter, **not a validated clinical model**. /metrics returns JSON, not Prometheus text.

**Security limitations:** The server has no built-in authentication or authorization. PHI-detection patterns are heuristic and cannot establish de-identification or regulatory compliance. Audit HMACs authenticate the in-memory chain during a process lifetime; the audit trail is not durably persisted. Do not expose the API to untrusted networks or submit identifiable clinical data.

## Tests and development

~~~bash
python -m pip install -e ".[dev]"
python -m pytest -q
node --check web/app.js
node --test web/test-app.cjs
~~~

The Node test runner (Node.js 18+) requires no npm packages. GitHub Actions checks Python versions 3.10, 3.11, and 3.12 and runs browser-algorithm regression tests. Front-end assets have no third-party runtime dependencies.

## License

MIT; see [LICENSE](LICENSE).
