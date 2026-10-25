# 3. 매체 제작 (단일 변수 → A/B 소재 → 프롬프트·AI 다듬기 → 사진·영상 초안 → 외주 정리)
# 3단계로 나눠 동시에 개발합니다. 이 파일은 1단계 담당자(공용 파일)만 고칩니다.
#   1단계 단일 변수 추출 ~ A/B 소재 선정: media_variable.py, media_ab.py (하위 탭 ①②)
#   2단계 프롬프트 만들기 + AI 다듬기: media_stage2/ (media_stage2_render(), 하위 탭 ③)
#   3단계 사진·영상 초안 → 외주 정리: media_stage3/ (media_stage3_render() ④, media_stage3_export_render() ⑤)
#   단계 사이 데이터: media_handoff.py
from pathlib import Path

import streamlit as st

import ui_theme as ui
from modules.media.media_ab import media_ab_plan_step
from modules.media.media_stage2.media_stage2 import MEDIA_S2_TAB_LABEL, media_stage2_render
from modules.media.media_stage3.media_stage3_export import MEDIA_S3_EXPORT_TAB_LABEL, media_stage3_export_render
from modules.media.media_stage3.media_stage3 import MEDIA_S3_TAB_LABEL, media_stage3_render
from modules.media.media_variable import MEDIA_VARIABLE_TAB_LABEL, media_variable_kpi_chip, media_variable_step

MEDIA_DIR = Path(__file__).resolve().parent   # 내 폴더 (images/, data/ 경로 만들 때 사용)
# 공통 로더(layout_load_css)는 media_style.css만 읽으므로, 단계 폴더의 CSS는 여기서 읽어 넣습니다
MEDIA_STAGE_CSS = [MEDIA_DIR / "media_stage2" / "media_stage2_style.css",
                   MEDIA_DIR / "media_stage3" / "media_stage3_style.css"]

# 하위 탭(단계): (탭 이름, 화면 함수). 순서대로 '다음 단계' 버튼으로 넘어갑니다.
# 2·3단계 탭 이름은 각 단계 파일의 MEDIA_S2_TAB_LABEL / MEDIA_S3_TAB_LABEL / MEDIA_S3_EXPORT_TAB_LABEL에서 정합니다 (단계 담당자가 바꿈)
MEDIA_STEPS = [
    (MEDIA_VARIABLE_TAB_LABEL, media_variable_step),
    ("A/B 소재 준비", media_ab_plan_step),
    (MEDIA_S2_TAB_LABEL, media_stage2_render),
    (MEDIA_S3_TAB_LABEL, media_stage3_render),
    (MEDIA_S3_EXPORT_TAB_LABEL, media_stage3_export_render),
]


def _media_go_step(label: str) -> None:
    """'이전/다음 단계' 버튼 콜백. 하위 탭(key="media-step")의 선택을 바꿉니다 (위젯이 그려지기 전에 실행됨)."""
    st.session_state["media-step"] = label


def media_load_stage_css() -> None:
    """2·3단계 폴더의 CSS를 화면에 넣습니다 (파일이 없거나 비어 있으면 건너뜀)."""
    css = "\n".join(p.read_text(encoding="utf-8") for p in MEDIA_STAGE_CSS if p.exists())
    if css.strip():
        # key="media-stage-css": media_style.css가 이 칸을 숨겨 화면에 빈 간격이 생기지 않게 함 (style은 그대로 적용됨)
        with st.container(key="media-stage-css"):
            st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


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
    media_load_stage_css()
    # key="media-root": media_style.css가 이 탭 안의 간격만 줄이도록 범위를 정하는 class (.st-key-media-root)
    with st.container(key="media-root"):
        ui.page_header("3. 매체 제작", "가설에서 변수 도출 → A/B 소재 → 프롬프트 → 사진·영상 초안 → 외주 정리, 단계별로 넘어가요")
        tabs = st.tabs([label for label, _ in MEDIA_STEPS], key="media-step", on_change="rerun")
        for i, (tab, (_, render)) in enumerate(zip(tabs, MEDIA_STEPS)):
            if tab.open:   # 선택된 단계만 그립니다
                with tab:
                    if i > 0:   # 하위 탭 바 오른쪽에 목표 KPI 칩 (하위 탭 ①은 요약 카드에 KPI가 이미 있음)
                        media_variable_kpi_chip()
                    render()
                    media_step_nav(i)
