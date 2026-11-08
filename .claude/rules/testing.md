---
paths:
  - "test_*.py"
  - "tests/**/*.py"
  - "scorer.py"
  - "indicators.py"
---

# 계산 로직과 테스트

`scorer.py` / `indicators.py` 는 외부 I/O가 없는 **순수 계산**이다. 테스트하기 쉬운 곳이고,
반드시 테스트할 곳이다. 수정은 **테스트 없이 커밋하지 않는다.**

## 테스트가 실제로 일하는지 확인하는 방법

고친 로직을 일부러 망가뜨려서 해당 테스트가 **실패하는지** 본다.
실패하지 않으면 그 테스트는 아무것도 지키지 않는다.

기대값은 **손계산해서 주석에 남긴다.** 코드를 다시 호출해 비교하면 공식이 바뀔 때
양쪽이 같이 바뀌어 아무것도 못 잡는다. (`tests/test_macro_score.py` 가 이 방식이다)

## 변이 테스트에는 `PYTHONDONTWRITEBYTECODE=1` 이 필수다

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s . -t . -p 'test_*.py'
```

이 맥의 Python은 Apple CommandLineTools 버전이고, 바이트코드 캐시를 로컬 `__pycache__/` 가
아니라 **홈 디렉터리**에 쓴다:

```
~/Library/Caches/com.apple.python/Users/lbw/IdeaProjects/<워크트리>/scorer.cpython-39.pyc
```

`find . -name __pycache__` 로는 **절대 안 나온다.**

pyc는 소스를 **mtime(초 단위)과 파일 크기**로만 검증한다. 변이와 원복이 같은 초 안에
일어나고 글자 수가 같으면(`0.70` ↔ `0.80`) Python이 캐시를 유효하다고 판단해
**변이된 바이트코드를 계속 실행한다.** 디스크 소스와 실행 결과가 어긋나고,
`inspect.getsource()` 는 디스크를 읽으므로 멀쩡해 보인다.

- 증상: 가중치가 분명히 0.80인데 `rate_weight` 가 0.7로 나온다
- 확인: `importlib.util.find_spec("scorer").cached` 로 캐시 경로를 본다
- 복구: 그 경로의 pyc를 삭제한다 (소스에서 자동 재생성된다)

2026-10-11 Macro Score 테스트 작성 중 실제로 이 함정에 빠졌고, 한동안 틀린 기대값을 쫓았다.

## 루트 `test_scorer.py` 와 `tests/test_scorer.py` 는 중복이 아니다

- **루트**: 정확한 값을 못 박는 회귀 테스트 (`assertAlmostEqual(score, 56.0)`)
- **`tests/`**: 성질 검사 + `opportunity` / `trend_health` / `data_confidence` / `shadow` 커버리지

배경은 `docs/adr/0002-two-tier-scorer-tests.md`.

## 결측과 0을 구분한다

`or` 로 기본값을 끼우지 않는다. `macro.get("ffr") or 5.25` 는 **0.00%를 결측으로 보고 갈아끼운다.**
정책금리 0%는 실재했던 값이다. `_or_default()` 를 쓴다 — `None` 일 때만 대체하고,
NaN은 통과시켜 `_clamp` 가 터뜨리게 둔다. 배경은 `docs/adr/0001-zero-is-not-missing.md`.
