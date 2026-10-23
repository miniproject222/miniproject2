# 3. 매체 제작
from pathlib import Path

import streamlit as st

MEDIA_DIR = Path(__file__).resolve().parent   # 내 폴더 (images/, data/ 경로 만들 때 사용)


def media_render():
    """사이드바에서 '3. 매체 제작' 탭을 열 때마다 실행됩니다. 화면은 전부 이 함수 안에서 그립니다."""
    st.header("3. 매체 제작")
    st.markdown(
        '<div class="media-card"><p class="media-desc">가설 2개 → 프롬프트 2개 → 결과물 2개 (프롬프트 다듬기)</p></div>',
        unsafe_allow_html=True,
    )
