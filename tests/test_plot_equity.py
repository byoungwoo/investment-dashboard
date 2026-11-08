import pathlib
import re
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

from plot_equity import HEIGHT, LABEL_MIN_GAP, PAD, SERIES, WIDTH, render


def write_run(directory, rows, trades=(), summary=None):
    directory = pathlib.Path(directory)
    lines = ["Date,equity,buy_hold"]
    lines += [f"{date},{eq},{bh}" for date, eq, bh in rows]
    (directory / "equity.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    trade_lines = ["date,signal_date,price,shares,cash_spent,fee"]
    trade_lines += [f"{d},{d},100,1,100,0" for d in trades]
    (directory / "trades.csv").write_text("\n".join(trade_lines) + "\n", encoding="utf-8")
    if summary is not None:
        import json
        (directory / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return directory


def label_positions(markup):
    found = re.findall(
        r'<text x="([\d.]+)" y="([\d.]+)" class="direct"[^>]*>([^<]+)</text>', markup
    )
    return [(float(x), float(y), label) for x, y, label in found]


def coordinates(markup):
    svg = re.search(r"<svg[^>]*>.*?</svg>", markup, re.S).group(0)
    xs = [float(v) for v in re.findall(r'(?:x|x1|x2|cx)="([-\d.]+)"', svg)]
    ys = [float(v) for v in re.findall(r'(?:y|y1|y2|cy)="([-\d.]+)"', svg)]
    for a, b in re.findall(r"[ML]([\d.]+) ([\d.]+)", svg):
        xs.append(float(a))
        ys.append(float(b))
    return xs, ys


class EquityChartTest(unittest.TestCase):
    def test_direct_labels_never_overlap_when_curves_end_together(self):
        """두 곡선이 같은 값으로 끝나는 것은 흔하다 — 라벨이 겹치면 둘 다 못 읽는다."""
        with tempfile.TemporaryDirectory() as tmp:
            run = write_run(tmp, [("2026-01-01", 100, 100), ("2026-01-02", 150, 150)])
            labels = label_positions(render(run))
        self.assertEqual(2, len(labels))
        gap = abs(labels[0][1] - labels[1][1])
        # 14는 11px 글자가 겹치지 않는 간격이다. LABEL_MIN_GAP 으로 비교하면
        # 상수를 낮추는 순간 기준도 함께 낮아져 아무것도 지키지 못한다.
        self.assertGreaterEqual(gap, 14, f"라벨 간격 {gap}px")
        self.assertGreaterEqual(LABEL_MIN_GAP, 14)

    def test_labels_stay_inside_the_canvas_at_the_extremes(self):
        """곡선이 위아래 끝에 붙어도 라벨이 캔버스를 벗어나지 않아야 한다."""
        for rows in ([("2026-01-01", 1, 1000), ("2026-01-02", 1, 1000)],
                     [("2026-01-01", 1000, 1), ("2026-01-02", 1000, 1)]):
            with tempfile.TemporaryDirectory() as tmp:
                labels = label_positions(render(write_run(tmp, rows)))
            for _, y, label in labels:
                self.assertGreaterEqual(y, PAD["top"], label)
                self.assertLessEqual(y, HEIGHT, label)

    def test_a_third_series_stops_instead_of_overlapping_labels(self):
        """라벨 분리는 쌍 하나에만 올바르다 — 3개에서는 조용히 겹치는 대신 멈춘다."""
        import plot_equity
        extra = dict(plot_equity.SERIES[0], key="third", label="세 번째")
        rows = ["Date,equity,buy_hold,third",
                "2026-01-01,100,100,100", "2026-01-02,100,100,100"]
        with tempfile.TemporaryDirectory() as tmp:
            run = pathlib.Path(tmp)
            (run / "equity.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
            original = plot_equity.SERIES
            plot_equity.SERIES = original + [extra]
            try:
                with self.assertRaises(ValueError) as caught:
                    render(run)
            finally:
                plot_equity.SERIES = original
        self.assertIn("라벨 스태킹", str(caught.exception))

    def test_every_coordinate_is_inside_the_canvas(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [(f"2026-01-{d:02d}", 100 + d * 3, 100 + d) for d in range(1, 20)]
            xs, ys = coordinates(render(write_run(tmp, rows)))
        self.assertGreaterEqual(min(xs), 0)
        self.assertLessEqual(max(xs), WIDTH)
        self.assertGreaterEqual(min(ys), 0)
        self.assertLessEqual(max(ys), HEIGHT)

    def test_flat_curve_still_draws_a_line(self):
        """평평한 곡선에서 0으로 나누면 선이 사라진다."""
        with tempfile.TemporaryDirectory() as tmp:
            rows = [("2026-01-01", 500, 500), ("2026-01-02", 500, 500)]
            markup = render(write_run(tmp, rows))
        self.assertEqual(2, len(re.findall(r'<path d="M', markup)))
        self.assertNotIn("nan", markup.lower())

    def test_zero_trades_says_it_is_not_performance(self):
        """체결 0회에서 수익률 0%는 '본전'이 아니라 '아무것도 안 샀다'는 뜻이다."""
        rows = [("2026-01-01", 100, 100), ("2026-01-02", 100, 120)]
        with tempfile.TemporaryDirectory() as tmp:
            empty = render(write_run(tmp, rows, trades=()))
        with tempfile.TemporaryDirectory() as tmp:
            traded = render(write_run(tmp, rows, trades=("2026-01-02",)))
        self.assertIn("전략 성과가 아니다", empty)
        self.assertNotIn("전략 성과가 아니다", traded)

    def test_trade_markers_only_on_dates_present_in_the_curve(self):
        """곡선에 없는 날짜의 체결 마커를 그리면 엉뚱한 위치에 점이 찍힌다."""
        rows = [("2026-01-01", 100, 100), ("2026-01-02", 110, 100)]
        with tempfile.TemporaryDirectory() as tmp:
            markup = render(write_run(tmp, rows, trades=("2026-01-02", "2099-12-31")))
        self.assertEqual(1, len(re.findall(r"<circle", markup)))

    def test_table_view_exists_for_every_point(self):
        """색만으로 전달하지 않는다 — 표가 대체 경로다."""
        rows = [(f"2026-02-{d:02d}", 100 + d, 100) for d in range(1, 8)]
        with tempfile.TemporaryDirectory() as tmp:
            markup = render(write_run(tmp, rows))
        self.assertIn("<table", markup)
        self.assertEqual(len(rows), len(re.findall(r"<tr><td>2026-02", markup)))

    def test_both_themes_define_every_colour_they_use(self):
        """다크 블록에만 정의된 색이 있으면 라이트에서 투명해진다."""
        rows = [("2026-01-01", 100, 100), ("2026-01-02", 120, 110)]
        with tempfile.TemporaryDirectory() as tmp:
            markup = render(write_run(tmp, rows))
        used = set(re.findall(r"var\((--[a-z0-9-]+)\)", markup))
        light = markup.split("@media")[0]
        for token in used:
            self.assertIn(f"{token}:", light, f"{token} 가 라이트 팔레트에 없다")
        self.assertIn('prefers-color-scheme: dark', markup)
        self.assertIn('[data-theme="dark"]', markup)

    def test_series_colours_come_from_the_validated_palette(self):
        """팔레트를 손으로 고치면 검증을 다시 돌려야 한다 — 값을 못 박는다."""
        self.assertEqual(["#2a78d6", "#eb6834"], [s["light"] for s in SERIES])
        self.assertEqual(["#3987e5", "#d95926"], [s["dark"] for s in SERIES])

    def test_summary_numbers_are_shown_not_recomputed(self):
        rows = [("2026-01-01", 1000, 1000), ("2026-01-02", 1100, 1200)]
        summary = {"return_pct": 10.0, "buy_hold_return_pct": 20.0,
                   "max_drawdown_pct": -5.5, "opportunity_coverage_pct": 42.0}
        with tempfile.TemporaryDirectory() as tmp:
            markup = render(write_run(tmp, rows, trades=("2026-01-02",), summary=summary))
        self.assertIn("+10.00%", markup)
        self.assertIn("+20.00%", markup)
        self.assertIn("-5.50%", markup)
        self.assertIn("-10.00%p", markup)   # 전략 - 매수보유
        self.assertIn("42%", markup)

    def test_missing_summary_shows_na_instead_of_a_wrong_number(self):
        rows = [("2026-01-01", 100, 100), ("2026-01-02", 110, 100)]
        with tempfile.TemporaryDirectory() as tmp:
            markup = render(write_run(tmp, rows, trades=("2026-01-02",)))
        self.assertIn("N/A", markup)
        self.assertNotIn("+0.00%", markup)


if __name__ == "__main__":
    unittest.main()
