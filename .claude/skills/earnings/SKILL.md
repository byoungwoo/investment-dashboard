---
description: 실적 발표 후 공시 스냅샷(data/fundamentals/<TICKER>.json) 초안을 1차 출처에서 작성한다. 커밋하지 않고 사용자 검토로 넘긴다.
disable-model-invocation: true
argument-hint: "<티커> [공시 URL (선택)]"
allowed-tools: Bash(python3 *) Bash(git *) Read Write Edit WebFetch
---

# 공시 스냅샷 초안 작성

## 스냅샷 신선도 · 다음 발표일
```!
python3 scripts/snapshot_status.py --earnings || python3 scripts/snapshot_status.py || true
```

## 대상
$ARGUMENTS

---

## 할 일

### 1. 1차 출처만 읽는다

- **SEC EDGAR 8-K / 보도자료 원문, 또는 회사 IR 페이지.** 요약 기사·블로그·AI 요약 금지
- 사용자가 URL을 줬으면 그것을 쓴다. 없으면 찾아서 **어느 문서를 읽었는지 먼저 보고한다**
- 1차 출처에서 숫자를 못 찾으면 **비워 두고 사용자에게 묻는다.** 지어내지 않는다
  (요약 기사와 공시가 어긋난 적이 있다 — 커밋 `8ee2ed4`, IREN 주식보상 $106M)

### 2. 기존 파일의 양식을 그대로 따른다

같은 종목의 현재 파일을 먼저 읽어 구조를 복사한다. 새 종목이면 `data/fundamentals/IREN.json`
을 본보기로 쓴다. 필수 키는 `tests/test_fundamental_snapshots.py` 의 `REQUIRED` 가 정본이다.

- `badges` 는 **정확히 3개**
- `updated` 는 **발표일** (작업한 날이 아니다). `YYYY-MM-DD`
- `period` 는 회사 표기 그대로 (`Q1 FY2027`, `Q2 2026`)
- `source_url` 은 **실제로 읽은 그 문서**의 URL
- `tone`: `profit` 은 **GAAP 기준에만** 쓴다. 조정 EBITDA에 쓰면 주식보상·감가상각을
  뺀 수치가 순이익처럼 읽힌다
- 숫자 뒤에 해석을 붙이지 않는다. 해석은 `status` / `next_checks` / `break_conditions` 몫이다

### 3. 쓰고 나서

```bash
python3 -m unittest discover -s . -t . -p 'test_*.py'
```

전부 통과해야 한다. 필수 키 누락·날짜 형식 오류는 여기서 잡힌다.

### 4. 멈추고 사용자에게 넘긴다

**커밋하지 않는다.** 아래를 보고한다:

- 읽은 문서 (URL)
- 넣은 숫자 — 공시의 어느 항목에서 왔는지 한 줄씩
- **확신이 없는 값 / 찾지 못한 값** ← 이게 가장 중요하다
- 테스트 결과

`badges` 3개를 **무엇으로 골랐는지**와 `status` 판정은 투자 해석이다. 에이전트의 선택을
그대로 두지 말고 사용자가 바꾸도록 명시적으로 묻는다.

### 5. 끝난 뒤

- 스냅샷이 처음 생긴 종목이면 `PROJECT_STATE.md` 의 열린 질문에서 해당 항목을 지운다
- `period` 가 바뀌었으면 `tests/test_fundamentals.py` 의 값 고정 테스트도 갱신해야 한다
  (그 테스트가 실패하는 것은 정상이다 — 분기가 넘어갔다는 신호다)
