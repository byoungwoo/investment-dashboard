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
)
from indicators import rsi, slow_stochastic, ma_deviation
from scorer import (
    valuation_score,
    technical_score,
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

st.title("📊 LBW Portfolio")

with st.expander("📐 스코어링 공식 보기", expanded=False):
    st.markdown("**Price Score = Valuation × 50% + Technical × 30% + Macro × 20%**")

    st.dataframe(
        pd.DataFrame({
            "컴포넌트": ["Valuation", "Technical", "Macro"],
            "지표": [
                "Forward PER + PEG",
                "RSI 35% + Slow Stochastic 35% + 200MA 이격도 30%",
                "Market Macro 80% + Fed Policy Regime 20%",
            ],
            "비중": ["50%", "30%", "20%"],
        }),
        hide_index=True, use_container_width=True,
    )
    st.caption("Market Macro = 10Y 금리 40% + 30Y 금리 40% + 장단기 금리차 20%")

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
        hide_index=True, use_container_width=True,
    )
    st.caption("핵심 원칙: 좋은 기업 ≠ 좋은 가격 — 아무리 훌륭한 기업도 비싸면 기다린다.")

# ── VIX 먼저 (macro_score stress regime 판단에 필요) ───────────────────────────
vix = 20.0
try:
    vix = load_vix()
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
fg_score, fg_rating, fg_emoji = 50.0, "—", "😐"
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
col6.metric("Fear & Greed", f"{fg_score:.0f}", f"{fg_emoji} {fg_rating}")

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
        f"Yield Curve: {yield_curve_status(macro)}"
    )
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
            hide_index=True, use_container_width=True,
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
            hide_index=True, use_container_width=True,
        )
        st.metric("Fed Policy Signal", f"{fed_s:.0f} / 100")
    st.divider()
    st.markdown(
        f"**최종 = {rate_s:.0f} × {rate_w*100:.0f}% + {fed_s:.0f} × {fed_w*100:.0f}% = {final_s}점**"
    )

try:
    marks_data = load_marks_temperature_data()
    vix_history = load_vix_history()
    mt_score, mt_label, mt_detail, mt_components = marks_temperature_score(
        marks_data,
        vix=vix,
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
        st.dataframe(pd.DataFrame(component_rows), hide_index=True, use_container_width=True)
else:
    st.metric("Marks Temperature", "—", "데이터 부족")
    st.caption(f"Marks Temperature unavailable: {mt_detail}")

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

display_cols = ["종목", "Thesis", "생존", "성장성", "Val", "Tech", "Score", "Grade", "Action"]
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
    .map(color_grade, subset=["Grade"])
    .map(color_score, subset=["Score"])
    .format({"Val": "{:.0f}", "Tech": "{:.0f}", "Score": "{:.1f}"}, na_rep="—")
)

st.dataframe(styled, use_container_width=True, hide_index=True, height=320)

copy_df = df_display.copy()
for col in ["Val", "Tech", "Score"]:
    copy_df[col] = copy_df[col].map(lambda v: "—" if pd.isna(v) else f"{v:.1f}" if col == "Score" else f"{v:.0f}")

copy_text = copy_df.to_csv(sep="\t", index=False)
copy_payload = json.dumps(copy_text)
copy_html = html.escape(copy_text)
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
    summary::marker {{
        color: #6b7280;
    }}
    #copy-status {{
        margin-left: auto;
        color: #6b7280;
        font-size: 13px;
        font-weight: 400;
    }}
    .content {{
        padding: 0 16px 14px;
    }}
    .caption {{
        margin: 2px 0 8px;
        color: #6b7280;
        font-size: 13px;
    }}
    textarea {{
        width: 100%;
        height: 180px;
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
        <summary>
            LLM 붙여넣기용 테이블
            <span id="copy-status"></span>
        </summary>
        <div class="content">
            <div class="caption">클릭하면 헤더 포함 TSV가 자동으로 복사됩니다. 자동 복사가 안 되면 아래 내용을 직접 복사하세요.</div>
            <textarea readonly>{copy_html}</textarea>
        </div>
    </details>
    <script>
    const text = {copy_payload};
    const details = document.getElementById("llm-copy");
    const status = document.getElementById("copy-status");

    async function fallbackCopy(value) {{
        const textarea = document.createElement("textarea");
        textarea.value = value;
        textarea.setAttribute("readonly", "");
        textarea.style.position = "fixed";
        textarea.style.left = "-9999px";
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        const copied = document.execCommand("copy");
        document.body.removeChild(textarea);
        return copied;
    }}

    async function copyTable() {{
        try {{
            if (navigator.clipboard && window.isSecureContext) {{
                await navigator.clipboard.writeText(text);
            }} else {{
                const copied = await fallbackCopy(text);
                if (!copied) throw new Error("fallback copy failed");
            }}
            status.textContent = "복사 완료";
            setTimeout(() => {{
                status.textContent = "";
            }}, 1800);
        }} catch (error) {{
            status.textContent = "직접 복사 필요";
        }}
    }}

    details.addEventListener("toggle", () => {{
        if (details.open) copyTable();
    }});
    </script>
    """,
    height=285,
)

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

st.caption(f"Macro v2.3: {m_detail} · Marks: {mt_detail} · 15분 캐시 적용")
