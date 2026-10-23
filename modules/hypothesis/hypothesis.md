# 2. 가설 수립 (`hypothesis`)

문제 해결 가설 제안 (현지 특성 반영)

| 파일 | 내용 |
|---|---|
| `hypothesis_page.py` | 화면 + 기능 (`hypothesis_render()` 함수 하나) |
| `hypothesis_style.css` | 디자인 (class는 `hypothesis-`로 시작) |
| `images/` | hypothesis에서만 쓰는 이미지 |
| `data/` | hypothesis에서만 쓰는 데이터 |

- 위젯 `key`, `st.session_state` 키는 `hypothesis-`로 시작합니다. (예: `key="hypothesis-btn-search"`)
- 다른 탭과 데이터 주고받기: `store_set("hypothesis", ...)` / `store_get("다른모듈")`
- Supabase 표 이름은 `hypothesis_`로 시작합니다. (예: `hypothesis_result`)
