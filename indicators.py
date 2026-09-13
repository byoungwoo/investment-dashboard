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


def trend_metrics(
    closes: pd.Series,
    benchmark_closes: pd.Series,
    slope_lookback: int = 20,
    relative_lookback: int = 63,
    now=None,
) -> dict:
    """Inputs for the lab-only Trend Health shadow signal."""
    clean = pd.to_numeric(closes, errors="coerce").dropna()
    benchmark = pd.to_numeric(benchmark_closes, errors="coerce").dropna()

    ma50_series = clean.rolling(50).mean()
    ma200_series = clean.rolling(200).mean()
    price = float(clean.iloc[-1]) if not clean.empty else float("nan")
    ma50 = float(ma50_series.iloc[-1]) if not ma50_series.empty else float("nan")
    ma200 = float(ma200_series.iloc[-1]) if not ma200_series.empty else float("nan")

    valid_ma200 = ma200_series.dropna()
    ma200_previous = (
        float(valid_ma200.iloc[-(slope_lookback + 1)])
        if len(valid_ma200) > slope_lookback
        else float("nan")
    )
    ma200_slope = (
        (ma200 / ma200_previous - 1) * 100
        if pd.notna(ma200) and pd.notna(ma200_previous) and ma200_previous != 0
        else float("nan")
    )
    dev200 = (
        (price / ma200 - 1) * 100
        if pd.notna(price) and pd.notna(ma200) and ma200 != 0
        else float("nan")
    )
    ma_spread = (
        (ma50 / ma200 - 1) * 100
        if pd.notna(ma50) and pd.notna(ma200) and ma200 != 0
        else float("nan")
    )

    stock_return = (
        (float(clean.iloc[-1]) / float(clean.iloc[-(relative_lookback + 1)]) - 1) * 100
        if len(clean) > relative_lookback
        else float("nan")
    )
    benchmark_return = (
        (float(benchmark.iloc[-1]) / float(benchmark.iloc[-(relative_lookback + 1)]) - 1) * 100
        if len(benchmark) > relative_lookback
        else float("nan")
    )
    relative_strength = stock_return - benchmark_return

    def is_fresh(series: pd.Series) -> bool:
        if series.empty:
            return False
        latest = pd.Timestamp(series.index[-1])
        reference = pd.Timestamp(now) if now is not None else pd.Timestamp.now(tz=latest.tz)
        if latest.tz is None and reference.tz is not None:
            reference = reference.tz_localize(None)
        elif latest.tz is not None and reference.tz is None:
            reference = reference.tz_localize(latest.tz)
        return 0 <= (reference.normalize() - latest.normalize()).days <= 4

    return {
        "dev200": dev200,
        "ma200_slope": ma200_slope,
        "ma_spread": ma_spread,
        "relative_strength": relative_strength,
        "stock_return_63d": stock_return,
        "benchmark_return_63d": benchmark_return,
        "history_points": len(clean),
        "benchmark_points": len(benchmark),
        "latest_date": None if clean.empty else pd.Timestamp(clean.index[-1]).date().isoformat(),
        "price_fresh": is_fresh(clean),
        "benchmark_fresh": is_fresh(benchmark),
    }
