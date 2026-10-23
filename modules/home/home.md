# 홈 (`home`)

날씨, 달력, 전날 매출과 이슈 알림

| 파일 | 내용 |
|---|---|
| `home_page.py` | 화면 + 기능 (`home_render()` 함수 하나) |
| `home_style.css` | 디자인 (class는 `home-`로 시작) |
| `images/` | home에서만 쓰는 이미지 |
| `data/` | home에서만 쓰는 데이터 |

- 위젯 `key`, `st.session_state` 키는 `home-`로 시작합니다. (예: `key="home-btn-search"`)
- 다른 탭과 데이터 주고받기: `store_set("home", ...)` / `store_get("다른모듈")`
- Supabase 표 이름은 `home_`로 시작합니다. (예: `home_result`)
