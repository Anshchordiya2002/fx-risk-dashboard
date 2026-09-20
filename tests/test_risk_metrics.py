"""
Sanity tests for VaR, ES, and hedge analysis.

These are the executable spec for the risk model.
"""
import numpy as np
import pandas as pd
import pytest

from src.risk_metrics import (
    historical_var,
    parametric_var,
    historical_es,
    parametric_es,
    pnl_series,
)
from src.hedge_analysis import apply_hedge_ratios, hedged_vs_unhedged


@pytest.fixture
def normal_pnl():
    """100k draws from N(0, 1000) — the analytical benchmark."""
    rng = np.random.default_rng(42)
    return pd.Series(rng.normal(loc=0.0, scale=1000.0, size=100_000))


@pytest.fixture
def fx_panel():
    """Synthetic CCY->GBP rates with two currencies."""
    idx = pd.date_range("2020-01-01", periods=500, freq="B")
    rng = np.random.default_rng(0)
    usd = 0.80 + np.cumsum(rng.normal(0, 0.003, len(idx)))
    eur = 0.86 + np.cumsum(rng.normal(0, 0.003, len(idx)))
    return pd.DataFrame({"USD": usd, "EUR": eur, "GBP": 1.0}, index=idx)


def test_historical_var_matches_normal_quantile(normal_pnl):
    # For N(0, 1000): VaR 95% ~ 1645, VaR 99% ~ 2326
    assert abs(historical_var(normal_pnl, 0.95) - 1645) < 60
    assert abs(historical_var(normal_pnl, 0.99) - 2326) < 90


def test_parametric_var_matches_normal_quantile(normal_pnl):
    assert abs(parametric_var(normal_pnl, 0.95) - 1645) < 30
    assert abs(parametric_var(normal_pnl, 0.99) - 2326) < 30


def test_es_greater_than_var(normal_pnl):
    for c in (0.95, 0.99):
        assert historical_es(normal_pnl, c) > historical_var(normal_pnl, c)
        assert parametric_es(normal_pnl, c) > parametric_var(normal_pnl, c)


def test_var_increases_with_confidence(normal_pnl):
    assert historical_var(normal_pnl, 0.99) > historical_var(normal_pnl, 0.95)
    assert parametric_var(normal_pnl, 0.99) > parametric_var(normal_pnl, 0.95)


def test_var_positive_for_loss_distribution(normal_pnl):
    # VaR is reported as a positive loss number
    assert historical_var(normal_pnl, 0.99) > 0
    assert parametric_var(normal_pnl, 0.99) > 0


def test_pnl_series_matches_manual_formula(fx_panel):
    signed = {"USD": 1_000_000, "EUR": 500_000}
    pnl = pnl_series(fx_panel, signed)

    delta_usd = fx_panel["USD"].diff() * signed["USD"]
    delta_eur = fx_panel["EUR"].diff() * signed["EUR"]
    expected = (delta_usd + delta_eur).dropna()

    # Align on index so pandas doesn't try to broadcast two different lengths
    aligned = pnl.reindex(expected.index)
    assert np.allclose(aligned.values, expected.values, atol=1e-9)


def test_apply_hedge_ratios_correct(fx_panel):
    signed = {"USD": 1_000_000, "EUR": 500_000}
    ratios = {"USD": 1.0, "EUR": 0.5}
    residual = apply_hedge_ratios(signed, ratios)
    assert residual["USD"] == 0.0
    assert residual["EUR"] == 250_000.0


def test_full_hedge_removes_all_exposure(fx_panel):
    signed = {"USD": 1_000_000}
    ratios = {"USD": 1.0}
    pnl_full = pnl_series(fx_panel, apply_hedge_ratios(signed, ratios))
    assert np.allclose(pnl_full.dropna().values, 0.0, atol=1e-9)


def test_zero_hedge_equals_unhedged(fx_panel):
    signed = {"USD": 1_000_000}
    ratios = {"USD": 0.0}
    pnl_un  = pnl_series(fx_panel, signed)
    pnl_hed = pnl_series(fx_panel, apply_hedge_ratios(signed, ratios))
    assert np.allclose(pnl_un.values, pnl_hed.values, atol=1e-9)


def test_hedged_vs_unhedged_returns_expected_columns(fx_panel):
    signed = {"USD": 1_000_000, "EUR": 500_000}
    ratios = {"USD": 1.0, "EUR": 0.0}
    df = hedged_vs_unhedged(fx_panel, signed, ratios, (0.95, 0.99))
    expected_cols = {
        "unhedged VaR", "hedged VaR", "VaR reduction %",
        "unhedged ES", "hedged ES", "ES reduction %",
    }
    assert expected_cols.issubset(df.columns)


def test_hedged_var_is_lower_than_unhedged(fx_panel):
    signed = {"USD": 1_000_000, "EUR": 500_000}
    ratios = {"USD": 1.0, "EUR": 1.0}
    df = hedged_vs_unhedged(fx_panel, signed, ratios, (0.99,))
    assert df.loc["99%", "hedged VaR"] < df.loc["99%", "unhedged VaR"]
