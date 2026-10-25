# 2. 가설 수립 - 검색어 클릭 문제(문제 시나리오.md 2단계) 가설 근거 · KPI · 최종 판단
# 1번 리포트가 store_set("report", {..., "sqp": {...}})로 넘긴 검색어 클릭 분석 값이 있을 때만 쓰입니다.
# hypothesis_page.py가 가설 후보 탭 안에서:
#   1) hypothesis_scenario_ibt()/_problem2_ibt()로 If·Because·Then 조각을 받아
#      hypothesis_if_then_card()로 그 탭(그리고 선택되면 맨 위 "선택된 가설" 칸)에 그리고,
#   2) hypothesis_scenario_detail_section()/_problem2_detail_section()으로 실행 세부사항·
#      KPI 판단 기준을 이어서 보여줍니다.
import html

import streamlit as st

def hypothesis_ibt_clean(ibt: dict) -> dict:
    """If·Because·Then 각 조각 안의 ", "(쉼표+공백)를 "·"로 바꿉니다. ③ 탭(media_variable_split)은
    저장된 가설 문장을 ", "로 잘라 If/Because/Then을 나누는데, 조각 안에 쉼표가 있으면(예: report의
    타깃 "Amazon.de, 자사몰에서…", 액션 "(Otto, Kaufland 등)") 엉뚱한 곳에서 잘렸습니다. 조각 안에
    쉼표가 없으면 문장 전체의 쉼표는 If 뒤 하나뿐이고, ③ 탭은 마지막 "때문에"에서 Because/Then을
    정확히 나눕니다. 카드와 저장 문장이 같은 조각을 쓰도록 모든 *_ibt()가 이 함수를 거칩니다."""
    return {k: str(v).replace(", ", "·").strip() for k, v in ibt.items()}


HYPOTHESIS_SCENARIO_KPIS = [
    ("메인", "CTR (클릭 ÷ 노출)", "직접 올려야 할 숫자. 시장 대비는 클릭 점유율 ÷ 노출 점유율"),
    ("진단", "노출 점유율, 검색 상단 노출 비율", "덜 눌리는 건지, 아예 덜 보이는 건지 구분"),
    ("안전장치", "CVR (단위 세션 비율, Unit Session Percentage)", "CTR만 오르고 구매가 줄면 실패. 클릭만 끄는 과장된 이미지 방지"),
    ("안전장치", "CPC, ACoS (광고비 ÷ 광고 매출)", "늘어난 클릭이 광고비를 더 써서 얻은 건지 확인"),
    ("결과", "구매 점유율, 매출", "늘어난 클릭이 실제 판매로 이어졌는지"),
    ("사업 효과", "CAC (광고비 ÷ 신규 고객 주문)", "광고 리포트의 신규 고객(New-to-brand) 수치로 대략 계산"),
    ("참고", "LTV, 리텐션율", "이 문제에는 약함. 냉감패드는 재구매 주기가 길고 아마존은 고객 정보를 거의 주지 않음"),
]


def hypothesis_scenario_ibt(sqp: dict) -> dict:
    """'소재 개선' 가설의 If·Because·Then 조각을 돌려줍니다. hypothesis_if_then_card()로
    그리는 쪽(가설 후보 탭, 선택되면 맨 위 "선택된 가설" 칸)과 hypothesis_scenario_sentence()
    (저장용 한 문장)가 전부 이 한 곳에서만 내용을 가져가므로 서로 어긋나지 않습니다.
    competitor_review 원문(경쟁 제품 약점 목록)·Keepa 평점/리뷰수 같은 통계는 길어서 문장에
    넣으면 "한눈에 읽기 좋게"가 안 돼서 Because에는 아예 안 넣고, 원문은 전부
    hypothesis_evidence_section()의 "📚 근거·출처 보기" 토글로만 보여줍니다."""
    listing = sqp.get("listing") or {}
    goal = sqp.get("kpi_goal") or 0   # 목표는 ① 리포트 값만 (고정 기본값 없음)

    because = (f"클릭 이후 전환은 시장과 비슷해서(클릭 대비 장바구니 우리 {sqp.get('cart_rate_ours')}% vs "
               f"시장 {sqp.get('cart_rate_market')}%) 문제는 첫인상이며 저가 제품과 비슷해 보이는 사진으로는 "
               f"클릭된 상품 중앙 가격보다 €{sqp.get('price_gap', 0):.0f} 더 비싼 이유가 안 보이기 때문에")

    return hypothesis_ibt_clean({
        "if": f"메인 이미지를 {listing.get('main_image', '현재 사진')}(A)에서 펼친 패드의 모서리를 살짝 들어 "
              "두께와 냉감 원단 질감이 보이는 각도(B)로 바꾼다면",
        "because": because,
        "then": f"'{sqp.get('query', '')}' 검색에서 클릭 점유율 ÷ 노출 점유율이 "
                f"{sqp.get('ratio', 0):.2f}배에서 {goal:.2f}배 이상으로 오를 것이다",
    })


def hypothesis_scenario_sentence(sqp: dict) -> str:
    """시나리오 메인 가설 한 문장 (If → Because → Then). hypothesis_scenario_ibt()의 조각을
    그대로 이어붙인 것이라, 카드에 보이는 내용과 저장되는 문장이 항상 같습니다."""
    ibt = hypothesis_scenario_ibt(sqp)
    return f"만약 {ibt['if']}, {ibt['because']} {ibt['then']}."


def hypothesis_scenario_problem2_ibt(p2: dict) -> dict:
    """'노출 확대' 가설의 If·Because·Then 조각. 소재가 아니라 광고 타이밍 문제라
    hypothesis_scenario_ibt()와는 액션·KPI가 다릅니다."""
    return hypothesis_ibt_clean({
        "if": f"독일 기상청(DWD) 최고기온 {p2.get('heat_temp', 28):.0f}°C 이상인 날에 "
              f"'{p2.get('query', '')}' 입찰을 올린다면",
        "because": "더운 날은 검색량 자체가 늘어 경쟁이 치열해지는데 지금은 노출 점유율이 낮아 "
                   "그 수요를 놓치고 있기 때문에",
        "then": f"노출 점유율이 {p2.get('imp_share', 0)}%에서 {p2.get('goal_imp_share', 0)}%로 올라 "
                f"{p2.get('month', '')} 기준 약 {p2.get('extra_clicks', 0):,}회 클릭이 늘 것이다",
    })


def hypothesis_scenario_problem2_sentence(p2: dict) -> str:
    """'노출 확대' 가설 후보(sqp["problem2"])의 한 문장. hypothesis_scenario_problem2_ibt()의
    조각을 그대로 이어붙인 것입니다."""
    ibt = hypothesis_scenario_problem2_ibt(p2)
    return f"만약 {ibt['if']}, {ibt['because']} {ibt['then']}."


def hypothesis_if_then_card(rows: list[tuple[str, str, str]]) -> None:
    """가설을 If(액션) · Because(이유) · Then(결과) 3줄짜리 색 배지 카드로 보여줍니다
    (사용자가 참고로 준 이미지와 같은 형태). rows는 [(라벨, css class 접미사, 내용), ...]
    형태로, 보통 [("If", "if", 액션), ("Because", "because", 이유), ("Then", "then", 결과)]
    3줄을 씁니다. 표보다 한눈에 들어와서 "스크롤 없이 가설을 바로 파악"하는 데 씁니다.
    가설 후보 탭 안과(맨 아래 선택 버튼 위) 맨 위 "지금 선택된 가설" 칸 양쪽에서 똑같이
    이 함수를 씁니다 — 선택된 가설도 If·Because·Then 카드로 보이길 원한다는 요청 반영."""
    icons = {"if": "✏️", "because": "❓", "then": "📈"}
    rows_html = "".join(
        f'<div class="hypothesis-ibt-row">'
        f'<span class="hypothesis-ibt-badge hypothesis-ibt-{cls}">{icons.get(cls, "")} {label}</span>'
        f'<span class="hypothesis-ibt-text">{html.escape(str(text), quote=False)}</span>'
        f"</div>"
        for label, cls, text in rows
    )
    st.markdown(f'<div class="hypothesis-ibt-box">{rows_html}</div>', unsafe_allow_html=True)


def hypothesis_scenario_table(rows) -> str:
    """두 칸짜리 마크다운 표 (긴 문장도 줄바꿈되도록 dataframe 대신 사용)."""
    body = "\n".join(f"| **{k}** | {str(v).replace('|', '/')} |" for k, v in rows)
    return f"| 칸 | 내용 |\n| --- | --- |\n{body}"


def hypothesis_scenario_detail_section(sqp: dict) -> None:
    """'소재 개선' 가설 후보 탭 안에서, If·Because·Then 카드보다 먼저 "실행 방법"을
    보여줍니다(실행 방법을 보고 가설을 비교·선택할 수 있어야 한다는 요구 반영). 타깃·목표
    KPI·준비할 소재·고정 요소·테스트 방법·기간·표본을 전부 토글 없이 메인 표 하나로
    보여주고(목표 KPI도 실행 방법과 같이 보는 게 비교에 더 편함), CAC/CTR 판단 기준처럼
    더 깊은 설명만 "📏 판단 기준 자세히 보기" 토글에 둡니다. 문제 설명·현지 특성·경쟁사 근거
    원문·출처는 여기 말고 hypothesis_page.py의 hypothesis_evidence_section()이 별도
    토글("📚 근거·출처 보기")로 모아 보여줍니다."""
    st.markdown("**:material/science: 실행 방법**")
    st.markdown(hypothesis_scenario_table(hypothesis_scenario_execution_rows(sqp)))


def hypothesis_scenario_execution_rows(sqp: dict) -> list[tuple[str, str]]:
    """'소재 개선' 가설의 실행 방법 표 행. 화면 표와 "선택하기" 저장값이 같은 행을 쓰도록 분리."""
    listing = sqp.get("listing") or {}
    goal = sqp.get("kpi_goal") or 0   # 목표는 ① 리포트 값만 (고정 기본값 없음)
    return [
        ("타깃", f"amazon.de '{sqp.get('query', '')}' 검색 결과"),
        ("목표 KPI", f"클릭 점유율 ÷ 노출 점유율 {sqp.get('ratio', 0):.2f}배 → {goal:.2f}배 이상"),
        ("준비할 소재", "메인 이미지 A안(현재)·B안(두께·원단 질감이 보이는 각도) 사진 각 1장"),
        ("고정 요소", f"흰 배경 실제 사진, 제목, 가격 €{listing.get('price', 0):.2f}, 쿠폰 없음"),
        ("테스트 방법", "Amazon Manage Your Experiments로 50:50 분할 노출"),
        ("기간·표본", "최소 2주 또는 각 안 1,000노출 이상 — 먼저 도달하는 쪽까지"),
    ]


def hypothesis_scenario_judgement(sqp: dict) -> None:
    """'소재 개선' 가설의 KPI 표·판단 기준(CTR로 승자, CAC로 사업 효과). 예전에는 실행 방법 아래
    토글이었는데, ① 탭처럼 화면 오른쪽 끝 아이콘을 누르면 창(dialog)으로 열리도록 옮겼습니다
    (창은 hypothesis_page.py의 hypothesis_dialog_judgement가 엶). 경쟁사 약점 데이터에 대한
    주의 문구도 원래 실행 방법 표 아래 3줄로 있었는데, 화면 높이를 줄이려고 이 창으로 옮겼습니다."""
    goal = sqp.get("kpi_goal") or 0   # 목표는 ① 리포트 값만 (고정 기본값 없음)
    st.caption("근거의 경쟁 제품 약점은 경쟁사 DB 값이고 실제 리뷰 원문이 아닙니다. 경쟁 제품 리뷰 30~50개를 모아 "
               "가장 많이 나오는 불만으로 바꿔 넣어야 하고, 불만이 다르게 나오면 액션도 바뀝니다 "
               "(예: '미끄러진다'가 많으면 바닥 미끄럼 방지면이 보이는 각도).")
    st.caption("클릭 단계 문제라 메인 KPI는 CTR, 나머지는 진단·안전장치")
    st.markdown("| 역할 | KPI | 쓰는 법 |\n| --- | --- | --- |\n"
                + "\n".join(f"| {a} | {b} | {c} |" for a, b, c in HYPOTHESIS_SCENARIO_KPIS))
    st.markdown(
        "**승자는 CTR로, 사업 효과는 CAC로**\n"
        "1. **승자 결정**: 클릭 점유율 ÷ 노출 점유율이 높은 쪽" + (f" ({goal:.2f}배 이상 목표)" if goal else "")
        + ". 단, CVR이 떨어지지 않아야 한다.\n"
        "2. **사업 효과 확인**: 이긴 이미지를 적용하기 전 4주와 후 4주의 CAC를 비교한다. "
        "계산이 어려우면 주문당 광고비나 ACoS로 대신한다.\n"
        "3. **발표 논리**: CTR이 오르면 같은 노출에서 클릭이 늘고, 클릭률이 높으면 클릭당 비용도 내려가는 경향이 있다. "
        "CVR까지 유지되면 주문당 비용이 줄고 결국 CAC가 낮아진다.")
    st.caption("CAC로 A/B 승자를 고르지 않는 이유: Manage Your Experiments 결과에는 버전별 광고비·신규 고객 수가 없고, "
               "신규 고객 구분은 광고 주문 일부에서만 나오며, 입찰·시즌·경쟁사 할인에도 크게 흔들립니다.")


def hypothesis_scenario_problem2_detail_section(p2: dict) -> None:
    """'노출 확대' 가설 후보 탭 안에서, If·Because·Then 카드보다 먼저 "실행 방법"을
    보여줍니다. 타깃·목표 KPI·고정 요소·테스트 방법을 전부 토글 없이 메인 표 하나로
    둡니다(목표 KPI도 실행 방법과 같이 보는 게 비교에 더 편함)."""
    st.markdown("**:material/science: 실행 방법**")
    st.markdown(hypothesis_scenario_table(hypothesis_scenario_problem2_execution_rows(p2)))
    st.caption("소재 외 문제(③ 광고 소재가 아니라 ④ 광고 타이밍)라 메인 이미지 테스트와 별개로 운영할 수 있습니다. "
               "다만 A/B 테스트용 사진·영상 결과물이 따로 나오지는 않는 가설입니다.")


def hypothesis_scenario_problem2_execution_rows(p2: dict) -> list[tuple[str, str]]:
    """'노출 확대' 가설의 실행 방법 표 행. 화면 표와 "선택하기" 저장값이 같은 행을 쓰도록 분리."""
    return [
        ("타깃", f"amazon.de '{p2.get('query', '')}' 검색 결과"),
        ("목표 KPI", f"노출 점유율 {p2.get('imp_share', 0)}% → {p2.get('goal_imp_share', 0)}% "
                    "(배수 1.2배 이상 유지)"),
        ("고정 요소", "소재 변경 없이 입찰가만 조정 (광고 소재가 필요 없는 가설)"),
        ("테스트 방법", f"{p2.get('month', '')} 폭염 주(최고기온 {p2.get('heat_temp', 28):.0f}°C 이상) 입찰 상향 후 "
                      "노출 점유율 비교 (평소 입찰·같은 요일대 대비, 변경 후 최소 3일 반영 대기)"),
    ]
