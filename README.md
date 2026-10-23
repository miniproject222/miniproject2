# 📊 마케팅 솔루션 대시보드

> 판매 데이터를 분석해 문제를 찾고 → 가설을 세우고 → 광고 매체와 솔루션을 만들고 → 날씨에 맞춰 광고 타이밍까지 추천하는 마케팅 대시보드

이 문서는 **각자 VS Code에서 작업한 코드를 GitHub에서 합칠 때 오류가 나지 않도록** 지킬 규칙을 정리한 것입니다.
작업 전에 한 번 끝까지 읽어 주세요. 규칙이 바뀌면 이 문서를 먼저 고치고 팀에 공유합니다.

---

## 1. 기능 구성

| 순서 | 탭 이름 | 하는 일 | 경쟁사 관련 기능 | 모듈 코드 |
|---|---|---|---|---|
| 홈 | 홈 | 날씨, 달력, 전날 매출과 이슈 알림 | - | `home` |
| 1 | 분석 리포트 | 결과 데이터 요약, 문제 분석, 리포트 다운로드 | 문제 요인의 내부/외부 분석 | `report` |
| 2 | 가설 수립 | 문제 해결 가설 제안 (현지 특성 반영) | 경쟁사 부정 리뷰를 우리 홍보 포인트로 활용 | `hypothesis` |
| 3 | 매체 제작 | 가설 2개 → 프롬프트 2개 → 결과물 2개 (프롬프트 다듬기) | 광고 소재 레퍼런스 (따라 하기 / 피하기) | `media` |
| 3-1 | 솔루션 제안 | 매체 외에 실행할 수 있는 솔루션 제안 | 경쟁사 부정 리뷰 활용 | `solution` |
| 4 | 날씨 광고 타이밍 | 날씨, 상황에 따른 광고(메타, 아마존) 노출 빈도와 예산 추천 | 폭염 + 경쟁사 품절 → 광고 빈도 증가 | `weather` |

- 화면 구성: 왼쪽 **사이드바**에 홈, 1~4번 탭이 있고 누르면 해당 화면으로 바뀝니다.
- **모듈 코드**는 파일명, 폴더명, id, class, 변수명 앞에 붙이는 이름입니다. 이름이 겹치지 않게 해 주는 가장 중요한 규칙입니다.
- 담당자 기록은 노션에 정리합니다.

---

## 2. 파일 구조

```
marketing-dashboard/
├── README.md                       # 전체 규칙 문서 (PM)
├── .gitignore                      # GitHub에 올리지 않을 파일 목록 (PM)
├── .editorconfig                   # 들여쓰기, 줄바꿈 통일 설정 (PM)
├── .env.example                    # API 키 이름 예시 (PM)
├── index.html                      # 사이드바 + 탭 전환 (PM)
│
├── common/                         # 화면 공통 (PM)
│   ├── common_style.css            # 색상 변수, 사이드바, 카드 디자인
│   ├── common_layout.js            # 사이드바 메뉴, 탭 전환
│   ├── common_store.js             # 탭끼리 데이터 주고받기
│   ├── common_api.js               # 서버 호출 함수
│   └── images/                     # 같이 쓰는 이미지 (로고, 아이콘)
│
├── server/                         # 서버 공통 (PM)
│   ├── main.py                     # 서버 실행, 6개 모듈 서버 연결
│   ├── requirements.txt            # 라이브러리 목록 (모두 한 줄 추가 가능)
│   └── shared/
│       ├── shared_ai.py            # AI 호출
│       ├── shared_weather.py       # 날씨 API 호출
│       └── shared_competitor.py    # 경쟁사 리뷰, 품절, 광고 소재 수집
│
├── data/                           # 같이 쓰는 원본 데이터 (PM, 수정 금지)
│
├── docs/                           # 회의록, 기획서
│
└── modules/                        # ⭐ 각자 자기 폴더만 수정
    ├── home/                       # 홈
    │   ├── home.md
    │   ├── home_main.html          # 화면
    │   ├── home_style.css          # 디자인
    │   ├── home_script.js          # 화면 기능
    │   ├── home_server.py          # 서버 기능
    │   ├── images/                 # 홈에서만 쓰는 이미지
    │   └── data/                   # 홈에서만 쓰는 데이터
    │
    ├── report/                     # 1. 분석 리포트
    │   ├── report.md
    │   ├── report_main.html
    │   ├── report_style.css
    │   ├── report_script.js
    │   ├── report_download.js      # 리포트 다운로드
    │   ├── report_server.py
    │   ├── images/
    │   └── data/
    │
    ├── hypothesis/                 # 2. 가설 수립
    │   ├── hypothesis.md
    │   ├── hypothesis_main.html
    │   ├── hypothesis_style.css
    │   ├── hypothesis_script.js
    │   ├── hypothesis_server.py
    │   ├── images/
    │   └── data/
    │
    ├── media/                      # 3. 매체 제작
    │   ├── media.md
    │   ├── media_main.html
    │   ├── media_style.css
    │   ├── media_script.js
    │   ├── media_server.py
    │   ├── images/
    │   └── data/
    │
    ├── solution/                   # 3-1. 솔루션 제안
    │   ├── solution.md
    │   ├── solution_main.html
    │   ├── solution_style.css
    │   ├── solution_script.js
    │   ├── solution_server.py
    │   ├── images/
    │   └── data/
    │
    └── weather/                    # 4. 날씨 광고 타이밍
        ├── weather.md
        ├── weather_main.html
        ├── weather_style.css
        ├── weather_script.js
        ├── weather_server.py
        ├── images/
        └── data/
```

### 누가 어떤 파일을 수정하나요?

| 구분 | 수정하는 곳 |
|---|---|
| **팀원** | **`modules/내모듈/` 하나만** (화면, 디자인, 서버, 이미지, 데이터 전부) |
| **PM** | `modules/` 밖의 전부 (`index.html`, `common/`, `server/`, `data/`, 설정 파일, 루트 `README.md`) |
| **모두 (한 줄 추가만)** | `server/requirements.txt` → [6-5. 개발 환경 통일](#6-5-개발-환경-통일), `.env.example` → [5. 보안 및 환경 변수 관리](#5-보안-및-환경-변수-관리-) 참고 |

- 내 탭에서만 쓰는 이미지와 데이터는 **내 폴더 안의 `images/`, `data/`**에 넣습니다.
- 여러 탭이 같이 쓰는 이미지는 `common/images/`, 같이 쓰는 원본 데이터는 루트 `data/`에 있습니다. (PM 관리)
- 공통 파일에 기능이 필요하면 직접 고치지 말고 PM에게 요청합니다.

---

## 3. 이름 짓기 규칙

### 3-1. 파일명

- **영어 소문자 + 언더바(`_`)**, 그리고 **모듈 코드로 시작**합니다.
- 한글, 띄어쓰기, `_최종`, `_v2` 같은 버전 표시는 쓰지 않습니다. 버전은 Git이 관리합니다.

| O | X |
|---|---|
| `report_chart.js` | `chart.js`, `Report-Chart.js`, `리포트차트.js` |
| `weather_rain_kma_202610.csv` | `날씨데이터_최종.csv` |
| `media_banner_01.png` | `배너 수정본.png` |

데이터 파일은 `모듈코드_내용_출처_기준연월.csv` 형식으로 짓습니다. (예: `modules/weather/data/weather_rain_kma_202610.csv`)
이미지 파일은 `모듈코드_내용_번호.png` 형식으로 짓습니다. (예: `modules/media/images/media_banner_01.png`)

### 3-2. 코드 안의 이름

| 종류 | 규칙 | 예시 |
|---|---|---|
| HTML id, CSS class | `모듈코드-이름` | `report-card`, `weather-btn-search` |
| JS 객체 | 모듈 코드 첫 글자만 대문자 | `Report`, `Hypothesis`, `Weather` |
| JS 변수, 함수 | 객체 안에 camelCase로 | `Report.loadData()` |
| Python 함수, 변수 | `모듈코드_이름` (snake_case) | `report_get_summary()` |
| 상수 | 대문자 + 언더바 | `MAX_RESULT`, `REPORT_MAX_ROWS` |

```html
<!-- O -->
<div id="report-summary" class="report-card"></div>

<!-- X : 다른 탭의 card와 겹쳐서 디자인이 깨짐 -->
<div id="summary" class="card"></div>
```

```javascript
// O : 내 코드는 전부 내 모듈 객체 안에
const Report = {
  init() {
    this.loadData();
  },
  loadData() {
    // ...
  },
};

// X : 다른 사람 코드와 이름이 겹칠 수 있음
let data = [];
function init() {}
```

---

## 4. 합칠 때 오류가 나지 않게 하는 규칙 ⭐

### 규칙 1. PM이 뼈대를 먼저 올린다
PM이 위 파일 구조 전체를 **빈 파일로 미리 만들어** `develop`에 올립니다.
- `index.html`에는 6개 탭이 모두 연결되어 있습니다.
- `server/main.py`에는 6개 모듈의 서버 파일(`모듈코드_server.py`)이 모두 연결되어 있습니다.

팀원은 이 뼈대를 받은 뒤 자기 파일 **내용만 채웁니다.** 그래서 공용 파일을 건드릴 일이 없습니다.

### 규칙 2. 내 화면은 `section` 하나, 실행은 `init()` 한 줄
```html
<!-- report_main.html -->
<section id="report-section">
  ... 화면 내용 전부 ...
</section>
```
```javascript
// report_script.js
const Report = {
  init() { ... },   // index.html이 이 한 줄만 호출합니다
};
```
이렇게 만들면 나중에 탭을 하나로 합치더라도 PM이 `index.html`만 고치면 됩니다.

### 규칙 3. 디자인은 공통 변수만 사용
같은 대시보드처럼 보이도록 색상, 글꼴, 모서리는 직접 쓰지 않습니다.

```css
/* O */
.report-card {
  background: var(--color-card);
  border-radius: var(--radius);
}

/* X : 색을 직접 쓰거나, 태그 전체에 스타일 걸기 */
.report-card { background: #fff3e0; }
body { margin: 0; }
```

| 변수 | 용도 |
|---|---|
| `--color-primary` | 메인 색 (버튼, 강조) |
| `--color-bg` / `--color-card` | 배경 / 카드 배경 |
| `--color-text` / `--color-sub` | 기본 글자 / 보조 글자 |
| `--radius` | 모서리 둥글기 |
| `--font-main` | 글꼴 |

### 규칙 4. 탭끼리 데이터는 `Store`로만 주고받기
다른 사람의 JS 파일을 직접 불러오지 않습니다. **내 모듈 이름의 키에만 저장하고, 다른 키는 읽기만** 합니다.

```javascript
// 리포트 탭이 저장
Store.set('report', { summary: '...', problems: [] });

// 가설 탭이 읽기
const report = Store.get('report');
```

| 키 | 저장하는 탭 | 읽는 탭 |
|---|---|---|
| `report` | report | hypothesis, media, solution |
| `hypothesis` | hypothesis | media, solution |
| `solution` | solution | home |
| `weather` | weather | home |

> 저장하는 데이터 모양(어떤 항목이 들어가는지)을 바꿀 때는 그 데이터를 읽는 탭 담당자에게 먼저 알려 주세요.

### 규칙 5. 서버 주소는 내 모듈 이름으로 시작
```python
# modules/report/report_server.py
from fastapi import APIRouter

router = APIRouter(prefix="/report")   # 내 주소는 전부 /report/...

@router.post("/analyze")               # → /report/analyze
def report_analyze():
    ...
```
- 화면에서 서버를 부를 때는 `common_api.js`의 `Api.get()` / `Api.post()`를 사용합니다.
- AI, 날씨, 경쟁사 데이터는 `server/shared/`의 함수를 **가져다 쓰기만** 합니다.

```python
from server.shared.shared_ai import ask_ai
```

### 규칙 6. 다른 사람 파일은 저장도 하지 않기
VS Code는 저장할 때 자동 정렬이 되기 때문에, 열어 보기만 하고 저장하면 내용이 바뀐 것으로 잡힐 수 있습니다.
**다른 사람 파일은 열어 보기만 하고 저장하지 않습니다.**

### 규칙 7. PR 올리기 전 체크리스트
- [ ] `modules/내모듈/` 안의 파일만 수정했다 (GitHub Desktop의 변경 파일 목록에서 확인)
- [ ] id, class, 변수, 함수에 모듈 코드를 붙였다
- [ ] 색상은 공통 변수만 사용했다
- [ ] `index.html`을 실행했을 때 내 탭이 잘 나온다
- [ ] 브라우저 콘솔(F12)에 빨간 에러가 없다
- [ ] `.env`나 API 키가 변경 파일 목록에 없다

---

## 5. 보안 및 환경 변수 관리 🔐

API 키처럼 밖으로 새면 안 되는 값은 코드에 직접 쓰지 않고 `.env` 파일에 넣습니다.

| 파일 | 위치 | 내용 | GitHub에 올라가나요? |
|---|---|---|---|
| `.env` | 프로젝트 맨 위 폴더 | **진짜 API 키** | ❌ 절대 안 올라감 (`.gitignore`에 등록) |
| `.env.example` | 프로젝트 맨 위 폴더 | 키 **이름**과 더미 값만 | ✅ 올라감 (팀원 안내용) |

### `.env.example` 모양

PM이 모듈별 칸을 미리 만들어 둡니다. 팀원은 **내 모듈 칸 아래에만** 한 줄씩 추가합니다.
(모두 맨 아래에 추가하면 같은 위치를 고친 것으로 인식되어 충돌이 납니다.)

```
# ===== 공통 (PM) =====
AI_API_KEY=your_ai_api_key_here
WEATHER_API_KEY=your_weather_api_key_here

# ===== home =====

# ===== report =====

# ===== hypothesis =====

# ===== media =====

# ===== solution =====

# ===== weather =====
```

### 새 API 키가 필요할 때 (예시)

> media 담당자 A가 영상 생성을 위해 Creatomate API 키를 새로 발급받아,
> 자기 브랜치 `feature/media-video`에서 작업하는 과정

**① 내 컴퓨터의 `.env`에 진짜 키 넣기**
```
CREATOMATE_API_KEY=진짜키12345
```
> `.env`가 `.gitignore`에 들어 있는지 꼭 확인합니다. GitHub Desktop 변경 목록에 `.env`가 보이면 **절대 commit하지 않습니다.**

**② `.env.example`의 `# ===== media =====` 아래에 더미 키 안내 추가**
```
# ===== media =====
# 영상 생성 Creatomate API 키 (발급: creatomate.com)
CREATOMATE_API_KEY=your_creatomate_api_key_here
```

**③ 코드에서는 이름으로만 불러오기**
```python
# modules/media/media_server.py
import os

CREATOMATE_API_KEY = os.getenv("CREATOMATE_API_KEY")   # O
# CREATOMATE_API_KEY = "진짜키12345"                    # X : 키가 GitHub에 올라감
```

**④ commit하고, 진짜 키 값은 카톡이나 노션으로 공유**
- commit: `chore: .env.example에 Creatomate API 키 안내 추가`
- 팀원들은 받은 키를 각자 자기 컴퓨터의 `.env`에 넣습니다.

> 💡 키가 실수로 GitHub에 올라갔다면, 커밋을 지우는 것만으로는 부족합니다. **바로 PM에게 알리고 해당 키를 재발급**받아야 합니다.

---

## 6. Git 사용 규칙

### 6-1. 용어 정리

| 용어 | 뜻 | 쉽게 말하면 |
|---|---|---|
| **commit** | 작업 단위 저장 | 내 컴퓨터에 **세이브 포인트** 만들기 |
| **push** | 서버로 전송 | 내 컴퓨터의 commit들을 GitHub에 올려 두기 |
| **pull** | 최신 내용 받기 | GitHub의 최신 코드를 내 컴퓨터로 가져오기 |
| **branch** | 작업 공간 분리 | 일종의 **평행세계**. 혼자 마음껏 실패해도 다른 사람에게 영향 없음 |
| **pull request (PR)** | 합치기 요청 | "이 기능 완성됐으니 `develop`에 합쳐 주세요" 요청서 |
| **merge** | 합치기 | 브랜치의 작업을 다른 브랜치에 합치는 것 |
| **conflict** | 충돌 | 두 사람이 같은 줄을 다르게 고쳐서 Git이 자동으로 못 합치는 상태 |

### 6-2. 브랜치 규칙

```
main                        ← 최종 완성본 (PM만 합침, branch protection 설정)
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
| `main` | 최종 완성본, 발표/제출용 | **PM만** develop → main 합침 |
| `develop` | 모든 기능을 모아 테스트 | 팀원은 **PR로만** 올림 (직접 push 금지) |
| `feature/모듈코드-기능명` | 기능 하나를 만드는 개인 작업 공간 | 각 담당자 |
| `fix/모듈코드-기능명` | 버그 수정 | 각 담당자 |

- 브랜치 이름은 **영어 소문자 + 하이픈(`-`)**: `feature/home-calendar`, `fix/report-pdf-font`
- 항상 **내 브랜치에 push → `develop`으로 PR**합니다.
- 기능 하나가 끝나면 브랜치도 끝냅니다. 다음 기능은 최신 `develop`에서 새 브랜치를 만듭니다.

### 6-3. 매일 작업 순서 (GitHub Desktop 기준)

**① 작업 시작 전: 최신 코드 받기**
1. Current Branch → `develop` 선택 → **Fetch origin → Pull origin**
2. 새 기능이면 **New Branch**로 `feature/모듈코드-기능명` 만들기 (develop 기준)
3. 이어서 하는 작업이면 내 브랜치로 이동 → Branch 메뉴 → **Update from develop**

**② 작업 → commit**
- 기능 하나, 수정 하나 단위로 자주 commit합니다.
- Summary, Description 작성법은 [6-6. 커밋 메시지 규칙](#6-6-커밋-메시지-규칙)을 따릅니다.

**③ push → PR**
1. **Push origin**으로 내 브랜치를 GitHub에 올리기
2. **Create Pull Request** → GitHub 웹사이트에서 `base: develop` ← `compare: 내 브랜치` 확인
3. PR 설명에 무엇을 만들었는지 적고 생성

**④ 합치기**
- 팀원 → `develop`: 팀원 1명 이상이 확인(Approve)한 뒤 합칩니다.
- `develop` → `main`: PM이 전체 탭을 실행해서 확인한 뒤 합칩니다.

> 💡 PR은 **작게, 자주** 올립니다. 며칠씩 쌓아 두면 충돌이 커집니다.
> 💡 충돌이 나면 혼자 해결하지 말고, 해당 파일 담당자와 같이 해결합니다.

### 6-4. 파일 및 코드 작성 규칙

- **본인 담당 폴더(`modules/내모듈/`)의 파일만** 수정합니다.
- `server/main.py`, `common/`, `index.html` 같은 **공용 파일은 PM만** 수정합니다.
  - PM이 6개 모듈을 처음부터 다 연결해 두었기 때문에 팀원이 공용 파일을 고칠 일은 거의 없습니다.
  - 공용 파일에 꼭 추가할 내용이 있으면 직접 고치지 말고 PM에게 요청합니다.
  - 여러 명이 공용 파일 "맨 아래"에 동시에 코드를 덧붙이면 Git은 같은 줄을 고친 것으로 보고 충돌이 납니다. 그래서 덧붙이기도 PM이 합니다.
- 예외: `server/requirements.txt`, `.env.example`은 정해진 자리에 **한 줄 추가만** 할 수 있습니다.
- 들여쓰기, 줄바꿈, 띄어쓰기 같은 **사소한 변경은 다른 사람 파일과 공용 파일에서 금지**합니다.

### 6-5. 개발 환경 통일

**Python 버전과 가상환경**
- Python 버전: `3.11` (팀 확정 후 수정)
- 가상환경 폴더 이름은 `venv`로 통일합니다. `.gitignore`에 등록되어 있어서 GitHub에 올라가지 않습니다.

```bash
# 처음 한 번
python -m venv venv
venv\Scripts\activate            # Mac: source venv/bin/activate
pip install -r server/requirements.txt

# 서버 실행 (프로젝트 맨 위 폴더에서)
uvicorn server.main:app --reload
```

**새 라이브러리를 설치했다면**
- `server/requirements.txt`에 **알파벳 순서 자리에 한 줄만** 추가합니다. 맨 아래에 몰아서 추가하면 다른 사람과 충돌합니다.
- 다른 줄은 건드리지 않습니다.
- 팀 채팅에 "○○ 라이브러리 추가했어요"라고 알립니다. 다른 팀원은 pull 받은 뒤 `pip install -r server/requirements.txt`를 다시 실행합니다.
- commit은 `chore: 라이브러리명 requirements에 추가`로 남깁니다.

**VS Code 설정**
- **Prettier** 확장을 설치하고 Format On Save를 켭니다. 모두 같은 정렬 규칙(`.editorconfig`)을 쓰기 때문에 결과가 같아집니다.
- 들여쓰기, 줄바꿈, 띄어쓰기만 바꾸는 작업은 **내 파일에서만**, `style:` 커밋으로 따로 올립니다.

### 6-6. 커밋 메시지 규칙

**Summary (commit 작은 칸)**: `태그: 한 줄 요약`
- 콜론(`:`) 뒤에는 한 칸 띄웁니다.
- 한국어로 명확하게 적습니다.

**Description (설명 칸)**: 무엇을, 어떻게, 왜 바꿨는지 반드시 적습니다.

```
Summary
feat: 캘린더 일정 추가 모달창 구현

Description
[무엇을] home_script.js, home_main.html에 일정 추가 모달 추가
[어떻게] 날짜를 클릭하면 모달이 열리고, 저장하면 달력에 표시되도록 구현
[왜] 홈 화면에서 프로모션 일정을 바로 등록할 수 있게 하기 위해
```

| 태그 | 언제 쓰나요 | 예시 |
|---|---|---|
| `feat` | 새 화면, 탭, 기능, 버튼 추가 | `feat: 캘린더 일정 추가 모달창 구현` |
| `fix` | 버그 수정 | `fix: 리포트 PDF 한글 깨짐 수정` |
| `docs` | 코드는 그대로, md 파일만 수정 | `docs: 프로젝트 설치 방법 가이드 추가` |
| `style` | 코드 동작 변화 없이 들여쓰기, 줄바꿈 정리 | `style: weather_server.py 들여쓰기 4칸 통일` |
| `refactor` | 기능은 같고 코드만 다듬음 | `refactor: 중복되는 날짜 변환 함수 하나로 통합` |
| `chore` | 라이브러리 추가, 설정 파일 수정 | `chore: pandas 라이브러리 requirements에 추가` |

❌ 이런 메시지는 금지합니다: `수정`, `최종`, `ㅇㅇ`, `asdf`, `코드 고침`

---

## 7. 금지 사항 🚫

- `main`, `develop`에 직접 push하기
- `modules/내모듈/` 밖의 파일 수정하기 (열어서 저장하는 것도 포함, `requirements.txt`·`.env.example` 한 줄 추가는 예외)
- 모듈 코드 없이 id, class, 변수, 함수 이름 짓기
- 색상 코드를 직접 쓰거나 `body`, `div` 등 태그 전체에 CSS 적용하기
- `.env`, API 키 올리기, 코드에 API 키 직접 쓰기
- 100MB 이상 파일 올리기 (큰 데이터는 드라이브 링크로 공유)
- `git push --force` 사용하기

---

## 8. 공통 설정 파일 (PM이 처음에 만듭니다)

### .gitignore
```
.env
venv/
__pycache__/
.vscode/
node_modules/
.DS_Store
Thumbs.db
*.log
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

## 9. 기술 스택

| 구분 | 사용 기술 |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python (FastAPI) |
| AI | (확정 후 기재) |
| 외부 API | 날씨 API, (영상/이미지 생성 API 확정 후 기재) |
| 협업 | GitHub, GitHub Desktop, VS Code, Notion |

---

## 10. 진행 현황

- [ ] PM: 뼈대(빈 파일 구조, index.html, main.py) `develop`에 올리기
- [ ] 홈 (`home`)
- [ ] 1. 분석 리포트 (`report`)
- [ ] 2. 가설 수립 (`hypothesis`)
- [ ] 3. 매체 제작 (`media`)
- [ ] 3-1. 솔루션 제안 (`solution`)
- [ ] 4. 날씨 광고 타이밍 (`weather`)
- [ ] 전체 통합 테스트 → `main` 반영
- [ ] 최종 발표

---

## 📝 변경 이력

| 날짜 | 내용 | 작성자 |
|---|---|---|
| 2026-10-21 | README 초안 작성 | 000 |
| 2026-10-22 | 기능 구성, 파일 구조 변경 (6개 모듈), Git 규칙 통합, 충돌 방지 규칙 추가 | 000 |
| 2026-10-22 | 파일 구조 정리: routers/, assets/, data/processed/ 삭제 → 모듈별 서버, 이미지, 데이터를 각 모듈 폴더로 이동 | 000 |
| 2026-10-23 | 보안 및 환경 변수 관리(.env, .env.example 작성 예시) 추가, 파일 및 코드 작성 규칙 추가 | 000 |
