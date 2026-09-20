"""
Configuration for the FX Risk Metrics Dashboard.

Defines the FX position book (currencies, notionals, directions), the
base currency, and the risk parameters (confidence levels, horizon).

This is the file a risk analyst would edit to model a client's portfolio.
"""
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class FXPosition:
    """A single FX position: buy or sell `notional` units of `currency`."""
    currency: str          # e.g. "USD", "EUR", "JPY"
    notional: float        # absolute size in the foreign currency
    direction: str = "long"  # "long" = bought foreign ccy, "short" = sold

    def signed_notional(self) -> float:
        """+notional for long, -notional for short."""
        if self.direction not in ("long", "short"):
            raise ValueError(f"direction must be 'long' or 'short', got {self.direction!r}")
        return self.notional if self.direction == "long" else -self.notional


@dataclass
class RiskConfig:
    base_currency: str = "GBP"
    confidence_levels: List[float] = field(default_factory=lambda: [0.95, 0.99])
    horizon_days: int = 1
    lookback_days: int = 500           # rolling window for historical VaR
    stress_windows: Dict[str, tuple] = field(default_factory=lambda: {
        "Brexit 2016":         ("2016-06-20", "2016-07-15"),
        "COVID crash 2020":    ("2020-02-20", "2020-03-31"),
        "Gilt crisis 2022":    ("2022-09-20", "2022-10-14"),
    })

    def validate(self) -> None:
        for c in self.confidence_levels:
            if not 0.5 < c < 1.0:
                raise ValueError(f"confidence level must be in (0.5, 1.0), got {c}")
        if self.horizon_days < 1:
            raise ValueError("horizon_days must be >= 1")
        if self.lookback_days < 30:
            raise ValueError("lookback_days must be >= 30")


@dataclass
class PortfolioConfig:
    """The full configuration: FX positions + risk parameters."""
    positions: List[FXPosition] = field(default_factory=lambda: [
        FXPosition("USD", 6_000_000, "long"),
        FXPosition("EUR", 4_000_000, "long"),
        FXPosition("JPY", 500_000_000, "long"),   # ~£2.5m
        FXPosition("CHF", 1_500_000, "long"),
    ])
    risk: RiskConfig = field(default_factory=RiskConfig)

    def validate(self) -> None:
        self.risk.validate()
        seen = set()
        for p in self.positions:
            if p.currency == self.risk.base_currency:
                raise ValueError(f"position in base currency {p.currency} is a no-op")
            if p.currency in seen:
                raise ValueError(f"duplicate position in {p.currency}; net them first")
            seen.add(p.currency)
            if p.notional <= 0:
                raise ValueError(f"notional must be positive, got {p.notional}")

    def currencies(self) -> List[str]:
        return [p.currency for p in self.positions]
