"""
Interactive FX risk dashboard (Streamlit).

Run with:
    streamlit run dashboard.py

The dashboard lets the user:
  - Adjust hedge ratios per currency with sliders
  - Pick confidence levels
  - See VaR / ES update live, both numerically and as rolling charts
  - Compare unhedged vs hedged side by side
"""
import pandas as pd
import streamlit as st

from src.config import PortfolioConfig
from src.data_loader import load_fx_rates
from src.risk_metrics import (
    pnl_series,
    historical_var,
    parametric_var,
    historical_es,
    parametric_es,
    rolling_var,
)
from src.hedge_analysis import apply_hedge_ratios, hedged_vs_unhedged


st.set_page_config(page_title="FX Risk Dashboard", layout="wide")


@st.cache_data(show_spinner=False)
def load_data(currencies, start, end, base):
    return load_fx_rates(currencies, start, end, base=base)


def main() -> None:
    st.title("FX Risk Metrics Dashboard")
    st.caption("Currency overlay risk analytics - VaR, Expected Shortfall, hedge effectiveness.")

    cfg = PortfolioConfig()
    signed = {p.currency: p.signed_notional() for p in cfg.positions}

    # --- Sidebar controls ---
    st.sidebar.header("Portfolio")
    st.sidebar.write(f"Base currency: **{cfg.risk.base_currency}**")
    st.sidebar.write(f"Horizon: **{cfg.risk.horizon_days} day**")

    start = st.sidebar.date_input("Start date", pd.to_datetime("2020-01-01"))
    end = st.sidebar.date_input("End date", pd.to_datetime("2025-01-01"))

    st.sidebar.header("Hedge ratios")
    default_ratios = {"USD": 1.00, "EUR": 0.50, "JPY": 0.00, "CHF": 0.75}
    hedge_ratios = {}
    for ccy in signed:
        default = default_ratios.get(ccy, 0.5)
        hedge_ratios[ccy] = st.sidebar.slider(
            f"{ccy} hedge ratio", 0.0, 1.0, default, 0.05, key=f"h_{ccy}"
        )

    # --- Load data ---
    fx = load_data(
        tuple(signed.keys()) + (cfg.risk.base_currency,),
        str(start), str(end), cfg.risk.base_currency
    )

    # --- Unhedged P&L ---
    pnl_unhedged = pnl_series(fx, signed)
    residual = apply_hedge_ratios(signed, hedge_ratios)
    pnl_hedged = pnl_series(fx, residual)

    # --- Metrics row ---
    st.subheader("Risk metrics")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Unhedged VaR 99%",
        f"{historical_var(pnl_unhedged, 0.99):,.0f} {cfg.risk.base_currency}",
    )
    c2.metric(
        "Hedged VaR 99%",
        f"{historical_var(pnl_hedged, 0.99):,.0f} {cfg.risk.base_currency}",
    )
    c3.metric(
        "Unhedged ES 99%",
        f"{historical_es(pnl_unhedged, 0.99):,.0f} {cfg.risk.base_currency}",
    )
    c4.metric(
        "Hedged ES 99%",
        f"{historical_es(pnl_hedged, 0.99):,.0f} {cfg.risk.base_currency}",
    )

    # --- Comparison table ---
    st.subheader("Hedged vs unhedged")
    table = hedged_vs_unhedged(fx, signed, hedge_ratios, cfg.risk.confidence_levels)
    st.dataframe(table, use_container_width=True)

    # --- Rolling VaR chart ---
    st.subheader("Rolling 1-year VaR (99%, historical)")
    roll_un = rolling_var(pnl_unhedged, 0.99, window=250).dropna()
    roll_hd = rolling_var(pnl_hedged,   0.99, window=250).dropna()
    chart_df = pd.DataFrame({
        "Unhedged VaR 99%": roll_un,
        "Hedged VaR 99%":   roll_hd,
    })
    st.line_chart(chart_df)

    # --- P&L distribution ---
    st.subheader("Daily P&L distribution")
    st.caption("Histogram of daily P&L, unhedged vs hedged (30 bins).")
    import numpy as np
    un_vals = pnl_unhedged.dropna().values
    hd_vals = pnl_hedged.dropna().values
    lo = float(min(un_vals.min(), hd_vals.min()))
    hi = float(max(un_vals.max(), hd_vals.max()))
    bins = np.linspace(lo, hi, 31)
    un_counts, edges = np.histogram(un_vals, bins=bins)
    hd_counts, _     = np.histogram(hd_vals, bins=bins)
    centers = (edges[:-1] + edges[1:]) / 2
    # Label bins in thousands of GBP for readability
    labels = [f"{c/1000:,.0f}k" for c in centers]
    dist_df = pd.DataFrame({
        "Unhedged": un_counts,
        "Hedged":   hd_counts,
    }, index=labels)
    st.bar_chart(dist_df, height=300)

    # --- Raw positions ---
    st.subheader("Position book")
    pos_df = pd.DataFrame([{
        "currency": c,
        "signed notional": signed[c],
        "hedge ratio": hedge_ratios[c],
        "residual exposure": residual[c],
    } for c in signed])
    st.dataframe(pos_df, use_container_width=True)


if __name__ == "__main__":
    main()
