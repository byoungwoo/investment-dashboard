import requests
import yfinance as yf
import pandas as pd

try:
    import streamlit as st
    FRED_API_KEY = st.secrets.get("FRED_API_KEY", "") or __import__("config").FRED_API_KEY
except Exception:
    from config import FRED_API_KEY

from config import NEUTRAL_RATE

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"


def fetch_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    return yf.Ticker(ticker).history(period=period)


def fetch_info(ticker: str) -> dict:
    return yf.Ticker(ticker).info


def _fred_latest(series_id: str):
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 5,
    }
    resp = requests.get(FRED_BASE, params=params, timeout=30)
    resp.raise_for_status()
    for obs in resp.json()["observations"]:
        if obs["value"] != ".":
            return float(obs["value"])
    return None


def _fred_history(series_id: str, limit: int = 100000) -> pd.Series:
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "asc",
        "limit": limit,
    }
    resp = requests.get(FRED_BASE, params=params, timeout=30)
    resp.raise_for_status()

    values = []
    dates = []
    for obs in resp.json()["observations"]:
        if obs["value"] == ".":
            continue
        dates.append(pd.to_datetime(obs["date"]))
        values.append(float(obs["value"]))

    return pd.Series(values, index=dates, name=series_id)


def _fred_observations(series_id: str, limit: int = 80) -> list[float]:
    """Last N valid observations for a FRED series, newest first."""
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": limit + 20,
    }
    resp = requests.get(FRED_BASE, params=params, timeout=30)
    resp.raise_for_status()
    vals = [float(o["value"]) for o in resp.json()["observations"] if o["value"] != "."]
    return vals[:limit]


def fetch_ffr() -> float:
    """Effective Federal Funds Rate (FRED: DFF)."""
    return _fred_latest("DFF")


def fetch_2y_change(lookback: int = 65) -> float:
    """2Y Treasury change over ~3 months (65 business days)."""
    obs = _fred_observations("DGS2", lookback)
    if len(obs) < 2:
        return 0.0
    return round(obs[0] - obs[-1], 3)


def fetch_tips() -> float:
    """10Y TIPS real yield (FRED: DFII10). Falls back to 10Y − breakeven."""
    try:
        val = _fred_latest("DFII10")
        if val is not None:
            return val
    except Exception:
        pass
    try:
        t10 = _fred_latest("DGS10")
        be  = _fred_latest("T10YIE")
        if t10 and be:
            return round(t10 - be, 3)
    except Exception:
        pass
    return 1.5


def fetch_vix() -> float:
    hist = yf.Ticker("^VIX").history(period="2d")
    return float(hist["Close"].iloc[-1])


def fetch_vix_history(period: str = "10y") -> pd.Series:
    hist = yf.Ticker("^VIX").history(period=period)
    return hist["Close"].dropna()


def fetch_fear_greed() -> dict:
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
        "Referer": "https://edition.cnn.com/",
        "Origin": "https://edition.cnn.com",
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()["fear_and_greed"]
    return {
        "score": round(float(data["score"]), 1),
        "rating": data["rating"],
    }


def _yf_yield(ticker: str) -> float:
    hist = yf.Ticker(ticker).history(period="2d")
    return float(hist["Close"].iloc[-1])


def _normalize_yf_yield(value: float) -> float:
    """Yahoo Treasury tickers may return either 4.7 or 47 style values."""
    return value / 10 if value > 20 else value


def fetch_macro() -> dict:
    result = {}
    source = "FRED"

    fred_map = [("t10y", "DGS10"), ("t30y", "DGS30"), ("t10y2y", "T10Y2Y"), ("ffr", "DFF")]
    for key, series_id in fred_map:
        try:
            result[key] = _fred_latest(series_id)
        except Exception:
            result[key] = None

    # 2Y 3-month direction signal
    try:
        result["delta_2y"] = fetch_2y_change()
    except Exception:
        result["delta_2y"] = 0.0

    # TIPS real yield (with fallback)
    try:
        result["tips"] = fetch_tips()
    except Exception:
        result["tips"] = 1.5

    # yfinance fallback for rate levels
    if result.get("t10y") is None:
        try:
            result["t10y"] = _normalize_yf_yield(_yf_yield("^TNX"))
            source = "yfinance"
        except Exception:
            pass
    if result.get("t30y") is None:
        try:
            result["t30y"] = _normalize_yf_yield(_yf_yield("^TYX"))
            source = "yfinance"
        except Exception:
            pass

    result["neutral_rate"] = NEUTRAL_RATE
    result["_source"] = source
    return result


def fetch_marks_temperature_data() -> dict:
    series_map = {
        "hy_spread": "BAMLH0A0HYM2",
        "nfci": "NFCI",
        "sloos": "DRTSCILM",
    }
    result = {}

    for key, series_id in series_map.items():
        try:
            history = _fred_history(series_id)
            latest = history.dropna().iloc[-1]
            latest_date = history.dropna().index[-1].date().isoformat()
            result[key] = {
                "series_id": series_id,
                "value": float(latest),
                "date": latest_date,
                "history": history,
            }
        except Exception as e:
            result[key] = {
                "series_id": series_id,
                "value": None,
                "date": None,
                "history": pd.Series(dtype=float),
                "error": str(e),
            }

    return result
