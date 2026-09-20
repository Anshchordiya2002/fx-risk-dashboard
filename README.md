# FX Risk Metrics Dashboard

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-11%20passed-brightgreen.svg)](#testing)
[![Data](https://img.shields.io/badge/data-ECB%20reference%20rates-blueviolet.svg)](https://data.ecb.europa.eu/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)](#license)

A Python risk analytics toolkit for a multi-currency FX position book. It computes **Value-at-Risk** (historical and parametric), **Expected Shortfall**, **historical stress-test P&L** and **hedge effectiveness**, using ten years of European Central Bank reference rates.

The project is modelled on the workflow of a **currency overlay desk**: quantifying how much currency risk a portfolio is running, and how much of it a passive hedging programme removes.

---

## Contents

- [Headline results](#headline-results)
- [What it answers](#what-it-answers)
- [Quick start](#quick-start)
- [Outputs](#outputs)
- [Stress scenarios](#stress-scenarios)
- [Hedging cost](#hedging-cost)
- [Methodology](#methodology)
- [Assumptions and limitations](#assumptions-and-limitations)
- [Project structure](#project-structure)
- [Testing](#testing)
- [Interactive dashboard](#interactive-dashboard)
- [Roadmap](#roadmap)

---

## Headline results

**Portfolio:** GBP base currency, approximately £10m equivalent notional
**Positions:** USD 6m long · EUR 4m long · JPY 500m long · CHF 1.5m long
**Sample:** 1 January 2015 – 1 January 2025
**Hedge programme:** USD 100% · EUR 50% · CHF 75% · JPY 0%

| Metric (1-day) | Unhedged | Hedged | Reduction |
|---|---:|---:|---:|
| VaR 95% | £92,020 | £43,403 | **52.8%** |
| VaR 99% | £171,432 | £75,587 | **55.9%** |
| ES 95% | £138,470 | £64,721 | **53.3%** |
| ES 99% | £220,331 | £101,602 | **53.9%** |

> **Key finding — fat tails.** On the same data, historical VaR 99% (£171k) is **16% higher** than parametric VaR 99% (£148k). The normal distribution materially understates tail risk for this book, which is why the tool reports both methods side by side.

![Rolling 1-year VaR 99%, hedged vs unhedged]

![Daily P&L distribution, hedged vs unhedged]

---

## What it answers

For any FX position book with configurable per-currency hedge ratios:

| Question | Analysis |
|---|---|
| How much could we lose on a bad day? | VaR 95% / 99%, historical and parametric |
| How bad is the average bad day? | Expected Shortfall |
| How much risk does a passive hedge remove? | Hedged vs unhedged VaR and ES |
| What happens in a real crisis? | Brexit 2016, COVID 2020, UK gilt crisis 2022 |
| What does the hedge cost to run? | Forward roll cost by currency |
| How does risk evolve over time? | Rolling 1-year VaR |

---

## Quick start

```bash
git clone https://github.com/Anshchordiya2002/fx-risk-dashboard.git
cd fx-risk-dashboard

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python src/fetch_ecb.py          # one-off: cache ECB rates (~10s)
python main.py                   # run the full pipeline

streamlit run dashboard.py       # optional: interactive dashboard
```

The ECB Data Portal is free and requires no API key.

---

## Outputs

`main.py` writes the following to `outputs/`:

| File | Contents |
|---|---|
| `rolling_var.png` | Rolling 1-year VaR 99%, unhedged vs hedged |
| `hedged_vs_unhedged_histogram.png` | Daily P&L distribution, unhedged vs hedged |
| `hedged_vs_unhedged.csv` | VaR / ES comparison table |
| `stress_scenarios.csv` | Brexit / COVID / gilt crisis P&L |

---

## Stress scenarios

Unhedged book, replaying historical GBP stress windows:

| Scenario | Days | Cumulative P&L | Worst day | VaR 99% in window |
|---|---:|---:|---:|---:|
| Brexit referendum 2016 | 20 | +£985,812 | −£213,344 | £210,541 |
| COVID crash 2020 | 29 | +£715,201 | −£245,871 | £235,136 |
| UK gilt crisis 2022 | 19 | +£36,564 | −£265,425 | £261,141 |

**Interpretation.** The book is long foreign currency against GBP, so each of these sterling-negative episodes produced a *cumulative gain* in GBP terms. The risk lies in the path: worst single-day losses of £213k–£265k, each at or beyond the full-sample VaR 99%. A hedge programme is sized against those daily losses, not the window total.

---

## Hedging cost

Transaction cost of rolling hedges monthly at a flat 1 bp per roll:

| Currency | Rolls | Total cost | Average per roll |
|---|---:|---:|---:|
| USD | 86 | £39,194 | £456 |
| EUR | 86 | £14,611 | £170 |
| CHF | 86 | £7,760 | £90 |
| **Total** | **258** | **£61,566** | — |

This is approximately **£6,200 per year, or ~6 bps on £10m notional**.

> **Note:** these figures cover transaction cost only. The economic cost or benefit of a currency hedge is dominated by **forward points** (the interest-rate differential between GBP and the hedged currency), which this version does not yet model. See [Assumptions](#assumptions-and-limitations) and [Roadmap](#roadmap).

---

## Methodology

### 1. Data

Daily EUR-based reference rates from the ECB Data Portal. Cross rates to the portfolio base currency are derived using EUR as the pivot:

```text
CCY → base = (EUR → base) / (EUR → CCY)
```

### 2. P&L construction

For a position of `signed_notional` units of a currency, with rates quoted as base currency per unit:

```text
daily P&L = signed_notional × (rate_t − rate_{t−1})
```

Book-level P&L is the sum across currencies.

### 3. Risk metrics

| Metric | Method |
|---|---|
| Historical VaR | Empirical (1 − c) quantile of daily P&L |
| Parametric VaR | Normal: −(μ + σ · z₁₋c) |
| Historical ES | Mean loss beyond historical VaR |
| Parametric ES | Normal: −(μ − σ · φ(z) / (1 − c)) |
| Horizon scaling | VaR_h = VaR_1 · √h (iid assumption) |

All losses are reported as positive numbers.

### 4. Hedge analysis

Residual exposure after hedging currency *c* at ratio *h_c*:

```text
residual_c = signed_notional_c × (1 − h_c)
```

VaR and ES are recomputed on the residual book and compared with the unhedged book.

### 5. Forward roll

Simulates monthly hedge rolls across the sample. Each roll incurs `roll_cost_bps` on the hedged notional; costs are aggregated by currency.

---

## Assumptions and limitations

Read these before quoting any number.

- **FX-only P&L.** Underlying asset returns are set to zero so the analysis isolates the currency component of return. In practice the asset/currency cross term is small but non-zero.
- **Forwards priced at spot.** Real forwards trade at spot ± forward points reflecting the interest-rate differential. For a GBP investor, hedging USD has carried a meaningful cost over much of the sample, while hedging EUR, CHF and JPY has typically earned positive carry. A flat roll cost captures transaction friction only, not this carry.
- **Parametric VaR assumes normally distributed P&L.** The gap to historical VaR is reported deliberately as a measure of fat-tail error.
- **√t horizon scaling.** Valid for iid returns. Under volatility clustering, true multi-day VaR can differ materially depending on the prevailing regime.
- **Correlation.** Historical VaR captures realised cross-currency correlation implicitly; no explicit correlation or tail-dependence model is fitted.
- **End-of-day data only.** Returns are based on ECB daily reference rates (fixed around 14:15 CET), not intraday prices.

---

## Project structure

```text
fx-risk-dashboard/
├── data/
│   └── fx_rates.csv            # cached ECB EUR-based rates
├── outputs/                    # charts and CSV reports
├── src/
│   ├── config.py               # positions, hedge ratios, risk parameters
│   ├── data_loader.py          # ECB cache reader, cross-rate conversion
│   ├── fetch_ecb.py            # one-off ECB fetcher
│   ├── risk_metrics.py         # VaR, ES, rolling VaR
│   ├── hedge_analysis.py       # hedged vs unhedged comparison
│   ├── stress_test.py          # named historical scenarios
│   ├── forward_roll.py         # monthly roll cost simulation
│   └── report.py               # static charts and CSV outputs
├── tests/
│   └── test_risk_metrics.py    # 11 unit tests
├── dashboard.py                # Streamlit interactive dashboard
├── main.py                     # one-command pipeline
├── requirements.txt
└── README.md
```

---

## Testing

```bash
python -m pytest -q
```

Eleven tests validate the core mathematics:

| Test | What it verifies |
|---|---|
| `test_historical_var_matches_normal_quantile` | Historical VaR 95% / 99% ≈ 1.645σ / 2.326σ on simulated normal data |
| `test_parametric_var_matches_normal_quantile` | Same, using the analytic method |
| `test_es_greater_than_var` | ES exceeds VaR at each confidence level |
| `test_var_increases_with_confidence` | VaR is monotonic in confidence |
| `test_var_positive_for_loss_distribution` | Losses are reported as positive values |
| `test_pnl_series_matches_manual_formula` | P&L arithmetic matches the closed form |
| `test_apply_hedge_ratios_correct` | Residual exposure formula |
| `test_full_hedge_removes_all_exposure` | h = 1.0 produces zero P&L |
| `test_zero_hedge_equals_unhedged` | h = 0.0 is a no-op |
| `test_hedged_vs_unhedged_returns_expected_columns` | Output schema |
| `test_hedged_var_is_lower_than_unhedged` | Hedging reduces VaR |

---

## Interactive dashboard

```bash
streamlit run dashboard.py
```

The Streamlit dashboard lets you explore hedge policy without touching code:

- **Per-currency hedge sliders** — adjust each hedge ratio independently
- **Live risk metrics** — VaR and ES recompute on every change
- **Position book view** — signed notional, hedge ratio and residual exposure side by side
- **Charts** — rolling VaR and P&L distribution update alongside the metrics

---

## Roadmap

- [ ] **Forward points** — price hedges from SONIA / SOFR / €STR / SARON / TONA differentials instead of a flat roll cost, capturing hedge carry
- [ ] **VaR backtesting** — Kupiec and Christoffersen tests on historical VaR breaches
- [ ] **Monte Carlo VaR** — Student-t marginals with a t-copula to model tail dependence explicitly
- [ ] **Regime-conditional hedging** — volatility-scaled overlay that raises hedge ratios in high-volatility regimes
- [ ] **Bank of England rates** — add BoE daily GBP spot rates as a second data source

---

## Tech stack

Python 3.12 · pandas · NumPy · SciPy · Matplotlib · Streamlit · pytest · ECB Data Portal API

---

## License

Released under the [MIT License](LICENSE).

---

## Author

**Ansh Chordiya**
· [GitHub](https://github.com/Anshchordiya2002)
