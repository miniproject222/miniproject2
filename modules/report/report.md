# 1. 분석 리포트 (`report`)

결과 데이터 요약, 문제 분석, 리포트 다운로드

| 파일 | 내용 |
|---|---|
| `report_page.py` | 화면 + 기능 (`report_render()` 함수 하나) |
| `report_style.css` | 디자인 (class는 `report-`로 시작) |
| `report_download.py` | 리포트 다운로드 버튼 (`report_download_button()`) |
| `images/` | report에서만 쓰는 이미지 |
| `data/` | report에서만 쓰는 데이터 |

- 위젯 `key`, `st.session_state` 키는 `report-`로 시작합니다. (예: `key="report-btn-search"`)
- 다른 탭과 데이터 주고받기: `store_set("report", ...)` / `store_get("다른모듈")`
- Supabase 표 이름은 `report_`로 시작합니다. (예: `report_result`)
