# 2. 가설 수립 - 자체 테스트
#
# hypothesis_page.py를 고칠 때마다 돌려서 "이전에 잡았던 버그가 다시 생기지 않았는지" 확인하는 회귀 테스트입니다.
# pytest 등 추가 라이브러리 없이 Streamlit 내장 streamlit.testing.v1.AppTest와 표준 라이브러리만 씁니다.
#
# 2026-10-25 변경: 가설 문장은 키워드 규칙·고정 개선율(8%·10% 등)을 쓰지 않고, ① 문제 분석이 문제마다
# 데이터로 만들어 주는 가설 재료(problem["plan"])로만 만듭니다. 변화율 = (목표 값 - 지금 값) ÷ 지금 값.
# plan이 없는 문제는 가설 후보가 되지 않습니다. 선택한 가설은 ① 리포트(store "report") 맨 아래에도 저장됩니다.
#
# 실행 (프로젝트 맨 위 폴더에서):
#   python modules/hypothesis/hypothesis_test.py
import copy
import re
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from streamlit.testing.v1 import AppTest  # noqa: E402

from modules.hypothesis.hypothesis_page import (  # noqa: E402
    SAMPLE_REPORT,
    hypothesis_action_key,
    hypothesis_build_ibt,
    hypothesis_build_sentence,
    hypothesis_change_pct,
    hypothesis_execution_rows,
    hypothesis_has_batchim,
    hypothesis_particle_ro,
    hypothesis_pick_candidates,
    hypothesis_pick_problem,
    hypothesis_resolve_ibt,
    hypothesis_resolve_sentence,
)

_ok = 0
_fail = 0


def check(cond: bool, msg: str) -> None:
    global _ok, _fail
    if cond:
        _ok += 1
    else:
        _fail += 1
        print(f"[FAIL] {msg}")


def _new_apptest(loaded: bool = True) -> AppTest:
    """hypothesis_render()를 실제로 그려서 클릭까지 흉내 낼 수 있는 AppTest를 만듭니다.
    loaded=True면 '불러오기'를 이미 누른 상태로 시작합니다 (불러오기 흐름 자체는 test_core_flow에서 확인)."""
    script = (
        "import sys\n"
        f"sys.path.insert(0, {str(ROOT_DIR)!r})\n"
        "from modules.hypothesis.hypothesis_page import hypothesis_render\n"
        "hypothesis_render()\n"
    )
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8")
    tmp.write(script)
    tmp.close()
    at = AppTest.from_file(tmp.name)
    if loaded:
        at.session_state["hypothesis-loaded"] = True
    return at


def select_and_store(at: AppTest, index: int) -> None:
    """'선택하기'(고르기만) → 오른쪽 위 '저장하기'(store에 저장)."""
    at.button(key=f"hypothesis-btn-pick-{index}").click().run()   # 카드 맨 위 '가설 N'으로 열기
    at.button(key=f"hypothesis-btn-save-{index}").click().run()
    at.button(key="hypothesis-btn-store").click().run()


def plan(action="상세 이미지 B안", now=10, goal=12, unit="%", better="up", visual=True, **extra) -> dict:
    """테스트용 가설 재료 (① report_plan.py가 만드는 모양)."""
    return {"action": action, "because": "데이터로 확인한 이유가 있기", "kpi": "전환율", "now": now, "goal": goal,
            "unit": unit, "better": better, "visual": visual, "material": "소재 1장", "fixed": "가격 그대로",
            "test": "A/B 50:50", "period": "안별 1,000세션", "goal_basis": "테스트 값", **extra}


def problem(title, type_="내부", group="", p=None, **extra) -> dict:
    out = {"title": title, "type": type_, "group": group, "detail": f"{title} 설명", "target": "독일 구매자", **extra}
    if p is not None:
        out["plan"] = p
    return out


def real_report() -> dict | None:
    """① 문제 분석의 실제 결과 (Keepa·검색어 분석 파일, 네트워크 호출 없음). report 모듈이 없으면 None."""
    try:
        import requests
        requests.get = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("network blocked"))
        from modules.report.report_data import report_load_data
        d = report_load_data()
    except Exception as err:   # report 모듈이 바뀌어도 이 테스트 파일은 돌아가게
        print(f"[참고] 실제 ① 리포트를 못 만듦: {type(err).__name__}: {err}")
        return None
    return {"summary": "실제 ①", "problems": d["problems"], "sqp": d["sqp_store"], "key_problems": d["key_problems"]}


# ─────────────────────────────────────────────
# 1. 핵심 흐름: 빈 상태 → 샘플 → 가설 1/2/3 → 선택(저장) → 다른 후보로 재선택
# ─────────────────────────────────────────────
def test_core_flow() -> None:
    at = _new_apptest(loaded=False)
    at.run()
    check(not at.exception, "[핵심] 1차 실행에 예외 없음")
    check(any("아직 불러오지 않음" in c.value for c in at.caption), "[핵심] 불러오기 전에는 기본 틀만 (안내 문구)")
    check(at.button(key="hypothesis-btn-store").disabled, "[핵심] 불러오기 전에는 저장하기 비활성")
    check(not [b for b in at.button if (b.key or "").startswith("hypothesis-btn-pick-")], "[핵심] 불러오기 전에는 가설 1·2·3 버튼 없음")
    at.button(key="hypothesis-btn-load").click().run()
    check(not at.exception, "[핵심] 불러오기 후 예외 없음")
    # ① 저장 리포트가 없으면 ② 불러오기 → ① 탭으로 이동, ①은 분석을 불러온 상태('다음으로'를 바로 누를 수 있게)
    from common.common_layout import LAYOUT_TABS   # 탭 아이콘은 PM이 바꿀 수 있어 탭 목록에서 이름을 만듦
    report_tab = next(t for t in LAYOUT_TABS if t["code"] == "report")
    report_label = f"{report_tab['icon']} {report_tab['label'].replace(' ', chr(160))}"
    check(at.session_state["main_tabs"] == report_label, f"[핵심] ① 리포트 없으면 ① 탭으로 이동 ({at.session_state['main_tabs']!r})")
    check(at.session_state["report-loaded"] is True, "[핵심] ① 탭은 불러오기 누른 상태로")
    check(not at.session_state["hypothesis-loaded"] if "hypothesis-loaded" in at.session_state else True, "[핵심] ② 는 아직 불러오기 전")
    check(not any("아직 분석된 문제가 없어요" in m.value for m in at.markdown), "[핵심] 따로 빈 화면(예시 데이터 버튼)은 없음")
    at.session_state["store-report"] = SAMPLE_REPORT   # ① 탭에서 '다음으로'(저장)했다고 가정
    at.button(key="hypothesis-btn-load").click().run()

    check(not at.exception, "[핵심] 샘플 클릭 후 예외 없음")
    # ① 문제 분석 순서 그대로 (예전에는 사진·영상 소재가 필요한 가설을 앞으로 옮겼음)
    cands = hypothesis_pick_candidates(SAMPLE_REPORT)
    check([c["title"] for c in cands] == ["경쟁사 가격 인하", "배송 지연 리뷰", "장바구니 이탈 증가"],
          f"[핵심] ① 순서 그대로 (실제: {[c['title'] for c in cands]})")
    check([b.label for b in at.button if (b.key or "").startswith("hypothesis-btn-pick-")] == ["가설 1", "가설 2", "가설 3"],
          "[핵심] 샘플 3문제가 카드 안 가설 1/2/3 버튼으로 뜸")
    check(any("아직 선택한 가설이 없어요" in m.value for m in at.markdown), "[핵심] 처음엔 '지금 선택된 가설' 비어 있음")
    check(sum("hypothesis-ibt-box" in m.value for m in at.markdown) == 0, "[핵심] 선택 전에는 If·Because·Then 카드 없음")
    check([b.label for b in at.button if b.key and b.key.startswith("hypothesis-btn-save-")] == ["선택하기"],
          "[핵심] 열린 후보 카드에 '선택하기' 버튼 1개")
    at.button(key="hypothesis-btn-pick-2").click().run()
    check("hypothesis-btn-save-2" in {b.key for b in at.button} and "hypothesis-btn-save-0" not in {b.key for b in at.button},
          "[핵심] '가설 3'을 누르면 가설 3 카드로 바뀜")
    at.button(key="hypothesis-btn-pick-0").click().run()

    check(at.button(key="hypothesis-btn-store").disabled, "[핵심] 고르기 전에는 저장하기 비활성")
    at.button(key="hypothesis-btn-save-0").click().run()
    check(at.button(key="hypothesis-btn-save-0").label == "✓ 선택됨", "[핵심] 선택 후 버튼 라벨 변경")
    check(at.button(key="hypothesis-btn-save-0").disabled, "[핵심] 이미 선택된 가설 버튼은 비활성화")
    check(at.session_state["store-hypothesis"] is None, "[핵심] '선택하기'만으로는 저장 안 됨")
    check(not at.button(key="hypothesis-btn-store").disabled, "[핵심] 고르면 저장하기 활성")
    check(any("**아직 저장 안 됨**" in m.value for m in at.markdown), "[핵심] 저장 전 안내 (제목 옆 물음표 안)")
    at.button(key="hypothesis-btn-store").click().run()
    check(not at.button(key="hypothesis-btn-store").disabled, "[핵심] 저장 후에도 '다음으로'는 켜짐 (저장된 가설 그대로 ③으로)")
    media_tab = next(t for t in LAYOUT_TABS if t["code"] == "media")   # 탭 이름은 PM이 바꿀 수 있어 탭 목록에서 만듦
    check(at.session_state["main_tabs"] == f"{media_tab['icon']} {media_tab['label'].replace(' ', chr(160))}", f"[핵심] 저장하면 ③ 탭으로 ({at.session_state['main_tabs']!r})")
    check(at.session_state["media-hypo-loading"] is True, "[핵심] '다음으로' → ③이 가설을 바로 불러오도록 표시")
    check(any("**저장됨**" in m.value for m in at.markdown), "[핵심] 저장 후 '저장됨' 표시 (제목 옆 물음표 안)")
    saved = at.session_state["store-hypothesis"]
    check(saved.get("text") == hypothesis_build_sentence(cands[0]), "[핵심] 저장 문장 = 화면 후보 문장")
    check(saved.get("hypothesis") == saved.get("text"), "[핵심] 홈이 읽는 'hypothesis' 키도 같이 저장")
    ibt = hypothesis_build_ibt(cands[0])
    check(all(any(v in m.value for m in at.markdown) for v in ibt.values()), "[핵심] '지금 선택된 가설'에 If·Because·Then 표시")

    select_and_store(at, 1)
    check(at.button(key="hypothesis-btn-save-1").label == "✓ 선택됨", "[핵심] 가설 2 선택 → 가설 2가 '선택됨'")
    at.button(key="hypothesis-btn-pick-0").click().run()
    check(at.button(key="hypothesis-btn-save-0").label == "선택하기", "[핵심] 가설 1은 '선택됨'에서 풀림")
    check(at.session_state["store-hypothesis"].get("text") == hypothesis_build_sentence(cands[1]), "[핵심] 최종 저장은 항상 1개")


# ─────────────────────────────────────────────
# 2. 방어적 처리: report 모양이 이상해도 죽지 않음
# ─────────────────────────────────────────────
def test_defensive() -> None:
    bad_reports = [
        "이건 dict가 아니라 문자열",
        {"problems": {"title": "리스트가 아니라 dict"}},
        {"problems": ["문자열로만 이루어진 리스트"]},
        {"problems": []},
        {"problems": [{"title": 12345, "type": "내부", "detail": "제목이 숫자", "plan": plan()}]},
        {"problems": [{"title": "plan 모양 이상", "plan": "문자열"}]},
        {"problems": [{"title": "plan 숫자 없음", "plan": plan(now="열")}]},
    ]
    for bad in bad_reports:
        at = _new_apptest()
        at.session_state["store-report"] = bad
        at.run()
        check(not at.exception, f"[방어] report={str(bad)[:60]!r} 에도 예외 없음")

    at = _new_apptest()
    at.session_state["store-report"] = {"problems": [problem("문제", p=plan())]}
    at.session_state["store-hypothesis"] = "예전에 남은 이상한 값"
    at.run()
    check(not at.exception, "[방어] 저장된 hypothesis가 dict가 아니어도 예외 없음")
    check(at.button(key="hypothesis-btn-save-0").label == "선택하기", "[방어] 이상한 저장값은 '선택됨'으로 치지 않음")


# ─────────────────────────────────────────────
# 3. 고정값 없음: 행동·이유·지표·변화율은 전부 plan(데이터)에서, plan이 없으면 후보가 아님
# ─────────────────────────────────────────────
def test_no_fixed_values() -> None:
    p = problem("리뷰 부족", group="신뢰", p=plan("정식 리뷰 요청", now=31, goal=93, unit="건", visual=False))
    s = hypothesis_build_sentence(p)
    check("31건에서 93건으로 200% 오를 것이다" in s, f"[고정값 없음] 변화율 = (93-31)÷31 = 200% (실제: {s})")
    check("정식 리뷰 요청을 적용한다면" in s and "데이터로 확인한 이유가 있기 때문에" in s, "[고정값 없음] 행동·이유가 plan 그대로")
    check(hypothesis_change_pct(p["plan"]) == 200, "[고정값 없음] hypothesis_change_pct 계산")

    p2 = copy.deepcopy(p)
    p2["plan"]["goal"] = 62
    check("100% 오를" in hypothesis_build_sentence(p2), "[고정값 없음] 목표 값이 바뀌면 변화율도 바뀜 (31→62 = 100%)")

    down = problem("부정 리뷰", p=plan("안내 메일", now=8, goal=2, unit="건", better="down"))
    check("8건에서 2건으로 75% 낮아질 것이다" in hypothesis_build_sentence(down), "[고정값 없음] 작을수록 좋은 지표는 '낮아질'")
    zero = problem("리뷰 0건", p=plan("리뷰 요청", now=0, goal=10, unit="건"))
    s0 = hypothesis_build_sentence(zero)
    check("0건에서 10건으로 오를 것이다" in s0 and "%" not in s0.split("때문에")[-1], "[고정값 없음] 지금 값 0이면 % 없이 값만")

    no_plan = [problem("경쟁사 가격 인하", "외부", "경쟁사"), problem("비시즌", "외부", "날씨", plan_none="날씨는 바꿀 수 없음")]
    check(hypothesis_pick_candidates({"problems": no_plan}) == [], "[고정값 없음] plan 없는 문제는 후보가 아님")
    check(hypothesis_build_sentence(no_plan[0]) == "", "[고정값 없음] plan 없으면 문장을 지어내지 않음")
    at = _new_apptest()
    at.session_state["store-report"] = {"problems": no_plan}
    at.run()
    md = "".join(m.value for m in at.markdown)
    check(not at.exception and "가설로 만들 데이터가 있는 문제가 없어요" in md, "[고정값 없음] plan 없는 문제만 있으면 안내")
    check("날씨는 바꿀 수 없음" in md, "[고정값 없음] 안내에 ①이 준 이유(plan_none) 표시")

    mixed = {"problems": no_plan + [p]}
    check([c["title"] for c in hypothesis_pick_candidates(mixed)] == ["리뷰 부족"], "[고정값 없음] plan 있는 문제만 후보")
    for old in ("8% 개선", "10% 개선", "27% 개선", "프로모션 배너", "세탁내구"):
        check(old not in hypothesis_build_sentence(p), f"[고정값 없음] 예전 고정 문구 '{old}' 없음")


# ─────────────────────────────────────────────
# 4. 문장 품질 (형식·조사)
# ─────────────────────────────────────────────
def check_sentence_quality(label: str, s: str) -> None:
    check(bool(s) and s.strip() == s, f"[품질:{label}] 비어있지 않고 앞뒤 공백 없음")
    check(s.startswith("만약 ") and s.endswith("것이다."), f"[품질:{label}] '만약 … 것이다.' 형식")
    check(s.count("만약") == 1 and s.count("것이다") == 1, f"[품질:{label}] 템플릿 문구 중복 없음")
    m = re.search(r"(\S+?)(을|를) 적용한다면", s)
    check(bool(m), f"[품질:{label}] '~을/를 적용한다면' 패턴")
    if m:
        check(m.group(2) == ("을" if hypothesis_has_batchim(m.group(1)) else "를"), f"[품질:{label}] 을/를 받침 규칙 ({m.group(0)})")


def test_quality() -> None:
    check(hypothesis_has_batchim("고친 사진)"), "[조사] 끝 괄호는 건너뛰고 '진' 기준 받침 있음")
    check(not hypothesis_has_batchim("없이)"), "[조사] '없이)'는 받침 없음")
    check(hypothesis_particle_ro("10% 수준") == "으로" and hypothesis_particle_ro("93건") == "으로", "[조사] 로/으로")
    check(hypothesis_particle_ro("0.98배") == "로", "[조사] '배' 뒤 로")
    s = hypothesis_build_sentence(problem("이미지", p=plan("메인 이미지 B안(지금 문제를 고친 사진)")))
    check("고친 사진)을 적용한다면" in s, f"[조사] 괄호로 끝난 행동 뒤 '을' (실제: {s})")
    for p in SAMPLE_REPORT["problems"]:
        check_sentence_quality(p["title"], hypothesis_build_sentence(p))
    rep = real_report()
    for p in hypothesis_pick_candidates(rep) if rep else []:
        check_sentence_quality(f"실제 ①:{p['title'][:12]}", hypothesis_build_sentence(p))


# ─────────────────────────────────────────────
# 5. 같은 문제면 항상 같은 문장 (무작위 없음)
# ─────────────────────────────────────────────
def test_deterministic() -> None:
    for p in SAMPLE_REPORT["problems"]:
        first = hypothesis_build_sentence(p)
        check(all(hypothesis_build_sentence(copy.deepcopy(p)) == first for _ in range(5)), f"[결정적:{p['title']}] 5번 모두 같음")
    check(hypothesis_pick_problem(SAMPLE_REPORT)["title"] == "경쟁사 가격 인하", "[결정적] hypothesis_pick_problem = 후보 1번")


# ─────────────────────────────────────────────
# 6. ③ 탭 연결: 저장 문장을 ", "로 잘라 If/Because/Then으로 씀 → 조각 안에 ", " 없어야 함
# ─────────────────────────────────────────────
def test_media_split_ready() -> None:
    items = list(SAMPLE_REPORT["problems"])
    items.append(problem("쉼표, 많은 문제", p=plan("A, B 이미지", because="가격이 €39, €29로 바뀌었기")))
    rep = real_report()
    items += hypothesis_pick_candidates(rep) if rep else []
    for p in items:
        ibt = hypothesis_resolve_ibt(p, None)
        label = str(p.get("title"))[:24]
        check(all(", " not in v for v in ibt.values()), f"[③연결:{label}] 조각 안에 ', ' 없음 ({ibt})")
        check(ibt["because"].endswith("때문에") and " 때문에 " not in ibt["then"], f"[③연결:{label}] Because/Then 경계")


# ─────────────────────────────────────────────
# 7. 후보끼리 실행 방법(행동)이 겹치면 뒤로
# ─────────────────────────────────────────────
def test_candidate_action_diversity() -> None:
    report = {"problems": [
        problem("장바구니 이탈률 71%", p=plan("배송비 안내 배너")),
        problem("장바구니 이탈 증가", p=plan("배송비 안내 배너")),   # 같은 행동
        problem("인증 미표시", p=plan("인증 마크 이미지")),
        problem("품절 임박", p=plan("재입고 알림", visual=False)),
    ]}
    cands = hypothesis_pick_candidates(report, limit=3)   # 서로 다른 행동이 상한만큼 있으면 겹치는 문제는 빠짐
    keys = [hypothesis_action_key(p) for p in cands]
    check(len(set(keys)) == len(keys) == 3, f"[다양성] 후보 3개의 행동이 모두 다름 ({keys})")
    check([c["title"] for c in cands] == ["장바구니 이탈률 71%", "인증 미표시", "품절 임박"], "[다양성] 겹치는 문제만 건너뜀")
    check(len(hypothesis_pick_candidates({"problems": report["problems"][:2]})) == 2, "[다양성] 부족하면 겹치는 문제로 채움")


# ─────────────────────────────────────────────
# 8. 저장: ② 칸("hypothesis")에 ①+② / ① 리포트("report") 맨 아래에도 선택 가설
# ─────────────────────────────────────────────
def test_save_report_plus_hypothesis() -> None:
    for report in (copy.deepcopy(SAMPLE_REPORT), real_report()):
        if not report:
            continue
        before = copy.deepcopy(report)
        at = _new_apptest()
        at.session_state["store-report"] = report
        at.run()
        cands = hypothesis_pick_candidates(copy.deepcopy(report))
        for j, p in enumerate(cands):
            select_and_store(at, j)
            label = f"[저장:{str(p.get('title'))[:14]}]"
            check(not at.exception, f"{label} 예외 없음")
            saved = at.session_state["store-hypothesis"]
            sel = saved.get("selected") or {}
            check(list(saved)[:2] == ["report", "selected"], f"{label} ② 칸: ① 리포트 → ② 내용 순서")
            check(sel.get("execution") == dict(hypothesis_execution_rows(p)), f"{label} 실행 방법 = 화면 표")
            check(sel.get("sentence") == saved.get("text") == hypothesis_resolve_sentence(p), f"{label} 문장 저장")
            check(all(k in saved for k in ("hypothesis", "text", "if_text", "because_text", "then_text", "problem_title")),
                  f"{label} ③·홈이 읽는 기존 키 유지")
            rep = at.session_state["store-report"]
            hyp = rep.get("hypothesis") or {}
            check(list(rep)[-1] == "hypothesis", f"{label} ① 리포트 맨 아래 키가 hypothesis")
            check(hyp.get("problem", {}).get("title") == p.get("title") and hyp.get("sentence") == saved.get("text"),
                  f"{label} ① 리포트 하단에 선택한 문제·문장")
            check(hyp.get("plan") == p.get("plan") and hyp.get("stale") is False, f"{label} 가설 재료(plan)·stale=False 저장")
            check({k: v for k, v in rep.items() if k != "hypothesis"} == {k: v for k, v in before.items() if k != "hypothesis"},
                  f"{label} ① 리포트의 다른 값은 그대로")
        check(sum(1 for k in at.session_state["store-report"] if k == "hypothesis") == 1, "[저장] 다시 선택해도 하단 가설은 1개")


# ─────────────────────────────────────────────
# 9. 가설 보고서 PDF
# ─────────────────────────────────────────────
def test_hypothesis_pdf() -> None:
    from modules.hypothesis.hypothesis_pdf import hypothesis_build_pdf
    at = _new_apptest()
    at.session_state["store-report"] = copy.deepcopy(SAMPLE_REPORT)
    at.run()
    check(at.button(key="hypothesis-btn-pdf").disabled, "[PDF] 선택 전에는 다운로드 아이콘 흐리게(비활성)")
    check({"hypothesis-btn-side-judge-0", "hypothesis-btn-side-evidence-0"} <= {b.key for b in at.button},
          "[아이콘] 오른쪽 아이콘 3개는 항상 같은 자리")
    select_and_store(at, 0)
    check(not at.button(key="hypothesis-btn-pdf").disabled, "[PDF] 선택 후 다운로드 아이콘 활성")
    at.button(key="hypothesis-btn-pdf").click().run()
    check(not at.exception, "[PDF] 다운로드 창 예외 없음")
    pdf = hypothesis_build_pdf(at.session_state["store-hypothesis"], "2026-10-25")
    check(pdf[:5] == b"%PDF-" and len(pdf) > 5000, f"[PDF] PDF 생성 ({len(pdf):,} bytes)")
    check(hypothesis_build_pdf({"text": "만약 A, B C."}, "2026-10-25")[:5] == b"%PDF-", "[PDF] 예전 저장값도 깨지지 않음")


# ─────────────────────────────────────────────
# 10. 배지: 외부 요인은 report가 준 분류를 그대로
# ─────────────────────────────────────────────
def test_badge_group() -> None:
    at = _new_apptest()
    at.session_state["store-report"] = {"problems": [
        problem("UWG 경고장 위험", "외부", "규제", p=plan("필수 표기")),
        problem("경쟁사 가격 인하", "외부", "경쟁사", p=plan("비교 이미지")),
        problem("분류 없는 외부 문제", "외부", p=plan("환율 안내")),
    ]}
    at.run()
    md = ""
    for k in range(3):   # 카드는 열린 가설 1개만 그려지므로 가설 1·2·3을 차례로 열어 배지를 모음
        at.button(key=f"hypothesis-btn-pick-{k}").click().run()
        md += "".join(m.value for m in at.markdown if "hypothesis-factor-line" in m.value)
    check(not at.exception, "[배지] 예외 없음")
    check("외부 요인 · 규제" in md and "외부 요인 · 경쟁사" in md, "[배지] 규제·경쟁사 분류 표시")
    check(md.count("외부 요인 · 경쟁사") == 1, "[배지] 경쟁사가 아닌 외부 문제에 '경쟁사'를 붙이지 않음")


# ─────────────────────────────────────────────
# 11. 실제 ① 리포트로: 후보·문장·표가 전부 데이터 값
# ─────────────────────────────────────────────
def test_real_report() -> None:
    rep = real_report()
    if not rep:
        check(True, "[실제 ①] report 모듈 없음 → 건너뜀")
        return
    cands = hypothesis_pick_candidates(rep)
    check(len(cands) >= 1, f"[실제 ①] 가설 후보 {len(cands)}개")
    check(all(p.get("plan") for p in cands), "[실제 ①] 후보는 모두 plan 있음")
    for p in cands:
        pl, s = p["plan"], hypothesis_build_sentence(p)
        label = f"[실제 ①:{p['title'][:14]}]"
        check(pl["action"] in s and pl["kpi"] in s, f"{label} 행동·지표가 plan 값")
        pct = hypothesis_change_pct(pl)
        check(pct is None or f"{abs(pct):.0f}%" in s, f"{label} 변화율 {pct}이 지금·목표 값 계산과 같음")
        rows = dict(hypothesis_execution_rows(p))
        check(all(rows.get(k) for k in ("목표 KPI", "준비할 소재", "테스트 방법")), f"{label} 실행 방법 표가 채워짐")
    planned = [p["title"] for p in rep["problems"] if p.get("plan") and "가설 없이" not in str(p.get("detail"))]
    titles = list(dict.fromkeys(c["title"] for c in cands))   # ①이 B안을 나눈 문제는 같은 제목으로 여러 후보
    check(titles == planned[:len(titles)], "[실제 ①] 후보 순서 = ① 문제 순서 (가설 재료 있는 문제만)")
    check(all(c.get("variant_label") for c in cands if (c["plan"] or {}).get("variants")), "[실제 ①] B안 후보마다 이름(variant_label)")
    check(len({c["plan"]["action"] for c in cands}) == len(cands), "[실제 ①] 후보마다 행동(B안)이 다름")
    tops = [k["title"] for k in rep["key_problems"]]
    for c in cands:
        if c["title"] in tops:
            check(c.get("report_rank_label") == f"① {tops.index(c['title']) + 1}순위", f"[실제 ①] '{c['title'][:12]}' 배지 = ① 순위")
    excluded = [p for p in rep["problems"] if not p.get("plan")]
    check(all(p.get("plan_none") for p in excluded), "[실제 ①] 후보에서 빠진 문제는 모두 이유(plan_none) 있음")
    at = _new_apptest()
    at.session_state["store-report"] = rep
    at.run()
    check(not at.exception, "[실제 ①] 화면 예외 없음")
    check(not at.button(key="hypothesis-btn-side-judge-0").disabled
          or not any(c.get("sqp_type") == "소재 개선" for c in cands[:1]), "[실제 ①] 검색어 소재 개선 후보는 판단 기준 아이콘 활성")


# ─────────────────────────────────────────────
# 12. 이용자가 고를 때만 선택: 예전에 저장된 가설이 있어도 자동으로 '선택됨'이 되지 않음
# ─────────────────────────────────────────────
def test_user_pick_only() -> None:
    at = _new_apptest()
    at.session_state["store-report"] = copy.deepcopy(SAMPLE_REPORT)
    first = hypothesis_pick_candidates(SAMPLE_REPORT)[0]
    at.session_state["store-hypothesis"] = {"text": hypothesis_build_sentence(first), "problem_title": first["title"]}
    at.run()
    check(not at.exception, "[직접 선택] 예외 없음")
    check(at.button(key="hypothesis-btn-save-0").label == "선택하기", "[직접 선택] 예전 저장값이 있어도 '선택됨' 자동 표시 안 함")
    check(at.button(key="hypothesis-btn-store").disabled, "[직접 선택] 고르기 전에는 '다음으로' 꺼짐")
    check(any("아직 선택한 가설이 없어요" in m.value for m in at.markdown), "[직접 선택] '지금 선택된 가설'도 비어 있음")
    at.button(key="hypothesis-btn-save-0").click().run()
    check(at.button(key="hypothesis-btn-save-0").label == "✓ 선택됨", "[직접 선택] 직접 고르면 '선택됨'")


if __name__ == "__main__":
    test_user_pick_only()
    test_core_flow()
    test_defensive()
    test_no_fixed_values()
    test_quality()
    test_deterministic()
    test_media_split_ready()
    test_candidate_action_diversity()
    test_save_report_plus_hypothesis()
    test_hypothesis_pdf()
    test_badge_group()
    test_real_report()

    print(f"\n총 {_ok + _fail}개 중 통과 {_ok}개, 실패 {_fail}개")
    if _fail:
        sys.exit(1)
    print("모두 통과했습니다.")
