---
paths:
  - "app.py"
  - "requirements.txt"
  - "config.py"
  - "fundamentals.py"
  - "data/fundamentals/*.json"
---

# 배포 (Streamlit Cloud)

`git push origin main` → `lbw-portfolio.streamlit.app` 자동 재배포.

## 모듈을 새로 추가·수정한 커밋은 새로고침으로 반영되지 않는다

Streamlit이 `app.py` 만 다시 실행하고 `sys.modules` 의 옛 모듈을 그대로 쓰기 때문에
`ImportError` 가 난다. 이때는 **Manage app → Reboot app** 으로 프로세스를 재시작한다.

(2026-10-11 `has_fundamental_detail` 추가 때 실제로 발생)

## 모듈 수준에서 읽는 데이터만 바뀐 커밋도 Reboot이 필요하다

`.py` 를 한 줄도 고치지 않고 `data/fundamentals/*.json` 만 갱신한 커밋도 그렇다.

- `fundamentals.py` 의 `FUNDAMENTAL_DETAILS = load_snapshots()` 는 **import 시점에 한 번**
  JSON을 읽는다. 옛 모듈이 `sys.modules` 에 남아 있으면 파일을 다시 읽지 않는다
- `config.py` 의 `PORTFOLIO` 도 모듈 수준 dict다 — 종목을 지워도 화면에 계속 남는다

이쪽은 **`ImportError` 로 드러나지 않는다.** 앱은 멀쩡히 뜨고 옛 분기 수치와 지운 종목을
조용히 보여준다. "스냅샷을 갱신했는데 화면이 그대로"일 때 파일을 다시 뒤지기 전에 Reboot한다.

(2026-11-08 ABB·VRT를 Q3 2026으로 갱신하고 ORCL을 제거한 커밋)

## `requirements.txt`

의존성을 추가하면 재배포만으로는 부족할 수 있다 — Reboot으로 환경을 다시 만든다.
FRED API 키는 `.streamlit/secrets.toml` 에 있고 **커밋하지 않는다.**
Streamlit Cloud 쪽 값은 Manage app → Settings → Secrets 에서 따로 넣는다.
