import unittest

from fetcher import parse_wsj_sp500_valuation


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


if __name__ == "__main__":
    unittest.main()
