import pandas as pd


def rsi(closes: pd.Series, period: int = 14) -> float:
    delta = closes.diff()
    gain = delta.clip(lower=0).ewm(com=period - 1, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(com=period - 1, min_periods=period).mean()
    rs = gain / loss
    return float((100 - 100 / (1 + rs)).iloc[-1])


def slow_stochastic(
    high: pd.Series, low: pd.Series, close: pd.Series,
    k_period: int = 14, smooth: int = 3,
) -> tuple[float, float]:
    ll = low.rolling(k_period).min()
    hh = high.rolling(k_period).max()
    fast_k = 100 * (close - ll) / (hh - ll)
    slow_k = fast_k.rolling(smooth).mean()
    slow_d = slow_k.rolling(smooth).mean()
    return float(slow_k.iloc[-1]), float(slow_d.iloc[-1])


def ma_deviation(closes: pd.Series) -> dict:
    price = float(closes.iloc[-1])
    ma50 = float(closes.rolling(50).mean().iloc[-1])
    ma200 = float(closes.rolling(200).mean().iloc[-1])
    return {
        "price": price,
        "ma50": ma50,
        "ma200": ma200,
        "dev50": (price - ma50) / ma50 * 100,
        "dev200": (price - ma200) / ma200 * 100,
        "golden_cross": ma50 > ma200,
    }
