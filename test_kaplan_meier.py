#!/usr/bin/env python3
"""
Tests for Kaplan-Meier Survival Estimator.
"""
import math
import os
import sys
import tempfile

import pytest

from kaplan_meier import (
    kaplan_meier,
    log_rank_test,
    hazard_rate,
    nelson_aalen,
    median_survival,
    summary,
    process_csv,
    _norm_cdf,
    _chi2_sf,
)


# ---------------------------------------------------------------------------
# Kaplan-Meier basic tests
# ---------------------------------------------------------------------------

class TestKaplanMeierBasic:
    def test_simple_no_censoring(self):
        """All events at times 1,2,3,4,5."""
        times = [1, 2, 3, 4, 5]
        events = [1, 1, 1, 1, 1]
        r = kaplan_meier(times, events)
        assert r["n_subjects"] == 5
        assert r["n_events"] == 5
        assert r["n_censored"] == 0
        # S(1) = 1*(1-1/5) = 0.8
        assert abs(r["survival"][0] - 0.8) < 1e-10
        # S(2) = 0.8*(1-1/4) = 0.6
        assert abs(r["survival"][1] - 0.6) < 1e-10
        # S(5) = 0
        assert abs(r["survival"][-1]) < 1e-10

    def test_all_censored(self):
        """All observations censored — no event times."""
        times = [1, 2, 3, 4, 5]
        events = [0, 0, 0, 0, 0]
        r = kaplan_meier(times, events)
        assert r["times"] == []
        assert r["survival"] == []
        assert r["median"] is None
        assert r["n_events"] == 0
        assert r["n_censored"] == 5

    def test_single_event(self):
        """Single subject with event."""
        r = kaplan_meier([5.0], [1])
        assert r["n_subjects"] == 1
        assert r["n_events"] == 1
        assert r["survival"][0] == 0.0
        assert r["median"] == 5.0

    def test_single_censored(self):
        """Single subject censored."""
        r = kaplan_meier([5.0], [0])
        assert r["n_events"] == 0
        assert r["median"] is None

    def test_mixed_censoring(self):
        """Mix of events and censoring."""
        times = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        events = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
        r = kaplan_meier(times, events)
        assert r["n_subjects"] == 10
        assert r["n_events"] == 5
        assert r["n_censored"] == 5
        assert len(r["times"]) == 5  # 5 event times
        # Survival should be monotonically non-increasing
        for i in range(1, len(r["survival"])):
            assert r["survival"][i] <= r["survival"][i - 1] + 1e-10

    def test_survival_bounded_01(self):
        """Survival probabilities should be in [0, 1]."""
        times = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        events = [1, 1, 0, 1, 0, 1, 1, 0, 1, 0]
        r = kaplan_meier(times, events)
        for s in r["survival"]:
            assert 0.0 <= s <= 1.0

    def test_empty_input_raises(self):
        """Empty input should raise ValueError."""
        with pytest.raises(ValueError):
            kaplan_meier([], [])

    def test_mismatched_lengths_raises(self):
        """Mismatched lengths should raise ValueError."""
        with pytest.raises(ValueError):
            kaplan_meier([1, 2], [1])

    def test_negative_time_raises(self):
        """Negative times should raise ValueError."""
        with pytest.raises(ValueError):
            kaplan_meier([-1, 2], [1, 0])


# ---------------------------------------------------------------------------
# Median survival
# ---------------------------------------------------------------------------

class TestMedianSurvival:
    def test_median_exact(self):
        """Median when S(t) crosses 0.5 exactly."""
        # 4 subjects, all events: S = 0.75, 0.5, 0.25, 0
        r = kaplan_meier([1, 2, 3, 4], [1, 1, 1, 1])
        assert r["median"] == 2  # S(2) = 0.5

    def test_median_between(self):
        """Median is the first time S(t) <= 0.5."""
        times = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        events = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        r = kaplan_meier(times, events)
        # S(1)=0.9, S(2)=0.8, S(3)=0.7, S(4)=0.6, S(5)=0.5
        assert r["median"] == 5

    def test_median_not_reached(self):
        """Median not reached when >50% survive."""
        times = [1, 2, 3, 4, 5]
        events = [1, 0, 0, 0, 0]
        r = kaplan_meier(times, events)
        # S(1) = 0.8 > 0.5, no more events
        assert r["median"] is None

    def test_median_survival_function(self):
        """Test the convenience function."""
        assert median_survival([1, 2, 3, 4], [1, 1, 1, 1]) == 2
        assert median_survival([1, 2, 3, 4, 5], [1, 0, 0, 0, 0]) is None


# ---------------------------------------------------------------------------
# Confidence intervals
# ---------------------------------------------------------------------------

class TestConfidenceIntervals:
    def test_ci_at_first_event(self):
        """CI should be narrow with few events."""
        times = [1, 2, 3, 4, 5]
        events = [1, 1, 1, 1, 1]
        r = kaplan_meier(times, events)
        for i in range(len(r["ci_lower"])):
            assert r["ci_lower"][i] <= r["survival"][i]
            assert r["ci_hi"][i] >= r["survival"][i]

    def test_ci_bounded(self):
        """CIs should be in [0, 1]."""
        times = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        events = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
        r = kaplan_meier(times, events)
        for lo, hi in zip(r["ci_lower"], r["ci_hi"]):
            assert 0.0 <= lo <= 1.0
            assert 0.0 <= hi <= 1.0
            assert lo <= hi

    def test_ci_narrows_with_more_data(self):
        """CI should be narrower with more subjects."""
        r_small = kaplan_meier([1, 2, 3], [1, 1, 1])
        r_large = kaplan_meier(
            [1, 1, 1, 2, 2, 2, 3, 3, 3],
            [1, 1, 1, 1, 1, 1, 1, 1, 1]
        )
        # Compare width at first event time
        w_small = r_small["ci_hi"][0] - r_small["ci_lower"][0]
        w_large = r_large["ci_hi"][0] - r_large["ci_lower"][0]
        assert w_large < w_small


# ---------------------------------------------------------------------------
# Nelson-Aalen
# ---------------------------------------------------------------------------

class TestNelsonAalen:
    def test_nelson_aalen_increasing(self):
        """Nelson-Aalen cumulative hazard should be non-decreasing."""
        times = [1, 2, 3, 4, 5]
        events = [1, 0, 1, 1, 0]
        r = kaplan_meier(times, events)
        for i in range(1, len(r["nelson_aalen"])):
            assert r["nelson_aalen"][i] >= r["nelson_aalen"][i - 1]

    def test_nelson_aalen_function(self):
        """Test the convenience function."""
        result = nelson_aalen([1, 2, 3], [1, 1, 1])
        assert len(result) == 3
        assert all("time" in r and "cumulative_hazard" in r for r in result)

    def test_nelson_aalen_all_events(self):
        """Nelson-Aalen with all events: H(t) = Σ 1/(n-i+1)."""
        times = [1, 2, 3, 4, 5]
        events = [1, 1, 1, 1, 1]
        r = kaplan_meier(times, events)
        # H(1) = 1/5 = 0.2
        assert abs(r["nelson_aalen"][0] - 0.2) < 1e-10
        # H(2) = 1/5 + 1/4 = 0.45
        assert abs(r["nelson_aalen"][1] - 0.45) < 1e-10


# ---------------------------------------------------------------------------
# Hazard rate
# ---------------------------------------------------------------------------

class TestHazardRate:
    def test_hazard_rate_nonnegative(self):
        """Hazard rates should be non-negative."""
        rates = hazard_rate([1, 2, 3, 4, 5], [1, 0, 1, 1, 0])
        for r in rates:
            assert r["hazard_rate"] >= 0

    def test_hazard_rate_structure(self):
        """Each hazard rate entry should have the right keys."""
        rates = hazard_rate([1, 2, 3], [1, 1, 0])
        for r in rates:
            assert "time" in r
            assert "hazard_rate" in r
            assert "deaths" in r
            assert "at_risk" in r


# ---------------------------------------------------------------------------
# Log-rank test
# ---------------------------------------------------------------------------

class TestLogRankTest:
    def test_identical_groups(self):
        """Identical groups should have p-value near 1."""
        times = [1, 2, 3, 4, 5]
        events = [1, 0, 1, 1, 0]
        lr = log_rank_test(times, events, times, events)
        assert lr["p_value"] > 0.5
        assert abs(lr["statistic"]) < 0.1

    def test_very_different_groups(self):
        """Very different groups should have small p-value."""
        # Group 1: all die early
        t1 = [1, 2, 3, 4, 5]
        e1 = [1, 1, 1, 1, 1]
        # Group 2: all survive long
        t2 = [10, 11, 12, 13, 14]
        e2 = [1, 1, 1, 1, 1]
        lr = log_rank_test(t1, e1, t2, e2)
        assert lr["p_value"] < 0.05

    def test_log_rank_output_keys(self):
        """Output should have statistic, p_value, z_score."""
        lr = log_rank_test([1, 2], [1, 1], [3, 4], [1, 1])
        assert "statistic" in lr
        assert "p_value" in lr
        assert "z_score" in lr

    def test_p_value_range(self):
        """p-value should be in [0, 1]."""
        lr = log_rank_test(
            [1, 2, 3, 4, 5], [1, 0, 1, 1, 0],
            [2, 3, 4, 5, 6], [0, 1, 1, 0, 1]
        )
        assert 0.0 <= lr["p_value"] <= 1.0


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

class TestSummary:
    def test_summary_output(self):
        """Summary should return a formatted string."""
        s = summary([1, 2, 3, 4, 5], [1, 0, 1, 1, 0])
        assert isinstance(s, str)
        assert "Kaplan-Meier" in s
        assert "Subjects" in s


# ---------------------------------------------------------------------------
# CSV processing
# ---------------------------------------------------------------------------

class TestCSVProcessing:
    def test_batch_process(self, tmp_path):
        """Batch CSV processing should produce output file."""
        csv_in = tmp_path / "input.csv"
        csv_out = tmp_path / "output.csv"
        csv_in.write_text(
            "time,event\n1,1\n2,0\n3,1\n4,1\n5,0\n",
            encoding="utf-8"
        )
        rows = process_csv(str(csv_in), str(csv_out))
        assert len(rows) > 0
        assert csv_out.exists()

    def test_batch_with_group(self, tmp_path):
        """Batch with group column should include log-rank results."""
        csv_in = tmp_path / "input.csv"
        csv_out = tmp_path / "output.csv"
        csv_in.write_text(
            "time,event,group\n1,1,A\n2,0,A\n3,1,A\n4,1,B\n5,0,B\n6,1,B\n",
            encoding="utf-8"
        )
        rows = process_csv(str(csv_in), str(csv_out))
        assert csv_out.exists()
        content = csv_out.read_text(encoding="utf-8")
        assert "logrank" in content


# ---------------------------------------------------------------------------
# Statistical helper functions
# ---------------------------------------------------------------------------

class TestStatHelpers:
    def test_norm_cdf(self):
        """Standard normal CDF at known values."""
        assert abs(_norm_cdf(0) - 0.5) < 1e-10
        assert abs(_norm_cdf(1.96) - 0.975) < 0.001
        assert abs(_norm_cdf(-1.96) - 0.025) < 0.001

    def test_chi2_sf(self):
        """Chi-square survival function at known values."""
        # P(X > 3.841) ≈ 0.05 for df=1
        assert abs(_chi2_sf(3.841, 1) - 0.05) < 0.005
        # P(X > 0) = 1
        assert abs(_chi2_sf(0, 1) - 1.0) < 1e-10

    def test_chi2_sf_df2(self):
        """Chi-square survival for df=2."""
        # P(X > 5.991) ≈ 0.05 for df=2
        assert abs(_chi2_sf(5.991, 2) - 0.05) < 0.005


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_tied_times(self):
        """Multiple events at the same time."""
        times = [1, 1, 1, 2, 2, 3]
        events = [1, 1, 0, 1, 0, 1]
        r = kaplan_meier(times, events)
        assert r["n_subjects"] == 6
        # At time 1: 6 at risk (all have time >= 1), 2 events -> S = 1*(1-2/6) = 2/3
        assert abs(r["survival"][0] - 2.0 / 3.0) < 1e-10

    def test_late_censoring(self):
        """Censoring after all events."""
        times = [1, 2, 3, 10, 20]
        events = [1, 1, 1, 0, 0]
        r = kaplan_meier(times, events)
        # S(1)=0.8, S(2)=0.6, S(3)=0.4 -> median = 3
        assert r["median"] == 3
        assert r["n_censored"] == 2

    def test_all_events_same_time(self):
        """All events at the same time."""
        r = kaplan_meier([5, 5, 5, 5], [1, 1, 1, 1])
        assert len(r["times"]) == 1
        assert r["survival"][0] == 0.0
        assert r["median"] == 5.0

    def test_large_dataset(self):
        """Performance test with larger dataset."""
        import random
        random.seed(42)
        n = 500
        times = [random.uniform(0.1, 100) for _ in range(n)]
        events = [random.choice([0, 1]) for _ in range(n)]
        r = kaplan_meier(times, events)
        assert r["n_subjects"] == n
        assert len(r["survival"]) > 0
