# 홈
from pathlib import Path

import streamlit as st

HOME_DIR = Path(__file__).resolve().parent   # 내 폴더 (images/, data/ 경로 만들 때 사용)


def home_render():
    """사이드바에서 '홈' 탭을 열 때마다 실행됩니다. 화면은 전부 이 함수 안에서 그립니다."""
    st.header("홈")
    st.markdown(
        '<div class="home-card"><p class="home-desc">날씨, 달력, 전날 매출과 이슈 알림</p></div>',
        unsafe_allow_html=True,
    )
