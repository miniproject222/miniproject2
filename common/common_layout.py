# 사이드바 메뉴, 탭 전환, 디자인 적용 (PM)
from pathlib import Path

import streamlit as st

from modules.home.home_page import home_render
from modules.hypothesis.hypothesis_page import hypothesis_render
from modules.media.media_page import media_render
from modules.report.report_page import report_render
from modules.weather.weather_page import weather_render

ROOT_DIR = Path(__file__).resolve().parent.parent

# 탭 목록: 작업 순서대로 표시됩니다 (홈 → ① 문제 분석 → ② 가설 → ③ 광고 소재·솔루션 → ④ 광고 타이밍)
LAYOUT_TABS = [
    {"code": "home", "label": "홈", "icon": "🏠", "render": home_render},
    {"code": "report", "label": "문제 분석", "icon": "①", "render": report_render},
    {"code": "hypothesis", "label": "가설 세우기", "icon": "②", "render": hypothesis_render},
    {"code": "media", "label": "광고 소재·솔루션", "icon": "③", "render": media_render},
    {"code": "weather", "label": "광고 타이밍", "icon": "④", "render": weather_render},
]


def layout_load_css():
    """공통 디자인과 각 모듈의 모듈코드_style.css를 화면에 적용합니다."""
    files = [ROOT_DIR / "common" / "common_style.css"]
    files += [ROOT_DIR / "modules" / t["code"] / f"{t['code']}_style.css" for t in LAYOUT_TABS]
    css = "\n".join(p.read_text(encoding="utf-8") for p in files if p.exists())
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# 지금은 app.py가 알약형 탭(st.tabs)으로 화면을 구성합니다 (design.md). 아래는 사이드바 메뉴 방식이 필요할 때 사용
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
