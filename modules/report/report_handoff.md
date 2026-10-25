# ① 문제 분석 → 다음 탭 데이터 전달 구조

대상: ② 가설, ③ 광고 소재, ④ 광고 타이밍, 홈 담당자 · 작성: report 담당 · 2026-10-24

## 한눈에 보기

```text
[원본 데이터]                          [① report 모듈]                     [저장]                         [다른 탭]
data/common_competitor_seori_202610.csv ┐
data/common_germany_knowledge_...csv    ├─> report_data.py ─> report_page.py ─> store_set("report", {...}) ─> store_get("report")
modules/report/data/*.json·csv          │   (분석·계산)        (화면 + 저장)       Supabase 표 common_store       홈 · ② · ③ · ④
Keepa API(마지막 조회값) · Open-Meteo   ┘                                         (key = "report")
```

- ① 탭을 열면 분석 결과를 `store_set("report", ...)`로 저장합니다. 내용이 바뀔 때만 다시 저장합니다.
- 다른 탭은 `from common.common_store import store_get` 후 `report = store_get("report")`로 읽습니다. ① 탭을 한 번도 열지 않았으면 `None`일 수 있으니 꼭 확인하세요.
- 값은 Supabase `common_store` 표에 저장되어, 새로고침하거나 다른 사람이 접속해도 같은 값을 봅니다.

## 탭별로 쓰면 되는 키 (`version: report-v2`, 2026-10-25 정리)

**지금 다른 탭이 읽는 키** (모양을 바꾸지 않음)

| 키 | 읽는 탭 | 내용 |
|---|---|---|
| `problems` | 홈, ② 가설 | 문제 목록. **맨 앞이 가장 중요한 문제**. 각 항목: `title`, `type`(내부/외부), `level`, `group`, `detail`, `target`, `metric`, `local_context`, `competitor_review` (검색어 문제는 `sqp_type`, `query` 추가) |
| `summary` | ② 가설 | 핵심 문제 한 줄 요약 (Top 3와 같은 순서) |
| `sqp` | ② 가설, ③ 광고 소재 | 검색어 클릭 분석: `query`, `imp_share`, `click_share`, `ratio`, `kpi_goal`, `listing`(우리 상품 메인 이미지·가격) 등 (노출·클릭은 **가상 SQP**) |
| `ab_test` | 홈 | A/B 결과 `{name, a:{ctr,cvr}, b:{ctr,cvr}, summary}` · ① 탭에 결과 파일(CSV)을 올렸을 때만, 없으면 `None` |

**다른 탭에서 쓰도록 준비한 키**

| 키 | 쓸 탭 | 내용 |
|---|---|---|
| `analyzed_on`, `previous` | ① (내부용) | 분석한 날, 이전 분석의 날짜·데이터 기준·1·2순위 제목 (이전 분석 대비 문구용) |
| `key_problems` | ② 가설 | 핵심 문제 Top 3 (검색어·내부·외부를 섞어 위험도 → 심각도 점수 순, `severity`: score·data·urgency·gap·basis) + 가설 질문 `question` · `problems` 앞 3개와 같은 순서 |
| `opportunities` | ② 가설 | 외부 기회 |
| `review_analysis` | ② 가설 | 리뷰 문제 근거·목표 (`seori`, `leader`, `five_star_needed`, `findings`, `metric`, `target`, `rule`) |
| `seori_profile` | ③ 광고 소재 | 서리 제품·가격(SleepCOOL 실적)·판매 채널·Q-max·인증(`certs`)·시험(`tests`)·강점·약점·Amazon 수수료 추정(`amazon_fees`)·체온 광고 규칙(`body_temp_rule`) |
| `ad_claims` | ③ 광고 소재 | **광고에 넣을 서리 문구**(독일어·한국어·필수 표기), 금지 표현(`forbidden`), AI 광고 장면(`allowed_scenes`) |
| `marketing_rules` | ③ 광고 소재 | 독일 광고 표현 규칙 8개 |
| `competitor_profiles` | ② 가설, ③ 광고 소재 | 경쟁사(Novilla·Mara Vital) 강점·약점·Keepa 값·상세페이지 특징 문구(`listing_features`) |
| `competitor_signals` | ④ 광고 타이밍 | 경쟁사 품절·현재가·가격 변화·쿠폰(`coupon`)·월 구매 배지(`monthly_sold`) |
| `competitor_ranking` | 공통 | 냉감패드 실적 순위: `rank`(냉감 전용끼리, 제외 상품은 None), `brand`, `type`, `sales_signal_365`, `summer_rank_median`, `reviews`, `monthly_sold` |
| `data_rules` | 공통 | **지표별 비교 기준·출처·기준일·신선도·구분(실제/가정/가상)**. 숫자를 쓸 때 함께 표시해 주세요 |
| `version`, `as_of` | 공통 | 데이터 모양 버전, 데이터 기준 시점 |
| `ab_upload` | (① 탭 자체 보관용) | 올린 A/B 결과 파일 원본 분석 — 다른 탭은 `ab_test`를 쓰세요 |

**뺀 키** (읽는 탭이 없고 겹치거나 비어 있음): `competitors`(→ `competitor_profiles`), `data_source`(→ `data_rules`), `cooling_sales`(→ `competitor_ranking`, 16KB → 순위 칸만), `ab_tests`·`ab_daily`(비어 있음), `seori_profile` 안의 `data_check`·`finished_qmax_ref`·`ad_check`·`body_temp` 세부(① 화면에만, 광고 문구는 `ad_claims`)

**나중에 추가할 키**: GA4 연결 후 `funnel_worst`, `utm`, `utm_worst`, `kpi`, `yesterday_sales`, `sales_delta`, `sales_7d` (홈이 기다리는 매출 값) · ③ 탭 저장 기능이 생기면 `ab_daily`

> 홈 탭은 ① 탭보다 먼저 그려져서, 같은 접속에서 처음 열 때는 이전에 저장된 값을 보여 줍니다. Supabase에 연결되면 저장된 값을 바로 읽습니다.

## 매일 아침 자동 갱신 (Keepa, 설정으로 켜기)

- 구매 배지(월 구매량), 1년 판매 신호, 가격, 리뷰, 재고는 Keepa 값이라, 아침에 자동으로 새로 받아야 그날 분석이 최신이 됩니다.
- secrets에 `KEEPA_AUTO_DAILY = "on"`을 넣으면 **매일 한국 08:00 이후 첫 접속 때 1번** 경쟁사 3곳(Novilla·Mara Vital·서리=SleepCOOL)을 조회합니다. 약 6토큰, 하루 최대 10토큰, 프로젝트 한도(600)를 넘으면 하지 않습니다.
- 기본은 꺼짐. 켜면 그 뒤 분석(문제·요인·KPI·리뷰·경쟁사 신호)은 화면을 열 때 새 값으로 다시 계산되어 다른 탭에도 저장됩니다.
- 주의: Streamlit Cloud에서는 파일 저장이 재시작 때 사라질 수 있어, 배포 환경에서 계속 쓰려면 결과를 Supabase 표(`report_...`)에 저장하는 작업이 추가로 필요합니다.

## DB 파일 (루트 `data/`, 읽기는 누구나)

| 파일 | 내용 | 다른 탭에서 쓸 곳 |
|---|---|---|
| `data/common_competitor_seori_202610.csv` | 경쟁사 DB (여러 시트를 `원본시트` 열로 구분): 경쟁사DB, 경쟁우위 비교, **체감 vs 실제 체온**, SEORI 시험·표시, 출처 등 | ③ AI 광고: '체감 vs 실제 체온' 시트의 각 행 `해석` 끝 **"AI 광고:"** 규칙과 주석 6~8 (써도 되는 표현·금지 표현·장면) |
| `data/common_germany_knowledge_seori_202610.csv` | 독일 시장 지식 DB (문화, 결제, 광고 표현 규칙 LNG-·LAW- 등) | ③ 광고 문구, ④ 시즌·날씨 |

- 경쟁사 순위는 **냉감 전용 상품 + 1년 판매 신호(Keepa) 기준** (2026-10-25): 1위 Novilla, 2위 Mara Vital, 3위 서리(가정: **SleepCOOL 실적**). RIBECO·Herlag는 양면(2-in-1) 제품, Traumnacht는 비냉감 실적 혼재라 순위에서 제외.
- 서리 = **2018년 독일 시장 진입, 현재 여름 전용 제품**으로 설정. 판매 실적(리뷰 31건·평점 3.8·판매 순위)은 SleepCOOL 값, 판매가는 서리 자체 €64.99(90x200, 모든 탭 같은 값), 제품명·소재·Q-max·인증은 서리 기획.
- 서리 Q-max는 완제품 0.207 W/㎠ (온도차 10℃, JIS L 1927)로 가정.

## report 폴더 파일 (참고, 수정은 report 담당만)

| 파일 | 역할 |
|---|---|
| `report_page.py` | 화면 + `store_set("report")` 저장 (`report_save_store`) |
| `report_data.py` | 모든 데이터를 모아 분석 (`report_load_data`) |
| `report_competitor.py` | 경쟁사 DB 읽기, 내부/외부 요인, 핵심 문제, 가설 탭용 `problems` |
| `report_sqp.py`, `report_sqp_view.py` | 검색어 클릭 분석 (가상 SQP) |
| `report_review.py` | 리뷰 분석, 냉감패드 실적 |
| `report_ab.py` | ③ 탭 A/B 결과 아침 분석, CSV 업로드 분석 |
| `report_keepa.py` | Keepa 조회 (토큰 한도 600, PIN 필요) |
| `report_pdf.py`, `report_download.py` | PDF 리포트 3종 |
| `data/report_seori_assumption_202610.json` | 서리 가정 (Q-max·인증·시험·광고 문구 `ad_claims`) |
| `data/report_keepa_*.json` | Keepa 마지막 조회값·상세·사용량 |
| `report.md` | 모듈 설명 (키 전체 설명은 '다른 탭에 넘기는 데이터' 표) |

## 주의

- 데이터 모양이 바뀌면 report 담당이 이 문서와 `report.md`를 함께 고칩니다. 새로 필요한 키가 있으면 report 담당에게 요청해 주세요.
- 노출·클릭(검색어 성과)은 **가상 데이터**, 경쟁 제품·가격·리뷰는 **Keepa 실제**, 기온은 **DWD 실제**입니다. 발표 때 구분해 주세요.
