"""Macro Score v2.3 공식을 못 박는 테스트.

v2.3 공식 (문서화된 정의):
    Macro Score      = Rate Level × 80% + Fed Policy Signal × 20%
                       (VIX > 25 stress 국면: 70% / 30%)
    Rate Level       = 10Y 75% + 30Y 25%
    Fed Policy Signal= FFR vs r* 35% + 2Y Δ(3개월) 25% + TIPS 10Y 40%

기대값은 전부 손계산해서 적는다. 코드를 다시 호출해 비교하면
공식이 바뀌어도 양쪽이 같이 바뀌어 아무것도 못 잡는다.
"""

import math
import unittest

from config import NEUTRAL_RATE
from scorer import _fed_policy_signal, _rate_level_score, macro_score


class RateLevelWeightTest(unittest.TestCase):
    """Rate Level = 10Y 75% + 30Y 25%"""

    def test_ten_year_carries_three_quarters_of_the_weight(self):
        # t10_s = 105 - 4.0*14 = 49.0
        # t30_s = 105 - 4.0*13 = 53.0
        # 49.0*0.75 + 53.0*0.25 = 50.0   (가중치가 뒤바뀌면 52.0)
        score, breakdown = _rate_level_score(4.0, 4.0)

        self.assertAlmostEqual(49.0, breakdown["t10_s"])
        self.assertAlmostEqual(53.0, breakdown["t30_s"])
        self.assertAlmostEqual(50.0, score)

    def test_score_is_capped_at_100(self):
        # 금리 0% → 105점이 나오지만 상한 100
        score, _ = _rate_level_score(0.0, 0.0)
        self.assertEqual(100, score)


class FedPolicySignalWeightTest(unittest.TestCase):
    """Fed Policy Signal = FFR 35% + 2Y Δ 25% + TIPS 40%"""

    def test_three_components_use_35_25_40(self):
        # gap     = 3.0 - 2.5 = 0.5  → ffr_s   = 60 - 0.5*15  = 52.5
        # delta_2y= 0.2             → delta_s = 60 - 0.2*45  = 51.0
        # tips    = 2.0             → tips_s  = 75 - 2.0*20  = 35.0
        # 52.5*0.35 + 51.0*0.25 + 35.0*0.40 = 45.125
        score, breakdown = _fed_policy_signal(3.0, 2.5, 0.2, 2.0)

        self.assertAlmostEqual(52.5, breakdown["ffr_s"])
        self.assertAlmostEqual(51.0, breakdown["delta_s"])
        self.assertAlmostEqual(35.0, breakdown["tips_s"])
        self.assertAlmostEqual(0.5, breakdown["gap"])
        self.assertAlmostEqual(45.125, score)

    def test_tips_carries_more_weight_than_the_policy_rate(self):
        """TIPS 40% > FFR 35% — v2.3이 TIPS를 Fed 신호의 최대 축으로 둔 설계."""
        only_ffr, _ = _fed_policy_signal(0.0, 0.0, 10.0, 10.0)   # ffr_s만 높게
        only_tips, _ = _fed_policy_signal(10.0, 0.0, 10.0, 0.0)  # tips_s만 높게
        self.assertGreater(only_tips, only_ffr)


class MacroBlendTest(unittest.TestCase):
    """Macro = Rate × 80% + Fed × 20% (stress 시 70% / 30%)"""

    MACRO = {
        "t10y": 4.0, "t30y": 4.0,
        "ffr": 3.0, "neutral_rate": 2.5,
        "delta_2y": 0.2, "tips": 2.0,
    }
    RATE_S = 50.0     # RateLevelWeightTest 참조
    FED_S = 45.125    # FedPolicySignalWeightTest 참조

    def test_calm_regime_blends_80_20(self):
        # 50.0*0.80 + 45.125*0.20 = 49.025
        score, _, breakdown = macro_score(self.MACRO, vix=20.0)

        self.assertFalse(breakdown["stress_regime"])
        self.assertAlmostEqual(0.80, breakdown["rate_weight"])
        self.assertAlmostEqual(0.20, breakdown["fed_weight"])
        self.assertAlmostEqual(49.025, score)

    def test_stress_regime_blends_70_30(self):
        # 50.0*0.70 + 45.125*0.30 = 48.5375
        score, _, breakdown = macro_score(self.MACRO, vix=30.0)

        self.assertTrue(breakdown["stress_regime"])
        self.assertAlmostEqual(0.70, breakdown["rate_weight"])
        self.assertAlmostEqual(0.30, breakdown["fed_weight"])
        self.assertAlmostEqual(48.5375, score)

    def test_vix_exactly_25_is_not_yet_stress(self):
        """공식은 'VIX > 25' — 경계값 25.0은 평시다."""
        _, _, at = macro_score(self.MACRO, vix=25.0)
        _, _, above = macro_score(self.MACRO, vix=25.01)

        self.assertFalse(at["stress_regime"])
        self.assertTrue(above["stress_regime"])

    def test_neutral_rate_falls_back_to_config(self):
        """r*을 안 주면 config.NEUTRAL_RATE를 쓴다 (FOMC SEP 갱신 지점)."""
        without = dict(self.MACRO)
        del without["neutral_rate"]

        _, _, breakdown = macro_score(without, vix=20.0)
        self.assertAlmostEqual(NEUTRAL_RATE, breakdown["inputs"]["neutral_rate"])

    def test_non_finite_input_raises_instead_of_scoring(self):
        """결측을 조용히 점수화하지 않는다 — NaN은 터뜨린다."""
        for field in ("t10y", "t30y", "ffr", "delta_2y", "tips"):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    macro_score({**self.MACRO, field: math.nan}, vix=20.0)

    def test_score_never_leaves_0_100(self):
        for macro in (
            {"t10y": 0.0, "t30y": 0.0, "ffr": 0.0, "neutral_rate": 2.5, "delta_2y": -5.0, "tips": -2.0},
            {"t10y": 20.0, "t30y": 20.0, "ffr": 20.0, "neutral_rate": 2.5, "delta_2y": 5.0, "tips": 10.0},
        ):
            with self.subTest(macro=macro):
                score, _, _ = macro_score(macro, vix=20.0)
                self.assertGreaterEqual(score, 0)
                self.assertLessEqual(score, 100)


class ZeroIsRealDataTest(unittest.TestCase):
    """0.00%는 결측이 아니다.

    `macro.get("ffr") or 5.25` 는 0.0을 falsy로 보고 기본값으로 갈아끼운다.
    정책금리 0.00%는 2008~2015, 2020~2022에 실재했고,
    TIPS 10Y 실질금리도 0 근방과 마이너스를 지났다.
    """

    BASE = {"t10y": 4.0, "t30y": 4.0, "neutral_rate": 2.5, "delta_2y": 0.0, "tips": 2.0}

    def test_zero_policy_rate_is_not_replaced_by_a_default(self):
        _, _, breakdown = macro_score({**self.BASE, "ffr": 0.0}, vix=20.0)

        self.assertAlmostEqual(0.0, breakdown["inputs"]["ffr"])
        # gap = 0.0 - 2.5 = -2.5 → ffr_s = 60 + 37.5 = 97.5
        self.assertAlmostEqual(97.5, breakdown["fed_detail"]["ffr_s"])

    def test_zero_tips_yield_is_not_replaced_by_a_default(self):
        _, _, breakdown = macro_score({**self.BASE, "tips": 0.0}, vix=20.0)

        self.assertAlmostEqual(0.0, breakdown["inputs"]["tips"])
        # tips_s = 75 - 0.0*20 = 75.0
        self.assertAlmostEqual(75.0, breakdown["fed_detail"]["tips_s"])

    def test_negative_rates_already_survive(self):
        """음수는 truthy라 지금도 정상 통과한다 — 대조군."""
        _, _, breakdown = macro_score({**self.BASE, "tips": -0.5}, vix=20.0)
        self.assertAlmostEqual(-0.5, breakdown["inputs"]["tips"])


if __name__ == "__main__":
    unittest.main()
