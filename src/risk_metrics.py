"""
FX risk metrics: Value-at-Risk (historical + parametric) and
Expected Shortfall, on a multi-currency position book.

All outputs are expressed in the base currency (e.g. GBP).

Definitions
-----------
VaR at confidence c and horizon h:
    The loss that will not be exceeded with probability c over horizon h.
    Reported as a POSITIVE number (a loss).

Expected Shortfall (ES) at confidence c:
    The average loss conditional on the loss exceeding VaR.
    Always >= VaR.
"""
from typing import Dict, Sequence

import numpy as np
import pandas as pd
from scipy import stats


# ---------- P&L construction ----------

def pnl_series(
    fx_base: pd.DataFrame,
    signed_notionals: Dict[str, float],
) -> pd.Series:
    """
    Daily P&L in base currency for a book of FX positions.

    fx_base: columns are CCY -> base rates, indexed by date.
    signed_notionals: {CCY: signed notional} where + = long foreign ccy.

    P&L on day t for a long position in CCY:
        notional * (rate_t - rate_{t-1})
    """
    cols = list(signed_notionals.keys())
    missing = set(cols) - set(fx_base.columns)
    if missing:
        raise ValueError(f"FX data missing for: {sorted(missing)}")

    delta = fx_base[cols].diff()
    notional = pd.Series(signed_notionals, dtype=float)[cols]
    return (delta * notional).sum(axis=1).dropna()


# ---------- VaR ----------

def historical_var(pnl: pd.Series, confidence: float) -> float:
    """
    Historical (empirical) VaR: the (1 - confidence) quantile of the P&L
    distribution, reported as a positive loss.
    """
    if not 0.5 < confidence < 1.0:
        raise ValueError("confidence must be in (0.5, 1.0)")
    q = np.quantile(pnl.dropna().values, 1.0 - confidence)
    return float(-q)


def parametric_var(pnl: pd.Series, confidence: float) -> float:
    """
    Parametric (variance-covariance) VaR assuming normally distributed
    P&L: VaR = -(mu + sigma * z_{1-c}), reported as a positive loss.
    """
    if not 0.5 < confidence < 1.0:
        raise ValueError("confidence must be in (0.5, 1.0)")
    r = pnl.dropna()
    mu = r.mean()
    sigma = r.std(ddof=1)
    z = stats.norm.ppf(1.0 - confidence)
    return float(-(mu + sigma * z))


def scale_var_to_horizon(var_1d: float, horizon_days: int) -> float:
    """Scale 1-day VaR to an h-day horizon under iid assumption (sqrt-of-time)."""
    if horizon_days < 1:
        raise ValueError("horizon_days must be >= 1")
    return var_1d * np.sqrt(horizon_days)


# ---------- Expected Shortfall ----------

def historical_es(pnl: pd.Series, confidence: float) -> float:
    """
    Historical Expected Shortfall: mean loss conditional on the loss
    being worse than the historical VaR.
    """
    if not 0.5 < confidence < 1.0:
        raise ValueError("confidence must be in (0.5, 1.0)")
    r = pnl.dropna()
    var = historical_var(r, confidence)
    tail = r[r <= -var]
    if tail.empty:
        return float(var)
    return float(-tail.mean())


def parametric_es(pnl: pd.Series, confidence: float) -> float:
    """
    Parametric ES assuming normally distributed P&L:
        ES = -(mu - sigma * phi(z) / (1 - c))
    """
    if not 0.5 < confidence < 1.0:
        raise ValueError("confidence must be in (0.5, 1.0)")
    r = pnl.dropna()
    mu = r.mean()
    sigma = r.std(ddof=1)
    z = stats.norm.ppf(1.0 - confidence)
    phi = stats.norm.pdf(z)
    return float(-(mu - sigma * phi / (1.0 - confidence)))


# ---------- Summary ----------

def risk_summary(
    pnl: pd.Series,
    confidence_levels: Sequence[float] = (0.95, 0.99),
    horizon_days: int = 1,
) -> pd.DataFrame:
    """
    Produce a tidy summary of all risk metrics for a P&L series.

    Rows: metric name (Historical VaR, Parametric VaR, Historical ES,
    Parametric ES). Columns: confidence level (e.g. "VaR 95%", "VaR 99%").
    """
    rows = {}
    for c in confidence_levels:
        label = f"{int(round(c * 100))}%"
        rows[f"Historical VaR {label}"] = scale_var_to_horizon(
            historical_var(pnl, c), horizon_days
        )
        rows[f"Parametric VaR {label}"] = scale_var_to_horizon(
            parametric_var(pnl, c), horizon_days
        )
        rows[f"Historical ES  {label}"] = historical_es(pnl, c)
        rows[f"Parametric ES  {label}"] = parametric_es(pnl, c)

    return pd.Series(rows, name="value").to_frame()


# ---------- Rolling VaR ----------

def rolling_var(
    pnl: pd.Series,
    confidence: float,
    window: int = 250,
    method: str = "historical",
) -> pd.Series:
    """
    Rolling VaR over a trailing window.

    pnl: daily P&L series.
    confidence: e.g. 0.99.
    window: rolling lookback in observations (default ~1 year of business days).
    method: "historical" or "parametric".
    """
    if method not in ("historical", "parametric"):
        raise ValueError("method must be 'historical' or 'parametric'")

    fn = historical_var if method == "historical" else parametric_var
    return pnl.rolling(window=window).apply(lambda x: fn(pd.Series(x), confidence), raw=False)
