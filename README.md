# 📊 마케팅 솔루션 대시보드

> 판매 데이터를 분석해 문제를 찾고 → 가설을 세우고 → 광고 매체와 솔루션을 만들고 → 날씨에 맞춰 광고 타이밍까지 추천하는 마케팅 대시보드

이 문서는 프로젝트 소개, 기술 구조, 파일 구조, 실행 및 배포 방법을 정리한 것입니다.
**작업 규칙(이름 짓기, 충돌 방지, Git 사용법)은 [RULES.md](RULES.md)에 있습니다.** 작업 전에 두 문서를 모두 읽어 주세요.

---

## 1. 기술 구조

| 구분 | 방식 |
|---|---|
| **만들기** | **Streamlit** — Python 하나로 화면과 기능을 한 번에 만듭니다 (HTML/JS/별도 서버 없음) |
| **데이터** | **Supabase**에 저장하고, 앱에서 `st.connection`으로 불러와 쓰고, 바뀐 내용은 다시 Supabase에 저장 |
| **배포** | GitHub `main`에 올리면 **Streamlit Community Cloud**가 자동으로 배포 |
| **비밀값** | API 키와 Supabase 주소는 **`.streamlit/secrets.toml`(내 컴퓨터)** 과 **Streamlit Cloud의 Secrets(배포)** 에만 넣기 |

```
[내 컴퓨터]  streamlit run app.py ──┐
                                    ├── st.connection("supabase") ──▶ [Supabase DB]
[Streamlit Cloud]  main 자동 배포 ──┘         (읽기 / 저장)
```

| 구분 | 사용 기술 |
|---|---|
| 화면 + 기능 | Python, Streamlit |
| 데이터베이스 | Supabase (`st-supabase-connection`) |
| 배포 | Streamlit Community Cloud |
| AI | OpenAI (`openai`): 변수 도출, 프롬프트 다듬기, 사진 초안, 스토리보드·번역 (키가 없으면 규칙 기반으로 대신 만듦) |
| 외부 API | 날씨: Open-Meteo, DWD · 경쟁사: Keepa (Amazon.de) · 영상 초안: Higgsfield (`higgsfield-client`) · 유입 분석: GA4 (없으면 샘플) |
| 문서·영상 처리 | `fpdf2`, `matplotlib` (PDF 보고서), `plotly` (그래프), `imageio-ffmpeg` (영상 자막 넣기) |
| 협업 | GitHub, GitHub Desktop, VS Code, Notion |

---

## 2. 기능 구성

| 순서 | 탭 이름 | 하는 일 | 경쟁사 관련 기능 | 모듈 코드 |
|---|---|---|---|---|
| 🏠 | 홈 | 독일 시간, 지구본(도시 기온), 지금 할 일 알림, 다른 탭 요약 | - | `home` |
| ① | 문제 분석 | 검색어 클릭 분석, 경쟁 포지션·리뷰 분석, 가설 재료 정리, PDF 리포트 다운로드 | Keepa 경쟁사 가격·평점·재고, 내부/외부 요인 분석 | `report` |
| ② | 가설 수립 | 문제 해결 가설 제안 (현지 특성 반영), 선택한 가설 PDF | 경쟁사 부정 리뷰를 우리 홍보 포인트로 활용 | `hypothesis` |
| ③ | 매체 제작 | 하위 탭 4개: 가설에서 변수 도출 → A/B 소재 준비(프롬프트 만들기·AI 다듬기) → 사진·영상 초안 제작 → 외주 정리(zip) | 광고 소재 레퍼런스 (따라 하기 / 피하기), 경쟁사 부정 리뷰 활용 | `media` |
| ④ | 날씨 광고 타이밍 | 권역 날씨에 따른 광고(메타, 아마존) 예산·채널 추천, PDF 보고서 | 폭염 + 경쟁사 품절 → 광고 빈도 증가 | `weather` |

- 화면 구성: 화면 맨 왼쪽 **세로 아이콘 줄**에 홈, ①~④ 탭이 작업 순서대로 있고, 누르면 해당 화면으로 바뀝니다. (탭 이름과 순서는 `common/common_layout.py`의 `LAYOUT_TABS`, 모양은 `common/common_style.css`, 공통 디자인은 `design.md`·`ui_theme.py`)
- 탭끼리는 `store_set` / `store_get`(Supabase `common_store`)으로 값을 넘깁니다: ① → ② → ③, 그리고 홈이 각 탭 값을 읽어 요약합니다.
- **모듈 코드**는 파일명, 폴더명, 함수명, 위젯 key, class, Supabase 표 이름 앞에 붙이는 이름입니다.
- 담당자 기록은 노션에 정리합니다.

---

## 3. 파일 구조

```
miniproject2/
├── README.md                       # 프로젝트 소개, 구조, 실행/배포 (PM)
├── RULES.md                        # 팀 작업 규칙 (PM)
├── CLAUDE.md                       # AI(Claude Code) 공통 작업 지침 (PM)
├── design.md                       # 디자인 가이드 (색, 카드 배치)
├── 문제 시나리오.md                 # 아마존 클릭률 문제 시나리오 (①·② 분석 기준)
├── app.py                          # ⭐ 시작 파일: streamlit run app.py (PM)
├── ui_theme.py                     # 공통 디자인 함수 (테마, 색, 지도 배치)
├── make_germany_image.py           # assets/germany.png 만드는 스크립트 (필요할 때만 실행)
├── requirements.txt                # 라이브러리 목록 (모두 한 줄 추가 가능)
├── .gitignore                      # GitHub에 올리지 않을 파일 목록 (PM)
├── .editorconfig                   # 들여쓰기, 줄바꿈 통일 설정 (PM)
│
├── assets/                         # 독일 지도 (germany.png, germany_states.geojson)
│
├── .streamlit/
│   ├── config.toml                 # 테마 색상 등 공통 설정 (PM, GitHub에 올라감)
│   ├── secrets.toml.example        # 비밀값 이름 예시 (모두 한 줄 추가 가능)
│   └── secrets.toml                # 🔐 진짜 비밀값 (각자 컴퓨터에만, GitHub에 안 올라감)
│
├── common/                         # 공통 기능 (PM)
│   ├── common_layout.py            # 탭 목록(LAYOUT_TABS), CSS 적용
│   ├── common_db.py                # Supabase 읽기 / 저장 (db_read, db_insert ...)
│   ├── common_store.py             # 탭끼리 데이터 주고받기 (store_get, store_set)
│   ├── common_style.css            # 색상 변수, 카드 디자인
│   ├── fonts/                      # 공통 폰트 SUIT (화면, PDF, 영상 자막)
│   └── images/                     # 같이 쓰는 이미지 (로고, 탭 아이콘)
│
├── data/                           # 같이 쓰는 원본 데이터: 경쟁사 DB, 독일 DB (PM, 수정 금지)
│
└── modules/                        # ⭐ 각자 자기 폴더만 수정
    │                               # 모든 모듈 폴더에 모듈코드.md(설명), CLAUDE.md(AI 안내), 모듈코드_prompt.md(프롬프트 기록),
    │                               # 모듈코드_style.css(디자인), images/, data/ 가 있습니다
    ├── home/                       # 홈
    │   ├── home_page.py            # 화면 + 기능 (home_render 함수 하나)
    │   ├── home_data.py            # 다른 탭 값 읽기, 지금 할 일 규칙
    │   └── home_globe.py           # 독일 중심 지구본 + 도시 기온
    │
    ├── report/                     # 1. 문제 분석
    │   ├── report_page.py
    │   ├── report_data.py          # 데이터 불러오기
    │   ├── report_sqp*.py          # 검색어 클릭 분석 (더미 SQP + Keepa·DWD)
    │   ├── report_competitor.py    # 경쟁사 비교, 내부/외부 요인
    │   ├── report_keepa.py         # Keepa 조회 (PIN·한도 확인)
    │   ├── report_review.py        # 리뷰 분석
    │   ├── report_plan.py          # ②에 넘길 가설 재료
    │   ├── report_image.py         # 이미지로 고칠 수 있는 문제
    │   ├── report_ga4.py           # GA4 유입·퍼널 (없으면 샘플)
    │   ├── report_ab.py            # A/B 결과 아침 분석
    │   └── report_download.py, report_pdf.py   # PDF 리포트
    │
    ├── hypothesis/                 # 2. 가설 수립
    │   ├── hypothesis_page.py
    │   ├── hypothesis_scenario.py  # 검색어 클릭 문제 가설 근거·KPI
    │   ├── hypothesis_pdf.py       # ①요약 + ②가설 PDF
    │   └── hypothesis_test.py      # 회귀 테스트
    │
    ├── media/                      # 3. 매체 제작 (3단계로 나눠 개발)
    │   ├── media_page.py           # 하위 탭 4개를 만들고 단계별 화면 함수를 부름
    │   ├── media_handoff.py        # 단계 사이 데이터 주고받기
    │   ├── media_variable.py       # 1단계 ①: 가설에서 변수 도출 (+ _ai.py, _pdf.py)
    │   ├── media_stage2/           # 2단계 ②: A/B 소재 준비 (프롬프트 만들기 + AI 다듬기)
    │   └── media_stage3/           # 3단계 ③ 사진·영상 초안(OpenAI, Higgsfield) → ④ 외주 정리(zip)
    │
    └── weather/                    # 4. 날씨 광고 타이밍
        ├── weather_page.py
        ├── weather_data.py         # 날씨 불러오기, 추천 계산
        └── weather_report.py       # PDF 보고서
```

> 폴더마다 있는 빈 `__init__.py`는 Python이 `modules.report.report_page`처럼 파일을 찾을 수 있게 해 주는 표시입니다. 지우지 않습니다.

### 이전 구조에서 바뀐 점

| 이전 (HTML + FastAPI) | 지금 (Streamlit) |
|---|---|
| `index.html` + `common/common_layout.js` | `app.py` + `common/common_layout.py` |
| `모듈코드_main.html` + `모듈코드_script.js` + `모듈코드_server.py` | **`모듈코드_page.py` 하나** |
| `common/common_api.js` (`Api.get/post`) | 필요 없음 (화면과 기능이 같은 Python 파일) |
| `common/common_store.js` (localStorage) | `common/common_store.py` (세션 + Supabase) |
| `server/shared/shared_ai.py` | 각 모듈의 `모듈코드_ai.py` (OpenAI를 직접 부름) |
| `server/requirements.txt` | `requirements.txt` (맨 위 폴더) |
| `.env` / `.env.example` | `.streamlit/secrets.toml` / `.streamlit/secrets.toml.example` |
| `uvicorn server.main:app --reload` | `streamlit run app.py` |

---

## 4. 처음 시작하기 (내 컴퓨터)

```bash
# 1) 가상환경 만들기 (프로젝트 맨 위 폴더에서, 처음 한 번)
python -m venv venv
venv\Scripts\activate            # Mac: source venv/bin/activate
pip install -r requirements.txt

# 2) 비밀값 파일 만들기 (처음 한 번)
copy .streamlit\secrets.toml.example .streamlit\secrets.toml     # Mac: cp .streamlit/secrets.toml.example .streamlit/secrets.toml
#    → secrets.toml을 열어 PM에게 받은 진짜 키와 Supabase 주소를 넣습니다

# 3) 실행
streamlit run app.py
#    → 브라우저에서 http://localhost:8501 이 자동으로 열립니다
#    → 파일을 저장하면 화면 오른쪽 위의 "Rerun"을 눌러 바로 확인할 수 있습니다
```

> Supabase 값을 아직 넣지 않아도 화면은 열립니다. 데이터 읽기/저장만 동작하지 않습니다.

---

## 5. 데이터: Supabase

### 5-1. 연결 방식

앱은 `st.connection("supabase")`으로 Supabase에 연결합니다. 주소와 키는 `secrets.toml`의 `[connections.supabase]`에서 자동으로 읽기 때문에 **코드에는 주소나 키를 쓰지 않습니다.**

```toml
# .streamlit/secrets.toml (맨 아래)
[connections.supabase]
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "Supabase > Project Settings > API 의 anon(public) 키"
```

### 5-2. 읽고, 쓰고, 다시 저장하기

모든 모듈은 `common/common_db.py`의 함수만 사용합니다.

```python
# modules/report/report_page.py
import pandas as pd
import streamlit as st

from common.common_db import db_read, db_insert, db_update


def report_render():
    rows = db_read("report_sales", month="2026-10")       # 읽기 (10분 캐시, ttl=0이면 매번 새로)
    df = pd.DataFrame(rows)

    edited = st.data_editor(df, key="report-editor-sales")   # 화면에서 수정
    if st.button("저장", key="report-btn-save"):
        for row in edited.to_dict("records"):
            db_update("report_sales", {"amount": row["amount"]}, id=row["id"])   # 다시 저장
        st.success("저장했습니다.")
```

| 함수 | 하는 일 |
|---|---|
| `db_read(표, ttl=600, 열=값 ...)` | 조건에 맞는 행 읽기 (결과를 ttl초 동안 캐시) |
| `db_insert(표, 행 또는 행 리스트)` | 행 추가 |
| `db_upsert(표, 행 또는 행 리스트)` | 기본 키가 같으면 수정, 없으면 추가 |
| `db_update(표, 바꿀 값, 열=값 ...)` | 조건에 맞는 행 수정 (조건 필수) |
| `db_delete(표, 열=값 ...)` | 조건에 맞는 행 삭제 (조건 필수) |

> 저장 함수를 부르면 캐시가 자동으로 비워져서, 다음 읽기에서 바뀐 값이 바로 보입니다.

### 5-3. 표(테이블) 만들기

- 표는 Supabase 웹사이트의 **Table Editor** 또는 **SQL Editor**에서 만듭니다.
- 표 이름은 **`모듈코드_내용`** (예: `report_sales`, `weather_forecast`). 공통 표는 `common_`으로 시작합니다.
- 새 표를 만들면 노션에 표 이름과 열 구성을 기록합니다.

**처음 한 번 (PM): 탭끼리 데이터를 주고받는 공통 표**

```sql
create table common_store (
  key text primary key,
  value jsonb,
  updated_at timestamptz default now()
);
```

> Supabase는 기본으로 RLS(행 보안)가 켜져 있어서, anon 키로 읽고 쓰려면 표마다 정책(Policy)을 추가해야 합니다.
> 팀 내부용이면 Table Editor > 표 선택 > **Add RLS policy**에서 읽기/쓰기를 허용하는 정책을 만듭니다.

---

## 6. 비밀값 관리 🔐

| 파일 / 위치 | 내용 | GitHub에 올라가나요? |
|---|---|---|
| `.streamlit/secrets.toml` | **진짜 API 키, Supabase 주소/키** (내 컴퓨터용) | ❌ 절대 안 올라감 (`.gitignore`에 등록) |
| `.streamlit/secrets.toml.example` | 키 **이름**과 더미 값만 | ✅ 올라감 (팀원 안내용) |
| Streamlit Cloud > App settings > **Secrets** | 배포된 앱이 쓰는 진짜 값 (`secrets.toml`과 같은 내용) | - (PM만 수정) |

코드에서는 이름으로만 불러옵니다.

```python
import streamlit as st

API_KEY = st.secrets["AI_API_KEY"]          # O
# API_KEY = "sk-진짜키12345"                 # X : 키가 GitHub에 올라감
```

새 키를 추가하는 방법은 [RULES.md › 4. 비밀값 관리](RULES.md#4-비밀값-관리-)를 따릅니다.

---

## 7. 배포: Streamlit Community Cloud

**GitHub `main`에 합쳐지면 자동으로 배포됩니다.** 따로 서버를 켜거나 배포 명령을 실행하지 않습니다.

### 처음 한 번 설정 (PM)

1. [share.streamlit.io](https://share.streamlit.io)에 GitHub 계정으로 로그인
2. **Create app** → 저장소 `miniproject222/miniproject2`, 브랜치 `main`, 시작 파일 `app.py` 선택
3. **Advanced settings**
   - Python 버전: `3.11` (팀 확정 버전과 맞춤)
   - **Secrets**: 내 `secrets.toml` 내용을 그대로 붙여 넣기
4. **Deploy** → 발급된 주소(`https://○○○.streamlit.app`)를 노션과 이 문서에 기록

### 이후

- `dev` → `main` PR이 합쳐지면 1~2분 안에 자동으로 새 버전이 올라갑니다.
- `requirements.txt`가 바뀌면 라이브러리도 자동으로 다시 설치됩니다.
- 새 비밀값이 생기면 **PM이 Streamlit Cloud > App settings > Secrets에도 추가**해야 배포된 앱에서 동작합니다.
- 배포가 실패하면 Streamlit Cloud 앱 화면 오른쪽 아래 **Manage app**에서 로그를 확인합니다.

배포 주소: (배포 후 기재)

---

## 8. 진행 현황

- [x] PM: 뼈대(빈 파일 구조, app.py, common/) 올리기
- [x] Streamlit + Supabase 구조로 전환
- [x] PM: Supabase 프로젝트 생성, `common_store` 표 만들기
- [x] PM: Streamlit Community Cloud 연결 (main 자동 배포)
- [x] 홈 (`home`)
- [x] 1. 문제 분석 (`report`)
- [x] 2. 가설 수립 (`hypothesis`)
- [x] 3. 매체 제작 (`media`)
- [x] 4. 날씨 광고 타이밍 (`weather`)
- [x] 전체 통합 → `main` 반영 (2026-10-27)
- [ ] 최종 발표

---

## 📝 변경 이력

| 날짜 | 내용 | 작성자 |
|---|---|---|
| 2026-10-21 | README 초안 작성 | 000 |
| 2026-10-22 | 기능 구성, 파일 구조 변경 (6개 모듈), Git 규칙 통합, 충돌 방지 규칙 추가 | 000 |
| 2026-10-22 | 파일 구조 정리: routers/, assets/, data/processed/ 삭제 → 모듈별 서버, 이미지, 데이터를 각 모듈 폴더로 이동 | 000 |
| 2026-10-23 | 보안 및 환경 변수 관리(.env, .env.example 작성 예시) 추가, 파일 및 코드 작성 규칙 추가 | 000 |
| 2026-10-23 | 모듈 설명 파일 이름 변경 (`README.md` → `모듈코드.md`) | 000 |
| 2026-10-23 | **Streamlit + Supabase + Streamlit Community Cloud 구조로 전환**: HTML/JS/FastAPI 삭제, 모듈별 `모듈코드_page.py`로 통합, `.env` → `.streamlit/secrets.toml`, 팀 규칙은 RULES.md로 정리 | 000 |
| 2026-10-23 | `solution` 모듈 삭제 → `media` 모듈로 합침 (`media_solution.py`), 탭 5개(홈, ①~④)로 정리 | 000 |
| 2026-10-24 | `media` 3단계 분리 반영: `media_solution.py` 삭제, `media_handoff.py`·`media_variable.py`·`media_ab.py`·`media_stage2/`·`media_stage3/` 추가, ③ 탭 설명 수정 | 000 |
| 2026-10-24 | `media` 흐름 변경: 2단계 프롬프트 만들기, 3단계 다듬기·매체 제작·외주 준비 (판정·솔루션 제안은 흐름에서 뺌), `.gitignore`에 `.claude/settings.local.json` 추가 | 000 |
| 2026-10-24 | `media` 단계 사이 값을 단계 폴더의 JSON 파일로 저장 (푸시·풀로 다른 컴퓨터에서도 이어짐) | 000 |
| 2026-10-25 | `media` 하위 탭 5개로 변경: AI 다듬기를 2단계로, 3단계는 ④ 사진·영상 초안(스토리보드 포함) + ⑤ 외주 정리 | 000 |
| 2026-10-25 | `media` 단계 사이 값을 Supabase(`store("media")`의 `handoff`)에 저장, 단계마다 넘기기 버튼을 눌러야만 저장 (JSON 파일 저장 중단), `store_get(key, fresh=True)` 추가 | 000 |
| 2026-10-27 | 최종 반영: 사용 기술(OpenAI, Keepa, Higgsfield, Open-Meteo·DWD, GA4), 탭 이름과 ③ 하위 탭 4개, 파일 구조(`common_ai.py` 삭제, `design.md`·`ui_theme.py`·`assets/`·`common/fonts/` 등 추가), `develop` → `dev`, 진행 현황 갱신 | 000 |
