# 3. 매체 제작 (`media`)

가설 2개 → 프롬프트 2개 → 결과물 2개 (프롬프트 다듬기)

| 파일 | 내용 |
|---|---|
| `media_page.py` | 화면 + 기능 (`media_render()` 함수 하나) |
| `media_style.css` | 디자인 (class는 `media-`로 시작) |
| `images/` | media에서만 쓰는 이미지 |
| `data/` | media에서만 쓰는 데이터 |

- 위젯 `key`, `st.session_state` 키는 `media-`로 시작합니다. (예: `key="media-btn-search"`)
- 다른 탭과 데이터 주고받기: `store_set("media", ...)` / `store_get("다른모듈")`
- Supabase 표 이름은 `media_`로 시작합니다. (예: `media_result`)
