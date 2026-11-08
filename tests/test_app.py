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
            # IREN은 적자라 Yahoo가 음수 forwardPE를 준다 — 밸류에이션 측정 불가 경로를
            # 실제 값으로 태운다. enterpriseValue는 EV/ARR 배수를 그리게 하려고 넣는다.
            "fetcher.fetch_info": lambda ticker: (
                {"forwardPE": -5.49, "pegRatio": 3.11, "enterpriseValue": 15.9e9}
                if ticker == "IREN"
                else {"forwardPE": 25.0, "pegRatio": 1.5}
            ),
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

            detail_buttons = [button for button in app.button if button.label == "🔍 Fundamental Detail"]
            self.assertEqual(4, len(detail_buttons))

            # IREN은 축별로 방향이 갈리는 종목이다 (수요 강화 / 일정 지연 / 조달 고위험).
            # Thesis Status 한 줄만 뜨고 세부 평가가 빠지면 패널이 상태를 숨긴 셈이 된다.
            app.button(key="fundamental-detail-IREN").click().run(timeout=30)
            self.assertEqual([], list(app.exception))
            iren_panel = " ".join(item.value for item in app.markdown)
            self.assertIn("IREN · Fundamental Detail", iren_panel)
            self.assertIn("실행 검증 중", iren_panel)
            self.assertIn("자금조달 · 희석", iren_panel)
            self.assertIn("고위험", iren_panel)

            # 측정 못한 50은 측정해서 나온 50과 화면에서 구별돼야 한다.
            # 적자로 밸류에이션이 비는 종목은 IREN 하나뿐이므로 정확히 한 번 나온다.
            self.assertEqual(1, iren_panel.count("(미측정)"))
            self.assertIn("Val 50 (미측정)", iren_panel)

            # EV/ARR은 공시 스냅샷이 아니라 라이브 시장값이다. 두 배수의 간격이
            # 미가동 ARR이고, 그게 이 종목의 핵심 위험이다.
            self.assertIn("EV / ARR · 라이브 시장값", iren_panel)
            self.assertIn("15.9x", iren_panel)
            self.assertIn("4.0x", iren_panel)

            app.button(key="fundamental-detail-AVGO").click().run(timeout=30)

        self.assertEqual([], list(app.exception))
        self.assertGreaterEqual(len(app.metric), 17)
        self.assertEqual(1, len(app.selectbox))
        self.assertTrue(any("AVGO · Fundamental Detail" in item.value for item in app.markdown))


if __name__ == "__main__":
    unittest.main()
