# 2. 가설 수립
from pathlib import Path

import streamlit as st

import ui_theme as ui

HYPOTHESIS_DIR = Path(__file__).resolve().parent   # 내 폴더 (images/, data/ 경로 만들 때 사용)


def hypothesis_render():
    """'2. 가설 수립' 탭을 열 때마다 실행됩니다. 화면은 전부 이 함수 안에서 그립니다."""
    ui.page_header("2. 가설 수립", "문제 해결 가설 제안 (현지 특성 반영)")

    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("**가설 A** (내용이 들어갈 자리)")
    with c2:
        with st.container(border=True):
            st.markdown("**가설 B** (내용이 들어갈 자리)")
    ui.share_list("경쟁사 부정 리뷰 유형 (샘플)", [("냉감 부족", "42", 0.5), ("세탁 후 변형", "25", 0.3), ("가격", "17", 0.2)])
