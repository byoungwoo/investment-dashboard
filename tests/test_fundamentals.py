import unittest

from fundamentals import FUNDAMENTAL_DETAILS, fundamental_badges_html


class FundamentalDetailsTest(unittest.TestCase):
    def test_every_portfolio_symbol_has_complete_display_data(self):
        self.assertEqual({"AVGO", "ABB", "VRT", "IREN"}, set(FUNDAMENTAL_DETAILS))
        for symbol, detail in FUNDAMENTAL_DETAILS.items():
            self.assertEqual(3, len(detail["badges"]), symbol)
            self.assertGreaterEqual(len(detail["flow"]), 3, symbol)
            self.assertGreaterEqual(len(detail["financials"]), 3, symbol)
            self.assertTrue(detail["source_url"].startswith("https://"), symbol)

    def test_badges_are_explicitly_excluded_from_score(self):
        rendered = fundamental_badges_html("IREN")
        self.assertIn("SCORE 미반영", rendered)
        self.assertIn("$128.8M", rendered)
        self.assertEqual("", fundamental_badges_html("UNKNOWN"))


if __name__ == "__main__":
    unittest.main()
