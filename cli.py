#!/usr/bin/env python3
"""
CLI for Kaplan-Meier Survival Estimator.

Usage:
  python cli.py analyze --time 1 2 3 4 5 --event 1 0 1 1 0
  python cli.py compare --time1 1 2 3 4 --event1 1 0 1 1 --time2 2 3 4 5 --event2 0 1 1 0
  python cli.py batch --input sample.csv --output results.csv
"""

import argparse
import json
import sys

from kaplan_meier import (
    kaplan_meier,
    log_rank_test,
    hazard_rate,
    nelson_aalen,
    summary,
    process_csv,
)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="kaplan-meier",
        description="Kaplan-Meier Survival Estimator",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- analyze ---
    p_analyze = sub.add_parser("analyze", help="Run Kaplan-Meier on a single group")
    p_analyze.add_argument(
        "--time", type=float, nargs="+", required=True,
        help="Observed times (event or censoring)"
    )
    p_analyze.add_argument(
        "--event", type=int, nargs="+", required=True,
        help="Event indicators: 1=event, 0=censored"
    )
    p_analyze.add_argument(
        "--json", action="store_true",
        help="Output as JSON instead of table"
    )

    # --- compare ---
    p_compare = sub.add_parser("compare", help="Log-rank test comparing two groups")
    p_compare.add_argument("--time1", type=float, nargs="+", required=True)
    p_compare.add_argument("--event1", type=int, nargs="+", required=True)
    p_compare.add_argument("--time2", type=float, nargs="+", required=True)
    p_compare.add_argument("--event2", type=int, nargs="+", required=True)

    # --- hazard ---
    p_hazard = sub.add_parser("hazard", help="Compute hazard rates at each event time")
    p_hazard.add_argument("--time", type=float, nargs="+", required=True)
    p_hazard.add_argument("--event", type=int, nargs="+", required=True)

    # --- batch ---
    p_batch = sub.add_parser("batch", help="Process CSV file (columns: time, event, [group])")
    p_batch.add_argument("-i", "--input", required=True, help="Input CSV path")
    p_batch.add_argument("-o", "--output", default="results.csv", help="Output CSV path")

    # --- audit ---
    p_audit = sub.add_parser("audit", help="Run a supervisor audit task via the agent suite")
    p_audit.add_argument("--task-id", default="CLI-TASK-01", help="Task identifier")
    p_audit.add_argument("--target", default="CLI-TARGET", help="Target / specimen identifier")
    p_audit.add_argument("--primary", type=float, default=10.0, help="Primary metric value")
    p_audit.add_argument("--secondary", type=float, default=2.0, help="Secondary metric value")
    p_audit.add_argument("--descriptor", default="NOMINAL", help="Status descriptor")
    p_audit.add_argument("--critical", action="store_true", help="Mark as critical")

    # --- chat ---
    p_chat = sub.add_parser("chat", help="Query the air-gapped reasoning adapter")
    p_chat.add_argument("query", nargs="+", help="Query text")

    # --- verify-audit ---
    p_verify = sub.add_parser("verify-audit", help="Verify HMAC-SHA256 audit trail integrity")

    # --- serve ---
    p_serve = sub.add_parser("serve", help="Start the FastAPI REST server")
    p_serve.add_argument("--host", default="0.0.0.0", help="Bind host")
    p_serve.add_argument("--port", type=int, default=8000, help="Bind port")

    args = parser.parse_args(argv)

    if args.command == "analyze":
        result = kaplan_meier(args.time, args.event)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(summary(args.time, args.event))
        return 0

    elif args.command == "compare":
        lr = log_rank_test(args.time1, args.event1, args.time2, args.event2)
        print("Log-Rank Test")
        print("=" * 40)
        print(f"  Chi-square statistic: {lr['statistic']}")
        print(f"  Z-score:              {lr['z_score']}")
        print(f"  P-value:              {lr['p_value']}")
        if lr["p_value"] < 0.05:
            print("  Conclusion: Significant difference (p < 0.05)")
        else:
            print("  Conclusion: No significant difference (p >= 0.05)")
        return 0

    elif args.command == "hazard":
        rates = hazard_rate(args.time, args.event)
        print(f"{'Time':>8}  {'Hazard Rate':>12}  {'Deaths':>8}  {'At Risk':>8}")
        print("-" * 42)
        for r in rates:
            print(f"{r['time']:>8.2f}  {r['hazard_rate']:>12.6f}  {r['deaths']:>8d}  {r['at_risk']:>8d}")
        return 0

    elif args.command == "batch":
        rows = process_csv(args.input, args.output)
        print(f"Processed {len(rows)} event times -> {args.output}")
        return 0

    elif args.command == "audit":
        from agents.supervisor import SystemSupervisor
        from agents.models import SystemTaskPayload

        supervisor = SystemSupervisor(model_provider="mock")
        payload = SystemTaskPayload(
            task_id=args.task_id,
            target_identifier=args.target,
            primary_metric=args.primary,
            secondary_metric=args.secondary,
            status_descriptor=args.descriptor,
            is_critical_flag=args.critical,
        )
        dossier = supervisor.process_task(payload)
        print(f"Dossier ID:    {dossier.dossier_id}")
        print(f"Urgency:       {dossier.overall_urgency.value}")
        print(f"Integrity:     {dossier.integrity_status.value}")
        print(f"Total Alerts:  {dossier.total_alerts}")
        return 0

    elif args.command == "chat":
        from agents.supervisor import SystemSupervisor

        supervisor = SystemSupervisor(model_provider="mock")
        query = " ".join(args.query)
        response = supervisor.query_supervisory_chat(query)
        print(response)
        return 0

    elif args.command == "verify-audit":
        from agents.base import AuditLogger

        valid = AuditLogger.verify_integrity()
        print(f"Audit trail integrity: {'VERIFIED' if valid else 'COMPROMISED'}")
        return 0

    elif args.command == "serve":
        from agents.api import app
        import uvicorn

        uvicorn.run(app, host=args.host, port=args.port)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
