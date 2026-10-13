#!/usr/bin/env python3
"""
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
"""

import math
import csv
from typing import List, Dict, Any, Optional


# ---------------------------------------------------------------------------
# Core Kaplan-Meier estimator
# ---------------------------------------------------------------------------

def kaplan_meier(times: List[float], events: List[int]) -> Dict[str, Any]:
    """
    Compute the Kaplan-Meier survival estimate.

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
    """
    if len(times) != len(events):
        raise ValueError("times and events must have the same length")
    if len(times) == 0:
        raise ValueError("At least one observation is required")
    for t in times:
        if isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t) or t < 0:
            raise ValueError("Times must be finite non-negative numbers")
    for e in events:
        if isinstance(e, bool) or e not in (0, 1):
            raise ValueError("Events must be 0 (censored) or 1 (event)")

    n = len(times)

    # Sort by time
    paired = sorted(zip(times, events), key=lambda x: x[0])
    sorted_times = [p[0] for p in paired]
    sorted_events = [p[1] for p in paired]

    # Identify unique event times (where at least one event occurs)
    unique_times_set = set()
    for t, e in zip(sorted_times, sorted_events):
        if e == 1:
            unique_times_set.add(t)
    event_times = sorted(unique_times_set)

    if not event_times:
        # All observations censored
        return {
            "times": [],
            "survival": [],
            "at_risk": [],
            "deaths": [],
            "censored": [],
            "median": None,
            "nelson_aalen": [],
            "greenwood_var": [],
            "ci_lower": [],
            "ci_upper": [],
            "ci_hi": [],
            "n_subjects": n,
            "n_events": 0,
            "n_censored": n,
        }

    # Build counts at each event time
    surv = []
    at_risk_list = []
    deaths_list = []
    censored_list = []
    na_hazard = []  # Nelson-Aalen cumulative hazard
    gw_var = []     # Greenwood variance
    ci_lo = []
    ci_hi = []

    s = 1.0  # current survival
    cum_hazard = 0.0  # Nelson-Aalen cumulative hazard
    cum_var = 0.0     # cumulative Greenwood variance
    remaining = n     # number still at risk

    # Pre-compute: for each unique time, how many deaths and censored
    death_counts = {}
    censor_counts = {}
    for t, e in zip(sorted_times, sorted_events):
        if e == 1:
            death_counts[t] = death_counts.get(t, 0) + 1
        else:
            censor_counts[t] = censor_counts.get(t, 0) + 1

    # Process all unique times in order (including censoring-only times for at-risk tracking)
    # We need to track at-risk at each event time
    # First, compute number at risk at each event time
    # n_i = number of subjects with time >= event_time
    idx = 0  # pointer into sorted data

    for et in event_times:
        # Count at risk: subjects with time >= et
        # (subjects still alive and uncensored just before et)
        # n_i = number of subjects with observed time >= et
        while idx < n and sorted_times[idx] < et:
            idx += 1
        n_i = n - idx

        d_i = death_counts.get(et, 0)
        c_i = censor_counts.get(et, 0)

        # Survival update
        if n_i > 0:
            s *= (1.0 - d_i / n_i)
        surv.append(s)

        at_risk_list.append(n_i)
        deaths_list.append(d_i)
        censored_list.append(c_i)

        # Nelson-Aalen: H(t) = Σ di/ni
        if n_i > 0:
            cum_hazard += d_i / n_i
        na_hazard.append(cum_hazard)

        # Greenwood variance: Var(S(t)) = S(t)^2 * Σ di/(ni*(ni-di))
        if n_i > 0 and (n_i - d_i) > 0:
            cum_var += d_i / (n_i * (n_i - d_i))
        gw_var.append(s * s * cum_var)

        # Log-log confidence interval
        # Using: CI = S(t)^{exp(±z * se(ln(-ln(S(t)))) / ln(S(t)))}
        # where se(ln(-ln(S(t)))) = sqrt(Var(S(t))) / (|ln(S(t))| * S(t))
        z = 1.96  # 95% CI
        if 0 < s < 1:
            ln_s = math.log(s)
            # Delta-method standard error for log(-log(S)), using Greenwood's sum.
            se_lnln = math.sqrt(cum_var) / abs(ln_s)
            g = math.log(-ln_s)
            g_lo = g - z * se_lnln
            g_hi = g + z * se_lnln
            ci_lo_val = math.exp(-math.exp(g_hi))
            ci_hi_val = math.exp(-math.exp(g_lo))
        elif s == 1.0:
            ci_lo_val = 1.0
            ci_hi_val = 1.0
        else:
            ci_lo_val = 0.0
            ci_hi_val = 0.0

        ci_lo.append(max(0.0, min(1.0, ci_lo_val)))
        ci_hi.append(max(0.0, min(1.0, ci_hi_val)))

    # Median survival: smallest t where S(t) <= 0.5
    median = None
    for i, s_val in enumerate(surv):
        if s_val <= 0.5:
            median = event_times[i]
            break

    return {
        "times": event_times,
        "survival": surv,
        "at_risk": at_risk_list,
        "deaths": deaths_list,
        "censored": censored_list,
        "median": median,
        "nelson_aalen": na_hazard,
        "greenwood_var": gw_var,
        "ci_lower": ci_lo,
        "ci_hi": ci_hi,
        "ci_upper": ci_hi,
        "n_subjects": n,
        "n_events": sum(events),
        "n_censored": n - sum(events),
    }


def median_survival(times: List[float], events: List[int]) -> Optional[float]:
    """Return the median survival time, or None if not reached."""
    result = kaplan_meier(times, events)
    return result["median"]


def hazard_rate(times: List[float], events: List[int]) -> List[Dict[str, float]]:
    """
    Compute the hazard rate at each event time.
    h(ti) = di / (ni * Δti)  where Δti = ti - t_{i-1}
    """
    result = kaplan_meier(times, events)
    et = result["times"]
    d = result["deaths"]
    n = result["at_risk"]

    rates = []
    for i in range(len(et)):
        dt = et[i] - (et[i - 1] if i > 0 else 0.0)
        if dt > 0 and n[i] > 0:
            rate = d[i] / (n[i] * dt)
        else:
            rate = 0.0
        rates.append({"time": et[i], "hazard_rate": rate, "deaths": d[i], "at_risk": n[i]})
    return rates


def nelson_aalen(times: List[float], events: List[int]) -> List[Dict[str, float]]:
    """Return Nelson-Aalen cumulative hazard at each event time."""
    result = kaplan_meier(times, events)
    return [
        {"time": t, "cumulative_hazard": h}
        for t, h in zip(result["times"], result["nelson_aalen"])
    ]


# ---------------------------------------------------------------------------
# Log-rank test
# ---------------------------------------------------------------------------

def log_rank_test(
    times1: List[float], events1: List[int],
    times2: List[float], events2: List[int],
) -> Dict[str, float]:
    """
    Log-rank test comparing two survival curves.

    Returns
    -------
    dict with keys:
        statistic : chi-square test statistic
        p_value   : p-value (approximation using chi-square with 1 df)
        z_score   : z-score (signed)
    """
    # Validate both groups, including sizes, event codes and finite times.
    kaplan_meier(times1, events1)
    kaplan_meier(times2, events2)

    # Combine and sort all unique event times
    all_times = sorted(set(
        [t for t, e in zip(times1, events1) if e == 1] +
        [t for t, e in zip(times2, events2) if e == 1]
    ))

    if not all_times:
        return {"statistic": 0.0, "p_value": 1.0, "z_score": 0.0}

    n1 = len(times1)
    n2 = len(times2)

    # Pre-sort
    sorted1 = sorted(zip(times1, events1), key=lambda x: x[0])
    sorted2 = sorted(zip(times2, events2), key=lambda x: x[0])
    t1_list = [p[0] for p in sorted1]
    e1_list = [p[1] for p in sorted1]
    t2_list = [p[0] for p in sorted2]
    e2_list = [p[1] for p in sorted2]

    O_minus_E = 0.0
    V = 0.0

    for ti in all_times:
        # At risk just before ti
        n1i = sum(1 for t in t1_list if t >= ti)
        n2i = sum(1 for t in t2_list if t >= ti)
        ni = n1i + n2i

        # Observed events at ti
        d1i = sum(1 for t, e in zip(t1_list, e1_list) if t == ti and e == 1)
        d2i = sum(1 for t, e in zip(t2_list, e2_list) if t == ti and e == 1)
        di = d1i + d2i

        if ni == 0 or ni == 1:
            continue

        # Expected events in group 1
        e1i = n1i * di / ni if ni > 0 else 0

        O_minus_E += (d1i - e1i)
        # Variance: hypergeometric variance
        # V = (n1i * n2i * di * (ni - di)) / (ni^2 * (ni - 1))
        if ni > 1:
            V += (n1i * n2i * di * (ni - di)) / (ni * ni * (ni - 1))

    if V == 0:
        return {"statistic": 0.0, "p_value": 1.0, "z_score": 0.0}

    chi_sq = (O_minus_E ** 2) / V
    z = O_minus_E / math.sqrt(V)

    # p-value from chi-square with 1 df: P(X > chi_sq)
    # Using survival function of chi-square(1) = 2 * (1 - Phi(sqrt(chi_sq)))
    p_value = _chi2_sf(chi_sq, 1)

    return {
        "statistic": round(chi_sq, 4),
        "p_value": p_value,
        "z_score": round(z, 4),
    }


# ---------------------------------------------------------------------------
# CSV batch processing
# ---------------------------------------------------------------------------

def process_csv(input_path: str, output_path: str) -> List[Dict[str, Any]]:
    """
    Process a CSV file with columns: time, event (and optionally group).
    If 'group' column exists, performs group comparison with log-rank test.
    """
    with open(input_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    # Determine column names
    time_col = _find_col(fieldnames, ["time", "survival_time", "days", "months", "t"])
    event_col = _find_col(fieldnames, ["event", "status", "dead", "e"])
    group_col = _find_col(fieldnames, ["group", "treatment", "arm", "cohort"], required=False)
    if not rows:
        raise ValueError("CSV must contain at least one observation")

    times = [float(r[time_col]) for r in rows]
    events = [float(r[event_col]) for r in rows]

    result = kaplan_meier(times, events)

    # Build output
    out_fields = [
        "km_time", "km_survival", "km_at_risk", "km_deaths",
        "km_ci_lower", "km_ci_upper", "km_nelson_aalen",
        "km_median", "km_n_subjects", "km_n_events"
    ]

    out_rows = []
    # One row per event time
    for i, t in enumerate(result["times"]):
        row = {}
        row["km_time"] = str(t)
        row["km_survival"] = str(round(result["survival"][i], 6))
        row["km_at_risk"] = str(result["at_risk"][i])
        row["km_deaths"] = str(result["deaths"][i])
        row["km_ci_lower"] = str(round(result["ci_lower"][i], 6))
        row["km_ci_upper"] = str(round(result["ci_hi"][i], 6))
        row["km_nelson_aalen"] = str(round(result["nelson_aalen"][i], 6))
        row["km_median"] = str(result["median"]) if result["median"] is not None else "NR"
        row["km_n_subjects"] = str(result["n_subjects"])
        row["km_n_events"] = str(result["n_events"])
        out_rows.append(row)

    # If group column exists, add log-rank test results
    if group_col:
        groups = set(r[group_col] for r in rows)
        if len(groups) == 2:
            g1, g2 = sorted(groups)
            t1 = [float(r[time_col]) for r in rows if r[group_col] == g1]
            e1 = [float(r[event_col]) for r in rows if r[group_col] == g1]
            t2 = [float(r[time_col]) for r in rows if r[group_col] == g2]
            e2 = [float(r[event_col]) for r in rows if r[group_col] == g2]
            lr = log_rank_test(t1, e1, t2, e2)
            out_fields += ["logrank_statistic", "logrank_p_value", "logrank_z_score"]
            for row in out_rows:
                row["logrank_statistic"] = str(lr["statistic"])
                row["logrank_p_value"] = str(lr["p_value"])
                row["logrank_z_score"] = str(lr["z_score"])

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(out_rows)

    return out_rows


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_col(fieldnames: List[str], candidates: List[str], required: bool = True) -> Optional[str]:
    """Find a column name from candidates (case-insensitive)."""
    lower_map = {c.lower(): c for c in fieldnames}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    if required:
        raise ValueError(f"Missing required CSV column: expected one of {', '.join(candidates)}")
    return None


def _chi2_sf(x: float, df: int) -> float:
    """
    Survival function (1-CDF) of chi-square distribution.
    For df=1: P(X>x) = 2*(1 - Phi(sqrt(x))) where Phi is standard normal CDF.
    Uses the error function approximation.
    """
    if x <= 0:
        return 1.0
    if df == 1:
        return math.erfc(math.sqrt(x / 2.0))
    elif df == 2:
        return math.exp(-x / 2.0)
    else:
        # For general df, use the regularized incomplete gamma function
        return 1.0 - _gamma_inc_reg(df / 2.0, x / 2.0)


def _norm_cdf(x: float) -> float:
    """Standard normal CDF using error function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _gamma_inc_reg(a: float, x: float) -> float:
    """
    Regularized lower incomplete gamma function P(a, x) via series expansion.
    P(a, x) = gamma_inc(a, x) / Gamma(a)
    """
    if x < 0:
        return 0.0
    if x == 0:
        return 0.0

    # Series expansion
    itmax = 200
    eps = 1e-12

    if x < a + 1.0:
        # Series representation
        ap = a
        total = 1.0 / a
        term = 1.0 / a
        for n in range(1, itmax + 1):
            ap += 1.0
            term *= x / ap
            total += term
            if abs(term) < abs(total) * eps:
                break
        return total * math.exp(-x + a * math.log(x) - _log_gamma(a))
    else:
        # Continued fraction (Lentz's method)
        return 1.0 - _gamma_inc_cf(a, x)


def _gamma_inc_cf(a: float, x: float) -> float:
    """Upper incomplete gamma via continued fraction."""
    itmax = 200
    eps = 1e-12
    fpmin = 1e-30

    b = x + 1.0 - a
    c = 1.0 / fpmin
    d = 1.0 / b
    h = d
    for i in range(1, itmax + 1):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < fpmin:
            d = fpmin
        c = b + an / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return math.exp(-x + a * math.log(x) - _log_gamma(a)) * h


def _log_gamma(x: float) -> float:
    """Log of gamma function using Stirling/Lanczos approximation."""
    if x < 0.5:
        return math.log(math.pi / math.sin(math.pi * x)) - _log_gamma(1.0 - x)
    x -= 1.0
    g = 7
    c = [
        0.99999999999980993,
        676.5203681218851,
        -1259.1392167224028,
        771.32342877765313,
        -176.61502916214059,
        12.507343278686905,
        -0.13857109526572012,
        9.9843695780195716e-6,
        1.5056327351493116e-7,
    ]
    total = c[0]
    for i in range(1, g + 2):
        total += c[i] / (x + i)
    st = x + g + 0.5
    return 0.5 * math.log(2.0 * math.pi) + (x + 0.5) * math.log(st) - st + math.log(total)


# ---------------------------------------------------------------------------
# Summary / display helpers
# ---------------------------------------------------------------------------

def summary(times: List[float], events: List[int]) -> str:
    """Return a formatted summary of the Kaplan-Meier analysis."""
    r = kaplan_meier(times, events)
    lines = []
    lines.append("Kaplan-Meier Survival Analysis")
    lines.append("=" * 50)
    lines.append(f"  Subjects:    {r['n_subjects']}")
    lines.append(f"  Events:      {r['n_events']}")
    lines.append(f"  Censored:    {r['n_censored']}")
    med = r["median"]
    lines.append(f"  Median:      {med if med is not None else 'Not reached'}")
    lines.append("")
    lines.append(f"  {'Time':>8}  {'S(t)':>8}  {'At Risk':>8}  {'Deaths':>8}  {'95% CI':>16}  {'H(t)':>10}")
    lines.append("  " + "-" * 70)
    for i in range(len(r["times"])):
        ci = f"[{r['ci_lower'][i]:.4f}, {r['ci_hi'][i]:.4f}]"
        lines.append(
            f"  {r['times'][i]:>8.2f}  {r['survival'][i]:>8.4f}  "
            f"{r['at_risk'][i]:>8d}  {r['deaths'][i]:>8d}  {ci:>16s}  {r['nelson_aalen'][i]:>10.4f}"
        )
    return "\n".join(lines)
