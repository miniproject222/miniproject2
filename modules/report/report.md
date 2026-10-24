# 1. 분석 리포트 (`report`)

결과 데이터 요약, 문제 분석 (내부/외부 요인, 경쟁사 비교), 문제 도출, 리포트 다운로드(PDF)

**실제 데이터만 표시합니다. 샘플(더미) 데이터는 쓰지 않습니다.** 데이터가 없는 카드는 무엇을 연결하면 나오는지 안내만 합니다.

| 파일 | 내용 |
|---|---|
| `report_page.py` | 화면 + 기능 (`report_render()` 함수 하나) |
| `report_data.py` | 실제 데이터 모으기 (`report_load_data()`), 유입 채널 계산, A/B 결과 계산 |
| `report_competitor.py` | 경쟁사 DB·독일 DB 읽기, Keepa 값 합치기, 내부/외부 요인·경쟁 포지션 KPI 만들기 |
| `report_keepa.py` | Keepa 조회 (확인 PIN + 동의 후 1회, 600토큰 한도), 스냅샷·사용량 저장 |
| `report_ga4.py` | GA4 연결 (UTM 유입 채널 + 구매 퍼널), UTM 링크 만들기, 자사몰 주소 `REPORT_SHOP_URL` |
| `report_pdf.py`, `report_download.py` | PDF 양식 3종 (① 기안 보고서형 ② 경영진 보고형 ③ 원페이지형), 화면과 같은 실제 데이터, fpdf2 필요 |
| `report_style.css` | 디자인 (class는 `report-`로 시작) |
| `data/report_keepa_asin_202610.json` | Keepa로 조회할 경쟁사 ASIN 5개 (Keepa 검색으로 찾은 후보, 확인 필요) |
| `data/report_keepa_snapshot.json` | Keepa 마지막 조회값 (화면은 이 값만 읽음) |
| `data/report_keepa_usage.json` | Keepa 토큰 한도(600)와 사용 기록 |
| `data/report_ab_tests.json` | 실제로 진행한 해결안 A/B 테스트 결과 (지금은 비어 있음) |

- 위젯 `key`, `st.session_state` 키는 `report-`로 시작합니다.
- 다른 탭과 데이터 주고받기: `store_set("report", ...)` / `store_get("다른모듈")`

## 데이터 출처

| 데이터 | 출처 | 상태 |
|---|---|---|
| 경쟁사 정보, 경쟁우위 점수, 인증·규제 체크리스트, 완제품 시험 계획 | `data/common_competitor_seori_202610.csv` (공통, 읽기만) | 사용 중 |
| 독일 시장 지식 (결제, 소비심리, 규제, 시즌 등) | `data/common_germany_knowledge_seori_202610.csv` (공통, 읽기만) | 사용 중 (ID 인용) |
| Amazon.de 경쟁사 현재가·90일 평균·평점·리뷰·순위 | Keepa 스냅샷 | 사용 중 (조회는 확인 후에만) |
| 독일 16개 주 현재 기온 | Open-Meteo (`ui_theme.fetch_state_temperatures`, 공통) | 사용 중 |
| 방문·주문·매출·전환율, 구매 퍼널, 유입 채널 | GA4 | 연결 전 (빈 상태) |
| 해결안 A/B 테스트 | `data/report_ab_tests.json` | 결과 없음 (빈 상태) |

## 화면 구성

| 자리 | 내용 |
|---|---|
| KPI 4개 | GA4 연결 전: 서리 경쟁 포지션 (㎡당 가격, 리뷰 수, 판매 채널, 출시 필수 인증·규제) / GA4 연결 후: 방문, 주문, 전환율, 매출 |
| 내부 요인 | 서리가 경쟁사 대비 부족한 점 (리뷰 0건, 인증·규제 미착수, 완제품 시험 미실시, ㎡당 가격, 판매 채널, 경쟁우위 점수, 여름 전용·물류) + GA4 연결 시 구매 퍼널 |
| 외부 요인 | ⚠️ 위협 (Keepa 경쟁사 가격 인하, 비시즌·현재 기온, Amazon PayPal 불가, 소비심리, 초저가 플랫폼, 친환경 표현 규제) / ✨ 기회 (경쟁사 Q-max 미공개, 에어컨 없는 가구, 경쟁사 품절·가격 인상) |
| 경쟁사 비교 | 경쟁사 DB + Keepa 비교표, Keepa 최신값 조회(확인 PIN), 경쟁우위 항목별 점수, 브랜드별 강점·약점 |
| 유입 채널 (UTM) | GA4 연결 시 채널별 성과 / 광고 링크(UTM) 만들기 |
| 해결안 A/B 테스트 | 실제 결과가 있으면 전환율, 차이, 유의확률(두 비율 z-검정) |
| 🎯 문제 도출 | 핵심 문제 Top 3 (내부 1순위, 외부 위협 1순위, 그다음 순위) + 근거 + 가설 탭 질문, 한 줄 요약, PDF 양식 선택 + 다운로드 |

## 다른 탭에 넘기는 데이터 (`store_get("report")`)

| 키 | 내용 | 쓰는 탭 |
|---|---|---|
| `summary` | 핵심 문제 한 줄 요약 | 홈, 가설 |
| `key_problems` | 핵심 문제 Top 3: `rank`, `type`(내부/외부), `level`, `group`, `title`, `detail`(근거), `question`(가설용 '어떻게 하면 ~할까?') | **② 가설** |
| `problems` | **핵심 문제 Top 3가 맨 앞**, 그다음 내부 요인·외부 위협 (낮음 제외). `title`, `type`(내부/외부), `level`, `group`, `detail` + 가설 탭 선택 필드 `target`, `metric`, `local_context`(독일 DB 근거), `competitor_review`(경쟁사 DB 약점·Keepa 평점, 실제 리뷰 원문 아님) | 홈(주요 문제), **② 가설 (`problems[0]`으로 가설 1개 생성)** |
| `opportunities` | 외부 기회: `title`, `level`, `detail` | 가설, 광고 소재 |
| `seori_profile` | 서리 제품: 제품명, 판매가, ㎡당 가격, 판매 채널, Q-max, 인증, 강점, 약점 | 가설, **③ 광고 소재** |
| `competitor_profiles` | 경쟁사 7곳: 강점, **약점**(→ 우리 홍보 포인트), Q-max, Amazon 현재가·90일 변화·평점·리뷰·재고 | **② 가설**, **③ 광고 소재**(레퍼런스) |
| `marketing_rules` | 독일 광고·상세페이지 표현 규칙 8개 (Sie 통일, 과장어 금지, 체온 표현 금지, Q-max 조건 표기, 친환경 표현 금지, 섬유 성분 표기 등, 독일 DB ID 포함) | **③ 광고 소재** |
| `competitor_signals` | 경쟁사 품절(`in_stock`)·현재가·90일 가격 변화·조회 시각 (Keepa) | **④ 광고 타이밍** (품절 → 광고 빈도 증가) |
| `competitors` | 간단 비교표 (브랜드, 가격, 평점, 리뷰 수, 판매 채널, 재고) | 공통 |
| `funnel_worst`, `utm`, `utm_worst` | GA4 연결 시 퍼널 최저 단계, 유입 채널 성과 (지금은 빈 값) | 광고 타이밍, 광고 소재 |
| `ab_tests` | 실제 A/B 결과 (지금은 빈 값) | 가설 |
| `data_source` | 데이터 출처 표시 | 공통 |

- 홈 탭이 읽는 `yesterday_sales`, `sales_delta`, `sales_7d`는 실제 매출 데이터(GA4)가 없어서 넣지 않습니다 (홈에는 '연결 전'으로 표시).
- 독일 시장 원본 지식(문화, 결제, 페르소나, 응대 템플릿, 검색 키워드)은 공통 파일 `data/common_germany_knowledge_seori_202610.csv`를 직접 읽으면 됩니다.
- 값은 내용이 바뀔 때마다(예: Keepa 새로 조회) 다시 저장됩니다.

## Keepa 사용 규칙 (토큰 한도 600)

- 화면을 열 때는 Keepa를 호출하지 않고 스냅샷만 보여 줍니다.
- 조회: 경쟁사 비교 > 'Keepa 최신값 조회'에서 확인 PIN 입력 + 동의 후 1회 (약 10토큰). `KEEPA_FETCH_PIN`이 없으면 조회 불가.
- 사용량은 `data/report_keepa_usage.json`에 기록하고, 남은 한도가 예상 사용량보다 적으면 막습니다.
- 로컬에서 조회한 뒤 스냅샷·사용량 파일을 커밋하면 배포 앱은 토큰 없이 마지막 값을 보여 줍니다.
- secrets의 report 칸: `KEEPA_API_KEY`, `KEEPA_FETCH_PIN`

## GA4 연결

- secrets의 report 칸: `REPORT_GA4_PROPERTY_ID`, `REPORT_GA4_CREDENTIALS` (requirements: `google-analytics-data`)
- 유입 채널: `sessionSource / sessionMedium / sessionCampaignName` × `sessions, ecommercePurchases, purchaseRevenue`
- 퍼널: 방문 = `sessions`, 이후 `view_item` → `add_to_cart` → `begin_checkout` → `purchase` (eventCount)
- 기간: 최근 30일 vs 그 전 30일, 1시간 캐시
