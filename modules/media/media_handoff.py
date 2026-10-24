# 3. 매체 제작 > 단계 사이 데이터 주고받기 (1단계 담당 파일 · 2·3단계는 읽고 부르기만)
# 1단계(가설에서 변수 도출 ~ A/B 소재 준비) → 2단계(결과·판정) → 3단계(솔루션 제안)로 넘기는 값의 모양을 여기서 정합니다.
# 모양(키 이름)을 바꿀 때는 세 담당자가 같이 정하고 이 파일만 고칩니다.
import streamlit as st

from modules.media.media_variable import MEDIA_VARIABLE_KPI

# 2단계가 판정 결과를 넣어 두는 session_state 키 (3단계가 읽음)
MEDIA_HANDOFF_RESULT_KEY = "media-handoff-result"

# 1단계 → 2단계: A/B 테스트 설계. 1단계가 정한 값이라 언제 불러도 같은 값입니다.
MEDIA_HANDOFF_PLAN = {
    "query": "kühlende matratzenauflage",          # 검색어
    "variable": "메인 이미지 촬영 구도",              # 독립 변수 (바꾸는 것 1개)
    "a": "접힌 패드 (위에서 찍은 사진)",              # A · 대조군 (지금 그대로)
    "b": "펼친 패드를 45도 위에서, 모서리를 살짝 들어 두께와 냉감 원단 결이 보이게",   # B · 실험군
    "kpi": MEDIA_VARIABLE_KPI,                     # 종속 변수 이름 (노출 대비 클릭률 = 클릭 점유율 ÷ 노출 점유율)
    "kpi_now": 0.63,                               # 지금 값 (배)
    "kpi_goal": 0.8,                               # 목표 값 (배 이상)
    "cvr_tolerance": 0.5,                          # 안전장치: B의 CVR이 A보다 이만큼(%p) 넘게 떨어지면 B 실패
}

# 2단계 → 3단계: 판정 결과 예시. 2단계가 아직 결과를 넣지 않았을 때 3단계가 이 값으로 먼저 개발합니다.
# (지금 숫자는 2단계 가상 데이터 media_ab_result_dummy_202610.json으로 계산한 값)
MEDIA_HANDOFF_RESULT_SAMPLE = {
    "source": "가상",                # 데이터 출처 ("가상" / "실제")
    "winner": "B",                   # 승자 안 이름
    "b_wins": True,                  # B(실험군)가 이겼는지
    "kpi": [0.63, 0.84],             # 노출 대비 클릭률 [A, B] (배)
    "cvr": [0.0861, 0.0847],         # CVR [A, B] (0~1 비율)
    "cvr_ok": True,                  # 안전장치 통과 여부
    "p_ctr": 0.0001,                 # CTR 차이의 유의확률 (0.05 미만이면 의미 있는 차이)
}


def media_handoff_plan() -> dict:
    """1단계 → 2단계: A/B 테스트 설계 (MEDIA_HANDOFF_PLAN 복사본)."""
    return dict(MEDIA_HANDOFF_PLAN)


def media_handoff_set_result(result: dict) -> None:
    """2단계가 판정을 마치면 부릅니다. 모양은 MEDIA_HANDOFF_RESULT_SAMPLE과 같게 넣습니다."""
    st.session_state[MEDIA_HANDOFF_RESULT_KEY] = dict(result)


def media_handoff_result() -> dict:
    """2단계 → 3단계: 판정 결과. 2단계가 아직 넣지 않았으면 예시 값에 "sample": True를 붙여 돌려줍니다."""
    saved = st.session_state.get(MEDIA_HANDOFF_RESULT_KEY)
    if isinstance(saved, dict):
        return {**saved, "sample": False}
    return {**MEDIA_HANDOFF_RESULT_SAMPLE, "sample": True}
