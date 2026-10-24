# 2. 가설 수립
from pathlib import Path

import streamlit as st

import ui_theme as ui
from common.common_store import store_get, store_set

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
        },
        {
            "title": "배송 지연 리뷰",
            "type": "내부",
            "detail": "최근 7일 부정 리뷰 12건 중 7건이 배송 지연을 언급했습니다.",
            "target": "München, Berlin 등 대도시 재구매 고객",
            "metric": "재구매율",
        },
        {
            "title": "장바구니 이탈 증가",
            "type": "내부",
            "detail": "결제 단계 이탈률 68% (+9%p). 배송비가 마지막 단계에 보이는 것이 원인으로 추정됩니다.",
            "target": "장바구니에 상품을 담은 독일 전체 고객",
            "metric": "결제 완료율",
        },
    ],
}


def hypothesis_has_batchim(word: str) -> bool:
    """마지막 글자에 받침이 있는지 (조사 이/가, 을/를을 고를 때 씀)"""
    word = (word or "").strip()
    if not word:
        return False
    code = ord(word[-1]) - 0xAC00
    if code < 0 or code > 11171:
        return False   # 한글 음절이 아니면 받침 없는 걸로 취급
    return code % 28 != 0


def hypothesis_particle(word: str, with_batchim: str, without_batchim: str) -> str:
    return with_batchim if hypothesis_has_batchim(word) else without_batchim


def hypothesis_shorten(text: str, limit: int = 40) -> str:
    """가설 문장 안에 끼워 넣을 때 너무 길어지지 않게 자릅니다.
    원문 전체는 이미 화면에 별도 줄(📍 현지 특성 / 💬 경쟁사 부정 리뷰)로 보여주므로,
    가설 문장 안에서는 짧게만 인용합니다."""
    text = str(text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def hypothesis_pick_action(
    desc: str,
    is_external: bool,
    competitor_review: str,
    title: str = "",
    group: str = "",
) -> tuple[str, str]:
    """문제 제목(title)·설명(desc)을 보고 액션 문구와 목표 변화량(%)을 고릅니다. 같은 입력이면
    항상 같은 결과를 돌려줍니다 (무작위 요소 없음) — 분석 결과에서 나온 "하나의 가설"이라는
    전제와 맞게, 같은 문제에 대해 여러 후보 중 하나를 고르는 게 아니라 항상 같은 답을 내야
    하기 때문입니다.
    action은 "~을 적용한다면"에 자연스럽게 붙도록 항상 명사형으로 끝냅니다
    (예: "노출한다"처럼 완결된 문장으로 끝내면 "노출한다을 적용한다면"처럼 비문이 됩니다).

    group: report가 문제 분류(예: "경쟁사", "날씨")를 같이 주면 그걸 우선 씁니다. 없으면(예: 샘플
    데이터) is_external로 대신 판단합니다. (실제 데이터로 검증하며 추가 — 아래 참고)
    """
    # title + detail을 합쳐서 찾습니다. detail은 수치·인용 위주라 키워드가 없을 때가 많고,
    # title이 오히려 더 핵심 키워드(인증, 시험, 채널 등)를 담고 있는 경우가 많습니다.
    search = f"{title} {desc}"
    action = "타깃 맞춤 프로모션 집중 노출"
    amount = "8%" if is_external else "10%"

    # "경쟁사" 그룹일 때만(그룹 정보가 없으면 외부 요인일 때만) competitor_review를 액션에 반영합니다.
    # report가 모든 문제에 같은 competitor_review를 채워 보낼 수도 있어서(실제로 그렇습니다),
    # "값이 있으면 무조건 최우선"으로 두면 PayPal 결제 문제 같은 것도 "경쟁사 리뷰 대응"으로
    # 잘못 나옵니다. 그 문제가 진짜 경쟁사 비교 문제일 때만 쓰도록 좁힙니다.
    is_competitor_problem = (group == "경쟁사") if group else is_external
    if competitor_review and is_competitor_problem:
        review_short = hypothesis_shorten(competitor_review, 26)
        action = f'"{review_short}" 등 독일 경쟁사 부정 리뷰 대응 홍보 콘텐츠 노출'
        amount = "8%"
    # "이탈/장바구니"를 "배송"보다 먼저 확인합니다. "장바구니 이탈" 문제의 설명 안에도
    # "배송비" 같은 단어가 곁다리로 섞여 있을 수 있는데, 그런 경우까지 "배송 지연" 액션으로
    # 잘못 분류되지 않도록 더 구체적인 키워드(이탈/장바구니)를 우선합니다.
    elif "이탈" in search or "장바구니" in search:
        action = "장바구니 단계에서 배송비를 미리 안내하는 화면 노출"
        amount = "9%"
    # ("배송 지연 리뷰"처럼 설명에 "리뷰"가 섞여 있어도, 내부 문제면 경쟁사 리뷰 대응이 아니라
    # 그 내부 문제에 맞는 액션을 고르기 위해 "배송"을 "리뷰" 체크보다 먼저 둡니다.
    # "물류"도 배송과 이어지는 문제라 같이 묶습니다 — 예: "독일 물류 거점 없음")
    elif "배송" in search or "물류" in search:
        action = "배송 현황을 안내하는 알림과 배송 지연 보상 쿠폰 제공"
        amount = "10%"
    elif "품절" in search or "재고" in search:
        action = "품절 임박 상품 묶음 할인 우선 노출"
        amount = "10%"
    # "비시즌/열대야"처럼 계절·시기 문제는 지금 날씨가 아니라 "비수기"라는 뜻이라
    # 날씨 카테고리와 액션을 다르게 둡니다 (광고 빈도 조정이 아니라 비수기 수요 평준화).
    elif any(w in search for w in ("비시즌", "비수기", "열대야", "성수기")):
        action = "비수기 전용 번들·선주문 프로모션으로 수요 평준화"
        amount = "10%"
    elif any(w in search for w in ("날씨", "폭염", "한파", "우천")):
        action = "날씨 상황에 맞춘 광고 노출 빈도 자동 조정"
        amount = "15%"
    # "신뢰"(리뷰가 아예 없는 신규 브랜드 등)는 "신규 고객 유입"과는 다른 문제라
    # (유입은 이미 되는데 신뢰가 없어서 전환이 안 되는 경우) 따로 둡니다.
    elif "신뢰" in search or "리뷰 0" in search:
        action = "체험단·얼리버드 리뷰 확보 캠페인으로 초기 신뢰 구축"
        amount = "10%"
    elif "신규" in search or "유입" in search:
        action = "신규 고객 대상 첫 구매 할인 쿠폰 노출"
        amount = "10%"
    # 경쟁사(외부) 관련 리뷰/후기 언급일 때만 "경쟁사 리뷰 대응" 액션을 씁니다.
    # (is_external 조건이 없으면, 우리 제품 자체의 배송/품질 리뷰를 언급한 내부 문제도
    # 엉뚱하게 "경쟁사 리뷰를 겨냥한 홍보"로 오해하는 문장이 나옵니다)
    elif is_external and ("리뷰" in search or "후기" in search):
        action = "경쟁사의 부정 리뷰 내용을 우리 서비스 강점과 비교하는 홍보 콘텐츠 노출"
        amount = "8%"
    elif "재방문" in search or "재구매" in search:
        action = "재구매 고객 전용 할인 쿠폰 발송"
        amount = "12%"
    elif "품질" in search or "불만" in search or "평점" in search:
        action = "품질 개선 공지와 무상 교환·보증 혜택 안내"
        amount = "8%"
    # "인증/규제"와 "시험"은 둘 다 출시 요건과 관련 있지만 액션이 달라서 분리합니다
    # (인증 서류 확보 vs 성능 시험 결과 공개). "인증"을 먼저 확인합니다 — 시험성적서도
    # 인증 문제의 설명에 같이 언급되는 경우가 많아서, 순서가 바뀌면 인증 문제가 시험
    # 카테고리로 잘못 분류됩니다.
    elif "인증" in search or "규제" in search:
        action = "필수 인증·시험성적서 확보 로드맵을 투명하게 공개"
        amount = "8%"
    elif "시험" in search or "검증" in search:
        action = "Q-max·세탁내구 등 공개 시험 결과 콘텐츠로 성능 입증"
        amount = "8%"
    elif "채널" in search:
        action = "신규 판매 채널(Otto, Kaufland 등) 입점 확대 안내"
        amount = "9%"
    elif "결제" in search or "수단" in search:
        action = "독일 선호 결제수단(Klarna 등) 추가 지원 안내"
        amount = "9%"
    elif any(w in search for w in ("인지도", "바이럴", "참여율")):
        action = "후기·스토리 중심 브랜드 콘텐츠 캠페인 노출"
        amount = "7%"
    elif "환율" in search:
        action = "환율 변동과 무관한 고정가 번들 상품 프로모션 노출"
        amount = "8%"
    elif "고객센터" in search or "응답" in search:
        action = "자주 묻는 질문 자동 응답과 고객센터 응답 시간 단축 안내"
        amount = "8%"
    elif "반품" in search:
        action = "반품 사유 설문과 사이즈·색상 맞춤 교환 가이드 제공"
        amount = "8%"
    # "가격" 격차 문제는 경쟁사 비교와 맞물릴 때가 많아 가장 뒤쪽(그 앞의 더 구체적인
    # 카테고리에 안 걸렸을 때만)에 둡니다.
    elif "가격" in search:
        action = "가격대별 번들·구성으로 체감 가격 차이 완화"
        amount = "8%"

    return action, amount


def hypothesis_pick_sensitivity(
    desc: str,
    is_external: bool,
    competitor_review: str,
    group: str = "",
) -> str:
    """이유 문장에 쓸 "~에 민감하게 반응할 가능성이 크기" 앞부분을 고릅니다.
    "외부" 요인이라고 전부 경쟁사 비교 문제는 아닙니다 (환율, 광고 플랫폼, 시장 트렌드 등도 외부 요인).
    경쟁사와 직접 관련 있을 때만(group이 "경쟁사"일 때, 또는 group 정보가 없고 설명에 "경쟁사"가
    나올 때) 그렇게 표현합니다. (group이 없을 때 competitor_review만 보고 판단하면
    hypothesis_pick_action()과 같은 이유로 틀릴 수 있어 "경쟁사" 텍스트 매칭으로 바꿨습니다)"""
    is_competitor_problem = (group == "경쟁사") if group else "경쟁사" in desc
    if is_competitor_problem:
        return "독일 경쟁사 대비 우리 혜택"
    if is_external:
        return "외부 시장 상황"
    return "해당 요인"


def hypothesis_build_sentence(problem: dict) -> str:
    """
    1번 분석 결과(문제)로 가설 문장을 만듭니다. (AI 연동 전까지는 규칙 기반으로 채웁니다)
    형식: 만약 [타깃/지점]에 [구체적인 액션]을 적용한다면,
          [이유/고객 심리] 때문에 [측정 가능한 지표/KPI]가 [얼마나] 개선될 것이다
    같은 problem이면 항상 같은 문장을 돌려줍니다 (무작위 요소 없음). 1번 분석 결과에서 나온
    "가설 1개"라는 전제상, 같은 문제에 여러 후보가 있는 게 아니라 하나의 답이 있어야 하기 때문입니다.
    """
    # report 쪽 값이 문자열이 아니거나(숫자 등) 아예 없을 수도 있으니 전부 str로 안전하게 바꿔 둡니다
    target = str(problem.get("target") or "독일 전체 고객")
    kpi = str(problem.get("metric") or "매출")
    title = str(problem.get("title") or "")
    desc = str(problem.get("detail") or title or "")
    is_external = problem.get("type") == "외부"
    group = str(problem.get("group") or "").strip()
    local_context = str(problem.get("local_context") or "").strip()
    competitor_review = str(problem.get("competitor_review") or "").strip()

    action, amount = hypothesis_pick_action(desc, is_external, competitor_review, title, group)
    sensitivity = hypothesis_pick_sensitivity(desc, is_external, competitor_review, group)

    # local_context가 있으면 "현지 특성 반영" 요구사항대로 이유에 항상 포함시킵니다.
    # detail(desc)은 바로 위 caption에 이미 그대로 보여주고 있으므로, 문장이 너무 길어지지
    # 않게 여기서는 다시 인용하지 않습니다.
    if local_context:
        context_short = hypothesis_shorten(local_context, 50)
        reason = f"{context_short} 때문에 고객이 {sensitivity}에 민감하게 반응할 가능성이 크기"
    else:
        # desc(detail)가 "~했습니다." 처럼 이미 완결된 문장으로 끝나는 경우가 많아서,
        # 마침표 뒤에 바로 "로"를 붙이면 "습니다.로"처럼 비문이 됩니다. 끝의 문장부호를 떼어내고 붙입니다.
        desc_for_reason = (desc or "분석 결과").rstrip(". !?。")
        reason = f"{desc_for_reason}로 미루어 볼 때 고객이 {sensitivity}에 민감하게 반응할 가능성이 크기"

    action_particle = hypothesis_particle(action, "을", "를")
    kpi_particle = hypothesis_particle(kpi, "이", "가")

    return (
        f"만약 {target}에 {action}{action_particle} 적용한다면, "
        f"{reason} 때문에 {kpi}{kpi_particle} {amount} 개선될 것이다."
    )
    # TODO(AI 연동): AI 사용 도구/키가 정해지면, 여기서 먼저 AI 호출을 시도하고
    # 실패하거나 준비 전이면 지금처럼 규칙 기반 문장으로 대체하도록 바꿉니다.


def hypothesis_pick_problem(report: dict | None) -> dict | None:
    """report["problems"](리스트)에서 가설을 만들 문제 1개를 고릅니다.
    맨 앞(0번)을 가장 중요한 문제로 보고 그것을 씁니다. 모양이 이상해도 절대 죽지 않게 방어합니다."""
    if not report:
        return None
    problems = report.get("problems")
    if not isinstance(problems, list):
        return None
    for item in problems:
        if isinstance(item, dict) and item.get("title"):
            return item
    return None


def hypothesis_problem_key(problem: dict) -> str:
    """리포트 문제가 바뀌었는지 비교하는 키 (제목 + 설명)"""
    return f"{problem.get('title', '')}|{problem.get('detail', '')}"


def _hypothesis_handle_reset(problem: dict) -> None:
    """'자동 생성 문장으로 되돌리기' 버튼의 on_click 콜백. hypothesis_build_sentence()는 같은 problem에
    항상 같은 문장을 돌려주므로(결정적), 이 버튼은 "다른 안을 보여주는" 게 아니라 textarea에서 손으로
    고친 내용을 원래 자동 생성 문장으로 되돌리는 용도입니다. 위젯이 그려지기 전에 실행되므로
    session_state를 안전하게 덮어쓸 수 있습니다."""
    st.session_state["hypothesis-draft-text"] = hypothesis_build_sentence(problem)


def _hypothesis_handle_save(problem: dict, text: str) -> None:
    """'가설 저장' 버튼의 on_click 콜백. media, solution, home 탭이 읽을 수 있게 'hypothesis' 키에
    가설 1개만 저장합니다. "hypothesis" 키는 home_data.py가 이미 기대하는 이름이라 같이 넣습니다."""
    text = str(text or "").strip()
    if not text:   # 버튼이 비활성화돼 있어야 하지만, 혹시 모를 상태 꼬임에 대비한 이중 방어
        return
    store_set(
        "hypothesis",
        {
            "hypothesis": text,   # home_data.py가 기대하는 키 이름 (완료 표시 등에 사용)
            "text": text,         # media 등에서 더 명확한 이름으로 읽고 싶을 때
            "problem_title": problem.get("title"),
            "target": problem.get("target"),
            "metric": problem.get("metric"),
            "type": problem.get("type"),
            "local_context": problem.get("local_context"),
            "competitor_review": problem.get("competitor_review"),
        },
    )


def hypothesis_render():
    """'2. 가설 수립' 탭을 열 때마다 실행됩니다. 화면은 전부 이 함수 안에서 그립니다."""
    ui.page_header("2. 가설 수립", "1번 분석 리포트의 문제를 바탕으로 가설 1개를 자동으로 만들어 드려요.")

    # report/problems 모양이 아직 안 정해졌거나 다른 탭이 예상과 다르게 저장해도
    # 화면이 깨지지 않도록, dict/list가 아니면 전부 "없음"으로 취급합니다.
    report = store_get("report")
    report = report if isinstance(report, dict) else None
    problem = hypothesis_pick_problem(report)

    summary = report.get("summary") if report else None
    if not summary and report and isinstance(report.get("problems"), list) and report["problems"]:
        summary = f"분석된 문제 {len(report['problems'])}건 중 첫 번째 문제를 기준으로 가설을 만들었어요."
    if not summary:
        summary = "분석 리포트 탭에서 먼저 문제를 분석해 주세요."

    with st.container(border=True, key="hypothesis-summary-card"):
        st.markdown("**📋 분석 리포트 문제 요약**")
        st.caption(summary)

    if not problem:
        # key="hypothesis-empty"를 줘서 hypothesis_style.css의 .st-key-hypothesis-empty 규칙이
        # 이 카드 버튼에도 똑같이 적용되게 합니다 (안 그러면 버튼 글씨가 또 안 보임).
        with st.container(border=True, key="hypothesis-empty"):
            st.markdown('<p class="hypothesis-empty-icon">🧭</p>', unsafe_allow_html=True)
            st.markdown('<p class="hypothesis-empty-title">아직 분석된 문제가 없어요</p>', unsafe_allow_html=True)
            st.caption("1. 분석 리포트 탭에서 문제를 분석하면, 그 결과로 가설이 자동으로 만들어져요.")
            st.button(
                "예시 데이터로 먼저 테스트하기",
                key="hypothesis-btn-sample",
                type="primary",
                width="stretch",
                on_click=lambda: store_set("report", SAMPLE_REPORT),
            )
        return

    problem_key = hypothesis_problem_key(problem)

    # 리포트 문제가 바뀌었으면(또는 처음 열었으면) 자동으로 가설을 새로 만듭니다.
    # 같은 문제가 유지되는 동안에는 이미 만든 가설(수정한 내용 포함)을 그대로 둡니다.
    if st.session_state.get("hypothesis-problem-key") != problem_key:
        st.session_state["hypothesis-draft-text"] = hypothesis_build_sentence(problem)
        st.session_state["hypothesis-problem-key"] = problem_key

    # key="hypothesis-card"를 주면 Streamlit이 이 카드에 .st-key-hypothesis-card 클래스를 붙여줘서,
    # hypothesis_style.css에서 다른 탭은 안 건드리고 이 카드 안만 정확히 골라 스타일을 고칠 수 있습니다.
    with st.container(border=True, key="hypothesis-card"):
        is_external = problem.get("type") == "외부"
        st.badge(
            "외부 요인 · 경쟁사" if is_external else "내부 요인",
            icon="⚠️" if is_external else "🏷️",
            color="orange" if is_external else "primary",
        )
        st.markdown(f"**{problem.get('title', '')}**")
        if problem.get("detail"):
            st.caption(str(problem["detail"]))
        if problem.get("local_context"):
            st.markdown(f"📍 **현지 특성** · {problem['local_context']}")
        if problem.get("competitor_review"):
            st.markdown(f"💬 **경쟁사 부정 리뷰** · {problem['competitor_review']}")

        st.divider()
        st.markdown("🤖 **분석 결과를 바탕으로 자동 생성된 가설**")
        st.text_area(
            "가설 문장",
            key="hypothesis-draft-text",
            height=120,   # 글자를 키운 만큼(hypothesis_style.css) 칸은 덜 비게 살짝 줄임
            label_visibility="collapsed",
        )
        # AI가 아직 연결되지 않아서 항상 규칙 기반입니다. AI 연동 후에는 source를 받아 문구를 바꾸면 됩니다.
        st.caption("✏️ 규칙 기반으로 자동 작성된 문장이에요. 자유롭게 고쳐서 저장하세요.")

        saved = store_get("hypothesis")
        saved = saved if isinstance(saved, dict) else None
        draft_text = str(st.session_state["hypothesis-draft-text"] or "").strip()
        is_saved = bool(saved) and saved.get("text") == draft_text

        c1, c2 = st.columns([1, 1])
        with c1:
            # "다른 안을 보여주는" 버튼이 아닙니다 — 1번 분석 결과에서 나온 가설은 하나뿐이어야
            # 하므로, 이 버튼은 손으로 고친 내용을 원래 자동 생성 문장으로 되돌리기만 합니다
            # (hypothesis_build_sentence는 같은 문제면 항상 같은 문장을 돌려줍니다).
            # text_area가 이미 그려진 뒤에 같은 키(session_state["hypothesis-draft-text"])를
            # 직접 덮어쓰면 StreamlitWidgetAlreadyInstantiatedError가 나므로, 위젯이 만들어지기
            # 전에 실행되는 on_click 콜백에서 값을 바꿉니다.
            st.button(
                "↺ 자동 생성 문장으로 되돌리기",
                key="hypothesis-btn-reset",
                on_click=_hypothesis_handle_reset,
                args=(problem,),
                type="secondary",
                width="stretch",
            )
        with c2:
            # media, solution 탭이 읽을 수 있게 "hypothesis" 키에 가설 1개만 저장
            # (이미 저장됐거나, 텍스트를 전부 지워 빈 칸이면 저장 버튼을 눌러도 의미가 없으니 비활성화)
            st.button(
                "✓ 저장됨" if is_saved else "가설 저장",
                key="hypothesis-btn-save",
                disabled=is_saved or not draft_text,
                on_click=_hypothesis_handle_save,
                args=(problem, draft_text),
                type="primary",
                width="stretch",
            )

        if is_saved:
            st.caption("✅ 이 가설이 저장됐어요. 다음 탭(매체 제작 등)에서 이 가설을 사용해요.")
