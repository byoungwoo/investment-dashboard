---
paths:
  - "config.py"
  - "fundamentals.py"
---

# 종목을 추가·수정할 때

`config.py` 의 `PORTFOLIO` 에 넣으면 끝이 아니다.

## `survival` / `growth` 는 점수가 아니다

1~5 **사용자 확신도 표시값**(★)이다. `WEIGHTS` 에 들어가지 않고 Price Score·Grade에
영향을 주지 않는다. **임의로 정하지 말고 사용자에게 확인받는다.**
배경은 `docs/adr/0004-survival-growth-as-user-conviction.md`.

## `FUNDAMENTAL_DETAILS` 는 수동 스냅샷이다

`fundamentals.py` 의 이 딕셔너리는 **일부 종목만** 가진 공시 스냅샷이고, 상세 UI 전용이다.
Price Score / Grade / Action / Shadow 모델과 의도적으로 분리돼 있다
(`docs/adr/0003-fundamentals-excluded-from-score.md`).

- 스냅샷이 없는 종목은 `has_fundamental_detail()` 가드가 상세 버튼을 막는다.
  이 가드를 우회하면 `show_fundamental_detail()` 에서 KeyError가 난다
- **실제 공시 수치를 지어내서 채우지 않는다.** 값이 없으면 비워 두고 사용자에게 받는다
- 채울 때 `period` / `updated` 를 함께 적는다 — 언제 기준 숫자인지가 수치 자체만큼 중요하다

## 추가한 뒤

```bash
python3 main.py
```

UI 없이 그 종목의 Val / Tech / Score가 **실제로 나오는지** 확인한다.
`ticker` 는 거래소에 따라 심볼이 다르다 (ABB → `ABBN.SW`).
