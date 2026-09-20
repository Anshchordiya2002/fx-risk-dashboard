"""
Forward roll simulation.

In a passive currency overlay, forwards are rolled on a fixed cycle
(typically monthly). At each roll:
  - The expiring forward is settled at the prevailing spot.
  - A new forward is entered for the next cycle.

This module computes the P&L and roll cost of that cycle for a book
of hedged positions. It is a simplified version of what an overlay
operations team does daily.
"""
from dataclasses import dataclass
from typing import Dict, List

import pandas as pd


@dataclass
class RollCycle:
    """One roll date: what settled, what was opened, at what rate."""
    roll_date: pd.Timestamp
    currency: str
    settled_notional: float     # signed, in foreign ccy
    spot_at_roll: float         # foreign -> base
    roll_cost_base: float       # cost in base currency (positive = cost)


def simulate_rolls(
    fx_base: pd.DataFrame,
    signed_notionals: Dict[str, float],
    hedge_ratios: Dict[str, float],
    roll_frequency_days: int = 30,
    roll_cost_bps: float = 1.0,
) -> List[RollCycle]:
    """
    Simulate forward rolls across the sample.

    At each roll date, for each currency with a non-zero hedge:
      - The hedged fraction of the notional is rolled.
      - A cost of `roll_cost_bps` basis points is applied on the rolled
        notional (proxy for bid/ask + forward points).

    Returns a flat list of RollCycle records.
    """
    if roll_frequency_days < 1:
        raise ValueError("roll_frequency_days must be >= 1")

    dates = fx_base.index
    roll_dates = dates[::roll_frequency_days]

    cycles: List[RollCycle] = []
    for d in roll_dates:
        for ccy, notional in signed_notionals.items():
            h = hedge_ratios.get(ccy, 0.0)
            if h == 0.0:
                continue
            hedged_notional = notional * h
            if ccy not in fx_base.columns:
                continue
            spot = float(fx_base.at[d, ccy])
            cost = abs(hedged_notional) * spot * (roll_cost_bps / 10_000.0)
            cycles.append(RollCycle(
                roll_date=d,
                currency=ccy,
                settled_notional=hedged_notional,
                spot_at_roll=spot,
                roll_cost_base=cost,
            ))
    return cycles


def roll_cost_summary(cycles: List[RollCycle]) -> pd.DataFrame:
    """
    Aggregate roll costs by currency: number of rolls, total cost, average cost.
    """
    if not cycles:
        return pd.DataFrame(columns=["rolls", "total cost", "avg cost"])

    df = pd.DataFrame([{
        "currency": c.currency,
        "roll_cost_base": c.roll_cost_base,
    } for c in cycles])

    return df.groupby("currency")["roll_cost_base"].agg(
        rolls="count",
        **{"total cost": "sum", "avg cost": "mean"},
    ).round(2)
