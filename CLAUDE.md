# Role: 개별주 Dashboard Developer

이 리포는 **개별주 포트폴리오 대시보드**다. ETF 앱(`investment-dashboard-byeon`)과는 별개 리포다.
그쪽 모델(`etf_scorer.py`)과 이쪽 모델은 서로 건드리지 않는다.

- 배포: `lbw-portfolio.streamlit.app`
- 리포: `github.com/byoungwoo/investment-dashboard`
- 보유: AVGO, ABB, VRT, IREN, ORCL

@PROJECT_STATE.md

## 작업 전후에 반드시 돌릴 것

```bash
python3 -m unittest discover -s . -t . -p 'test_*.py'
```

**49개가 전부 통과해야 한다.** 0.2초 미만으로 끝난다.

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

## 커밋 금지

- `.streamlit/secrets.toml` (FRED API 키)
- `__pycache__/`, `*.pyc`

## 워크트리

```
investment-dashboard         [main]    ← 배포 대상
investment-dashboard-lab     [lab]     ← 실험
investment-dashboard-hotfix  [hotfix]  ← 긴급 수정
```

`lab` / `hotfix` 는 작업을 **시작하기 전에** main 기준으로 맞춘다.
`PROJECT_STATE.md` 는 **main이 소유한다** — lab / hotfix 세션은 수정하지 않고,
진행 상태를 PR 핸드오프 코멘트(`/handoff`)로 남긴다.

## 맥락이 어디에 있는지

| 찾는 것 | 파일 |
|---|---|
| 지금 상태 / 다음 할 일 | `PROJECT_STATE.md` (위에서 자동 로드) |
| 과거 결정의 "왜" | `docs/adr/` — 뒤집기 전에 해당 ADR을 읽는다 |
| 테스트·pyc 함정 | `.claude/rules/testing.md` (계산 파일 열 때 자동 로드) |
| 종목 추가 절차 | `.claude/rules/portfolio.md` |
| 배포·Reboot 조건 | `.claude/rules/deploy.md` |
| 세션 인수인계 | `/catchup` 으로 읽고, `/handoff` 로 남긴다 |

## 핵심 철학

Howard Marks: "좋은 기업 ≠ 좋은 가격"
