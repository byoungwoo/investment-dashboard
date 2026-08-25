import requests
import yfinance as yf
import pandas as pd

try:
    import streamlit as st
    FRED_API_KEY = st.secrets.get("FRED_API_KEY", "") or __import__("config").FRED_API_KEY
except Exception:
    from config import FRED_API_KEY

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


def fetch_macro() -> dict:
    result = {}
    source = "FRED"

    # FRED 시도
    fred_map = [("t10y", "DGS10"), ("t30y", "DGS30"), ("t10y2y", "T10Y2Y")]
    for key, series_id in fred_map:
        try:
            result[key] = _fred_latest(series_id)
        except Exception:
            result[key] = None

    # FRED 실패 시 yfinance fallback (^TNX=10Y, ^TYX=30Y)
    if result.get("t10y") is None:
        try:
            result["t10y"] = _yf_yield("^TNX") / 10  # ^TNX는 x10 스케일
            source = "yfinance"
        except Exception:
            pass
    if result.get("t30y") is None:
        try:
            result["t30y"] = _yf_yield("^TYX") / 10
            source = "yfinance"
        except Exception:
            pass
    if result.get("t10y2y") is None and result.get("t10y") and result.get("t30y"):
        # T10Y2Y 근사값: 별도 fetch 불가 시 None 유지
        pass

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
