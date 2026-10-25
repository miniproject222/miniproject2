# 4. 날씨 광고 타이밍 (`weather`)

날씨, 상황에 따른 광고(메타, 아마존) 노출 빈도와 예산 추천

| 파일 | 내용 |
|---|---|
| `weather_page.py` | 화면 + 기능 (`weather_render()` 함수 하나) |
| `weather_data.py` | Open-Meteo 날씨(4개 권역), 경쟁사 재고(경쟁사 DB + Keepa 마지막 조회값, 못 읽으면 샘플), 히트 스코어·예산 추천 계산 |
| `weather_report.py` | PDF 보고서 만들기 (`weather_make_pdf()`, matplotlib + `common/fonts/SUIT`) |
| `weather_style.css` | 디자인 (class는 `weather-`로 시작) |
| `images/` | weather에서만 쓰는 이미지 |
| `data/` | weather에서만 쓰는 데이터 |

- 위젯 `key`, `st.session_state` 키는 `weather-`로 시작합니다. (예: `key="weather-btn-search"`)
- 다른 탭과 데이터 주고받기: `store_set("weather", ...)` / `store_get("다른모듈")`
- Supabase 표 이름은 `weather_`로 시작합니다. (예: `weather_result`)

## 화면 구성

왼쪽 넓은 본문 + 오른쪽 좁은 열 (대시보드형 2단)

- 본문 위: 권역 날씨 카드 4개 가로 배치 (북부 Hamburg·Bremen·Kiel / 서부 Köln·Düsseldorf·Dortmund /
  동부 Berlin·Leipzig·Dresden / 남부 München·Stuttgart·Nürnberg). 큰 숫자는 3개 도시 평균, 오른쪽 위에 날씨 이모지
- 본문 가운데 (반반): 채널별 추천 액션 | 이번 주 광고 예산
  - 예산 카드: 주간 예산 슬라이더(최소·최대는 오른쪽 위 "범위 설정"에서 입력) → 채널 비율(슬라이더로 메타 비율 바로 조정,
    처음 값은 경쟁사 재고 기준 추천값) → 메타·아마존 금액 2칸
- 본문 아래: 7일 중 최고기온 30°C 이상인 권역만 날짜별 메타 예산(€) 그래프
- 오른쪽 위: 경쟁사 재고 시그널 (품절·정상 개수 + 목록, 제목 옆에 "Keepa · 조회일 기준". 샘플일 때만 재고 낮음 칸 표시)
- 오른쪽 아래: 오늘의 추천 (할 일 카드 목록 + PDF 보고서 버튼)
- 오른쪽 위 "폭염 시나리오(샘플)" 토글: 실제 예보 대신 여름 샘플로 화면·보고서 확인
- 이 탭을 연 동안만 본문 폭을 넓히고 위·양옆 여백을 둠 (`weather_style.css` 맨 위, 탭 순서 5번째 기준)
- 날씨 카드를 뺀 모든 박스는 흰 카드 배경(테두리 없음), 카드 가로 간격은 권역 카드 4칸 간격과 같게 맞춤
- 글꼴: 팀 공용 글꼴 SUIT (`common/fonts`와 같은 글꼴의 웹 버전을 jsDelivr에서 불러와 이 탭에만 적용)

## 예산 계산 규칙

- 채널: 추천 비율은 아마존 기본 40%, 경쟁사 재고 낮음 45%, 품절 50%, 나머지는 메타 (직접 설정하면 그 비율 사용)
- 메타: 60%는 4개 권역·7일에 똑같이, 40%는 30°C 이상 예보일에 (최고기온 - 29)점 비례로 추가
- 아마존: 전국 단위, 날짜별 가중치 1 + 0.1 × (그날 4개 권역 점수 합)
- 금액은 반올림해도 합계가 주간 예산과 정확히 같게 나눔 (`weather_split`)

## 경쟁사 재고 데이터

`weather_data.py`의 `weather_get_competitors()`가 아래 두 파일을 **읽기만** 합니다. (Keepa API를 직접 부르지 않아 토큰을 쓰지 않음)

| 데이터 | 파일 | 쓰는 값 |
|---|---|---|
| 경쟁사 DB (PM 공용) | `data/common_competitor_seori_202610.csv` | `원본시트`가 "경쟁사DB"이고 `구분`이 "독일 N위"인 경쟁사의 브랜드·제품명·ASIN (report 대시보드와 같은 상위 경쟁사) |
| Keepa 마지막 조회값 (report 관리) | `modules/report/data/report_keepa_snapshot.json` | ASIN별 `in_stock`(없으면 품절), `fetched_at`(조회 시점) |

- 값은 report 탭에서 Keepa를 조회할 때(조회 버튼 또는 아침 자동 갱신, 하루 1번) 바뀝니다. 실시간 값이 아닙니다.
- Keepa 값으로는 품절/정상만 알 수 있어, 실제 데이터에서는 "재고 낮음"과 "품절 N일째" 대신 "품절 (10/24 확인)"처럼 조회일을 표시합니다.
- 파일이 없거나 형식이 바뀌어 못 읽으면 샘플 3줄을 쓰고 "샘플" 표시를 붙입니다.

화면과 보고서가 쓰는 모양:

```python
[{"competitor": "Novilla", "product": "...", "asin": "B0...", "status": "soldout", "days": None, "checked": "2026-10-24"}]
# status: "soldout" | "low" | "normal", days: 그 상태가 이어진 일수(샘플만), checked: Keepa 조회 시점(샘플은 "")
```
