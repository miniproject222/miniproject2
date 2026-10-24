# 3. 매체 제작 > 2단계: 프롬프트 만들기 (2단계 담당 · JY 브랜치)
# 1단계가 정한 단일 변수와 A/B 소재(media_handoff_plan())를 받아
# 2-1 기본 프롬프트 쓰기 → 2-2 단일 변수 칸 비워 두기 → 2-3 빈칸 채워 A, B 만들기를 하고,
# 프롬프트 재료를 media_handoff_set_prompt()로 3단계에 넘깁니다. 화면은 media_stage2_render() 안에서만 그립니다.
# 이름 규칙: 함수 media_s2_..., 위젯 key·session_state 키·CSS class media-s2-...
# (이전 A/B 결과·판정 코드는 media_stage2_judge.py에 보관)
from pathlib import Path

import streamlit as st

from modules.media.media_handoff import media_handoff_plan

MEDIA_S2_TAB_LABEL = "프롬프트 만들기"   # 하위 탭 이름 (여기서 바꾸면 탭과 이전/다음 버튼 글자가 함께 바뀜)
MEDIA_S2_DIR = Path(__file__).resolve().parent   # 2단계 폴더 (data/ 경로 만들 때 사용)


def media_stage2_render():
    """2단계 하위 탭(이름은 MEDIA_S2_TAB_LABEL, 탭 이름이 제목 역할). 반드시 media_render() 안에서 부릅니다."""
    plan = media_handoff_plan()   # 1단계 A/B 설계 (단일 변수, A 소재, B 소재)
    st.caption("A와 B에 똑같이 들어갈 기본 프롬프트를 쓰고, 단일 변수 자리만 빈칸으로 남겨 A, B를 채워요.")
    st.markdown(f"단일 변수: **{plan['variable']}** · A: {plan['a']} · B: {plan['b']}")
    # 2단계 담당이 만들 자리: 2-1 기본 프롬프트 → 2-2 빈칸({slot}) → 2-3 A, B 빈칸 채우기
    # 다 만들면 media_handoff_set_prompt({...})로 넘깁니다 (모양은 media_handoff.py의 MEDIA_HANDOFF_PROMPT_SAMPLE)
