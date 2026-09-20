"""
One-off fetcher: pull daily EUR-based FX rates from the ECB Data Portal
and write them to data/fx_rates.csv.

Run once (or whenever you want to refresh the cache):

    python src/fetch_ecb.py

Source: https://data.ecb.europa.eu/
No API key, no rate limit.
"""
import io
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests


ECB_URL = (
    "https://data-api.ecb.europa.eu/service/data/EXR/"
    "D.{ccy}.EUR.SP00.A?format=csvdata"
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
CACHE_PATH = DATA_DIR / "fx_rates.csv"

DEFAULT_CURRENCIES = ["USD", "EUR", "JPY", "CHF", "GBP"]


def fetch_ecb_rate(ccy: str, timeout: int = 30) -> pd.DataFrame:
    """Fetch the ECB daily EUR -> CCY reference rate."""
    if ccy == "EUR":
        raise ValueError("EUR is the ECB base; no fetch needed.")
    url = ECB_URL.format(ccy=ccy)
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df = df[["TIME_PERIOD", "OBS_VALUE"]].rename(
        columns={"TIME_PERIOD": "date", "OBS_VALUE": ccy}
    )
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date").sort_index()


def fetch_all(currencies: Iterable[str]) -> pd.DataFrame:
    """Fetch EUR->CCY rates for all currencies and merge on date."""
    cols = [c for c in currencies if c != "EUR"]
    frames = [fetch_ecb_rate(c) for c in cols]
    df = pd.concat(frames, axis=1)
    df["EUR"] = 1.0
    return df.sort_index()


def main() -> None:
    print(f"Fetching {DEFAULT_CURRENCIES} from ECB ...")
    fx = fetch_all(DEFAULT_CURRENCIES)
    fx.to_csv(CACHE_PATH)
    print(f"Wrote {len(fx):,} rows to {CACHE_PATH}")
    print(f"Date range: {fx.index.min().date()} -> {fx.index.max().date()}")
    print(f"Columns:    {list(fx.columns)}")


if __name__ == "__main__":
    main()
