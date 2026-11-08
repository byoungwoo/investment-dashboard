import unittest
from datetime import date, datetime

from fetcher import parse_earnings_calendar, parse_wsj_sp500_valuation


WSJ_FIXTURE = """
<table>
  <thead><tr><th></th><th>9/11/26†</th><th>Year ago†</th><th>Estimate^</th></tr></thead>
  <tbody>
    <tr><td>S&amp;P 500 Index</td><td>23.22</td><td>25.10</td><td>20.25</td><td>1.08</td><td>1.18</td></tr>
  </tbody>
</table>
"""


class WsjValuationParserTest(unittest.TestCase):
    def test_parses_sp500_row(self):
        result = parse_wsj_sp500_valuation(WSJ_FIXTURE)

        self.assertEqual(23.22, result["ttm_pe"])
        self.assertEqual(25.10, result["year_ago_pe"])
        self.assertEqual(20.25, result["forward_pe"])
        self.assertEqual(1.08, result["dividend_yield"])
        self.assertEqual("9/11/26", result["as_of"])
        self.assertAlmostEqual(100 / 23.22, result["earnings_yield"])

    def test_missing_row_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "row not found"):
            parse_wsj_sp500_valuation("<html></html>")


class EarningsCalendarTest(unittest.TestCase):
    TODAY = date(2026, 11, 8)

    def test_picks_the_next_date_not_the_first(self):
        calendar = {"Earnings Date": [date(2026, 8, 7), date(2026, 11, 13), date(2027, 2, 12)]}
        self.assertEqual(date(2026, 11, 13), parse_earnings_calendar(calendar, self.TODAY))

    def test_today_counts_as_upcoming(self):
        calendar = {"Earnings Date": [self.TODAY]}
        self.assertEqual(self.TODAY, parse_earnings_calendar(calendar, self.TODAY))

    def test_only_past_dates_yield_nothing(self):
        calendar = {"Earnings Date": [date(2026, 8, 7)]}
        self.assertIsNone(parse_earnings_calendar(calendar, self.TODAY))

    def test_accepts_datetime_and_iso_string(self):
        for raw in (datetime(2026, 11, 13, 21, 0), "2026-11-13", "2026-11-13 21:00:00"):
            self.assertEqual(
                date(2026, 11, 13), parse_earnings_calendar({"Earnings Date": raw}, self.TODAY), raw
            )

    def test_unknown_shape_fails_closed(self):
        """스키마가 바뀌면 추측하지 말고 None — 틀린 발표일이 더 나쁘다."""
        for calendar in (None, {}, [], "2026-11-13", {"Earnings Date": None},
                         {"Earnings Date": ["언젠가"]}):
            self.assertIsNone(parse_earnings_calendar(calendar, self.TODAY), repr(calendar))


if __name__ == "__main__":
    unittest.main()
