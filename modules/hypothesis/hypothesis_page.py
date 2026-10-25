# 2. 가설 수립
import copy
import html
from datetime import datetime
from pathlib import Path

import streamlit as st

import ui_theme as ui
from common.common_store import store_get, store_set
from modules.hypothesis.hypothesis_scenario import (
    hypothesis_ibt_clean,
    hypothesis_if_then_card,
    hypothesis_scenario_judgement,
    hypothesis_scenario_table,
)

HYPOTHESIS_MAX_CANDIDATES = 3   # "가설 1/2/3" 하부 탭 개수 상한

HYPOTHESIS_DIR = Path(__file__).resolve().parent   # 내 폴더 (images/, data/ 경로 만들 때 사용)

# 1. 분석 리포트 탭이 아래 모양으로 store_set("report", ...) 해 준다고 가정합니다.
# (기본 키 title/type/detail은 home_data.py의 HOME_DEMO가 이미 쓰고 있는 모양과 맞췄습니다.
#  target/metric/local_context/competitor_review는 가설 탭이 쓰려고 추가로 받는 선택 필드입니다.)
# report = {
#   "summary": "문제 요약 텍스트",            # 선택
#   "problems": [                            # 리스트. 맨 앞(0번) 문제로 가설 1개를 만듭니다
#     {
#       "title": ..., "type": "내부" | "외부",   # home과 같은 키/한글값
#       "detail": ...,                          # home과 같은 키 (= 문제 설명)
#       "target": ...,                          # 선택, 타깃 고객/채널
#       "metric": ...,                          # 선택, 측정 지표
#       "local_context": ...,                   # 선택, 현지(독일) 시장 특성
#       "competitor_review": ...,               # 선택, 독일에 진출한 경쟁사(유사 제품) 부정 리뷰 요약
#     },
#     ...
#   ],
# }
# (report 탭 담당자와 이 모양을 맞춰 주세요. 아직 안 정해졌으면 아래 샘플 버튼으로 먼저 테스트)

# MODO(독일 시장 냉감패드) 기준 샘플. home_data.py의 HOME_DEMO["report"]["problems"]와 같은
# 문제들을 쓰되, 가설 생성에 필요한 타깃/지표/현지 특성/경쟁사 리뷰를 덧붙였습니다.
SAMPLE_REPORT = {
    "summary": "경쟁사가 냉감패드 가격을 낮췄고, 배송 지연에 대한 부정 리뷰도 늘고 있어요.",
    "problems": [
        {
            "title": "경쟁사 가격 인하",
            "type": "외부",
            "detail": "경쟁사 B가 냉감패드 가격을 €39 → €29로 내렸습니다 (3일 전).",
            "target": "Amazon.de 독일 2030 구매자",
            "metric": "전환율",
            "local_context": "독일은 가격 비교 사이트(idealo)와 리뷰를 꼼꼼히 보고 사는 시장",
            "competitor_review": "경쟁 냉감패드 브랜드에 '냉감 부족', '세탁 후 변형' 부정 리뷰 다수",
            "plan": {   # 예시 값 (실제는 ① 문제 분석이 데이터로 만들어 줌)
                "action": "우리 vs 경쟁사 B 가격·냉감 성능 비교 상세 이미지", "because": "경쟁사 B가 €39에서 €29로 내려 가격 차이가 €10 벌어졌기",
                "kpi": "전환율", "now": 2.4, "goal": 2.9, "unit": "%", "better": "up", "visual": True,
                "material": "비교 상세 이미지 1장", "fixed": "가격·메인 이미지 그대로", "test": "상세 이미지 A/B 50:50",
                "period": "예시: 안별 4,000세션", "goal_basis": "예시 값",
            },
        },
        {
            "title": "배송 지연 리뷰",
            "type": "내부",
            "detail": "최근 7일 부정 리뷰 12건 중 7건이 배송 지연을 언급했습니다.",
            "target": "München, Berlin 등 대도시 재구매 고객",
            "metric": "재구매율",
            "plan": {
                "action": "배송 예정일 안내 메일", "because": "최근 7일 부정 리뷰 12건 중 7건이 배송 지연을 언급했기",
                "kpi": "배송 관련 부정 리뷰", "now": 7, "goal": 3, "unit": "건", "better": "down", "visual": False,
                "material": "안내 메일 문안", "fixed": "배송 업체 그대로", "test": "안내 전후 7일 부정 리뷰 비교",
                "period": "예시: 2주", "goal_basis": "예시 값",
            },
        },
        {
            "title": "장바구니 이탈 증가",
            "type": "내부",
            "detail": "결제 단계 이탈률 68% (+9%p). 배송비가 마지막 단계에 보이는 것이 원인으로 추정됩니다.",
            "target": "장바구니에 상품을 담은 독일 전체 고객",
            "metric": "결제 완료율",
            "plan": {
                "action": "상품 페이지 배송비 사전 표시 배너", "because": "결제 단계 이탈률이 68%로 9%p 올랐고 배송비가 마지막 단계에 보이기",
                "kpi": "결제 완료율", "now": 32.0, "goal": 41.0, "unit": "%", "better": "up", "visual": True,
                "material": "배송비 안내 배너 1장", "fixed": "가격·배송비 그대로", "test": "배너 A/B 50:50",
                "period": "예시: 안별 1,500세션", "goal_basis": "예시 값 (이탈률 상승 전 수준)",
            },
        },
    ],
}


def hypothesis_has_batchim(word: str) -> bool:
    """마지막 글자에 받침이 있는지 (조사 이/가, 을/를을 고를 때 씀). 끝의 괄호·문장부호는 건너뜀
    (예: "…고친 사진)" → "진" 기준으로 "을")."""
    word = str(word or "").strip()
    while word and not (word[-1].isalnum() or "가" <= word[-1] <= "힣"):
        word = word[:-1]
    if not word:
        return False
    code = ord(word[-1]) - 0xAC00
    if code < 0 or code > 11171:
        return False   # 한글 음절이 아니면 받침 없는 걸로 취급
    return code % 28 != 0


def hypothesis_particle(word: str, with_batchim: str, without_batchim: str) -> str:
    return with_batchim if hypothesis_has_batchim(word) else without_batchim


# 숫자로 끝날 때 읽는 소리의 받침: 0(영)·3(삼)·6(육)은 ㄹ 아닌 받침, 1(일)·7(칠)은 ㄹ 받침, 나머지는 받침 없음
_HYPOTHESIS_DIGIT_FINAL = {"0": "other", "3": "other", "6": "other", "1": "rieul", "7": "rieul"}


def hypothesis_particle_ro(word: str) -> str:
    """조사 로/으로: 받침 없음·ㄹ 받침 뒤는 "로", 그 외 받침 뒤는 "으로". 끝의 괄호·문장부호는
    건너뛰고 읽히는 마지막 글자로 판단합니다 (예: "…10% 수준" → "으로", "…(신규 브랜드)" → "로").
    예전에는 "로"로 고정해 "수준로", "위험로" 같은 비문이 나왔습니다."""
    text = str(word or "").rstrip()
    while text and not (text[-1].isalnum() or "가" <= text[-1] <= "힣"):
        text = text[:-1]
    if not text:
        return "로"
    last = text[-1]
    if "가" <= last <= "힣":
        final = (ord(last) - 0xAC00) % 28
        return "로" if final in (0, 8) else "으로"   # 8 = ㄹ 받침
    return "으로" if _HYPOTHESIS_DIGIT_FINAL.get(last) == "other" else "로"


def hypothesis_plan(problem: dict) -> dict | None:
    """report(1번)가 문제마다 데이터로 만들어 준 가설 재료(plan). 필요한 칸이 다 있을 때만 돌려줍니다.
    plan 칸: action(행동), because(이유), kpi(지표 이름), now(지금 값), goal(목표 값), unit(단위),
    better("up"=클수록 좋음 / "down"=작을수록 좋음), visual(사진·영상 소재 필요 여부), material(준비할 소재),
    fixed(고정 요소), test(테스트 방법), period(기간·표본), goal_basis(목표 근거).
    고정 개선율·키워드 문구는 쓰지 않으므로, plan이 없는 문제는 가설 후보가 되지 않습니다."""
    plan = problem.get("plan") if isinstance(problem, dict) else None
    if not isinstance(plan, dict):
        return None
    if not all(str(plan.get(k) or "").strip() for k in ("action", "because", "kpi")):
        return None
    if not all(isinstance(plan.get(k), (int, float)) for k in ("now", "goal")):
        return None
    return plan


def hypothesis_change_pct(plan: dict) -> float | None:
    """지금 값 → 목표 값의 변화율(%) = (목표 - 지금) ÷ 지금. 작을수록 좋은 지표는 줄어드는 비율.
    지금 값이 0이면 비율을 계산할 수 없어 None (문장에는 값만 씀)."""
    now, goal = plan["now"], plan["goal"]
    if not now:
        return None
    pct = (goal - now) / now * 100
    return -pct if plan.get("better") == "down" else pct


def hypothesis_num(value) -> str:
    """정수는 1,234 / 소수는 0.63처럼 (불필요한 0 없이)."""
    if isinstance(value, float) and not value.is_integer():
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    return f"{int(value):,}"


def hypothesis_goal_text(plan: dict) -> str:
    """'31건 → 93건 (+200%)'처럼 지금 값·목표 값·변화율."""
    unit = str(plan.get("unit") or "")
    pct = hypothesis_change_pct(plan)
    change = f" ({'+' if plan.get('better') != 'down' else '-'}{abs(pct):.0f}%)" if pct is not None else ""
    return f"{hypothesis_num(plan['now'])}{unit} → {hypothesis_num(plan['goal'])}{unit}{change}"


def hypothesis_build_ibt(problem: dict) -> dict:
    """가설 If·Because·Then. 전부 report의 plan(그 문제의 데이터)에서 만듭니다.
    Then의 변화율은 지금 값과 목표 값으로 계산합니다 (고정 %가 아님). plan이 없으면 빈 조각."""
    plan = hypothesis_plan(problem)
    if not plan:
        return {"if": "", "because": "", "then": ""}
    target = str(problem.get("target") or plan.get("target") or "").strip()
    action = str(plan["action"]).strip()
    kpi = str(plan["kpi"]).strip()
    unit = str(plan.get("unit") or "")
    goal = f"{hypothesis_num(plan['goal'])}{unit}"
    pct = hypothesis_change_pct(plan)
    move = "오를" if plan.get("better") != "down" else "낮아질"
    then = (f"{kpi}{hypothesis_particle(kpi, '이', '가')} {hypothesis_num(plan['now'])}{unit}에서 "
            f"{goal}{hypothesis_particle_ro(goal)} {f'{abs(pct):.0f}% ' if pct is not None else ''}{move} 것이다")
    where = f"{target}에 " if target else ""
    return hypothesis_ibt_clean({
        "if": f"{where}{action}{hypothesis_particle(action, '을', '를')} 적용한다면",
        "because": f"{str(plan['because']).strip()} 때문에",
        "then": then,
    })


def hypothesis_build_sentence(problem: dict) -> str:
    """가설 한 문장: 만약 [대상]에 [행동]을 적용한다면, [데이터 이유] 때문에 [지표]가 [지금 값]에서 [목표 값]으로 [변화율] 오를 것이다.
    같은 problem이면 항상 같은 문장입니다 (무작위 요소 없음). plan이 없으면 빈 문자열."""
    ibt = hypothesis_build_ibt(problem)
    if not ibt["if"]:
        return ""
    return f"만약 {ibt['if']}, {ibt['because']} {ibt['then']}."


def hypothesis_generic_detail_section(problem: dict) -> None:
    """가설 후보 탭 안의 "실행 방법" 표 (전부 report plan의 값)."""
    st.markdown("**:material/science: 실행 방법**")
    st.markdown(hypothesis_scenario_table(hypothesis_generic_execution_rows(problem)))
    basis = (hypothesis_plan(problem) or {}).get("goal_basis")
    st.caption(f"목표 근거: {basis}" if basis else "① 문제 분석 데이터로 만든 실행 방법이에요.")


def hypothesis_generic_execution_rows(problem: dict) -> list[tuple[str, str]]:
    """실행 방법 표 행. 화면 표와 "선택하기" 저장값이 같은 행을 씁니다."""
    plan = hypothesis_plan(problem)
    if not plan:
        return []
    rows = [("타깃", str(problem.get("target") or "-")),
            ("목표 KPI", f"{plan['kpi']} {hypothesis_goal_text(plan)}"),
            ("준비할 소재", str(plan.get("material") or "-")),
            ("고정 요소", str(plan.get("fixed") or "-")),
            ("테스트 방법", str(plan.get("test") or "-"))]
    if plan.get("period"):
        rows.append(("기간·표본", str(plan["period"])))
    return rows


def hypothesis_execution_rows(problem: dict, sqp: dict | None = None) -> list[tuple[str, str]]:
    """실행 방법 표 행 (모든 유형이 같은 plan 기반). sqp 인자는 예전 호출과 맞추려고 남겨 둠."""
    return hypothesis_generic_execution_rows(problem)


def hypothesis_evidence_rows(problem: dict) -> list[tuple[str, str]]:
    """문제 설명(detail)·현지 특성(local_context)·경쟁사 부정 리뷰(competitor_review) 원문(출처
    포함)을 표 행으로 모읍니다. 실행 방법 표에는 이 원문을 안 넣고, 오른쪽 끝 "근거·출처"
    아이콘을 누르면 열리는 창(hypothesis_dialog_evidence)에서만 보여줍니다."""
    rows = []
    if problem.get("detail"):
        rows.append(("문제 설명", str(problem["detail"])))
    if problem.get("local_context"):
        rows.append(("현지 특성 근거", str(problem["local_context"])))
    if problem.get("competitor_review"):
        rows.append(("경쟁사 부정 리뷰 근거", str(problem["competitor_review"])))
    return rows


# 상세 내용은 ① 탭처럼 화면 오른쪽 끝 아이콘을 누르면 지금 화면 위에 창(dialog)으로 엽니다
# (예전에는 실행 방법 아래 토글 2개였음 — "상세보기는 1번 탭처럼 오른쪽으로" 요청 반영).
@st.dialog("근거 · 출처", width="large", icon=":material/menu_book:")
def hypothesis_dialog_evidence(problem: dict) -> None:
    st.markdown(hypothesis_scenario_table(hypothesis_evidence_rows(problem)))
    st.caption("원문은 report(1번) 리포트가 준 값 그대로예요. 끝 괄호가 데이터 출처입니다.")


@st.dialog("KPI 표 · 판단 기준", width="large", icon=":material/fact_check:")
def hypothesis_dialog_judgement(sqp: dict) -> None:
    hypothesis_scenario_judgement(sqp)


@st.dialog("가설 보고서 다운로드", icon=":material/download:")
def hypothesis_dialog_pdf(saved: dict) -> None:
    """① 문제 분석 요약 + ② 선택한 가설을 한 PDF로 내려받습니다 (① 탭 PDF에는 가설이 없어서 따로 만듦)."""
    try:
        from modules.hypothesis.hypothesis_pdf import hypothesis_build_pdf
    except ImportError:
        st.warning("PDF를 만들려면 fpdf2 라이브러리가 필요합니다. `pip install -r requirements.txt`를 실행해 주세요.")
        return
    st.caption("① 핵심 요약·문제 도출 + ② 선택한 가설(If·Because·Then)·실행 방법이 들어가요. "
               "경쟁사 비교 등 ① 전체 내용은 ① 탭 PDF에 있어요.")
    today = datetime.now().strftime("%Y-%m-%d")
    st.download_button(
        "가설 보고서 다운로드 (PDF)",
        data=hypothesis_build_pdf(saved, today),
        file_name=f"hypothesis_report_{today}.pdf",
        mime="application/pdf",
        key="hypothesis-btn-download-pdf",
        type="primary",
        width="stretch",
    )


def hypothesis_resolve_ibt(problem: dict, sqp: dict | None = None) -> dict:
    """가설(If·Because·Then)은 후보마다 1벌. 검색어 문제도 다른 문제와 똑같이 report plan으로 만듭니다
    (예전에는 검색어 문제만 hypothesis_scenario.py의 별도 문장을 썼음). sqp 인자는 예전 호출과 맞추려고 남겨 둠."""
    return hypothesis_build_ibt(problem)


def hypothesis_resolve_sentence(problem: dict, sqp: dict | None = None) -> str:
    """가설 문장(저장용 한 문장). hypothesis_build_sentence()와 같음."""
    return hypothesis_build_sentence(problem)


def hypothesis_is_visual_candidate(problem: dict, sqp: dict | None = None) -> bool:
    """이 가설이 A/B 테스트용 사진·영상 소재로 바로 이어지는지 (report plan의 visual 값)."""
    return bool((hypothesis_plan(problem) or {}).get("visual"))


def hypothesis_pick_candidates(report: dict | None, limit: int = HYPOTHESIS_MAX_CANDIDATES) -> list[dict]:
    """report["problems"](리스트)에서 가설 후보를 최대 `limit`개 고릅니다. 모양이 이상한 항목·
    중복 제목·"가설 대상 아님"으로 명시된 문제는 건너뛰고, 남은 문제 중 A/B 테스트 결과물
    (사진·영상)로 바로 이어지는 문제를 먼저 보여줍니다 — 그 그룹 안에서는 report가 원래 매긴
    중요도 순서를 그대로 유지하고, 소재가 필요 없는 운영성 문제는 뒤로 밀립니다 (사진·영상
    후보가 `limit`개보다 적을 때만 운영성 문제로 채워집니다). 절대 죽지 않게 방어합니다."""
    if not report:
        return []
    problems = report.get("problems")
    if not isinstance(problems, list):
        return []
    sqp = report.get("sqp") if isinstance(report.get("sqp"), dict) else None

    valid: list[dict] = []
    seen_titles: set[str] = set()
    for item in problems:
        if not isinstance(item, dict) or not item.get("title"):
            continue
        # report_sqp.py(검색어 클릭 분석)는 "검색 의도가 다른" 검색어를 "가설 없이 광고 제외
        # 키워드로 처리"라고 스스로 명시합니다. 가설을 만들 대상이 아니라고 1번 쪽이 이미
        # 판단한 문제이므로, 후보 목록에서도 건너뜁니다.
        if "가설 없이" in str(item.get("detail") or ""):
            continue
        # 고정 문구·고정 개선율을 쓰지 않으므로, report가 데이터로 가설 재료(plan)를 준 문제만 후보
        if not hypothesis_plan(item):
            continue
        title = item["title"]
        if title in seen_titles:   # 같은 제목이 중복으로 와도 같은 가설 후보를 두 번 보여주지 않음
            continue
        seen_titles.add(title)
        valid.append(item)

    visual = [p for p in valid if hypothesis_is_visual_candidate(p, sqp)]
    non_visual = [p for p in valid if p not in visual]
    ordered = visual + non_visual

    # 실행 방법(액션)이 이미 고른 후보와 같은 문제는 뒤로 미룹니다 — 예: "장바구니 이탈률 71%"와
    # "장바구니 이탈 증가"가 둘 다 "장바구니 배송비 안내 배너"라 후보 3개 중 2개가 같은 실행 방법이
    # 되던 문제(① 형식 분석 30개 중 8개에서 발생). 서로 다른 액션이 limit개보다 적을 때만 겹치는
    # 문제로 채웁니다. 순서 규칙(사진·영상 우선, 그 안에서 report 순서)은 그대로입니다.
    picked, used_actions, held = [], set(), []
    for p in ordered:
        key = hypothesis_action_key(p, sqp)
        if key in used_actions:
            held.append(p)
            continue
        used_actions.add(key)
        picked.append(p)
    return (picked + held)[:limit]


def hypothesis_action_key(problem: dict, sqp: dict | None = None) -> str:
    """후보끼리 실행 방법이 겹치는지 비교할 때 쓰는 액션 이름 (report plan의 action)."""
    return str((hypothesis_plan(problem) or {}).get("action") or problem.get("title") or "")


def hypothesis_pick_problem(report: dict | None) -> dict | None:
    """하위 호환용: 가설 후보 중 1번(가장 중요한 문제)만 돌려줍니다."""
    candidates = hypothesis_pick_candidates(report, limit=1)
    return candidates[0] if candidates else None


def _hypothesis_handle_save(problem: dict, text: str, ibt: dict) -> None:
    """'가설 저장' 버튼의 on_click 콜백. media, solution, home 탭이 읽을 수 있게 'hypothesis' 키에
    가설 1개만 저장합니다. "hypothesis" 키는 home_data.py가 이미 기대하는 이름이라 같이 넣습니다.
    if_text/because_text/then_text도 같이 저장해서, 맨 위 "지금 선택된 가설" 칸도 가설 후보
    탭과 똑같은 If·Because·Then 카드로 보여줄 수 있게 합니다."""
    text = str(text or "").strip()
    if not text:   # 버튼이 비활성화돼 있어야 하지만, 혹시 모를 상태 꼬임에 대비한 이중 방어
        return
    # ① 리포트 값 전체를 맨 앞에 그대로 담고, 그 아래에 ② 내용(선택한 가설·실행 방법)을 붙여 저장
    # ("선택하기를 누르면 1번 리포트 값에 2번 내용이 하단에 추가돼 저장" 요청). ① 칸("report")은
    # 공용 규칙상 읽기만 하고 건드리지 않으므로, 합친 값은 ② 칸에 둡니다. 그 아래 기존 키들
    # (hypothesis/text/if_text…)은 ③·홈 탭이 이미 읽고 있어서 그대로 유지합니다.
    report = store_get("report")
    report = copy.deepcopy(report) if isinstance(report, dict) else None
    sqp = report.get("sqp") if report and isinstance(report.get("sqp"), dict) else None
    store_set(
        "hypothesis",
        {
            "report": report,
            "selected": {
                "problem": copy.deepcopy(problem),
                "if": ibt.get("if", ""),
                "because": ibt.get("because", ""),
                "then": ibt.get("then", ""),
                "sentence": text,
                "execution": dict(hypothesis_execution_rows(problem, sqp)),
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
            "hypothesis": text,   # home_data.py가 기대하는 키 이름 (완료 표시 등에 사용)
            "text": text,         # media 등에서 더 명확한 이름으로 읽고 싶을 때
            "if_text": ibt.get("if", ""),
            "because_text": ibt.get("because", ""),
            "then_text": ibt.get("then", ""),
            "problem_title": problem.get("title"),
            "target": problem.get("target"),
            "metric": problem.get("metric"),
            "type": problem.get("type"),
            "local_context": problem.get("local_context"),
            "competitor_review": problem.get("competitor_review"),
        },
    )
    # ① 리포트("report") 맨 아래에도 선택한 가설을 붙여 저장 → ③ 탭은 ① 분석 + ② 가설이 든 리포트 하나만 읽으면 됨
    # (① 탭이 다시 저장해도 이 칸은 유지하고, 문제가 사라지면 stale 표시: report_page.report_save_store)
    if report is not None:
        report_with_hyp = copy.deepcopy(report)
        report_with_hyp.pop("hypothesis", None)   # 예전 선택을 지우고 맨 아래에 새로 붙임
        report_with_hyp["hypothesis"] = {
            "problem": copy.deepcopy(problem),
            "if": ibt.get("if", ""),
            "because": ibt.get("because", ""),
            "then": ibt.get("then", ""),
            "sentence": text,
            "plan": copy.deepcopy(hypothesis_plan(problem)),
            "execution": dict(hypothesis_execution_rows(problem, sqp)),
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "stale": False,
            "stale_reason": "",
        }
        store_set("report", report_with_hyp)


def _hypothesis_render_candidate(index: int, problem: dict, sqp: dict | None, saved: dict | None) -> None:
    """가설 후보 1개(탭)를 그립니다. 제목 줄(오른쪽 끝에 작은 선택 버튼) → "🧪 실행 방법"
    메인 표(실행 방법을 보고 가설을 비교·선택할 수 있도록, If·Because·Then보다 먼저) →
    If·Because·Then 가설 카드 → 근거·출처 토글 순서입니다. 선택 여부와 관계없이 모든 후보를
    똑같은 구성으로 그립니다(예전에는 이미 선택된 후보만 카드를 생략했는데, "선택 안 한
    가설들도 실행 방법이 위에 뜨면 좋겠다"는 요청으로 전부 통일). index는 위젯 key를
    후보마다 다르게 만드는 데만 씁니다."""
    # 검색어 '소재 개선' 문제면 오른쪽 끝에 KPI 판단 기준(CTR·CVR 안전장치) 창 아이콘을 더 둡니다
    is_sqp_main = bool(
        sqp and problem.get("sqp_type") == "소재 개선" and sqp.get("query") == problem.get("query")
    )

    ibt = hypothesis_resolve_ibt(problem, sqp)
    text = f"만약 {ibt['if']}, {ibt['because']} {ibt['then']}."
    is_saved = bool(saved) and saved.get("text") == text and saved.get("problem_title") == problem.get("title")

    # key="hypothesis-card-{index}"를 주면 Streamlit이 .st-key-hypothesis-card-{index} 클래스를
    # 붙여줘서, hypothesis_style.css가 (와일드카드 선택자로) 이 카드들만 정확히 골라 스타일을 고칩니다.
    with st.container(border=True, key=f"hypothesis-card-{index}"):
        is_external = problem.get("type") == "외부"
        # 배지 + 제목 줄 오른쪽 끝에 작은 선택 버튼을 바로 붙입니다 — 예전에는 맨 아래에
        # 가로로 꽉 찬 "이 가설 선택하기" 버튼 + "✅ 선택됨" 안내 박스가 따로 있었는데,
        # "선택됨 박스는 지우고 이 위치 오른쪽 끝에 조그맣게 선택 버튼만 넣어 달라"는
        # 요청으로 제목 줄에 통합했습니다.
        # 외부 요인 뒤에는 report가 준 실제 분류(경쟁사·규제·날씨 등)를 붙임 — 예전엔 외부면 무조건
        # "경쟁사"라고 붙여서 규제(UWG) 문제도 "외부 요인 · 경쟁사"로 잘못 보였음
        group = html.escape(str(problem.get("group") or "").strip(), quote=False)
        badge_label = (f"⚠️ 외부 요인 · {group}" if group else "⚠️ 외부 요인") if is_external else "🏷️ 내부 요인"
        badge_class = "hypothesis-badge-external" if is_external else "hypothesis-badge-internal"
        title_col, button_col = st.columns([5, 1])
        with title_col:
            st.markdown(
                f'<p class="hypothesis-factor-line"><span class="hypothesis-badge {badge_class}">{badge_label}</span>'
                f' <b>{html.escape(str(problem.get("title", "")), quote=False)}</b></p>',
                unsafe_allow_html=True,
            )
        with button_col:
            # media, home 탭이 읽을 수 있게 "hypothesis" 키에 가설 1개만 저장 (가설 1/2/3 중
            # 사용자가 "선택"한 1개만 최종 저장됨 — 다른 후보를 선택하면 이 값이 바뀜).
            st.button(
                "✓ 선택됨" if is_saved else "선택하기",
                key=f"hypothesis-btn-save-{index}",
                disabled=is_saved,
                on_click=_hypothesis_handle_save,
                args=(problem, text, ibt),
                type="primary" if not is_saved else "secondary",
            )

        # 가설 후보 탭 안에서는 "실행 방법"만 보여주고 If·Because·Then 카드는 그리지 않습니다
        # — 선택하면 어차피 맨 위 "지금 선택된 가설" 칸에 카드로 뜨니, 탭 안에서 또 보여주는
        # 건 중복이라는 지적을 반영했습니다. ibt 자체는 선택 시 저장할 값으로는 계속 씁니다.
        hypothesis_generic_detail_section(problem)   # 모든 유형 같은 표 (report plan 값)

    # 오른쪽 끝 아이콘(① 탭과 같은 방식, hypothesis_style.css의 [class*="st-key-hypothesis-side-"]가
    # 화면에 고정). 가설 1/2/3 하부 탭마다 따로 그려지지만, 열린 탭 것만 보입니다.
    with st.container(key=f"hypothesis-side-{index}"):
        if is_sqp_main and st.button("", icon=":material/fact_check:",
                                     key=f"hypothesis-btn-side-judge-{index}", type="tertiary"):
            hypothesis_dialog_judgement(sqp)
        if hypothesis_evidence_rows(problem) and st.button("", icon=":material/menu_book:",
                                                           key=f"hypothesis-btn-side-evidence-{index}", type="tertiary"):
            hypothesis_dialog_evidence(problem)
        # 가설을 선택(저장)한 뒤에만: ① 요약 + ② 가설 PDF 다운로드
        if saved and isinstance(saved.get("selected"), dict) and st.button(
                "", icon=":material/download:", key=f"hypothesis-btn-side-pdf-{index}", type="tertiary"):
            hypothesis_dialog_pdf(saved)


def hypothesis_render():
    """'2. 가설 수립' 탭을 열 때마다 실행됩니다. 화면은 전부 이 함수 안에서 그립니다."""
    ui.page_header("2. 가설 수립", "1번 분석 리포트의 상위 문제로 가설 후보를 자동으로 만들고, 그중 하나를 골라 저장해요.")

    # report/problems 모양이 아직 안 정해졌거나 다른 탭이 예상과 다르게 저장해도
    # 화면이 깨지지 않도록, dict/list가 아니면 전부 "없음"으로 취급합니다.
    report = store_get("report")
    report = report if isinstance(report, dict) else None
    candidates = hypothesis_pick_candidates(report)
    sqp = report.get("sqp") if report else None
    sqp = sqp if isinstance(sqp, dict) else None

    problems = report.get("problems") if report else None
    if not candidates and isinstance(problems, list) and any(isinstance(p, dict) and p.get("title") for p in problems):
        # 문제는 있는데 데이터로 가설 재료(plan)를 만들 수 있는 문제가 없음 → 지어낸 문장 대신 이유를 보여 줌
        with st.container(border=True, key="hypothesis-empty"):
            st.markdown('<p class="hypothesis-empty-title">가설로 만들 데이터가 있는 문제가 없어요</p>', unsafe_allow_html=True)
            st.caption("고정 문구·고정 개선율을 쓰지 않아서, ① 문제 분석이 지금 값과 목표 값을 데이터로 준 문제만 가설이 됩니다.")
            reasons = [f"- {html.escape(str(p['title']), quote=False)}: {html.escape(str(p.get('plan_none') or '가설 재료 없음'), quote=False)}"
                       for p in problems if isinstance(p, dict) and p.get("title")][:8]
            st.markdown("\n".join(reasons))
        return

    if not candidates:
        # key="hypothesis-empty"를 줘서 hypothesis_style.css의 .st-key-hypothesis-empty 규칙이
        # 이 카드 버튼에도 똑같이 적용되게 합니다 (안 그러면 버튼 글씨가 또 안 보임).
        with st.container(border=True, key="hypothesis-empty"):
            st.markdown('<p class="hypothesis-empty-icon">🧭</p>', unsafe_allow_html=True)
            st.markdown('<p class="hypothesis-empty-title">아직 분석된 문제가 없어요</p>', unsafe_allow_html=True)
            st.caption("1. 분석 리포트 탭에서 문제를 분석하면, 그 결과로 가설 후보가 자동으로 만들어져요.")
            st.button(
                "예시 데이터로 먼저 테스트하기",
                key="hypothesis-btn-sample",
                type="primary",
                width="stretch",
                on_click=lambda: store_set("report", SAMPLE_REPORT),
            )
        return

    saved = store_get("hypothesis")
    saved = saved if isinstance(saved, dict) else None

    # 왼쪽에 "가설 후보"(표가 있어 내용이 많으니 넓게 3), 오른쪽에 "지금 선택된 가설"(카드
    # 하나라 좁게 2)을 나란히 둡니다 — 위아래로 쌓으면 스크롤이 많이 생겨서 옆으로 배치.
    # 페이지 제목 바로 밑에 붙어 보여서 두 칸 전체를 조금 내림 (.hypothesis-top-gap)
    st.markdown('<div class="hypothesis-top-gap"></div>', unsafe_allow_html=True)
    candidates_col, selected_col = st.columns([3, 2], gap="medium")

    # 두 칸 제목을 같은 크기(####, 페이지 제목보다 작게)로 맞추고, 오른쪽엔 왼쪽 "가설 1/2/3"
    # 탭 줄 높이만큼 빈칸(hypothesis-tab-spacer)을 둬서 왼쪽 후보 카드와 오른쪽 선택된 가설
    # 카드의 윗선이 같은 높이에서 시작하게 합니다.
    with selected_col:
        with st.container(key="hypothesis-heading-selected"):
            st.markdown("#### :material/check_circle: 지금 선택된 가설")
        st.markdown('<div class="hypothesis-heading-gap"></div>', unsafe_allow_html=True)
        st.markdown('<div class="hypothesis-tab-spacer"></div>', unsafe_allow_html=True)
        with st.container(border=True, key="hypothesis-selected-card"):
            if saved and str(saved.get("text") or "").strip():
                # 선택된 가설도 가설 후보 탭과 똑같은 If·Because·Then 카드로 보여줍니다
                # (요청 반영). if_text/because_text/then_text가 없는 예전 저장값(하위 호환)은
                # 밋밋한 박스로라도 문장을 그대로 보여줍니다.
                if saved.get("if_text") and saved.get("because_text") and saved.get("then_text"):
                    hypothesis_if_then_card([
                        ("If", "if", saved["if_text"]),
                        ("Because", "because", saved["because_text"]),
                        ("Then", "then", saved["then_text"]),
                    ])
                else:
                    st.markdown(f'<p class="hypothesis-callout-box">{html.escape(str(saved["text"]), quote=False)}</p>',
                                unsafe_allow_html=True)
            else:
                st.markdown(
                    '<p class="hypothesis-callout-box hypothesis-callout-empty">'
                    "아직 선택한 가설이 없어요. 왼쪽 가설 1·2·3 중 하나를 고르고 "
                    "'선택하기'를 눌러 주세요.</p>",
                    unsafe_allow_html=True,
                )

    with candidates_col:
        with st.container(key="hypothesis-heading-candidates"):
            st.markdown("#### :material/science: 가설 후보")
        # 제목 줄은 그대로 두고 그 아래 탭·박스만 내림 (오른쪽에도 같은 간격을 둬 윗선 정렬 유지)
        st.markdown('<div class="hypothesis-heading-gap"></div>', unsafe_allow_html=True)
        tabs = st.tabs([f"가설 {i + 1}" for i in range(len(candidates))], key="hypothesis-candidate-tabs")
        for i, (tab, problem) in enumerate(zip(tabs, candidates)):
            with tab:
                _hypothesis_render_candidate(i, problem, sqp, saved)
