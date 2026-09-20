"""
FX rate loader.

Reads a locally-cached CSV of daily FX rates and provides them as a tidy
DataFrame. The cache is written by src/fetch_ecb.py (and later
src/fetch_boe.py) so that day-to-day runs never hit the network.
"""
from pathlib import Path
from typing import Iterable

import pandas as pd


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
CACHE_PATH = DATA_DIR / "fx_rates.csv"


def load_fx_rates(
    currencies: Iterable[str],
    start: str,
    end: str,
    base: str = "GBP",
) -> pd.DataFrame:
    """
    Return daily FX rates for the requested currencies as *foreign -> base*.

    The cache stores EUR-based rates (EUR -> CCY). This function converts
    them to the requested base on load, so callers always see the rates
    they need.

    Parameters
    ----------
    currencies : iterable of str
        Currency codes (e.g. ["USD", "EUR", "JPY", "CHF"]).
    start, end : str
        Inclusive date range, ISO format ("2020-01-01").
    base : str
        Base currency code. Must be present in the cache. Default "GBP".

    Returns
    -------
    DataFrame indexed by date, columns are the requested currencies
    (excluding base), values are *foreign -> base* rates.
    """
    if not CACHE_PATH.exists():
        raise FileNotFoundError(
            f"No FX cache at {CACHE_PATH}. "
            "Run `python src/fetch_ecb.py` first."
        )

    fx_eur = pd.read_csv(CACHE_PATH, index_col=0, parse_dates=True)

    needed = set(currencies) | {base}
    missing = needed - set(fx_eur.columns)
    if missing:
        raise ValueError(
            f"Cache missing currencies {sorted(missing)}. "
            f"Available: {sorted(fx_eur.columns)}"
        )

    # Slice by date
    fx_eur = fx_eur.sort_index().loc[start:end]

    # Convert EUR->CCY to CCY->base using EUR as pivot:
    #   CCY -> base = (EUR -> base) / (EUR -> CCY)
    base_series = fx_eur[base]
    fx_base = fx_eur.rdiv(base_series, axis=0)  # EUR->base divided by EUR->CCY

    # Drop the base column itself and the pivot EUR if not requested
    cols = [c for c in currencies if c != base]
    return fx_base[cols]
