import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import json
import html

from config import PORTFOLIO
from fetcher import (
    fetch_history,
    fetch_info,
    fetch_macro,
    fetch_vix,
    fetch_vix_history,
    fetch_fear_greed,
    fetch_marks_temperature_data,
    fetch_sp500_valuation,
)
from indicators import rsi, slow_stochastic, ma_deviation, trend_metrics
from scorer import (
    data_confidence,
    valuation_score,
    technical_score,
    opportunity_score,
    trend_health_score,
    shadow_diagnosis,
    macro_score,
    macro_status,
    marks_temperature_score,
    price_score,
    yield_curve_status,
    to_grade,
)

st.set_page_config(page_title="LBW Portfolio", page_icon="📊", layout="centered")

st.markdown(
    """
    <style>
    .stHeading a {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

STARS = {5: "★★★★★", 4: "★★★★☆", 3: "★★★☆☆", 2: "★★☆☆☆", 1: "★☆☆☆☆"}

GRADE_COLOR = {
    "S": "#c084fc",
    "A": "#4ade80",
    "B": "#86efac",
    "C": "#fbbf24",
    "D": "#f87171",
}


@st.cache_data(ttl=900)
def load_macro():
    return fetch_macro()

@st.cache_data(ttl=900)
def load_vix():
    return fetch_vix()

@st.cache_data(ttl=900)
def load_fear_greed():
    return fetch_fear_greed()


@st.cache_data(ttl=900)
def load_vix_history():
    return fetch_vix_history()


@st.cache_data(ttl=900)
def load_marks_temperature_data():
    return fetch_marks_temperature_data()


@st.cache_data(ttl=21600)
def load_sp500_valuation():
    return fetch_sp500_valuation()


@st.cache_data(ttl=900)
def load_history(ticker: str):
    return fetch_history(ticker)


@st.cache_data(ttl=900)
def load_ticker(ticker: str):
    hist = load_history(ticker)
    info = fetch_info(ticker)
    return hist, info


def analyze(symbol: str, cfg: dict, m_score: float) -> dict:
    ticker = cfg["ticker"]
    base = {
        "종목": f"{symbol} ({cfg.get('name_kr', '')})",
        "Thesis": cfg["thesis"],
        "역할": cfg.get("role", "—"),
        "생존": STARS.get(cfg["survival"], "?"),
        "성장성": STARS.get(cfg["growth"], "?"),
        "Val": None,
        "Tech": None,
        "Macro": round(m_score),
        "Score": None,
        "Grade": "—",
        "Action": "—",
        "Opportunity": None,
        "Trend": None,
        "Confidence": 0.0,
        "ConfidenceLabel": "LOW",
        "Shadow": "데이터 부족 — Shadow 진단 N/A",
        "_note": cfg.get("note", ""),
        "_val_detail": "",
        "_tech_detail": "",
        "_opportunity_detail": "",
        "_trend_detail": "",
        "_confidence_detail": "0/10 valid",
        "_opportunity_breakdown": {},
        "_trend_breakdown": {},
        "_trend_metrics": {},
        "_data_date": None,
        "_benchmark": cfg.get("benchmark", "SPY"),
        "_shadow_error": None,
        "_error": None,
    }
    try:
        hist, info = load_ticker(ticker)
        closes = hist["Close"]
        v_score, v_detail = valuation_score(info)
        rsi_val = rsi(closes)
        stoch_k, stoch_d = slow_stochastic(hist["High"], hist["Low"], closes)
        ma = ma_deviation(closes)
        t_score, t_detail = technical_score(
            rsi_val,
            stoch_k,
            stoch_d,
            ma,
        )
        base.update({
            "Val": round(v_score),
            "Tech": None if t_score is None else round(t_score),
            "_val_detail": v_detail,
            "_tech_detail": t_detail,
        })
        if t_score is None:
            base.update({
                "Score": None,
                "Grade": "N/A",
                "Action": "N/A",
            })
        else:
            effective_val = v_score if v_detail != "N/A" else 50
            s = price_score(effective_val, t_score, m_score)
            grade, action = to_grade(s)
            base.update({
                "Score": round(s, 1),
                "Grade": grade,
                "Action": action,
            })

        # Lab shadow signals are isolated from the official Score/Grade path.
        opportunity, opportunity_detail, opportunity_breakdown = opportunity_score(
            v_score, v_detail, rsi_val, stoch_k, stoch_d,
        )
        benchmark = pd.Series(dtype=float)
        try:
            benchmark_hist = load_history(base["_benchmark"])
            benchmark = benchmark_hist["Close"]
        except Exception as e:
            base["_shadow_error"] = f"Benchmark {base['_benchmark']}: {e}"

        metrics = trend_metrics(closes, benchmark)
        trend, trend_detail, trend_breakdown = trend_health_score(metrics)
        confidence, confidence_label, confidence_detail = data_confidence(
            v_score, v_detail, rsi_val, stoch_k, stoch_d, metrics,
        )
        base.update({
            "Opportunity": None if opportunity is None else round(opportunity, 1),
            "Trend": None if trend is None else round(trend, 1),
            "Confidence": round(confidence),
            "ConfidenceLabel": confidence_label,
            "Shadow": shadow_diagnosis(opportunity, trend),
            "_opportunity_detail": opportunity_detail,
            "_trend_detail": trend_detail,
            "_confidence_detail": confidence_detail,
            "_opportunity_breakdown": opportunity_breakdown,
            "_trend_breakdown": trend_breakdown,
            "_trend_metrics": metrics,
            "_data_date": metrics.get("latest_date"),
        })
    except Exception as e:
        base["_error"] = str(e)
    return base


# ── UI ─────────────────────────────────────────────────────────────────────────

st.title("📊 LBW Portfolio")

with st.expander("📐 스코어링 공식 보기", expanded=False):
    st.markdown("**Price Score = Valuation × 50% + Technical × 30% + Macro × 20%**")

    st.dataframe(
        pd.DataFrame({
            "컴포넌트": ["Valuation", "Technical", "Macro"],
            "지표": [
                "Forward PER + PEG",
                "RSI 35% + Slow Stochastic 35% + 200MA 이격도 30%",
                "Normal: Rate Level 80% + Fed Policy Signal 20% / VIX > 25: 70% + 30%",
            ],
            "비중": ["50%", "30%", "20%"],
        }),
        hide_index=True, width="stretch",
    )
    st.caption("Rate Level = 10Y 75% + 30Y 25%")
    st.caption("Fed Policy Signal = FFR vs r* 35% + 2Y 3개월 변화 25% + TIPS 10Y 40%")
    st.caption("장단기 금리차는 점수 구성요소가 아니며 상태 경고에만 사용됩니다.")

    st.dataframe(
        pd.DataFrame({
            "점수": ["88+", "78+", "65+", "50+", "0+"],
            "등급": ["S", "A", "B", "C", "D"],
            "의미": [
                "강력 매수 — 비정상적 기회, 망설이지 말 것",
                "매수 — 상당히 매력적인 가격",
                "분할매수 고려 — 합리적, 한 번에 다 사지 말 것",
                "보유 / 관망 — 비싸다, 더 좋은 가격 기다릴 것",
                "추격매수 금지 — 매우 비싸다, 신규 진입 하지 말 것",
            ],
        }),
        hide_index=True, width="stretch",
    )
    st.caption("핵심 원칙: 좋은 기업 ≠ 좋은 가격 — 아무리 훌륭한 기업도 비싸면 기다린다.")

# ── VIX 먼저 (macro_score stress regime 판단에 필요) ───────────────────────────
vix = 20.0
marks_vix = None
try:
    vix = load_vix()
    marks_vix = vix
except Exception:
    pass

# ── Macro ────────────────────────────────────────────────────────────────────────
macro = {"t10y": None, "t30y": None}
m_score, m_detail, m_breakdown = macro_score(macro, vix)

with st.spinner("매크로 데이터 로딩 중..."):
    try:
        macro = load_macro()
        m_score, m_detail, m_breakdown = macro_score(macro, vix)
        if macro.get("_source") == "yfinance":
            st.info("FRED 타임아웃 → Yahoo Finance 금리 데이터로 대체")
    except Exception as e:
        st.error(f"FRED API 연결 실패 — 🔄 새로고침으로 재시도 ({e})")

# ── Fear & Greed ─────────────────────────────────────────────────────────────────
fg_score, fg_rating, fg_emoji = None, "—", "😐"
try:
    fg = load_fear_greed()
    fg_score = fg["score"]
    fg_rating = fg["rating"].replace("_", " ").title()
    fg_emoji = (
        "😱" if fg_score < 25 else "😟" if fg_score < 45 else
        "😐" if fg_score < 55 else "😏" if fg_score < 75 else "🤑"
    )
except Exception:
    pass

def fmt(val, spec=".2f", suffix="%", fallback="—"):
    return f"{val:{spec}}{suffix}" if val is not None else fallback

# ── Metrics 행 ────────────────────────────────────────────────────────────────────
vix_label = "😌 Low" if vix < 20 else ("⚠️ Elevated" if vix < 30 else "🔥 High")
inp = m_breakdown.get("inputs", {})

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("10Y Treasury", fmt(macro.get("t10y")))
col2.metric("30Y Treasury", fmt(macro.get("t30y")))
col3.metric("FFR", fmt(inp.get("ffr"), spec=".2f"))
col4.metric("Macro Score", f"{m_breakdown['final_score']} / 100", macro_status(m_score))
col5.metric("VIX", f"{vix:.1f}", vix_label)
col6.metric(
    "Fear & Greed",
    "N/A" if fg_score is None else f"{fg_score:.0f}",
    f"{fg_emoji} {fg_rating}",
)

# ── S&P 500 Market Valuation Context (Shadow only) ─────────────────────────────
st.markdown("#### 🔬 Market Valuation Context · Shadow")
st.caption("시장 배경 정보이며 Price Score와 Grade에는 반영되지 않습니다.")
try:
    sp500_valuation = load_sp500_valuation()
    earnings_yield = sp500_valuation["earnings_yield"]
    treasury_10y = macro.get("t10y")
    yield_gap = earnings_yield - treasury_10y if treasury_10y is not None else None

    vc1, vc2, vc3, vc4, vc5 = st.columns(5)
    vc1.metric(
        "S&P 500 TTM P/E",
        f"{sp500_valuation['ttm_pe']:.2f}",
        f"1Y ago {sp500_valuation['year_ago_pe']:.2f}",
        delta_color="off",
    )
    vc2.metric("Earnings Yield", f"{earnings_yield:.2f}%")
    vc3.metric(
        "Forward P/E",
        f"{sp500_valuation['forward_pe']:.2f}",
        "Operating earnings",
        delta_color="off",
    )
    vc4.metric("Dividend Yield", f"{sp500_valuation['dividend_yield']:.2f}%")
    vc5.metric("Earnings Yield − 10Y", "N/A" if yield_gap is None else f"{yield_gap:+.2f}%p")
    st.caption(
        f"WSJ 기준일 {sp500_valuation['as_of'] or 'N/A'} · "
        "TTM은 as-reported earnings, Forward는 operating earnings · "
        "단순 Yield Gap이며 공식 Equity Risk Premium이 아닙니다. · "
        "[WSJ P/E & Yields](https://www.wsj.com/market-data/stocks/peyields)"
    )
except Exception as e:
    sp500_valuation = None
    st.warning(f"S&P 500 valuation: N/A · WSJ 데이터 로딩 실패 ({e})")

# ── Macro Score 산정 내역 Toggle ─────────────────────────────────────────────────
rate_bd = m_breakdown.get("rate_detail", {})
fed_bd  = m_breakdown.get("fed_detail",  {})
rate_s  = m_breakdown.get("rate_score",  0)
fed_s   = m_breakdown.get("fed_score",   0)
rate_w  = m_breakdown.get("rate_weight", 0.80)
fed_w   = m_breakdown.get("fed_weight",  0.20)
final_s = m_breakdown.get("final_score", 0)
stress  = m_breakdown.get("stress_regime", False)

with st.expander("📐 Macro Score 산정 내역 (v2.3)", expanded=False):
    regime_str = "🔴 Stress (VIX > 25)" if stress else "🟢 Normal"
    st.caption(
        f"VIX Regime: {regime_str}  ·  "
        f"Rate Level {rate_w*100:.0f}% + Fed Policy Signal {fed_w*100:.0f}%  ·  "
        f"r* = {inp.get('neutral_rate', 2.5):.1f}%  ·  "
        f"Yield Curve Warning: {yield_curve_status(macro)}"
    )
    st.caption("장단기 금리차는 Macro 점수에 포함되지 않고 상태 경고에만 사용됩니다.")
    ca, cb = st.columns(2)
    with ca:
        st.markdown("**Rate Level Score**")
        st.dataframe(
            pd.DataFrame({
                "지표":   ["10Y Treasury", "30Y Treasury"],
                "현재값": [fmt(inp.get("t10y")), fmt(inp.get("t30y"))],
                "점수":   [f"{rate_bd.get('t10_s', 0):.0f}", f"{rate_bd.get('t30_s', 0):.0f}"],
                "비중":   ["75%", "25%"],
            }),
            hide_index=True, width="stretch",
        )
        st.metric("Rate Level", f"{rate_s:.0f} / 100")
    with cb:
        st.markdown("**Fed Policy Signal**")
        gap = fed_bd.get("gap", 0)
        st.dataframe(
            pd.DataFrame({
                "지표":   ["FFR vs r*", "2Y Δ (3개월)", "TIPS 10Y"],
                "현재값": [
                    f"{inp.get('ffr', 0):.2f}% / r* {inp.get('neutral_rate', 2.5):.1f}% → gap {gap:+.2f}%",
                    f"{inp.get('delta_2y', 0):+.2f}%",
                    f"{inp.get('tips', 0):.2f}%",
                ],
                "점수":   [
                    f"{fed_bd.get('ffr_s', 0):.0f}",
                    f"{fed_bd.get('delta_s', 0):.0f}",
                    f"{fed_bd.get('tips_s', 0):.0f}",
                ],
                "비중":   ["35%", "25%", "40%"],
            }),
            hide_index=True, width="stretch",
        )
        st.metric("Fed Policy Signal", f"{fed_s:.0f} / 100")
    st.divider()
    st.markdown(
        f"**최종 = {rate_s:.0f} × {rate_w*100:.0f}% + {fed_s:.0f} × {fed_w*100:.0f}% = {final_s}점**"
    )

marks_data = {}
vix_history = None
try:
    marks_data = load_marks_temperature_data()
except Exception:
    pass
try:
    vix_history = load_vix_history()
except Exception:
    pass
try:
    mt_score, mt_label, mt_detail, mt_components = marks_temperature_score(
        marks_data,
        vix=marks_vix,
        vix_history=vix_history,
        fear_greed=fg_score,
    )
except Exception as e:
    mt_score, mt_label, mt_detail, mt_components = None, "—", str(e), {}

if mt_score is not None:
    st.metric("Marks Temperature", f"{mt_score:.0f} / 100", mt_label)
    with st.expander("Marks Temperature 구성 보기", expanded=False):
        st.caption("높을수록 좋은 투자환경이 아니라, 위험선호/자본공급/낙관론이 뜨거운 상태입니다.")
        component_rows = []
        for c in mt_components.values():
            component_rows.append({
                "Component": c["label"],
                "Weight": f"{c['weight'] * 100:.0f}%",
                "Latest": "—" if c["value"] is None else f"{c['value']:.2f}",
                "Date": c["date"] or "—",
                "Heat": "—" if c["heat"] is None else f"{c['heat']:.0f}",
            })
        st.dataframe(pd.DataFrame(component_rows), hide_index=True, width="stretch")
else:
    st.metric("Marks Temperature", "N/A", "데이터 부족")
    st.caption(mt_detail)

st.divider()

# 포트폴리오 로딩
if st.button("🔄 새로고침", type="primary"):
    st.cache_data.clear()
    st.rerun()

rows = []
with st.spinner("포트폴리오 분석 중..."):
    for symbol, cfg in PORTFOLIO.items():
        rows.append(analyze(symbol, cfg, m_score))

# ── 종목 카드 ─────────────────────────────────────────────────────────────────────
card_cols = st.columns(2)
for i, row in enumerate(rows):
    with card_cols[i % 2]:
        grade       = row["Grade"]
        grade_color = GRADE_COLOR.get(grade, "#6b7280")
        score_str   = f"{row['Score']:.1f}" if row["Score"] is not None else "N/A"
        val_str     = f"{row['Val']:.0f}"   if row["Val"]   is not None else "N/A"
        tech_str    = f"{row['Tech']:.0f}"  if row["Tech"]  is not None else "N/A"
        opportunity_str = f"{row['Opportunity']:.1f}" if row["Opportunity"] is not None else "N/A"
        trend_str = f"{row['Trend']:.1f}" if row["Trend"] is not None else "N/A"
        opportunity_width = row["Opportunity"] if row["Opportunity"] is not None else 0
        trend_width = row["Trend"] if row["Trend"] is not None else 0
        confidence_color = {
            "HIGH": "#22c55e",
            "MEDIUM": "#f59e0b",
            "LOW": "#ef4444",
        }.get(row["ConfidenceLabel"], "#6b7280")
        sub_detail  = ""
        if row["_val_detail"] or row["_tech_detail"]:
            sub_detail = (
                f'<div style="font-size:11px;color:#9ca3af;margin-top:6px;">'
                f'{row["_val_detail"]} &nbsp;·&nbsp; {row["_tech_detail"]}'
                f"</div>"
            )
        error_html = (
            f'<div style="color:#f87171;font-size:12px;margin-top:6px;">{row["_error"]}</div>'
            if row["_error"] else ""
        )
        shadow_error_html = (
            f'<div style="color:#f59e0b;font-size:11px;margin-top:5px;">'
            f'{html.escape(row["_shadow_error"])}</div>'
            if row["_shadow_error"] else ""
        )

        st.markdown(
            f"""
            <div style="
                border:1px solid rgba(49,51,63,0.2);
                border-radius:14px;
                padding:18px 20px;
                margin-bottom:14px;
            ">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">
                <div>
                  <div style="font-size:17px;font-weight:700;">{row['종목']}</div>
                  <div style="font-size:11px;color:#6b7280;margin-top:3px;">{row['Thesis']}</div>
                </div>
                <div style="text-align:center;min-width:60px;">
                  <div style="font-size:42px;font-weight:900;color:{grade_color};line-height:1;">{grade}</div>
                  <div style="font-size:11px;color:#6b7280;margin-top:2px;">{row['Action']}</div>
                </div>
              </div>
              <div style="font-size:28px;font-weight:700;margin-bottom:10px;">
                {score_str}<span style="font-size:13px;font-weight:400;color:#6b7280;"> / 100</span>
              </div>
              <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px;">
                <span style="background:rgba(49,51,63,0.07);border-radius:6px;padding:3px 9px;font-size:12px;">Val {val_str}</span>
                <span style="background:rgba(49,51,63,0.07);border-radius:6px;padding:3px 9px;font-size:12px;">Tech {tech_str}</span>
                <span style="background:rgba(49,51,63,0.07);border-radius:6px;padding:3px 9px;font-size:12px;">Macro {row['Macro']}</span>
              </div>
              <div style="font-size:12px;color:#6b7280;">
                생존 {row['생존']} &nbsp;·&nbsp; 성장 {row['성장성']}
              </div>
              {sub_detail}
              <div style="border-top:1px dashed rgba(107,114,128,0.35);margin-top:13px;padding-top:11px;">
                <div style="font-size:10px;font-weight:700;letter-spacing:.08em;color:#7c3aed;margin-bottom:8px;">
                  SHADOW ANALYSIS · GRADE 미반영
                </div>
                <div style="display:grid;grid-template-columns:86px 1fr 38px;gap:7px;align-items:center;font-size:11px;">
                  <span>Opportunity</span>
                  <span style="height:6px;background:rgba(124,58,237,.12);border-radius:5px;overflow:hidden;">
                    <span style="display:block;height:100%;width:{opportunity_width}%;background:#8b5cf6;"></span>
                  </span>
                  <strong>{opportunity_str}</strong>
                  <span>Trend Health</span>
                  <span style="height:6px;background:rgba(37,99,235,.12);border-radius:5px;overflow:hidden;">
                    <span style="display:block;height:100%;width:{trend_width}%;background:#3b82f6;"></span>
                  </span>
                  <strong>{trend_str}</strong>
                </div>
                <div style="display:flex;justify-content:space-between;gap:8px;margin-top:9px;font-size:11px;">
                  <span style="color:{confidence_color};font-weight:700;">● Confidence {row['ConfidenceLabel']} · {row['Confidence']:.0f}%</span>
                  <span style="color:#6b7280;">{row['_data_date'] or 'N/A'}</span>
                </div>
                <div style="font-size:12px;font-weight:600;margin-top:7px;">{row['Shadow']}</div>
                {shadow_error_html}
              </div>
              {error_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

# ── Shadow Model 상세 ──────────────────────────────────────────────────────────
with st.expander("🔬 Shadow Model Lab · Opportunity × Trend Health", expanded=False):
    st.caption("실험 신호이며 기존 Price Score, Grade, Action에는 영향을 주지 않습니다.")
    selected_shadow = st.selectbox("종목 선택", [r["종목"] for r in rows], key="shadow-symbol")
    shadow_row = next(r for r in rows if r["종목"] == selected_shadow)

    sa, sb, sc = st.columns(3)
    sa.metric(
        "Opportunity",
        "N/A" if shadow_row["Opportunity"] is None else f"{shadow_row['Opportunity']:.1f}",
    )
    sb.metric(
        "Trend Health",
        "N/A" if shadow_row["Trend"] is None else f"{shadow_row['Trend']:.1f}",
    )
    sc.metric(
        "Data Confidence",
        f"{shadow_row['Confidence']:.0f}%",
        shadow_row["ConfidenceLabel"],
    )
    st.markdown(f"**진단:** {shadow_row['Shadow']}")
    st.caption(shadow_row["_confidence_detail"])

    if shadow_row["Opportunity"] is not None and shadow_row["Trend"] is not None:
        marker_left = max(2, min(98, shadow_row["Trend"]))
        marker_bottom = max(2, min(98, shadow_row["Opportunity"]))
        components.html(
            f"""
            <style>
            body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; color:#31333f; }}
            .axis-title {{ font-size:12px; font-weight:700; color:#6b7280; margin-bottom:5px; }}
            .matrix {{ position:relative; height:260px; margin:0 8px 24px 42px; border:1px solid #9ca3af;
                       background:linear-gradient(to right, transparent 49.8%,#9ca3af 50%,transparent 50.2%),
                                  linear-gradient(to top, transparent 49.8%,#9ca3af 50%,transparent 50.2%); }}
            .q {{ position:absolute; width:48%; height:46%; padding:9px; font-size:12px; box-sizing:border-box; }}
            .tl {{ left:0; top:0; background:rgba(245,158,11,.08); }}
            .tr {{ right:0; top:0; background:rgba(34,197,94,.08); }}
            .bl {{ left:0; bottom:0; background:rgba(239,68,68,.06); }}
            .br {{ right:0; bottom:0; background:rgba(59,130,246,.06); }}
            .marker {{ position:absolute; left:{marker_left}%; bottom:{marker_bottom}%; transform:translate(-50%,50%);
                       width:15px; height:15px; border-radius:50%; background:#7c3aed; border:3px solid white;
                       box-shadow:0 0 0 2px #7c3aed; z-index:5; }}
            .marker-label {{ position:absolute; left:{marker_left}%; bottom:{marker_bottom}%; transform:translate(13px,19px);
                             font-size:11px; font-weight:700; color:#7c3aed; white-space:nowrap; z-index:6; }}
            .x {{ text-align:right; font-size:12px; color:#6b7280; margin-top:-18px; }}
            .y {{ position:absolute; left:-38px; top:45%; transform:rotate(-90deg); font-size:12px; color:#6b7280; }}
            </style>
            <div class="axis-title">{html.escape(selected_shadow)}</div>
            <div style="position:relative;">
              <div class="y">Opportunity →</div>
              <div class="matrix">
                <div class="q tl"><b>⚠ 추세 확인</b><br>싸지만 추세 훼손</div>
                <div class="q tr"><b>★ Prime Setup</b><br>가격 매력 + 건강한 추세</div>
                <div class="q bl"><b>✕ Weak</b><br>가격 매력과 추세 모두 약함</div>
                <div class="q br"><b>↑ Stretched</b><br>추세는 건강하지만 가격 부담</div>
                <div class="marker"></div>
                <div class="marker-label">{shadow_row['Opportunity']:.1f} / {shadow_row['Trend']:.1f}</div>
              </div>
              <div class="x">Trend Health →</div>
            </div>
            """,
            height=320,
        )
    else:
        st.warning("필수 데이터가 부족해 2×2 매트릭스에 표시할 수 없습니다.")

    if shadow_row["_opportunity_breakdown"]:
        left, right = st.columns(2)
        with left:
            st.markdown("**Opportunity 구성**")
            st.json(shadow_row["_opportunity_breakdown"])
            st.caption(shadow_row["_opportunity_detail"])
        with right:
            st.markdown("**Trend Health 구성**")
            st.json(shadow_row["_trend_breakdown"])
            st.caption(shadow_row["_trend_detail"])

# ── LLM 붙여넣기 테이블 ──────────────────────────────────────────────────────────
df = pd.DataFrame(rows)
display_cols = [
    "종목", "생존", "성장성", "Val", "Tech", "Score", "Grade", "Action",
    "Opportunity", "Trend", "Confidence", "ConfidenceLabel", "Shadow", "Thesis",
]
copy_df = df[display_cols].copy()
for col in ["Val", "Tech", "Score", "Opportunity", "Trend", "Confidence"]:
    copy_df[col] = copy_df[col].map(lambda v: "N/A" if pd.isna(v) else f"{v:.1f}" if col == "Score" else f"{v:.0f}")

copy_text    = copy_df.to_csv(sep="\t", index=False)
copy_payload = json.dumps(copy_text)
copy_html_   = html.escape(copy_text)
components.html(
    f"""
    <style>
    body {{
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: #31333f;
    }}
    details {{
        border: 1px solid rgba(49, 51, 63, 0.2);
        border-radius: 8px;
        background: white;
    }}
    summary {{
        min-height: 42px;
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 0 16px;
        cursor: pointer;
        font-size: 16px;
        font-weight: 600;
        user-select: none;
    }}
    summary::marker {{ color: #6b7280; }}
    #copy-status {{
        margin-left: auto;
        color: #6b7280;
        font-size: 13px;
        font-weight: 400;
    }}
    .content {{ padding: 0 16px 14px; }}
    .caption {{ margin: 2px 0 8px; color: #6b7280; font-size: 13px; }}
    textarea {{
        width: 100%;
        height: 160px;
        box-sizing: border-box;
        border: 1px solid rgba(49, 51, 63, 0.2);
        border-radius: 8px;
        padding: 10px;
        resize: vertical;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 13px;
        line-height: 1.4;
        color: #111827;
        background: #f9fafb;
    }}
    </style>
    <details id="llm-copy">
        <summary>LLM 붙여넣기용 테이블<span id="copy-status"></span></summary>
        <div class="content">
            <div class="caption">클릭하면 TSV가 자동 복사됩니다.</div>
            <textarea readonly>{copy_html_}</textarea>
        </div>
    </details>
    <script>
    const text = {copy_payload};
    const details = document.getElementById("llm-copy");
    const status  = document.getElementById("copy-status");
    async function copyTable() {{
        try {{
            if (navigator.clipboard && window.isSecureContext) {{
                await navigator.clipboard.writeText(text);
            }} else {{
                const ta = document.createElement("textarea");
                ta.value = text; ta.style.position="fixed"; ta.style.left="-9999px";
                document.body.appendChild(ta); ta.focus(); ta.select();
                document.execCommand("copy"); document.body.removeChild(ta);
            }}
            status.textContent = " · 복사 완료";
            setTimeout(() => {{ status.textContent = ""; }}, 1800);
        }} catch(e) {{ status.textContent = " · 직접 복사 필요"; }}
    }}
    details.addEventListener("toggle", () => {{ if (details.open) copyTable(); }});
    </script>
    """,
    height=265,
)

st.caption(f"Macro v2.3: {m_detail} · Marks: {mt_detail} · 15분 캐시 적용")
