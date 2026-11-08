---
description: 이 리포의 현재 상태와 직전 작업을 복원해 10줄 브리핑을 낸다. 새 세션·새 팀원·오랜만의 복귀 때 첫 명령으로 사용.
argument-hint: "[궁금한 영역 (선택)]"
allowed-tools: Bash(git *) Read mcp__github
---

# 맥락 복원

## 현재 상태 파일
!`cat PROJECT_STATE.md 2>/dev/null || echo "(PROJECT_STATE.md 없음)"`

## 브랜치와 위치
```!
git branch --show-current
git worktree list
git status --short || true
```

## 최근 히스토리
!`git log --oneline -12`

## 남아 있는 핸드오프 노트
!`ls -t docs/handoff/ 2>/dev/null | head -5 || true`

## 관심 영역
$ARGUMENTS

---

## 할 일

1. 현재 브랜치에 PR이 있으면 github MCP로 **최신 코멘트 2~3개**를 읽는다
   (없거나 MCP 미연결이면 건너뛰고, 브리핑에 "PR 정보 없음"이라고 적는다).
   `docs/handoff/<브랜치>.md` 가 있으면 가장 최근 항목을 읽는다.

2. 위 데이터와 어긋나는 점이 있으면 **그걸 먼저 말한다.**
   `PROJECT_STATE.md` 의 최종 갱신일이 최근 커밋보다 오래됐다면 상태 파일이 낡은 것이다.

3. **10줄 이내**로 브리핑한다. 파일 내용을 그대로 복창하지 않는다:

```
지금: <배포 상태 / 어느 커밋>
직전 작업: <무엇이 끝났나>
진행 중: <있으면 어디까지, 없으면 "없음">
다음: <우선순위 1~3개>
막힌 것: <사용자 결정이 필요한 것>
주의: <상태 파일과 실제가 어긋나는 점, 있으면>
```

4. 과거 결정을 뒤집는 작업을 요청받으면 먼저 `docs/adr/` 에서 해당 ADR을 찾아 읽는다.
   브리핑 단계에서는 ADR을 전부 읽지 않는다 — 목록만 확인한다.
