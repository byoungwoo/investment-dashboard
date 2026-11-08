"""공시 스냅샷의 신선도를 한 표로 본다.

`/earnings` 스킬과 사람이 같이 쓴다. 기본은 오프라인 — 파일만 읽는다.
`--earnings` 를 주면 yfinance에서 다음 실적 발표일까지 확인한다 (네트워크).

    python3 scripts/snapshot_status.py
    python3 scripts/snapshot_status.py --earnings
"""

import sys
from datetime import date
from pathlib import Path

# scripts/ 에서 실행해도 리포 루트 모듈을 읽을 수 있게.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import PORTFOLIO
from fundamentals import FUNDAMENTAL_DETAILS, STALE_AFTER_DAYS, snapshot_age_days


def main(check_earnings=False):
    today = date.today()
    next_earnings = {}
    if check_earnings:
        from fetcher import fetch_next_earnings
        for symbol in PORTFOLIO:
            next_earnings[symbol] = fetch_next_earnings(PORTFOLIO[symbol]["ticker"])

    print(f"{'종목':<6} {'기준 분기':<12} {'갱신일':<12} {'경과':>6}  상태")
    for symbol in sorted(PORTFOLIO):
        detail = FUNDAMENTAL_DETAILS.get(symbol)
        if detail is None:
            print(f"{symbol:<6} {'-':<12} {'-':<12} {'-':>6}  스냅샷 없음")
            continue
        age = snapshot_age_days(detail, today)
        age_text = "?" if age is None else f"{age}일"
        state = "낡음" if age is not None and age >= STALE_AFTER_DAYS else "최신"
        print(f"{symbol:<6} {detail['period']:<12} {detail['updated']:<12} {age_text:>6}  {state}")

    if check_earnings:
        print("\n다음 실적 발표일")
        for symbol in sorted(next_earnings):
            when = next_earnings[symbol]
            if when is None:
                print(f"  {symbol:<6} 미확인")
            else:
                print(f"  {symbol:<6} {when.isoformat()} (D-{(when - today).days})")


if __name__ == "__main__":
    main(check_earnings="--earnings" in sys.argv)
