import math
from typing import Optional

from config import WEIGHTS, GRADE_THRESHOLDS, NEUTRAL_RATE


def _clamp(v: float, lo: float = 0, hi: float = 100) -> float:
    if not math.isfinite(v):
        raise ValueError("score input must be finite")
    return max(lo, min(hi, v))


def _is_finite(value) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


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
) -> tuple[Optional[float], str]:
    dev200 = ma.get("dev200")
    missing = []
    if not _is_finite(rsi_val):
        missing.append("RSI")
    if not (_is_finite(stoch_k) and _is_finite(stoch_d)):
        missing.append("Stoch")
    if not _is_finite(dev200):
        missing.append("200MA")

    if missing:
        return None, f"N/A: {', '.join(missing)}"

    # RSI: oversold(30-) = high, overbought(70+) = low
    rsi_s = _clamp(95 - (rsi_val - 20) * 1.25)

    # Slow Stochastic
    avg_stoch = (stoch_k + stoch_d) / 2
    stoch_s = _clamp(95 - avg_stoch * 0.9)

    # Distance from 200MA: below 200MA = attractive
    ma_s = _clamp(65 - dev200 * 0.9)

    # Golden cross bonus
    if ma["golden_cross"]:
        ma_s = _clamp(ma_s + 5)

    score = rsi_s * 0.35 + stoch_s * 0.35 + ma_s * 0.30
    detail = f"RSI={rsi_val:.0f} Stoch={avg_stoch:.0f} vs200={dev200:+.0f}%"
    return _clamp(score), detail


# ── Lab shadow signals (do not affect Price Score or Grade) ───────────────────

def opportunity_score(
    valuation: float,
    valuation_detail: str,
    rsi_val: float,
    stoch_k: float,
    stoch_d: float,
) -> tuple[Optional[float], str, dict]:
    missing = []
    if valuation_detail == "N/A" or not _is_finite(valuation):
        missing.append("Valuation")
    if not _is_finite(rsi_val):
        missing.append("RSI")
    if not (_is_finite(stoch_k) and _is_finite(stoch_d)):
        missing.append("Stoch")
    if missing:
        return None, f"N/A: {', '.join(missing)}", {}

    rsi_entry = _clamp((70 - rsi_val) / 40 * 100)
    stoch_avg = (stoch_k + stoch_d) / 2
    stoch_entry = _clamp(100 - stoch_avg)
    score = _clamp(valuation * 0.60 + rsi_entry * 0.20 + stoch_entry * 0.20)
    breakdown = {
        "valuation": round(valuation, 1),
        "rsi_entry": round(rsi_entry, 1),
        "stoch_entry": round(stoch_entry, 1),
    }
    return score, "Val 60% + RSI Entry 20% + Stoch Entry 20%", breakdown


def trend_health_score(metrics: dict) -> tuple[Optional[float], str, dict]:
    required = {
        "Price/200MA": metrics.get("dev200"),
        "200MA Slope": metrics.get("ma200_slope"),
        "MA Structure": metrics.get("ma_spread"),
        "Relative Strength": metrics.get("relative_strength"),
    }
    missing = [label for label, value in required.items() if not _is_finite(value)]
    if missing:
        return None, f"N/A: {', '.join(missing)}", {}

    position = _clamp(50 + 2.5 * required["Price/200MA"])
    slope = _clamp(50 + 10 * required["200MA Slope"])
    structure = _clamp(50 + 5 * required["MA Structure"])
    relative = _clamp(50 + 2.5 * required["Relative Strength"])
    score = _clamp(
        position * 0.30
        + slope * 0.30
        + structure * 0.20
        + relative * 0.20
    )
    breakdown = {
        "price_position": round(position, 1),
        "ma200_slope": round(slope, 1),
        "ma_structure": round(structure, 1),
        "relative_strength": round(relative, 1),
    }
    return score, "Position 30% + Slope 30% + Structure 20% + Relative 20%", breakdown


def data_confidence(
    valuation: float,
    valuation_detail: str,
    rsi_val: float,
    stoch_k: float,
    stoch_d: float,
    metrics: dict,
) -> tuple[float, str, str]:
    checks = {
        "Valuation": valuation_detail != "N/A" and _is_finite(valuation),
        "RSI": _is_finite(rsi_val),
        "Slow Stoch": _is_finite(stoch_k) and _is_finite(stoch_d),
        "Price/200MA": _is_finite(metrics.get("dev200")),
        "200MA Slope": _is_finite(metrics.get("ma200_slope")),
        "MA Structure": _is_finite(metrics.get("ma_spread")),
        "Relative Strength": _is_finite(metrics.get("relative_strength")),
        "History 220+": metrics.get("history_points", 0) >= 220,
        "Benchmark 64+": metrics.get("benchmark_points", 0) >= 64,
        "Latest Bars": bool(metrics.get("price_fresh")) and bool(metrics.get("benchmark_fresh")),
    }
    passed = sum(checks.values())
    score = passed / len(checks) * 100
    label = "HIGH" if score >= 90 else "MEDIUM" if score >= 70 else "LOW"
    failed = [label for label, ok in checks.items() if not ok]
    detail = f"{passed}/{len(checks)} valid"
    if failed:
        detail += f" · Missing: {', '.join(failed)}"
    return score, label, detail


def shadow_diagnosis(opportunity: Optional[float], trend: Optional[float]) -> str:
    if opportunity is None or trend is None:
        return "데이터 부족 — Shadow 진단 N/A"
    if opportunity >= 65 and trend >= 60:
        return "★ 가격 매력 + 건강한 추세"
    if opportunity >= 65:
        return "⚠ 싸지만 추세 확인 필요"
    if trend >= 60:
        return "↑ 추세는 건강하지만 가격 매력 제한"
    return "✕ 가격 매력과 추세 모두 약함"


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
    if not _is_finite(value) or history is None:
        return None
    clean = history.dropna()
    clean = clean[clean.map(_is_finite)]
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
        "heat": None if not _is_finite(fear_greed) else _clamp(fear_greed),
    }

    available = [
        c for c in components.values()
        if c["heat"] is not None and c["weight"] > 0
    ]
    total_weight = sum(c["weight"] for c in available)
    missing = [
        c["label"] for c in components.values()
        if c["heat"] is None and c["weight"] > 0
    ]
    if missing:
        detail = (
            f"데이터 가용률: {total_weight * 100:.0f}% · "
            f"누락: {', '.join(missing)}"
        )
        return None, "N/A", detail, components

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


def price_score(val: float, tech: Optional[float], macro: float) -> Optional[float]:
    if tech is None:
        return None
    return (
        val * WEIGHTS["valuation"]
        + tech * WEIGHTS["technical"]
        + macro * WEIGHTS["macro"]
    )


def to_grade(score: Optional[float]) -> tuple[str, str]:
    if score is None:
        return "N/A", "N/A"
    for threshold, grade, action in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade, action
    return "D", "No Chase / Reduce"
