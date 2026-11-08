"""Offline, point-in-time signal replay and a configurable buy-only experiment.

Inputs must contain only information available at each historical close.
No fetching or substitution of today's valuation is performed here.
"""
from dataclasses import dataclass
import math

import pandas as pd

from indicators import rsi, slow_stochastic, trend_metrics
from scorer import opportunity_score, trend_health_score, valuation_score


@dataclass(frozen=True)
class BuyRules:
    opportunity_min: float = 70.0
    trend_min: float = 60.0
    improvement_sessions: int = 5
    tranches: int = 3
    spacing_sessions: int = 5
    cost_bps: float = 10.0

    def __post_init__(self):
        for name in ('opportunity_min', 'trend_min'):
            value = getattr(self, name)
            if not math.isfinite(value) or not 0 <= value <= 100:
                raise ValueError(name + ' must be in [0, 100]')
        for name in ('improvement_sessions', 'tranches', 'spacing_sessions'):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(name + ' must be a positive integer')
        if not math.isfinite(self.cost_bps) or self.cost_bps < 0:
            raise ValueError('cost_bps must be finite and nonnegative')


def _validate_dates(frame):
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise ValueError('Use a DatetimeIndex of exchange session dates')
    if frame.index.tz is not None or not frame.index.equals(frame.index.normalize()):
        raise ValueError('Use timezone-naive midnight session dates')
    if frame.index.hasnans or frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError('Dates must be valid, unique and increasing')


def replay_signals(prices, benchmark, valuations=None, rules=None):
    """Replay closes; valuations are EXACT-date, historical observation rows.

    valuations columns: forwardPE, pegRatio (optional). Its index denotes the
    session at whose close these observations were already known. Never label
    a current estimate with an earlier date. Missing dates are not filled.
    Prices need consistently adjusted Open/High/Low/Close, benchmark Close.
    """
    rules = rules or BuyRules()
    _validate_dates(prices)
    _validate_dates(benchmark)
    for col in ('Open', 'High', 'Low', 'Close'):
        values = pd.to_numeric(prices[col], errors='coerce')
        if not values.map(lambda v: math.isfinite(v) and v > 0).all():
            raise ValueError('Invalid price: ' + col)
    if valuations is not None:
        _validate_dates(valuations)
    rows = []
    for i, date in enumerate(prices.index):
        past = prices.iloc[:i + 1]
        # A matching benchmark session is required; stale bars are not reused.
        market = benchmark.loc[benchmark.index <= date, 'Close']
        trend = None
        if date in market.index:
            metrics = trend_metrics(past['Close'], market, now=date)
            trend, _, _ = trend_health_score(metrics)
        opportunity = None
        reason = 'missing historical valuation'
        if valuations is not None and date in valuations.index:
            info = valuations.loc[date].to_dict()
            info = {k: v for k, v in info.items() if pd.notna(v)}
            val, detail = valuation_score(info)
            k, d = slow_stochastic(past['High'], past['Low'], past['Close'])
            opportunity, reason, _ = opportunity_score(val, detail, rsi(past['Close']), k, d)
        rows.append({'opportunity': opportunity, 'trend': trend, 'detail': reason})
    result = pd.DataFrame(rows, index=prices.index, columns=['opportunity', 'trend', 'detail'])
    result['trend_previous'] = result['trend'].shift(rules.improvement_sessions)
    result['eligible'] = (
        (result['opportunity'] >= rules.opportunity_min)
        & (result['trend'] >= rules.trend_min)
        & (result['trend'] > result['trend_previous'])
    )
    return result


def simulate_buys(prices, signals, rules=None, initial_cash=10000.0):
    """At most N equal cash tranches; prior close signal executes next open.

    No sales, leverage or automatic replenishment. Uninvested cash earns zero.
    Costs are charged on buys. End values are marked to close, without selling.
    """
    rules = rules or BuyRules()
    _validate_dates(prices)
    if prices.empty or not prices.index.equals(signals.index):
        raise ValueError('Prices and signals must have identical nonempty dates')
    if not math.isfinite(initial_cash) or initial_cash <= 0:
        raise ValueError('initial_cash must be positive and finite')
    for col in ('Open', 'Close'):
        if not prices[col].map(lambda v: math.isfinite(v) and v > 0).all():
            raise ValueError('Invalid execution price: ' + col)
    cash, shares = float(initial_cash), 0.0
    tranche = initial_cash / rules.tranches
    cost = rules.cost_bps / 10000
    last_buy = -rules.spacing_sessions
    trades, equity = [], []
    for i, (date, bar) in enumerate(prices.iterrows()):
        signal = signals['eligible'].iloc[i - 1] if i else False
        if (pd.notna(signal) and bool(signal) and len(trades) < rules.tranches
                and i - last_buy >= rules.spacing_sessions):
            spend = min(tranche, cash)
            quantity = spend / (bar['Open'] * (1 + cost))
            shares += quantity
            cash -= spend
            last_buy = i
            trades.append({'date': date, 'signal_date': prices.index[i - 1],
                           'price': bar['Open'], 'shares': quantity,
                           'cash_spent': spend, 'fee': spend - quantity * bar['Open']})
        equity.append(cash + shares * bar['Close'])
    curve = pd.Series(equity, index=prices.index, name='equity')
    # Include initial capital in the peak so the first day's loss counts.
    peaks = curve.cummax().clip(lower=initial_cash)
    benchmark_shares = initial_cash / (prices['Open'].iloc[0] * (1 + cost))
    return {
        'trades': pd.DataFrame(trades), 'equity': curve,
        'return_pct': (curve.iloc[-1] / initial_cash - 1) * 100,
        'max_drawdown_pct': ((curve / peaks - 1) * 100).min(),
        'buy_hold_return_pct': (benchmark_shares * prices['Close'].iloc[-1] / initial_cash - 1) * 100,
        'cash_remaining': cash,
        'eligible_days': int(signals['eligible'].fillna(False).sum()),
        'opportunity_coverage_pct': float(signals['opportunity'].notna().mean() * 100),
    }


def main():
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prices', required=True)
    parser.add_argument('--benchmark', required=True)
    parser.add_argument('--valuations', help='Historical observations; never current estimates backfilled')
    parser.add_argument('--start', required=True, help='Evaluation start date after warmup, YYYY-MM-DD')
    parser.add_argument('--output', required=True, help='New output directory')
    parser.add_argument('--opportunity-min', type=float, default=70)
    parser.add_argument('--trend-min', type=float, default=60)
    parser.add_argument('--improvement-sessions', type=int, default=5)
    parser.add_argument('--tranches', type=int, default=3)
    parser.add_argument('--spacing-sessions', type=int, default=5)
    parser.add_argument('--cost-bps', type=float, default=10)
    args = parser.parse_args()
    rules = BuyRules(**{k: getattr(args, k) for k in BuyRules.__dataclass_fields__})

    def read(path):
        return pd.read_csv(path, parse_dates=['Date']).set_index('Date')

    prices, benchmark = read(args.prices), read(args.benchmark)
    valuations = read(args.valuations) if args.valuations else None
    signals = replay_signals(prices, benchmark, valuations, rules)
    window = prices.index >= pd.Timestamp(args.start)
    result = simulate_buys(prices.loc[window], signals.loc[window], rules)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    signals.to_csv(output / 'signals.csv')
    result.pop('trades').to_csv(output / 'trades.csv', index=False)
    result.pop('equity').to_csv(output / 'equity.csv')
    result['rules'] = vars(rules)
    result['warning'] = ('Experimental buy-only simulation; missing valuation dates never trigger buys. '
                         'Zero trades do not establish strategy performance. No sell rule or cash interest. '
                         'Current portfolio selection introduces selection bias.')
    (output / 'summary.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
