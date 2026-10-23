# 3-1. 솔루션 제안 (`solution`)

매체 외에 실행할 수 있는 솔루션 제안

| 파일 | 내용 |
|---|---|
| `solution_page.py` | 화면 + 기능 (`solution_render()` 함수 하나) |
| `solution_style.css` | 디자인 (class는 `solution-`로 시작) |
| `images/` | solution에서만 쓰는 이미지 |
| `data/` | solution에서만 쓰는 데이터 |

- 위젯 `key`, `st.session_state` 키는 `solution-`로 시작합니다. (예: `key="solution-btn-search"`)
- 다른 탭과 데이터 주고받기: `store_set("solution", ...)` / `store_get("다른모듈")`
- Supabase 표 이름은 `solution_`로 시작합니다. (예: `solution_result`)
