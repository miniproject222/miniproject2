# 4. 날씨 광고 타이밍 (`weather`)

날씨, 상황에 따른 광고(메타, 아마존) 노출 빈도와 예산 추천

| 파일 | 내용 |
|---|---|
| `weather_page.py` | 화면 + 기능 (`weather_render()` 함수 하나) |
| `weather_style.css` | 디자인 (class는 `weather-`로 시작) |
| `images/` | weather에서만 쓰는 이미지 |
| `data/` | weather에서만 쓰는 데이터 |

- 위젯 `key`, `st.session_state` 키는 `weather-`로 시작합니다. (예: `key="weather-btn-search"`)
- 다른 탭과 데이터 주고받기: `store_set("weather", ...)` / `store_get("다른모듈")`
- Supabase 표 이름은 `weather_`로 시작합니다. (예: `weather_result`)
