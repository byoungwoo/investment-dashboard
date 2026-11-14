"""백테스트 출력 디렉터리를 self-contained HTML 차트 한 장으로 만든다.

의존성은 표준 라이브러리뿐이다. matplotlib을 쓰면 requirements.txt에 들어가고,
그러면 배포되는 Streamlit 앱까지 끌고 들어간다 — 이 차트는 로컬 실험 결과를
보는 도구일 뿐이므로 앱의 의존성을 늘리지 않는다.

사용법:
    python3 scripts/plot_equity.py <백테스트 출력 디렉터리>
"""
import csv
import html
import json
import math
import pathlib
import sys

# dataviz 스킬의 기준 팔레트. 라이트/다크 양쪽 ALL PASS 검증된 슬롯 1·2다.
#   node scripts/validate_palette.js "#2a78d6,#eb6834" --mode light
#   node scripts/validate_palette.js "#3987e5,#d95926" --mode dark
SERIES = [
    {"key": "equity", "label": "분할매수 전략", "light": "#2a78d6", "dark": "#3987e5"},
    {"key": "buy_hold", "label": "전량 매수보유", "light": "#eb6834", "dark": "#d95926"},
]

WIDTH, HEIGHT = 920, 380
LABEL_MIN_GAP = 14          # 11px 글자가 겹치지 않는 최소 세로 간격
PAD = {"top": 18, "right": 124, "bottom": 34, "left": 68}


def read_equity(directory):
    rows = []
    with open(directory / "equity.csv", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            point = {"date": row["Date"]}
            for series in SERIES:
                raw = row.get(series["key"])
                point[series["key"]] = float(raw) if raw not in (None, "") else None
            rows.append(point)
    if not rows:
        raise SystemExit("equity.csv 가 비어 있다")
    return rows


def read_trades(directory):
    path = directory / "trades.csv"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as handle:
        return [row["date"][:10] for row in csv.DictReader(handle) if row.get("date")]


def read_summary(directory):
    path = directory / "summary.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _scales(rows):
    values = [v for row in rows for key in (s["key"] for s in SERIES)
              if (v := row.get(key)) is not None]
    low, high = min(values), max(values)
    if low == high:                      # 평평한 곡선도 선이 보여야 한다
        pad = abs(low) * 0.01 or 1.0     # 값이 0이면 비율 패딩도 0이라 0으로 나눈다
        low, high = low - pad, high + pad
    span = high - low
    low, high = low - span * 0.08, high + span * 0.08
    plot_w = WIDTH - PAD["left"] - PAD["right"]
    plot_h = HEIGHT - PAD["top"] - PAD["bottom"]
    last = max(len(rows) - 1, 1)

    def x(i):
        return PAD["left"] + plot_w * i / last

    def y(value):
        return PAD["top"] + plot_h * (1 - (value - low) / (high - low))

    return x, y, low, high


def _nice_step(span, count):
    """1·2·5 × 10ⁿ 중 이상적 간격에 가장 가까운 단계. 올림만 하면 간격이 두 배로
    튀어 눈금이 두어 개만 남는다 — 그래서 로그상 거리로 가장 가까운 것을 고른다."""
    raw = span / max(count - 1, 1)
    if raw <= 0:
        return 1.0
    power = 10 ** math.floor(math.log10(raw))
    candidates = [mult * power for mult in (1, 2, 5, 10)]
    return min(candidates, key=lambda step: abs(math.log10(step / raw)))


def _ticks(low, high, count=5):
    """눈금은 9,613,346 이 아니라 10,000,000 으로 읽혀야 한다. 범위 안에 드는
    배수만 남기므로 개수는 count 와 다를 수 있다 — 깔끔한 수가 우선이다."""
    step = _nice_step(high - low, count)
    value = math.ceil(low / step) * step
    ticks = []
    while value <= high + step * 1e-9:
        ticks.append(value)
        value += step
    return ticks or [low, high]


def _js(value):
    """<script> 안에 박는 JSON. `</script>` 가 든 CSV 한 줄이 페이지를 끊어먹지
    않도록 꺾쇠와 앰퍼샌드까지 escape 한다 — json.dumps 는 거기까지 하지 않는다."""
    return (json.dumps(value, ensure_ascii=False)
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))


def _money(value):
    return f"{value:,.0f}"


def _svg(rows, trades, initial):
    x, y, low, high = _scales(rows)
    parts = []

    # 격자와 y축 — 눈금은 데이터가 아니므로 뒤로 물린다
    for value in _ticks(low, high):
        gy = y(value)
        parts.append(f'<line x1="{PAD["left"]}" y1="{gy:.1f}" x2="{WIDTH - PAD["right"]}" '
                     f'y2="{gy:.1f}" stroke="var(--grid)" stroke-width="1"/>')
        parts.append(f'<text x="{PAD["left"] - 10}" y="{gy + 4:.1f}" text-anchor="end" '
                     f'class="tick">{_money(value)}</text>')

    # 최초 자금선 — 손익 0 기준. 점선으로 데이터와 구별한다
    if low <= initial <= high:
        iy = y(initial)
        parts.append(f'<line x1="{PAD["left"]}" y1="{iy:.1f}" x2="{WIDTH - PAD["right"]}" '
                     f'y2="{iy:.1f}" stroke="var(--axis)" stroke-width="1" stroke-dasharray="4 4"/>')
        parts.append(f'<text x="{WIDTH - PAD["right"] + 6}" y="{iy + 4:.1f}" '
                     f'class="tick">최초 자금</text>')

    # x축 날짜 — 양 끝과 가운데만. 모든 점에 날짜를 달면 읽을 수 없다
    for i in {0, len(rows) // 2, len(rows) - 1}:
        anchor = "start" if i == 0 else ("end" if i == len(rows) - 1 else "middle")
        parts.append(f'<text x="{x(i):.1f}" y="{HEIGHT - PAD["bottom"] + 20}" '
                     f'text-anchor="{anchor}" class="tick">'
                     f'{html.escape(rows[i]["date"])}</text>')

    # 선 — 2px, round join/cap
    ends = []
    for index, series in enumerate(SERIES, start=1):
        points = [(x(i), y(row[series["key"]])) for i, row in enumerate(rows)
                  if row.get(series["key"]) is not None]
        if not points:
            continue
        path = " ".join(f'{"M" if n == 0 else "L"}{px:.1f} {py:.1f}'
                        for n, (px, py) in enumerate(points))
        parts.append(f'<path class="series" d="{path}" fill="none" '
                     f'stroke="var(--series-{index})" stroke-width="2" '
                     f'stroke-linejoin="round" stroke-linecap="round"/>')
        ends.append({"index": index, "x": points[-1][0], "y": points[-1][1],
                     "y_line": points[-1][1], "label": series["label"]})

    # 직접 라벨 — 범례와 함께 두어 색만으로 구분하지 않게 한다. 두 곡선이 비슷한
    # 값으로 끝나면 라벨이 겹치므로 최소 간격까지 벌린다. 흔한 경우다.
    #
    # 이 분리는 쌍 하나에만 올바르다. 3개 이상에서는 인접 쌍을 한 번 훑는 것으로
    # 수렴하지 않는다 (같은 값 3개 → 최소 간격 3.5px, 손으로 확인). 시리즈를
    # 늘리려면 라벨 스태킹을 먼저 고쳐야 하므로 조용히 겹치는 대신 여기서 멈춘다.
    if len(ends) > 2:
        raise ValueError(
            "직접 라벨 분리가 2개까지만 올바르다. SERIES를 늘리기 전에 "
            "라벨 스태킹을 고쳐라 (scripts/plot_equity.py)"
        )
    for a, b in zip(ends, ends[1:]):
        overlap = LABEL_MIN_GAP - abs(b["y"] - a["y"])
        if overlap > 0:
            upper, lower = sorted((a, b), key=lambda e: e["y"])
            upper["y"] -= overlap / 2
            lower["y"] += overlap / 2
    for end in ends:
        # 벌린 라벨은 제 선에서 떨어진다. 연결선으로 다시 붙이고, 그 끝의 가로
        # 토막이 색 키 노릇을 한다 — 글자 자체에는 계열색을 입히지 않는다.
        # #eb6834 은 라이트 표면에서 3.12:1 이라 본문 글자 대비에 못 미친다.
        parts.append(f'<path class="leader" d="M{end["x"]:.1f} {end["y_line"]:.1f} '
                     f'L{end["x"] + 6:.1f} {end["y"]:.1f} '
                     f'L{end["x"] + 16:.1f} {end["y"]:.1f}" fill="none" '
                     f'stroke="var(--series-{end["index"]})" stroke-width="2" '
                     f'stroke-linejoin="round" stroke-linecap="round"/>')
        parts.append(f'<text x="{end["x"] + 22:.1f}" y="{end["y"] + 4:.1f}" '
                     f'class="direct">{html.escape(end["label"])}</text>')

    # 체결 지점 — 표면색 2px 링을 둘러 선 위에서도 읽히게 한다
    by_date = {row["date"]: i for i, row in enumerate(rows)}
    for traded in trades:
        i = by_date.get(traded)
        if i is None or rows[i].get("equity") is None:
            continue
        parts.append(f'<circle cx="{x(i):.1f}" cy="{y(rows[i]["equity"]):.1f}" r="4.5" '
                     f'fill="var(--series-1)" stroke="var(--surface)" stroke-width="2"/>')

    return (f'<svg viewBox="0 0 {WIDTH} {HEIGHT}" width="100%" tabindex="0" '
            f'role="img" aria-label="백테스트 평가액 추이. 좌우 화살표로 날짜별 값을 읽는다"'
            f'>{"".join(parts)}</svg>')


def _stat(label, value, tone=""):
    return (f'<div class="stat"><div class="stat-label">{html.escape(label)}</div>'
            f'<div class="stat-value {tone}">{html.escape(value)}</div></div>')


def _table(rows, trades):
    traded = set(trades)
    body = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            html.escape(row["date"]),
            _money(row["equity"]) if row.get("equity") is not None else "—",
            _money(row["buy_hold"]) if row.get("buy_hold") is not None else "—",
            "체결" if row["date"] in traded else "",
        )
        for row in rows
    )
    return ('<details><summary>표로 보기</summary><div class="scroll"><table>'
            "<thead><tr><th>날짜</th><th>분할매수 전략</th><th>전량 매수보유</th><th></th></tr></thead>"
            f"<tbody>{body}</tbody></table></div></details>")


def render(directory):
    directory = pathlib.Path(directory)
    rows = read_equity(directory)
    trades = read_trades(directory)
    summary = read_summary(directory)
    initial = rows[0]["equity"] if rows[0].get("equity") is not None else 0.0

    def pct(key):
        value = summary.get(key)
        return f"{value:+.2f}%" if isinstance(value, (int, float)) else "N/A"

    strategy = summary.get("return_pct")
    hold = summary.get("buy_hold_return_pct")
    comparable = isinstance(strategy, (int, float)) and isinstance(hold, (int, float))
    gap = f"{strategy - hold:+.2f}%p" if comparable else "N/A"
    # 부호가 이미 방향을 말한다 — 색은 거드는 채널이지 혼자 뜻을 지지 않는다
    gap_tone = ("good" if strategy >= hold else "bad") if comparable else ""

    stats = "".join([
        _stat("분할매수 전략", pct("return_pct")),
        _stat("전량 매수보유", pct("buy_hold_return_pct")),
        _stat("차이", gap, gap_tone),
        _stat("최대 낙폭", pct("max_drawdown_pct")),
        _stat("체결", f"{len(trades)}회"),
        _stat("Opportunity 자료 커버리지",
              f'{summary.get("opportunity_coverage_pct", 0):.0f}%'),
    ])

    # 거래가 없으면 수익률 0%가 "전략이 본전"으로 읽힌다. 실제로는 아무것도 안 산 것이다.
    notice = ""
    if not trades:
        notice = ('<p class="notice"><span aria-hidden="true">⚠</span> 체결이 0회다. '
                  '조건이 성립한 날이 없었거나 시점별 밸류에이션 자료가 없었다는 뜻이며, '
                  '<strong>전략 성과가 아니다.</strong></p>')

    return f"""<meta charset="utf-8">
<title>백테스트 평가액 추이</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  .viz-root {{
    color-scheme: light;
    --surface: #fcfcfb; --plane: #f9f9f7;
    --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
    --grid: #e1e0d9; --axis: #c3c2b7; --border: rgba(11,11,11,.10);
    --series-1: #2a78d6; --series-2: #eb6834;
    /* 상태색은 테마를 타지 않는다. 계열색을 상태에 돌려 쓰지 않으려고 따로 둔다 */
    --good: #0ca30c; --critical: #d03b3b; --warning: #fab219;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:where(:not([data-theme="light"])) .viz-root {{
      color-scheme: dark;
      --surface: #1a1a19; --plane: #0d0d0d;
      --ink: #fff; --ink-2: #c3c2b7; --muted: #898781;
      --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,.10);
      --series-1: #3987e5; --series-2: #d95926;
    }}
  }}
  :root[data-theme="dark"] .viz-root {{
    color-scheme: dark;
    --surface: #1a1a19; --plane: #0d0d0d;
    --ink: #fff; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,.10);
    --series-1: #3987e5; --series-2: #d95926;
  }}
  body {{ margin: 0; background: var(--plane); }}
  .viz-root {{
    font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif;
    background: var(--plane); color: var(--ink);
    padding: 24px; min-height: 100vh; box-sizing: border-box;
  }}
  .card {{ background: var(--surface); border: 1px solid var(--border);
           border-radius: 12px; padding: 18px; max-width: 1000px; margin: 0 auto; }}
  h1 {{ font-size: 17px; margin: 0 0 2px; }}
  .sub {{ color: var(--ink-2); font-size: 12px; margin: 0 0 16px; }}
  .stats {{ display: grid; gap: 8px; margin-bottom: 14px;
            grid-template-columns: repeat(auto-fill, minmax(136px, 1fr)); }}
  .stat {{ border: 1px solid var(--border); border-radius: 10px; padding: 9px 11px; }}
  /* keep-all 이 없으면 "커버리지"가 음절 중간에서 끊긴다 */
  .stat-label {{ font-size: 11px; color: var(--ink-2); word-break: keep-all; }}
  .stat-value {{ font-size: 19px; font-weight: 700; margin-top: 1px; }}
  .stat-value.good {{ color: var(--good); }}
  .stat-value.bad {{ color: var(--critical); }}
  .legend {{ display: flex; gap: 16px; align-items: center; margin: 0 0 6px;
             font-size: 12px; color: var(--ink-2); flex-wrap: wrap; }}
  .key {{ display: inline-block; width: 16px; height: 2px; border-radius: 2px;
          margin-right: 6px; vertical-align: 4px; }}
  .key.dot {{ width: 9px; height: 9px; border-radius: 50%; vertical-align: -1px; }}
  .chart {{ position: relative; overflow-x: auto; }}
  text.tick {{ fill: var(--muted); font-size: 11px; font-variant-numeric: tabular-nums; }}
  text.direct {{ font-size: 11px; font-weight: 600; fill: var(--ink-2); }}
  .notice {{ border-left: 3px solid var(--warning); background: var(--plane);
             padding: 9px 12px; border-radius: 6px; font-size: 12.5px; color: var(--ink-2); }}
  #tip {{ position: absolute; pointer-events: none; opacity: 0; transition: opacity .1s;
          background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
          padding: 7px 9px; font-size: 12px; white-space: nowrap;
          box-shadow: 0 2px 10px rgba(0,0,0,.14); font-variant-numeric: tabular-nums; }}
  #tip .tip-date {{ color: var(--ink-2); font-size: 11px; margin-bottom: 2px; }}
  #tip .tip-row {{ display: flex; align-items: center; gap: 6px; line-height: 1.55; }}
  #tip .tip-value {{ color: var(--ink); font-weight: 700; }}
  #tip .tip-name {{ color: var(--ink-2); font-size: 11px; }}
  #tip .tip-trade {{ color: var(--ink-2); font-size: 11px; margin-top: 2px; }}
  #tip .tip-trade:empty {{ display: none; }}
  .chart svg:focus-visible {{ outline: 2px solid var(--ink-2); outline-offset: 2px; }}
  details {{ margin-top: 14px; font-size: 13px; color: var(--ink-2); }}
  .scroll {{ overflow-x: auto; max-height: 320px; overflow-y: auto; }}
  table {{ border-collapse: collapse; font-size: 12px; margin-top: 8px; width: 100%; }}
  th, td {{ text-align: right; padding: 4px 10px; border-bottom: 1px solid var(--grid);
            font-variant-numeric: tabular-nums; }}
  th:first-child, td:first-child {{ text-align: left; }}
</style>
<div class="viz-root"><div class="card">
  <h1>백테스트 평가액 추이</h1>
  <p class="sub">미투자 현금을 포함한 총 평가액. 일별 종가 평가이며 장중 손실이 아니다.
     재현 실험 결과이고 투자 권고가 아니다.</p>
  <div class="stats">{stats}</div>
  {notice}
  <div class="legend">
    <span><span class="key" style="background:var(--series-1)"></span>분할매수 전략</span>
    <span><span class="key" style="background:var(--series-2)"></span>전량 매수보유</span>
    <span><span class="key dot" style="background:var(--series-1)"></span>체결 시점</span>
  </div>
  <div class="chart" id="chart">{_svg(rows, trades, initial)}<div id="tip" role="status"
       aria-live="polite"></div></div>
  {_table(rows, trades)}
</div></div>
<script>
const DATA = {_js(rows)};
const TRADED = new Set({_js(sorted(set(trades)))});
const KEYS = {_js([{"key": s["key"], "slot": i, "name": s["label"]}
                   for i, s in enumerate(SERIES, start=1)])};
const chart = document.getElementById('chart');
const svg = chart.querySelector('svg');
const tip = document.getElementById('tip');
const L = {PAD["left"]}, R = {WIDTH - PAD["right"]}, W = {WIDTH};
const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
line.setAttribute('stroke', 'var(--axis)');
line.setAttribute('stroke-width', '1');
line.setAttribute('y1', {PAD["top"]});
line.setAttribute('y2', {HEIGHT - PAD["bottom"]});
line.setAttribute('opacity', '0');
svg.appendChild(line);

// 툴팁은 한 번 짓고 textContent 로만 갱신한다. 날짜는 CSV에서 온 값이라
// innerHTML 로 꽂으면 자료가 마크업이 된다.
const add = (tag, cls, parent) => {{
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  (parent || tip).appendChild(node);
  return node;
}};
const tipDate = add('div', 'tip-date');
const values = {{}};
for (const s of KEYS) {{
  const row = add('div', 'tip-row');
  add('span', 'key', row).style.background = 'var(--series-' + s.slot + ')';
  values[s.key] = add('strong', 'tip-value', row);   // 값이 먼저, 이름은 거든다
  add('span', 'tip-name', row).textContent = s.name;
}}
const tipTrade = add('div', 'tip-trade');

const fmt = v => v == null ? '—' : v.toLocaleString(undefined, {{maximumFractionDigits: 0}});
let active = -1;

function show(i) {{
  active = Math.max(0, Math.min(DATA.length - 1, i));
  const row = DATA[active];
  const px = L + (R - L) * active / Math.max(DATA.length - 1, 1);
  line.setAttribute('x1', px); line.setAttribute('x2', px); line.setAttribute('opacity', '1');
  tipDate.textContent = row.date;
  for (const s of KEYS) values[s.key].textContent = fmt(row[s.key]);
  // 체결 점은 반지름 4.5px 이라 그 자체를 겨냥할 수 없다 — 크로스헤어가 대신 알린다
  tipTrade.textContent = TRADED.has(row.date) ? '이 날 체결' : '';
  tip.style.opacity = 1;
  const box = svg.getBoundingClientRect();
  const left = px / W * box.width;
  tip.style.left = Math.max(0, Math.min(left + 14, box.width - tip.offsetWidth - 4)) + 'px';
  tip.style.top = '14px';
}}

function hide() {{
  tip.style.opacity = 0;
  line.setAttribute('opacity', '0');
}}

svg.addEventListener('pointermove', event => {{
  const box = svg.getBoundingClientRect();
  const vx = (event.clientX - box.left) / box.width * W;
  if (vx < L || vx > R) {{ hide(); return; }}
  show(Math.round((vx - L) / (R - L) * (DATA.length - 1)));
}});
svg.addEventListener('pointerleave', hide);

// 호버로만 읽히게 두지 않는다 — 키보드에서도 같은 값이 나온다
svg.addEventListener('focus', () => show(active < 0 ? 0 : active));
svg.addEventListener('blur', hide);
svg.addEventListener('keydown', event => {{
  const step = event.shiftKey ? 10 : 1;
  if (event.key === 'ArrowRight') show(active + step);
  else if (event.key === 'ArrowLeft') show(active - step);
  else if (event.key === 'Home') show(0);
  else if (event.key === 'End') show(DATA.length - 1);
  else if (event.key === 'Escape') hide();
  else return;
  event.preventDefault();
}});
</script>
"""


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    directory = pathlib.Path(sys.argv[1])
    out = directory / "equity.html"
    out.write_text(render(directory), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
