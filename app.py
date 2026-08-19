import streamlit as st
import pandas as pd

from config import PORTFOLIO
from fetcher import fetch_history, fetch_info, fetch_macro, fetch_vix, fetch_fear_greed
from indicators import rsi, slow_stochastic, ma_deviation
from scorer import valuation_score, technical_score, macro_score, price_score, to_grade

st.set_page_config(page_title="이병우 포트폴리오 Dashboard", page_icon="📊", layout="wide")

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
def load_ticker(ticker: str):
    hist = fetch_history(ticker)
    info = fetch_info(ticker)
    return hist, info


def analyze(symbol: str, cfg: dict, m_score: float) -> dict:
    ticker = cfg["ticker"]
    base = {
        "종목": f"{symbol} ({cfg.get('name_kr', '')})",
        "Thesis": cfg["thesis"],
        "생존": STARS.get(cfg["survival"], "?"),
        "성장성": STARS.get(cfg["growth"], "?"),
        "Val": None,
        "Tech": None,
        "Macro": round(m_score),
        "Score": None,
        "Grade": "—",
        "Action": "—",
        "_val_detail": "",
        "_tech_detail": "",
        "_error": None,
    }
    try:
        hist, info = load_ticker(ticker)
        closes = hist["Close"]
        v_score, v_detail = valuation_score(info)
        t_score, t_detail = technical_score(
            rsi(closes),
            *slow_stochastic(hist["High"], hist["Low"], closes),
            ma_deviation(closes),
        )
        effective_val = v_score if v_detail != "N/A" else 50
        s = price_score(effective_val, t_score, m_score)
        grade, action = to_grade(s)
        base.update({
            "Val": round(v_score),
            "Tech": round(t_score),
            "Score": round(s, 1),
            "Grade": grade,
            "Action": action,
            "_val_detail": v_detail,
            "_tech_detail": t_detail,
        })
    except Exception as e:
        base["_error"] = str(e)
    return base


# ── UI ─────────────────────────────────────────────────────────────────────────

st.title("📊 이병우 포트폴리오 Dashboard")

with st.expander("📐 스코어링 공식 보기", expanded=False):
    st.markdown("""
**Price Score = Valuation × 50% + Technical × 30% + Macro × 20%**

| 컴포넌트 | 지표 | 비중 |
|---|---|---|
| **Valuation** | Forward PER + PEG (성장률 대비 멀티플) | 50% |
| **Technical** | RSI 35% + Slow Stochastic 35% + 200MA 이격도 30% | 30% |
| **Macro** | 10Y 금리 40% + 30Y 금리 40% + 장단기 금리차 20% | 20% |

| 점수 | 등급 | 의미 |
|---|---|---|
| 88+ | **S** | 강력 매수 — 비정상적 기회, 망설이지 말 것 |
| 78+ | **A** | 매수 — 상당히 매력적인 가격 |
| 65+ | **B** | 분할매수 고려 — 합리적, 한 번에 다 사지 말 것 |
| 50+ | **C** | 보유 / 관망 — 비싸다, 더 좋은 가격 기다릴 것 |
| 0+  | **D** | 추격매수 금지 — 매우 비싸다, 신규 진입 하지 말 것 |

> 핵심 원칙: **좋은 기업 ≠ 좋은 가격** — 아무리 훌륭한 기업도 비싸면 기다린다.
""")

# Macro 헤더
with st.spinner("매크로 데이터 로딩 중..."):
    try:
        macro = load_macro()
        m_score, m_detail = macro_score(macro)
        source = macro.get("_source", "FRED")
        if source == "yfinance":
            st.info("FRED 타임아웃 → Yahoo Finance 금리 데이터로 대체")
    except Exception as e:
        st.error(f"FRED API 연결 실패 — 🔄 새로고침으로 재시도 ({e})")
        macro = {"t10y": None, "t30y": None, "t10y2y": None}
        m_score, m_detail = macro_score(macro)

def fmt(val, spec=".2f", suffix="%", fallback="—"):
    return f"{val:{spec}}{suffix}" if val is not None else fallback

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("10Y Treasury", fmt(macro.get("t10y")))
col2.metric("30Y Treasury", fmt(macro.get("t30y")))
col3.metric("10Y-2Y Spread", fmt(macro.get("t10y2y"), spec="+.2f"))
col4.metric("Macro Score", f"{m_score:.0f} / 100")

try:
    vix = load_vix()
    vix_label = "😌 Low" if vix < 20 else ("⚠️ Elevated" if vix < 30 else "🔥 High")
    col5.metric("VIX", f"{vix:.1f}", vix_label)
except Exception:
    col5.metric("VIX", "—")

try:
    fg = load_fear_greed()
    fg_score = fg["score"]
    fg_rating = fg["rating"].replace("_", " ").title()
    fg_emoji = (
        "😱" if fg_score < 25 else
        "😟" if fg_score < 45 else
        "😐" if fg_score < 55 else
        "😏" if fg_score < 75 else "🤑"
    )
    col6.metric("Fear & Greed", f"{fg_score:.0f}", f"{fg_emoji} {fg_rating}")
except Exception:
    col6.metric("Fear & Greed", "—")

st.divider()

# 포트폴리오 로딩
if st.button("🔄 새로고침", type="primary"):
    st.cache_data.clear()
    st.rerun()

rows = []
with st.spinner("포트폴리오 분석 중..."):
    for symbol, cfg in PORTFOLIO.items():
        rows.append(analyze(symbol, cfg, m_score))

# 테이블
df = pd.DataFrame(rows)

display_cols = ["종목", "Thesis", "생존", "성장성", "Val", "Tech", "Macro", "Score", "Grade", "Action"]
df_display = df[display_cols].copy()


def color_grade(val):
    color = GRADE_COLOR.get(val, "#6b7280")
    return f"color: {color}; font-weight: bold"


def color_score(val):
    if val is None:
        return ""
    if val >= 78:
        return "color: #4ade80"
    if val >= 65:
        return "color: #86efac"
    if val >= 50:
        return "color: #fbbf24"
    return "color: #f87171"


styled = (
    df_display.style
    .applymap(color_grade, subset=["Grade"])
    .applymap(color_score, subset=["Score"])
    .format({"Val": "{:.0f}", "Tech": "{:.0f}", "Macro": "{:.0f}", "Score": "{:.1f}"}, na_rep="—")
)

st.dataframe(styled, use_container_width=True, hide_index=True, height=320)

st.divider()

# 종목별 상세
st.subheader("종목별 상세")
selected = st.selectbox("종목 선택", [r["종목"] for r in rows])
detail = next(r for r in rows if r["종목"] == selected)

if detail["_error"]:
    st.error(f"데이터 오류: {detail['_error']}")
else:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Valuation", f"{detail['Val'] or '—'}", detail["_val_detail"])
    c2.metric("Technical", f"{detail['Tech'] or '—'}", detail["_tech_detail"])
    c3.metric("Score", f"{detail['Score'] or '—'}")
    grade = detail["Grade"]
    c4.metric("Grade", grade, detail["Action"])

st.caption(f"Macro: {m_detail} · 15분 캐시 적용")
