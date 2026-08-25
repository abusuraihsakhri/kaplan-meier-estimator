# Kaplan-Meier Survival Estimator

A pure-Python (stdlib-only) implementation of the Kaplan-Meier survival estimator with confidence intervals, log-rank test, hazard rate estimation, and Nelson-Aalen cumulative hazard.

## Features

- **Kaplan-Meier survival function**: S(t) = Π(ti≤t) (1 − di/ni)
- **Censored data handling**: Properly accounts for right-censored observations
- **Median survival time**: First time where S(t) ≤ 0.5
- **95% Confidence intervals**: Log-log method (complementary log-log transformation)
- **Greenwood variance**: Var(S(t)) = S(t)² × Σ di/(ni×(ni−di))
- **Log-rank test**: Chi-square test comparing two survival curves
- **Hazard rate estimation**: h(ti) = di / (ni × Δti)
- **Nelson-Aalen cumulative hazard**: H(t) = Σ di/ni
- **CSV batch processing**: Process datasets with optional group comparison

## Formulas

### Survival Function
S(t) = ∏(ti ≤ t) (1 − di/ni)

Where:
- di = number of events at time ti
- ni = number at risk just before time ti

### Log-Rank Test
χ² = (O₁ − E₁)² / V

Where:
- O₁ = observed events in group 1
- E₁ = expected events in group 1
- V = hypergeometric variance

### Nelson-Aalen Cumulative Hazard
Ĥ(t) = Σ(ti ≤ t) di/ni

## Usage

### Command Line

```bash
# Single group analysis
python cli.py analyze --time 1 2 3 4 5 6 8 10 --event 1 0 1 1 0 1 1 0

# Compare two groups (log-rank test)
python cli.py compare --time1 1 2 3 4 5 --event1 1 0 1 1 0 \
                      --time2 2 3 4 5 6 --event2 0 1 1 0 1

# Hazard rates
python cli.py hazard --time 1 2 3 4 5 --event 1 0 1 1 0

# Batch CSV processing
python cli.py batch --input sample.csv --output results.csv
```

### Python API

```python
from kaplan_meier import kaplan_meier, log_rank_test, hazard_rate, nelson_aalen

# Basic analysis
times = [1, 2, 3, 4, 5, 6, 8, 10]
events = [1, 0, 1, 1, 0, 1, 1, 0]
result = kaplan_meier(times, events)

print(f"Median survival: {result['median']}")
print(f"Survival at times: {list(zip(result['times'], result['survival']))}")

# Log-rank test
lr = log_rank_test(
    [1, 2, 3, 4, 5], [1, 0, 1, 1, 0],
    [2, 3, 4, 5, 6], [0, 1, 1, 0, 1]
)
print(f"p-value: {lr['p_value']}")

# Hazard rates
rates = hazard_rate(times, events)
```

## CSV Format

Input CSV should have columns for time and event (auto-detected from common names):

| time | event | group |
|------|-------|-------|
| 1    | 1     | A     |
| 2    | 0     | A     |
| 3    | 1     | B     |

Column names are matched case-insensitively from: `time`, `survival_time`, `days`, `months`, `t` and `event`, `status`, `dead`, `censored`, `e`.

## Testing

```bash
python -m pytest test_kaplan_meier.py -v
```

## License

MIT
