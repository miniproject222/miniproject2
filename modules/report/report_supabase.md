# ① 문제 분석(report) Supabase 연동 요청

대상: PM · 작성: report 담당 · 2026-10-25

## 요약

- ① 탭 결과는 이미 `store_set("report")`로 **`common_store` 표(key = `"report"`)**에 저장되게 만들어 두었습니다. Supabase만 연결되면 바로 저장됩니다 (약 22KB, JSON 1행).
- 그 외에 **실행 중에 바뀌는 파일 3개**와 **A/B 결과**는 Streamlit Cloud에서 재시작하면 사라지므로, report 전용 표 4개가 필요합니다.
- 고정 참고 데이터(경쟁사 DB, 독일 DB, 서리 가정 등)는 지금처럼 저장소 파일로 두어도 됩니다.

## 1. 반드시 필요한 것

### 1-1. `common_store` 표 (공통, PM 담당)

| 열 | 형식 | 설명 |
|---|---|---|
| `key` | text, 기본 키 | `"report"` |
| `value` | jsonb | ① 탭 결과 전체 (`version: report-v2`) |

- 다른 탭(홈·② 가설·③ 광고 소재)이 `store_get("report")`로 읽는 값입니다. 이 표가 없으면 새로고침할 때마다 사라지고, 다른 사람 화면에는 보이지 않습니다.
- 들어가는 키 목록: `report_handoff.md`의 '탭별로 쓰면 되는 키'

### 1-2. report 전용 표 (새로 만들 표 4개)

Streamlit Cloud는 앱이 다시 시작되면 실행 중에 쓴 파일이 지워집니다. 아래 값은 실행 중에 바뀌므로 표로 옮겨야 합니다.

| 표 이름 | 지금 파일 | 왜 필요한가 | 열 (제안) |
|---|---|---|---|
| **`report_keepa_usage`** | `data/report_keepa_usage.json` | **Keepa 토큰 사용량 기록.** 사라지면 프로젝트 한도(600)를 넘겨 조회할 수 있음 | `id`(자동), `used_at`(timestamp), `tokens`(int), `what`(text) · 한도 600은 코드 상수 |
| **`report_keepa_snapshot`** | `data/report_keepa_snapshot.json` | 경쟁사 현재가·평점·리뷰·순위·재고. 화면·KPI·다른 탭 경쟁사 신호의 원본 | `asin`(text, 기본 키), `data`(jsonb), `fetched_at`(timestamp) |
| **`report_keepa_detail`** | `data/report_keepa_detail_202610.json` | 냉감패드 실적 순위(1년 판매 신호·여름 순위), 월 구매 배지, 가격 기준(작년 같은 날), 리뷰 1년 변화 | `asin`(text, 기본 키), `data`(jsonb), `updated_at`(timestamp) |
| **`report_ab_result`** | (지금은 store 안 `ab_upload`) | ① 탭에 올린 A/B 결과 파일 분석 기록. 홈 탭 `ab_test`의 원본 | `id`(자동), `uploaded_at`(timestamp), `file_name`(text), `result`(jsonb), `verdict`(text) |

- 행 수: snapshot·detail 각 10개 안팎, usage는 조회할 때마다 1행 (하루 최대 1~2행), ab_result는 올릴 때마다 1행
- 저장·읽기는 RULES대로 `common_db`의 `db_read`·`db_upsert`·`db_insert`만 씁니다. 표가 만들어지면 report 코드를 표 기준으로 바꾸겠습니다 (지금은 파일 사용).

### 1-3. Streamlit Cloud Secrets (report 칸)

| 이름 | 값 | 비고 |
|---|---|---|
| `KEEPA_API_KEY` | Keepa API 키 | 필수 (배포 화면의 Keepa 조회·아침 자동 갱신) |
| `KEEPA_FETCH_PIN` | 조회 확인용 PIN | 필수 (화면 버튼 조회 보호) |
| `KEEPA_AUTO_DAILY` | `"off"` 또는 `"on"` | 선택. `"on"`이면 매일 08:00(한국) 이후 첫 접속에 경쟁사 3곳 자동 조회 (약 6토큰, 하루 최대 10) |
| `REPORT_GA4_PROPERTY_ID`, `REPORT_GA4_CREDENTIALS` | GA4 속성 ID, 서비스 계정 JSON | GA4 연결 시 (매출·퍼널·UTM) |

- `.streamlit/secrets.toml.example`에 추가할 줄 (PM 파일이라 report 담당은 수정하지 않음):
  ```toml
  KEEPA_FETCH_PIN = "your_pin_here"
  KEEPA_AUTO_DAILY = "off"   # "on"이면 매일 아침 Keepa 자동 갱신 (report)
  ```

## 2. Supabase에 넣지 않아도 되는 것 (저장소 파일 유지)

실행 중에 바뀌지 않는 참고 데이터라 파일로 두어도 배포에 문제가 없습니다.

| 파일 | 내용 |
|---|---|
| `data/common_competitor_seori_202610.csv` | 공통 경쟁사 DB (여러 시트) |
| `data/common_germany_knowledge_seori_202610.csv` | 독일 시장 지식 DB |
| `modules/report/data/report_seori_assumption_202610.json` | 서리 가정 (Q-max·인증·시험·광고 문구) |
| `modules/report/data/report_shop_reviews_202610.json` | 자사몰 리뷰 (가정: SleepCOOL 공식몰 Trusted Shops, 2026-10-25 조회) |
| `modules/report/data/report_market_cooling10_202610.json` | 냉감패드 10개사 ㎡당 가격 |
| `modules/report/data/report_keepa_asin_202610.json` | Keepa 조회 상품 목록 |
| `modules/report/data/report_sqp_*`, `report_listing_dummy_*`, `report_ads_keywords_dummy_*` | 검색어 분석 가상 데이터 |
| `modules/report/data/report_temp_dwd_202608.csv`, `report_sqp_events_202608.json` | 기온(DWD)·이벤트 |

> 경쟁사 DB를 팀원이 화면에서 직접 고치게 할 계획이 생기면 그때 표로 옮기면 됩니다.

## 3. 진행 순서 제안

1. PM: `common_store` 표 확인 + report 전용 표 4개 생성 + Cloud Secrets 입력
2. report 담당: Keepa 사용량·스냅샷·상세·A/B 결과를 파일 대신 표에 읽고 쓰도록 코드 변경 (`common_db` 사용)
3. 함께 확인: 배포 화면에서 ① 탭 열기 → `common_store`에 `report` 행 생성 → 홈·② 탭에서 값 확인

## 참고

- 다른 탭이 읽는 키와 형식: `modules/report/report_handoff.md`
- 지금 다른 탭이 실제로 읽는 키: 홈 `problems`·`ab_test`(+ GA4 매출 키는 연결 후), ② 가설 `problems`·`sqp`·`summary`, ③ 광고 소재 `sqp`
