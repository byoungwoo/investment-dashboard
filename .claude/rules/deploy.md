---
paths:
  - "app.py"
  - "requirements.txt"
---

# 배포 (Streamlit Cloud)

`git push origin main` → `lbw-portfolio.streamlit.app` 자동 재배포.

## 모듈을 새로 추가·수정한 커밋은 새로고침으로 반영되지 않는다

Streamlit이 `app.py` 만 다시 실행하고 `sys.modules` 의 옛 모듈을 그대로 쓰기 때문에
`ImportError` 가 난다. 이때는 **Manage app → Reboot app** 으로 프로세스를 재시작한다.

(2026-10-11 `has_fundamental_detail` 추가 때 실제로 발생)

## `requirements.txt`

의존성을 추가하면 재배포만으로는 부족할 수 있다 — Reboot으로 환경을 다시 만든다.
FRED API 키는 `.streamlit/secrets.toml` 에 있고 **커밋하지 않는다.**
Streamlit Cloud 쪽 값은 Manage app → Settings → Secrets 에서 따로 넣는다.
