# 3. 매체 제작 + 솔루션 제안
from pathlib import Path

import streamlit as st

import ui_theme as ui
from modules.media.media_ab import media_ab_section
from modules.media.media_solution import media_solution_section

MEDIA_DIR = Path(__file__).resolve().parent   # 내 폴더 (images/, data/ 경로 만들 때 사용)


def media_render():
    """'3. 매체 제작' 탭을 열 때마다 실행됩니다. 화면은 전부 이 함수 안에서 그립니다."""
    ui.page_header("3. 매체 제작", "가설 2개 → 프롬프트 2개 → 결과물 2개 (프롬프트 다듬기)")

    c1, c2 = st.columns(2)
    for col, name in ((c1, "A"), (c2, "B")):
        with col:
            with st.container(border=True):
                st.markdown(f"**프롬프트 {name}**")
                st.text_area(f"프롬프트 {name}", key=f"media-prompt-{name}", label_visibility="collapsed")
                st.markdown(f"**결과물 {name}** (생성 결과가 들어갈 자리)")

    # 메인 이미지 A/B (media_ab.py): 1번 리포트의 검색어 클릭 분석이 있을 때만 표시
    media_ab_section()

    # 매체 외 솔루션 제안 (media_solution.py)
    media_solution_section()
