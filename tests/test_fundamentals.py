import unittest

from config import PORTFOLIO
from fundamentals import (
    FUNDAMENTAL_DETAILS,
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
        """스냅샷 없는 보유 종목은 상세 버튼이 아예 렌더되지 않아야 한다.

        예전에는 버튼이 모든 종목에 렌더됐고, 스냅샷 없는 종목에서 누르면
        show_fundamental_detail()의 FUNDAMENTAL_DETAILS[symbol]이 KeyError를 냈다.
        """
        for symbol in set(PORTFOLIO) - set(FUNDAMENTAL_DETAILS):
            self.assertFalse(has_fundamental_detail(symbol), symbol)
            self.assertEqual("", fundamental_badges_html(symbol), symbol)

    def test_symbol_with_snapshot_is_allowed_through(self):
        for symbol in FUNDAMENTAL_DETAILS:
            self.assertTrue(has_fundamental_detail(symbol), symbol)

    def test_badges_are_explicitly_excluded_from_score(self):
        rendered = fundamental_badges_html("IREN")
        self.assertIn("SCORE 미반영", rendered)
        self.assertIn("$128.8M", rendered)
        self.assertEqual("", fundamental_badges_html("UNKNOWN"))


if __name__ == "__main__":
    unittest.main()
