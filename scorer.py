from config import WEIGHTS, GRADE_THRESHOLDS
from typing import Optional


def _clamp(v: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, v))


def valuation_score(info: dict) -> tuple[float, str]:
    fpe = info.get("forwardPE")
    peg = info.get("pegRatio")

    if not fpe or fpe <= 0:
        return 50.0, "N/A"

    # Forward PE → raw score
    pe_score = _clamp(
        110 - fpe * 1.8 if fpe < 50 else 20 - (fpe - 50) * 0.3
    )

    # PEG blends in when available (growth-adjusted view)
    if peg and peg > 0:
        peg_score = _clamp(95 - peg * 25)
        score = pe_score * 0.55 + peg_score * 0.45
        detail = f"fPE={fpe:.1f} PEG={peg:.2f}"
    else:
        score = pe_score
        detail = f"fPE={fpe:.1f}"

    return _clamp(score), detail


def technical_score(
    rsi_val: float,
    stoch_k: float,
    stoch_d: float,
    ma: dict,
) -> tuple[float, str]:
    # RSI: oversold(30-) = high, overbought(70+) = low
    rsi_s = _clamp(95 - (rsi_val - 20) * 1.25)

    # Slow Stochastic
    avg_stoch = (stoch_k + stoch_d) / 2
    stoch_s = _clamp(95 - avg_stoch * 0.9)

    # Distance from 200MA: below 200MA = attractive
    dev200 = ma["dev200"]
    ma_s = _clamp(65 - dev200 * 0.9)

    # Golden cross bonus
    if ma["golden_cross"]:
        ma_s = _clamp(ma_s + 5)

    score = rsi_s * 0.35 + stoch_s * 0.35 + ma_s * 0.30
    detail = f"RSI={rsi_val:.0f} Stoch={avg_stoch:.0f} vs200={dev200:+.0f}%"
    return _clamp(score), detail


def macro_score(macro: dict) -> tuple[float, str]:
    t10 = macro.get("t10y") or 4.3
    t30 = macro.get("t30y") or 4.6
    t10y2y = macro.get("t10y2y") or 0.0

    # Higher yield = lower score (risk-free competition)
    t10_s = _clamp(105 - t10 * 14)
    t30_s = _clamp(105 - t30 * 13)

    # Yield curve: inverted = cautious
    curve_s = _clamp(60 + t10y2y * 20)

    score = t10_s * 0.40 + t30_s * 0.40 + curve_s * 0.20
    detail = f"10Y={t10:.2f}% 30Y={t30:.2f}% curve={t10y2y:+.2f}%"
    return _clamp(score), detail


def _percentile(value: float, history) -> Optional[float]:
    if value is None or history is None:
        return None
    clean = history.dropna()
    if clean.empty:
        return None
    return float((clean <= value).mean() * 100)


def marks_temperature_score(
    marks_data: dict,
    vix: Optional[float] = None,
    vix_history=None,
    fear_greed: Optional[float] = None,
) -> tuple[Optional[float], str, str, dict]:
    components = {}

    fred_specs = {
        "hy_spread": ("HY Spread", 0.30, "lower_is_hot"),
        "nfci": ("NFCI", 0.25, "lower_is_hot"),
        "sloos": ("SLOOS", 0.15, "lower_is_hot"),
    }

    for key, (label, weight, direction) in fred_specs.items():
        item = marks_data.get(key, {})
        value = item.get("value")
        pct = _percentile(value, item.get("history"))
        heat = None if pct is None else (100 - pct if direction == "lower_is_hot" else pct)
        components[key] = {
            "label": label,
            "weight": weight,
            "value": value,
            "date": item.get("date"),
            "heat": None if heat is None else _clamp(heat),
        }

    vix_pct = _percentile(vix, vix_history)
    components["vix"] = {
        "label": "VIX",
        "weight": 0.15,
        "value": vix,
        "date": None,
        "heat": None if vix_pct is None else _clamp(100 - vix_pct),
    }

    components["fear_greed"] = {
        "label": "Fear & Greed",
        "weight": 0.15,
        "value": fear_greed,
        "date": None,
        "heat": None if fear_greed is None else _clamp(fear_greed),
    }

    available = [
        c for c in components.values()
        if c["heat"] is not None and c["weight"] > 0
    ]
    if not available:
        return None, "—", "No data", components

    total_weight = sum(c["weight"] for c in available)
    score = sum(c["heat"] * c["weight"] for c in available) / total_weight
    score = _clamp(score)

    if score < 20:
        label = "❄️ Extreme Fear"
    elif score < 40:
        label = "🧊 Cool"
    elif score < 60:
        label = "Neutral"
    elif score < 80:
        label = "🔥 Warm"
    else:
        label = "🔥🔥 Hot"

    detail = " · ".join(
        f"{c['label']}={c['heat']:.0f}"
        for c in components.values()
        if c["heat"] is not None
    )
    return score, label, detail, components


def price_score(val: float, tech: float, macro: float) -> float:
    return (
        val * WEIGHTS["valuation"]
        + tech * WEIGHTS["technical"]
        + macro * WEIGHTS["macro"]
    )


def to_grade(score: float) -> tuple[str, str]:
    for threshold, grade, action in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade, action
    return "D", "No Chase / Reduce"
