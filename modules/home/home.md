# 홈 (`home`)

날씨 + 각 탭 데이터 보고 → 팝업 알림

| 파일 | 내용 |
|---|---|
| `home_page.py` | 화면 (`home_render()`), 팝업 알림 |
| `home_data.py` | 다른 탭 데이터 읽기 (`store_get`), 알림 규칙, 광고 빈도 임시 규칙 |
| `home_globe.py` | 가운데 위성 지구본 + 주요 도시 실시간 기온 (Open-Meteo) |
| `home_style.css` | 디자인 (class는 `home-`로 시작) |
| `images/home_europe_bluemarble_01.jpg` | 지구본용 위성 사진 (NASA Blue Marble, 퍼블릭 도메인) |
| `data/` | home에서만 쓰는 데이터 |

## 화면 구성

| 자리 | 내용 | 데이터 |
|---|---|---|
| 전날 매출, 주요 문제, 매출 추이 | ① 문제 분석 결과 | `store_get("report")` |
| 도시별 기온, 지구본 | 독일 주요 도시 현재 기온 | Open-Meteo (실시간) |
| 알림 + 팝업 | 폭염(30°C 이상), 전날 매출 10% 이상 하락, ④ 광고 타이밍 알림 | 기온 + `report` + `weather` |
| 광고 빈도 추천 | ④ 광고 타이밍 추천값 (연결 전에는 기온 기준 임시 규칙) | `store_get("weather")` |
| 전체 진행률, 단계별 진행 | ①~④ 각 탭에 결과가 저장됐는지 | 각 탭 `store` |

다른 탭이 아직 구현 전이면 "연결 전" 자리 표시가 나옵니다.

## 홈이 읽는 데이터 모양 (각 탭 담당자에게 요청)

```python
store_set("report", {
    "yesterday_sales": 1284.0,        # 전날 매출 (€)
    "sales_delta": -0.18,             # 전일 대비 증감 (비율, -0.18 = 18% 하락)
    "sales_7d": [980, 1020, 1100, 1500, 1620, 1560, 1284],   # 최근 7일 매출 (오래된 날 → 어제)
    "problems": [{"title": "장바구니 이탈 증가", "type": "내부"}],   # type: 내부 / 외부
})
store_set("weather", {
    "ad_multiplier": 1.8,             # 광고 빈도 배수
    "reason": "폭염 + 경쟁사 품절",
    "alerts": [{"level": "high", "text": "경쟁사 품절 감지"}],     # level: high(팝업) / info
})
# hypothesis, media: 내용은 자유. 값이 저장되어 있으면 "완료"로 표시
```

- 위젯 `key`, `st.session_state` 키는 `home-`로 시작합니다. (예: `home-alerts-shown`)
- Supabase 표 이름은 `home_`로 시작합니다. (예: `home_result`)
