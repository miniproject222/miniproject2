# 2. 가설 수립
from pathlib import Path

import streamlit as st

HYPOTHESIS_DIR = Path(__file__).resolve().parent   # 내 폴더 (images/, data/ 경로 만들 때 사용)


def hypothesis_render():
    """사이드바에서 '2. 가설 수립' 탭을 열 때마다 실행됩니다. 화면은 전부 이 함수 안에서 그립니다."""
    st.header("2. 가설 수립")
    st.markdown(
        '<div class="hypothesis-card"><p class="hypothesis-desc">문제 해결 가설 제안 (현지 특성 반영)</p></div>',
        unsafe_allow_html=True,
    )
