# 2. 가설 수립 - 자체 테스트
#
# report(1번) 탭이 아직 없어도, hypothesis_page.py를 고칠 때마다 이 파일을 돌려서
# "이전에 잡았던 버그가 다시 생기지 않았는지"를 바로 확인할 수 있게 만든 회귀 테스트입니다.
# pytest 등 추가 라이브러리가 필요 없고, Streamlit에 내장된 streamlit.testing.v1.AppTest와
# 표준 라이브러리만 사용합니다.
#
# 실행 (프로젝트 맨 위 폴더에서):
#   python modules/hypothesis/hypothesis_test.py
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
    hypothesis_build_ibt,
    hypothesis_build_sentence,
    hypothesis_has_batchim,
    hypothesis_pick_action,
    hypothesis_pick_candidates,
    hypothesis_pick_problem,
    hypothesis_resolve_ibt,
    hypothesis_pick_sensitivity,
    hypothesis_resolve_sentence,
)
from modules.hypothesis.hypothesis_scenario import (  # noqa: E402
    hypothesis_scenario_ibt,
    hypothesis_scenario_problem2_ibt,
    hypothesis_scenario_problem2_sentence,
    hypothesis_scenario_sentence,
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


def _new_apptest() -> AppTest:
    """hypothesis_render()를 실제로 그려서 클릭/입력까지 흉내 낼 수 있는 AppTest를 만듭니다."""
    script = (
        "import sys\n"
        f"sys.path.insert(0, {str(ROOT_DIR)!r})\n"
        "from modules.hypothesis.hypothesis_page import hypothesis_render\n"
        "hypothesis_render()\n"
    )
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8")
    tmp.write(script)
    tmp.close()
    return AppTest.from_file(tmp.name)


# ─────────────────────────────────────────────
# 1. 핵심 흐름: 빈 상태 → 샘플 → 가설 1/2/3 탭(근거를 쭉 읽음) → 선택(저장) → 다른 후보로 재선택
#    (가설 문장을 따로 수정하는 칸은 없앴습니다 — 근거를 읽고 "이 가설 선택하기"만 누릅니다)
# ─────────────────────────────────────────────
def test_core_flow() -> None:
    at = _new_apptest()
    at.run()
    check(not at.exception, "[핵심] 1차 실행에 예외 없음")
    check(any("아직 분석된 문제가 없어요" in m.value for m in at.markdown), "[핵심] 리포트 없으면 empty 안내 표시")

    at.button(key="hypothesis-btn-sample").click().run()
    check(not at.exception, "[핵심] 샘플 클릭 후 예외 없음")
    # SAMPLE_REPORT 3문제 중 "경쟁사 가격 인하"/"장바구니 이탈 증가"는 사진·영상 결과물로
    # 바로 이어지는 액션(visual=True)이라 우선순위가 높고, "배송 지연 리뷰"(알림·쿠폰 액션,
    # visual=False)는 맨 뒤로 밀려서 가설 1=경쟁사 가격 인하, 가설 2=장바구니 이탈 증가,
    # 가설 3=배송 지연 리뷰 순서가 됩니다 (hypothesis_pick_candidates의 A/B 테스트 우선순위).
    check(any("경쟁사 가격 인하" in m.value for m in at.markdown), "[핵심] 가설 1(문제 1)의 제목이 표시됨 (A/B 테스트 우선순위)")
    check([t.label for t in at.tabs] == ["가설 1", "가설 2", "가설 3"], "[핵심] SAMPLE_REPORT 문제 3개가 가설 1/2/3 탭으로 뜸")
    check(
        any("아직 선택한 가설이 없어요" in m.value for m in at.markdown),
        "[핵심] 처음에는 '지금 선택된 가설' 칸이 비어있다고 안내함",
    )
    # 현지 특성/경쟁사 부정 리뷰 원문은 더 이상 캡션(📍/💬)으로 상시 노출되지 않고,
    # "📚 근거 · 출처 보기" 토글 안에 모여 있습니다(가설 문장을 짧고 읽기 좋게 하기 위함).
    evidence_labels = [e.label for e in at.get("expander") if "근거 · 출처" in e.label]
    check(len(evidence_labels) == 3, f"[핵심] 가설 후보마다 '근거·출처' 토글이 1개씩 뜸 (실제: {len(evidence_labels)}개)")
    check(
        any("가격 비교 사이트(idealo)" in m.value for m in at.markdown),
        "[핵심] 현지 특성 원문이 근거·출처 토글 안에 표시됨",
    )
    check(
        any("냉감 부족" in m.value for m in at.markdown),
        "[핵심] 경쟁사 부정 리뷰 원문이 근거·출처 토글 안에 표시됨",
    )
    check(
        sum("hypothesis-ibt-box" in m.value for m in at.markdown) == 3,
        "[핵심] 가설 후보마다 If · Because · Then 카드가 펼치지 않아도 바로 보임 (3개)",
    )
    check(
        [b.label for b in at.button if b.key and b.key.startswith("hypothesis-btn-save-")] == ["이 가설 선택하기"] * 3,
        "[핵심] 가설 후보마다 '이 가설 선택하기' 버튼 1개만 있음",
    )

    expected_text = hypothesis_build_sentence(SAMPLE_REPORT["problems"][0])   # 가설 1 = 경쟁사 가격 인하
    at.button(key="hypothesis-btn-save-0").click().run()
    check(at.button(key="hypothesis-btn-save-0").label == "✓ 선택됨", "[핵심] 선택 후 버튼 라벨 변경")
    check(at.button(key="hypothesis-btn-save-0").disabled, "[핵심] 이미 선택된 가설의 버튼은 다시 못 누르게 비활성화")
    saved = at.session_state["store-hypothesis"]
    check(isinstance(saved, dict), "[핵심] 저장된 hypothesis가 dict 1개 (배열 아님)")
    check(saved.get("hypothesis") == saved.get("text"), "[핵심] home_data.py가 기대하는 'hypothesis' 키도 같이 저장됨")
    check(saved.get("text") == expected_text, "[핵심] 저장된 문장이 hypothesis_build_sentence() 결과와 정확히 같음")
    # "지금 선택된 가설" 칸도 If·Because·Then 카드로 보이므로(요청 반영), 하나의 문장 대신
    # if_text/because_text/then_text가 각각 markdown에 그대로 보이는지 확인합니다.
    expected_ibt = hypothesis_build_ibt(SAMPLE_REPORT["problems"][0])
    check(
        any(expected_ibt["if"] in m.value for m in at.markdown)
        and any(expected_ibt["because"] in m.value for m in at.markdown)
        and any(expected_ibt["then"] in m.value for m in at.markdown),
        "[핵심] '지금 선택된 가설' 칸에 If·Because·Then 카드로 선택한 내용이 그대로 보임",
    )

    # 가설 2를 선택하면, "선택된 가설"이 가설 2로 바뀌고 가설 1의 버튼은 다시 "선택하기"로
    # 풀려야 함 (최종 저장은 항상 1개만 — 가설은 1개를 "고르는" 것이지 여러 개를 동시에 저장하지 않음)
    expected_text2 = hypothesis_build_sentence(SAMPLE_REPORT["problems"][2])   # 가설 2 = 장바구니 이탈 증가
    at.button(key="hypothesis-btn-save-1").click().run()
    check(at.button(key="hypothesis-btn-save-1").label == "✓ 선택됨", "[핵심] 가설 2를 선택하면 가설 2 버튼이 '선택됨'으로 바뀜")
    check(at.button(key="hypothesis-btn-save-0").label == "이 가설 선택하기", "[핵심] 가설 2를 선택하면 가설 1 버튼은 '선택됨'에서 풀림")
    saved2 = at.session_state["store-hypothesis"]
    check(saved2.get("text") == expected_text2, "[핵심] 최종 저장된 hypothesis가 가설 2 문장으로 바뀜 (가설은 항상 1개만 최종 저장)")


# ─────────────────────────────────────────────
# 2. 방어적 처리: report 모양이 이상해도 절대 죽지 않아야 함
# ─────────────────────────────────────────────
def test_defensive() -> None:
    bad_reports = [
        "이건 dict가 아니라 문자열",
        {"problems": {"title": "리스트가 아니라 dict"}},
        {"problems": ["문자열로만 이루어진 리스트"]},
        {"problems": []},
        {"problems": [{"title": 12345, "type": "내부", "detail": "제목이 숫자"}]},
    ]
    for bad_report in bad_reports:
        at = _new_apptest()
        at.session_state["store-report"] = bad_report
        at.run()
        check(not at.exception, f"[방어] report={bad_report!r} 에도 예외 없음")

    at = _new_apptest()
    at.session_state["store-report"] = {"problems": [{"title": "문제", "type": "내부", "detail": "설명"}]}
    at.session_state["store-hypothesis"] = "예전에 남은 이상한 값"
    at.run()
    check(not at.exception, "[방어] 저장된 hypothesis가 dict가 아니어도 예외 없음")
    check(at.button(key="hypothesis-btn-save-0").label == "이 가설 선택하기", "[방어] 이상한 저장값은 '선택됨'으로 치지 않음")


# ─────────────────────────────────────────────
# 3. home_data.py의 실제 샘플 데이터와 호환되는지 (교차 검증)
# ─────────────────────────────────────────────
def test_home_data_compat() -> None:
    # modules/home/home_data.py의 HOME_DEMO["report"]와 같은 모양 (팀원 담당 파일, 복사 금지라 값만 그대로 옮김)
    home_demo_report = {
        "yesterday_sales": 1284.0,
        "sales_delta": -0.18,
        "problems": [
            {"title": "장바구니 이탈 증가", "type": "내부", "detail": "결제 단계 이탈률 68% (+9%p). 배송비가 마지막 단계에 보이는 것이 원인으로 추정됩니다."},
            {"title": "경쟁사 가격 인하", "type": "외부", "detail": "경쟁사 B가 냉감패드 가격을 €39 → €29로 내렸습니다 (3일 전)."},
            {"title": "배송 지연 리뷰", "type": "내부", "detail": "최근 7일 부정 리뷰 12건 중 7건이 배송 지연을 언급했습니다."},
        ],
    }
    at = _new_apptest()
    at.session_state["store-report"] = home_demo_report
    at.run()
    check(not at.exception, "[호환] home_data.py의 실제 HOME_DEMO를 그대로 넣어도 예외 없음")
    check(
        any("장바구니" in m.value for m in at.markdown),
        "[호환] HOME_DEMO의 첫 번째 문제(장바구니 이탈)가 가설 1 제목으로 표시됨",
    )
    expected = hypothesis_build_sentence(home_demo_report["problems"][0])
    at.button(key="hypothesis-btn-save-0").click().run()
    saved = at.session_state["store-hypothesis"]
    check(saved.get("text") == expected, "[호환] 가설 1을 선택하면 장바구니 이탈 문제 기준 문장이 저장됨")


# ─────────────────────────────────────────────
# 4. 문장 품질 공통 체크 (길이/형식/문법/조사)
# ─────────────────────────────────────────────
def check_sentence_quality(label: str, s: str) -> None:
    check(bool(s) and s.strip() == s, f"[품질:{label}] 비어있지 않고 앞뒤 공백 없음")
    check(s.startswith("만약 "), f"[품질:{label}] '만약'으로 시작")
    check(s.endswith("것이다."), f"[품질:{label}] '것이다.'로 끝남")
    check(len(s) < 260, f"[품질:{label}] 길이가 적정함 ({len(s)}자, 260자 미만)")
    check(".로" not in s, f"[품질:{label}] '.로' 같은 이중 문장부호 비문이 없음")
    check(s.count("만약") == 1 and s.count("것이다") == 1, f"[품질:{label}] 템플릿 문구가 중복되지 않음")

    m = re.search(r"에 (.+?)(을|를) 적용한다면", s)
    check(bool(m), f"[품질:{label}] '~을/를 적용한다면' 패턴이 있음")
    if m:
        expected = "을" if hypothesis_has_batchim(m.group(1)) else "를"
        check(m.group(2) == expected, f"[품질:{label}] action 조사(을/를)가 받침 규칙과 일치")


# ─────────────────────────────────────────────
# 5. 실제로 겪었던 버그들의 회귀 테스트
# ─────────────────────────────────────────────
def test_regression_bugs() -> None:
    # "배송 지연 리뷰"(내부)가 '리뷰'라는 단어 때문에 경쟁사 대응으로 잘못 분류되면 안 됨
    action, _, _, _ = hypothesis_pick_action("최근 7일 부정 리뷰 12건 중 7건이 배송 지연을 언급했습니다.", False, "")
    check("배송" in action, "[회귀] 내부 '배송+리뷰' 설명은 배송 관련 액션으로 분류됨")
    check("경쟁사" not in action, "[회귀] 내부 문제는 '경쟁사' 대응 액션으로 가지 않음")

    # "장바구니 이탈" 설명에 "배송비"가 섞여 있어도 배송 액션으로 잘못 가면 안 됨
    action, _, _, _ = hypothesis_pick_action("결제 단계 이탈률 68%. 배송비가 마지막 단계에 보이는 것이 원인입니다.", False, "")
    check("장바구니" in action, "[회귀] 설명에 '배송비'가 섞여도 장바구니 관련 액션으로 분류됨")

    # 경쟁사와 무관한 외부 요인(구글 광고 등)을 "경쟁사 대비"라고 설명하면 안 됨
    s = hypothesis_pick_sensitivity("구글 쇼핑 광고를 통한 신규 방문자가 줄었습니다.", True, "")
    check(s == "외부 시장 상황", "[회귀] 경쟁사와 무관한 외부 요인은 '외부 시장 상황'으로 표현")

    # 설명이 "~했습니다."처럼 완결된 문장으로 끝나도 "습니다.로" 같은 비문이 생기면 안 됨
    s = hypothesis_build_sentence({"title": "t", "type": "내부", "detail": "문제가 발생했습니다."})
    check(".로" not in s, "[회귀] '~습니다.' 뒤에 이중 문장부호 비문이 생기지 않음")

    # competitor_review/local_context 원문을 통째로 인용해 문장이 너무 길어지면 안 됨 (textarea 안 보이던 버그)
    long_problem = {
        "title": "장기 체류 외국인 타깃 부족", "type": "외부",
        "detail": "베를린, 뮌헨 등 대도시의 장기 체류 외국인 커뮤니티를 타깃팅하는 광고가 거의 없습니다.",
        "local_context": "독일 대도시에는 영어를 쓰는 장기 체류 외국인 커뮤니티가 크고, 이들은 현지 결제수단과 리뷰를 영어로 찾아보는 경향이 뚜렷하며 가격보다 배송 신뢰도를 더 중요하게 생각하는 경향이 있음",
        "competitor_review": "경쟁사 영어 리뷰 페이지에 배송 추적이 안 된다는 불만과 고객센터가 독일어만 지원한다는 불만이 꾸준히 올라오고 있고 환불 절차가 느리다는 지적도 반복적으로 등장함",
    }
    s = hypothesis_build_sentence(long_problem)
    check(len(s) < 260, f"[회귀] 아주 긴 local_context/competitor_review가 들어와도 문장이 260자 미만으로 유지됨 ({len(s)}자)")

    # report(1번)가 실제로 모든 문제에 같은 competitor_review를 채워 보내서(실데이터 확인됨),
    # group이 "경쟁사"가 아닌 문제까지 전부 "경쟁사 부정 리뷰 대응"으로 잘못 나오던 버그.
    # (예: PayPal 결제 문제가 group="플랫폼"인데도 경쟁사 리뷰 대응 액션이 나왔던 실제 사례)
    same_competitor_review = (
        "Novilla Q-max 미공개 / RIBECO 냉감 성능 수치 근거 없음 · "
        "Amazon 평점 Novilla 3.6 (경쟁사 DB 약점, Keepa 평점)"
    )
    paypal_problem = {
        "title": "Amazon.de 일반 PayPal 결제 불가", "type": "외부", "group": "플랫폼",
        "detail": "Amazon.de는 일반 PayPal 결제를 받지 않습니다.",
        "competitor_review": same_competitor_review,
    }
    action, _, _, _ = hypothesis_pick_action(
        paypal_problem["detail"], True, same_competitor_review,
        paypal_problem["title"], paypal_problem["group"],
    )
    check("경쟁사 부정 리뷰" not in action, "[회귀] group이 '경쟁사'가 아니면 competitor_review가 있어도 경쟁사 리뷰 대응 액션으로 가지 않음")
    check("결제" in action, "[회귀] PayPal 결제 문제는 결제수단 지원 액션으로 분류됨")
    s = hypothesis_build_sentence(paypal_problem)
    check("경쟁사 부정 리뷰" not in s, "[회귀] hypothesis_build_sentence()도 group 기준으로 같은 competitor_review를 걸러냄")

    # group == "경쟁사"면 (키워드가 안 걸려도) 여전히 competitor_review를 액션에 반영해야 함
    action, _, _, _ = hypothesis_pick_action(
        "90일 평균 €29.41 → 현재 €25.66", True, same_competitor_review,
        "Novilla 가격 13% 인하", "경쟁사",
    )
    check("경쟁사 부정 리뷰" in action, "[회귀] group='경쟁사'면 competitor_review가 액션에 반영됨")


# ─────────────────────────────────────────────
# 6. 가설은 "1번 분석 결과에서 나온 답 1개"여야 하므로, 같은 문제면 항상 같은 문장이어야 함
#    (예전에는 "다시 생성"이 무작위로 다른 문구를 주게 만들었는데, "분석 결과 → 최적 가설 1개"
#    라는 전제와 맞지 않아서 되돌림. 대신 "↺ 자동 생성 문장으로 되돌리기"로 바꿔서, 손으로
#    고친 내용을 원래 문장으로 되돌리는 용도로만 씁니다)
# ─────────────────────────────────────────────
def test_deterministic() -> None:
    problem = SAMPLE_REPORT["problems"][0]   # competitor_review가 있는 문제
    seen = {hypothesis_build_sentence(problem) for _ in range(20)}
    check(
        len(seen) == 1,
        f"[결정성] 같은 문제를 20번 생성해도 항상 같은 문장 1개만 나옴 (실제로 나온 종류: {len(seen)}) "
        "- 가설은 '분석 결과에서 나온 답 1개'여야 하므로 무작위 요소가 있으면 안 됨",
    )

    # 어떤 설명을 넣어도(키워드가 하나도 안 걸려도) action/amount는 항상 나와야 함
    for desc in ["", "아무 키워드도 없는 설명입니다", "배송 이탈 장바구니 리뷰 품질 환율"]:
        action, amount, _, _ = hypothesis_pick_action(desc, False, "")
        check(bool(action) and bool(amount), f"[결정성] desc={desc!r} 에도 action/amount가 항상 나옴")
        action2, amount2, _, _ = hypothesis_pick_action(desc, False, "")
        check((action, amount) == (action2, amount2), f"[결정성] desc={desc!r} 를 두 번 불러도 결과가 같음")


# ─────────────────────────────────────────────
# 7. 현실적인 시나리오 20개 (MODO 독일 냉감패드 사업 기준)
#    report(1번) 탭이 아직 없어서 실제 데이터로 검증할 수 없으므로,
#    1번이 실제로 만들어지면 나올 법한 문제들을 폭넓게 만들어 대신 검증합니다.
# ─────────────────────────────────────────────
REALISTIC_PROBLEMS = [
    {
        "title": "경쟁사 가격 인하", "type": "외부",
        "detail": "경쟁사 B가 냉감패드 가격을 €39 → €29로 내렸습니다 (3일 전).",
        "target": "Amazon.de 독일 2030 구매자", "metric": "전환율",
        "local_context": "독일은 가격 비교 사이트(idealo)를 많이 쓰는 시장",
        "competitor_review": "경쟁 브랜드에 '냉감 부족' 부정 리뷰 다수",
    },
    {
        "title": "배송 지연 리뷰", "type": "내부",
        "detail": "최근 7일 부정 리뷰 12건 중 7건이 배송 지연을 언급했습니다.",
        "target": "München, Berlin 대도시 고객", "metric": "재구매율",
    },
    {
        "title": "장바구니 이탈 증가", "type": "내부",
        "detail": "결제 단계 이탈률 68% (+9%p). 배송비가 마지막 단계에 보이는 것이 원인으로 추정됩니다.",
        "target": "장바구니에 상품을 담은 전체 고객", "metric": "결제 완료율",
    },
    {
        "title": "폭염 특보 중 품절", "type": "내부",
        "detail": "München 지역 폭염 특보 발령 중 베스트셀러 색상이 품절됐습니다.",
        "target": "München, Stuttgart 거주 고객", "metric": "재고 회전율",
    },
    {
        "title": "신규 고객 유입 저조", "type": "외부",
        "detail": "구글 쇼핑 광고를 통한 신규 방문자가 지난달보다 20% 줄었습니다.",
        "target": "신규 방문 독일 고객", "metric": "신규 가입률",
    },
    {
        "title": "재구매 고객 비율 하락", "type": "내부",
        "detail": "최근 90일 재구매 고객 비율이 18%에서 11%로 떨어졌습니다.",
        "target": "첫 구매 후 90일 이내 고객", "metric": "재구매율",
    },
    {
        "title": "환율 변동으로 가격 경쟁력 하락", "type": "외부",
        "detail": "원/유로 환율 상승으로 실질 판매가가 경쟁사 대비 높아졌습니다.",
        "target": "독일 전체 온라인 구매자", "metric": "평균 판매가",
    },
    {
        "title": "제품 품질 불만", "type": "내부",
        "detail": "지난달 대비 품질 관련 1점 평가가 늘었습니다.",
        "target": "구매 후 2주 이내 고객", "metric": "평균 평점",
    },
    {
        "title": "SNS 바이럴 효과 미흡", "type": "외부",
        "detail": "인스타그램 캠페인 참여율이 업계 평균보다 낮습니다.",
        "target": "18~24세 독일 Z세대", "metric": "참여율",
    },
    {
        "title": "반품률 증가", "type": "내부",
        "detail": "최근 한 달 반품률이 3.2%에서 5.1%로 늘었습니다.",
        "target": "최근 1개월 구매 고객", "metric": "반품률",
    },
    {
        "title": "모바일 결제 이탈", "type": "내부",
        "detail": "모바일에서 결제 수단 선택 단계 이탈이 데스크톱보다 높습니다.",
        "target": "모바일로 접속하는 고객", "metric": "모바일 결제 완료율",
    },
    {
        "title": "경쟁사 신제품 출시", "type": "외부",
        "detail": "경쟁사가 한국 시장형 냉감 소재를 적용한 신제품을 출시했습니다.",
        "target": "소재 비교 후기를 찾아보는 구매자", "metric": "전환율",
        "competitor_review": "신제품 리뷰에 '우리 제품보다 시원하다'는 평가 다수",
    },
    {
        "title": "현지 결제수단 미지원", "type": "내부",
        "detail": "Klarna, Sofort 같은 독일 선호 결제수단을 아직 지원하지 않습니다.",
        "target": "결제 단계에서 이탈하는 고객", "metric": "결제 전환율",
        "local_context": "독일은 신용카드보다 Klarna 같은 후불 결제를 선호하는 시장",
    },
    {
        "title": "Returning customer CVR drop", "type": "internal",   # 영어 type은 '외부'로 안 잡혀야 함
        "detail": "Conversion rate for returning visitors dropped 4%p this month.",
        "target": "EU returning visitors", "metric": "CVR",
    },
    {
        "title": "고객센터 응답 지연", "type": "내부",
        "detail": "평균 응답 시간이 24시간에서 48시간으로 늘었습니다.",
        # target/metric 전부 없음 (최소 정보)
    },
    {
        "title": "폭염 예보 대비 광고 부족", "type": "내부",
        "detail": "다음 주 전국 폭염 예보인데 광고 노출 빈도가 평소와 같습니다.",
        "target": "폭염 지역 거주 고객", "metric": "광고 클릭률",
    },
    {
        "title": "가격 민감 구간 이탈", "type": "외부",
        "detail": "€30 이상 구간에서 이탈률이 높습니다.",
        "local_context": "가격 민감 시장",
        "competitor_review": "경쟁사 리뷰 '비싸다' 다수",
    },
    {
        "title": "장기 체류 외국인 타깃 부족", "type": "외부",
        "detail": "베를린, 뮌헨 등 대도시의 장기 체류 외국인 커뮤니티를 타깃팅하는 광고가 거의 없습니다.",
        "target": "베를린·뮌헨 장기 체류 외국인", "metric": "노출 대비 전환율",
        "local_context": "독일 대도시에는 영어를 쓰는 장기 체류 외국인 커뮤니티가 크고, 이들은 현지 결제수단과 리뷰를 영어로 찾아보는 경향이 뚜렷함",
        "competitor_review": "경쟁사 영어 리뷰 페이지에 배송 추적이 안 된다는 불만과 고객센터가 독일어만 지원한다는 불만이 반복됨",
    },
    {
        "title": "전반적 브랜드 인지도 부족", "type": "외부",
        "detail": "설문 조사 결과 브랜드 인지도가 경쟁사 대비 낮게 나타났습니다.",
        "target": "냉감패드 구매를 고려하는 전체 독일 소비자", "metric": "브랜드 인지도",
    },
    {
        "title": "할인 쿠폰 사용률 저조", "type": "내부",
        "target": "쿠폰을 받은 전체 고객", "metric": "쿠폰 사용률",
        # detail 없음 (title로 대체돼야 함)
    },
]


# ─────────────────────────────────────────────
# 7-1. report(1번)의 실제 competitor_review 전역 중복 이슈를 겪은 뒤 새로 추가한 카테고리들
#      (modules/report/report_competitor.py가 실제로 만들어 보내는 group/제목 패턴 기준)
# ─────────────────────────────────────────────
NEW_CATEGORY_PROBLEMS = [
    {"title": "출시 필수 인증·규제 6건 미착수", "type": "내부", "group": "인증·규제",
     "detail": "OEKO-TEX Standard 100 등 인증이 아직 없습니다.", "expect": "인증"},
    {"title": "완제품 시험 7건 결과 없음", "type": "내부", "group": "시험",
     "detail": "접촉냉감 Q-max 시험값이 없습니다.", "expect": "시험"},
    {"title": "판매 채널 2개 (경쟁사 최다 5개)", "type": "내부", "group": "채널",
     "detail": "Amazon.de, 자사몰 외 채널이 없습니다.", "expect": "채널"},
    {"title": "리뷰 0건 (신규 브랜드)", "type": "내부", "group": "신뢰",
     "detail": "경쟁사 Novilla 310건 대비 리뷰가 없습니다.", "expect": "신뢰"},
    {"title": "10월 비시즌 (여름 전용 제품)", "type": "외부", "group": "날씨",
     "detail": "수요는 열대야가 많은 6~8월에 집중됩니다.", "expect": "비수기"},
    {"title": "㎡당 가격이 최저가 경쟁사의 5.5배", "type": "내부", "group": "가격",
     "detail": "서리 €44.4 vs Novilla €8.0.", "expect": "가격"},
]


def test_new_categories() -> None:
    for p in NEW_CATEGORY_PROBLEMS:
        action, _, _, _ = hypothesis_pick_action(
            p["detail"], p["type"] == "외부", "", p["title"], p["group"],
        )
        check(p["expect"] in action, f"[신규카테고리:{p['title']}] 기대 키워드 '{p['expect']}'가 액션에 들어감 (실제: {action})")
        s = hypothesis_build_sentence(p)
        check_sentence_quality(p["title"], s)


# ─────────────────────────────────────────────
# 7-2. 검색어 클릭 문제(시나리오) 섹션: 팀원이 추가한 hypothesis_scenario.py가
#      report["sqp"]가 있을 때 예외 없이 접기(expander) 구조로 뜨는지, 버튼 글씨
#      안 보임 버그(hypothesis_style.css)가 같이 수정됐는지 확인
# ─────────────────────────────────────────────
SQP_SAMPLE = {
    "query": "kühlende matratzenauflage", "ratio": 0.63, "kpi_goal": 0.8,
    "source": "검색 클릭 가상 SQP", "cart_rate_ours": 16.4, "cart_rate_market": 17.1,
    "price_gap": 5, "listing": {"main_image": "위에서 찍은 사진", "price": 64.99},
    "problem2": {"heat_temp": 28, "query": "kühlmatte bett", "imp_share": 6.9,
                 "goal_imp_share": 9.0, "month": "6월", "extra_clicks": 265},
}


def test_scenario_section() -> None:
    # SAMPLE_REPORT 문제들은 sqp_type이 없어서 이 sqp와 무관함 → 그래도 가설 후보마다
    # If·Because·Then 카드는 뜨되(hypothesis_generic_evidence_section, 규칙 기반 근거 —
    # 펼치지 않아도 바로 보이는 형태), sqp 전용 "KPI 표" expander는 뜨면 안 됨
    # (엉뚱한 근거를 끌어오지 않음)
    report = dict(SAMPLE_REPORT)
    report["sqp"] = SQP_SAMPLE
    at = _new_apptest()
    at.session_state["store-report"] = report
    at.run()
    check(not at.exception, "[시나리오] sqp가 있는 report를 넣어도 예외 없음")
    md_values = [m.value for m in at.markdown]
    check(
        sum("hypothesis-ibt-box" in v for v in md_values) == len(SAMPLE_REPORT["problems"]),
        f"[시나리오] 모든 가설 후보에 If·Because·Then 카드가 하나씩 바로 뜸 (실제: {sum('hypothesis-ibt-box' in v for v in md_values)}개)",
    )
    expander_labels = [e.label for e in at.get("expander")]
    check(
        not any("KPI 표" in lb for lb in expander_labels),
        "[시나리오] 어떤 가설 후보도 이 sqp와 무관하면 sqp 전용 'KPI 표' expander는 안 뜸 (엉뚱한 근거 섞임 방지)",
    )
    check(
        not any("대안 가설" in v for v in md_values),
        "[시나리오] '대안 가설 보기' 섹션은 제거됨",
    )

    s = hypothesis_scenario_sentence(SQP_SAMPLE)
    check(s.startswith("만약 ") and s.endswith("것이다."), "[시나리오] 소재 개선 가설 문장도 '만약~것이다.' 템플릿을 따름")
    s2 = hypothesis_scenario_problem2_sentence(SQP_SAMPLE["problem2"])
    check(s2.startswith("만약 ") and s2.endswith("것이다."), "[시나리오] 노출 확대 가설 문장도 '만약~것이다.' 템플릿을 따름")

    # report에 sqp가 없어도(일반적인 경우) 가설 후보마다 규칙 기반 If·Because·Then 카드는 그대로 바로 보임
    at2 = _new_apptest()
    at2.session_state["store-report"] = SAMPLE_REPORT
    at2.run()
    check(not at2.exception, "[시나리오] sqp가 없는 report는 예외 없음")
    md_values2 = [m.value for m in at2.markdown]
    check(
        sum("hypothesis-ibt-box" in v for v in md_values2) == len(SAMPLE_REPORT["problems"]),
        "[시나리오] sqp가 없어도 가설 후보마다 규칙 기반 If·Because·Then 카드는 그대로 바로 보임",
    )


# ─────────────────────────────────────────────
# 7-3. 실제 report가 "검색어 클릭 문제"를 problems[0]으로 보내면서(report_sqp.py) 드러난 버그:
#      그 문제에 대해 hypothesis_page.py가 키워드만 보고 다시(더 부정확하게) 가설을 만들어
#      hypothesis_scenario.py의 "문제 1 가설" 카드와 서로 다른 문장 2개가 동시에 보였음.
#      "가설은 항상 1개"여야 하므로, sqp가 있으면 그 쪽 문장을 그대로 유일한 답으로 써야 함.
# ─────────────────────────────────────────────
SQP_MAIN_PROBLEM = {
    "title": "'kühlende matratzenauflage' 검색에서 보이는 만큼 안 눌림 (클릭 ÷ 노출 0.63배)",
    "type": "내부", "level": "높음", "group": "검색 클릭",
    "detail": "검색량이 가장 많은 'kühlende matratzenauflage'에서 노출 점유율 9.0%에 비해 클릭 점유율이 5.7%였다.",
    "target": "amazon.de 'kühlende matratzenauflage' 검색 결과",
    "metric": "클릭 점유율 ÷ 노출 점유율",
    "local_context": "온라인 쇼핑객의 54%가 구매 전 리뷰를 확인한다 (2021). (독일 DB SHP-006)",
    "competitor_review": "Novilla Q-max 미공개 (경쟁사 DB 약점, 실제 리뷰 원문 아님)",
    "sqp_type": "소재 개선", "query": "kühlende matratzenauflage",
}
SQP_INTENT_MISMATCH_PROBLEM = {
    "title": "'kühltopper'는 검색 의도가 다름 (클릭된 상품 중앙 가격 €79.99)",
    "type": "내부", "level": "중간", "group": "검색 클릭",
    "detail": "배수 1.8배지만 클릭된 상품이 우리보다 €30 비싼 두꺼운 토퍼라 가설 없이 광고 제외 키워드로 처리 (가상 SQP)",
    "sqp_type": "제외 검토", "query": "kühltopper",
}


SQP_EXPANSION_PROBLEM = {
    "title": "'kühlmatte bett'는 잘 눌리는데 덜 보임 (노출 점유율 6.9%, 배수 1.27배)",
    "type": "내부", "level": "중간", "group": "검색 클릭",
    "detail": "노출 점유율을 9%로 올리면 6월에만 약 265회 클릭 증가 예상. 소재보다 광고 예산 문제라 소재 외 문제로 분류 (가상 SQP)",
    "sqp_type": "노출 확대", "query": "kühlmatte bett",
}


def test_sqp_single_hypothesis() -> None:
    sqp_store = SQP_SAMPLE | {"query": "kühlende matratzenauflage", "ratio": 0.63, "kpi_goal": 0.8}

    # (1) sqp 쿼리가 일치하면("소재 개선"), 규칙 기반으로 다시 만들지 않고
    # hypothesis_scenario_sentence()를 그대로 씀
    resolved = hypothesis_resolve_sentence(SQP_MAIN_PROBLEM, sqp_store)
    check(
        resolved == hypothesis_scenario_sentence(sqp_store),
        "[시나리오 통합] sqp가 일치하면 hypothesis_scenario.py의 문장을 그대로 유일한 가설로 씀 (키워드 기반 재생성 안 함)",
    )
    rule_based = hypothesis_build_sentence(SQP_MAIN_PROBLEM)
    check(
        resolved != rule_based,
        "[시나리오 통합] (참고) 키워드 기반 문장과는 실제로 다름 — 그래서 둘 다 보이면 '가설 2개'처럼 보였던 것",
    )

    # (1-1) "노출 확대" 문제도 sqp["problem2"]와 쿼리가 일치하면 그 전용 문장을 그대로 씀
    resolved2 = hypothesis_resolve_sentence(SQP_EXPANSION_PROBLEM, sqp_store)
    check(
        resolved2 == hypothesis_scenario_problem2_sentence(sqp_store["problem2"]),
        "[시나리오 통합] '노출 확대' 문제도 sqp.problem2가 일치하면 그 전용 문장을 그대로 유일한 가설로 씀",
    )

    # (2) sqp가 없거나 쿼리가 다른 문제면, 평소처럼 규칙 기반으로 만듦 (하위 호환)
    check(
        hypothesis_resolve_sentence(SQP_MAIN_PROBLEM, None) == rule_based,
        "[시나리오 통합] sqp가 없으면 평소처럼 규칙 기반 문장을 씀",
    )
    other_sqp = SQP_SAMPLE | {"query": "다른 검색어"}
    check(
        hypothesis_resolve_sentence(SQP_MAIN_PROBLEM, other_sqp) == rule_based,
        "[시나리오 통합] sqp의 query가 문제의 query와 다르면 규칙 기반 문장을 씀 (엉뚱한 근거를 끌어오지 않음)",
    )

    # (3) '검색 클릭' 문제도 (sqp 없이) 규칙 기반만으로 만들 때, 더 이상 안 맞는 기본값(타깃 맞춤
    # 프로모션)이 아니라 그럴듯한 액션이 나와야 함 (sqp_type별)
    action, _, _, _ = hypothesis_pick_action(
        SQP_MAIN_PROBLEM["detail"], False, "", SQP_MAIN_PROBLEM["title"], "검색 클릭",
    )
    check("메인 이미지" in action, "[시나리오 통합] '안 눌림'(소재 개선) 문제는 메인 이미지 관련 액션으로 분류됨")

    # (4) report_sqp.py가 "가설 없이 광고 제외 키워드로 처리"라고 명시한 문제(검색 의도 다름)는
    # 후보 목록에서 아예 빠져야 함 (hypothesis_pick_problem/candidates 둘 다 확인)
    report = {"problems": [SQP_INTENT_MISMATCH_PROBLEM, SQP_MAIN_PROBLEM]}
    picked = hypothesis_pick_problem(report)
    check(
        picked is not None and picked.get("title") == SQP_MAIN_PROBLEM["title"],
        "[시나리오 통합] '가설 없이' 문제가 맨 앞이어도 건너뛰고 다음 문제를 고름",
    )
    candidates = hypothesis_pick_candidates(report)
    check(
        all("가설 없이" not in str(c.get("detail") or "") for c in candidates),
        "[시나리오 통합] 가설 후보 목록에도 '가설 없이' 문제는 전혀 안 들어감",
    )

    # (5) 화면 전체로도 확인: problems[0]이 sqp와 정확히 일치하는 실제 report 모양을 넣으면,
    # 가설 1·2를 각각 선택했을 때 hypothesis_scenario_sentence()/_problem2_sentence()와
    # 정확히 같은 문장이 저장되고(화면에는 가설 문장 자체가 아니라 근거 표만 바로 보임),
    # sqp 전용 'KPI 표' expander는 소재 개선(가설 1) 탭에만 뜸
    report_full = {"problems": [SQP_MAIN_PROBLEM, SQP_EXPANSION_PROBLEM], "sqp": sqp_store}
    at = _new_apptest()
    at.session_state["store-report"] = report_full
    at.run()
    check(not at.exception, "[시나리오 통합] 실제 모양(검색 클릭 문제 2개 + 일치하는 sqp)을 넣어도 예외 없음")

    at.button(key="hypothesis-btn-save-0").click().run()
    saved = at.session_state["store-hypothesis"]
    check(saved.get("text") == resolved, "[시나리오 통합] 가설 1을 선택하면 hypothesis_scenario_sentence()와 정확히 같은 문장이 저장됨")

    at.button(key="hypothesis-btn-save-1").click().run()
    saved2 = at.session_state["store-hypothesis"]
    check(saved2.get("text") == resolved2, "[시나리오 통합] 가설 2를 선택하면 hypothesis_scenario_problem2_sentence()와 정확히 같은 문장이 저장됨")

    expander_labels = [e.label for e in at.get("expander")]
    check(
        sum("KPI 표" in lb for lb in expander_labels) == 1,
        f"[시나리오 통합] sqp 전용 'KPI 표' expander는 소재 개선(가설 1) 탭에만 1개 뜸 (실제: {sum('KPI 표' in lb for lb in expander_labels)}개)",
    )
    # 가설 1·2 탭에 각각 If·Because·Then 카드가 하나씩(2개) + 방금 선택한 가설 2가 맨 위
    # "지금 선택된 가설" 칸에도 같은 카드로 보이므로(+1개) 총 3개가 뜸
    md_values = [m.value for m in at.markdown]
    check(
        sum("hypothesis-ibt-box" in v for v in md_values) == 3,
        f"[시나리오 통합] 가설 1·2 탭(2개) + 선택된 가설 칸(1개), 총 3개의 If·Because·Then 카드가 뜸 (실제: {sum('hypothesis-ibt-box' in v for v in md_values)}개)",
    )


def test_realistic_sweep() -> None:
    for p in REALISTIC_PROBLEMS:
        try:
            s = hypothesis_build_sentence(p)
        except Exception as e:  # noqa: BLE001 - 테스트에서는 어떤 예외든 실패로 기록
            check(False, f"[실전:{p['title']}] 예외 발생: {e}")
            continue
        check_sentence_quality(p["title"], s)

    # 내부 문제인데 '리뷰'가 섞여 있어도 "경쟁사" 대응 문구가 안 나와야 하는 것들 재확인 (회귀)
    for p in REALISTIC_PROBLEMS:
        if p["type"] != "외부" and "리뷰" in p.get("detail", ""):
            s = hypothesis_build_sentence(p)
            check("독일 경쟁사" not in s, f"[실전:{p['title']}] 내부 문제는 '독일 경쟁사' 대응 문구가 안 들어감")


if __name__ == "__main__":
    test_core_flow()
    test_defensive()
    test_home_data_compat()
    test_regression_bugs()
    test_deterministic()
    test_new_categories()
    test_scenario_section()
    test_sqp_single_hypothesis()
    test_realistic_sweep()

    print(f"\n총 {_ok + _fail}개 중 통과 {_ok}개, 실패 {_fail}개")
    if _fail:
        sys.exit(1)
    print("모두 통과했습니다.")
