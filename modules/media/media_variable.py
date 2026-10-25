# 3. 매체 제작 > 가설에서 변수 도출
# '가설 불러오기'를 누르면 2번 탭이 저장한 가설(store "hypothesis")을 다시 읽고, 그 가설로 후보 변수 묶음을 만들어
# (AI 또는 규칙, media_variable_ai.py) 사용자가 표에서 A/B로 실험할 변수 하나와 그 변수의 B안을 고릅니다.
# 어떤 가설이 와도 화면이 그려지고, 메인 이미지 변수가 없으면 2·3단계로 넘기는 확정만 막습니다.
# 3번 탭의 하위 탭 ①(가설에서 변수 도출)에서 부릅니다.
# 고른 A/B 설계(plan)는 1번 리포트 값으로 채워 화면에 보여 주고, 사용자가 확정하면 2단계로 넘깁니다 (media_handoff.py).
# 바깥 값을 읽는 곳은 두 함수뿐입니다: 가설 media_variable_saved(), 리포트 media_variable_report_sqp()
import re
from functools import partial

import streamlit as st

from common.common_store import store_get
from modules.media.media_handoff import MEDIA_HANDOFF_PLAN, media_handoff_plan, media_handoff_set_plan
from modules.media.media_variable_ai import MEDIA_VARIABLE_AI_RULE_SOURCE, media_variable_generate

MEDIA_VARIABLE_TAB_LABEL = "가설에서 변수 도출"   # 하위 탭 ① 이름 (media_page.py와 다른 하위 탭의 '① 으로 가서 확정하기' 버튼이 씀)
# '가설 불러오기'로 읽어 둔 값 (session_state). 다시 불러오기 전까지는 2번 탭에서 가설을 바꿔도 이 값을 씀
MEDIA_VARIABLE_HYPO_KEY = "media-variable-hypo"   # 불러온 가설 (media_variable_saved()의 모양)
MEDIA_VARIABLE_GEN_KEY = "media-variable-gen"     # 그 가설의 후보 묶음 {"text", "set", "source", "error"}

# 가설 콜아웃 각 줄 앞에 붙는 배지 (Streamlit 마크다운 배지 문법)
MEDIA_VARIABLE_BADGES = [":blue-badge[If]", ":violet-badge[Because]", ":green-badge[Then]"]
# 가설 콜아웃을 짧게 보여 줄 때 If 끝에서 걷어 낼 문장 틀 (정규식, 바꿀 말). 위에서부터 차례로 적용
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
# 표의 한 줄 = 사용자가 고를 수 있는 변수 하나. 판정(통과/제외)은 묶음에 쓰지 않고 media_variable_judge()가 규칙으로 계산합니다.
# 변수 칸: name(표 이름 = 독립 변수), kind(main_image·title·price 등), if_match(가설의 If와 맞는지),
#          fallback(제외되면 대신 쓸 곳), reason(If와 안 맞는 이유), b_options(이 변수로 만들 B안 목록)
# B안 칸: label(고르기 버튼 이름), b, ref_prompt / 메인 이미지 규칙을 어긴 안만: rule_break, fallback
# 목록 순서 = 화면에 보일 우선순위
MEDIA_VARIABLE_STAGE_KIND = "main_image"   # 2·3단계(프롬프트 → 매체 제작)가 이어받을 수 있는 변수 종류
MEDIA_VARIABLE_PASS = "✅ 통과"     # 고를 수 있는 변수의 판정 값
MEDIA_VARIABLE_SHOW = 3   # 변수 표에 보여 줄 줄 수 (가설·후보 목록이 바뀌어도 이 수만큼만)
MEDIA_VARIABLE_PICK_MAX = MEDIA_VARIABLE_SHOW - 1   # 고를 수 있는 변수 수 (표의 한 줄은 걸러낸 예시로 남김)
MEDIA_VARIABLE_VAR_KEY = "media-variable-var"       # 사용자가 표에서 고른 변수 이름 (session_state)
MEDIA_VARIABLE_TABLE_KEY = "media-variable-table"   # 변수 표 (st.dataframe) key 앞부분 (뒤에 붙는 번호를 바꿔 선택을 되돌림)
MEDIA_VARIABLE_PICK_KEY = "media-variable-pick"     # B안 고르기 버튼 (st.segmented_control) key 앞부분 (뒤에 변수 번호)
# 사용자가 고른 B안 {변수 이름: 버튼 이름} (session_state). 버튼 값은 다른 하위 탭에 가면 Streamlit이 지우므로 따로 둠
MEDIA_VARIABLE_B_KEY = "media-variable-b"
MEDIA_VARIABLE_ROW_PX = 47   # 변수 표 줄 높이 (오른쪽 '고르기 버튼 + A·B 표'와 높이를 맞춤, media_style.css 참고)


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
    if (st.session_state.get(MEDIA_VARIABLE_GEN_KEY) or {}).get("text") == hypo["text"]:
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
    """Then을 짧게: '전환율이 2.4%에서 2.9%로 21% 오를 것이다' → '전환율 2.4% → 2.9% (21%↑)'.
    이 모양이 아니면 끝의 마침표만 빼고 그대로 둡니다 (뜻을 바꾸지 않도록 정해진 모양만 줄임)."""
    text = text.strip().rstrip(".")
    m = re.fullmatch(MEDIA_VARIABLE_THEN_PATTERN, text)
    if not m:
        return text
    arrow = "↑" if m["verb"] in MEDIA_VARIABLE_THEN_UP else "↓"
    goal = m["b"] + (" 이상" if m["more"] else "")
    return f"{m['metric']} {m['a']} → {goal} " + (f"({m['pct']}{arrow})" if m["pct"] else arrow)


def media_variable_callout(hypo: dict) -> None:
    """가설 콜아웃(st.info). If / Because / Then을 배지 붙은 줄로 나누고, 문장 틀만 걷어 낸 짧은 모양으로 보여 줍니다
    (대상은 맨 위 칩, Then은 숫자를 화살표로). 줄인 것은 화면뿐이고, 원문 문장 그대로는 오른쪽 위 '원문' ⓘ에 둡니다.
    2번 탭이 나눠 저장한 If/Because/Then이 있으면 그대로 쓰고, 없으면 문장을 나눕니다. 나눌 수 없는 문장은 한 덩어리로 보여 줍니다."""
    text = media_variable_kpi_name(hypo["text"])
    if hypo.get("if") and hypo.get("because") and hypo.get("then"):
        parts = [media_variable_kpi_name(p) for p in (hypo["if"], hypo["because"], hypo["then"])]
    else:
        parts = media_variable_split(text)
    if parts:
        target, parts[0] = media_variable_short_if(parts[0], str((hypo.get("problem") or {}).get("target") or ""))
        parts[1] = parts[1].strip().rstrip(",")
        parts[2] = f"**{media_variable_short_then(parts[2])}**"
        body = "  \n".join(f"{badge} {part}" for badge, part in zip(MEDIA_VARIABLE_BADGES, parts))
        if target:
            body = f":gray-badge[대상: {target}]  \n{body}"
    else:
        body = text
    st.info(body, icon="📥")
    # key="media-hypo-origin": media_style.css가 콜아웃 오른쪽 위 구석에 띄움
    with st.container(key="media-hypo-origin"):
        st.markdown(":gray[원문]", help=f"**2번 탭에서 넘어온 가설 원문**\n\n{hypo['text']}")

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
    """변수 하나의 (고를 수 있는지, 판정, 이유).
    걸러내는 순서: 가설의 If → 2·3단계가 이어받을 수 있는 종류(메인 이미지) → 메인 이미지 규칙 안에서 만들 B안이 있는지."""
    if not v.get("if_match"):
        return False, f"제외 → {v.get('fallback') or '다음 테스트'}", v.get("reason") or "가설의 If가 아님"
    if v.get("kind") != MEDIA_VARIABLE_STAGE_KIND:
        return False, "제외 → 다음 테스트", "2·3단계는 메인 이미지 변수만 이어받음"
    ok, broken = media_variable_b_options(v)
    if not ok:
        return False, "제외 → 서브 이미지", "메인 이미지 규칙 안에서 만들 B안이 없음"
    return True, MEDIA_VARIABLE_PASS, f"가설의 If · 규칙 안 B안 {len(ok)}개" + (f" (규칙 위반 {len(broken)}개 제외)" if broken else "")


def media_variable_label(c: dict) -> str:
    """B안 고르기 버튼에 보일 이름 (label이 없으면 이름)."""
    return c.get("label") or c.get("name", "")


def media_variable_candidates() -> dict:
    """지금 가설의 변수 판정 결과 {"set", "passed", "dropped", "variable", "options", "broken", "picked"}.
    passed = 고를 수 있는 변수(MEDIA_VARIABLE_PICK_MAX개까지), dropped = 제외 변수, variable = 사용자가 표에서 고른 변수,
    options / broken = 그 변수의 B로 쓸 수 있는 안 / 규칙 위반으로 못 쓰는 안, picked = 사용자가 고른 B안 (+ "variable" 칸).
    아직 고르지 않았으면 2단계로 확정해 둔 값 → 첫 통과 변수·첫 B안 순으로 고릅니다. 고를 변수가 없으면 variable·picked는 빈 dict."""
    cset = media_variable_candidate_set()
    passed, dropped = [], []
    for v in cset.get("variables", []):
        if not isinstance(v, dict) or not v.get("name"):
            continue
        ok, verdict, why = media_variable_judge(v)
        (passed if ok else dropped).append({**v, "verdict": verdict, "why": why})
    passed = passed[:MEDIA_VARIABLE_PICK_MAX]
    saved = media_handoff_plan()
    saved = {} if saved["sample"] else saved
    chosen = st.session_state.get(MEDIA_VARIABLE_VAR_KEY)
    variable = (next((v for v in passed if v["name"] == chosen), None)
                or next((v for v in passed if v["name"] == saved.get("variable")), None)
                or (passed[0] if passed else {}))
    options, broken = media_variable_b_options(variable) if variable else ([], [])
    chosen_b = st.session_state.get(MEDIA_VARIABLE_B_KEY, {}).get(variable["name"]) if variable else None
    picked = (next((o for o in options if media_variable_label(o) == chosen_b), None)
              or next((o for o in options if o["b"] == saved.get("b")), None)
              or (options[0] if options else {}))
    if picked:
        picked = {**picked, "variable": variable["name"]}
    return {"set": cset, "passed": passed, "dropped": dropped, "variable": variable,
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
    가설을 불러왔는데 고를 메인 이미지 변수가 없으면 variable은 표 첫 줄, b는 빈 문자열입니다 (확정 버튼이 꺼짐).
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
        rows = media_variable_rows(cands)
        plan.update(variable=rows[0]["name"] if rows else "", b="", b_ref="")
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


def media_variable_ref_prompt(b: str) -> str:
    """지금 가설의 후보 묶음에서 B 문장이 같은 B안의 AI 레퍼런스 프롬프트 (없으면 빈 문자열)."""
    for v in media_variable_candidate_set().get("variables", []):
        for o in (v.get("b_options") or []) if isinstance(v, dict) else []:
            if isinstance(o, dict) and o.get("b") == b:
                return o.get("ref_prompt") or ""
    return ""


def media_variable_go_step() -> None:
    """'① 으로 가서 확정하기' 버튼 콜백. 하위 탭을 ①로 바꿉니다 (위젯이 그려지기 전에 실행됨)."""
    st.session_state["media-step"] = MEDIA_VARIABLE_TAB_LABEL


def media_variable_has_goal(plan: dict) -> bool:
    """plan에 지금·목표 KPI 숫자가 있는지 (리포트 검색어 클릭 분석 KPI 가설일 때만 있음)."""
    return all(isinstance(plan.get(k), (int, float)) for k in ("kpi_now", "kpi_goal"))


def media_variable_kpi_text(plan: dict) -> str:
    """요약 카드·칩에 보일 KPI 한 줄. 숫자가 없으면 지표 이름과 '목표는 가설의 Then'만 보여 줍니다."""
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
        # 앞 배지로 칩이 무엇인지 알려 줌 (하위 탭 ① 요약 카드의 :green-badge[KPI]와 같은 색)
        label = f" · :gray[{MEDIA_VARIABLE_SQP_LABEL}]" if media_variable_has_goal(plan) else ""
        st.markdown(f":green-badge[🎯 A/B 목표 KPI] {media_variable_kpi_text(plan)}{label}", help="\n\n".join(tip))


def media_variable_hypothesis_step(plan: dict, picked: dict, hypo: dict):
    """2번 가설 탭에서 가져온 가설 콜아웃 + 핵심 요약 카드 (media_variable_step()의 윗부분)."""
    # 넓은 화면: 왼쪽(하위 탭 바 아래 빈자리)에 핵심 요약, 오른쪽(탭 바와 같은 줄)에 가설 콜아웃 (media_style.css)
    variable = f"{plan['variable']} ({media_variable_label(picked)})" if picked else (plan["variable"] or "없음")
    with st.container(horizontal=True, key="media-hypo-top"):
        with st.container(key="media-hypo-summary"):
            st.markdown(f":violet-badge[독립 변수] {variable}  \n"
                        f":green-badge[KPI] {media_variable_kpi_text(plan)}")
        with st.container(key="media-hypo-callout"):
            media_variable_callout(hypo)
    gen = st.session_state.get(MEDIA_VARIABLE_GEN_KEY) or {}
    if gen.get("source") == MEDIA_VARIABLE_AI_RULE_SOURCE:   # AI를 못 써서 규칙으로 만든 후보: 이유는 ⓘ에
        st.markdown(":gray-badge[규칙으로 만든 후보] AI를 쓰지 못해 가설의 If를 그대로 후보 변수와 B안으로 썼어요",
                    help=f"**이유**: {gen.get('error') or '-'}\n\n"
                         "같은 가설은 다시 만들지 않아요. 키를 넣은 뒤 새로고침하고 다시 불러오면 AI 후보로 바뀌어요.")


def media_variable_rows(cands: dict) -> list[dict]:
    """변수 표에 보일 줄: 통과 변수 → 제외 변수 순으로 MEDIA_VARIABLE_SHOW줄까지."""
    return (cands["passed"] + cands["dropped"])[:MEDIA_VARIABLE_SHOW]


def _media_variable_table_key() -> str:
    """변수 표 key. 뒤 번호를 올리면 새 표가 되어 선택이 고른 변수로 되돌아갑니다."""
    return f"{MEDIA_VARIABLE_TABLE_KEY}-{st.session_state.get('media-variable-table-ver', 0)}"


def _media_variable_select(rows: list[dict]) -> None:
    """변수 표에서 줄을 고를 때 콜백. 통과 변수면 그 변수로 바꾸고,
    제외 변수를 누르거나 고른 줄을 다시 눌러 선택이 풀리면 이유를 알리고 표 선택을 고른 변수로 되돌립니다."""
    state = st.session_state.get(_media_variable_table_key())
    picked_rows = state.selection.rows if state else []
    row = rows[picked_rows[0]] if picked_rows and picked_rows[0] < len(rows) else None
    if row and row["verdict"] == MEDIA_VARIABLE_PASS:
        st.session_state[MEDIA_VARIABLE_VAR_KEY] = row["name"]
        return
    if row:   # 제외 변수: 왜 A/B로 못 쓰는지 토스트로 보여 줌
        st.toast(f"**{row['name']}**: A/B로 못 써요 · {row['why']} ({row['verdict']})", icon="🚫")
    st.session_state["media-variable-table-ver"] = st.session_state.get("media-variable-table-ver", 0) + 1


def media_variable_derive_step(plan: dict, price: str, defaults: list[str], cands: dict):
    """후보 변수 걸러내기(표에서 변수 하나 고르기) → 고른 변수를 A/B로 나누기 (media_variable_step()의 아랫부분).
    선정 표의 값은 plan에서 가져옵니다."""
    passed, variable, options, picked = cands["passed"], cands["variable"], cands["options"], cands["picked"]
    rows = media_variable_rows(cands)
    # 왼쪽(변수 표)을 조금 넓혀 긴 문장이 한 줄에 들어가게 함 → 오른쪽(B안 고르기 버튼 + A·B 표)과 높이를 맞춤
    c1, c2 = st.columns([1.2, 1], gap="medium")
    with c1:
        # 걸러내는 기준은 제목 옆 ⓘ에 마우스를 올리면 보임 (설명 줄이 빠져 오른쪽 선정 표와 위쪽 끝이 맞음)
        hidden = cands["dropped"][max(0, MEDIA_VARIABLE_SHOW - len(passed)):]
        st.markdown("**후보 변수 걸러내기**", help=(
            "가설에서 바꿀 수 있는 변수를 한 줄에 하나씩 보여 줘요. 통과한 줄을 눌러 A/B로 실험할 변수를 골라요.\n\n"
            f"**후보를 만든 곳**: {(st.session_state.get(MEDIA_VARIABLE_GEN_KEY) or {}).get('source') or '-'} "
            "(판정은 아래 기준으로 코드가 다시 계산)\n\n"
            "**통과 기준**: 가설의 If와 맞고, 2·3단계가 이어받을 수 있는 메인 이미지 변수이며, "
            "아마존 메인 이미지 규칙 안에서 Manage Your Experiments로 돌릴 B안이 있어야 해요."
            + ("\n\n**표에 안 보이는 제외 변수**: " + ", ".join(f"{v['name']} ({v['verdict']})" for v in hidden)
               if hidden else "")))
        if rows:
            sel = [rows.index(variable)] if variable in rows else []
            # 줄 높이를 MEDIA_VARIABLE_ROW_PX로 고정 → 헤더 + 3줄의 높이가 오른쪽과 같아짐
            # (key="media-variable-candidates": 이 표만 찾을 수 있게 감쌈)
            with st.container(key="media-variable-candidates"):
                st.dataframe([{"변수": v["name"], "판정": v["verdict"], "이유": v["why"]} for v in rows],
                           hide_index=True, key=_media_variable_table_key(),
                           on_select=partial(_media_variable_select, rows), selection_mode="single-row",
                           selection_default={"selection": {"rows": sel, "columns": []}},
                           row_height=MEDIA_VARIABLE_ROW_PX, height=MEDIA_VARIABLE_ROW_PX * (len(rows) + 1) + 2,
                           column_config={"변수": st.column_config.TextColumn(width=190),
                                          "판정": st.column_config.TextColumn(width=125),
                                          "이유": st.column_config.TextColumn(width="large")})
        else:
            st.caption("이 가설의 후보 목록이 아직 없어요.")
    with c2:
        # 표에는 A·B만 (스크롤 없이 한 화면에 보이도록, 변수 표와 높이도 맞춤).
        # 독립·종속 변수는 위 요약 카드에 있고, 통제 변수·안전장치·B로 못 쓰는 안·가설에 딸린 참고 설명(note)은
        # 제목 옆 ⓘ에서 보임 (화면에서만 빠지고 2단계로 넘기는 plan에는 그대로 있음)
        note = cands["set"].get("note")
        broken = "\n".join(f"- {o['label']}: {o['rule_break']} → {o.get('fallback') or '서브 이미지'}"
                           for o in cands["broken"])
        st.markdown("**선정한 단일 변수**", help=(
            "왼쪽 표에서 고른 변수를 A(지금 그대로)와 B(바꾼 안)로 나눠요.\n\n"
            "**A는 고정**: 지금 아마존에 올라가 있는 메인 이미지(1번 리포트 값)라 바꾸지 않아요. "
            "지금보다 나아지는지 비교해야 가설(KPI가 지금 값에서 목표로 오르는지)을 확인할 수 있어서, "
            "A는 그대로 두고 B만 위 버튼으로 골라요.\n\n"
            f"**통제 변수 (고정)**: 같은 제품·색상, 흰 배경, 같은 조명과 보정, 제품 85% 이상 · 제목, 가격 {price}, 쿠폰 없음, "
            "불릿, A+ 콘텐츠, 서브 이미지, 광고 입찰\n\n"
            + (f"**종속 변수 (메인 KPI)**: {plan['kpi']} = {MEDIA_VARIABLE_KPI_RAW} (시장 대비 CTR)\n\n"
               if media_variable_has_goal(plan) else f"**종속 변수 (메인 KPI)**: {plan['kpi']} (목표는 가설의 Then)\n\n")
            + f"**안전장치**: CVR(단위 세션 비율)이 A보다 {plan['cvr_tolerance']:g}%p 넘게 떨어지면 B 실패"
            + (f"\n\n**B로 못 쓰는 안 (메인 이미지 규칙 위반)**\n{broken}" if broken else "")
            + (f"\n\n{note}" if note else "")))
        if options:   # 고른 변수의 B안 중 하나 (required=True: 고른 것을 다시 눌러도 빈 선택이 되지 않음)
            pick_key = f"{MEDIA_VARIABLE_PICK_KEY}-{passed.index(variable)}"
            st.segmented_control("B안 고르기", [media_variable_label(o) for o in options],
                                 default=media_variable_label(picked), required=True, key=pick_key,
                                 on_change=partial(_media_variable_pick_b, pick_key, variable["name"]),
                                 label_visibility="collapsed")
        if not passed:   # 메인 이미지 변수가 없는 가설: 표는 보여 주고 확정만 막음 (확정 줄에도 같은 안내)
            st.info("이 가설에는 메인 이미지로 실험할 변수가 없어요. 2·3단계(프롬프트 → 사진·영상)는 메인 이미지 "
                    "변수만 이어받아서 이 가설은 확정할 수 없어요.", icon="🚫")
            return
        # key="media-variable-picked": media_style.css가 구분 칸('A · 대조군')을 한 줄로 유지
        with st.container(key="media-variable-picked"):
            st.markdown("| 구분 | 내용 |\n| --- | --- |\n"
                        f"| **A · 대조군** | {plan['a']} (현재 사진 · 고정) |\n"
                        f"| **B · 실험군** | {plan['b']} |")
        if defaults:   # 리포트 탭을 아직 안 열었거나 리포트 칸 이름이 바뀌었을 때 바로 알아차리도록
            st.caption(f"1번 리포트 값이 없어 기본값으로 보여 줘요: {', '.join(defaults)}")


def _media_variable_pick_b(key: str, name: str) -> None:
    """B안 버튼 콜백. 고른 B안을 버튼과 따로 저장해, 다른 하위 탭에 갔다 와도 확정 전 선택이 남게 합니다."""
    st.session_state.setdefault(MEDIA_VARIABLE_B_KEY, {})[name] = st.session_state.get(key)


def _media_variable_confirm(plan: dict) -> None:
    """'이 변수로 확정' 버튼 콜백. A/B 설계를 2단계로 넘기고(modules/media/data/media_handoff_plan.json), 다음 화면에서 토스트를 띄웁니다."""
    media_handoff_set_plan(plan)
    st.session_state["media-variable-confirmed-toast"] = True


def media_variable_confirm_step(plan: dict):
    """선정 표 아래 확정 줄: 사용자가 고른 단일 변수를 확인하고 확정해야 2단계로 넘어갑니다."""
    state = media_variable_confirm_state(plan)
    confirmed = state == "same"
    if st.session_state.pop("media-variable-confirmed-toast", False):
        st.toast("단일 변수를 확정했어요. 다음 단계들이 이 값을 받아요", icon="✅")
    if not plan["b"]:   # 고를 메인 이미지 변수가 없음 → 확정 버튼 없이 안내만
        st.markdown(":gray-badge[확정 불가] 메인 이미지 변수가 있는 가설을 2번 탭에서 고르고 다시 불러와 주세요")
        return
    if confirmed:
        note = ":green-badge[✅ 확정됨] 다음 단계(A/B 소재 준비부터)가 이 값을 받아요"
    elif state == "changed":   # 확정한 뒤 고른 후보나 리포트 값이 바뀜
        note = ":orange-badge[다시 확정 필요] 확정한 뒤 고른 값이 바뀌었어요. 다음 단계는 아직 이전 값을 받아요"
    else:
        note = "후보를 고르고 확정하면 다음 단계(A/B 소재 준비부터)로 넘어가요"
    with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center",
                      key="media-variable-confirm-row"):
        st.markdown(note)
        if not confirmed:   # 확정된 뒤에는 버튼을 숨기고, 값이 바뀌면 '다시 확정'으로 다시 보여 줌
            st.button("다시 확정" if state == "changed" else "이 변수로 확정", key="media-btn-variable-confirm",
                      type="primary", on_click=_media_variable_confirm, args=(plan,))


def _media_variable_start_load() -> None:
    """'가설 불러오기' 버튼 콜백. 다음 화면 그리기에서 스피너를 띄우고 불러오도록 표시만 해 둡니다 (AI가 오래 걸릴 수 있어서)."""
    st.session_state["media-hypo-loading"] = True


def media_variable_step():
    """하위 탭 '가설에서 변수 도출': 오른쪽 위 '가설 불러오기' 버튼 → 가설 콜아웃 → 후보 걸러내기·단일 변수 선정.
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
    with st.container(key="media-hypo-box"):
        media_variable_hypothesis_step(plan, cands["picked"], hypo)
        # key="media-hypo-divider": media_style.css가 구분선 위아래 기본 여백(2em)을 줄여 윗줄 바로 아래에 붙임
        with st.container(key="media-hypo-divider"):
            st.divider()
        media_variable_derive_step(plan, price, defaults, cands)
        media_variable_confirm_step(plan)
