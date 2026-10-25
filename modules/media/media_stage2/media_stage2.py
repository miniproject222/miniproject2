# 3. 매체 제작 > 하위 탭 ② A/B 소재 준비 (2단계 폴더 · PM 담당)
# 2026-10-25 PM 결정: 1단계의 'A/B 소재 준비'(옛 media_ab.py)와 2단계 '프롬프트 만들기' 탭을 이 파일 한 곳으로 합침.
# 화면 순서: ①에서 확정한 A·B 카드 → 기본 프롬프트·빈칸 → AI로 다듬기 + 확인 → '프롬프트 넘기기'
#   - A/B 설계는 1단계가 '이 변수로 확정'으로 넘긴 값(media_variable_confirmed_plan(), 안에서 media_handoff_plan())
#   - AI 다듬기 재료는 리포트 값(store_get("report"))과 아마존 메인 이미지 규칙(media_stage2_ai.MEDIA_S2_AMAZON_RULES)
#   - 넘기기 버튼을 누르면 결과를 media_handoff_set_prompt()로 3단계(사진·영상 초안 제작)에 넘깁니다.
# 화면은 media_stage2_render() 안에서만 그립니다 (media_page.py가 하위 탭에서 부름).
# 이름 규칙: 함수 media_s2_..., 위젯 key·session_state 키·CSS class media-s2-...
# (이전 A/B 결과·판정 코드는 media_stage2_judge.py에 보관, AI 다듬기 재료·호출·확인은 media_stage2_ai.py)
from pathlib import Path

import pandas as pd
import streamlit as st

from common.common_store import store_get
from modules.media.media_handoff import (MEDIA_HANDOFF_PROMPT_SAMPLE, MEDIA_HANDOFF_SLOT, media_handoff_check,
                                         media_handoff_fill,
                                         media_handoff_plan, media_handoff_prompt, media_handoff_set_prompt)
from modules.media.media_stage2.media_stage2_ai import (MEDIA_S2_AI_KEY, MEDIA_S2_OPENAI_MODEL, media_s2_ai_material,
                                                        media_s2_ai_ready,
                                                        media_s2_ai_run, media_s2_forbidden_hits,
                                                        media_s2_forbidden_terms)
# 1단계(min)가 다른 하위 탭용으로 만든 함수: 확정한 A/B 설계 + 상태, '① 으로 가서 확정하기' 버튼 콜백
from modules.media.media_variable import media_variable_confirmed_plan, media_variable_go_step

MEDIA_S2_TAB_LABEL = "A/B 소재 준비"   # 하위 탭 이름 (여기서 바꾸면 탭과 이전/다음 버튼 글자가 함께 바뀜)
MEDIA_S2_DIR = Path(__file__).resolve().parent   # 2단계 폴더 (data/ 경로 만들 때 사용)


def media_s2_slot_from_ref(base: str, ref: str) -> str:
    """1단계가 넘긴 B안 영어 문장(ref)에서 기본 프롬프트(base)의 {slot} 자리에 들어갈 부분만 잘라 냅니다.
    ref의 앞뒤가 base의 앞뒤와 다르면 빈 문자열 (그때는 예시 빈칸을 씀)."""
    head, _, tail = base.partition(MEDIA_HANDOFF_SLOT)
    if ref.startswith(head) and ref.endswith(tail) and len(ref) > len(head) + len(tail):
        return ref[len(head):len(ref) - len(tail)].strip()
    return ""


def media_s2_draft() -> dict:
    """2-1 ~ 2-3 결과: 기본 프롬프트, 빈칸, A/B 빈칸 문구, 고정 요소.
    빈칸 B는 1단계에서 확정한 B안의 영어 문장(plan["b_ref"])에서 잘라 쓰고, 없으면 예시 값을 씁니다.
    기본 프롬프트·빈칸 A는 2단계 담당이 화면을 만들기 전까지 예시 값(MEDIA_HANDOFF_PROMPT_SAMPLE)을 씁니다."""
    plan = media_handoff_plan()
    draft = {k: MEDIA_HANDOFF_PROMPT_SAMPLE[k] for k in ("base", "slot_a", "slot_b", "fixed")} |         {"variable": plan["variable"], "slot_b_from_plan": False}
    slot_b = media_s2_slot_from_ref(draft["base"], plan.get("b_ref") or "")
    if slot_b:
        draft["slot_b"], draft["slot_b_from_plan"] = slot_b, True
    return draft


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


def _media_s2_ai_refine(draft: dict) -> None:
    """'AI로 다듬기' 버튼 콜백 (프롬프트 칸이 그려지기 전에 실행되어 칸 값을 바꿀 수 있음).
    확인을 통과하면 프롬프트 A·B 칸을 다듬은 문장으로 바꾸고 결과를 media-s2-ai-result에 보관합니다.
    실패하면 칸은 그대로 두고 경고 문구만 남깁니다."""
    try:
        check = media_s2_ai_run(draft)
    except RuntimeError as err:
        st.session_state["media-s2-ai-msg"] = [f"AI 다듬기 실패: {err}. 프롬프트는 그대로 두었어요."]
        return
    if not check["ok"]:
        st.session_state["media-s2-ai-msg"] = [f"AI 답을 쓰지 않았어요: {e}" for e in check["errors"]]
        return
    result = check["result"]
    st.session_state["media-s2-prompt-A"] = result["prompt_a"]
    st.session_state["media-s2-prompt-B"] = result["prompt_b"]
    st.session_state["media-s2-ai-result"] = result
    st.session_state["media-s2-ai-msg"] = check["warnings"]


def media_s2_ai_current(prompt_a: str, prompt_b: str) -> dict | None:
    """지금 칸의 프롬프트가 AI 결과 그대로일 때만 그 결과 (되돌리거나 직접 고치면 None → 바꾼 곳을 넘기지 않음)."""
    result = st.session_state.get("media-s2-ai-result")
    if result and result["prompt_a"] == prompt_a and result["prompt_b"] == prompt_b:
        return result
    return None


def media_s2_ai_header(draft: dict) -> None:
    """'AI로 다듬기 + 확인' 제목 줄: 왼쪽 제목, 오른쪽 끝에 'AI로 다듬기' 버튼 (프롬프트 A·B 칸 바로 위). AI는 OpenAI만 씀."""
    ready = media_s2_ai_ready()
    title, btn_col = st.columns([4.2, 1.1], vertical_alignment="center")
    with title:
        st.markdown("**AI로 다듬기 + 확인**")
    with btn_col:
        st.button("AI로 다듬기", key="media-s2-btn-refine", type="primary", width="stretch", disabled=not ready,
                  help=(f"OpenAI({MEDIA_S2_OPENAI_MODEL})로 리포트 규칙에 맞춰 기본 프롬프트의 공통 부분만 다듬어요 "
                        "(빈칸·고정 요소는 그대로)" if ready else f"secrets.toml에 {MEDIA_S2_AI_KEY}를 넣어 주세요"),
                  on_click=_media_s2_ai_refine, args=(draft,))


def media_s2_ai_report(draft: dict, prompt_a: str, prompt_b: str) -> None:
    """프롬프트 칸 아래: AI 경고, 바꾼 곳 표, 찍지 말 것 / 넣을 것, 그리고 키가 없어도 도는 금지 단어 검사."""
    for msg in st.session_state.pop("media-s2-ai-msg", []):
        st.warning(msg)

    material = media_s2_ai_material(draft)
    terms = media_s2_forbidden_terms(material["forbidden"])
    hits = media_s2_forbidden_hits(prompt_a + "\n" + prompt_b, material["forbidden"])
    if hits:
        st.warning("리포트 금지 표현이 프롬프트에 있어요: " + ", ".join(hits))
    elif terms:
        st.caption(f"금지 단어 검사 통과 · 검사한 단어: {', '.join(terms)}")
    else:
        st.caption("금지 단어 검사: ① 문제 분석 탭을 한 번 열면 리포트 금지 표현으로 검사해요.")

    result = media_s2_ai_current(prompt_a, prompt_b)
    if result is None:
        if st.session_state.get("media-s2-ai-result"):
            st.caption("프롬프트를 되돌리거나 직접 고쳐서 AI 다듬기 결과(바꾼 곳·찍지 말 것·넣을 것)는 넘기지 않아요.")
        return
    with st.container(border=True, key="media-s2-ai-box"):
        st.markdown(f"**AI 다듬기 결과** · {result.get('provider', '')}")
        if not result["used_report"]:
            st.info("리포트 규칙 없이 다듬었어요 (아마존 메인 이미지 규칙만 사용). ① 문제 분석 탭을 열고 다시 눌러 주세요.")
        for w in result["slot_warnings"]:
            st.warning(f"A/B 문구 확인: {w}")
        if result["changes"]:
            st.dataframe(pd.DataFrame([{
                "바꾼 곳": c["where"], "뺌·더함": c["kind"], "이유": c["reason"],
                "근거": c["basis"] if c["basis_ok"] else f"{c['basis'] or '-'} ⚠️ 근거 확인 필요",
            } for c in result["changes"]]), hide_index=True, width="stretch")
        else:
            st.caption("AI가 바꾼 곳이 없어요.")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**🚫 찍지 말 것**")
            st.markdown("\n".join(f"- {x}" for x in result["avoid"]) or "-")
        with c2:
            st.markdown("**✅ 넣을 것**")
            st.markdown("\n".join(f"- {x}" for x in result["include"]) or "-")


def media_s2_refine_section(draft: dict) -> tuple[str, str, bool]:
    """2-4 AI로 다듬기 + 확인. 다듬은 프롬프트 A, B와 확인 통과 여부를 돌려줍니다."""
    saved = media_handoff_prompt()   # 전에 넘긴 다듬은 결과가 있으면 그걸로 칸을 채움 (탭을 오가도 유지)
    same_draft = not saved["sample"] and saved["base"] == draft["base"] and saved["slot_a"] == draft["slot_a"] \
        and saved["slot_b"] == draft["slot_b"]
    sig = (draft["base"], draft["slot_a"], draft["slot_b"])
    if st.session_state.get("media-s2-draft-sig") != sig:   # 1단계에서 다른 B를 확정하면 칸을 새 문장으로
        st.session_state["media-s2-draft-sig"] = sig
        for k in ("media-s2-prompt-A", "media-s2-prompt-B", "media-s2-ai-result"):
            st.session_state.pop(k, None)
    # 전에 넘긴 값에 AI 결과(바꾼 곳 등)가 있으면 다시 열어도 결과 표가 이어지게 채움
    if same_draft and "media-s2-ai-result" not in st.session_state and saved["changes"]:
        st.session_state["media-s2-ai-result"] = {
            "base": "", "prompt_a": saved["prompt_a"], "prompt_b": saved["prompt_b"],
            "changes": [{**c, "basis_ok": True} for c in saved["changes"]], "avoid": saved["avoid"],
            "include": saved["include"], "slot_warnings": [], "used_report": True, "provider": "전에 넘긴 결과"}

    media_s2_ai_header(draft)
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
    media_s2_ai_report(draft, prompts["A"], prompts["B"])

    rules = media_s2_report_rules()
    with st.expander(f"리포트에서 받은 규칙 · 금지 표현 {len(rules['forbidden'])}개 · "
                     f"광고 표현 규칙 {len(rules['marketing_rules'])}개", expanded=False):
        if not rules["forbidden"] and not rules["marketing_rules"]:
            st.caption("① 문제 분석 탭을 한 번 열면 리포트 값이 들어와요.")
        for f in rules["forbidden"]:
            st.markdown(f"- 🚫 {f}")
        for r in rules["marketing_rules"]:
            st.markdown(f"- {r['id']} {r['topic']}: {r['rule']}")
    return prompts["A"], prompts["B"], check["ok"]


def media_s2_handoff_value(draft: dict, prompt_a: str, prompt_b: str) -> dict:
    """3단계(④ 사진·영상 초안 제작, ⑤ 외주 정리)로 넘기는 값 (모양은 media_handoff.py의 MEDIA_HANDOFF_PROMPT_SAMPLE).
    changes·avoid·include는 지금 칸이 AI 다듬기 결과 그대로일 때만 채웁니다 (되돌리거나 직접 고치면 빈 목록)."""
    keep = {k: v for k, v in draft.items() if k != "slot_b_from_plan"}
    ai = media_s2_ai_current(prompt_a, prompt_b) or {}
    changes = [{k: c[k] for k in ("where", "kind", "reason", "basis")} for c in ai.get("changes", [])]
    return {**keep, "prompt_a": prompt_a, "prompt_b": prompt_b, "changes": changes,
            "avoid": list(ai.get("avoid", [])), "include": list(ai.get("include", []))}


def _media_s2_handoff(draft: dict) -> None:
    """'④로 넘기기' 버튼 콜백. 확인을 통과한 지금 프롬프트 A·B를 3단계로 넘깁니다 (Supabase에 저장)."""
    a, b = st.session_state.get("media-s2-prompt-A", ""), st.session_state.get("media-s2-prompt-B", "")
    if media_handoff_check(draft, a, b)["ok"]:
        media_handoff_set_prompt(media_s2_handoff_value(draft, a, b))
        st.session_state["media-s2-handoff-toast"] = True


def media_s2_handoff_step(draft: dict, prompt_a: str, prompt_b: str, ok: bool) -> None:
    """넘기기 줄: 버튼을 눌러야만 3단계로 넘어갑니다. 넘기기 전 / 넘김 완료 / 바뀌어서 다시 넘겨야 함을 보여 줍니다."""
    if st.session_state.pop("media-s2-handoff-toast", False):
        st.toast("프롬프트를 사진·영상 초안 제작으로 넘겼어요", icon="✅")
    saved = media_handoff_prompt()
    now = media_s2_handoff_value(draft, prompt_a, prompt_b)
    sent = not saved["sample"] and all(saved.get(k) == v for k, v in now.items())
    if sent:
        note = ":green-badge[✅ 넘김 완료] 사진·영상 초안 제작이 이 프롬프트를 받아요"
    elif not saved["sample"]:
        note = ":orange-badge[다시 넘기기 필요] 넘긴 뒤 프롬프트가 바뀌었어요. 사진·영상 초안 제작은 아직 이전 값을 받아요"
    else:
        note = "확인을 통과하면 '프롬프트 넘기기'를 눌러 주세요. 누르기 전에는 사진·영상 초안 제작이 예시 프롬프트를 받아요"
    with st.container(horizontal=True, vertical_alignment="center", key="media-s2-handoff-row"):
        st.markdown(note)
        if not sent:
            st.button("다시 넘기기" if not saved["sample"] else "프롬프트 넘기기", key="media-s2-btn-handoff",
                      type="primary", disabled=not ok, on_click=_media_s2_handoff, args=(draft,),
                      help=None if ok else "위 확인을 통과해야 넘길 수 있어요")


def media_s2_ab_section() -> bool:
    """위쪽: ①에서 '이 변수로 확정'한 A·B 소재 카드 (옛 media_ab.py의 media_ab_plan_step() 위쪽을 옮김).
    확정 전이면 빈 카드와 '① 으로 가서 확정하기' 버튼만 보여 주고 False (그 아래 프롬프트 만들기도 그리지 않음)."""
    plan, state = media_variable_confirmed_plan()
    if plan is None:   # 아직 확정 전: 빈 카드로 ①에서 확정하도록 안내
        with st.container(border=True, key="media-s2-ab-empty"):
            st.markdown("**아직 확정한 변수가 없어요**")
            st.caption("① 에서 변수와 B안을 고르고 '이 변수로 확정'을 누르면 여기에 A/B 소재와 프롬프트가 나와요.")
            st.button("① 으로 가서 확정하기", key="media-s2-btn-go-confirm", type="primary",
                      on_click=media_variable_go_step)
        return False
    if state == "changed":   # ①에서 다른 값을 골랐지만 아직 확정하지 않음
        with st.container(horizontal=True, vertical_alignment="center", key="media-s2-ab-pending"):
            st.markdown(":orange-badge[확정 안 됨] ① 에서 새로 고른 값이 아직 확정되지 않아, 이전에 확정한 값으로 보여 줘요")
            st.button("① 으로 가서 확정하기", key="media-s2-btn-go-confirm", type="secondary",
                      on_click=media_variable_go_step)

    # 지금 메인 이미지의 문제점은 리포트(검색어 분석 sqp의 listing)에서 읽음 (검색어·KPI는 탭 바 오른쪽 KPI 칩에 있음)
    report = store_get("report") or {}
    sqp = report.get("sqp") if isinstance(report.get("sqp"), dict) else {}
    listing = sqp.get("listing") if isinstance(sqp.get("listing"), dict) else {}
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("**A · 현재 (대조군)**")
            st.markdown(f"{plan['a']}  \n"
                        f'<span class="media-desc">{listing.get("main_image_issue", "")}</span>', unsafe_allow_html=True)
    with c2:
        with st.container(border=True):
            st.markdown("**B · 제안 (실험군)**")
            # B 카드 아래는 확정한 독립 변수 (min #42에서 고정 문구 대신 바꾼 것을 반영, 어떤 가설에도 맞게)
            st.markdown(f"{plan['b']}  \n<span class=\"media-desc\">독립 변수: {plan['variable']}</span>",
                        unsafe_allow_html=True)
    return True


def media_s2_prompt_section():
    """아래쪽: 프롬프트 만들기 (기본 프롬프트·빈칸 → AI로 다듬기 + 확인 → 넘기기).
    A·B 소재 설명은 위쪽 카드에 이미 있어서 여기서는 다시 보여 주지 않습니다."""
    st.markdown("**📝 프롬프트 만들기**")
    st.caption("A와 B에 똑같이 들어갈 기본 프롬프트에서 단일 변수 자리만 빈칸으로 남겨 A, B를 채운 뒤 AI로 다듬어요.")

    # 2-1 ~ 2-3: 2단계 담당이 만들 자리 (기본 프롬프트 → 빈칸 {slot} → A, B 빈칸 채우기). 지금은 예시 값
    draft = media_s2_draft()
    st.markdown("**2-1 ~ 2-3 기본 프롬프트와 빈칸** (예시)")
    if not draft["slot_b_from_plan"]:
        st.caption("1단계에서 확정한 B안의 영어 문장이 없어 예시 빈칸 B를 써요. ①에서 '이 변수로 확정'을 다시 눌러 주세요.")
    st.code(draft["base"], language=None, wrap_lines=True)

    prompt_a, prompt_b, ok = media_s2_refine_section(draft)
    media_s2_handoff_step(draft, prompt_a, prompt_b, ok)


def media_stage2_render():
    """하위 탭 ② A/B 소재 준비 (이름은 MEDIA_S2_TAB_LABEL). 반드시 media_render() 안에서 부릅니다.
    위쪽 A·B 소재 카드 → 아래쪽 프롬프트 만들기. ①에서 확정하기 전에는 빈 카드만 보여 줍니다."""
    if not media_s2_ab_section():
        return
    st.divider()
    media_s2_prompt_section()
