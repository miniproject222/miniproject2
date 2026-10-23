# 대시보드 시작 파일 (PM)
# 로컬 실행: 프로젝트 맨 위 폴더에서 streamlit run app.py
# 배포: GitHub main에 올리면 Streamlit Community Cloud가 이 파일로 자동 배포합니다
# 디자인 규칙은 design.md, 공통 디자인 함수는 ui_theme.py에 있습니다
import streamlit as st

import ui_theme as ui
from common.common_layout import LAYOUT_TABS, layout_load_css

# 1) 반드시 맨 위에서 1번만
ui.apply_theme(page_title="마케팅 솔루션 대시보드", page_icon="📊")
layout_load_css()   # common_style.css + 각 모듈의 모듈코드_style.css

# 사이드바
with st.sidebar:
    st.markdown('<p class="common-logo">📊 마케팅 대시보드</p>', unsafe_allow_html=True)
    st.caption("냉감패드 · 독일 그로스 대시보드")
    show_temp = st.toggle("지역별 온도 표시", value=False)
    use_live = st.toggle("실시간 기온 (Open-Meteo)", value=False, disabled=not show_temp)


def app_get_temps():
    """토글 상태에 따라 None / 실시간 / 샘플 온도 반환"""
    if not show_temp:
        return None
    if use_live:
        live = ui.fetch_state_temperatures()
        if live:
            return live
        st.sidebar.warning("실시간 기온 조회 실패 → 샘플값으로 표시합니다.")
    return ui.sample_state_temperatures()


# 지도를 쓰는 탭은 st.session_state["temps"]를 읽어 ui.hero_layout(temps=...)에 넘깁니다
st.session_state["temps"] = app_get_temps()
if show_temp:
    st.sidebar.caption("Weather data by Open-Meteo.com" if use_live else "샘플 온도 (폭염일 가정)")

# 알약형 탭: 각 모듈의 모듈코드_render()가 탭 안을 그립니다
tabs = st.tabs([f"{t['icon']} {t['label']}" for t in LAYOUT_TABS])
for tab, t in zip(tabs, LAYOUT_TABS):
    with tab:
        t["render"]()
