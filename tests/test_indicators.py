import math
import unittest

import pandas as pd

from indicators import trend_metrics


class TrendMetricsTest(unittest.TestCase):
    def test_builds_finite_metrics_from_two_year_history(self):
        index = pd.date_range(end="2026-09-11", periods=300, freq="B")
        closes = pd.Series([100 + i * 0.2 for i in range(300)], index=index)
        benchmark = pd.Series([100 + i * 0.1 for i in range(300)], index=index)

        result = trend_metrics(closes, benchmark, now="2026-09-13")

        for key in ("dev200", "ma200_slope", "ma_spread", "relative_strength"):
            self.assertTrue(math.isfinite(result[key]), key)
        self.assertEqual(300, result["history_points"])
        self.assertEqual("2026-09-11", result["latest_date"])
        self.assertTrue(result["price_fresh"])
        self.assertTrue(result["benchmark_fresh"])


if __name__ == "__main__":
    unittest.main()
