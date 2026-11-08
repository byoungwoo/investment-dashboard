---
description: 현재 브랜치의 작업을 고정 템플릿으로 요약해 PR 코멘트(없으면 docs/handoff/)로 남긴다. 세션을 끝낼 때 사용.
disable-model-invocation: true
argument-hint: "[남길 메모 (선택)]"
allowed-tools: Bash(git *) Read Write Edit mcp__github
---

# 세션 핸드오프 작성

다음 데이터는 이미 수집됐다. 추측하지 말고 이것만 근거로 쓴다.

## 브랜치
!`git branch --show-current`

## main 과의 차이
```!
git diff main...HEAD --stat || true
git log main..HEAD --oneline || true
```

## 커밋되지 않은 변경
!`git status --short || true`

## 최근 커밋
!`git log --oneline -8`

## 사용자 메모
$ARGUMENTS

---

## 할 일

1. 테스트 상태를 **직접 확인한다**: `python3 -m unittest discover -s . -t . -p 'test_*.py'`
   (49개 통과가 기준선. 돌리지 않았다면 "미확인"이라고 쓴다 — 통과했다고 추정하지 않는다)

2. 아래 템플릿을 **항목 순서 그대로** 채운다. 모르는 항목은 비우지 말고 "없음" / "미확인"을 쓴다.
   채팅 대화를 그대로 옮기지 않는다. 다음 사람이 **재개하는 데 필요한 것만** 쓴다.

```markdown
## 핸드오프 — <브랜치> / <YYYY-MM-DD>

**문제**: 무엇을 하려 했나 (1~2줄)
**내린 결정**: 선택한 것 + 왜. 되돌릴 수 있는지
**건드린 파일**: 파일 — 무엇을 바꿨나
**테스트**: 49개 통과 / N개 실패(어느 것) / 미확인
**다음 단계**: 구체적인 다음 행동 1~3개
**막힌 지점**: 사용자 결정이 필요한 것, 모르는 것
```

3. 남길 위치를 정한다:
   - **현재 브랜치에 PR이 있으면** → github MCP로 그 PR에 코멘트를 추가한다
     (`list_pull_requests` / `search_pull_requests` 로 `head` 가 현재 브랜치인 PR을 찾고,
     `add_issue_comment` 로 코멘트. 서버가 노출하는 실제 도구 이름을 쓴다)
   - **PR이 없거나 github MCP가 연결되지 않았으면** → `docs/handoff/<브랜치>.md` 에 **append**
     (덮어쓰지 않는다. 최신 항목이 위로 오게 쌓는다)
   - 어느 쪽에 남겼는지 마지막에 한 줄로 보고한다

4. `main` 에서 실행한 경우에만, 그리고 상태가 실제로 바뀌었을 때만
   `PROJECT_STATE.md` 의 "지금 상태 / 진행 중 / 다음 우선순위"를 갱신한다.
   **`lab` / `hotfix` 에서는 `PROJECT_STATE.md` 를 수정하지 않는다** (main 소유).

5. "왜 그렇게 정했는가"가 앞으로도 유효한 결정이면 핸드오프에 묻어두지 말고
   `docs/adr/` 에 새 ADR로 올릴 것을 제안한다 (`docs/adr/0000-template.md` 사용).
