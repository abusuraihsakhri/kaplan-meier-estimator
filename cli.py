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

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
