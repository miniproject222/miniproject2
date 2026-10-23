# 3-1. 솔루션 제안
from pathlib import Path

import streamlit as st

SOLUTION_DIR = Path(__file__).resolve().parent   # 내 폴더 (images/, data/ 경로 만들 때 사용)


def solution_render():
    """사이드바에서 '3-1. 솔루션 제안' 탭을 열 때마다 실행됩니다. 화면은 전부 이 함수 안에서 그립니다."""
    st.header("3-1. 솔루션 제안")
    st.markdown(
        '<div class="solution-card"><p class="solution-desc">매체 외에 실행할 수 있는 솔루션 제안</p></div>',
        unsafe_allow_html=True,
    )
