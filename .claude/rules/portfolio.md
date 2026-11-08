---
paths:
  - "config.py"
  - "fundamentals.py"
  - "data/fundamentals/*.json"
---

# 종목을 추가·수정할 때

`config.py` 의 `PORTFOLIO` 에 넣으면 끝이 아니다.

## `survival` / `growth` 는 점수가 아니다

1~5 **사용자 확신도 표시값**(★)이다. `WEIGHTS` 에 들어가지 않고 Price Score·Grade에
영향을 주지 않는다. **임의로 정하지 말고 사용자에게 확인받는다.**
배경은 `docs/adr/0004-survival-growth-as-user-conviction.md`.

## 공시 스냅샷은 `data/fundamentals/<TICKER>.json` 에 있다

**파일명이 심볼이다.** `fundamentals.load_snapshots()` 가 읽어 `FUNDAMENTAL_DETAILS` 를 만든다.
`fundamentals.py` 는 렌더 로직만 — 숫자를 고칠 때 이 파일을 열 일은 없다 (ADR-0005).
**갱신은 `/earnings <티커>` 로 시작한다.** 신선도는 `python3 scripts/snapshot_status.py --earnings`.

일부 종목만 가진 공시 스냅샷이고, 상세 UI 전용이다.
Price Score / Grade / Action / Shadow 모델과 의도적으로 분리돼 있다
(`docs/adr/0003-fundamentals-excluded-from-score.md`).

- 스냅샷이 없는 종목은 `has_fundamental_detail()` 가드가 상세 버튼을 막는다.
  이 가드를 우회하면 `show_fundamental_detail()` 에서 KeyError가 난다
- **실제 공시 수치를 지어내서 채우지 않는다.** 값이 없으면 비워 두고 사용자에게 받는다
- `period` / `updated` / `source_url` 은 **필수다.** 없으면
  `tests/test_fundamental_snapshots.py` 가 실패한다 — 출처 없는 수치는 커밋되지 않는다
- `updated` 는 **발표일**이고 `YYYY-MM-DD` 다. 100일이 지나면 앱이 상세 패널에 경고를 띄운다

## 추가한 뒤

```bash
python3 main.py
```

UI 없이 그 종목의 Val / Tech / Score가 **실제로 나오는지** 확인한다.
`ticker` 는 거래소에 따라 심볼이 다르다 (ABB → `ABBN.SW`).
