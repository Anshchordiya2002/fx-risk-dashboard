"""
Report outputs: CSV saves and static charts for the README.

Charts use the matplotlib Agg backend so they work headless (no display
required), which matters for CI and for running on servers.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


OUT_DIR = Path(__file__).resolve().parent.parent / "outputs"
OUT_DIR.mkdir(exist_ok=True)


def save_summary(df: pd.DataFrame, filename: str) -> Path:
    """Save a DataFrame to outputs/<filename>."""
    path = OUT_DIR / filename
    df.round(4).to_csv(path)
    return path


def plot_rolling_var(
    roll_unhedged: pd.Series,
    roll_hedged: pd.Series,
    filename: str = "rolling_var.png",
) -> Path:
    """Rolling 1-year VaR 99%: unhedged vs hedged."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(roll_unhedged.index, roll_unhedged.values,
            label="Unhedged", linewidth=1.4)
    ax.plot(roll_hedged.index, roll_hedged.values,
            label="Hedged", linewidth=1.4)
    ax.set_title("Rolling 1-year VaR (99%, historical)")
    ax.set_ylabel("VaR (base currency)")
    ax.set_xlabel("Date")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()

    path = OUT_DIR / filename
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_hedged_vs_unhedged_histogram(
    pnl_unhedged: pd.Series,
    pnl_hedged: pd.Series,
    bins: int = 40,
    filename: str = "hedged_vs_unhedged_histogram.png",
) -> Path:
    """Overlaid histograms of daily P&L, unhedged vs hedged."""
    fig, ax = plt.subplots(figsize=(10, 5))
    un = pnl_unhedged.dropna().values
    hd = pnl_hedged.dropna().values
    lo = float(min(un.min(), hd.min()))
    hi = float(max(un.max(), hd.max()))
    edges = np.linspace(lo, hi, bins + 1)

    ax.hist(un, bins=edges, alpha=0.55, label="Unhedged", color="steelblue")
    ax.hist(hd, bins=edges, alpha=0.55, label="Hedged",   color="darkorange")
    ax.set_title("Daily P&L distribution: unhedged vs hedged")
    ax.set_xlabel("Daily P&L (base currency)")
    ax.set_ylabel("Frequency")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()

    path = OUT_DIR / filename
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path
