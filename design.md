# DESIGN.md — MODO Germany Growth Dashboard (Streamlit)

> 독일 냉감패드 그로스 대시보드의 **Streamlit 디자인 가이드**입니다.
> 레이아웃은 레퍼런스(General statistics 대시보드)의 3단 카드 구조를 따르고,
> 색상은 지정 팔레트 6색, 중앙 비주얼은 **독일 지도 이미지**를 사용합니다.
> 지역별 온도는 같은 이미지 위에 겹쳐 표시하도록 설계되어 있습니다.
> 모든 디자인은 `ui_theme.py` 한 파일에서 관리하며, 각 탭은 그 함수만 불러 씁니다.

---

## 1. 폴더 구조

```
project/
├── README.md
├── design.md                     ← 이 문서
├── app.py                        ← 탭 구성 (홈 · 퍼널 · 경쟁/팝업 · A/B)
├── ui_theme.py                   ← 팔레트 · CSS · 공통 카드 · 독일 지도/온도
├── make_germany_image.py         ← GeoJSON → assets/germany.png 생성 (최초 1회)
├── requirements.txt
├── .streamlit/
│   └── config.toml               ← 라이트 모드 고정 + 기본 색
└── assets/
    ├── germany_states.geojson    ← 독일 16개 주 경계 (출처: github.com/isellsoap/deutschlandGeoJSON)
    └── germany.png               ← 중앙에 표시되는 독일 지도 이미지
```

**실행 순서**
```bash
pip install -r requirements.txt
python make_germany_image.py      # assets/germany.png 생성 (색을 바꿨을 때만 다시 실행)
streamlit run app.py
```

**requirements.txt**
```
streamlit>=1.40
plotly>=5.20
pandas>=2.0
requests>=2.31
matplotlib>=3.8
```

**원칙**
- 탭 파일 안에서 색상 코드(`#...`)나 `<style>`을 직접 쓰지 않습니다. 모두 `ui_theme.py`에서 가져옵니다.
- 새 컴포넌트가 필요하면 `ui_theme.py`에 함수로 추가합니다.
- 중앙 비주얼은 `ui.hero_layout()` 또는 `ui.germany_visual()` 하나로 통일합니다.

---

## 2. 색상

### 2-1. 팔레트

| 이름 | HEX | 의미 |
|---|---|---|
| 파스텔 보라 (lavender) | `#C4C3E3` | 독일 지도 면, 보조 막대, 서늘한 온도 |
| 다크 보라 (violet) | `#504E76` | 텍스트, 활성 탭, 버튼, 핵심 수치 |
| 라이트 베이지 (beige) | `#FDF8E2` | 페이지 배경, 진행바 트랙 |
| 라이트 그린 (green) | `#A3B565` | 계열 3번, 증가(▲) 배지 기준색 |
| 라이트 오렌지 (peach) | `#FCDD9D` | 계열 4번, 따뜻한 온도 |
| 오렌지 (orange) | `#F1642E` | 계열 5번, 더운 온도, 감소(▼) 배지 기준색 |

### 2-2. 역할별 토큰 (`THEME`)

| 토큰 | 값 | 용도 |
|---|---|---|
| `bg` | `#FDF8E2` | 페이지 배경 |
| `card` | `#FFFFFF` | 카드 배경 |
| `text` | `#504E76` | 제목·본문·숫자 |
| `muted` | `#8C8AA8` | 라벨·보조 설명 (다크 보라를 밝힌 파생색) |
| `primary` / `primary_hover` | `#504E76` / `#3F3D61` | 활성 탭·버튼 |
| `primary_soft` | `#C4C3E3` | 연한 강조 |
| `accent` | `#F1642E` | 화면당 1곳 강조 (더위·경고) |
| `up_bg` / `up_text` | `#EEF2DD` / `#5E6B2E` | 증가 배지 |
| `down_bg` / `down_text` | `#FDE3D8` / `#B9441A` | 감소 배지 |

### 2-3. 사용 규칙
- **계열 순서는 고정**: 다크 보라 → 파스텔 보라 → 그린 → 피치 → 오렌지 (`SERIES`). 탭이 달라도 같은 항목은 같은 색을 유지합니다.
- **증감 배지는 연한 배경 + 진한 글자**로 씁니다. 그린(`#A3B565`)·오렌지(`#F1642E`)를 흰 배경 위 작은 글자색으로 쓰면 대비가 부족해 읽기 어렵습니다. 화살표(▲▼)를 항상 함께 표시해 색만으로 의미를 전달하지 않습니다.
- **오렌지는 아껴 씁니다**: 냉감패드의 핵심 메시지인 "더위"를 상징하는 색이므로, 온도·경고 외의 장식에는 쓰지 않습니다.
- **온도 색 구간**: 파스텔 보라(서늘) → 피치(따뜻) → 오렌지(더움), 기본 범위 10~35°C (`TEMP_SCALE`).

---

## 3. 타이포그래피

Pretendard (CDN), 없으면 Noto Sans KR

| 용도 | 크기 / 굵기 | 색 |
|---|---|---|
| 페이지 제목 | 26px / 700 | text |
| 대형 숫자 | 42px / 700 | text |
| 카드 숫자 | 30px / 700 | text |
| 라벨 | 13px / 400 | muted |
| 보조 설명 | 11px / 400 | muted |
| 증감 배지 | 12px / 600 | up_text · down_text |

---

## 4. 레이아웃

```
┌──────────┬───────────────────────────────────────────────┐
│          │ 페이지 제목 / 설명                            │
│ 사이드바 │ (홈) (퍼널 분석) (경쟁·팝업) (A/B 테스트)      │ ← 알약형 탭
│ - 온도   ├─────────────┬─────────────────┬──────────────┤
│   토글   │  좌측 카드   │   독일 지도      │  우측 카드    │ ← hero_layout (1 : 2 : 1)
│ - 실시간 │  KPI · 목록  │  (+ 지역별 온도) │  예측 · 진행  │
└──────────┴─────────────┴─────────────────┴──────────────┘
```

- 지도가 필요한 탭: `ui.hero_layout(left, right, temps=..., key="탭별_고유키")`
- 지도가 필요 없는 탭: `st.columns(4)` + `ui.kpi_card()` 행, 본문은 `st.container(border=True)` 카드
- `key`는 탭마다 다르게 지정합니다. 같은 지도를 두 탭에서 쓰면 Streamlit 요소 ID가 겹쳐 오류가 납니다.

---

## 5. 컴포넌트

| 함수 | 설명 | 레퍼런스 대응 |
|---|---|---|
| `apply_theme(page_title)` | `set_page_config` + 전역 CSS. 앱 맨 위에서 1번 | — |
| `page_header(title, caption)` | 탭 제목·설명 | General statistics |
| `kpi_card(label, value, delta, sub, big)` | 숫자 카드, `delta="+14%"` / `"-3%"` | All users, Forecast |
| `share_list(title, rows)` | 비율 바 + 목록, `rows=[(이름, 값, 비율)]` | Current activity |
| `progress_list(title, value, rows)` | 항목별 진행 막대 | Time Statistic |
| `germany_visual(temps, height, temp_range, key)` | 독일 지도 이미지, `temps`가 있으면 온도 오버레이 | 중앙 지구 |
| `hero_layout(left, right, **kwargs)` | 3단 레이아웃 | 전체 화면 |
| `fetch_state_temperatures()` | Open-Meteo 16개 주 현재 기온 (1시간 캐시) | — |
| `sample_state_temperatures()` | API 연결 전 샘플 기온 | — |

---

## 6. 독일 지도 · 지역별 온도 설계

**왜 사진(이미지) 위에 온도를 겹치는가**
- `make_germany_image.py`가 독일 16개 주 경계(GeoJSON)를 팔레트 색으로 그려 `germany.png`를 만듭니다.
- 이미지의 경도·위도 범위를 `GERMANY_BBOX`(경도 5.8~15.1, 위도 47.2~55.1)로 고정해 저장합니다.
- 온도를 표시할 때는 같은 범위를 좌표축으로 쓰는 Plotly 그래프에 이 이미지를 배경으로 깔고, 도시 위도·경도에 온도 원을 찍습니다. 그래서 이미지와 점이 정확히 맞습니다.
- 위도 51° 부근은 경도 1°가 위도 1°보다 짧으므로, 세로 비율을 `1/cos(위도)`(약 1.6)로 보정합니다.

**표시 모드**

| 사이드바 설정 | 화면 |
|---|---|
| 지역별 온도 OFF | 독일 지도 이미지만 (`st.image`) |
| 지역별 온도 ON | 이미지 + 16개 지역 온도 원 (샘플값) |
| + 실시간 기온 ON | Open-Meteo 현재 기온, 실패 시 샘플값으로 자동 대체 |

**기준 지점**: 16개 주의 대표 도시 1곳씩. 대부분 주도이고, 지도에서 Berlin과 겹치는 Brandenburg는 Cottbus, Wiesbaden과 겹치는 Rheinland-Pfalz는 Koblenz를 씁니다.

**이미지 교체 시 주의**
- 다른 독일 지도 이미지를 쓰려면 **경도 5.8~15.1, 위도 47.2~55.1 범위로 잘린 이미지**여야 온도 위치가 맞습니다. 범위가 다르면 `GERMANY_BBOX` 값을 이미지에 맞게 수정합니다.
- 브란덴부르크 문 같은 풍경 사진은 온도 오버레이용으로 맞지 않습니다. 배너 이미지로만 쓰고, 온도는 지도 이미지에 표시합니다.
- 지도 색을 바꾸면 `python make_germany_image.py`를 다시 실행합니다.

**추후 확장 방향**
- 주 경계 면 자체를 온도 색으로 칠하는 방식(choropleth)은 `assets/germany_states.geojson`의 `name` 속성(예: `Bayern`)을 키로 연결하면 됩니다.
- 기온 데이터는 Open-Meteo `current=temperature_2m` 외에, 성수기 분석용으로 `archive-api.open-meteo.com`의 과거 일별 최고기온(`temperature_2m_max`)을 쓰면 "폭염일수 × 판매량" 분석으로 연결할 수 있습니다.
- Open-Meteo는 비상업 무료이며, 화면에 `Weather data by Open-Meteo.com` 표기가 필요합니다(앱 사이드바에 자동 표기). 상업 서비스로 전환하면 유료 키가 필요합니다.

---

## 7. 새 탭 추가 절차

1. `app.py`의 `st.tabs([...])`에 탭 이름을 추가하고 변수 하나를 받습니다.
2. `with 새탭:` 블록 첫 줄에 `ui.page_header("제목", "설명")`
3. 지도가 필요하면 `ui.hero_layout(left, right, temps=temps, key="새탭_map")`, 필요 없으면 `st.columns` + `ui.kpi_card`
4. 새 스타일이 필요하면 탭이 아니라 `ui_theme.py`에 함수로 추가합니다.

## 8. 주의사항

- 화면의 숫자는 모두 **샘플 데이터**입니다. 발표 자료에서는 출처 또는 "가정값"을 명시합니다.
- 샘플 기온은 "여름 폭염일, 북쪽 서늘·남쪽 더움"을 가정한 값입니다. 실제 관측값이 아닙니다.
- `.streamlit/config.toml`에서 `theme.base = "light"`로 고정해, 사용자의 다크 모드 설정과 관계없이 같은 색으로 보이게 했습니다.

---

## 9. 전체 코드

### 9-1. ui_theme.py

```python
"""
ui_theme.py
독일 프로젝트(MODO 냉감패드) 공통 UI 테마 모듈 — Streamlit

- 팔레트: 파스텔 보라 #C4C3E3 / 다크 보라 #504E76 / 라이트 베이지 #FDF8E2
          라이트 그린 #A3B565 / 라이트 오렌지 #FCDD9D / 오렌지 #F1642E
- 중앙 비주얼: 지구본 대신 독일 지도 이미지(assets/germany.png)
- 지역별 온도: germany_visual(temps=[...]) 로 같은 이미지 위에 겹쳐 표시
- 모든 탭에서 import 해서 같은 함수로 재사용
"""

from __future__ import annotations

import base64
import math
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import plotly.graph_objects as go
import streamlit as st

BASE = Path(__file__).parent
GERMANY_IMAGE = BASE / "assets" / "germany.png"

# ─────────────────────────────────────────────
# 1. 팔레트 (레퍼런스 색상 그대로)
# ─────────────────────────────────────────────
PALETTE = {
    "lavender": "#C4C3E3",   # 파스텔 보라
    "violet": "#504E76",     # 다크 보라
    "beige": "#FDF8E2",      # 라이트 베이지
    "green": "#A3B565",      # 차분한 라이트 그린
    "peach": "#FCDD9D",      # 라이트 오렌지
    "orange": "#F1642E",     # 오렌지
}

# ─────────────────────────────────────────────
# 2. 디자인 토큰 (역할별 색) — 여기만 바꾸면 전 탭 반영
# ─────────────────────────────────────────────
THEME = {
    "bg": PALETTE["beige"],
    "card": "#FFFFFF",
    "text": PALETTE["violet"],
    "muted": "#8C8AA8",              # 다크 보라를 밝힌 보조 텍스트
    "line": "#EFEDE0",
    "primary": PALETTE["violet"],    # 활성 탭, 버튼, 핵심 숫자
    "primary_hover": "#3F3D61",
    "primary_soft": PALETTE["lavender"],
    "accent": PALETTE["orange"],     # 강조 1곳 (더위·경고)
    # 증감 배지: 원색은 흰 배경 위 글자 대비가 낮아, 배경은 연하게·글자는 진하게
    "up_bg": "#EEF2DD", "up_text": "#5E6B2E",
    "down_bg": "#FDE3D8", "down_text": "#B9441A",
    "radius": "18px",
    "shadow": "0 8px 24px rgba(80, 78, 118, 0.08)",
}

# 목록·막대·차트 계열 색 순서
SERIES = [PALETTE["violet"], PALETTE["lavender"], PALETTE["green"], PALETTE["peach"], PALETTE["orange"]]

# 온도 색 구간: 서늘함(보라) → 따뜻함(피치) → 더움(오렌지)
TEMP_SCALE = [[0.0, PALETTE["lavender"]], [0.5, PALETTE["peach"]], [1.0, PALETTE["orange"]]]

# 독일 지도 이미지의 경도·위도 범위 (make_germany_image.py 와 공유)
GERMANY_BBOX = {"lon": (5.8, 15.1), "lat": (47.2, 55.1)}

# 16개 주 대표 도시 (지역별 온도 표시 기준점)
# 대부분 주도이며, 지도에서 겹치는 Brandenburg(Potsdam↔Berlin), Rheinland-Pfalz(Mainz↔Wiesbaden)는 다른 도시로 대체
GERMAN_STATES = [
    {"state": "Schleswig-Holstein",     "city": "Kiel",        "lat": 54.32, "lon": 10.14},
    {"state": "Hamburg",                "city": "Hamburg",     "lat": 53.55, "lon": 9.99},
    {"state": "Mecklenburg-Vorpommern", "city": "Schwerin",    "lat": 53.63, "lon": 11.41},
    {"state": "Bremen",                 "city": "Bremen",      "lat": 53.08, "lon": 8.80},
    {"state": "Niedersachsen",          "city": "Hannover",    "lat": 52.37, "lon": 9.73},
    {"state": "Berlin",                 "city": "Berlin",      "lat": 52.52, "lon": 13.40},
    {"state": "Brandenburg",            "city": "Cottbus",     "lat": 51.76, "lon": 14.33},
    {"state": "Sachsen-Anhalt",         "city": "Magdeburg",   "lat": 52.12, "lon": 11.63},
    {"state": "Nordrhein-Westfalen",    "city": "Düsseldorf",  "lat": 51.23, "lon": 6.78},
    {"state": "Sachsen",                "city": "Dresden",     "lat": 51.05, "lon": 13.74},
    {"state": "Thüringen",              "city": "Erfurt",      "lat": 50.98, "lon": 11.03},
    {"state": "Hessen",                 "city": "Wiesbaden",   "lat": 50.08, "lon": 8.24},
    {"state": "Rheinland-Pfalz",        "city": "Koblenz",     "lat": 50.36, "lon": 7.59},
    {"state": "Saarland",               "city": "Saarbrücken", "lat": 49.24, "lon": 6.99},
    {"state": "Bayern",                 "city": "München",     "lat": 48.14, "lon": 11.58},
    {"state": "Baden-Württemberg",      "city": "Stuttgart",   "lat": 48.78, "lon": 9.18},
]


# ─────────────────────────────────────────────
# 3. 전역 CSS (앱 시작 시 1번만 호출)
# ─────────────────────────────────────────────
def apply_theme(page_title: str = "MODO Growth Dashboard", page_icon: str = "🇩🇪") -> None:
    """st.set_page_config + 전역 CSS 주입. 앱 파일 맨 위에서 1번만 호출."""
    st.set_page_config(page_title=page_title, page_icon=page_icon, layout="wide")
    t = THEME
    st.markdown(
        f"""
        <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');

        html, body, [data-testid="stAppViewContainer"] {{
            background: {t['bg']};
            color: {t['text']};
            font-family: 'Pretendard', 'Noto Sans KR', sans-serif;
        }}
        [data-testid="stHeader"] {{ background: transparent; }}
        .block-container {{ padding-top: 2rem; max-width: 1400px; }}
        h1, h2, h3, p, label {{ color: {t['text']}; }}

        /* 사이드바 */
        [data-testid="stSidebar"] {{
            background: {t['card']};
            border-right: 1px solid {t['line']};
        }}

        /* 탭: 알약형 */
        .stTabs [data-baseweb="tab-list"] {{ gap: 8px; }}
        .stTabs [data-baseweb="tab"] {{
            background: {t['card']};
            border-radius: 999px;
            padding: 8px 18px;
            box-shadow: {t['shadow']};
            color: {t['muted']};
        }}
        .stTabs [aria-selected="true"] {{
            background: {t['primary']} !important;
            color: #FFFFFF !important;
        }}
        .stTabs [aria-selected="true"] p {{ color: #FFFFFF !important; }}
        .stTabs [data-baseweb="tab-highlight"],
        .stTabs [data-baseweb="tab-border"] {{ display: none; }}

        /* st.container(border=True) → 카드 */
        [data-testid="stVerticalBlockBorderWrapper"] {{
            background: {t['card']};
            border: none !important;
            border-radius: {t['radius']};
            box-shadow: {t['shadow']};
        }}

        /* 버튼 */
        .stButton > button {{
            background: {t['primary']};
            color: #FFFFFF;
            border: none;
            border-radius: 12px;
            padding: 0.5rem 1.2rem;
        }}
        .stButton > button:hover {{ background: {t['primary_hover']}; color: #FFFFFF; }}

        /* 토글 활성 색 */
        [data-testid="stToggle"] [aria-checked="true"] {{ background: {t['primary']} !important; }}

        /* 커스텀 카드 */
        .ui-card {{
            background: {t['card']};
            border-radius: {t['radius']};
            box-shadow: {t['shadow']};
            padding: 18px 20px;
            margin-bottom: 14px;
        }}
        .ui-label {{ font-size: 13px; color: {t['muted']}; margin-bottom: 4px; }}
        .ui-value {{ font-size: 30px; font-weight: 700; color: {t['text']}; line-height: 1.2; }}
        .ui-value.big {{ font-size: 42px; }}
        .ui-delta {{
            display: inline-block; font-size: 12px; font-weight: 600;
            padding: 2px 8px; border-radius: 999px; margin-left: 6px; vertical-align: middle;
        }}
        .ui-delta.up {{ background: {t['up_bg']}; color: {t['up_text']}; }}
        .ui-delta.down {{ background: {t['down_bg']}; color: {t['down_text']}; }}
        .ui-sub {{ font-size: 11px; color: {t['muted']}; margin-top: 2px; }}
        .ui-title {{ font-size: 26px; font-weight: 700; color: {t['text']}; margin-bottom: 2px; }}
        .ui-caption {{ font-size: 13px; color: {t['muted']}; margin-bottom: 18px; }}
        .ui-row {{
            display: grid; grid-template-columns: 1fr auto 44px; gap: 8px; align-items: center;
            font-size: 13px; padding: 6px 0; border-bottom: 1px solid {t['line']};
        }}
        .ui-row:last-child {{ border-bottom: none; }}
        .ui-dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; }}
        .ui-track {{ height: 6px; border-radius: 6px; background: {PALETTE['beige']}; margin: 4px 0 10px; }}
        .ui-track > span {{ display: block; height: 100%; border-radius: 6px; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# 4. 공통 컴포넌트
# ─────────────────────────────────────────────
def page_header(title: str, caption: str = "") -> None:
    """각 탭 상단 제목."""
    st.markdown(
        f'<div class="ui-title">{title}</div><div class="ui-caption">{caption}</div>',
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, delta: str | None = None, sub: str = "", big: bool = False) -> None:
    """숫자 카드. delta 는 '+14%' 또는 '-3%' 형식."""
    delta_html = ""
    if delta:
        down = delta.strip().startswith("-")
        arrow = "▼" if down else "▲"
        text = delta.strip().lstrip("+-")
        delta_html = f'<span class="ui-delta {"down" if down else "up"}">{arrow} {text}</span>'
    st.markdown(
        f"""
        <div class="ui-card">
            <div class="ui-label">{label}</div>
            <div class="ui-value {'big' if big else ''}">{value}{delta_html}</div>
            <div class="ui-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def share_list(title: str, rows: Iterable[tuple[str, str, float]]) -> None:
    """비율 바 + 목록. rows = [(이름, 값표시, 비율0~1), ...]"""
    rows = list(rows)
    bar = "".join(
        f'<span style="display:inline-block;width:{r[2]*100:.1f}%;height:6px;background:{SERIES[i % len(SERIES)]};"></span>'
        for i, r in enumerate(rows)
    )
    items = "".join(
        f"""<div class="ui-row">
              <span><span class="ui-dot" style="background:{SERIES[i % len(SERIES)]}"></span>{name}</span>
              <span>{val}</span>
              <span class="ui-sub" style="text-align:right">{ratio*100:.0f}%</span>
            </div>"""
        for i, (name, val, ratio) in enumerate(rows)
    )
    st.markdown(
        f"""
        <div class="ui-card">
            <div class="ui-label" style="font-weight:600;color:{THEME['text']}">{title}</div>
            <div style="display:flex;border-radius:6px;overflow:hidden;margin:6px 0 10px;">{bar}</div>
            {items}
        </div>
        """,
        unsafe_allow_html=True,
    )


def progress_list(title: str, value: str, rows: Iterable[tuple[str, str, float]]) -> None:
    """항목별 진행 막대. rows = [(라벨, 값표시, 비율0~1), ...]"""
    items = "".join(
        f"""<div style="display:flex;justify-content:space-between;font-size:12px;">
              <span>{name}</span><span class="ui-sub">{val}</span></div>
            <div class="ui-track"><span style="width:{ratio*100:.0f}%;background:{SERIES[i % len(SERIES)]}"></span></div>"""
        for i, (name, val, ratio) in enumerate(rows)
    )
    st.markdown(
        f"""
        <div class="ui-card">
            <div class="ui-label">{title}</div>
            <div class="ui-value">{value}</div>
            <div style="margin-top:10px;">{items}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# 5. 독일 지도 이미지 + 지역별 온도 오버레이
# ─────────────────────────────────────────────
@lru_cache(maxsize=4)
def _image_data_uri(path: str) -> str:
    data = Path(path).read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode()


def germany_visual(
    temps: list[dict] | None = None,
    image_path: Path | str = GERMANY_IMAGE,
    height: int = 560,
    temp_range: tuple[float, float] = (10, 35),
    key: str = "germany_map",
) -> None:
    """
    독일 지도 이미지를 표시.
    - temps 가 없으면: 이미지만 표시
    - temps 가 있으면: 같은 이미지 위에 지역별 온도 원(색=온도)과 '29°' 라벨을 겹쳐 표시
      temps 형식: [{'city','lat','lon','temp'}] (GERMAN_STATES + 온도값)
    - key: 여러 탭에서 쓸 때 탭마다 다른 값으로 지정 (Streamlit 요소 ID 중복 방지)
    """
    image_path = Path(image_path)
    if not image_path.exists():
        st.warning("assets/germany.png 가 없습니다. `python make_germany_image.py` 를 먼저 실행하세요.")
        return

    # 온도 없이 사진만 → st.image (가장 가볍고 선명)
    if not temps:
        st.image(str(image_path), width="stretch")
        return

    lon_min, lon_max = GERMANY_BBOX["lon"]
    lat_min, lat_max = GERMANY_BBOX["lat"]
    k = 1 / math.cos(math.radians((lat_min + lat_max) / 2))
    lo, hi = temp_range

    fig = go.Figure()
    fig.add_layout_image(
        source=_image_data_uri(str(image_path)),
        xref="x", yref="y",
        x=lon_min, y=lat_max,
        sizex=lon_max - lon_min, sizey=lat_max - lat_min,
        sizing="stretch", layer="below",
    )
    fig.add_trace(
        go.Scatter(
            x=[p["lon"] for p in temps],
            y=[p["lat"] for p in temps],
            mode="markers+text",
            text=[f"{p['temp']:.0f}°" for p in temps],
            textposition="middle center",
            textfont=dict(size=11, color=THEME["text"], family="Pretendard"),
            marker=dict(
                size=34,
                color=[p["temp"] for p in temps],
                colorscale=TEMP_SCALE,
                cmin=lo, cmax=hi,
                line=dict(color="#FFFFFF", width=2),
                colorbar=dict(
                    title=dict(text="°C", font=dict(color=THEME["muted"])),
                    thickness=10, len=0.5, outlinewidth=0,
                    tickfont=dict(color=THEME["muted"]),
                ),
            ),
            customdata=[[p.get("city", ""), p.get("state", "")] for p in temps],
            hovertemplate="%{customdata[0]} (%{customdata[1]})<br>%{marker.color:.1f}°C<extra></extra>",
        )
    )
    fig.update_xaxes(range=[lon_min, lon_max], visible=False, fixedrange=True)
    fig.update_yaxes(range=[lat_min, lat_max], visible=False, fixedrange=True,
                     scaleanchor="x", scaleratio=k)
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=key)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_state_temperatures() -> list[dict]:
    """
    Open-Meteo(무료·키 불필요)에서 16개 주도의 현재 기온을 한 번에 조회.
    실패하면 빈 리스트 반환 → 호출부에서 샘플값으로 대체.
    상업적 서비스로 전환 시 유료 키 필요, 화면에 'Weather data by Open-Meteo.com' 표기.
    """
    import requests

    params = {
        "latitude": ",".join(str(s["lat"]) for s in GERMAN_STATES),
        "longitude": ",".join(str(s["lon"]) for s in GERMAN_STATES),
        "current": "temperature_2m",
        "timezone": "Europe/Berlin",
    }
    try:
        res = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        data = data if isinstance(data, list) else [data]
        return [
            {**s, "temp": float(d["current"]["temperature_2m"])}
            for s, d in zip(GERMAN_STATES, data)
        ]
    except Exception:
        return []


def sample_state_temperatures() -> list[dict]:
    """API 연결 전 화면 확인용 샘플 (여름 폭염일 가정: 북쪽 서늘·남쪽 더움)."""
    sample = [24, 26, 25, 27, 29, 31, 31, 30, 30, 32, 30, 31, 31, 30, 33, 33]
    return [{**s, "temp": float(t)} for s, t in zip(GERMAN_STATES, sample)]


def hero_layout(left, right, ratio=(1, 2, 1), **visual_kwargs) -> None:
    """
    3단 레이아웃: [좌측 카드 | 중앙 독일 지도 | 우측 카드]
    left, right 는 인자 없는 함수(카드를 그리는 함수) → 탭마다 내용만 바꿔 재사용
    visual_kwargs 는 germany_visual() 로 전달 (예: temps=..., key="home_map")
    """
    c1, c2, c3 = st.columns(ratio, gap="large")
    with c1:
        left()
    with c2:
        germany_visual(**visual_kwargs)
    with c3:
        right()
```

### 9-2. app.py

```python
"""
app.py
MODO 독일 냉감패드 그로스 대시보드 — ui_theme 공통 디자인을 4개 탭에 적용
실행:
    python make_germany_image.py   # 최초 1회 (assets/germany.png 생성)
    streamlit run app.py
"""

import pandas as pd
import streamlit as st

import ui_theme as ui

# 1) 반드시 맨 위에서 1번만
ui.apply_theme(page_title="MODO Growth · Germany")

# 사이드바
with st.sidebar:
    st.markdown("### MODO")
    st.caption("냉감패드 · 독일 그로스 대시보드")
    show_temp = st.toggle("지역별 온도 표시", value=False)
    use_live = st.toggle("실시간 기온 (Open-Meteo)", value=False, disabled=not show_temp)


def get_temps():
    """토글 상태에 따라 None / 실시간 / 샘플 온도 반환"""
    if not show_temp:
        return None
    if use_live:
        live = ui.fetch_state_temperatures()
        if live:
            return live
        st.sidebar.warning("실시간 기온 조회 실패 → 샘플값으로 표시합니다.")
    return ui.sample_state_temperatures()


temps = get_temps()
if show_temp:
    st.sidebar.caption("Weather data by Open-Meteo.com" if use_live else "샘플 온도 (폭염일 가정)")

tab_home, tab_funnel, tab_compete, tab_ab = st.tabs(
    ["🏠 홈", "📉 퍼널 분석", "🏷 경쟁·팝업 위치", "🧪 A/B 테스트"]
)

# ─────────────────────────────────────────────
# 탭 1. 홈
# ─────────────────────────────────────────────
with tab_home:
    ui.page_header("General statistics", "독일 시장 냉감패드 판매 현황 (샘플 데이터)")

    def home_left():
        ui.kpi_card("총 방문자", "128,430", "+14%", "전년 동기 대비", big=True)
        ui.share_list(
            "도시별 활동",
            [("Berlin", "38,520", 0.30), ("München", "32,100", 0.25),
             ("Hamburg", "25,700", 0.20), ("Köln", "19,300", 0.15), ("Frankfurt", "12,810", 0.10)],
        )

    def home_right():
        ui.kpi_card("월 매출 예측", "€32,875", "+14%", "전월 €21,450")
        ui.kpi_card("연 매출 예측", "€387,122", "+12%", "전년 €321,000")
        ui.progress_list(
            "시즌 판매량", "16,073",
            [("6월", "4,820", 0.55), ("7월", "6,930", 0.80), ("8월", "4,323", 0.50)],
        )

    ui.hero_layout(home_left, home_right, temps=temps, key="home_map")

# ─────────────────────────────────────────────
# 탭 2. 퍼널 분석 (지도 없이 카드만 재사용)
# ─────────────────────────────────────────────
with tab_funnel:
    ui.page_header("퍼널 분석", "방문 → 상품조회 → 장바구니 → 결제시작 → 결제완료")

    funnel = pd.DataFrame(
        {"단계": ["방문", "상품조회", "장바구니", "결제시작", "결제완료"],
         "사용자": [128430, 51200, 9800, 4100, 2050]}
    )
    funnel["전환율(%)"] = (funnel["사용자"] / funnel["사용자"].shift(1) * 100).round(1)

    k1, k2, k3, k4 = st.columns(4)
    with k1: ui.kpi_card("방문", f"{funnel['사용자'][0]:,}")
    with k2: ui.kpi_card("장바구니 전환", f"{funnel['전환율(%)'][2]}%", "-2.1%")
    with k3: ui.kpi_card("결제시작 전환", f"{funnel['전환율(%)'][3]}%", "+1.4%")
    with k4: ui.kpi_card("결제완료 전환", f"{funnel['전환율(%)'][4]}%", "-4.8%")

    with st.container(border=True):
        st.dataframe(funnel, width="stretch", hide_index=True)

# ─────────────────────────────────────────────
# 탭 3. 경쟁·팝업 위치 (같은 독일 지도 재사용)
# ─────────────────────────────────────────────
with tab_compete:
    ui.page_header("경쟁 제품 · 팝업 위치 제안", "지역별 온도를 켜면 더운 지역부터 팝업 후보를 비교할 수 있습니다")

    def compete_left():
        ui.kpi_card("경쟁 제품 수 (Amazon.de)", "214", "+18", "냉감패드 카테고리")
        ui.share_list(
            "가격대 분포",
            [("€20 미만", "96", 0.45), ("€20~40", "75", 0.35), ("€40 이상", "43", 0.20)],
        )

    def compete_right():
        ui.progress_list(
            "팝업 후보 점수", "Berlin",
            [("Berlin", "92", 0.92), ("München", "78", 0.78), ("Hamburg", "61", 0.61)],
        )
        if temps:
            hottest = sorted(temps, key=lambda p: p["temp"], reverse=True)[:3]
            ui.progress_list(
                "기온 상위 지역", f"{hottest[0]['city']} {hottest[0]['temp']:.0f}°",
                [(p["city"], f"{p['temp']:.0f}°C", min(p["temp"] / 40, 1)) for p in hottest],
            )

    ui.hero_layout(compete_left, compete_right, temps=temps, key="compete_map")

# ─────────────────────────────────────────────
# 탭 4. A/B 테스트
# ─────────────────────────────────────────────
with tab_ab:
    ui.page_header("A/B 테스트", "결제수단 노출 순서 실험 (Klarna 우선 vs PayPal 우선)")
    a, b, c = st.columns(3)
    with a: ui.kpi_card("A안 전환율", "48.2%")
    with b: ui.kpi_card("B안 전환율", "52.9%", "+9.8%")
    with c: ui.kpi_card("p-value", "0.031", sub="유의수준 0.05 기준 유의")
    if st.button("결과 기록하기"):
        st.success("실험 로그에 저장했습니다 (예시).")
```

### 9-3. make_germany_image.py

```python
"""
make_germany_image.py
assets/germany_states.geojson(독일 16개 주 경계) → assets/germany.png 생성

- 팔레트 색으로 칠한 독일 지도 이미지를 만듭니다.
- 이미지 범위(경도·위도)를 ui_theme.GERMANY_BBOX 와 정확히 맞춰 저장하므로,
  나중에 지역별 온도를 같은 좌표로 이미지 위에 겹쳐 표시할 수 있습니다.
- 실행: python make_germany_image.py   (최초 1회, 색을 바꿨을 때만 다시 실행)
"""

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

from ui_theme import GERMANY_BBOX, PALETTE

BASE = Path(__file__).parent
GEOJSON = BASE / "assets" / "germany_states.geojson"
OUT = BASE / "assets" / "germany.png"


def iter_rings(geometry):
    """Polygon / MultiPolygon 의 외곽 링 좌표만 꺼냄"""
    if geometry["type"] == "Polygon":
        yield geometry["coordinates"][0]
    elif geometry["type"] == "MultiPolygon":
        for poly in geometry["coordinates"]:
            yield poly[0]


def main() -> None:
    data = json.loads(GEOJSON.read_text(encoding="utf-8"))

    lon_min, lon_max = GERMANY_BBOX["lon"]
    lat_min, lat_max = GERMANY_BBOX["lat"]
    # 위도 51° 부근에서 경도 1°가 위도 1°보다 짧으므로 세로 비율 보정
    k = 1 / math.cos(math.radians((lat_min + lat_max) / 2))
    height_in = 12
    width_in = height_in * (lon_max - lon_min) / ((lat_max - lat_min) * k)

    fig = plt.figure(figsize=(width_in, height_in), dpi=120)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)
    ax.set_aspect(k)
    ax.axis("off")

    for feature in data["features"]:
        for ring in iter_rings(feature["geometry"]):
            ax.add_patch(
                Polygon(
                    ring,
                    closed=True,
                    facecolor=PALETTE["lavender"],
                    edgecolor="#FFFFFF",
                    linewidth=1.6,
                    joinstyle="round",
                )
            )

    OUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUT, transparent=True)
    plt.close(fig)
    print(f"저장 완료: {OUT}")


if __name__ == "__main__":
    main()
```

### 9-4. .streamlit/config.toml

```toml
[theme]
base = "light"
primaryColor = "#504E76"
backgroundColor = "#FDF8E2"
secondaryBackgroundColor = "#FFFFFF"
textColor = "#504E76"
```

