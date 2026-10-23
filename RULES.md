# 📏 팀 규칙 (RULES)

이 문서는 **각자 VS Code에서 작업한 코드를 GitHub에서 합칠 때 오류가 나지 않도록** 지킬 규칙입니다.
프로젝트 소개, 기술 구조, 파일 구조, 실행/배포 방법은 [README.md](README.md)를 확인하세요.

작업 전에 한 번 끝까지 읽어 주세요. 규칙이 바뀌면 이 문서를 먼저 고치고 팀에 공유합니다.

---

## 1. 누가 어떤 파일을 수정하나요.?

| 구분 | 수정하는 곳 |
|---|---|
| **팀원** | **`modules/내모듈/` 하나만** (화면, 기능, 디자인, 이미지, 데이터 전부) |
| **PM** | `modules/` 밖의 전부 (`app.py`, `common/`, `.streamlit/config.toml`, `data/`, 설정 파일, `README.md`, `RULES.md`), Supabase 공통 표, Streamlit Cloud 설정 |
| **모두 (한 줄 추가만)** | `requirements.txt` → [6-5. 개발 환경 통일](#6-5-개발-환경-통일), `.streamlit/secrets.toml.example` → [4. 비밀값 관리](#4-비밀값-관리-) 참고 |

> 공통 파일에 기능이 필요하면 직접 고치지 말고 PM에게 요청합니다.

**내 폴더 안의 구성** (report 예시)

```
modules/report/
├── __init__.py             # 지우지 않기 (빈 파일)
├── report.md               # 모듈 설명
├── report_page.py          # 화면 + 기능 (report_render 함수 하나)
├── report_style.css        # 디자인
├── report_download.py      # (선택) 기능이 길어지면 report_xxx.py로 나눠도 됩니다
├── images/                 # report에서만 쓰는 이미지
└── data/                   # report에서만 쓰는 데이터
```

- 내 탭에서만 쓰는 이미지와 데이터는 **내 폴더 안의 `images/`, `data/`**에 넣습니다.
- 여러 탭이 같이 쓰는 이미지는 `common/images/`, 같이 쓰는 원본 데이터는 루트 `data/`에 있습니다. (PM 관리, 읽기만 가능)
- 계속 쌓이거나 수정되는 데이터(결과, 사용자가 입력한 값)는 파일이 아니라 **Supabase 표**에 저장합니다.

**모듈 코드**

| 탭 | 모듈 코드 | 폴더 |
|---|---|---|
| 홈 | `home` | `modules/home/` |
| 1. 분석 리포트 | `report` | `modules/report/` |
| 2. 가설 수립 | `hypothesis` | `modules/hypothesis/` |
| 3. 매체 제작 | `media` | `modules/media/` |
| 3-1. 솔루션 제안 | `solution` | `modules/solution/` |
| 4. 날씨 광고 타이밍 | `weather` | `modules/weather/` |

모듈 코드는 파일명, 함수명, 위젯 key, class, Supabase 표 이름 앞에 붙이는 이름입니다. **이름이 겹치지 않게 해 주는 가장 중요한 규칙**입니다.

---

## 2. 이름 짓기 규칙

### 2-1. 파일명

- **영어 소문자 + 언더바(`_`)**, 그리고 **모듈 코드로 시작**합니다.
- 한글, 띄어쓰기, `_최종`, `_v2` 같은 버전 표시는 쓰지 않습니다. 버전은 Git이 관리합니다.

| O | X |
|---|---|
| `report_chart.py` | `chart.py`, `Report-Chart.py`, `리포트차트.py` |
| `weather_rain_kma_202610.csv` | `날씨데이터_최종.csv` |
| `media_banner_01.png` | `배너 수정본.png` |

- 데이터 파일: `모듈코드_내용_출처_기준연월.csv` (예: `modules/weather/data/weather_rain_kma_202610.csv`)
- 이미지 파일: `모듈코드_내용_번호.png` (예: `modules/media/images/media_banner_01.png`)

### 2-2. 코드 안의 이름

| 종류 | 규칙 | 예시 |
|---|---|---|
| Python 함수, 변수 | `모듈코드_이름` (snake_case) | `report_get_summary()` |
| 상수 | 대문자 + 언더바 | `REPORT_MAX_ROWS` |
| **위젯 `key`** | `모듈코드-이름` | `st.button("검색", key="weather-btn-search")` |
| **`st.session_state` 키** | `모듈코드-이름` | `st.session_state["report-selected-month"]` |
| HTML class (`st.markdown`으로 넣을 때) | `모듈코드-이름` | `report-card` |
| Supabase 표 | `모듈코드_내용` | `report_sales`, `weather_forecast` |

> ⚠️ Streamlit은 **앱 전체에서 위젯 key가 하나라도 겹치면 에러**가 납니다. 위젯에는 항상 `key="모듈코드-..."`를 붙입니다.

```python
# O
st.button("분석", key="report-btn-analyze")
st.session_state["report-result"] = result

# X : 다른 탭에도 "분석" 버튼이 있으면 key가 겹쳐 에러
st.button("분석")
st.session_state["result"] = result
```

---

## 3. 합칠 때 오류가 나지 않게 하는 규칙 ⭐

### 규칙 1. PM이 뼈대를 먼저 올린다
PM이 파일 구조 전체를 **빈 파일로 미리 만들어** `develop`에 올립니다.
- `common/common_layout.py`에는 6개 탭(`모듈코드_render` 함수)이 모두 연결되어 있습니다.

팀원은 이 뼈대를 받은 뒤 자기 폴더의 파일 **내용만 채웁니다.** 그래서 공용 파일을 건드릴 일이 없습니다.

### 규칙 2. 내 화면은 `모듈코드_render()` 함수 하나
```python
# modules/report/report_page.py
import streamlit as st


def report_render():   # 사이드바에서 이 탭을 열 때마다 실행됩니다
    st.header("1. 분석 리포트")
    ... 화면과 기능 전부 ...
```
- 함수 이름 `모듈코드_render`는 바꾸지 않습니다. `common_layout.py`가 이 이름으로 연결합니다.
- **파일 맨 위(함수 밖)에는 `st.` 코드를 쓰지 않습니다.** 함수 밖 코드는 앱이 켜질 때 모든 탭에서 한 번에 실행되기 때문입니다. (import, 상수, 함수 정의만 가능)
- `st.set_page_config()`는 `common_layout.py`에서만 부릅니다.
- 다른 모듈의 파일은 import하지 않습니다. 내 폴더 안의 파일만 import합니다.

```python
from modules.report.report_download import report_download_button   # O : 내 폴더
from modules.weather.weather_page import weather_get_forecast        # X : 다른 사람 폴더
```

### 규칙 3. 디자인은 Streamlit 기본 + 공통 변수만 사용
같은 대시보드처럼 보이도록 기본 색은 `.streamlit/config.toml`의 테마를 따르고, 직접 꾸밀 때는 공통 CSS 변수만 씁니다.

```python
st.markdown('<div class="report-card">요약</div>', unsafe_allow_html=True)
```
```css
/* modules/report/report_style.css */
/* O */
.report-card {
  background: var(--color-card);
  border-radius: var(--radius);
}

/* X : 색을 직접 쓰거나, Streamlit 전체/태그 전체에 스타일 걸기 */
.report-card { background: #fff3e0; }
div, p, .stButton button { margin: 0; }
```

| 변수 | 용도 |
|---|---|
| `--color-primary` | 메인 색 (버튼, 강조) |
| `--color-bg` / `--color-card` | 배경 / 카드 배경 |
| `--color-text` / `--color-sub` | 기본 글자 / 보조 글자 |
| `--color-border` | 테두리 |
| `--radius` | 모서리 둥글기 |
| `--font-main` | 글꼴 |

> 변수는 `common/common_style.css`에 있습니다. 필요한 변수가 없으면 PM에게 추가를 요청합니다.
> 모든 모듈의 CSS가 한 화면에 같이 적용되므로 **class는 반드시 `모듈코드-`로 시작**해야 다른 탭이 깨지지 않습니다.

### 규칙 4. 탭끼리 데이터는 `store`로만 주고받기
**내 모듈 이름의 키에만 저장하고, 다른 키는 읽기만** 합니다. 저장한 값은 Supabase에도 남아서 새로고침해도 유지됩니다.

```python
from common.common_store import store_get, store_set

# 리포트 탭이 저장
store_set("report", {"summary": "...", "problems": []})

# 가설 탭이 읽기
report = store_get("report")
if not report:
    st.info("먼저 1. 분석 리포트 탭에서 분석을 실행해 주세요.")   # 값이 없을 때도 화면이 깨지지 않게
    return
```

| 키 | 저장하는 탭 | 읽는 탭 |
|---|---|---|
| `report` | report | hypothesis, media, solution |
| `hypothesis` | hypothesis | media, solution |
| `solution` | solution | home |
| `weather` | weather | home |

- 값은 dict, list, 문자열, 숫자만 넣습니다. DataFrame은 `df.to_dict("records")`로 바꿔서 넣습니다.
- 저장하는 데이터 모양(어떤 항목이 들어가는지)을 바꿀 때는 그 데이터를 읽는 탭 담당자에게 먼저 알려 주세요.

### 규칙 5. 데이터는 `common_db`로 읽고 저장, 내 표만 쓰기
```python
from common.common_db import db_read, db_insert, db_update

rows = db_read("report_sales", month="2026-10")               # 읽기
db_insert("report_result", {"month": "2026-10", "text": "..."})  # 저장
```
- Supabase에 직접 연결하는 코드(`create_client`, 주소/키 직접 입력)를 쓰지 않습니다. 항상 `common/common_db.py` 함수를 씁니다.
- **내 모듈 이름으로 시작하는 표(`report_...`)에만 저장/수정/삭제**합니다. 다른 모듈의 표와 `common_` 표는 읽기만 합니다.
- 표를 새로 만들거나 열 구성을 바꾸면 노션에 기록하고 팀에 알립니다.
- AI, 날씨, 경쟁사 기능은 `common/`의 함수를 **가져다 쓰기만** 합니다.

```python
from common.common_ai import ask_ai
```

### 규칙 6. 다른 사람 파일은 저장도 하지 않기
VS Code는 저장할 때 자동 정렬이 되기 때문에, 열어 보기만 하고 저장하면 내용이 바뀐 것으로 잡힐 수 있습니다.
**다른 사람 파일과 공용 파일은 열어 보기만 하고 저장하지 않습니다.**

### 규칙 7. PR 올리기 전 체크리스트
- [ ] `modules/내모듈/` 안의 파일만 수정했다 (GitHub Desktop의 변경 파일 목록에서 확인)
- [ ] `requirements.txt`, `secrets.toml.example`을 고쳤다면 정해진 자리에 한 줄만 추가했다
- [ ] 함수, 위젯 key, session_state 키, class, 표 이름에 모듈 코드를 붙였다
- [ ] 색상은 공통 변수만 사용했다
- [ ] `streamlit run app.py`로 실행했을 때 내 탭이 잘 나오고, 다른 탭도 깨지지 않는다
- [ ] 화면에 빨간 에러 상자가 없고, 터미널에도 에러가 없다
- [ ] `.streamlit/secrets.toml`이나 API 키가 변경 파일 목록에 없다

---

## 4. 비밀값 관리 🔐

API 키, Supabase 주소처럼 밖으로 새면 안 되는 값은 코드에 직접 쓰지 않고 **`.streamlit/secrets.toml`** 에 넣습니다.
배포된 앱은 **Streamlit Cloud의 Secrets**에 넣은 값을 씁니다. 이 두 곳 외에는 어디에도 넣지 않습니다.

| 파일 / 위치 | 내용 | GitHub에 올라가나요? |
|---|---|---|
| `.streamlit/secrets.toml` | **진짜 키** (내 컴퓨터용) | ❌ 절대 안 올라감 (`.gitignore`에 등록) |
| `.streamlit/secrets.toml.example` | 키 **이름**과 더미 값만 | ✅ 올라감 (팀원 안내용) |
| Streamlit Cloud > App settings > Secrets | **진짜 키** (배포용) | - (PM만 수정) |

### `secrets.toml.example` 모양

PM이 모듈별 칸을 미리 만들어 둡니다. 팀원은 **내 모듈 칸 아래에만** 한 줄씩 추가합니다.
(모두 맨 아래에 추가하면 같은 위치를 고친 것으로 인식되어 충돌이 납니다.)

```toml
# ===== 공통 (PM) =====
AI_API_KEY = "your_ai_api_key_here"
WEATHER_API_KEY = "your_weather_api_key_here"

# ===== home =====

# ===== report =====

# ===== hypothesis =====

# ===== media =====

# ===== solution =====

# ===== weather =====

# ===== Supabase (PM, 맨 아래 고정) =====
[connections.supabase]
SUPABASE_URL = "https://your-project-id.supabase.co"
SUPABASE_KEY = "your_supabase_anon_key_here"
```

> ⚠️ **`[connections.supabase]`는 항상 맨 아래**에 둡니다. TOML은 `[묶음]` 아래에 쓴 줄을 전부 그 묶음 안으로 넣기 때문에, 그 아래에 키를 추가하면 `st.secrets["키"]`로 찾을 수 없습니다.
> 값은 반드시 큰따옴표로 감쌉니다: `KEY = "값"`

### 새 API 키가 필요할 때 (예시)

> media 담당자 A가 영상 생성을 위해 Creatomate API 키를 새로 발급받아,
> 자기 브랜치 `feature/media-video`에서 작업하는 과정

**① 내 컴퓨터의 `.streamlit/secrets.toml`에 진짜 키 넣기** (`# ===== media =====` 아래)
```toml
CREATOMATE_API_KEY = "진짜키12345"
```
> GitHub Desktop 변경 목록에 `secrets.toml`이 보이면 **절대 commit하지 않습니다.**

**② `secrets.toml.example`의 `# ===== media =====` 아래에 더미 키 안내 추가**
```toml
# ===== media =====
# 영상 생성 Creatomate API 키 (발급: creatomate.com)
CREATOMATE_API_KEY = "your_creatomate_api_key_here"
```

**③ 코드에서는 이름으로만 불러오기**
```python
# modules/media/media_page.py
import streamlit as st


def media_render():
    api_key = st.secrets["CREATOMATE_API_KEY"]   # O : 함수 안에서 불러오기
    # api_key = "진짜키12345"                     # X : 키가 GitHub에 올라감
```

**④ commit하고, 진짜 키 값은 카톡이나 노션으로 공유**
- commit: `chore: secrets.toml.example에 Creatomate API 키 안내 추가`
- 팀원들은 받은 키를 각자 자기 컴퓨터의 `.streamlit/secrets.toml`에 넣습니다.
- **PM은 Streamlit Cloud > App settings > Secrets에도 같은 줄을 추가**합니다. (안 하면 배포된 앱에서만 에러)

> 💡 키가 실수로 GitHub에 올라갔다면, 커밋을 지우는 것만으로는 부족합니다. **바로 PM에게 알리고 해당 키를 재발급**받아야 합니다.

---

## 5. AI 도구(Claude / Codex 등)로 작업할 때

- **commit, push, PR, merge는 담당자가 직접 합니다.** AI에게는 커밋 메시지 제안만 요청하고, `git add` / `git commit` / `git push` / `git merge`는 AI가 실행하지 않게 합니다.
- AI가 공통 파일이나 다른 사람 파일을 고치는 경우가 많으니, 작업 후 **변경 파일 목록을 꼭 확인**합니다.
- AI에게 요청할 때 아래 규칙을 함께 붙여 넣습니다. `[모듈코드]`는 내 모듈 코드(예: `report`)로 바꿉니다.

```
먼저 README.md와 RULES.md를 읽어 주세요.
이 프로젝트는 Streamlit + Supabase로 만들고, Streamlit Community Cloud로 배포합니다.

규칙:
- 내 모듈 코드는 [모듈코드]입니다.
- modules/[모듈코드]/ 폴더 밖의 파일은 수정하지 마세요.
  (app.py, common/, .streamlit/config.toml, data/, 다른 모듈 폴더 수정 금지)
- 화면과 기능은 modules/[모듈코드]/[모듈코드]_page.py의 [모듈코드]_render() 함수 안에 작성하고,
  함수 이름은 바꾸지 마세요. 함수 밖에는 st. 코드를 쓰지 마세요. st.set_page_config()는 쓰지 마세요.
- 코드가 길어지면 modules/[모듈코드]/[모듈코드]_xxx.py로 나누고, 다른 모듈 폴더는 import하지 마세요.
- 이미지는 modules/[모듈코드]/images/, 데이터 파일은 modules/[모듈코드]/data/에 넣어 주세요.
- 파일명과 Python 함수/변수는 [모듈코드]_ 로,
  위젯 key, st.session_state 키, CSS class는 [모듈코드]- 로 시작하게 해 주세요.
- 모든 위젯에 key="[모듈코드]-..."를 붙여 주세요.
- 색상, 글꼴, 모서리는 common/common_style.css의 CSS 변수만 사용하세요.
- 다른 탭과 데이터를 주고받을 때는 common/common_store.py의 store_get / store_set만 사용하고,
  '[모듈코드]' 키에만 저장하세요.
- Supabase는 common/common_db.py의 db_read / db_insert / db_upsert / db_update / db_delete만 사용하고,
  [모듈코드]_ 로 시작하는 표에만 저장하세요.
- AI, 날씨, 경쟁사 기능은 common/의 함수를 가져다 쓰기만 하세요.
- API 키는 st.secrets["키이름"]으로 불러오고, 코드에 직접 쓰지 마세요.
- 새 라이브러리나 새 API 키가 필요하면 직접 추가하지 말고,
  requirements.txt와 .streamlit/secrets.toml.example에 추가할 한 줄을 알려 주세요.
- 공통 파일 수정이 필요해 보이면 수정하지 말고 알려 주세요.
- git add / commit / push / merge는 실행하지 마세요.
  작업이 끝나면 바뀐 파일 목록과 커밋 메시지 제안만 알려 주세요.
```

---

## 6. Git 사용 규칙

### 6-1. 용어 정리

| 용어 | 뜻 | 쉽게 말하면 |
|---|---|---|
| **commit** | 작업 단위 저장 | 내 컴퓨터에 **세이브 포인트** 만들기 |
| **push** | 서버로 전송 | 내 컴퓨터의 commit들을 GitHub에 올려 두기 |
| **pull** | 최신 내용 받기 | GitHub의 최신 코드를 내 컴퓨터로 가져오기 |
| **branch** | 작업 공간 분리 | 일종의 **평행세계**. 혼자 마음껏 실패해도 다른 사람에게 영향 없음 |
| **pull request (PR)** | 합치기 요청 | GitHub Desktop에서 **Create Pull Request** → GitHub 웹사이트에서 "이 기능 완성됐으니 `develop`에 합쳐 주세요" 요청서 작성 |
| **merge** | 합치기 | 브랜치의 작업을 다른 브랜치에 합치는 것 |
| **conflict** | 충돌 | 두 사람이 같은 줄을 다르게 고쳐서 Git이 자동으로 못 합치는 상태 |

### 6-2. 브랜치 규칙

```
main                        ← 최종 완성본 = 배포 (합쳐지면 Streamlit Cloud에 자동 배포, PM만 합침)
 └── develop                ← 팀원 작업을 모으는 곳
      ├── feature/home-calendar
      ├── feature/report-download
      ├── feature/hypothesis-review
      ├── feature/media-prompt
      ├── feature/solution-list
      └── feature/weather-ad-frequency
```

| 브랜치 | 용도 | 누가 |
|---|---|---|
| `main` | 최종 완성본, **자동 배포**, 발표/제출용 | **PM만** develop → main 합침 |
| `develop` | 모든 기능을 모아 테스트 | 팀원은 **PR로만** 올림 (직접 push 금지) |
| `feature/모듈코드-기능명` | 기능 하나를 만드는 개인 작업 공간 | 각 담당자 |
| `fix/모듈코드-기능명` | 버그 수정 | 각 담당자 |

- 브랜치 이름은 **영어 소문자 + 하이픈(`-`)**: `feature/home-calendar`, `fix/report-pdf-font`
- 항상 **내 브랜치에 push → `develop`으로 PR**합니다.
- `main`에 합쳐지는 순간 실제 배포 주소가 바뀌므로, `main`에는 develop에서 확인이 끝난 것만 합칩니다.
- 기능 하나가 끝나면 브랜치도 끝냅니다. 다음 기능은 최신 `develop`에서 새 브랜치를 만듭니다.
- 기능별 담당자 기록은 노션에 정리합니다.

### 6-3. 매일 작업 순서 (GitHub Desktop 기준)

**① 작업 시작 전: 최신 코드 받기**
1. Current Branch → `develop` 선택 → **Fetch origin → Pull origin**
2. 새 기능이면 **New Branch**로 `feature/모듈코드-기능명` 만들기 (develop 기준)
3. 이어서 하는 작업이면 내 브랜치로 이동 → Branch 메뉴 → **Update from develop**
4. `requirements.txt`가 바뀌었으면 `pip install -r requirements.txt` 다시 실행

**② 작업 → 확인 → commit**
- `streamlit run app.py`로 내 탭을 확인합니다.
- 기능 하나, 수정 하나 단위로 자주 commit합니다.
- Summary, Description 작성법은 [6-6. 커밋 메시지 규칙](#6-6-커밋-메시지-규칙)을 따릅니다.

**③ push → PR**
1. **Push origin**으로 내 브랜치를 GitHub에 올리기
2. **Create Pull Request** → GitHub 웹사이트에서 `base: develop` ← `compare: 내 브랜치` 확인
3. PR 설명에 무엇을 만들었는지, 새로 만든 Supabase 표나 비밀값이 있는지 적고 생성

**④ 합치기**
- 팀원 → `develop`: 팀원 1명 이상이 확인(Approve)한 뒤 합칩니다.
- `develop` → `main`: PM이 전체 탭을 실행해서 확인하고, 새 비밀값을 Streamlit Cloud Secrets에 넣은 뒤 합칩니다. (합치면 자동 배포)

> 💡 PR은 **작게, 자주** 올립니다. 며칠씩 쌓아 두면 충돌이 커집니다.
> 💡 충돌이 나면 혼자 해결하지 말고, 해당 파일 담당자와 같이 해결합니다.

### 6-4. 파일 및 코드 작성 규칙

- **본인 담당 폴더(`modules/내모듈/`)의 파일만** 수정합니다.
- `app.py`, `common/`, `.streamlit/config.toml` 같은 **공용 파일은 PM만** 수정합니다.
  - PM이 6개 모듈을 처음부터 다 연결해 두었기 때문에 팀원이 공용 파일을 고칠 일은 거의 없습니다.
  - 공용 파일에 꼭 추가할 내용이 있으면 직접 고치지 말고 PM에게 요청합니다.
  - 여러 명이 공용 파일 "맨 아래"에 동시에 코드를 덧붙이면 Git은 같은 줄을 고친 것으로 보고 충돌이 납니다. 그래서 덧붙이기도 PM이 합니다.
- 예외: `requirements.txt`, `.streamlit/secrets.toml.example`은 정해진 자리에 **한 줄 추가만** 할 수 있습니다.
- 들여쓰기, 줄바꿈, 띄어쓰기 같은 **사소한 변경은 다른 사람 파일과 공용 파일에서 금지**합니다.

### 6-5. 개발 환경 통일

**Python 버전과 가상환경**
- Python 버전: `3.11` (팀 확정 후 수정, Streamlit Cloud 설정과 같게 맞춤)
- 가상환경 폴더 이름은 `venv`로 통일합니다. `.gitignore`에 등록되어 있어서 GitHub에 올라가지 않습니다.

```bash
# 처음 한 번 (프로젝트 맨 위 폴더에서)
python -m venv venv
venv\Scripts\activate            # Mac: source venv/bin/activate
pip install -r requirements.txt

# 실행 (프로젝트 맨 위 폴더에서)
streamlit run app.py
```

**새 라이브러리를 설치했다면**
- `requirements.txt`에 **알파벳 순서 자리에 한 줄만** 추가합니다. 맨 아래에 몰아서 추가하면 다른 사람과 충돌합니다.
- 다른 줄은 건드리지 않습니다.
- Streamlit Cloud는 이 파일을 보고 라이브러리를 설치하므로, **빠뜨리면 내 컴퓨터에선 되는데 배포에서만 에러**가 납니다.
- 팀 채팅에 "○○ 라이브러리 추가했어요"라고 알립니다. 다른 팀원은 pull 받은 뒤 `pip install -r requirements.txt`를 다시 실행합니다.
- commit은 `chore: 라이브러리명 requirements에 추가`로 남깁니다.

**VS Code 설정**
- **Python**, **Prettier** 확장을 설치하고 Format On Save를 켭니다. 모두 같은 정렬 규칙(`.editorconfig`)을 쓰기 때문에 결과가 같아집니다.
- 들여쓰기, 줄바꿈, 띄어쓰기만 바꾸는 작업은 **내 파일에서만**, `style:` 커밋으로 따로 올립니다.

### 6-6. 커밋 메시지 규칙

**Summary (commit 작은 칸)**: `태그: 한 줄 요약`
- 콜론(`:`) 뒤에는 한 칸 띄웁니다.
- 한국어로 명확하게 적습니다.

**Description (설명 칸)**: 무엇을, 어떻게, 왜 바꿨는지 반드시 적습니다.

```
Summary
feat: 캘린더 일정 추가 기능 구현

Description
[무엇을] home_page.py에 일정 추가 폼과 home_schedule 표 저장 추가
[어떻게] 날짜를 고르고 저장하면 Supabase에 저장되고 달력에 표시되도록 구현
[왜] 홈 화면에서 프로모션 일정을 바로 등록할 수 있게 하기 위해
```

| 태그 | 언제 쓰나요 | 예시 |
|---|---|---|
| `feat` | 새 화면, 탭, 기능, 버튼 추가 | `feat: 캘린더 일정 추가 기능 구현` |
| `fix` | 버그 수정 | `fix: 리포트 PDF 한글 깨짐 수정` |
| `docs` | 코드는 그대로, md 파일만 수정 | `docs: 프로젝트 설치 방법 가이드 추가` |
| `style` | 코드 동작 변화 없이 들여쓰기, 줄바꿈 정리 | `style: weather_page.py 들여쓰기 4칸 통일` |
| `refactor` | 기능은 같고 코드만 다듬음 | `refactor: 중복되는 날짜 변환 함수 하나로 통합` |
| `chore` | 라이브러리 추가, 설정 파일 수정 | `chore: pandas 라이브러리 requirements에 추가` |

❌ 이런 메시지는 금지합니다: `수정`, `최종`, `ㅇㅇ`, `asdf`, `코드 고침`

---

## 7. 금지 사항 🚫

- `main`, `develop`에 직접 push하기 (`main`은 push하는 순간 배포됩니다)
- `modules/내모듈/` 밖의 파일 수정하기 (열어서 저장하는 것도 포함, `requirements.txt`·`secrets.toml.example` 한 줄 추가는 예외)
- 모듈 코드 없이 함수, 위젯 key, session_state 키, class, Supabase 표 이름 짓기
- `모듈코드_render()` 함수 밖에 `st.` 코드 쓰기, `st.set_page_config()` 쓰기
- 색상 코드를 직접 쓰거나 태그 전체, Streamlit 기본 요소 전체에 CSS 적용하기
- 다른 모듈의 Supabase 표나 `common_` 표에 저장/수정/삭제하기
- `.streamlit/secrets.toml`, API 키, Supabase 주소/키 올리기, 코드에 직접 쓰기
- 100MB 이상 파일 올리기 (큰 데이터는 Supabase나 드라이브 링크로 공유)
- `git push --force` 사용하기
- AI 도구에게 commit, push, merge 맡기기

---

## 8. 공통 설정 파일 (PM이 처음에 만듭니다)

### .gitignore
```
.streamlit/secrets.toml
.env
venv/
__pycache__/
.vscode/
node_modules/
.DS_Store
Thumbs.db
*.log
```

### .streamlit/config.toml
```toml
[theme]
base = "light"
primaryColor = "#3b6ef5"
backgroundColor = "#f4f6fa"
secondaryBackgroundColor = "#ffffff"
textColor = "#1f2430"
```

### .editorconfig
```
root = true

[*]
charset = utf-8
end_of_line = lf
indent_style = space
indent_size = 2
insert_final_newline = true
trim_trailing_whitespace = true

[*.py]
indent_size = 4
```

---

## 📝 변경 이력

| 날짜 | 내용 | 작성자 |
|---|---|---|
| 2026-10-22 | README에서 팀 규칙을 분리해 RULES.md 작성, AI 도구 사용 규칙 추가 | 000 |
| 2026-10-23 | README 파일 구조 기준으로 수정 (routers/, assets/, data/processed/ 삭제 → 모듈 폴더 안의 `_server.py`, `images/`, `data/`), 보안 및 환경 변수 관리 예시 추가, 파일 및 코드 작성 규칙 추가 | 000 |
| 2026-10-23 | 모듈 설명 파일 이름 변경 (`README.md` → `모듈코드.md`) | 000 |
| 2026-10-23 | **Streamlit + Supabase 구조로 전환**: `모듈코드_page.py` / `모듈코드_render()` 규칙, 위젯 key 규칙, `store_get/store_set`, `common_db` 사용 규칙, `.env` → `.streamlit/secrets.toml` + Streamlit Cloud Secrets, main 자동 배포 반영 | 000 |
