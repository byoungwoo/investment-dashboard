# ADR-0002: `scorer` 테스트를 루트/`tests/` 두 층으로 나눈다

- 날짜: 2026-10-11 (기록: 2026-10-19)
- 작성자: 이병우
- 상태: 유효
- 출처: 334717e `chore: make the full test suite runnable in one command`, 기존 CLAUDE.md

## 맥락

`test_scorer.py` 가 루트와 `tests/` 양쪽에 있다. 이름이 같아서 **중복처럼 보이고,
한쪽을 지우고 싶은 충동이 든다.** 중복이 아니다.

## 결정

두 층은 역할이 다르다. 둘 다 유지한다.

| 위치 | 성격 |
|---|---|
| `test_scorer.py` (루트) | **값을 못 박는 회귀 테스트** — `assertAlmostEqual(score, 56.0)` 처럼 구체값 고정 |
| `tests/test_scorer.py` | **성질 검사** + `opportunity` / `trend_health` / `data_confidence` / `shadow` 커버리지 |

전체 실행은 **반드시** 한 명령으로:

```bash
python3 -m unittest discover -s . -t . -p 'test_*.py'
```

**`-s tests` 로 줄여 쓰면** 루트 `test_scorer.py` 를 조용히 건너뛰고 "OK"를 낸다.
통과했다고 착각하게 만드는 쪽이 아무것도 안 돌리는 것보다 위험하다.

## 근거

구체값 고정과 성질 검사는 깨지는 조건이 다르다. 공식을 의도적으로 바꾸면 루트가 깨지고(의도된 마찰),
리팩터링으로 성질이 무너지면 `tests/` 가 깨진다. 한 파일에 섞으면 "이 실패는 의도된 것인가"를
매번 판단해야 한다.

## 검토한 대안과 기각 이유

- **루트 테스트를 `tests/` 로 이동** — `-s tests` 축약이 안전해지지만, 두 성격이 한 디렉터리에 섞여
  실패의 의미 구분이 사라진다. 기각
- **pytest 도입으로 수집 규칙 통일** — 의존성 추가 없이 표준 unittest로 충분하다. 기각

## 결과

디렉터리 구조 자체가 함정을 품고 있다 → 테스트 명령을 `CLAUDE.md` 와
`.claude/rules/testing.md` 양쪽에 경고와 함께 박아두는 것으로 상쇄한다.
구조를 바꾸려면 이 ADR을 먼저 대체해야 한다.
