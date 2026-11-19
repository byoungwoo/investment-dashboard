import math
import unittest

import pandas as pd

from scorer import (
    _clamp,
    marks_temperature_score,
    price_score,
    technical_score,
    to_grade,
    valuation_score,
)


class ValuationScoreTest(unittest.TestCase):
    """Price Score의 50%인데 직접 회귀 테스트가 없던 자리."""

    def test_forward_pe_only(self):
        # fPE=25 → 110 - 25*1.8 = 110 - 45 = 65.0
        score, detail = valuation_score({"forwardPE": 25.0})

        self.assertAlmostEqual(score, 65.0)
        self.assertEqual(detail, "fPE=25.0")

    def test_peg_blends_in(self):
        # pe   = 110 - 20*1.8 = 74.0
        # peg  = 95 - 1.5*25  = 57.5
        # 합성 = 74.0*0.55 + 57.5*0.45 = 40.7 + 25.875 = 66.575
        score, detail = valuation_score({"forwardPE": 20.0, "pegRatio": 1.5})

        self.assertAlmostEqual(score, 66.575)
        self.assertEqual(detail, "fPE=20.0 PEG=1.50")

    def test_expensive_branch_is_continuous_at_fifty(self):
        # fPE=50 은 두 번째 식: 20 - (50-50)*0.3 = 20.0
        # fPE=60 →            20 - 10*0.3      = 17.0
        self.assertAlmostEqual(valuation_score({"forwardPE": 50.0})[0], 20.0)
        self.assertAlmostEqual(valuation_score({"forwardPE": 60.0})[0], 17.0)

    def test_negative_forward_pe_is_not_measured(self):
        # IREN처럼 적자기업은 forwardPE가 음수 → 50점 + N/A 로 드러낸다
        score, detail = valuation_score({"forwardPE": -12.0})

        self.assertEqual(score, 50.0)
        self.assertEqual(detail, "N/A")

    def test_nan_forward_pe_returns_na_instead_of_raising(self):
        # NaN은 truthy고 `nan <= 0` 은 False라 예전엔 가드를 통과해
        # _clamp가 ValueError를 던졌다. yfinance info는 NaN을 흔히 돌려준다.
        score, detail = valuation_score({"forwardPE": math.nan})

        self.assertEqual(score, 50.0)
        self.assertEqual(detail, "N/A")

    def test_missing_forward_pe_returns_na(self):
        self.assertEqual(valuation_score({})[0], 50.0)
        self.assertEqual(valuation_score({"forwardPE": None})[1], "N/A")

    def test_nan_peg_is_ignored_not_blended(self):
        # PEG가 NaN이면 Forward PE 단독 점수와 같아야 한다 (65.0)
        score, detail = valuation_score({"forwardPE": 25.0, "pegRatio": math.nan})

        self.assertAlmostEqual(score, 65.0)
        self.assertEqual(detail, "fPE=25.0")


class TechnicalScoreTest(unittest.TestCase):
    def setUp(self):
        self.ma = {"dev200": 10.0, "golden_cross": False}

    def test_normal_inputs_keep_existing_score(self):
        score, detail = technical_score(50.0, 40.0, 50.0, self.ma)

        self.assertAlmostEqual(score, 56.0)
        self.assertEqual(detail, "RSI=50 Stoch=45 vs200=+10%")

    def test_missing_rsi_returns_na(self):
        score, detail = technical_score(math.nan, 40.0, 50.0, self.ma)

        self.assertIsNone(score)
        self.assertEqual(detail, "N/A: RSI")

    def test_missing_stochastic_k_returns_na(self):
        score, detail = technical_score(50.0, math.nan, 50.0, self.ma)

        self.assertIsNone(score)
        self.assertEqual(detail, "N/A: Stoch")

    def test_missing_stochastic_d_returns_na(self):
        score, detail = technical_score(50.0, 40.0, math.nan, self.ma)

        self.assertIsNone(score)
        self.assertEqual(detail, "N/A: Stoch")

    def test_missing_200ma_returns_na(self):
        score, detail = technical_score(
            50.0, 40.0, 50.0, {"dev200": math.nan, "golden_cross": False}
        )

        self.assertIsNone(score)
        self.assertEqual(detail, "N/A: 200MA")

    def test_all_missing_items_are_reported_in_display_order(self):
        score, detail = technical_score(
            math.nan,
            math.nan,
            math.nan,
            {"dev200": math.nan, "golden_cross": False},
        )

        self.assertIsNone(score)
        self.assertEqual(detail, "N/A: RSI, Stoch, 200MA")

    def test_infinite_technical_inputs_return_na(self):
        cases = [
            (math.inf, 40.0, 50.0, self.ma, "N/A: RSI"),
            (50.0, -math.inf, 50.0, self.ma, "N/A: Stoch"),
            (
                50.0,
                40.0,
                50.0,
                {"dev200": math.inf, "golden_cross": False},
                "N/A: 200MA",
            ),
        ]

        for rsi_val, stoch_k, stoch_d, ma, expected_detail in cases:
            with self.subTest(expected_detail=expected_detail):
                score, detail = technical_score(rsi_val, stoch_k, stoch_d, ma)
                self.assertIsNone(score)
                self.assertEqual(detail, expected_detail)

    def test_missing_technical_score_propagates_to_final_result(self):
        technical, _ = technical_score(math.nan, 40.0, 50.0, self.ma)

        final = price_score(60.0, technical, 50.0)

        self.assertIsNone(final)
        self.assertEqual(to_grade(final), ("N/A", "N/A"))


class ClampTest(unittest.TestCase):
    def test_non_finite_values_are_rejected(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    _clamp(value)


class MarksTemperatureScoreTest(unittest.TestCase):
    def setUp(self):
        self.history = pd.Series([10.0, 30.0, 40.0, 50.0, 60.0])

    def marks_data(self):
        return {
            key: {
                "value": 20.0,
                "date": "2026-09-01",
                "history": self.history.copy(),
            }
            for key in ("hy_spread", "nfci", "sloos")
        }

    def test_all_components_keep_existing_fixed_weight_score(self):
        score, label, detail, components = marks_temperature_score(
            self.marks_data(),
            vix=20.0,
            vix_history=self.history,
            fear_greed=60.0,
        )

        self.assertAlmostEqual(score, 77.0)
        self.assertEqual(label, "🔥 Warm")
        self.assertEqual(
            detail,
            "HY Spread=80 · NFCI=80 · SLOOS=80 · VIX=80 · Fear & Greed=60",
        )
        self.assertAlmostEqual(sum(c["weight"] for c in components.values()), 1.0)

    def test_any_missing_required_component_returns_na(self):
        cases = [
            ("hy_spread", "HY Spread", 70),
            ("nfci", "NFCI", 75),
            ("sloos", "SLOOS", 85),
            ("vix", "VIX", 85),
            ("fear_greed", "Fear & Greed", 85),
        ]

        for missing_key, missing_label, expected_coverage in cases:
            with self.subTest(missing=missing_label):
                marks_data = self.marks_data()
                vix = 20.0
                fear_greed = 60.0
                if missing_key in marks_data:
                    marks_data[missing_key]["value"] = math.nan
                elif missing_key == "vix":
                    vix = math.inf
                else:
                    fear_greed = None

                score, label, detail, _ = marks_temperature_score(
                    marks_data,
                    vix=vix,
                    vix_history=self.history,
                    fear_greed=fear_greed,
                )

                self.assertIsNone(score)
                self.assertEqual(label, "N/A")
                self.assertEqual(
                    detail,
                    f"데이터 가용률: {expected_coverage}% · 누락: {missing_label}",
                )

    def test_partial_30_percent_data_is_not_reweighted(self):
        marks_data = {
            key: {
                "value": None,
                "date": None,
                "history": pd.Series(dtype=float),
            }
            for key in ("hy_spread", "nfci", "sloos")
        }

        score, label, detail, components = marks_temperature_score(
            marks_data,
            vix=20.0,
            vix_history=self.history,
            fear_greed=60.0,
        )

        self.assertIsNone(score)
        self.assertEqual(label, "N/A")
        self.assertEqual(
            detail,
            "데이터 가용률: 30% · 누락: HY Spread, NFCI, SLOOS",
        )
        self.assertEqual(components["vix"]["heat"], 80.0)
        self.assertEqual(components["fear_greed"]["heat"], 60.0)
        self.assertEqual(components["vix"]["weight"], 0.15)
        self.assertEqual(components["fear_greed"]["weight"], 0.15)


if __name__ == "__main__":
    unittest.main()
