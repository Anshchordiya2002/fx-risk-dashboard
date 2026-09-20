"""
Non-interactive pipeline: run the full FX risk analysis end to end.

    python main.py

Prints a text report and writes outputs/*.csv + outputs/*.png.
"""
import pandas as pd

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", None)

from src.config import PortfolioConfig
from src.data_loader import load_fx_rates
from src.risk_metrics import pnl_series, risk_summary, rolling_var
from src.hedge_analysis import hedged_vs_unhedged
from src.stress_test import run_stress_tests
from src.forward_roll import simulate_rolls, roll_cost_summary
from src.report import (
    save_summary,
    plot_rolling_var,
    plot_hedged_vs_unhedged_histogram,
)


def main() -> None:
    cfg = PortfolioConfig()
    cfg.validate()

    print("=" * 72)
    print("FX RISK METRICS DASHBOARD")
    print("=" * 72)
    print(f"Base currency:  {cfg.risk.base_currency}")
    print(f"Confidence:     {cfg.risk.confidence_levels}")
    print(f"Horizon:        {cfg.risk.horizon_days} day")
    print()

    currencies = list({p.currency for p in cfg.positions} | {cfg.risk.base_currency})
    fx = load_fx_rates(currencies, "2015-01-01", "2025-01-01",
                       base=cfg.risk.base_currency)
    signed = {p.currency: p.signed_notional() for p in cfg.positions}

    # ---- 1. Unhedged risk metrics ----
    print("-" * 72)
    print("1. UNHEDGED POSITION RISK")
    print("-" * 72)
    pnl_unhedged = pnl_series(fx, signed)
    print(risk_summary(pnl_unhedged, tuple(cfg.risk.confidence_levels),
                       cfg.risk.horizon_days).round(2))
    print()

    # ---- 2. Hedged vs unhedged ----
    print("-" * 72)
    print("2. HEDGED vs UNHEDGED (example ratios: USD 1.0, EUR 0.5, CHF 0.75, JPY 0.0)")
    print("-" * 72)
    hedge_ratios = {"USD": 1.00, "EUR": 0.50, "JPY": 0.00, "CHF": 0.75}
    cmp = hedged_vs_unhedged(fx, signed, hedge_ratios, cfg.risk.confidence_levels)
    print(cmp)
    print()

    # ---- 3. Stress tests ----
    print("-" * 72)
    print("3. STRESS SCENARIOS (unhedged book)")
    print("-" * 72)
    stress = run_stress_tests(fx, signed)
    print(stress)
    print()

    # ---- 4. Forward roll cost ----
    print("-" * 72)
    print("4. FORWARD ROLL COST (1 bp per roll, monthly cycle)")
    print("-" * 72)
    cycles = simulate_rolls(fx, signed, hedge_ratios,
                            roll_frequency_days=30, roll_cost_bps=1.0)
    print(roll_cost_summary(cycles))
    total = sum(c.roll_cost_base for c in cycles)
    years = (fx.index.max() - fx.index.min()).days / 365.25
    print(f"\nTotal roll cost:  {total:,.2f} {cfg.risk.base_currency}")
    print(f"Per year (avg):   {total / years:,.2f} {cfg.risk.base_currency}")
    print()

    # ---- 5. Charts ----
    print("-" * 72)
    print("5. OUTPUTS")
    print("-" * 72)
    save_summary(cmp, "hedged_vs_unhedged.csv")
    save_summary(stress, "stress_scenarios.csv")

    roll_unhedged = rolling_var(pnl_unhedged, 0.99, window=250).dropna()
    pnl_hedged = pnl_series(fx, {c: signed[c] * (1 - hedge_ratios.get(c, 0.0))
                                 for c in signed})
    roll_hedged = rolling_var(pnl_hedged, 0.99, window=250).dropna()

    plot_rolling_var(roll_unhedged, roll_hedged)
    plot_hedged_vs_unhedged_histogram(pnl_unhedged, pnl_hedged)
    print("Wrote outputs/rolling_var.png")
    print("Wrote outputs/hedged_vs_unhedged_histogram.png")
    print("Wrote outputs/hedged_vs_unhedged.csv")
    print("Wrote outputs/stress_scenarios.csv")
    print()
    print("Done.")


if __name__ == "__main__":
    main()
