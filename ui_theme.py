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
