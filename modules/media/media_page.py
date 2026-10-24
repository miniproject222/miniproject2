# 3. 매체 제작 + 솔루션 제안
from pathlib import Path

import streamlit as st

import ui_theme as ui
from modules.media.media_ab import media_ab_plan_step, media_ab_result_step
from modules.media.media_solution import media_solution_section
from modules.media.media_variable import media_variable_step

MEDIA_DIR = Path(__file__).resolve().parent   # 내 폴더 (images/, data/ 경로 만들 때 사용)

# 하위 탭(단계): (탭 이름, 화면 함수). 순서대로 '다음 단계' 버튼으로 넘어갑니다.
MEDIA_STEPS = [
    ("가설에서 변수 도출", media_variable_step),
    ("A/B 소재 준비", media_ab_plan_step),
    ("결과·판정", media_ab_result_step),
    ("솔루션 제안", media_solution_section),
]


def _media_go_step(label: str) -> None:
    """'이전/다음 단계' 버튼 콜백. 하위 탭(key="media-step")의 선택을 바꿉니다 (위젯이 그려지기 전에 실행됨)."""
    st.session_state["media-step"] = label


def media_step_nav(i: int) -> None:
    """하위 탭 맨 아래 이전/다음 단계 버튼 (이전은 왼쪽, 다음은 오른쪽)."""
    align = "right" if i == 0 else ("left" if i == len(MEDIA_STEPS) - 1 else "distribute")
    with st.container(horizontal=True, horizontal_alignment=align, key=f"media-step-nav-{i}"):
        if i > 0:
            prev = MEDIA_STEPS[i - 1][0]
            st.button(f"← {prev}", key=f"media-btn-step-prev-{i}", type="secondary",
                      on_click=_media_go_step, args=(prev,))
        if i < len(MEDIA_STEPS) - 1:
            nxt = MEDIA_STEPS[i + 1][0]
            st.button(f"다음: {nxt} →", key=f"media-btn-step-next-{i}", type="primary",
                      on_click=_media_go_step, args=(nxt,))


def media_render():
    """'3. 매체 제작' 탭을 열 때마다 실행됩니다. 화면은 전부 이 함수 안에서 그립니다."""
    # key="media-root": media_style.css가 이 탭 안의 간격만 줄이도록 범위를 정하는 class (.st-key-media-root)
    with st.container(key="media-root"):
        ui.page_header("3. 매체 제작", "가설에서 변수 도출 → A/B 소재 → 결과 → 솔루션, 단계별로 넘어가요")
        tabs = st.tabs([label for label, _ in MEDIA_STEPS], key="media-step", on_change="rerun")
        for i, (tab, (_, render)) in enumerate(zip(tabs, MEDIA_STEPS)):
            if tab.open:   # 선택된 단계만 그립니다
                with tab:
                    render()
                    media_step_nav(i)
