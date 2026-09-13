import unittest
from contextlib import ExitStack
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest


def price_history():
    index = pd.date_range(end="2026-09-11", periods=501, freq="B")
    close = pd.Series([100 + i * 0.1 for i in range(len(index))], index=index)
    return pd.DataFrame({
        "Open": close - 0.2,
        "High": close + 1.0,
        "Low": close - 1.0,
        "Close": close,
    })


def marks_data():
    history = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    return {
        key: {"value": 20.0, "date": "2026-09-11", "history": history.copy()}
        for key in ("hy_spread", "nfci", "sloos")
    }


class DashboardSmokeTest(unittest.TestCase):
    def test_dashboard_renders_with_shadow_sections(self):
        fake_history = price_history()
        replacements = {
            "fetcher.fetch_history": lambda ticker, period="2y": fake_history.copy(),
            "fetcher.fetch_info": lambda ticker: {"forwardPE": 25.0, "pegRatio": 1.5},
            "fetcher.fetch_macro": lambda: {
                "t10y": 4.3,
                "t30y": 4.6,
                "t10y2y": 0.4,
                "ffr": 5.25,
                "neutral_rate": 2.5,
                "delta_2y": 0.0,
                "tips": 1.5,
                "_source": "FRED",
            },
            "fetcher.fetch_vix": lambda: 20.0,
            "fetcher.fetch_vix_history": lambda: pd.Series([15.0, 20.0, 25.0]),
            "fetcher.fetch_fear_greed": lambda: {"score": 60.0, "rating": "greed"},
            "fetcher.fetch_marks_temperature_data": marks_data,
            "fetcher.fetch_sp500_valuation": lambda: {
                "ttm_pe": 23.22,
                "year_ago_pe": 25.10,
                "forward_pe": 20.25,
                "dividend_yield": 1.08,
                "year_ago_dividend_yield": 1.18,
                "earnings_yield": 100 / 23.22,
                "as_of": "9/11/26",
                "source": "fixture",
                "url": "https://www.wsj.com/market-data/stocks/peyields",
            },
        }

        with ExitStack() as stack:
            for target, replacement in replacements.items():
                stack.enter_context(patch(target, replacement))
            app = AppTest.from_file("app.py", default_timeout=30).run(timeout=30)

        self.assertEqual([], list(app.exception))
        self.assertGreaterEqual(len(app.metric), 17)
        self.assertEqual(1, len(app.selectbox))


if __name__ == "__main__":
    unittest.main()
