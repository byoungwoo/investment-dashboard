import unittest
from unittest.mock import patch

import pandas as pd

from backtest import BuyRules, replay_signals, simulate_buys


def prices(count=230):
    index = pd.bdate_range('2025-01-01', periods=count)
    close = pd.Series([100 + i * .2 + (i % 5) * .1 for i in range(count)], index=index)
    return pd.DataFrame({'Open': close, 'High': close + 1, 'Low': close - 1, 'Close': close})


class BacktestTests(unittest.TestCase):
    def test_thresholds_are_inclusive_but_improvement_is_strict(self):
        bars = prices(4)
        values = pd.DataFrame({'forwardPE': 10.}, index=bars.index)
        with patch('backtest.trend_health_score', side_effect=[
            (59., '', {}), (60., '', {}), (60., '', {}), (61., '', {})
        ]), patch('backtest.opportunity_score', side_effect=[
            (70., '', {}), (70., '', {}), (70., '', {}), (69.9, '', {})
        ]):
            signals = replay_signals(bars, bars, values, BuyRules(improvement_sessions=1))
        self.assertEqual([False, True, False, False], signals['eligible'].tolist())

    def test_absent_valuation_never_triggers_buys(self):
        bars = prices()
        signals = replay_signals(bars, bars)
        self.assertTrue(signals['opportunity'].isna().all())
        self.assertFalse(signals['eligible'].any())
        self.assertTrue(pd.notna(signals['trend'].iloc[-1]))

    def test_future_data_cannot_change_past_signals(self):
        bars = prices()
        values = pd.DataFrame({'forwardPE': 15.0}, index=bars.index)
        full = replay_signals(bars, bars, values)
        early = replay_signals(bars.iloc[:-5], bars, values)
        pd.testing.assert_frame_equal(full.iloc[:-5], early)

    def test_valuation_is_not_backfilled_or_forward_filled(self):
        bars = prices()
        values = pd.DataFrame({'forwardPE': [10.]}, index=bars.index[-2:-1])
        signals = replay_signals(bars, bars, values)
        self.assertEqual(1, signals['opportunity'].notna().sum())
        self.assertTrue(pd.isna(signals['opportunity'].iloc[-1]))

    def test_next_open_spacing_and_cash_limit(self):
        bars = prices(8)
        bars.loc[:, 'Open'] = 100.
        bars.loc[:, 'Close'] = 110.
        signals = pd.DataFrame({'eligible': True, 'opportunity': 80.}, index=bars.index)
        result = simulate_buys(bars, signals, BuyRules(spacing_sessions=2, cost_bps=0), initial_cash=300)
        self.assertEqual(list(bars.index[[1, 3, 5]]), list(result['trades']['date']))
        self.assertEqual(list(bars.index[[0, 2, 4]]), list(result['trades']['signal_date']))
        # 3 tranches of 100 buy 3 shares at 100; final value 3*110=330.
        self.assertAlmostEqual(10., result['return_pct'])
        self.assertAlmostEqual(0., result['cash_remaining'])
        self.assertEqual(300., result['equity'].iloc[0])

    def test_fees_and_initial_peak_drawdown(self):
        bars = prices(3)
        bars.loc[:, 'Open'] = 100.
        bars.loc[:, 'Close'] = 90.
        signals = pd.DataFrame({'eligible': True, 'opportunity': 80.}, index=bars.index)
        result = simulate_buys(bars, signals, BuyRules(tranches=1, cost_bps=100), initial_cash=101)
        # 101 cash buys one 100 share plus 1 fee; ending equity 90.
        self.assertAlmostEqual(1., result['trades']['fee'].iloc[0])
        self.assertAlmostEqual((90 / 101 - 1) * 100, result['max_drawdown_pct'])

    def test_last_close_signal_is_not_executed(self):
        bars = prices(3)
        signals = pd.DataFrame({'eligible': [False, False, True], 'opportunity': 80.}, index=bars.index)
        result = simulate_buys(bars, signals)
        self.assertTrue(result['trades'].empty)
        self.assertEqual(0., result['return_pct'])

    def test_invalid_rules_and_dates_rejected(self):
        with self.assertRaises(ValueError):
            BuyRules(tranches=0)
        with self.assertRaises(ValueError):
            BuyRules(cost_bps=float('nan'))
        bars = prices(3)
        with self.assertRaises(ValueError):
            replay_signals(bars.iloc[::-1], bars)


if __name__ == '__main__':
    unittest.main()
