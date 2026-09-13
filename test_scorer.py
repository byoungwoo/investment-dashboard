import math
import unittest

from scorer import _clamp, price_score, technical_score, to_grade


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


if __name__ == "__main__":
    unittest.main()
