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

    def test_relative_strength_aligns_on_dates_not_bar_counts(self):
        """거래일 수가 달라도 같은 기간끼리 비교해야 한다.

        종목과 벤치마크가 **같은 날짜에 같은 값**이면, 벤치마크에 휴장일이
        더 있더라도 상대강도는 정확히 0이어야 한다.
        각자 63칸씩 뒤로 세던 시절엔 서로 다른 기간을 빼서 0이 나오지 않았다.
        """
        index = pd.date_range(end="2026-09-11", periods=300, freq="B")
        # 값 = 날짜의 위치. 따라서 두 계열은 같은 날짜에 같은 값을 갖는다.
        closes = pd.Series([100.0 + i for i in range(300)], index=index)
        # 벤치마크만 마지막 63거래일 안쪽에서 10일을 쉰다 (240~249번 자리)
        holidays = index[240:250]
        benchmark = closes.drop(holidays)
        self.assertEqual(290, len(benchmark))

        result = trend_metrics(closes, benchmark, now="2026-09-13")

        # 창: index[-64] = 236번 자리(값 336) ~ index[-1] = 299번 자리(값 399)
        # 수익률 = (399 / 336 - 1) * 100 = 18.75%  — 양쪽 모두
        self.assertAlmostEqual(18.75, result["stock_return_63d"])
        self.assertAlmostEqual(18.75, result["benchmark_return_63d"])
        self.assertAlmostEqual(0.0, result["relative_strength"])
        # 벤치마크 바 수는 그대로 보고한다 (data_confidence의 "Benchmark 64+"용)
        self.assertEqual(290, result["benchmark_points"])

    def test_benchmark_that_misses_the_window_start_is_not_scored(self):
        """창 시작일을 못 덮는 벤치마크로 숫자를 지어내지 않는다."""
        index = pd.date_range(end="2026-09-11", periods=30, freq="B")
        closes = pd.Series([100.0 + i for i in range(30)], index=index)
        # 창 시작일(index[-6]) 이후에만 존재하지만 바 수는 충분한 벤치마크
        late = pd.date_range(start=index[-5], periods=10, freq="D")
        benchmark = pd.Series([200.0 + i for i in range(10)], index=late)

        result = trend_metrics(closes, benchmark, relative_lookback=5, now="2026-09-13")

        self.assertTrue(math.isfinite(result["stock_return_63d"]))
        self.assertTrue(math.isnan(result["benchmark_return_63d"]))
        self.assertTrue(math.isnan(result["relative_strength"]))


if __name__ == "__main__":
    unittest.main()
