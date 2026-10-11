import html

import streamlit as st


TONE_COLORS = {
    "actual": ("#2563eb", "rgba(37,99,235,.10)"),
    "leading": ("#7c3aed", "rgba(124,58,237,.10)"),
    "operating": ("#059669", "rgba(5,150,105,.10)"),
    "forward": ("#d97706", "rgba(217,119,6,.11)"),
    "profit": ("#16a34a", "rgba(22,163,74,.10)"),
    "risk": ("#dc2626", "rgba(220,38,38,.09)"),
}


# Official filing snapshots for the fundamental detail UI only. These values are
# intentionally isolated from the Price Score, Grade, Action, and Shadow models.
FUNDAMENTAL_DETAILS = {
    "IREN": {
        "period": "FY2026",
        "updated": "2026-08-27",
        "badges": [
            {"label": "ACTUAL", "value": "$128.8M", "tone": "actual", "detail": "FY26 AI revenue"},
            {"label": "LIVE ARR", "value": "$1.0B", "tone": "operating", "detail": "Operating ARR"},
            {"label": "CONTRACTED", "value": "$4.0B", "tone": "forward", "detail": "Contracted ARR"},
        ],
        "flow_title": "Contract-to-Cash",
        "flow": [
            {"label": "Contract", "value": "$4.0B ARR", "detail": "2026 capacity"},
            {"label": "Build", "value": "Horizon 2–4", "detail": "Commissioning"},
            {"label": "Service", "value": "$1.0B ARR", "detail": "Operating"},
            {"label": "Recognized", "value": "$128.8M", "detail": "FY26 GAAP revenue"},
        ],
        "financial_title": "Q4 FY2026 수익성",
        "financials": [
            {"label": "AI Cloud Revenue", "value": "+$70.5M", "tone": "actual"},
            {"label": "Direct AI Cloud Cost", "value": "-$9.2M", "tone": "risk"},
            {"label": "Direct Contribution", "value": "+$61.3M", "tone": "profit"},
            {"label": "FY26 Net Income", "value": "-$702.6M", "tone": "risk"},
        ],
        "financial_note": (
            "FY26 순손실에는 기존 Bitcoin 채굴장비 전환과 관련된 비현금성 손상차손 "
            "$638.8M이 포함됩니다. ARR는 GAAP 매출이 아니며 고객 인수 이후 매출로 인식됩니다."
        ),
        "status": {"emoji": "🟡", "label": "실행 검증 중", "tone": "forward"},
        "next_checks": [
            "Horizon 2–4 고객 인수와 연말 가동",
            "Operating ARR $4.0B 전환",
            "2027년 분기 AI 매출의 급증",
            "감가상각·이자비용 흡수",
        ],
        "break_conditions": [
            "2027년에도 AI 매출이 M 단위에 정체",
            "고객 인수 또는 데이터센터 준공 지연",
            "추가 대규모 증자와 주주가치 희석",
            "계약 취소·가격 재협상",
        ],
        "source_label": "IREN FY26 Results / SEC filing",
        "source_url": "https://www.sec.gov/Archives/edgar/data/1878848/000187884826000051/irenreportsfy26results.htm",
    },
    "AVGO": {
        "period": "Q3 FY2026",
        "updated": "2026-09-02",
        "badges": [
            {"label": "REVENUE", "value": "$29.6B", "tone": "actual", "detail": "Q3 total"},
            {"label": "AI REVENUE", "value": "$16.7B", "tone": "operating", "detail": "+221% YoY"},
            {"label": "Q4 AI GUIDE", "value": "$21.7B", "tone": "forward", "detail": "Forward"},
        ],
        "flow_title": "AI Demand-to-Revenue",
        "flow": [
            {"label": "Demand", "value": "AI Compute", "detail": "Hyperscalers"},
            {"label": "Design Win", "value": "ASIC + Network", "detail": "Custom silicon"},
            {"label": "Production", "value": "$16.7B", "detail": "+54% QoQ"},
            {"label": "Next Guide", "value": "$21.7B", "detail": "+236% YoY"},
        ],
        "financial_title": "Q3 FY2026 수익성",
        "financials": [
            {"label": "GAAP Operating Income", "value": "+$16.0B", "tone": "profit"},
            {"label": "Free Cash Flow", "value": "+$13.7B", "tone": "profit"},
            {"label": "FCF Margin", "value": "46%", "tone": "profit"},
            {"label": "Total Revenue Growth", "value": "+86%", "tone": "actual"},
        ],
        "financial_note": "Q4 수치는 회사 가이던스이며 실제 실적이 아닙니다.",
        "status": {"emoji": "🟢", "label": "실적 가속", "tone": "operating"},
        "next_checks": [
            "Q4 AI Revenue $21.7B 달성",
            "신규 커스텀 ASIC 고객·디자인 수주",
            "AI Networking 성장 지속",
            "현금흐름과 마진 유지",
        ],
        "break_conditions": [
            "AI 매출 성장률이 2분기 연속 급격히 둔화",
            "AI 또는 전체 매출 가이던스 하향",
            "주요 고객의 주문 축소",
            "고객 집중 위험의 현실화",
        ],
        "source_label": "Broadcom Q3 FY2026 Results",
        "source_url": "https://investors.broadcom.com/news-releases/news-release-details/broadcom-inc-announces-third-quarter-fiscal-year-2026-financial",
    },
    "ABB": {
        "period": "Q2 2026",
        "updated": "2026-07-16",
        "badges": [
            {"label": "ORDERS", "value": "$12.04B", "tone": "leading", "detail": "+30% YoY"},
            {"label": "BOOK / BILL", "value": "1.27x", "tone": "operating", "detail": "Orders ÷ Revenue"},
            {"label": "REVENUE", "value": "$9.48B", "tone": "actual", "detail": "+14% YoY"},
        ],
        "flow_title": "Demand-to-Revenue",
        "flow": [
            {"label": "Demand", "value": "DC + Grid", "detail": "Electrification"},
            {"label": "Orders", "value": "$12.04B", "detail": "+30% YoY"},
            {"label": "Execution", "value": "1.27x", "detail": "Book-to-Bill"},
            {"label": "Revenue", "value": "$9.48B", "detail": "+14% YoY"},
        ],
        "financial_title": "Q2 2026 수익성",
        "financials": [
            {"label": "Operational EBITA", "value": "+$1.93B", "tone": "profit"},
            {"label": "Operational EBITA Margin", "value": "20.2%", "tone": "profit"},
            {"label": "Operating Cash Flow", "value": "+$1.15B", "tone": "actual"},
            {"label": "Free Cash Flow", "value": "+$881M", "tone": "profit"},
        ],
        "financial_note": "Orders는 ABB 전체 수주이며 AI 데이터센터 전용 수치가 아닙니다.",
        "status": {"emoji": "🟢", "label": "수주·마진 동반 성장", "tone": "operating"},
        "next_checks": [
            "Electrification 수주 증가 지속",
            "데이터센터 주문 성장",
            "Book-to-Bill 1.0x 이상 유지",
            "Operational EBITA 마진 20%대 유지",
        ],
        "break_conditions": [
            "Book-to-Bill 1.0x 미만 지속",
            "수주잔고 감소",
            "데이터센터 전력 투자 연기",
            "마진 하락과 재고 증가 동시 발생",
        ],
        "source_label": "ABB Q2 2026 Results",
        "source_url": "https://new.abb.com/news/detail/137496/q2-2026-results",
    },
    "VRT": {
        "period": "Q2 2026",
        "updated": "2026-07-29",
        "badges": [
            {"label": "Q2 SALES", "value": "$3.27B", "tone": "actual", "detail": "+24% YoY"},
            {"label": "ADJ. MARGIN", "value": "22.6%", "tone": "profit", "detail": "+410 bps"},
            {"label": "FY26 GUIDE", "value": "$14.0B", "tone": "forward", "detail": "Midpoint"},
        ],
        "flow_title": "AI Buildout-to-Revenue",
        "flow": [
            {"label": "Buildout", "value": "AI Data Center", "detail": "Structural demand"},
            {"label": "Infrastructure", "value": "Power + Cooling", "detail": "Critical path"},
            {"label": "Delivery", "value": "+18%", "detail": "Organic sales"},
            {"label": "Q2 Sales", "value": "$3.27B", "detail": "+24% YoY"},
        ],
        "financial_title": "Q2 2026 수익성",
        "financials": [
            {"label": "Adjusted Operating Profit", "value": "+$738M", "tone": "profit"},
            {"label": "Adjusted Operating Margin", "value": "22.6%", "tone": "profit"},
            {"label": "Operating Cash Flow", "value": "+$1.10B", "tone": "actual"},
            {"label": "Adjusted Free Cash Flow", "value": "+$925M", "tone": "profit"},
        ],
        "financial_note": "FY26 가이던스는 매출 $13.8B–$14.2B, 유기적 성장 30–32%입니다.",
        "status": {"emoji": "🟢", "label": "수요 강세 + 마진 확장", "tone": "operating"},
        "next_checks": [
            "Q3 유기적 성장률 34–36% 달성",
            "조정 영업마진 24% 이상 진입",
            "대형 프로젝트 납기",
            "현금흐름이 매출 성장과 함께 증가",
        ],
        "break_conditions": [
            "수주 또는 프로젝트 파이프라인 감소",
            "연간 가이던스 하향",
            "공급망 병목으로 반복적인 매출 인식 지연",
            "매출 증가에도 영업마진 하락",
        ],
        "source_label": "Vertiv Q2 2026 Results",
        "source_url": "https://investors.vertiv.com/news/news-details/2026/Vertiv-Reports-Strong-Second-Quarter-2026-with-Diluted-EPS-Growth-of-53-Adjusted-Diluted-EPS-Growth-of-60-Raises-Full-Year-2026-Guidance-Across-All-Key-Metrics/default.aspx",
    },
}


def _tone(tone):
    return TONE_COLORS.get(tone, ("#6b7280", "rgba(107,114,128,.09)"))


def has_fundamental_detail(symbol):
    """Fundamental Detail 패널을 띄울 수 있는 종목인지.

    PORTFOLIO에는 있지만 FUNDAMENTAL_DETAILS에 스냅샷이 없는 종목이 있을 수 있다.
    그런 종목까지 상세 버튼을 렌더하면 show_fundamental_detail()에서 KeyError가 난다.
    """
    return symbol in FUNDAMENTAL_DETAILS


def fundamental_badges_html(symbol):
    detail = FUNDAMENTAL_DETAILS.get(symbol)
    if not detail:
        return ""

    badges = []
    for badge in detail["badges"]:
        color, background = _tone(badge["tone"])
        label = html.escape(badge["label"])
        value = html.escape(badge["value"])
        badges.append(
            f'<span style="display:inline-flex;align-items:center;gap:5px;border:1px solid {color}55;'
            f'background:{background};color:{color};border-radius:999px;padding:4px 8px;font-size:10px;'
            f'font-weight:700;white-space:nowrap;"><span>{label}</span><strong>{value}</strong></span>'
        )

    return (
        '<div style="border-top:1px dashed rgba(107,114,128,.35);margin-top:12px;padding-top:10px;">'
        '<div style="font-size:9px;font-weight:700;letter-spacing:.08em;color:#2563eb;margin-bottom:7px;">'
        'FUNDAMENTAL SNAPSHOT · SCORE 미반영</div>'
        f'<div style="display:flex;gap:5px;flex-wrap:wrap;">{"".join(badges)}</div>'
        '</div>'
    )


def _kpi_html(badges):
    cards = []
    for badge in badges:
        color, background = _tone(badge["tone"])
        cards.append(
            '<div style="min-width:135px;flex:1;border:1px solid '
            f'{color}55;background:{background};border-radius:12px;padding:12px 14px;">'
            f'<div style="font-size:10px;font-weight:800;letter-spacing:.06em;color:{color};">'
            f'{html.escape(badge["label"])}</div>'
            f'<div style="font-size:24px;font-weight:800;margin-top:2px;">{html.escape(badge["value"])}</div>'
            f'<div style="font-size:11px;color:#6b7280;margin-top:2px;">{html.escape(badge["detail"])}</div>'
            '</div>'
        )
    return f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 18px;">{"".join(cards)}</div>'


def _flow_html(stages):
    items = []
    for index, stage in enumerate(stages):
        if index:
            items.append('<div style="align-self:center;color:#9ca3af;font-size:22px;">→</div>')
        items.append(
            '<div style="min-width:120px;flex:1;border:1px solid rgba(107,114,128,.25);'
            'border-radius:10px;padding:10px;background:rgba(107,114,128,.04);">'
            f'<div style="font-size:10px;color:#6b7280;font-weight:700;">{html.escape(stage["label"])}</div>'
            f'<div style="font-size:16px;font-weight:800;margin-top:2px;">{html.escape(stage["value"])}</div>'
            f'<div style="font-size:10px;color:#6b7280;margin-top:2px;">{html.escape(stage["detail"])}</div>'
            '</div>'
        )
    return (
        '<div style="display:flex;gap:6px;align-items:stretch;overflow-x:auto;padding:2px 0 12px;">'
        f'{"".join(items)}</div>'
    )


def _financials_html(financials):
    rows = []
    for item in financials:
        color, _ = _tone(item["tone"])
        rows.append(
            '<div style="display:flex;justify-content:space-between;gap:12px;padding:8px 2px;'
            'border-bottom:1px solid rgba(107,114,128,.16);font-size:13px;">'
            f'<span>{html.escape(item["label"])}</span>'
            f'<strong style="color:{color};">{html.escape(item["value"])}</strong>'
            '</div>'
        )
    return f'<div style="margin-bottom:8px;">{"".join(rows)}</div>'


@st.dialog("Fundamental Detail", width="large")
def show_fundamental_detail(symbol):
    detail = FUNDAMENTAL_DETAILS[symbol]
    st.markdown(f"### {html.escape(symbol)} · Fundamental Detail")
    st.caption(f"{detail['period']} · Updated {detail['updated']} · 공식 공시 스냅샷")
    st.caption("이 패널은 Price Score · Grade · Action · Shadow 계산에 반영되지 않습니다.")

    st.markdown(_kpi_html(detail["badges"]), unsafe_allow_html=True)

    st.markdown(f"#### {detail['flow_title']}")
    st.markdown(_flow_html(detail["flow"]), unsafe_allow_html=True)

    st.markdown(f"#### {detail['financial_title']}")
    st.markdown(_financials_html(detail["financials"]), unsafe_allow_html=True)
    st.caption(detail["financial_note"])

    status = detail["status"]
    status_color, status_background = _tone(status["tone"])
    st.markdown(
        '<div style="margin:16px 0 12px;border-left:4px solid '
        f'{status_color};background:{status_background};border-radius:8px;padding:11px 13px;">'
        f'<strong>{status["emoji"]} Thesis Status: {html.escape(status["label"])}</strong></div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)
    with left:
        st.markdown("**다음 확인**")
        st.markdown("\n".join(f"- {item}" for item in detail["next_checks"]))
    with right:
        st.markdown("**논리 훼손**")
        st.markdown("\n".join(f"- {item}" for item in detail["break_conditions"]))

    st.divider()
    st.markdown(f"Source: [{detail['source_label']}]({detail['source_url']})")
