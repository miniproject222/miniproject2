# 3. 매체 제작 > 가설에서 변수 도출
# '가설 불러오기'를 누르면 2번 탭이 저장한 가설(store "hypothesis")을 다시 읽고, 그 가설로 후보 변수 묶음을 만들어
# (AI 또는 규칙, media_variable_ai.py) 사용자가 변수 블럭에서 A/B로 실험할 변수 하나와 그 변수의 B안을 고릅니다.
# 어떤 변수 블럭이든 고를 수 있고, 메인 이미지로 진행할 수 없는 변수를 고르면 경고를 보여 주고 2·3단계로 넘기는 확정만 막습니다.
# 3번 탭의 하위 탭 ①(가설에서 변수 도출)에서 부릅니다.
# 고른 A/B 설계(plan)는 1번 리포트 값으로 채워 화면에 보여 주고, 사용자가 확정하면 2단계로 넘깁니다 (media_handoff.py).
# 바깥 값을 읽는 곳은 두 함수뿐입니다: 가설 media_variable_saved(), 리포트 media_variable_report_sqp()
import re

import streamlit as st

from common.common_store import store_get
from modules.media.media_handoff import (MEDIA_HANDOFF_PLAN, media_handoff_clear_plan, media_handoff_plan,
                                         media_handoff_set_plan)
from modules.media.media_variable_ai import MEDIA_VARIABLE_AI_RULE_SOURCE, media_variable_generate

MEDIA_VARIABLE_TAB_LABEL = "가설에서 변수 도출"   # 하위 탭 ① 이름 (media_page.py와 다른 하위 탭의 '① 으로 가서 확정하기' 버튼이 씀)
# '가설 불러오기'로 읽어 둔 값 (session_state). 다시 불러오기 전까지는 2번 탭에서 가설을 바꿔도 이 값을 씀
MEDIA_VARIABLE_HYPO_KEY = "media-variable-hypo"   # 불러온 가설 (media_variable_saved()의 모양)
MEDIA_VARIABLE_GEN_KEY = "media-variable-gen"     # 그 가설의 후보 묶음 {"text", "set", "source", "error"}

# 가설의 If를 짧게(규칙 후보의 B안) 만들 때 끝에서 걷어 낼 문장 틀 (정규식, 바꿀 말). 위에서부터 차례로 적용
MEDIA_VARIABLE_IF_TRIMS = [(r"(을|를) 적용한다면$", " 적용"), (r"바꾸면$", "변경"), (r"(한다면|하면)$", "")]
# Then '지표가 A에서 B(이상)로 (N%) 오를/낮아질 것이다' 모양 → '지표 A → B (N%↑)'
MEDIA_VARIABLE_THEN_PATTERN = (r"(?P<metric>.+?)(?:이|가) (?P<a>\S+?)에서 (?P<b>\S+?)(?P<more> 이상)?(?:으로|로) "
                               r"(?:(?P<pct>[\d.]+%p?) )?(?P<verb>오를|높아질|늘어날|올라갈|낮아질|줄어들|떨어질) 것이다")
MEDIA_VARIABLE_THEN_UP = ("오를", "높아질", "늘어날", "올라갈")
# KPI 이름: 가설 문장(2번 탭과 같은 원문)은 그대로 두고, 화면에 보일 때만 쉬운 이름으로 바꿉니다
MEDIA_VARIABLE_KPI_RAW = "클릭 점유율 ÷ 노출 점유율"
MEDIA_VARIABLE_KPI = MEDIA_HANDOFF_PLAN["kpi"]   # "노출 대비 클릭률"
# 가설이 1번 리포트 검색어 클릭 분석(sqp)의 KPI를 말하는지 볼 표시 (원래 이름이나 쉬운 이름 중 하나)
MEDIA_VARIABLE_HYPO_KPIS = [MEDIA_VARIABLE_KPI_RAW, MEDIA_VARIABLE_KPI]
# 목표 KPI 칩의 짧은 출처 표시 (리포트 검색어 클릭 분석은 가상 SQP, 전체 출처는 칩의 ⓘ 툴팁)
MEDIA_VARIABLE_SQP_LABEL = "가상 데이터"

# 후보 묶음 모양 (media_variable_ai.py가 만듦): {"kpi", "note", "variables"}
# 블럭 하나 = 사용자가 고를 수 있는 변수 하나 (어느 블럭이든 고를 수 있음).
# 판정(이미지로 진행 / 진행 불가)은 묶음에 쓰지 않고 media_variable_judge()가 규칙으로 계산합니다.
# 변수 칸: name(블럭 이름 = 독립 변수), kind(main_image·title·price 등), if_match(가설의 If와 맞는지),
#          fallback(제외되면 대신 쓸 곳), reason(If와 안 맞는 이유), b_options(이 변수로 만들 B안 목록)
# B안 칸: label(B안 체크박스 이름), b, ref_prompt / 메인 이미지 규칙을 어긴 안만: rule_break, fallback
# 목록 순서 = 화면에 보일 우선순위
MEDIA_VARIABLE_STAGE_KIND = "main_image"   # 2·3단계(프롬프트 → 매체 제작)가 이어받을 수 있는 변수 종류
# 판정 값: 2·3단계로 진행 / 메인 이미지 변수가 아님 / 메인 이미지 변수지만 B안이 없음 (뒤 둘은 골라도 확정만 막음)
MEDIA_VARIABLE_PASS = "✅ 이미지로 진행"
MEDIA_VARIABLE_NOT_IMAGE = "⚠️ 이미지로 해결 불가"
MEDIA_VARIABLE_NO_B = "⚠️ B안 없음"
# 진행할 수 없는 변수를 골랐을 때 오른쪽 경고와 확정 줄 안내 {판정: (경고, 확정 줄 안내)}
MEDIA_VARIABLE_BLOCK_MSG = {
    MEDIA_VARIABLE_NOT_IMAGE: ("지금은 메인 이미지 문제만 해결할 수 있어요. 이 변수의 솔루션 기능은 추후 업데이트 예정이에요.",
                               "기능 업데이트 예정 · 지금은 메인 이미지 변수만 확정할 수 있어요"),
    MEDIA_VARIABLE_NO_B: ("이 변수로 만들 메인 이미지 B안이 없어요. B안이 있는 메인 이미지 변수를 골라 주세요.",
                          "이 변수로 만들 B안이 없어요 · B안이 있는 메인 이미지 변수를 골라 주세요"),
}
# 판정 배지 색 (Streamlit 마크다운 배지 :색-badge[...])
MEDIA_VARIABLE_VERDICT_BADGE = {MEDIA_VARIABLE_PASS: "green", MEDIA_VARIABLE_NOT_IMAGE: "orange", MEDIA_VARIABLE_NO_B: "orange"}
MEDIA_VARIABLE_SHOW = 3   # 변수 블럭을 보여 줄 수 (가설·후보 목록이 바뀌어도 이 수만큼만)
MEDIA_VARIABLE_VAR_KEY = "media-variable-var"       # 사용자가 블럭에서 고른 변수 이름 (session_state)
MEDIA_VARIABLE_PICK_KEY = "media-variable-pick"     # B안 체크박스 (st.checkbox) key 앞부분 (뒤에 변수 번호-B안 번호)
MEDIA_VARIABLE_LEAVE_KEY = "media-variable-need-confirm"   # ①을 떠나려다 막혔을 때 경고창에 보일 이유 (session_state)


def media_variable_saved(fresh: bool = False) -> dict:
    """2번 가설 탭이 저장한 가설 {"text", "if", "because", "then", "problem"} (저장 전이면 빈 dict).
    새 모양("selected" 칸)을 먼저 읽고, 없으면 예전 평평한 키(text, if_text …)를 읽습니다.
    fresh면 이번 접속에 기억해 둔 값 대신 Supabase에서 다시 읽습니다 ('가설 불러오기' 버튼)."""
    saved = store_get("hypothesis", fresh=fresh)
    if not isinstance(saved, dict):
        return {}
    sel = saved.get("selected") if isinstance(saved.get("selected"), dict) else {}
    text = str(sel.get("sentence") or saved.get("text") or saved.get("hypothesis") or "").strip()
    if not text:
        return {}
    problem = sel.get("problem") if isinstance(sel.get("problem"), dict) else \
        {k: saved.get(f) for k, f in (("title", "problem_title"), ("type", "type"), ("target", "target"),
                                      ("metric", "metric")) if saved.get(f)}
    return {"text": text, "problem": problem,
            **{k: str(sel.get(k) or saved.get(f"{k}_text") or "").strip() for k in ("if", "because", "then")}}


def media_variable_loaded() -> dict:
    """'가설 불러오기'로 읽어 둔 가설 (아직 안 불렀거나 2번 탭 저장 전이면 빈 dict)."""
    return st.session_state.get(MEDIA_VARIABLE_HYPO_KEY) or {}


def media_variable_hypothesis() -> str:
    """이 탭에서 쓸 가설 문장: 불러온 가설 → (아직 안 불렀으면) 2번 탭이 저장한 가설 → 빈 문자열."""
    return (media_variable_loaded() or media_variable_saved()).get("text", "")


def media_variable_load() -> None:
    """2번 탭 가설을 Supabase에서 다시 읽고, 가설 문장이 바뀌었으면 후보 묶음을 새로 만듭니다 (같은 가설이면 AI를 다시 부르지 않음)."""
    hypo = media_variable_saved(fresh=True)
    st.session_state[MEDIA_VARIABLE_HYPO_KEY] = hypo
    if not hypo:
        st.session_state.pop(MEDIA_VARIABLE_GEN_KEY, None)
        return
    gen = st.session_state.get(MEDIA_VARIABLE_GEN_KEY) or {}
    # 같은 가설이라도 AI 후보에 짧은 If·Because(short)가 없으면(이 칸이 생기기 전에 만든 후보) 다시 만듦
    if gen.get("text") == hypo["text"] and ((gen.get("set") or {}).get("short") or gen.get("source") == MEDIA_VARIABLE_AI_RULE_SOURCE):
        return
    listing = media_variable_report_sqp().get("listing")
    cset, source, error = media_variable_generate(hypo, listing if isinstance(listing, dict) else {})
    st.session_state[MEDIA_VARIABLE_GEN_KEY] = {"text": hypo["text"], "set": cset, "source": source, "error": error}


def media_variable_candidate_set() -> dict:
    """불러온 가설의 후보 묶음 (아직 안 불렀으면 빈 dict)."""
    gen = st.session_state.get(MEDIA_VARIABLE_GEN_KEY) or {}
    return gen.get("set") or {} if gen.get("text") == media_variable_loaded().get("text") else {}


def media_variable_uses_sqp(hypo: dict) -> bool:
    """가설이 1번 리포트 검색어 클릭 분석(sqp)의 KPI를 말하는지 → 그때만 지금·목표 KPI 숫자를 sqp에서 가져옵니다.
    고른 문제의 검색어가 sqp 검색어와 같거나, 가설 문장에 그 KPI 이름이 들어 있으면 맞다고 봅니다."""
    query = media_variable_report_sqp().get("query")
    return bool(query and (hypo.get("problem") or {}).get("query") == query) or \
        any(k in hypo.get("text", "") for k in MEDIA_VARIABLE_HYPO_KPIS)


def media_variable_kpi_name(text: str) -> str:
    """화면 표시용: 'A ÷ B' KPI 표현을 쉬운 이름(노출 대비 클릭률)으로 바꿉니다."""
    return text.replace(MEDIA_VARIABLE_KPI_RAW, MEDIA_VARIABLE_KPI)


def media_variable_split(text: str) -> list[str] | None:
    """가설 문장을 If / Because / Then 세 덩어리로 나눕니다. 나눌 수 없으면 None.
    - "만약 ~바꾸면, ~보여서, ~것이다."처럼 쉼표가 두 번 이상이면: 첫 덩어리 / 가운데 / 마지막
    - "만약 ~적용한다면, ~ 때문에 ~것이다."처럼 쉼표가 한 번이면: 뒤쪽을 마지막 "때문에"에서 나눔"""
    pieces = [p.strip() for p in text.split(", ") if p.strip()]
    if len(pieces) >= 3:
        return [pieces[0] + ",", ", ".join(pieces[1:-1]) + ",", pieces[-1]]
    if len(pieces) == 2 and " 때문에 " in pieces[1]:
        because, then = pieces[1].rsplit(" 때문에 ", 1)
        return [pieces[0] + ",", because + " 때문에", then]
    return None


def media_variable_short_if(text: str, target: str) -> tuple[str, str]:
    """If를 짧게: (대상, 바꿀 것). 문장 앞의 '{대상}에 '는 대상 칩으로 빼고, 끝의 '~을 적용한다면'·'~바꾸면' 같은
    문장 틀만 걷어 냅니다. 대상이 문장 앞에 없으면 대상은 빈 문자열."""
    text = text.removeprefix("만약").strip().rstrip(",").strip()
    # 2번 탭은 문장 안의 ", "를 "·"로 바꿔 저장하므로(hypothesis_scenario.py) 두 모양 모두 찾음
    for name in dict.fromkeys([target, target.replace(", ", "·")] if target else []):
        josa = next((j for j in ("에게 ", "에 ") if text.startswith(name + j)), None)
        if josa:
            target, text = name, text[len(name + josa):]
            break
    else:
        target = ""
    for pattern, repl in MEDIA_VARIABLE_IF_TRIMS:
        text = re.sub(pattern, repl, text)
    return target, text


def media_variable_short_then(text: str) -> str:
    """Then을 짧게, 굵은 글씨(markdown)로: '전환율이 2.4%에서 2.9%로 21% 오를 것이다' → '**전환율** **2.4% → 2.9% (21%↑)**'.
    지표 이름과 숫자를 따로 굵게 둠 → 좁은 두 칸 화면에서 media_style.css가 그 사이에서만 줄을 나눔.
    이 모양이 아니면 끝의 마침표만 빼고 그대로 둡니다 (뜻을 바꾸지 않도록 정해진 모양만 줄임)."""
    text = text.strip().rstrip(".")
    m = re.fullmatch(MEDIA_VARIABLE_THEN_PATTERN, text)
    if not m:
        return f"**{text}**"
    arrow = "↑" if m["verb"] in MEDIA_VARIABLE_THEN_UP else "↓"
    goal = m["b"] + (" 이상" if m["more"] else "")
    return f"**{m['metric']}** **{m['a']} → {goal} " + (f"({m['pct']}{arrow})" if m["pct"] else arrow) + "**"


def media_variable_parts(hypo: dict) -> list[str] | None:
    """가설의 [If, Because, Then] (화면용 KPI 이름). 2번 탭이 나눠 저장한 값이 있으면 그대로, 없으면 문장을 나눕니다.
    나눌 수 없는 문장이면 None."""
    if hypo.get("if") and hypo.get("because") and hypo.get("then"):
        return [media_variable_kpi_name(p) for p in (hypo["if"], hypo["because"], hypo["then"])]
    return media_variable_split(media_variable_kpi_name(hypo["text"]))


def media_variable_goal_text(plan: dict, hypo: dict) -> str:
    """요약 칩의 목표 KPI 한 줄. 리포트 숫자가 있으면 그 숫자, 없으면 가설의 Then을 짧게 (숫자를 화살표로)."""
    parts = media_variable_parts(hypo)
    if media_variable_has_goal(plan) or not parts:
        return media_variable_kpi_text(plan)
    return media_variable_short_then(parts[2])


def media_variable_hypo_tip(hypo: dict) -> str:
    """요약 칩 ⓘ에 보일 2번 탭 가설 (If / Because / Then 원문, 나눌 수 없으면 문장 그대로)."""
    parts = media_variable_parts(hypo)
    body = ("\n".join(f"- **{name}**: {p.strip().rstrip(',')}" for name, p in zip(("If", "Because", "Then"), parts))
            if parts else media_variable_kpi_name(hypo["text"]))
    return f"**2번 가설 탭에서 불러온 가설**\n\n{body}"


def media_variable_is_stale(hypo: dict) -> bool:
    """불러온 가설이 2번 탭에 지금 저장된 가설과 다른지 (2번 탭에서 '선택하기'로 다른 가설을 고른 뒤 다시 불러오지 않음).
    이번 접속에 기억해 둔 값으로만 비교합니다 (다른 사람이 저장한 값은 '다시 불러오기'를 눌러야 반영)."""
    saved = media_variable_saved()
    return bool(saved) and saved != hypo

def media_variable_b_options(v: dict) -> tuple[list[dict], list[dict]]:
    """변수 하나의 (B로 쓸 수 있는 안, 메인 이미지 규칙을 어겨 못 쓰는 안)."""
    ok, broken = [], []
    for o in v.get("b_options") or []:
        if isinstance(o, dict) and o.get("label"):
            if o.get("rule_break"):
                broken.append(o)
            elif o.get("b"):
                ok.append(o)
    return ok, broken


def media_variable_judge(v: dict) -> tuple[bool, str, str]:
    """변수 하나의 (2·3단계로 진행할 수 있는지, 판정, 이유). 고르는 것은 막지 않고, 진행할 수 없으면 확정만 막습니다.
    보는 순서: 2·3단계가 이어받을 수 있는 종류(메인 이미지)인지 → 메인 이미지 규칙 안에서 만들 B안이 있는지.
    가설의 If와 맞는지(if_match)는 진행 조건이 아니라 이유 칸에 참고로만 적습니다."""
    off_if = "" if v.get("if_match") else " · 가설의 If와 다름"
    if v.get("kind") != MEDIA_VARIABLE_STAGE_KIND:
        return False, MEDIA_VARIABLE_NOT_IMAGE, "지금은 메인 이미지 문제만 해결 가능" + off_if
    ok, broken = media_variable_b_options(v)
    if not ok:   # AI는 가설의 If와 맞는 변수에만 B안을 만듦 (media_variable_ai.py)
        why = "가설의 If와 달라 B안을 만들지 않음" if off_if else "메인 이미지 규칙 안에서 만들 B안이 없음"
        return False, MEDIA_VARIABLE_NO_B, why + (f" (규칙 위반 {len(broken)}개)" if broken else "")
    return True, MEDIA_VARIABLE_PASS, (f"메인 이미지 · 규칙 안 B안 {len(ok)}개" + (f" (규칙 위반 {len(broken)}개 제외)" if broken else "")
                                       + off_if)


def media_variable_label(c: dict) -> str:
    """B안 체크박스에 보일 이름 (label이 없으면 이름)."""
    return c.get("label") or c.get("name", "")


def media_variable_candidates() -> dict:
    """지금 가설의 변수 판정 결과 {"set", "rows", "hidden", "variable", "options", "broken", "picked"}.
    rows = 블럭으로 보일 변수(진행 가능 → 진행 불가 순으로 MEDIA_VARIABLE_SHOW개, 변수마다 "ok"·"verdict"·"why"),
    hidden = 블럭에 못 들어간 변수, variable = 사용자가 블럭에서 고른 변수(어느 블럭이든),
    options / broken = 그 변수의 B로 쓸 수 있는 안 / 규칙 위반으로 못 쓰는 안,
    picked = 2단계로 확정해 둔 B안 (+ "variable" 칸). 체크 = 확정이라 확정 전이거나 고른 변수가 확정한 변수와 다르면 빈 dict.
    variable은 블럭에서 고른 변수 → 2단계로 확정해 둔 변수 → 진행 가능한 첫 줄 → 첫 줄 순으로 고릅니다. 후보가 없으면 variable은 빈 dict."""
    cset = media_variable_candidate_set()
    good, bad = [], []
    for v in cset.get("variables", []):
        if not isinstance(v, dict) or not v.get("name"):
            continue
        ok, verdict, why = media_variable_judge(v)
        (good if ok else bad).append({**v, "ok": ok, "verdict": verdict, "why": why})
    rows, hidden = (good + bad)[:MEDIA_VARIABLE_SHOW], (good + bad)[MEDIA_VARIABLE_SHOW:]
    saved = media_handoff_plan()
    saved = {} if saved["sample"] else saved
    chosen = st.session_state.get(MEDIA_VARIABLE_VAR_KEY)
    variable = (next((v for v in rows if v["name"] == chosen), None)
                or next((v for v in rows if v["name"] == saved.get("variable")), None)
                or next((v for v in rows if v["ok"]), None)
                or (rows[0] if rows else {}))
    options, broken = media_variable_b_options(variable) if variable else ([], [])
    if not variable.get("ok"):   # 진행할 수 없는 변수: B안을 고르지 않음 (규칙 위반 안은 ⓘ에 그대로)
        options = []
    # 체크 = 확정: 2단계로 확정해 둔 변수·B안만 체크된 것으로 봄 (안 골랐으면 아무것도 체크하지 않음)
    picked = next((o for o in options if saved.get("variable") == variable["name"] and o["b"] == saved.get("b")), {})
    if picked:
        picked = {**picked, "variable": variable["name"]}
    return {"set": cset, "rows": rows, "hidden": hidden, "variable": variable,
            "options": options, "broken": broken, "picked": picked}


def media_variable_report_sqp() -> dict:
    """1번 리포트의 검색어 클릭 분석(store "report"의 sqp). 없으면 빈 dict."""
    report = store_get("report")
    sqp = report.get("sqp") if isinstance(report, dict) else None
    return sqp if isinstance(sqp, dict) else {}


def media_variable_plan() -> tuple[dict, str, list[str]]:
    """(A/B 설계 plan, 가격 문구, 기본값을 쓴 항목 이름 목록).
    plan은 media_handoff.py의 기본값(MEDIA_HANDOFF_PLAN)에서 시작해, 사용자가 고른 후보(독립 변수·B)와
    1번 리포트 값(검색어·A·KPI)으로 덮어씁니다.
    가설을 불러왔는데 고른 변수가 진행할 수 없는 변수면 variable은 그 변수 이름, b는 빈 문자열입니다 (확정이 막힘).
    가설이 리포트 검색어 클릭 분석의 KPI가 아니면 KPI 이름은 후보 묶음·문제의 지표로, 지금·목표 숫자는 None입니다."""
    sqp = media_variable_report_sqp()
    listing = sqp.get("listing") if isinstance(sqp.get("listing"), dict) else {}
    plan, defaults = dict(MEDIA_HANDOFF_PLAN), []
    hypo = media_variable_loaded()
    cands = media_variable_candidates()
    picked = cands["picked"]
    if picked:
        plan["variable"] = picked.get("variable") or plan["variable"]
        plan["b"] = picked["b"]
        plan["b_ref"] = picked.get("ref_prompt", "")   # B안의 영어 레퍼런스 프롬프트 (2단계가 프롬프트 B로 씀)
    elif hypo:
        plan.update(variable=cands["variable"].get("name", ""), b="", b_ref="")
    sqp_kpi = not hypo or media_variable_uses_sqp(hypo)
    if not sqp_kpi:
        plan.update(kpi=cands["set"].get("kpi") or (hypo.get("problem") or {}).get("metric") or "가설의 Then 지표",
                    kpi_now=None, kpi_goal=None)
    # (plan 키, 리포트 값, 맞는 자료형, 화면에 보일 이름)
    for key, value, kind, label in [
        ("query", sqp.get("query"), str, "검색어"),
        ("a", listing.get("main_image"), str, "A · 대조군"),
        *([("kpi_now", sqp.get("ratio"), (int, float), "지금 KPI"),
           ("kpi_goal", sqp.get("kpi_goal"), (int, float), "목표 KPI")] if sqp_kpi else []),
    ]:
        if isinstance(value, kind) and value != "":
            plan[key] = value
        else:
            defaults.append(label)
    if isinstance(listing.get("price"), (int, float)):
        price = f"€{listing['price']:.2f}"
    else:
        price = "현재 가격"
        defaults.append("가격")
    return plan, price, defaults


def media_variable_confirm_state(plan: dict) -> str:
    """2단계로 확정해 둔 값과 plan 비교: "none"(확정 전) / "same"(확정됨) / "changed"(확정 뒤 고른 값이 바뀜).
    이번 접속에서 아직 가설을 불러오지 않았으면 고르는 중인 값이 없으므로 확정한 값 그대로("same")로 봅니다."""
    saved = media_handoff_plan()
    if saved["sample"]:
        return "none"
    if not media_variable_candidate_set():
        return "same"
    return "same" if all(saved.get(k) == v for k, v in plan.items()) else "changed"


def media_variable_confirmed_plan() -> tuple[dict | None, str]:
    """(확정해 둔 A/B 설계 plan, 상태). 하위 탭 ②부터는 ①에서 고르는 중인 값이 아니라 이 값을 기준으로 보여 줍니다.
    확정 전이면 plan은 None. 상태는 지금 ①에서 고른 값과 비교한 media_variable_confirm_state()."""
    saved = media_handoff_plan()
    if saved["sample"]:
        return None, "none"
    current, _, _ = media_variable_plan()
    return {k: v for k, v in saved.items() if k != "sample"}, media_variable_confirm_state(current)


def media_variable_go_step() -> None:
    """'① 으로 가서 확정하기' 버튼 콜백. 하위 탭을 ①로 바꿉니다 (위젯이 그려지기 전에 실행됨)."""
    st.session_state["media-step"] = MEDIA_VARIABLE_TAB_LABEL


def media_variable_has_goal(plan: dict) -> bool:
    """plan에 지금·목표 KPI 숫자가 있는지 (리포트 검색어 클릭 분석 KPI 가설일 때만 있음)."""
    return all(isinstance(plan.get(k), (int, float)) for k in ("kpi_now", "kpi_goal"))


def media_variable_kpi_text(plan: dict) -> str:
    """요약 칩·목표 KPI 칩에 보일 KPI 한 줄. 숫자가 없으면 지표 이름과 '목표는 가설의 Then'만 보여 줍니다."""
    if media_variable_has_goal(plan):
        return f"{plan['kpi']} {plan['kpi_now']:g}배 → **{plan['kpi_goal']:g}배 이상**"
    return f"{plan['kpi']} · 목표는 가설의 Then"


def media_variable_kpi_chip() -> None:
    """하위 탭 바 오른쪽 빈자리에 띄우는 목표 KPI 칩 (하위 탭 ②~④, media_page.py에서 부름).
    단계를 옮겨 다녀도 목표값이 계속 보이게 합니다. 검색어·점유율·출처는 칩의 ⓘ 툴팁에 둡니다 (media_style.css).
    확정한 값이 있으면 그 값(②부터 보이는 값)으로, 없으면 ①에서 고르는 중인 값으로 그립니다."""
    current, _, defaults = media_variable_plan()
    plan = media_variable_confirmed_plan()[0] or current
    sqp = media_variable_report_sqp()
    if media_variable_has_goal(plan):
        tip = [f"이번 A/B 테스트의 목표예요. B안이 {plan['kpi']}을 지금 {plan['kpi_now']:g}배에서 "
               f"{plan['kpi_goal']:g}배 이상으로 올리면 성공이에요.",
               f"**검색어**: {plan['query']}"]
    else:   # 리포트 검색어 클릭 분석 KPI가 아닌 가설: 목표 숫자는 가설의 Then에 있음
        tip = [f"이번 A/B 테스트의 목표예요. B안이 {plan['kpi']}을 가설의 Then만큼 올리면 성공이에요.",
               f"**가설**: {media_variable_hypothesis()}"]
    if media_variable_has_goal(plan) and sqp.get("imp_share") is not None and sqp.get("click_share") is not None:
        tip.append(f"**지금**: 노출 점유율 {sqp['imp_share']}% · 클릭 점유율 {sqp['click_share']}% "
                   f"→ {plan['kpi']} {plan['kpi_now']:g}배")
    if sqp.get("source"):   # 리포트의 출처 문장은 여러 지표의 실제/가상 구분이라 길어서 항목별로 나눠 보여 줌
        tip.append("**데이터 출처** (1번 리포트)\n"
                   + "\n".join(f"- {s.strip()}" for s in str(sqp["source"]).split(" / ") if s.strip()))
    if sqp.get("period"):
        tip.append(f"**기간**: {sqp['period']}")
    if defaults:
        tip.append(f"1번 리포트 값이 없어 기본값으로 보여 줘요: {', '.join(defaults)}")
    with st.container(key="media-kpi-chip"):
        # 앞 배지로 칩이 무엇인지 알려 줌 (하위 탭 ① 요약 칩의 :green-badge[KPI]와 같은 색)
        label = f" · :gray[{MEDIA_VARIABLE_SQP_LABEL}]" if media_variable_has_goal(plan) else ""
        st.markdown(f":green-badge[🎯 A/B 목표 KPI] {media_variable_kpi_text(plan)}{label}", help="\n\n".join(tip))


def media_variable_summary_chip(plan: dict, cands: dict, hypo: dict):
    """하위 탭 ①의 요약 칩 '[독립 변수] … · [🎯 목표 KPI] …' (ⓘ에 2번 탭 가설).
    ②~④의 목표 KPI 칩과 같은 모양·자리 (넓은 화면은 하위 탭 바와 같은 줄 오른쪽 끝, media_style.css).
    칩은 탭 패널 기준으로 띄우므로 나타나는 애니메이션 상자(media-hypo-box) 밖에서 부릅니다."""
    picked, chosen = cands["picked"], cands["variable"]
    variable = f"{plan['variable']} ({media_variable_label(picked)})" if picked else (plan["variable"] or "없음")
    if chosen and not chosen["ok"]:   # 고른 변수가 진행할 수 없는 변수: 칩에도 표시 (이유는 아래 오른쪽 경고)
        variable += " :orange-badge[⚠️ 진행 불가]"
    with st.container(key="media-hypo-summary"):
        st.markdown(f":violet-badge[독립 변수] {variable} · "
                    f":green-badge[🎯 목표 KPI] {media_variable_goal_text(plan, hypo)}",
                    help=media_variable_hypo_tip(hypo))


def media_variable_hypothesis_step(hypo: dict):
    """2번 탭 가설이 바뀌었을 때 경고 + 규칙 후보 안내 (media_variable_step()의 윗부분)."""
    if media_variable_is_stale(hypo):
        st.warning("2번 가설 탭에서 고른 가설이 바뀌었어요. 오른쪽 위 '다시 불러오기'를 눌러야 새 가설로 변수를 도출해요.",
                   icon="🔄")
    gen = st.session_state.get(MEDIA_VARIABLE_GEN_KEY) or {}
    if gen.get("source") == MEDIA_VARIABLE_AI_RULE_SOURCE:   # AI를 못 써서 규칙으로 만든 후보: 이유는 ⓘ에
        st.markdown(":gray-badge[규칙으로 만든 후보] AI를 쓰지 못해 가설의 If를 그대로 후보 변수와 B안으로 썼어요",
                    help=f"**이유**: {gen.get('error') or '-'}\n\n"
                         "같은 가설은 다시 만들지 않아요. 키를 넣은 뒤 새로고침하고 다시 불러오면 AI 후보로 바뀌어요.")


def _media_variable_select(name: str) -> None:
    """변수 블럭을 누를 때 콜백. 어떤 블럭이든 그 변수로 바꿉니다 (진행할 수 없는 변수는 오른쪽 경고 + 확정만 막음).
    고른 블럭을 다시 눌러도 선택이 풀리지 않습니다."""
    st.session_state[MEDIA_VARIABLE_VAR_KEY] = name


def media_variable_cards(rows: list[dict], variable: dict) -> None:
    """후보 변수 블럭 목록: 블럭 하나 = 변수 하나 (윗줄 '라디오 표시 + 이름 + 판정 배지', 아랫줄 이유).
    블럭 전체를 덮는 투명 버튼(key media-variable-choose-<번호>)을 눌러 고르고,
    고른 블럭은 key가 media-variable-card-on-<번호>로 바뀌어 media_style.css가 테두리를 진하게 그립니다."""
    # key="media-variable-candidates": 블럭 사이 간격을 media_style.css에서 정함
    with st.container(key="media-variable-candidates"):
        for i, v in enumerate(rows):
            on = v is variable
            with st.container(key=f"media-variable-card-{'on-' if on else ''}{i}"):
                mark = ":material/radio_button_checked:" if on else ":material/radio_button_unchecked:"
                st.markdown(f"{mark} **{v['name']}** "
                            f":{MEDIA_VARIABLE_VERDICT_BADGE[v['verdict']]}-badge[{v['verdict']}]")
                st.caption(v["why"])
                st.button(f"{v['name']} 고르기", key=f"media-variable-choose-{i}",
                          on_click=_media_variable_select, args=(v["name"],))


def media_variable_derive_step(plan: dict, price: str, defaults: list[str], cands: dict):
    """후보 변수 선택(블럭에서 변수 하나 고르기) → 고른 변수를 A/B로 나누기 (media_variable_step()의 아랫부분).
    선정 표의 값은 plan에서 가져옵니다."""
    rows, variable, options, picked = cands["rows"], cands["variable"], cands["options"], cands["picked"]
    # 왼쪽(변수 블럭)을 조금 넓혀 이유가 한 줄에 들어가게 함 → 오른쪽(B안 고르기 블럭 + A·B 표)과 높이를 맞춤
    c1, c2 = st.columns([1.2, 1], gap="medium")
    with c1:
        # 판정 기준은 제목 옆 ⓘ에 마우스를 올리면 보임 (설명 줄이 빠져 오른쪽 선정 표와 위쪽 끝이 맞음)
        hidden = cands["hidden"]
        st.markdown("**후보 변수 선택**", help=(
            "가설에서 바꿀 수 있는 변수를 블럭 하나에 하나씩 보여 줘요. 어느 블럭이든 눌러 A/B로 실험할 변수를 골라요.\n\n"
            f"**후보를 만든 곳**: {(st.session_state.get(MEDIA_VARIABLE_GEN_KEY) or {}).get('source') or '-'} "
            "(판정은 아래 기준으로 코드가 다시 계산)\n\n"
            f"**{MEDIA_VARIABLE_PASS}**: 2·3단계가 이어받을 수 있는 메인 이미지 변수이고, "
            "아마존 메인 이미지 규칙 안에서 Manage Your Experiments로 돌릴 B안이 있어요.\n\n"
            f"**{MEDIA_VARIABLE_NOT_IMAGE} · {MEDIA_VARIABLE_NO_B}**: 골라도 되지만 다음 단계로 확정할 수는 없어요 "
            "(지금은 메인 이미지 문제만 해결 가능, 기능 업데이트 예정). 가설의 If와 다른 변수는 블럭 아랫줄 이유에 적어요."
            + ("\n\n**화면에 안 보이는 변수**: " + ", ".join(f"{v['name']} ({v['verdict']})" for v in hidden)
               if hidden else "")))
        if rows:
            media_variable_cards(rows, variable)
        else:
            st.caption("이 가설의 후보 목록이 아직 없어요.")
    with c2:
        # 표에는 A·B만 (스크롤 없이 한 화면에 보이도록, 변수 표와 높이도 맞춤).
        # 독립·종속 변수는 위 요약 칩에 있고, 통제 변수·안전장치·B로 못 쓰는 안·가설에 딸린 참고 설명(note)은
        # 제목 옆 ⓘ에서 보임 (화면에서만 빠지고 2단계로 넘기는 plan에는 그대로 있음)
        note = cands["set"].get("note")
        broken = "\n".join(f"- {o['label']}: {o['rule_break']} → {o.get('fallback') or '서브 이미지'}"
                           for o in cands["broken"])
        # 제목 줄: 제목 옆에 B안 고르기 블럭(옵션 체크박스)을 나란히 (진행할 수 있는 변수일 때만)
        # key="media-variable-picked-head": media_style.css가 제목과 블럭 사이 간격을 정함
        head = st.container(horizontal=True, vertical_alignment="center", key="media-variable-picked-head")
        head.markdown("**선정한 단일 변수**", width="content", help=(
            "왼쪽 블럭에서 고른 변수를 A(지금 그대로)와 B(바꾼 안)로 나눠요.\n\n"
            "**A는 고정**: 지금 아마존에 올라가 있는 메인 이미지(1번 리포트 값)라 바꾸지 않아요. "
            "지금보다 나아지는지 비교해야 가설(KPI가 지금 값에서 목표로 오르는지)을 확인할 수 있어서, "
            "A는 그대로 두고 B만 제목 옆 체크박스로 골라요.\n\n"
            f"**통제 변수 (고정)**: 같은 제품·색상, 흰 배경, 같은 조명과 보정, 제품 85% 이상 · 제목, 가격 {price}, 쿠폰 없음, "
            "불릿, A+ 콘텐츠, 서브 이미지, 광고 입찰\n\n"
            + (f"**종속 변수 (메인 KPI)**: {plan['kpi']} = {MEDIA_VARIABLE_KPI_RAW} (시장 대비 CTR)\n\n"
               if media_variable_has_goal(plan) else f"**종속 변수 (메인 KPI)**: {plan['kpi']} (목표는 가설의 Then)\n\n")
            + f"**안전장치**: CVR(단위 세션 비율)이 A보다 {plan['cvr_tolerance']:g}%p 넘게 떨어지면 B 실패"
            + (f"\n\n**B로 못 쓰는 안 (메인 이미지 규칙 위반)**\n{broken}" if broken else "")
            + (f"\n\n{note}" if note else "")))
        if not variable:   # 후보가 없음 (왼쪽에 안내, 확정 줄에서 확정을 막음)
            return
        if not variable["ok"]:   # 진행할 수 없는 변수: 고른 것은 그대로 두고 경고만 (확정 줄에서 확정을 막음)
            st.warning(f"**{variable['name']}** · {MEDIA_VARIABLE_BLOCK_MSG[variable['verdict']][0]}", icon="⚠️")
            return
        if options:
            with head:
                media_variable_b_box(options, picked, rows.index(variable), plan)
        # key="media-variable-picked": media_style.css가 구분 칸('A · 대조군')을 한 줄로 유지
        with st.container(key="media-variable-picked"):
            st.markdown("| 구분 | 내용 |\n| --- | --- |\n"
                        f"| **A · 대조군** | {plan['a']} (현재 사진 · 고정) |\n"
                        f"| **B · 실험군** | {plan['b'] or '제목 옆 옵션을 체크해 골라요'} |")
        if defaults:   # 리포트 탭을 아직 안 열었거나 리포트 칸 이름이 바뀌었을 때 바로 알아차리도록
            st.caption(f"1번 리포트 값이 없어 기본값으로 보여 줘요: {', '.join(defaults)}")


def media_variable_b_box(options: list[dict], picked: dict, index: int, plan: dict) -> None:
    """B안 고르기 블럭: 한 블럭 안에 '체크박스 + 옵션 N'을 가로로 나란히 (하나만 고름). 체크 = 확정, 체크를 풀면 확정 취소.
    화면 글자는 B안 이름과 상관없이 항상 '옵션 1', '옵션 2' …이고, 고른 B안 내용은 아래 A·B 표의 B 줄에서 보입니다.
    체크 상태는 매번 그리기 전에 2단계로 확정해 둔 값(picked)으로 맞춥니다. 확정한 뒤 리포트 값이 바뀌면(state "changed") 체크를 비워
    다시 체크하면 새 값으로 확정되게 합니다."""
    chosen = media_variable_label(picked) if picked and media_variable_confirm_state(plan) == "same" else None
    # key="media-variable-b-box": media_style.css가 변수 블럭과 같은 카드 모양 + 옵션 사이 구분선을 그림
    with st.container(horizontal=True, vertical_alignment="center", key="media-variable-b-box"):
        for i, o in enumerate(options):
            key = f"{MEDIA_VARIABLE_PICK_KEY}-{index}-{i}"
            st.session_state[key] = media_variable_label(o) == chosen   # 위젯을 그리기 전이라 값을 바꿀 수 있음 (value 인자는 쓰지 않음)
            st.checkbox(f"옵션 {i + 1}", key=key, on_change=_media_variable_pick_b, args=(key, plan, o), width="content")


def _media_variable_pick_b(key: str, plan: dict, option: dict) -> None:
    """B안 체크박스 콜백. 체크하면 그 B안으로 A/B 설계를 2단계로 넘기고(확정), 체크를 풀면 넘긴 값을 지웁니다(확정 취소).
    다음 화면에서 토스트를 띄웁니다."""
    if st.session_state.get(key):
        media_handoff_set_plan({**plan, "b": option["b"], "b_ref": option.get("ref_prompt", "")})
        st.session_state["media-variable-confirmed-toast"] = "set"
    else:
        media_handoff_clear_plan()
        st.session_state["media-variable-confirmed-toast"] = "clear"


def media_variable_confirm_step(plan: dict, variable: dict):
    """선정 표 아래 상태 줄 (확정 버튼은 없음, B안 옵션을 체크하면 확정). 진행할 수 없는 변수나 후보가 없으면 '다음 단계 진행 불가'."""
    toast = st.session_state.pop("media-variable-confirmed-toast", None)
    if toast == "set":
        st.toast("단일 변수를 확정했어요. 다음 단계들이 이 값을 받아요", icon="✅")
    elif toast == "clear":
        st.toast("확정을 취소했어요. 옵션을 다시 체크해야 다음 단계로 넘어가요", icon="↩️")
    state = media_variable_confirm_state(plan)
    if not variable.get("ok"):
        reason = (MEDIA_VARIABLE_BLOCK_MSG[variable["verdict"]][1] if variable.get("verdict") in MEDIA_VARIABLE_BLOCK_MSG
                  else "후보 변수가 없어요 · 2번 탭에서 다른 가설을 고르고 다시 불러와 주세요")
        note = f":orange-badge[🚫 다음 단계 진행 불가] {reason}"
    elif state == "same":
        note = ":green-badge[✅ 확정됨] 다음 단계(A/B 소재 준비부터)가 이 값을 받아요 · 체크를 풀면 확정이 취소돼요"
    elif state == "changed" and media_handoff_plan().get("variable") == variable["name"]:   # 같은 변수인데 리포트 값 등이 바뀜
        note = ":orange-badge[다시 확정 필요] 확정한 뒤 리포트 값이 바뀌었어요. 옵션을 다시 체크하면 새 값으로 확정돼요"
    else:
        note = "옵션을 체크하면 확정되고 다음 단계(A/B 소재 준비부터)로 넘어가요"
    with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center",
                      key="media-variable-confirm-row"):
        st.markdown(note)


def media_variable_can_leave(warn: bool = True) -> bool:
    """하위 탭 ①을 떠날 때('다음' 버튼, 다른 하위 탭 클릭) 먼저 부르는 확인 (media_page.py).
    ①에서 고른 값이 확정한 값과 같을 때(state "same")만 True. 아니면 False이고, warn이면 경고창 이유를 남깁니다
    (다음 화면에서 media_variable_leave_notice()가 띄움)."""
    plan, _, _ = media_variable_plan()
    state = media_variable_confirm_state(plan)
    if state == "same":
        return True
    if not warn:
        return False
    variable = media_variable_candidates()["variable"]
    if variable and not variable["ok"]:
        reason = ("이 변수는 지금 이미지로 해결할 수 없어 다음 단계로 갈 수 없어요 (기능 업데이트 예정). "
                  "진행 가능한(✅) 변수를 골라 옵션을 체크해 주세요.")
    elif state == "changed":
        reason = "고른 변수·옵션이 확정한 값과 달라요. 옵션을 체크해 지금 값으로 확정해 주세요."
    else:
        reason = ("아직 확정한 단일 변수가 없어요. " + ("B안 옵션을 체크하면 확정돼요." if media_variable_loaded()
                                                    else "오른쪽 위 '가설 불러오기'를 누르고 B안 옵션을 체크해 주세요."))
    st.session_state[MEDIA_VARIABLE_LEAVE_KEY] = reason
    return False


@st.dialog("단일 변수를 확정해 주세요")
def _media_variable_need_confirm_dialog(reason: str) -> None:
    """①을 떠나려다 막혔을 때 가운데에 뜨는 경고창."""
    st.markdown(reason)
    st.caption("체크한 옵션이 2단계로 넘어가는 B안이에요. 체크를 풀면 확정이 취소돼요.")
    if st.button("확인", key="media-btn-variable-need-confirm-ok", type="primary"):
        st.rerun()


def media_variable_leave_notice() -> None:
    """①을 떠나려다 막혔으면(media_variable_can_leave가 이유를 남김) 가운데 경고창을 띄웁니다. media_render()가 매번 부릅니다."""
    if reason := st.session_state.pop(MEDIA_VARIABLE_LEAVE_KEY, None):
        _media_variable_need_confirm_dialog(reason)


def media_variable_locked_step() -> None:
    """①에서 확정 전에 ②~④ 하위 탭을 직접 눌렀을 때 그 탭 내용 대신 보이는 잠금 안내."""
    with st.container(border=True, key="media-variable-locked"):
        st.markdown("**🔒 단일 변수를 먼저 확정해 주세요**")
        st.caption("① 가설에서 변수 도출에서 B안 옵션을 체크하면 확정되고, 이 단계부터 볼 수 있어요.")
        st.button(f"← {MEDIA_VARIABLE_TAB_LABEL}로 가기", key="media-btn-variable-locked-go", type="primary",
                  on_click=media_variable_go_step)


def _media_variable_start_load() -> None:
    """'가설 불러오기' 버튼 콜백. 다음 화면 그리기에서 스피너를 띄우고 불러오도록 표시만 해 둡니다 (AI가 오래 걸릴 수 있어서)."""
    st.session_state["media-hypo-loading"] = True


def media_variable_step():
    """하위 탭 '가설에서 변수 도출': 오른쪽 위 '가설 불러오기' 버튼 → 요약 칩(독립 변수·목표 KPI) → 후보 변수 선택·단일 변수 선정.
    반드시 media_render() 안에서 부릅니다."""
    loading = st.session_state.pop("media-hypo-loading", False)
    loaded = loading or st.session_state.get("media-hypo-loaded", False)
    with st.container(horizontal=True, horizontal_alignment="right", key="media-hypo-load-row"):
        st.button("↻ 다시 불러오기" if loaded else "📥 가설 불러오기", key="media-btn-hypo-load",
                  type="secondary" if loaded else "primary", on_click=_media_variable_start_load)

    # 버튼을 누른 직후 한 번만: 2번 탭 가설을 Supabase에서 다시 읽고 후보 묶음을 만듦 (AI를 부르면 몇 초 걸림)
    if loading:
        with st.spinner("2번 가설 탭에서 가설을 불러와 후보 변수를 만드는 중…"):
            media_variable_load()
        st.session_state["media-hypo-loaded"] = True
        if media_variable_loaded():
            st.toast("가설을 불러왔어요", icon="📥")

    hypo = media_variable_loaded()
    if not loaded or not hypo:
        with st.container(border=True, key="media-hypo-empty"):
            if loaded:   # 불러왔지만 2번 탭에 저장된 가설이 없음
                st.markdown("**2번 탭에서 선택한 가설이 없어요**")
                st.caption("2. 가설 수립 탭에서 가설 하나를 '선택하기'로 고른 뒤, 오른쪽 위 '다시 불러오기'를 눌러 주세요.")
            else:
                st.markdown("**아직 불러온 가설이 없어요**")
                st.caption("오른쪽 위 '가설 불러오기'를 누르면 2번 가설 탭의 가설을 가져와 A/B로 바꿀 변수를 도출해요.")
        return

    # key="media-hypo-box": media_style.css의 나타나는 애니메이션(.st-key-media-hypo-box)
    plan, price, defaults = media_variable_plan()
    cands = media_variable_candidates()
    media_variable_summary_chip(plan, cands, hypo)
    with st.container(key="media-hypo-box"):
        media_variable_hypothesis_step(hypo)
        # key="media-hypo-divider": media_style.css가 구분선 위아래 기본 여백(2em)을 줄여 윗줄 바로 아래에 붙임
        with st.container(key="media-hypo-divider"):
            st.divider()
        media_variable_derive_step(plan, price, defaults, cands)
        media_variable_confirm_step(plan, cands["variable"])
