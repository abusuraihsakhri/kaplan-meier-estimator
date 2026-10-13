"""Regression tests for statistical validation, CSV schema and audit authentication."""
import csv
import math
import pytest
from kaplan_meier import kaplan_meier, log_rank_test, process_csv
from agents.base import AuditTrail


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), -1])
def test_invalid_survival_times(value):
    with pytest.raises(ValueError):
        kaplan_meier([value], [1])


@pytest.mark.parametrize("events", [[0.5], [2], [-1]])
def test_invalid_event_codes(events):
    with pytest.raises(ValueError):
        kaplan_meier([1], events)


def test_log_rank_rejects_unvalidated_groups():
    with pytest.raises(ValueError):
        log_rank_test([1, 2], [1], [1], [1])
    with pytest.raises(ValueError):
        log_rank_test([float("nan")], [1], [1], [1])


def test_greenwood_loglog_ci_alias():
    result = kaplan_meier([1, 2, 3, 4], [1, 1, 1, 1])
    assert result["ci_upper"] == result["ci_hi"]
    assert result["ci_lower"][0] <= result["survival"][0] <= result["ci_upper"][0]
    censored = kaplan_meier([1], [0])
    assert censored["ci_upper"] == []


def test_csv_requires_explicit_columns(tmp_path):
    infile, outfile = tmp_path / "data.csv", tmp_path / "out.csv"
    infile.write_text("time,age\n1,32\n", encoding="utf-8")
    with pytest.raises(ValueError, match="event"):
        process_csv(str(infile), str(outfile))
    assert not outfile.exists()


def test_csv_rejects_fractional_events(tmp_path):
    infile, outfile = tmp_path / "data.csv", tmp_path / "out.csv"
    infile.write_text("time,event\n1,0.9\n", encoding="utf-8")
    with pytest.raises(ValueError):
        process_csv(str(infile), str(outfile))


def test_csv_export_contains_only_aggregate_data(tmp_path):
    infile, outfile = tmp_path / "data.csv", tmp_path / "out.csv"
    infile.write_text("time,event,patient_id\n1,1,patient-A\n2,0,patient-B\n", encoding="utf-8")
    process_csv(str(infile), str(outfile))
    result = outfile.read_text(encoding="utf-8")
    assert "patient-A" not in result
    assert "patient_id" not in result
    assert "km_time" in result


def test_audit_detects_entry_mutation():
    audit = AuditTrail(secret_key="test-key")
    audit.log("runner", "unit", "EVENT", {"state":"ok"})
    assert audit.verify_integrity()
    audit.logs[0]["actor"] = "attacker"
    assert not audit.verify_integrity()


def test_audit_detects_hash_mutation():
    audit = AuditTrail(secret_key="test-key")
    audit.log("runner", "unit", "EVENT", {"state":"ok"})
    audit.logs[0]["current_hash"] = "0" * 64
    assert not audit.verify_integrity()
