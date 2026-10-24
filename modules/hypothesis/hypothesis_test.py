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
    hypothesis_build_sentence,
    hypothesis_has_batchim,
    hypothesis_pick_action,
    hypothesis_pick_sensitivity,
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
# 1. 핵심 흐름: 빈 상태 → 샘플 → 생성 → 저장 → 수정 → 되돌리기
# ─────────────────────────────────────────────
def test_core_flow() -> None:
    at = _new_apptest()
    at.run()
    check(not at.exception, "[핵심] 1차 실행에 예외 없음")
    check(any("아직 분석된 문제가 없어요" in m.value for m in at.markdown), "[핵심] 리포트 없으면 empty 안내 표시")

    at.button(key="hypothesis-btn-sample").click().run()
    check(not at.exception, "[핵심] 샘플 클릭 후 예외 없음")
    check(any("경쟁사 가격 인하" in m.value for m in at.markdown), "[핵심] 문제 제목(problems[0])이 표시됨")

    draft = at.text_area(key="hypothesis-draft-text").value
    check(bool(draft), "[핵심] 가설 문장이 비어있지 않음")
    check(len(draft) < 260, f"[핵심] 가설 문장 길이가 적정함 ({len(draft)}자)")
    check("Amazon.de" in draft, "[핵심] target이 문장에 들어감")
    check(any("📍" in m.value and "현지 특성" in m.value for m in at.markdown), "[핵심] 현지 특성 줄 표시")
    check(any("💬" in m.value and "경쟁사 부정 리뷰" in m.value for m in at.markdown), "[핵심] 경쟁사 부정 리뷰 줄 표시")

    at.button(key="hypothesis-btn-save").click().run()
    check(at.button(key="hypothesis-btn-save").label == "✓ 저장됨", "[핵심] 저장 후 버튼 라벨 변경")
    saved = at.session_state["store-hypothesis"]
    check(isinstance(saved, dict), "[핵심] 저장된 hypothesis가 dict 1개 (배열 아님)")
    check(saved.get("hypothesis") == saved.get("text"), "[핵심] home_data.py가 기대하는 'hypothesis' 키도 같이 저장됨")

    at.text_area(key="hypothesis-draft-text").set_value("   ").run()
    check(at.button(key="hypothesis-btn-save").disabled, "[핵심] 공백만 입력하면 저장 버튼 비활성화")

    at.text_area(key="hypothesis-draft-text").set_value("수정된 문장 테스트").run()
    check(at.button(key="hypothesis-btn-save").label == "가설 저장", "[핵심] 다시 수정하면 저장 버튼 활성화")
    check(at.text_area(key="hypothesis-draft-text").value != draft, "[핵심] 직접 수정하면 원래 자동 생성 문장과 달라짐")

    # "↺ 자동 생성 문장으로 되돌리기" 버튼: 다른 안을 보여주는 게 아니라, 손으로 고친 내용을
    # 원래 자동 생성 문장(draft)으로 되돌리는 용도입니다 (1번 분석 결과 = 가설 1개라는 전제와 일치).
    at.button(key="hypothesis-btn-reset").click().run()
    check(not at.exception, "[핵심] 되돌리기 클릭 후 예외 없음 (StreamlitWidgetAlreadyInstantiatedError 재발 방지)")
    check(at.text_area(key="hypothesis-draft-text").value == draft, "[핵심] 되돌리기를 누르면 수정 전 자동 생성 문장과 정확히 같아짐")


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
    check(at.button(key="hypothesis-btn-save").label == "가설 저장", "[방어] 이상한 저장값은 '저장됨'으로 치지 않음")


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
    draft = at.text_area(key="hypothesis-draft-text").value
    check("장바구니" in draft or "배송비" in draft, "[호환] HOME_DEMO의 첫 번째 문제(장바구니 이탈) 기준으로 생성됨")


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
    action, _ = hypothesis_pick_action("최근 7일 부정 리뷰 12건 중 7건이 배송 지연을 언급했습니다.", False, "")
    check("배송" in action, "[회귀] 내부 '배송+리뷰' 설명은 배송 관련 액션으로 분류됨")
    check("경쟁사" not in action, "[회귀] 내부 문제는 '경쟁사' 대응 액션으로 가지 않음")

    # "장바구니 이탈" 설명에 "배송비"가 섞여 있어도 배송 액션으로 잘못 가면 안 됨
    action, _ = hypothesis_pick_action("결제 단계 이탈률 68%. 배송비가 마지막 단계에 보이는 것이 원인입니다.", False, "")
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
        action, amount = hypothesis_pick_action(desc, False, "")
        check(bool(action) and bool(amount), f"[결정성] desc={desc!r} 에도 action/amount가 항상 나옴")
        action2, amount2 = hypothesis_pick_action(desc, False, "")
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
    test_realistic_sweep()

    print(f"\n총 {_ok + _fail}개 중 통과 {_ok}개, 실패 {_fail}개")
    if _fail:
        sys.exit(1)
    print("모두 통과했습니다.")
