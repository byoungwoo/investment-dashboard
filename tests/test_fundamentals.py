import unittest

from config import PORTFOLIO
from fundamentals import (
    FUNDAMENTAL_DETAILS,
    arr_multiples,
    TONE_COLORS,
    _financials_html,
    fundamental_badges_html,
    has_fundamental_detail,
)


class FundamentalDetailsTest(unittest.TestCase):
    def test_registered_snapshots_are_complete(self):
        self.assertEqual({"AVGO", "ABB", "VRT", "IREN"}, set(FUNDAMENTAL_DETAILS))
        for symbol, detail in FUNDAMENTAL_DETAILS.items():
            self.assertEqual(3, len(detail["badges"]), symbol)
            self.assertGreaterEqual(len(detail["flow"]), 3, symbol)
            self.assertGreaterEqual(len(detail["financials"]), 3, symbol)
            self.assertTrue(detail["source_url"].startswith("https://"), symbol)

    def test_snapshots_never_describe_an_unheld_symbol(self):
        self.assertLessEqual(set(FUNDAMENTAL_DETAILS), set(PORTFOLIO))

    def test_symbol_without_snapshot_is_gated_not_crashed(self):
        """스냅샷 없는 종목은 상세 버튼이 아예 렌더되지 않아야 한다.

        예전에는 버튼이 모든 종목에 렌더됐고, 스냅샷 없는 종목에서 누르면
        show_fundamental_detail()의 FUNDAMENTAL_DETAILS[symbol]이 KeyError를 냈다.

        PORTFOLIO - FUNDAMENTAL_DETAILS 를 돌리면 전 종목에 스냅샷이 있는 순간
        루프가 비어 아무것도 검사하지 않고 통과한다 (ORCL 제거 때 실제로 그렇게 됐다).
        가드는 포트폴리오 구성과 무관하게 동작해야 하므로 없는 심볼로 직접 찌른다.
        """
        missing = "ZZZZ"
        self.assertNotIn(missing, FUNDAMENTAL_DETAILS)
        self.assertFalse(has_fundamental_detail(missing))
        self.assertEqual("", fundamental_badges_html(missing))

        # 보유 종목에 스냅샷 공백이 생기면 그쪽도 같이 막혀야 한다.
        for symbol in set(PORTFOLIO) - set(FUNDAMENTAL_DETAILS):
            self.assertFalse(has_fundamental_detail(symbol), symbol)
            self.assertEqual("", fundamental_badges_html(symbol), symbol)

    def test_symbol_with_snapshot_is_allowed_through(self):
        for symbol in FUNDAMENTAL_DETAILS:
            self.assertTrue(has_fundamental_detail(symbol), symbol)

    def test_iren_snapshot_tracks_fy27_q1(self):
        """FY27 Q1(2026-11-05 발표) 기준 값 고정.

        AI 매출은 FY26 연간 $128.8M보다 이 한 분기가 더 크다. 과거 스냅샷이
        남아 있으면 "AI 매출이 정체"라는 이미 약해진 가설을 계속 보게 된다.
        """
        detail = FUNDAMENTAL_DETAILS["IREN"]
        self.assertEqual("Q1 FY2027", detail["period"])
        self.assertEqual("$200M", detail["badges"][0]["value"])
        rows = {item["label"]: item for item in detail["financials"]}
        self.assertEqual("-$263M", rows["GAAP Net Loss"]["value"])
        self.assertEqual("risk", rows["GAAP Net Loss"]["tone"])
        # 조정 EBITDA 흑자에 profit 톤을 주면 주식보상·감가상각·금융비용을
        # 제외한 수치가 순이익처럼 읽힌다. profit 톤은 GAAP 기준에만 쓴다.
        self.assertNotEqual("profit", rows["Adjusted EBITDA"]["tone"])
        # 조정 EBITDA $66M과 순손실 -$263M의 간격을 만드는 세 항목.
        # 이 행들이 빠지면 패널이 "흑자 전환"처럼 읽힌다.
        self.assertEqual("-$148M", rows["Depreciation & Amortization"]["value"])
        self.assertEqual("-$73M", rows["Finance Expense"]["value"])
        # 주식보상은 8-K 조정 EBITDA 조정표의 $106M이다. 다른 값이 들어오면
        # 출처를 다시 확인해야 한다 — 요약 기사와 공시가 어긋난 적이 있다.
        self.assertEqual("-$106M", rows["Stock-Based Compensation"]["value"])

    def test_iren_source_points_at_the_quarter_it_describes(self):
        detail = FUNDAMENTAL_DETAILS["IREN"]
        self.assertIn("q1-fy27", detail["source_url"])
        self.assertTrue(detail["source_url"].startswith("https://www.sec.gov/Archives/"))

    def test_arr_multiples_use_the_disclosed_denominators(self):
        detail = FUNDAMENTAL_DETAILS["IREN"]
        rows = arr_multiples(detail, 15.9e9)
        self.assertEqual(["15.9x", "4.0x"], [r["value"] for r in rows])
        # 분모는 패널에 적힌 ARR과 같아야 한다. 표시 문자열을 파싱하지 않고
        # 숫자를 따로 두는 이유 — "$1.0B"가 바뀌면 배수도 함께 바뀌어야 한다.
        self.assertEqual([1.0e9, 4.0e9], [item["arr"] for item in detail["arr_multiples"]])

    def test_arr_multiples_never_invent_a_number(self):
        """EV를 못 구하면 배수를 그리지 않는다 — 0으로 나누거나 추정하지 않는다."""
        detail = FUNDAMENTAL_DETAILS["IREN"]
        for bad in (None, 0, -1, float("nan"), "15.9B"):
            self.assertEqual([], arr_multiples(detail, bad), repr(bad))

    def test_arr_multiples_only_where_arr_is_disclosed(self):
        for symbol, detail in FUNDAMENTAL_DETAILS.items():
            if symbol == "IREN":
                continue
            self.assertEqual([], arr_multiples(detail, 15.9e9), symbol)

    def test_status_breakdown_is_optional_and_rendered_by_the_row_renderer(self):
        breakdown = FUNDAMENTAL_DETAILS["IREN"]["status_breakdown"]
        self.assertEqual(4, len(breakdown))
        rendered = _financials_html(breakdown)
        for item in breakdown:
            self.assertIn(item["label"], rendered)
            self.assertIn(item["value"], rendered)
        # 나머지 종목은 이 키가 없어도 패널이 떠야 한다.
        for symbol, detail in FUNDAMENTAL_DETAILS.items():
            self.assertIsInstance(detail.get("status_breakdown", []), list, symbol)

    def test_every_tone_is_defined(self):
        """톤 오타는 _tone()이 회색으로 조용히 대체한다 — 화면만 보면 모른다."""
        for symbol, detail in FUNDAMENTAL_DETAILS.items():
            tones = [item["tone"] for item in detail["badges"]]
            tones += [item["tone"] for item in detail["financials"]]
            tones += [item["tone"] for item in detail.get("status_breakdown", [])]
            tones.append(detail["status"]["tone"])
            for tone in tones:
                self.assertIn(tone, TONE_COLORS, symbol + ": " + tone)

    def test_badges_are_explicitly_excluded_from_score(self):
        rendered = fundamental_badges_html("IREN")
        self.assertIn("SCORE 미반영", rendered)
        self.assertIn("$200M", rendered)
        self.assertEqual("", fundamental_badges_html("UNKNOWN"))


if __name__ == "__main__":
    unittest.main()
