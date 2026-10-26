# 3. 매체 제작 (단일 변수 → A/B 소재 → 프롬프트·AI 다듬기 → 사진·영상 초안 → 외주 정리)
# 3단계로 나눠 동시에 개발합니다. 이 파일은 1단계 담당자(공용 파일)만 고칩니다.
#   1단계 단일 변수 추출: media_variable.py (하위 탭 ①)
#   2단계 A/B 소재 준비 + 프롬프트 만들기·AI 다듬기: media_stage2/ (media_stage2_render(), 하위 탭 ②)
#     (2026-10-25 PM 결정: 옛 media_ab.py와 '프롬프트 만들기' 탭을 media_stage2로 합침)
#   3단계 사진·영상 초안 → 외주 정리: media_stage3/ (media_stage3_render() ③, media_stage3_export_render() ④)
#   단계 사이 데이터: media_handoff.py
from pathlib import Path

import streamlit as st

import ui_theme as ui
from modules.media.media_stage2.media_stage2 import MEDIA_S2_TAB_LABEL, media_s2_handoff_now, media_stage2_render
from modules.media.media_stage3.media_stage3_export import MEDIA_S3_EXPORT_TAB_LABEL, media_stage3_export_render
from modules.media.media_stage3.media_stage3 import MEDIA_S3_SUB_TABS, MEDIA_S3_TAB_LABEL, _media_s3_go, media_stage3_render
from modules.media.media_variable import (MEDIA_VARIABLE_TAB_LABEL, _media_variable_start_load, media_variable_can_leave,
                                          media_variable_kpi_chip, media_variable_leave_notice, media_variable_locked_step,
                                          media_variable_step)

MEDIA_DIR = Path(__file__).resolve().parent   # 내 폴더 (images/, data/ 경로 만들 때 사용)
# 공통 로더(layout_load_css)는 media_style.css만 읽으므로, 단계 폴더의 CSS는 여기서 읽어 넣습니다
MEDIA_STAGE_CSS = [MEDIA_DIR / "media_stage2" / "media_stage2_style.css",
                   MEDIA_DIR / "media_stage3" / "media_stage3_style.css"]

# 하위 탭(단계): (탭 이름, 화면 함수). 순서대로 제목 줄 '다음으로' 버튼으로 넘어갑니다.
# 2·3단계 탭 이름은 각 단계 파일의 MEDIA_S2_TAB_LABEL / MEDIA_S3_TAB_LABEL / MEDIA_S3_EXPORT_TAB_LABEL에서 정합니다 (단계 담당자가 바꿈)
MEDIA_STEPS = [
    (MEDIA_VARIABLE_TAB_LABEL, media_variable_step),
    (MEDIA_S2_TAB_LABEL, media_stage2_render),
    (MEDIA_S3_TAB_LABEL, media_stage3_render),
    (MEDIA_S3_EXPORT_TAB_LABEL, media_stage3_export_render),
]


# '다음' 버튼을 누를 때 탭을 옮기기 전에 먼저 할 일 (탭 이름 → 함수)
# 2026-10-25 PM 결정: ② A/B 소재 준비의 '다음' 버튼이 프롬프트 A·B를 3단계로 넘김 (따로 있던 넘기기 버튼 대신)
# ① 단일 변수: B안 옵션을 체크(= 확정)해야 넘어감. 안 했으면 탭을 옮기지 않고 가운데 경고창
#   (고른 변수가 이미지로 진행할 수 없는 변수면 경고창 대신 그 변수의 솔루션 팝업 → 확정하면 보고서용 PDF 저장 버튼)
# (하위 탭을 직접 누르면 탭은 바뀌지만 ②~④ 내용 대신 잠금 안내가 보임 → media_render())
MEDIA_STEP_ON_NEXT = {MEDIA_VARIABLE_TAB_LABEL: media_variable_can_leave, MEDIA_S2_TAB_LABEL: media_s2_handoff_now}


def _media_go_step(label: str, before=None) -> None:
    """단계 이동 (제목 줄 '다음으로'의 _media_click_next에서 부름). before가 있으면 먼저 부르고(False를 돌려주면 옮기지 않음),
    하위 탭(key="media-step")의 선택을 바꿉니다 (위젯이 그려지기 전에 실행됨)."""
    if before and before() is False:   # 먼저 할 일이 '옮기지 마'(False)를 돌려주면 그대로 머묾 (예: AI 다듬기 전 경고창)
        return
    st.session_state["media-step"] = label


def _media_step_changed() -> None:
    """하위 탭(key="media-step")을 직접 눌렀을 때 콜백. ② 뒤 탭으로 가는데 ①에서 확정 전이면 경고창을 띄우도록 표시만 합니다.
    (콜백에서 탭을 ①로 되돌리면 브라우저에는 눌린 탭이 그대로 보여서, 탭은 두고 그 탭 내용 대신 잠금 안내를 보여 줌)"""
    if st.session_state.get("media-step") != MEDIA_VARIABLE_TAB_LABEL:
        media_variable_can_leave()


def media_load_stage_css() -> None:
    """2·3단계 폴더의 CSS를 화면에 넣습니다 (파일이 없거나 비어 있으면 건너뜀)."""
    css = "\n".join(p.read_text(encoding="utf-8") for p in MEDIA_STAGE_CSS if p.exists())
    if css.strip():
        # key="media-stage-css": media_style.css가 이 칸을 숨겨 화면에 빈 간격이 생기지 않게 함 (style은 그대로 적용됨)
        with st.container(key="media-stage-css"):
            st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


MEDIA_HELP_ABOUT = "가설에서 변수 도출 → A/B 소재·프롬프트 → 사진·영상 초안 제작 → 외주 정리, 단계별로 넘어가요."
MEDIA_HELP_ORDER = ("**순서**: 오른쪽 위 '불러오기'(② 가설 탭에서 저장한 가설) → 단계마다 '다음으로' "
                    "(가설에서 변수 도출에서 B안을 골라 확정해야 다음 단계가 열려요). 지난 단계는 단계 탭을 눌러 돌아가요")


def _media_step_index() -> int:
    """지금 고른 단계(하위 탭 key="media-step")의 번호. 아직 고르지 않았으면 첫 단계(0)."""
    labels = [label for label, _ in MEDIA_STEPS]
    current = st.session_state.get("media-step")
    return labels.index(current) if current in labels else 0


def _media_next(i: int) -> tuple[str, str] | None:
    """머리줄 '다음으로'가 갈 곳 ("sub" 또는 "step", 이름). 마지막 단계면 None.
    사진·영상 초안 제작에서는 그 안의 탭(사진 → 영상 → 만든 결과 보기)을 차례로 지난 뒤 다음 단계로 (예전 ④ 이전/다음 줄과 같은 순서)."""
    if MEDIA_STEPS[i][0] == MEDIA_S3_TAB_LABEL:
        sub = st.session_state.get("media-s3-sub")
        j = MEDIA_S3_SUB_TABS.index(sub) if sub in MEDIA_S3_SUB_TABS else 0
        if j < len(MEDIA_S3_SUB_TABS) - 1:
            return "sub", MEDIA_S3_SUB_TABS[j + 1]
    return ("step", MEDIA_STEPS[i + 1][0]) if i < len(MEDIA_STEPS) - 1 else None


def _media_click_next() -> None:
    """머리줄 '다음으로' 콜백: 예전 단계 맨 아래 '다음: … →' 버튼과 같은 동작
    (단계를 옮길 때는 MEDIA_STEP_ON_NEXT를 먼저 부름: ① 확정 확인, ② 프롬프트 A·B를 3단계로 넘기기)."""
    i = _media_step_index()
    nxt = _media_next(i)
    if nxt is None:
        return
    kind, name = nxt
    if kind == "sub":
        _media_s3_go(sub=name)
    else:
        _media_go_step(name, MEDIA_STEP_ON_NEXT.get(MEDIA_STEPS[i][0]))


def _media_click_load() -> None:
    """머리줄 '불러오기' 콜백: 예전 가설에서 변수 도출 단계 오른쪽 위 '↻ 다시 불러오기'와 같은 동작.
    불러오기는 그 단계 화면을 그릴 때 실행되므로 그 단계로 옮김 (② 가설 탭 '다음으로'와 같은 방식)."""
    _media_variable_start_load()
    st.session_state["media-step"] = MEDIA_STEPS[0][0]


def media_header() -> None:
    """① 문제 분석·② 가설 세우기와 같은 제목 줄: 제목 · 바로 옆 물음표(설명) · 오른쪽 끝 '불러오기'·'다음으로'.
    (예전 단계마다 맨 아래 있던 이전/다음 줄 대신. 지난 단계는 단계 탭을 눌러 돌아감)"""
    i = _media_step_index()
    nxt = _media_next(i)
    locked = i > 0 and not media_variable_can_leave(warn=False)   # 가설에서 변수 도출 확정 전: 단계 내용 대신 잠금 안내
    with st.container(horizontal=True, vertical_alignment="center", key="media-head"):
        with st.container(key="media-head-title"):
            ui.page_header("3. 매체 제작")   # 설명 한 줄은 옆 물음표 안 (①·② 탭과 같음)
        with st.container(key="media-help"):
            with st.popover("", icon=":material/help:", type="tertiary", help="이 탭 안내"):
                st.markdown(f"{MEDIA_HELP_ABOUT}\n\n{MEDIA_HELP_ORDER}")
        st.button("불러오기", icon=":material/download:", key="media-btn-hypo-load", on_click=_media_click_load,
                  help="② 가설 탭에서 저장한 가설을 다시 불러와요 (가설에서 변수 도출 단계로 이동)")
        st.button("다음으로", icon=":material/arrow_forward:", key="media-btn-next", type="primary",
                  disabled=nxt is None or locked, on_click=_media_click_next,
                  help=(f"다음: {nxt[1]}" if nxt else "마지막 단계예요") if not locked else "가설에서 변수 도출에서 먼저 확정해 주세요")


def media_render():
    """'3. 매체 제작' 탭을 열 때마다 실행됩니다. 화면은 전부 이 함수 안에서 그립니다."""
    media_load_stage_css()
    # key="media-root": media_style.css가 이 탭 안의 간격만 줄이도록 범위를 정하는 class (.st-key-media-root)
    with st.container(key="media-root"):
        media_variable_leave_notice()   # ①을 떠나려다 막혔으면 가운데 경고창, 진행 불가 변수면 솔루션 팝업
        media_header()
        tabs = st.tabs([label for label, _ in MEDIA_STEPS], key="media-step", on_change=_media_step_changed)
        for i, (tab, (_, render)) in enumerate(zip(tabs, MEDIA_STEPS)):
            if tab.open:   # 선택된 단계만 그립니다
                with tab:
                    if i > 0 and not media_variable_can_leave(warn=False):   # ①에서 확정 전: 내용 대신 잠금 안내
                        media_variable_locked_step()
                        break
                    if i > 0:   # 하위 탭 바 오른쪽에 목표 KPI 칩 (하위 탭 ①은 요약 칩에 KPI가 이미 있음)
                        media_variable_kpi_chip()
                    render()
