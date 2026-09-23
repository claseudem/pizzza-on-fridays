import numpy as np
import pandas as pd

from app.models import market_data


class _FakeTicker:
    """Imita ``yf.Ticker`` con la tabla que devuelve ``get_earnings_dates``."""

    def __init__(self, ticker):
        self.ticker = ticker

    def get_earnings_dates(self, limit):
        index = pd.DatetimeIndex(
            ["2025-12-10 06:00", "2026-09-29 08:00", "2026-06-09 06:00"], tz="America/New_York", name="Earnings Date"
        )
        return pd.DataFrame(
            {
                "EPS Estimate": [-0.01, -0.01, np.nan],
                "Reported EPS": [-0.05, np.nan, -0.07],
                "Surprise(%)": [-262.0, np.nan, np.nan],
            },
            index=index,
        )


def test_get_earnings_parses_yfinance_table(monkeypatch):
    market_data._cache.clear()
    monkeypatch.setattr(market_data.yf, "Ticker", _FakeTicker)

    earnings = market_data.get_earnings("UEC")

    # Ordenados del más reciente al más antiguo, con NaN convertidos a None.
    assert [pd.Timestamp(e["time"], unit="s").date().isoformat() for e in earnings] == [
        "2026-09-29",
        "2026-06-09",
        "2025-12-10",
    ]
    assert earnings[0]["eps_reported"] is None  # reporte futuro
    assert earnings[1]["eps_estimate"] is None
    assert earnings[2] == {
        "time": earnings[2]["time"],
        "eps_estimate": -0.01,
        "eps_reported": -0.05,
        "surprise_percent": -262.0,
    }


def test_get_earnings_returns_empty_list_when_yfinance_fails(monkeypatch):
    market_data._cache.clear()

    class _Broken:
        def __init__(self, ticker):
            pass

        def get_earnings_dates(self, limit):
            raise RuntimeError("Yahoo no responde")

    monkeypatch.setattr(market_data.yf, "Ticker", _Broken)
    assert market_data.get_earnings("UEC") == []
