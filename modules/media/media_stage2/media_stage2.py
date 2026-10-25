# 3. 매체 제작 > 2단계: 프롬프트 만들기 + AI 다듬기 (2단계 담당 · JY 브랜치)
# 1단계가 정한 단일 변수와 A/B 소재(media_handoff_plan())를 받아
# 2-1 기본 프롬프트 쓰기 → 2-2 단일 변수 칸 비워 두기 → 2-3 빈칸 채워 A, B 만들기 →
# 2-4 리포트 값(store_get("report"))으로 AI 다듬기 + 확인을 하고,
# 결과를 media_handoff_set_prompt()로 3단계에 넘깁니다. 화면은 media_stage2_render() 안에서만 그립니다.
# 이름 규칙: 함수 media_s2_..., 위젯 key·session_state 키·CSS class media-s2-...
# (이전 A/B 결과·판정 코드는 media_stage2_judge.py에 보관)
from pathlib import Path

import streamlit as st

from common.common_store import store_get
from modules.media.media_handoff import (MEDIA_HANDOFF_PROMPT_SAMPLE, media_handoff_check, media_handoff_fill,
                                         media_handoff_plan, media_handoff_prompt, media_handoff_set_prompt)

MEDIA_S2_TAB_LABEL = "프롬프트 만들기"   # 하위 탭 이름 (여기서 바꾸면 탭과 이전/다음 버튼 글자가 함께 바뀜)
MEDIA_S2_DIR = Path(__file__).resolve().parent   # 2단계 폴더 (data/ 경로 만들 때 사용)


def media_s2_draft() -> dict:
    """2-1 ~ 2-3 결과: 기본 프롬프트, 빈칸, A/B 빈칸 문구, 고정 요소.
    2단계 담당이 화면을 만들기 전까지는 예시 값(MEDIA_HANDOFF_PROMPT_SAMPLE)을 씁니다."""
    plan = media_handoff_plan()
    return {k: MEDIA_HANDOFF_PROMPT_SAMPLE[k] for k in ("base", "slot_a", "slot_b", "fixed")} | \
        {"variable": plan["variable"]}


def media_s2_report_rules() -> dict:
    """2-4에서 쓰는 리포트 값 (① 탭이 저장한 store("report")). ① 탭을 아직 안 열었으면 빈 목록."""
    report = store_get("report") or {}
    claims = report.get("ad_claims") or {}
    return {"forbidden": claims.get("forbidden") or [],          # 금지 표현 (독일어·한국어)
            "marketing_rules": report.get("marketing_rules") or [],   # 독일 광고 표현 규칙 8개 (DB ID)
            "seori_profile": report.get("seori_profile") or {},       # 우리 제품 강점·약점·광고 가능 여부
            "competitor_profiles": report.get("competitor_profiles") or []}


def _media_s2_reset(name: str, text: str) -> None:
    """'되돌리기' 버튼 콜백. 다듬은 프롬프트 칸을 빈칸만 채운 원래 문장으로 되돌립니다."""
    st.session_state[f"media-s2-prompt-{name}"] = text


def media_s2_refine_section(draft: dict) -> tuple[str, str, bool]:
    """2-4 AI로 다듬기 + 확인. 다듬은 프롬프트 A, B와 확인 통과 여부를 돌려줍니다."""
    st.markdown("**2-4 AI로 다듬기 + 확인**")
    rules = media_s2_report_rules()
    with st.expander(f"리포트에서 받은 규칙 · 금지 표현 {len(rules['forbidden'])}개 · "
                     f"광고 표현 규칙 {len(rules['marketing_rules'])}개", expanded=False):
        if not rules["forbidden"] and not rules["marketing_rules"]:
            st.caption("① 문제 분석 탭을 한 번 열면 리포트 값이 들어와요.")
        for f in rules["forbidden"]:
            st.markdown(f"- 🚫 {f}")
        for r in rules["marketing_rules"]:
            st.markdown(f"- {r['id']} {r['topic']}: {r['rule']}")
    st.button("AI로 다듬기", key="media-s2-btn-refine", disabled=True,
              help="AI 키가 들어오면 연결합니다. 지금은 아래 칸에서 직접 고칠 수 있어요.")

    saved = media_handoff_prompt()   # 전에 넘긴 다듬은 결과가 있으면 그걸로 칸을 채움 (탭을 오가도 유지)
    same_draft = not saved["sample"] and saved["base"] == draft["base"] and saved["slot_a"] == draft["slot_a"] \
        and saved["slot_b"] == draft["slot_b"]
    prompts = {}
    c1, c2 = st.columns(2)
    for col, name in ((c1, "A"), (c2, "B")):
        original = media_handoff_fill(draft["base"], draft[f"slot_{name.lower()}"])
        key = f"media-s2-prompt-{name}"
        if key not in st.session_state:
            st.session_state[key] = saved[f"prompt_{name.lower()}"] if same_draft else original
        with col:
            with st.container(border=True):
                st.markdown(f"**프롬프트 {name}** · 빈칸: {draft['slot_' + name.lower()]}")
                prompts[name] = st.text_area(f"프롬프트 {name}", key=key, height=160, label_visibility="collapsed")
                st.button("되돌리기", key=f"media-s2-btn-reset-{name}",
                          on_click=_media_s2_reset, args=(name, original))

    check = media_handoff_check(draft, prompts["A"], prompts["B"])
    if check["ok"]:
        st.success("A와 B는 빈칸만 다르고, 고정 요소도 모두 남아 있어요.")
    else:
        if not check["slot_ok"]:
            st.warning("빈칸 문구가 바뀌었어요. 단일 변수가 흔들리니 되돌려 주세요.")
        elif not check["same_rest"]:
            st.warning("빈칸 밖에서 A와 B가 서로 달라요. 바뀐 쪽을 되돌려 주세요.")
        if check["missing"]:
            st.warning("빠진 고정 요소: " + ", ".join(check["missing"]))
    return prompts["A"], prompts["B"], check["ok"]


def media_stage2_render():
    """2단계 하위 탭(이름은 MEDIA_S2_TAB_LABEL, 탭 이름이 제목 역할). 반드시 media_render() 안에서 부릅니다."""
    plan = media_handoff_plan()   # 1단계 A/B 설계 (단일 변수, A 소재, B 소재)
    st.caption("A와 B에 똑같이 들어갈 기본 프롬프트를 쓰고, 단일 변수 자리만 빈칸으로 남겨 A, B를 채운 뒤 AI로 다듬어요.")
    st.markdown(f"단일 변수: **{plan['variable']}** · A: {plan['a']} · B: {plan['b']}")

    # 2-1 ~ 2-3: 2단계 담당이 만들 자리 (기본 프롬프트 → 빈칸 {slot} → A, B 빈칸 채우기). 지금은 예시 값
    draft = media_s2_draft()
    st.markdown("**2-1 ~ 2-3 기본 프롬프트와 빈칸** (예시)")
    st.code(draft["base"], language=None, wrap_lines=True)

    prompt_a, prompt_b, ok = media_s2_refine_section(draft)
    if ok:
        # 3단계(사진·영상 초안, 외주 정리)로 넘기는 값 (모양은 media_handoff.py의 MEDIA_HANDOFF_PROMPT_SAMPLE)
        # changes·avoid·include는 AI 다듬기를 연결하면 채웁니다
        media_handoff_set_prompt({**draft, "prompt_a": prompt_a, "prompt_b": prompt_b,
                                  "changes": [], "avoid": [], "include": []})
