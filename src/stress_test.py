"""
Historical stress testing.

Replays the FX position book through named historical stress windows
and reports the realised P&L, VaR and ES over each window. These are
the scenarios a JPM overlay client asks about in meetings.
"""
from typing import Dict, Tuple

import pandas as pd

from src.risk_metrics import pnl_series, historical_var, historical_es


DEFAULT_SCENARIOS: Dict[str, Tuple[str, str]] = {
    "Brexit 2016":      ("2016-06-20", "2016-07-15"),
    "COVID crash 2020": ("2020-02-20", "2020-03-31"),
    "Gilt crisis 2022": ("2022-09-20", "2022-10-14"),
}


def run_stress_tests(
    fx_base: pd.DataFrame,
    signed_notionals: Dict[str, float],
    scenarios: Dict[str, Tuple[str, str]] = None,
    confidence: float = 0.99,
) -> pd.DataFrame:
    """
    For each scenario window, compute:
      - total P&L over the window
      - worst single-day P&L
      - number of loss days
      - historical VaR and ES within the window
    """
    if scenarios is None:
        scenarios = DEFAULT_SCENARIOS

    rows = []
    for name, (start, end) in scenarios.items():
        window = fx_base.loc[start:end]
        if window.empty:
            rows.append({
                "scenario": name, "start": start, "end": end,
                "days": 0, "total P&L": float("nan"),
                "worst day": float("nan"), "loss days": 0,
                "VaR 99%": float("nan"), "ES 99%": float("nan"),
            })
            continue

        pnl = pnl_series(window, signed_notionals)

        rows.append({
            "scenario": name,
            "start": start,
            "end": end,
            "days": len(pnl),
            "total P&L": pnl.sum(),
            "worst day": pnl.min(),
            "loss days": int((pnl < 0).sum()),
            "VaR 99%": historical_var(pnl, confidence) if len(pnl) >= 10 else float("nan"),
            "ES 99%": historical_es(pnl, confidence) if len(pnl) >= 10 else float("nan"),
        })

    return pd.DataFrame(rows).set_index("scenario").round(2)
