# Role: 개별주 Dashboard Developer

이 리포는 **개별주 포트폴리오 대시보드**다. ETF 앱(`investment-dashboard-byeon`)과는 별개 리포다.

- 배포: `lbw-portfolio.streamlit.app`
- 리포: `github.com/byoungwoo/investment-dashboard`
- 보유: AVGO, ABB, VRT, IREN, ORCL

## 작업 전후에 반드시 돌릴 것

```bash
python3 -m unittest discover -s . -t . -p 'test_*.py'
```

36개가 전부 통과해야 한다. 1초 미만으로 끝난다.

**`-s tests` 로 줄여 쓰지 말 것.** 루트의 `test_scorer.py` 12개를 조용히 건너뛰고
"OK"를 내보낸다. 통과했다고 착각하게 만드는 쪽이 더 위험하다.

## 파일 역할

| 파일 | 성격 |
|---|---|
| `scorer.py`, `indicators.py` | **순수 계산.** 외부 I/O 없음 → 테스트하기 쉬운 곳, 반드시 테스트할 곳 |
| `fetcher.py` | 외부 I/O (yfinance, FRED). 테스트 경계 |
| `config.py` | 포트폴리오 정의, 가중치, Grade 임계값 |
| `fundamentals.py` | 공시 스냅샷 (수동 입력). 점수 계산에 **미반영** |
| `app.py` | Streamlit UI |
| `main.py` | CLI. `python3 main.py` 로 전 종목 점수를 표로 확인 — UI 없이 빠르게 검증할 때 |

## 계산 로직을 고칠 때

`scorer.py` / `indicators.py` 수정은 **테스트 없이 커밋하지 않는다.**

테스트가 실제로 일하는지 확인하는 방법: 고친 로직을 일부러 망가뜨려서
해당 테스트가 **실패하는지** 본다. 실패하지 않으면 그 테스트는 아무것도 지키지 않는다.

루트 `test_scorer.py`와 `tests/test_scorer.py`는 중복이 아니다.
- 루트: 정확한 값을 못 박는 회귀 테스트 (`assertAlmostEqual(score, 56.0)`)
- `tests/`: 성질 검사 + `opportunity` / `trend_health` / `data_confidence` / `shadow` 커버리지

## 종목을 추가할 때

`config.py`의 `PORTFOLIO`에만 넣으면 끝이 아니다.

- `survival` / `growth` 는 1~5 **사용자 확신도 표시값**이다 (★). 점수 계산에 안 들어간다.
  임의로 정하지 말고 사용자에게 확인받는다.
- `fundamentals.py`의 `FUNDAMENTAL_DETAILS` 는 **일부 종목만** 가진 수동 스냅샷이다.
  없는 종목은 `has_fundamental_detail()` 가드가 상세 버튼을 막는다.
  **실제 공시 수치를 지어내서 채우지 않는다.**
- 추가 후 `python3 main.py` 로 그 종목의 Val/Tech/Score가 실제로 나오는지 확인한다.

## 배포

`git push origin main` → Streamlit Cloud 자동 재배포.

**모듈을 새로 추가/수정한 커밋은 새로고침으로 반영되지 않는다.**
Streamlit이 `app.py`만 다시 실행하고 `sys.modules`의 옛 모듈을 그대로 쓰기 때문에
`ImportError`가 난다. 이때는 **Manage app → Reboot app** 으로 프로세스를 재시작한다.
(2026-10-11 `has_fundamental_detail` 추가 때 실제로 발생)

## 커밋 금지

- `.streamlit/secrets.toml` (FRED API 키)
- `__pycache__/`, `*.pyc`

## 워크트리

```
investment-dashboard         [main]    ← 배포 대상
investment-dashboard-lab     [lab]     ← 실험
investment-dashboard-hotfix  [hotfix]  ← 긴급 수정
```

`lab` / `hotfix` 는 쓰기 전에 `main` 기준으로 맞춰야 한다 (지금 둘 다 main에 병합된 과거 커밋에 멈춰 있음).

## 핵심 철학

Howard Marks: "좋은 기업 ≠ 좋은 가격"
