# 사이드바 메뉴, 탭 전환, 디자인 적용 (PM)
from pathlib import Path

import streamlit as st

from modules.home.home_page import home_render
from modules.hypothesis.hypothesis_page import hypothesis_render
from modules.media.media_page import media_render
from modules.report.report_page import report_render
from modules.solution.solution_page import solution_render
from modules.weather.weather_page import weather_render

ROOT_DIR = Path(__file__).resolve().parent.parent

# 탭 목록: 순서대로 사이드바에 표시됩니다
LAYOUT_TABS = [
    {"code": "home", "label": "홈", "icon": "🏠", "render": home_render},
    {"code": "report", "label": "1. 분석 리포트", "icon": "📈", "render": report_render},
    {"code": "hypothesis", "label": "2. 가설 수립", "icon": "💡", "render": hypothesis_render},
    {"code": "media", "label": "3. 매체 제작", "icon": "🎬", "render": media_render},
    {"code": "solution", "label": "3-1. 솔루션 제안", "icon": "🧩", "render": solution_render},
    {"code": "weather", "label": "4. 날씨 광고 타이밍", "icon": "🌦️", "render": weather_render},
]


def layout_load_css():
    """공통 디자인과 각 모듈의 모듈코드_style.css를 화면에 적용합니다."""
    files = [ROOT_DIR / "common" / "common_style.css"]
    files += [ROOT_DIR / "modules" / t["code"] / f"{t['code']}_style.css" for t in LAYOUT_TABS]
    css = "\n".join(p.read_text(encoding="utf-8") for p in files if p.exists())
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def layout_run():
    st.set_page_config(page_title="마케팅 솔루션 대시보드", page_icon="📊", layout="wide")
    layout_load_css()
    st.sidebar.markdown('<p class="common-logo">📊 마케팅 대시보드</p>', unsafe_allow_html=True)

    pages = [
        st.Page(
            t["render"],
            title=t["label"],
            icon=t["icon"],
            url_path=t["code"],          # 주소: /report, /weather ...
            default=t["code"] == "home",
        )
        for t in LAYOUT_TABS
    ]
    st.navigation(pages).run()
