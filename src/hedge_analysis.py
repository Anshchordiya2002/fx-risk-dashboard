"""
Hedged vs unhedged risk comparison.

Applies a set of hedge ratios to the FX position book and re-measures
VaR and Expected Shortfall. The residual exposure after hedging
currency c at ratio h is (1 - h).

Mirrors the JPM passive currency overlay concept: neutralise a chosen
fraction of FX exposure to reduce portfolio VaR.
"""
from typing import Dict

import pandas as pd

from src.risk_metrics import historical_var, historical_es, pnl_series


def apply_hedge_ratios(
    signed_notionals: Dict[str, float],
    hedge_ratios: Dict[str, float],
) -> Dict[str, float]:
    """
    Return the residual (post-hedge) signed notional per currency.

    residual = signed_notional * (1 - hedge_ratio)
    """
    for ccy, h in hedge_ratios.items():
        if not 0.0 <= h <= 1.0:
            raise ValueError(f"hedge ratio for {ccy} must be in [0,1], got {h}")

    out = {}
    for ccy, notional in signed_notionals.items():
        h = hedge_ratios.get(ccy, 0.0)
        out[ccy] = notional * (1.0 - h)
    return out


def hedged_vs_unhedged(
    fx_base: pd.DataFrame,
    signed_notionals: Dict[str, float],
    hedge_ratios: Dict[str, float],
    confidence_levels=(0.95, 0.99),
) -> pd.DataFrame:
    """
    Compare VaR and ES before and after hedging.

    Returns a DataFrame indexed by confidence level, columns:
    unhedged VaR, hedged VaR, VaR reduction %, unhedged ES, hedged ES,
    ES reduction %.
    """
    unhedged_pnl = pnl_series(fx_base, signed_notionals)
    residual = apply_hedge_ratios(signed_notionals, hedge_ratios)
    hedged_pnl = pnl_series(fx_base, residual)

    rows = []
    for c in confidence_levels:
        uv = historical_var(unhedged_pnl, c)
        hv = historical_var(hedged_pnl, c)
        ue = historical_es(unhedged_pnl, c)
        he = historical_es(hedged_pnl, c)
        rows.append({
            "confidence": f"{int(round(c * 100))}%",
            "unhedged VaR": uv,
            "hedged VaR": hv,
            "VaR reduction %": 100.0 * (uv - hv) / uv if uv else float("nan"),
            "unhedged ES": ue,
            "hedged ES": he,
            "ES reduction %": 100.0 * (ue - he) / ue if ue else float("nan"),
        })
    return pd.DataFrame(rows).set_index("confidence").round(2)
