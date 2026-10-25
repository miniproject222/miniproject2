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

## 탭별로 쓰면 되는 키

| 쓰는 탭 | 키 | 내용 |
|---|---|---|
| **② 가설** | `problems` | 문제 목록. **맨 앞이 가장 중요한 문제**. 각 항목: `title`, `type`(내부/외부), `level`, `group`, `detail`, `target`, `metric`, `local_context`, `competitor_review`. 검색어 문제는 `sqp_type`, `query`도 있음 |
| ② 가설 | `key_problems` | 핵심 문제 Top 3 + 가설 질문 `question` ('어떻게 하면 ~할까?') |
| ② 가설 | `summary` | 핵심 문제 한 줄 요약 |
| ② 가설·③ | `sqp` | 검색어 클릭 분석: 메인 검색어, 노출·클릭 점유율, 배수, 놓친 클릭, 우리 상품, 경쟁 제품(Keepa) 등 (노출·클릭은 **가상 SQP**) |
| ② 가설 | `review_analysis` | 리뷰 분석: 리뷰 수·평점 비교, 목표(`target`), 근거(`findings`) |
| ② 가설 | `opportunities` | 외부 기회 |
| **③ 광고 소재** | `ad_claims` | **광고에 넣을 서리 문구** (독일어·한국어·필수 표기), 금지 표현(`forbidden`), AI 광고 장면(`allowed_scenes`) |
| ③ 광고 소재 | `marketing_rules` | 독일 광고 표현 규칙 8개 (체온 표현 금지, Q-max 조건 표기 등) |
| ③ 광고 소재 | `seori_profile` | 서리 제품 정보: 가격, Q-max 0.207(10℃), 인증, 시험, 강점·약점, 체감 vs 실제 체온, 광고 가능 여부(`ad_check`) |
| ③ 광고 소재 | `competitor_profiles` | 경쟁사 강점·약점, 상세페이지 특징 문구(`listing_features`) → 레퍼런스 |
| **④ 광고 타이밍** | `competitor_signals` | 경쟁사 품절·현재가·90일 가격 변화·쿠폰 기록(`coupon`)·월 구매 배지 |
| ④·③ | `utm`, `utm_worst`, `funnel_worst` | GA4 연결 후 채널·퍼널 성과 (지금은 빈 값) |
| 공통 | `competitors` | 간단 비교표 (브랜드, 가격, 평점, 리뷰 수, 판매 채널, 재고) |
| 공통 | `cooling_sales` | 냉감패드 실적만 (여름 순위, 판매 신호) |
| 공통 | `ab_daily` | **[보류] 지금은 None** · ③ 탭 A/B 결과 아침 자동 분석 (③ 탭 저장 기능 완성 후 켬) |
| 공통 | `ab_upload` | 직접 올린 A/B 결과 파일(CSV) 분석 |
| 공통 | `data_source` | 데이터 출처 표시 문구 |
| 공통 | `data_rules` | **지표별 비교 기준·출처·기준일·신선도·구분(실제/가정/가상)**. 다른 탭에서 숫자를 쓸 때 이 기준을 함께 표시해 주세요 |

> 홈 탭이 기다리는 `yesterday_sales`, `sales_7d`, `kpi`, `ab_test`는 실제 매출(GA4)이 없어 **아직 넣지 않습니다** (홈은 '연결 전'으로 표시).

## ③ → ① 으로 받는 값 (③ 담당자 요청, **현재 보류**)

①은 매일 아침(한국 08:00 이후 첫 접속) ③ 탭 결과를 읽어 A/B를 분석하도록 만들어 두었지만, ③ 탭 저장 기능이 아직 없어 **주석으로 꺼 두었습니다** (`report_data.py`의 [보류]). ③ 탭에서 아래 모양으로 저장하면 켭니다.

```python
store_set("media", {
    "ab_result": {"source": "실제", "period": "...", "query": "kühlende matratzenauflage", "market_ctr": 0.03,
                  "variants": [{"name": "A", "desc": "...", "impressions": 0, "clicks": 0, "sessions": 0, "units": 0, "orders": 0},
                               {"name": "B", "desc": "...", "impressions": 0, "clicks": 0, "sessions": 0, "units": 0, "orders": 0}],
                  "cac": {"before": {"spend": 0, "new_to_brand_orders": 0}, "after": {"spend": 0, "new_to_brand_orders": 0}}},
    "utm": [{"source": "google", "medium": "cpc", "campaign": "...", "sessions": 0, "orders": 0, "revenue": 0}],
    "updated_at": "2026-10-25 07:30",
})
```

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
- 서리 = **2018년 독일 시장 진입, 현재 여름 전용 제품**으로 설정. 판매 실적(가격 €89.90·리뷰 31건·평점 3.8·판매 순위)은 SleepCOOL 값, 제품명·소재·Q-max·인증은 서리 기획.
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
