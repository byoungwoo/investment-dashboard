import html
import json
import math
import pathlib
from datetime import date

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
#
# 값은 data/fundamentals/<TICKER>.json 에 있다. 분기마다 바뀌는 것은 숫자뿐이고
# 렌더 로직은 그대로다. 데이터를 파일로 분리해 두면 스냅샷을 갱신할 때
# 이 모듈의 함수를 건드릴 일이 없다.
SNAPSHOT_DIR = pathlib.Path(__file__).resolve().parent / "data" / "fundamentals"


def load_snapshots(directory=None):
    """<TICKER>.json 을 전부 읽어 {심볼: 스냅샷} 으로 돌려준다.

    파일명이 심볼이다 — 파일 안에 심볼을 다시 적으면 둘이 어긋날 수 있다.
    """
    directory = pathlib.Path(directory) if directory else SNAPSHOT_DIR
    snapshots = {}
    for path in sorted(directory.glob("*.json")):
        with open(path, encoding="utf-8") as handle:
            snapshots[path.stem] = json.load(handle)
    return snapshots


FUNDAMENTAL_DETAILS = load_snapshots()


# 분기는 약 91일이다. 그보다 오래된 스냅샷은 다음 분기 실적이 이미 나왔을
# 가능성이 있다 — 화면이 조용히 과거를 보여주는 것을 막는다.
STALE_AFTER_DAYS = 100


def snapshot_age_days(detail, today=None):
    """스냅샷 기준일로부터 며칠 지났나. `updated` 가 날짜가 아니면 None."""
    try:
        updated = date.fromisoformat(detail["updated"])
    except (KeyError, TypeError, ValueError):
        return None
    return ((today or date.today()) - updated).days


def staleness_note(detail, today=None):
    """상세 패널에 띄울 신선도 경고. 아직 신선하면 None 을 돌려 아무것도 띄우지 않는다."""
    age = snapshot_age_days(detail, today)
    if age is None or age < STALE_AFTER_DAYS:
        return None
    return (
        f"이 스냅샷은 {age}일 전({detail['updated']}) 공시 기준입니다. "
        "다음 분기 실적이 이미 발표됐을 수 있습니다."
    )


def _tone(tone):
    return TONE_COLORS.get(tone, ("#6b7280", "rgba(107,114,128,.09)"))


def has_fundamental_detail(symbol):
    """Fundamental Detail 패널을 띄울 수 있는 종목인지.

    PORTFOLIO에는 있지만 FUNDAMENTAL_DETAILS에 스냅샷이 없는 종목이 있을 수 있다.
    그런 종목까지 상세 버튼을 렌더하면 show_fundamental_detail()에서 KeyError가 난다.
    """
    return symbol in FUNDAMENTAL_DETAILS


def arr_multiples(detail, enterprise_value):
    """공시 ARR을 분모로 라이브 EV 배수를 낸다.

    EV는 주가라서 매일 바뀐다. 공시 스냅샷과 같은 블록에 두면 "Updated" 날짜가
    거짓이 되므로 호출부에서 분리해 렌더한다. EV가 없으면 빈 리스트를 돌려
    아무것도 그리지 않는다 — 배수를 지어내지 않는다.
    """
    spec = detail.get("arr_multiples")
    if not spec or isinstance(enterprise_value, bool):
        return []
    if not isinstance(enterprise_value, (int, float)):
        return []
    # yfinance는 결측을 NaN으로 주기도 한다. 걸러내지 않으면 "nanx"가 렌더된다.
    if not math.isfinite(enterprise_value) or enterprise_value <= 0:
        return []
    return [
        {
            "label": item["label"],
            "value": f'{enterprise_value / item["arr"]:.1f}x',
            "tone": item["tone"],
        }
        for item in spec
    ]


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
def show_fundamental_detail(symbol, enterprise_value=None):
    detail = FUNDAMENTAL_DETAILS[symbol]
    st.markdown(f"### {html.escape(symbol)} · Fundamental Detail")
    st.caption(f"{detail['period']} · Updated {detail['updated']} · 공식 공시 스냅샷")
    st.caption("이 패널은 Price Score · Grade · Action · Shadow 계산에 반영되지 않습니다.")

    stale = staleness_note(detail)
    if stale:
        st.warning(stale)

    st.markdown(_kpi_html(detail["badges"]), unsafe_allow_html=True)

    st.markdown(f"#### {detail['flow_title']}")
    st.markdown(_flow_html(detail["flow"]), unsafe_allow_html=True)

    multiples = arr_multiples(detail, enterprise_value)
    if multiples:
        st.markdown("#### EV / ARR · 라이브 시장값")
        st.markdown(_financials_html(multiples), unsafe_allow_html=True)
        st.caption(
            "EV는 주가에 따라 매일 바뀌므로 위 공시 스냅샷의 일부가 아닙니다. "
            "두 배수의 간격이 아직 가동되지 않은 ARR이며, 그 전환은 가동 일정에 달려 있습니다. "
            "계약 기준 배수는 미가동 ARR을 분모에 넣은 값이므로 일정이 밀릴수록 싸 보입니다."
        )

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

    # 세부 평가는 Thesis Status 한 줄로는 담기지 않는다. 축별로 방향이 갈릴 때
    # (수요는 강화, 일정은 지연) 재무 행 렌더러를 그대로 재사용해 label-value로 적는다.
    if detail.get("status_breakdown"):
        st.markdown(_financials_html(detail["status_breakdown"]), unsafe_allow_html=True)

    left, right = st.columns(2)
    with left:
        st.markdown("**다음 확인**")
        st.markdown("\n".join(f"- {item}" for item in detail["next_checks"]))
    with right:
        st.markdown("**논리 훼손**")
        st.markdown("\n".join(f"- {item}" for item in detail["break_conditions"]))

    st.divider()
    st.markdown(f"Source: [{detail['source_label']}]({detail['source_url']})")
