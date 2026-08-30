from config import WEIGHTS, GRADE_THRESHOLDS, NEUTRAL_RATE
from typing import Optional


def _clamp(v: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, v))


# ── Macro Score v2.3 helpers ────────────────────────────────────────────────────

def _rate_level_score(t10: float, t30: float) -> tuple[float, dict]:
    t10_s = _clamp(105 - t10 * 14)
    t30_s = _clamp(105 - t30 * 13)
    score = _clamp(t10_s * 0.75 + t30_s * 0.25)
    return score, {"t10_s": round(t10_s, 1), "t30_s": round(t30_s, 1)}


def _fed_policy_signal(ffr: float, neutral_rate: float, delta_2y: float, tips: float) -> tuple[float, dict]:
    gap     = ffr - neutral_rate
    ffr_s   = _clamp(60 - gap * 15)
    delta_s = _clamp(60 - delta_2y * 45)
    tips_s  = _clamp(75 - tips * 20)
    score   = _clamp(ffr_s * 0.35 + delta_s * 0.25 + tips_s * 0.40)
    return score, {
        "ffr_s":   round(ffr_s, 1),
        "delta_s": round(delta_s, 1),
        "tips_s":  round(tips_s, 1),
        "gap":     round(gap, 2),
    }


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


def macro_score(macro: dict, vix: float = 20.0) -> tuple[float, str, dict]:
    t10          = macro.get("t10y")         or 4.3
    t30          = macro.get("t30y")         or 4.6
    ffr          = macro.get("ffr")          or 5.25
    neutral_rate = macro.get("neutral_rate") or NEUTRAL_RATE
    delta_2y     = macro.get("delta_2y")     or 0.0
    tips         = macro.get("tips")         or 1.5

    # VIX > 25 → stress regime: Fed Policy Signal weight expands
    stress = vix > 25
    rate_w = 0.70 if stress else 0.80
    fed_w  = 0.30 if stress else 0.20

    rate_s, rate_bd = _rate_level_score(t10, t30)
    fed_s, fed_bd   = _fed_policy_signal(ffr, neutral_rate, delta_2y, tips)
    final = _clamp(rate_s * rate_w + fed_s * fed_w)

    detail = f"10Y={t10:.2f}% FFR={ffr:.2f}% TIPS={tips:.2f}%"
    breakdown = {
        "rate_score":    round(rate_s, 1),
        "fed_score":     round(fed_s, 1),
        "rate_weight":   rate_w,
        "fed_weight":    fed_w,
        "stress_regime": stress,
        "final_score":   round(final),
        "rate_detail":   rate_bd,
        "fed_detail":    fed_bd,
        "inputs": {
            "t10y": t10, "t30y": t30,
            "ffr": ffr, "neutral_rate": neutral_rate,
            "delta_2y": delta_2y, "tips": tips,
            "vix": vix,
        },
    }
    return final, detail, breakdown


def macro_status(score: float) -> str:
    if score >= 80:
        return "🟢 Strong Risk-On"
    if score >= 65:
        return "🟢 Risk-On"
    if score >= 50:
        return "🟡 Neutral"
    if score >= 35:
        return "🟠 Caution"
    return "🔴 Risk-Off"


def yield_curve_status(macro: dict) -> str:
    t10 = macro.get("t10y")
    t30 = macro.get("t30y")
    t10y2y = macro.get("t10y2y")

    warnings = []
    if t10 is not None:
        if t10 > 4.80:
            warnings.append("10Y Red")
        elif t10 >= 4.50:
            warnings.append("10Y Orange")

    if t30 is not None:
        if t30 > 5.30:
            warnings.append("30Y Red")
        elif t30 >= 5.00:
            warnings.append("30Y Orange")

    if t10y2y is not None:
        if t10y2y < 0:
            warnings.append("Curve Inverted")
        elif t10y2y < 0.30:
            warnings.append("Curve Red")
        elif t10y2y < 0.50:
            warnings.append("Curve Orange")

    if any("Red" in warning or "Inverted" in warning for warning in warnings):
        return "🔴 Red / " + " · ".join(warnings)
    if warnings:
        return "🟠 Orange / " + " · ".join(warnings)
    return "🟢 Green"


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
