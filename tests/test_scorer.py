import math
import unittest

import pandas as pd

from scorer import (
    _clamp,
    data_confidence,
    marks_temperature_score,
    opportunity_score,
    price_score,
    shadow_diagnosis,
    technical_score,
    to_grade,
    trend_health_score,
)


VALID_MA = {"dev200": 5.0, "golden_cross": True}


class TechnicalScoreTest(unittest.TestCase):
    def test_valid_inputs_produce_a_score(self):
        score, detail = technical_score(50.0, 40.0, 45.0, VALID_MA)

        self.assertIsNotNone(score)
        self.assertTrue(math.isfinite(score))
        self.assertNotIn("N/A", detail)

    def test_non_finite_rsi_is_not_scored(self):
        score, detail = technical_score(float("nan"), 40.0, 45.0, VALID_MA)

        self.assertIsNone(score)
        self.assertEqual("N/A: RSI", detail)

    def test_non_finite_stochastic_is_not_scored(self):
        score, detail = technical_score(50.0, float("inf"), 45.0, VALID_MA)

        self.assertIsNone(score)
        self.assertEqual("N/A: Stoch", detail)

    def test_non_finite_200ma_is_not_scored(self):
        score, detail = technical_score(
            50.0,
            40.0,
            45.0,
            {"dev200": float("nan"), "golden_cross": False},
        )

        self.assertIsNone(score)
        self.assertEqual("N/A: 200MA", detail)

    def test_all_unavailable_inputs_are_reported(self):
        score, detail = technical_score(
            float("nan"),
            float("nan"),
            float("nan"),
            {"dev200": float("nan"), "golden_cross": False},
        )

        self.assertIsNone(score)
        self.assertEqual("N/A: RSI, Stoch, 200MA", detail)

    def test_missing_technical_propagates_to_final_grade(self):
        technical, _ = technical_score(float("nan"), 40.0, 45.0, VALID_MA)

        self.assertIsNone(price_score(60.0, technical, 50.0))
        self.assertEqual(("N/A", "N/A"), to_grade(None))


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

    def test_all_components_use_fixed_weights(self):
        score, label, _, components = marks_temperature_score(
            self.marks_data(),
            vix=20.0,
            vix_history=self.history,
            fear_greed=60.0,
        )

        self.assertAlmostEqual(77.0, score)
        self.assertEqual("🔥 Warm", label)
        self.assertAlmostEqual(1.0, sum(c["weight"] for c in components.values()))

    def test_missing_components_return_na_without_reweighting(self):
        score, label, detail, components = marks_temperature_score(
            {},
            vix=20.0,
            vix_history=self.history,
            fear_greed=60.0,
        )

        self.assertIsNone(score)
        self.assertEqual("N/A", label)
        self.assertEqual("데이터 가용률: 30% · 누락: HY Spread, NFCI, SLOOS", detail)
        self.assertEqual(0.15, components["vix"]["weight"])
        self.assertEqual(0.15, components["fear_greed"]["weight"])


class ShadowScoreTest(unittest.TestCase):
    def test_opportunity_formula(self):
        score, _, breakdown = opportunity_score(75.0, "fPE=20.0", 35.0, 30.0, 30.0)

        self.assertAlmostEqual(76.5, score)
        self.assertEqual(87.5, breakdown["rsi_entry"])
        self.assertEqual(70.0, breakdown["stoch_entry"])

    def test_opportunity_missing_input_returns_na_without_reweighting(self):
        score, detail, breakdown = opportunity_score(50.0, "N/A", 35.0, 30.0, 30.0)

        self.assertIsNone(score)
        self.assertEqual("N/A: Valuation", detail)
        self.assertEqual({}, breakdown)

    def test_trend_health_formula(self):
        score, _, breakdown = trend_health_score({
            "dev200": -8.0,
            "ma200_slope": 1.5,
            "ma_spread": -2.0,
            "relative_strength": -5.0,
        })

        self.assertAlmostEqual(44.0, score)
        self.assertEqual(30.0, breakdown["price_position"])

    def test_trend_missing_input_returns_na_without_reweighting(self):
        score, detail, breakdown = trend_health_score({
            "dev200": -8.0,
            "ma200_slope": math.nan,
            "ma_spread": -2.0,
            "relative_strength": -5.0,
        })

        self.assertIsNone(score)
        self.assertEqual("N/A: 200MA Slope", detail)
        self.assertEqual({}, breakdown)

    def test_confidence_is_data_quality_not_grade_input(self):
        metrics = {
            "dev200": 1.0,
            "ma200_slope": 1.0,
            "ma_spread": 1.0,
            "relative_strength": 1.0,
            "history_points": 300,
            "benchmark_points": 300,
            "price_fresh": True,
            "benchmark_fresh": True,
        }

        score, label, detail = data_confidence(70.0, "fPE=20.0", 50.0, 40.0, 45.0, metrics)

        self.assertEqual(100.0, score)
        self.assertEqual("HIGH", label)
        self.assertEqual("10/10 valid", detail)

    def test_shadow_quadrants(self):
        self.assertIn("가격 매력", shadow_diagnosis(80.0, 80.0))
        self.assertIn("추세 확인", shadow_diagnosis(80.0, 40.0))
        self.assertIn("가격 매력 제한", shadow_diagnosis(40.0, 80.0))
        self.assertIn("모두 약함", shadow_diagnosis(40.0, 40.0))


if __name__ == "__main__":
    unittest.main()
