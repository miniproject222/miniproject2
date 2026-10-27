# 3. 매체 제작 > 하위 탭 ② A/B 소재 준비 (2단계 폴더 · PM 담당)
# 2026-10-25 PM 결정: 1단계의 'A/B 소재 준비'(옛 media_ab.py)와 2단계 '프롬프트 만들기' 탭을 이 파일 한 곳으로 합침.
# 화면 순서: ①에서 확정한 A·B 카드 + 독립 변수 → A안·B안 프롬프트 만들기 → AI로 다듬기 → 리포트 규칙 팝업
#   - A/B 설계는 1단계가 '이 변수로 확정'으로 넘긴 값(media_variable_confirmed_plan(), 안에서 media_handoff_plan())
#   - A·B 프롬프트: AI(OpenAI)가 수업 형식 6칸으로 A를 먼저 만들고, 독립 변수 칸 하나만 바꿔 B를 만듦 (media_stage2_ai)
#     A를 지금 메인 이미지 그대로 쓸지 새로 설계할지는 자동 판단 (media_s2_mode)
#   - 사용자가 A나 B 칸을 고치면 다른 쪽의 같은 부분도 같이 바뀜 → A·B 차이는 항상 독립 변수 칸 하나
#   - AI 다듬기 재료는 리포트 값(store_get("report")), 아마존 메인 이미지 규칙, 독일 디자인 DB
#   - '다음: 사진·영상 초안 제작 →'(media_page.py)을 누르면 media_s2_handoff_now()가 결과를 3단계에 넘김.
#     AI로 다듬기를 한 번도 안 했으면 넘기지 않고 가운데 경고창을 띄움
# 화면은 media_stage2_render() 안에서만 그립니다 (media_page.py가 하위 탭에서 부름).
# 이름 규칙: 함수 media_s2_..., 위젯 key·session_state 키·CSS class media-s2-...
# (이전 A/B 결과·판정 코드는 media_stage2_judge.py에 보관, AI 재료·호출·확인은 media_stage2_ai.py)
from html import escape
from pathlib import Path

import streamlit as st

from common.common_store import store_get
from modules.media.media_handoff import (MEDIA_HANDOFF_PROMPT_SAMPLE, MEDIA_HANDOFF_SLOT, media_handoff_check,
                                         media_handoff_fill, media_handoff_prompt, media_handoff_set_prompt)
from modules.media.media_stage2.media_stage2_ai import (MEDIA_S2_AI_KEY, MEDIA_S2_OPENAI_MODEL, media_s2_ai_material,
                                                        media_s2_ai_ready, media_s2_ai_run, media_s2_forbidden_hits,
                                                        media_s2_generate, media_s2_listing, media_s2_mode,
                                                        media_s2_translate)
# 1단계(min)가 다른 하위 탭용으로 만든 함수: 확정한 A/B 설계 + 상태, '① 으로 가서 확정하기' 버튼 콜백
from modules.media.media_variable import (media_variable_candidates, media_variable_confirmed_plan,
                                          media_variable_go_step, media_variable_goal_text,
                                          media_variable_hypo_tip, media_variable_kpi_text, media_variable_label,
                                          media_variable_loaded,
                                          media_variable_plan)

MEDIA_S2_TAB_LABEL = "A/B 소재 준비"   # 하위 탭 이름 (여기서 바꾸면 탭과 이전/다음 버튼 글자가 함께 바뀜)
MEDIA_S2_DIR = Path(__file__).resolve().parent   # 2단계 폴더 (data/ 경로 만들 때 사용)
MEDIA_S2_HANDOFF_KEYS = ("variable", "base", "slot_a", "slot_b", "fixed")   # draft 중 3단계로 넘기는 칸 (약속된 키만)

# session_state 키
MEDIA_S2_GEN = "media-s2-gen"            # 지금 확정한 A/B에 대한 프롬프트 {"sig", "draft", "orig", "source", "error"}
MEDIA_S2_REFINED = "media-s2-refined"    # AI로 다듬기를 한 번이라도 한 프롬프트의 sig (안 했으면 '다음'에서 경고창)


# ─────────────────────────────────────────────
# A·B 프롬프트 (draft = 기본 프롬프트 base + 빈칸 slot_a/slot_b + 고정 요소 fixed + 독립 변수 variable)
# ─────────────────────────────────────────────
def media_s2_plan_sig(plan: dict) -> tuple:
    """확정한 A/B 설계가 바뀌었는지 알아보는 표시 (바뀌면 프롬프트를 새로 만듦)."""
    return tuple(str(plan.get(k) or "") for k in ("variable", "a", "b", "b_ref", "a_mode", "a_reason"))


def media_s2_sample_draft(plan: dict) -> dict:
    """AI를 쓸 수 없을 때의 예시 프롬프트 (media_handoff.py의 예시 값)."""
    return {**{k: MEDIA_HANDOFF_PROMPT_SAMPLE[k] for k in ("base", "slot_a", "slot_b")},
            "fixed": list(MEDIA_HANDOFF_PROMPT_SAMPLE["fixed"]), "variable": plan.get("variable") or ""}


def media_s2_draft() -> dict | None:
    """지금 확정한 A/B에 대한 프롬프트 draft (아직 안 만들었거나 ①에서 다시 확정했으면 None). 콜백에서도 씀."""
    plan = media_variable_confirmed_plan()[0]
    gen = st.session_state.get(MEDIA_S2_GEN)
    if plan is None or not gen or gen["sig"] != media_s2_plan_sig(plan):
        return None
    return gen["draft"]


def media_s2_ensure_draft(plan: dict) -> dict:
    """프롬프트 draft를 준비합니다 (이미 있으면 그대로).
    순서: 전에 넘긴 값(같은 독립 변수일 때) → OpenAI로 새로 만들기 → 예시 값."""
    sig = media_s2_plan_sig(plan)
    gen = st.session_state.get(MEDIA_S2_GEN)
    if gen and gen["sig"] == sig:
        return gen
    for k in ("media-s2-prompt-A", "media-s2-prompt-B", "media-s2-ai-result", MEDIA_S2_REFINED,
              "media-s2-input-A", "media-s2-edit-A"):
        st.session_state.pop(k, None)
    force = st.session_state.pop("media-s2-regen", False)   # '다시 만들기'를 눌렀으면 전에 넘긴 값을 쓰지 않음
    saved = media_handoff_prompt()
    gen = {"sig": sig, "source": "", "error": "", "mode": media_s2_mode(plan)}
    if (not force and not saved["sample"] and saved.get("variable") == plan.get("variable")
            and saved["base"].count(MEDIA_HANDOFF_SLOT) == 1):
        gen.update(source="saved", draft={k: saved[k] for k in MEDIA_S2_HANDOFF_KEYS})
        # 전에 넘긴 칸 내용으로 채우고, AI 다듬기를 했던 값이면 다듬기 완료로 봄
        st.session_state["media-s2-prompt-A"], st.session_state["media-s2-prompt-B"] = saved["prompt_a"], saved["prompt_b"]
        if saved["changes"]:
            st.session_state[MEDIA_S2_REFINED] = sig
            st.session_state["media-s2-ai-result"] = {
                "base": saved["base"], "prompt_a": saved["prompt_a"], "prompt_b": saved["prompt_b"],
                "changes": [{**c, "basis_ok": True} for c in saved["changes"]], "avoid": saved["avoid"],
                "include": saved["include"], "slot_warnings": [], "used_report": True, "provider": "전에 넘긴 결과"}
    elif media_s2_ai_ready():
        try:
            with st.spinner("AI가 A안 프롬프트를 만들고, 독립 변수만 바꿔 B안 프롬프트를 만드는 중이에요…"):
                draft = media_s2_generate(plan, gen["mode"])
            gen.update(source="ai", draft={k: draft[k] for k in MEDIA_S2_HANDOFF_KEYS}, notes=draft.get("notes", ""))
        except (RuntimeError, ValueError) as err:
            gen.update(source="sample", draft=media_s2_sample_draft(plan), error=str(err))
    else:
        gen.update(source="sample", draft=media_s2_sample_draft(plan),
                   error=f"secrets.toml에 {MEDIA_S2_AI_KEY}가 없어 AI로 만들 수 없어요")
    gen["orig"] = dict(gen["draft"])   # '되돌리기'가 돌아갈 처음 프롬프트
    st.session_state[MEDIA_S2_GEN] = gen
    return gen


def _media_s2_regen() -> None:
    """'A·B 다시 만들기' 버튼 콜백: 지금 프롬프트를 버리고 OpenAI로 새로 만듭니다 (다음 화면에서 만듦)."""
    st.session_state.pop(MEDIA_S2_GEN, None)
    st.session_state["media-s2-regen"] = True


def _media_s2_reset() -> None:
    """'되돌리기' 버튼 콜백: A·B 두 칸을 처음 만든 프롬프트로 함께 되돌립니다 (둘의 차이를 변수 하나로 유지)."""
    gen = st.session_state.get(MEDIA_S2_GEN)
    if not gen:
        return
    gen["draft"] = dict(gen["orig"])
    st.session_state["media-s2-edit-A"] = False
    st.session_state.pop(MEDIA_S2_INPUT.format("A"), None)
    for n in ("A", "B"):
        st.session_state[f"media-s2-prompt-{n}"] = media_handoff_fill(gen["draft"]["base"], gen["draft"][f"slot_{n.lower()}"])


def media_s2_report_rules() -> dict:
    """리포트 규칙 팝업에서 쓰는 리포트 값 (① 탭이 저장한 store("report")). ① 탭을 아직 안 열었으면 빈 목록."""
    report = store_get("report") or {}
    claims = report.get("ad_claims") or {}
    return {"forbidden": claims.get("forbidden") or [],          # 금지 표현 (독일어·한국어)
            "marketing_rules": report.get("marketing_rules") or [],   # 독일 광고 표현 규칙 8개 (DB ID)
            "seori_profile": report.get("seori_profile") or {},       # 우리 제품 강점·약점·광고 가능 여부
            "competitor_profiles": report.get("competitor_profiles") or []}


# ─────────────────────────────────────────────
# AI로 다듬기
# ─────────────────────────────────────────────
def _media_s2_ai_refine() -> None:
    """'AI로 다듬기' 버튼 콜백 (프롬프트 칸이 그려지기 전에 실행되어 칸 값을 바꿀 수 있음).
    확인을 통과하면 프롬프트 A·B 칸과 기본 프롬프트를 다듬은 문장으로 바꾸고, 다듬기 완료로 표시합니다.
    실패하면 칸은 그대로 두고 경고 문구만 남깁니다."""
    gen = st.session_state.get(MEDIA_S2_GEN)
    if not gen:
        return
    # 사용자가 칸을 직접 고쳤으면(마지막 AI 결과·처음 만든 프롬프트와 다르면) 고친 A·B도 AI에 보냄
    # → AI가 고친 내용에서 분위기·공통 요소만 뽑아 A·B에 똑같이 반영 (2026-10-27 PM)
    _media_s2_keep_input("A")   # 입력 칸이 열린 채로 눌렀어도 마지막 글을 보관
    edits = media_s2_user_edits(gen)
    try:
        check = media_s2_ai_run(gen["draft"], edits)
    except RuntimeError as err:
        st.session_state["media-s2-ai-msg"] = [f"AI 다듬기 실패: {err}. 프롬프트는 그대로 두었어요."]
        return
    if not check["ok"]:
        st.session_state["media-s2-ai-msg"] = [f"AI 답을 쓰지 않았어요: {e}" for e in check["errors"]]
        return
    result = check["result"]
    gen["draft"]["base"] = result["base"]
    st.session_state["media-s2-prompt-A"] = result["prompt_a"]
    st.session_state["media-s2-prompt-B"] = result["prompt_b"]
    st.session_state["media-s2-ai-result"] = result
    st.session_state["media-s2-edit-A"] = False                 # 다듬은 결과를 보기 화면으로 보여 줌
    st.session_state.pop(MEDIA_S2_INPUT.format("A"), None)
    st.session_state[MEDIA_S2_REFINED] = gen["sig"]
    st.session_state["media-s2-ai-msg"] = check["warnings"]
    st.session_state["media-s2-show-ai"] = True   # 다음 화면에서 'AI 다듬기 결과' 팝업을 띄움


def media_s2_user_edits(gen: dict) -> dict | None:
    """사용자가 프롬프트 A를 직접 고쳤으면 {"A": 지금 A}, 아니면 None (B는 직접 고칠 수 없음).
    기준: 마지막 AI 다듬기 결과가 있으면 그 결과, 없으면 처음 만든 프롬프트."""
    a, b = st.session_state.get("media-s2-prompt-A", ""), st.session_state.get("media-s2-prompt-B", "")
    result = st.session_state.get("media-s2-ai-result")
    if result:
        before = (result["prompt_a"], result["prompt_b"])
    else:
        orig = gen.get("orig") or gen["draft"]
        before = (media_handoff_fill(orig["base"], orig["slot_a"]), media_handoff_fill(orig["base"], orig["slot_b"]))
    return {"A": a} if a != before[0] else None   # 2026-10-27 PM: 수정은 프롬프트 A에서만


def media_s2_ai_current(prompt_a: str, prompt_b: str) -> dict | None:
    """지금 칸의 프롬프트가 AI 다듬기 결과 그대로일 때만 그 결과 (직접 고치면 None → 바꾼 곳 표는 넘기지 않음)."""
    result = st.session_state.get("media-s2-ai-result")
    if result and result["prompt_a"] == prompt_a and result["prompt_b"] == prompt_b:
        return result
    return None


MEDIA_S2_HELP = ("정확한 성과 측정을 위해 AI가 선정한 핵심 변수({var}) 외 세부 요소는 고정됩니다. "
                 "브랜드에 어울리는 '전체 분위기'를 편하게 수정해주세요.")


@st.dialog("A안·B안 프롬프트 만들기")
def _media_s2_help_dialog(variable: str) -> None:
    """제목 옆 (?) 버튼을 누르면 뜨는 설명 (✕로 닫힘)."""
    st.markdown(MEDIA_S2_HELP.format(var=variable))


def media_s2_ai_header(gen: dict) -> None:
    """맨 위 제목 줄: '📝 A안·B안 프롬프트 만들기' + (?) 버튼 (누르면 설명이 뜸)."""
    # (?)는 펼침 메뉴(popover) 대신 아이콘만 있는 버튼 → 누르면 설명 팝업 (아래 화살표가 붙지 않게)
    with st.container(horizontal=True, vertical_alignment="center", key="media-s2-title-row"):
        st.markdown('<div class="media-s2-title">📝 A안·B안 프롬프트 만들기</div>', unsafe_allow_html=True)
        st.button("", key="media-s2-help", icon=":material/help_outline:", type="tertiary",
                  on_click=_media_s2_help_dialog, args=(gen["draft"]["variable"],))
    if gen["source"] == "sample" and gen.get("error"):
        st.warning(f"AI로 A·B 프롬프트를 만들지 못했어요 ({gen['error']}). 'A·B 다시 만들기'를 눌러 다시 시도해 주세요.")


def media_s2_marked(text: str, slot: str) -> str:
    """보기 화면용 HTML: 줄바꿈을 지키고, 독립 변수 부분(slot)에 빨간 밑줄 (.media-s2-var)."""
    if slot and text.count(slot) == 1:
        head, _, tail = text.partition(slot)
        body = f'{escape(head)}<span class="media-s2-var">{escape(slot)}</span>{escape(tail)}'
    else:
        body = escape(text)
    return f'<div class="media-s2-view">{body}</div>'


@st.dialog("프롬프트 번역본", width="medium")
def _media_s2_ko_dialog(name: str, text: str, slot: str) -> None:
    """'번역본 보기' 팝업: 위에 영어 프롬프트(독립 변수 빨간 밑줄), 아래에 한국어 번역 (✕로 닫힘)."""
    st.markdown(f"**프롬프트 {name} · {'대조군' if name == 'A' else '실험군'}**")
    st.markdown('<div class="media-s2-ko-label">영어 (원문)</div>' + media_s2_marked(text, slot).replace(
        'class="media-s2-view"', 'class="media-s2-view media-s2-view-auto"'), unsafe_allow_html=True)
    try:
        with st.spinner("한국어로 옮기는 중이에요…"):
            ko = media_s2_translate(text, slot)
    except RuntimeError as err:
        st.warning(f"번역하지 못했어요: {err}")
        return
    # 번역문의 [[ ]] 부분(독립 변수)에 원문과 같은 빨간 밑줄
    head, _, rest = ko.partition("[[")
    mid, _, tail = rest.partition("]]")
    body = (f'{escape(head)}<span class="media-s2-var">{escape(mid)}</span>{escape(tail)}' if rest and mid
            else escape(ko.replace("[[", "").replace("]]", "")))
    st.markdown(f'<div class="media-s2-ko-label">한국어 (번역)</div>'
                f'<div class="media-s2-view media-s2-view-auto">{body}</div>', unsafe_allow_html=True)


MEDIA_S2_INPUT = "media-s2-input-{}"   # 수정 중 입력 칸 key. 고친 글은 media-s2-prompt-{A}에 따로 보관
# (입력 칸 key에만 두면 '수정 완료'로 칸이 닫힐 때 Streamlit이 그 값을 지워서, 고친 내용이 사라졌음 — 2026-10-27 수정)


def _media_s2_keep_input(name: str) -> None:
    """입력 칸 글을 프롬프트 값(media-s2-prompt-{name})에 옮겨 보관 (칸이 닫혀도 남게)."""
    ikey = MEDIA_S2_INPUT.format(name)
    if ikey in st.session_state:
        st.session_state[f"media-s2-prompt-{name}"] = st.session_state[ikey]


def _media_s2_toggle_edit(name: str) -> None:
    """'수정하기' / '수정 완료' 버튼 콜백: 그 칸을 입력 칸 ↔ 보기 화면(빨간 밑줄)으로 바꿈.
    열 때는 지금 프롬프트를 입력 칸에 넣고, 닫을 때는 입력 칸 글을 프롬프트 값에 보관."""
    key = f"media-s2-edit-{name}"
    if st.session_state.get(key, False):
        _media_s2_keep_input(name)
        st.session_state.pop(MEDIA_S2_INPUT.format(name), None)
    else:
        st.session_state[MEDIA_S2_INPUT.format(name)] = st.session_state.get(f"media-s2-prompt-{name}", "")
    st.session_state[key] = not st.session_state.get(key, False)


def media_s2_ai_report(draft: dict, prompt_a: str, prompt_b: str) -> None:
    """프롬프트 칸 아래: AI 경고, 금지 단어 경고 (AI 다듬기 결과 표는 팝업 _media_s2_ai_dialog)."""
    for msg in st.session_state.pop("media-s2-ai-msg", []):
        st.warning(msg)
    # 금지 단어 검사는 늘 돌리고, 걸렸을 때만 경고
    material = media_s2_ai_material(draft)
    hits = media_s2_forbidden_hits(prompt_a + "\n" + prompt_b, material["forbidden"])
    if hits:
        st.warning("리포트 금지 표현이 프롬프트에 있어요: " + ", ".join(hits))


def media_s2_refine_section(gen: dict, plan: dict) -> tuple[str, str, bool]:
    """프롬프트 박스 두 칸(위에 A·B 소재 요약 → 프롬프트 보기/수정 → 되돌리기·수정하기) → 독립 변수 줄 → 도구 줄 → 경고.
    프롬프트 A, B와 확인 통과 여부를 돌려줍니다."""
    draft = gen["draft"]
    media_s2_ai_header(gen)
    listing = media_s2_listing()
    summary = {   # 박스 맨 위 A·B 소재 요약 (①에서 확정한 A·B, A는 지금 메인 이미지 문제점도)
        # A가 새로 설계(new)면 이름을 '새 기준 사진'으로, 아래 줄은 ①이 넘긴 이유(a_reason)를 먼저 보여 줌
        "A": f'<b>A · {"현재" if gen.get("mode") == "keep" else "새 기준 사진"} (대조군)</b> : {escape(plan["a"])}'
             + (f'<br><span>{escape(note)}</span>' if (note := (plan.get("a_reason") if gen.get("mode") == "new" else "")
                                                       or listing.get("main_image_issue")) else ""),
        "B": f'<b>B · 제안 (실험군)</b> : {escape(plan["b"])}',
    }
    prompts = {}
    c1, c2 = st.columns(2)
    for col, name in ((c1, "A"), (c2, "B")):
        key = f"media-s2-prompt-{name}"
        if key not in st.session_state:
            st.session_state[key] = media_handoff_fill(draft["base"], draft[f"slot_{name.lower()}"])
        # 2026-10-27 PM: 수정은 프롬프트 A에서만 (전체 분위기·배경). B는 AI로 다듬기를 누르면 A와 똑같이 맞춰짐
        editing = name == "A" and st.session_state.get(f"media-s2-edit-{name}", False)
        with col:
            with st.container(border=True, key=f"media-s2-prompt-box-{name}"):
                # 안쪽 div 하나로 감싸야 세로 가운데 정렬할 때 'A · 현재 (대조군) : …'가 한 줄로 이어짐
                st.markdown(f'<div class="media-s2-sum"><div>{summary[name]}</div></div>', unsafe_allow_html=True)
                st.markdown(f"**프롬프트 {name} · {'대조군' if name == 'A' else '실험군'}**")
                if editing:   # 수정 중: 입력 칸 (A만. B에는 'AI로 다듬기'를 눌렀을 때 반영)
                    ikey = MEDIA_S2_INPUT.format(name)
                    if ikey not in st.session_state:
                        st.session_state[ikey] = st.session_state[key]
                    st.text_area(f"프롬프트 {name}", key=ikey, height=230, label_visibility="collapsed",
                                 on_change=_media_s2_keep_input, args=(name,))
                    prompts[name] = st.session_state[key]
                else:         # 보기: 독립 변수 부분에 빨간 밑줄
                    prompts[name] = st.session_state[key]
                    st.markdown(media_s2_marked(prompts[name], draft[f"slot_{name.lower()}"]), unsafe_allow_html=True)
                with st.container(horizontal=True, key=f"media-s2-box-btns-{name}"):
                    st.button("되돌리기", key=f"media-s2-btn-reset-{name}", type="secondary", icon=":material/undo:",
                              on_click=_media_s2_reset, help="A·B 두 칸을 처음 만든 프롬프트로 함께 되돌려요")
                    # 버튼 순서: 되돌리기 · 번역본 보기 · (A만) 수정하기
                    st.button("번역본 보기", key=f"media-s2-btn-ko-{name}", type="secondary", icon=":material/translate:",
                              disabled=not media_s2_ai_ready(), on_click=_media_s2_ko_dialog,
                              args=(name, prompts[name], draft[f"slot_{name.lower()}"]),
                              help="영어 프롬프트와 한국어 번역을 팝업으로 보여 줘요 (OpenAI 번역)")
                    if name == "A":
                        st.button("수정 완료" if editing else "수정하기", key=f"media-s2-btn-edit-{name}", type="secondary",
                                  icon=":material/check:" if editing else ":material/edit:",
                                  on_click=_media_s2_toggle_edit, args=(name,),
                                  help=None if editing else ("전체 분위기·배경만 고칠 수 있어요. "
                                                            "'AI로 다듬기'를 누르면 프롬프트 B에도 똑같이 반영돼요"))

    st.markdown(f'<div class="media-s2-ab-var">🎯 <span>독립 변수</span> : <b>{escape(plan["variable"])}</b></div>',
                unsafe_allow_html=True)

    # 도구 줄: 왼쪽 '리포트에서 받은 규칙 ↗' · 'AI 다듬기 목록 보러가기 ↗', 오른쪽 'A·B 다시 만들기' + 'AI로 다듬기'
    rules = media_s2_report_rules()
    ready = media_s2_ai_ready()
    has_result = bool(st.session_state.get("media-s2-ai-result"))
    with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center",
                      key="media-s2-tool-row"):
        with st.container(horizontal=True, vertical_alignment="center", width="content", key="media-s2-link-btns"):
            st.button(f"리포트에서 받은 규칙 · 금지 표현 {len(rules['forbidden'])}개 · "
                      f"광고 표현 규칙 {len(rules['marketing_rules'])}개 ↗", key="media-s2-btn-rules", type="secondary",
                      on_click=_media_s2_rules_dialog)
            st.button("AI 다듬기 목록 보러가기 ↗", key="media-s2-btn-ai-list", type="secondary",
                      disabled=not has_result, on_click=_media_s2_ai_dialog,
                      help=None if has_result else "'AI로 다듬기'를 누르면 볼 수 있어요")
        with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center",
                          width="content", key="media-s2-ai-btns"):
            st.button("A·B 다시 만들기", key="media-s2-btn-regen", type="secondary", icon=":material/refresh:",
                      disabled=not ready, on_click=_media_s2_regen,
                      help="①에서 확정한 A·B로 프롬프트를 처음부터 새로 만들어요 (지금 고친 내용은 사라져요)")
            st.button("AI로 다듬기", key="media-s2-btn-refine", type="secondary", icon=":material/auto_awesome:",
                      disabled=not ready, on_click=_media_s2_ai_refine,
                      help=(f"OpenAI({MEDIA_S2_OPENAI_MODEL})로 리포트 규칙·독일 디자인 DB에 맞춰 공통 부분만 다듬고, "
                            "프롬프트 A에서 고친 분위기·배경을 B에도 똑같이 반영해요 (독립 변수·고정 요소는 그대로)" if ready
                            else f"secrets.toml에 {MEDIA_S2_AI_KEY}를 넣어 주세요"))

    check = media_handoff_check(draft, prompts["A"], prompts["B"])
    if media_s2_user_edits(gen):   # A를 고쳤고 아직 다듬기 전: B와 다른 건 정상 (다듬기를 누르면 맞춰짐)
        st.info("프롬프트 A를 고쳤어요. 'AI로 다듬기'를 누르면 고친 분위기·배경이 프롬프트 B에도 똑같이 반영돼요.",
                icon=":material/info:")
    elif not check["ok"]:   # 통과했을 때는 따로 알리지 않음 (문제가 있을 때만 경고)
        if not check["slot_ok"]:
            st.warning("독립 변수 부분이 바뀌었어요. '되돌리기'로 되돌려 주세요.")
        elif not check["same_rest"]:
            st.warning("독립 변수 말고도 A와 B가 서로 달라요. '되돌리기'로 되돌려 주세요.")
        if check["missing"]:
            st.warning("빠진 고정 요소: " + ", ".join(check["missing"]))
    media_s2_ai_report(draft, prompts["A"], prompts["B"])
    return prompts["A"], prompts["B"], check["ok"]


@st.dialog("AI 다듬기 결과", width="large")
def _media_s2_ai_dialog() -> None:
    """AI로 다듬기 결과 팝업 (다듬기 직후 자동으로 뜨고, 'AI 다듬기 목록 보러가기 ↗'로 다시 열 수 있음, ✕로 닫힘).
    표 모양은 리포트 규칙 팝업과 같은 .media-s2-rules."""
    result = st.session_state.get("media-s2-ai-result")
    if not result:
        st.caption("아직 AI로 다듬은 결과가 없어요.")
        return
    st.caption(f"{result.get('provider', '')} · 바꾼 곳 {len(result['changes'])}개")
    if not result["used_report"]:
        st.info("리포트 규칙 없이 다듬었어요 (아마존 메인 이미지 규칙만 사용). ① 문제 분석 탭을 열고 다시 눌러 주세요.")
    for w in result["slot_warnings"]:
        st.warning(f"A/B 문구 확인: {w}")
    rows = "".join(
        f"<tr><td>{escape(c['where'])}</td><td>{escape(c['kind'])}</td><td>{escape(c['reason'])}</td>"
        f"<td><b>{escape(c['basis'] or '-')}</b>{'' if c.get('basis_ok', True) else ' ⚠️ 근거 확인 필요'}</td></tr>"
        for c in result["changes"]) or '<tr><td colspan="4">AI가 바꾼 곳이 없어요.</td></tr>'
    st.markdown('<div class="media-s2-rules"><h4>✏️ 바꾼 곳</h4>'
                '<table class="media-s2-rules-ai"><colgroup><col><col><col><col></colgroup>'
                f"<thead><tr><th>바꾼 곳</th><th>뺌·더함</th><th>이유</th><th>근거</th></tr></thead><tbody>{rows}</tbody>"
                "</table></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="media-s2-rules"><h4>🚫 찍지 말 것</h4></div>', unsafe_allow_html=True)
        st.markdown("\n".join(f"- {escape(x)}" for x in result["avoid"]) or "-")
    with c2:
        st.markdown('<div class="media-s2-rules"><h4>✅ 넣을 것</h4></div>', unsafe_allow_html=True)
        st.markdown("\n".join(f"- {escape(x)}" for x in result["include"]) or "-")


@st.dialog("리포트에서 받은 규칙", width="large")
def _media_s2_rules_dialog() -> None:
    """리포트 규칙 팝업 (오른쪽 위 ✕나 바깥을 누르면 닫힘). 표 두 개로 정리: 금지 표현(표현 | 이유), 광고 표현 규칙(ID | 항목 | 규칙).
    표 모양·열 폭은 media_stage2_style.css의 .media-s2-rules."""
    rules = media_s2_report_rules()
    if not rules["forbidden"] and not rules["marketing_rules"]:
        st.caption("① 문제 분석 탭을 한 번 열면 리포트 값이 들어와요.")
        return

    def split(text):   # "표현 (이유)" → ("표현", "이유"), 괄호가 없으면 이유는 "-"
        text = str(text).strip()
        if text.endswith(")") and " (" in text:
            head, _, tail = text.rpartition(" (")
            return head.strip(), tail[:-1].strip()
        return text, "-"

    rows = "".join(f"<tr><td>{i}</td><td>{escape(w)}</td><td>{escape(why)}</td></tr>"
                   for i, (w, why) in enumerate((split(f) for f in rules["forbidden"]), 1))
    st.markdown(f'<div class="media-s2-rules"><h4>🚫 금지 표현 <em>{len(rules["forbidden"])}개</em></h4>'
                '<table class="media-s2-rules-ban"><colgroup><col><col><col></colgroup>'
                f"<thead><tr><th>#</th><th>쓰면 안 되는 표현</th><th>이유</th></tr></thead><tbody>{rows}</tbody></table>"
                "</div>", unsafe_allow_html=True)
    rows = "".join(f"<tr><td><b>{escape(r['id'])}</b></td><td>{escape(r['topic'])}</td><td>{escape(r['rule'])}</td></tr>"
                   for r in rules["marketing_rules"])
    st.markdown(f'<div class="media-s2-rules"><h4>📏 독일 광고 표현 규칙 <em>{len(rules["marketing_rules"])}개</em></h4>'
                '<table class="media-s2-rules-law"><colgroup><col><col><col></colgroup>'
                f"<thead><tr><th>ID</th><th>항목</th><th>규칙</th></tr></thead><tbody>{rows}</tbody></table>"
                "</div>", unsafe_allow_html=True)


@st.dialog("AI 다듬기가 필요해요")
def _media_s2_need_refine_dialog(edited: bool = False) -> None:
    """'다음'을 눌렀는데 AI로 다듬기를 안 했거나, 다듬은 뒤 프롬프트를 직접 고쳤을 때 가운데에 뜨는 경고창."""
    # 따옴표 바로 뒤에 한글이 붙으면 마크다운 굵게(**)가 안 먹어서 HTML <b>로 씀
    if edited:
        st.markdown("프롬프트를 고쳤어요. 넘어가기 전에 <b>‘AI로 다듬기’</b>를 다시 눌러 주세요.", unsafe_allow_html=True)
        st.caption("고친 내용에서 전체 분위기·공통 요소만 뽑아 프롬프트 A와 B에 똑같이 반영해요.")
    else:
        st.markdown("사진·영상 초안을 만들기 전에 <b>‘AI로 다듬기’</b>를 눌러 주세요.", unsafe_allow_html=True)
        st.caption("리포트 규칙·독일 디자인 DB에 맞춰 프롬프트를 다듬어야 사진·영상 초안 제작으로 넘어갈 수 있어요.")
    if st.button("확인", key="media-s2-btn-need-refine-ok", type="primary"):
        st.rerun()


# ─────────────────────────────────────────────
# 3단계로 넘기기 ('다음: 사진·영상 초안 제작 →' 버튼, media_page.py)
# ─────────────────────────────────────────────
def media_s2_handoff_value(draft: dict, prompt_a: str, prompt_b: str) -> dict:
    """3단계(사진·영상 초안 제작, 외주 정리)로 넘기는 값 (모양은 media_handoff.py의 MEDIA_HANDOFF_PROMPT_SAMPLE).
    changes·avoid·include는 지금 칸이 AI 다듬기 결과 그대로일 때만 채웁니다 (직접 고치면 빈 목록)."""
    keep = {k: draft[k] for k in MEDIA_S2_HANDOFF_KEYS}
    ai = media_s2_ai_current(prompt_a, prompt_b) or {}
    changes = [{k: c[k] for k in ("where", "kind", "reason", "basis")} for c in ai.get("changes", [])]
    return {**keep, "prompt_a": prompt_a, "prompt_b": prompt_b, "changes": changes,
            "avoid": list(ai.get("avoid", [])), "include": list(ai.get("include", []))}


def media_s2_handoff_now():
    """'다음: 사진·영상 초안 제작 →' 버튼(media_page.py)을 누를 때 먼저 부르는 콜백.
    - AI로 다듬기를 한 번도 안 했으면(키가 있을 때) 넘기지 않고 False → 탭을 옮기지 않고 가운데 경고창
    - 확인을 통과하고 전에 넘긴 값과 다르면 3단계로 넘김 (Supabase에 저장). 3단계로 가도 이 탭의 칸 내용은 그대로 남음"""
    draft = media_s2_draft()
    if draft is None:   # ①에서 확정 전이거나 이번 접속에서 이 탭을 아직 안 열었음 → 전에 넘긴 값을 그대로 둠
        return None
    a, b = st.session_state.get("media-s2-prompt-A", ""), st.session_state.get("media-s2-prompt-B", "")
    if not (a and b):
        return None
    # 다듬기를 안 했거나, 다듬은 뒤에 칸을 직접 고쳤으면(지금 칸 ≠ 마지막 AI 결과) 넘기지 않고 경고창 (2026-10-27 PM)
    if media_s2_ai_ready() and (st.session_state.get(MEDIA_S2_REFINED) != st.session_state[MEDIA_S2_GEN]["sig"]
                                or media_s2_ai_current(a, b) is None):
        st.session_state["media-s2-need-refine"] = "edited" if st.session_state.get("media-s2-ai-result") else True
        return False
    if not media_handoff_check(draft, a, b)["ok"]:
        st.toast("프롬프트 A·B가 확인을 통과하지 못해 넘기지 않았어요. A/B 소재 준비에서 고쳐 주세요.", icon="⚠️")
        return None
    value = media_s2_handoff_value(draft, a, b)
    saved = media_handoff_prompt()
    if saved["sample"] or any(saved.get(k) != v for k, v in value.items()):
        media_handoff_set_prompt(value)
        st.toast("프롬프트 A·B를 사진·영상 초안 제작으로 넘겼어요", icon="✅")
    return None


# ─────────────────────────────────────────────
# 화면
# ─────────────────────────────────────────────
def media_s2_ab_section() -> dict | None:
    """①에서 '이 변수로 확정'한 A/B 설계를 읽습니다 (A·B 요약은 아래 프롬프트 박스 맨 위에 보여 줌).
    확정 전이면 빈 카드와 '① 으로 가서 확정하기' 버튼만 보여 주고 None (그 아래 프롬프트 만들기도 그리지 않음)."""
    plan, state = media_variable_confirmed_plan()
    if plan is None:   # 아직 확정 전: 빈 카드로 ①에서 확정하도록 안내
        with st.container(border=True, key="media-s2-ab-empty"):
            st.markdown("**아직 확정한 변수가 없어요**")
            st.caption("① 에서 변수와 B안을 고르고 '이 변수로 확정'을 누르면 여기에 A/B 소재와 프롬프트가 나와요.")
            st.button("① 으로 가서 확정하기", key="media-s2-btn-go-confirm", type="primary",
                      on_click=media_variable_go_step)
        return None
    if state == "changed":   # ①에서 다른 값을 골랐지만 아직 확정하지 않음
        with st.container(horizontal=True, vertical_alignment="center", key="media-s2-ab-pending"):
            st.markdown(":orange-badge[확정 안 됨] ① 에서 새로 고른 값이 아직 확정되지 않아, 이전에 확정한 값으로 보여 줘요")
            st.button("① 으로 가서 확정하기", key="media-s2-btn-go-confirm", type="secondary",
                      on_click=media_variable_go_step)
    return plan


def media_s2_prompt_section(plan: dict) -> None:
    """A안·B안 프롬프트 만들기 (제목 줄 → 프롬프트 박스 두 칸 → 독립 변수 줄 → 도구 줄 → 경고).
    넘기기는 맨 아래 '다음: 사진·영상 초안 제작 →' 버튼이 media_s2_handoff_now()로 함."""
    gen = media_s2_ensure_draft(plan)
    media_s2_refine_section(gen, plan)


def media_s2_summary_chip() -> None:
    """② 탭 바 오른쪽 칩 '[독립 변수] … · [🎯 목표 KPI] …' — ① 가설에서 변수 도출의 요약 칩과 같은 내용·모양 (2026-10-27 PM).
    ②에서는 공통 '목표 KPI' 칩(media_variable_kpi_chip) 대신 이 칩을 보여 줌 (공통 칩은 media_stage2_style.css에서 ②일 때만 숨김).
    값은 ①에서 확정한 plan (확정 전이면 고르는 중인 값), ⓘ에는 ①과 같이 2번 탭 가설."""
    current, _, _ = media_variable_plan()
    plan = media_variable_confirmed_plan()[0] or current
    picked = media_variable_candidates()["picked"]
    hypo = media_variable_loaded()
    variable = f"{plan.get('variable')} ({media_variable_label(picked)})" if picked else (plan.get("variable") or "없음")
    # 이번 접속에 ①을 아직 안 열어 가설을 안 불러왔으면 확정한 KPI 숫자만 (가설 Then은 불러온 뒤)
    goal = media_variable_goal_text(plan, hypo) if hypo.get("text") else media_variable_kpi_text(plan)
    with st.container(key="media-s2-chip"):
        st.markdown(f":violet-badge[독립 변수] {variable} · :green-badge[🎯 목표 KPI] {goal}",
                    help=media_variable_hypo_tip(hypo) if hypo.get("text") else None)


def media_stage2_render():
    """하위 탭 ② A/B 소재 준비 (이름은 MEDIA_S2_TAB_LABEL). 반드시 media_render() 안에서 부릅니다.
    ①에서 확정하기 전에는 빈 카드만 보여 줍니다."""
    media_s2_summary_chip()   # 탭 바 오른쪽: 독립 변수 + 목표 KPI (① 요약 칩과 같은 정보, 공통 KPI 칩 대신)
    plan = media_s2_ab_section()
    if plan is None:
        return
    media_s2_prompt_section(plan)
    if st.session_state.pop("media-s2-show-ai", False):        # 방금 AI로 다듬었으면 결과 팝업
        _media_s2_ai_dialog()
    elif need := st.session_state.pop("media-s2-need-refine", False):   # '다음'을 눌렀는데 다듬기 전이면 가운데 경고창
        _media_s2_need_refine_dialog(need == "edited")
