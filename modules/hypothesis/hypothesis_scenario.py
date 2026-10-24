# 2. 가설 수립 - 검색어 클릭 문제(문제 시나리오.md 2단계) 가설 · KPI · 최종 판단
# 1번 리포트가 store_set("report", {..., "sqp": {...}})로 넘긴 검색어 클릭 분석 값이 있을 때만 보입니다.
# hypothesis_render() 맨 아래에서 부릅니다.
import streamlit as st

HYPOTHESIS_SCENARIO_KPIS = [
    ("메인", "CTR (클릭 ÷ 노출)", "직접 올려야 할 숫자. 시장 대비는 클릭 점유율 ÷ 노출 점유율"),
    ("진단", "노출 점유율, 검색 상단 노출 비율", "덜 눌리는 건지, 아예 덜 보이는 건지 구분"),
    ("안전장치", "CVR (단위 세션 비율, Unit Session Percentage)", "CTR만 오르고 구매가 줄면 실패. 클릭만 끄는 과장된 이미지 방지"),
    ("안전장치", "CPC, ACoS (광고비 ÷ 광고 매출)", "늘어난 클릭이 광고비를 더 써서 얻은 건지 확인"),
    ("결과", "구매 점유율, 매출", "늘어난 클릭이 실제 판매로 이어졌는지"),
    ("사업 효과", "CAC (광고비 ÷ 신규 고객 주문)", "광고 리포트의 신규 고객(New-to-brand) 수치로 대략 계산"),
    ("참고", "LTV, 리텐션율", "이 문제에는 약함. 냉감패드는 재구매 주기가 길고 아마존은 고객 정보를 거의 주지 않음"),
]


def hypothesis_scenario_sentence(sqp: dict) -> str:
    """시나리오 메인 가설 한 문장 (If → Because → Then)."""
    return (
        "만약 메인 이미지를 펼친 패드의 냉감 원단 질감과 두께가 보이는 각도로 바꾸면, "
        "저가 제품과의 품질 차이가 바로 보여서, "
        f"'{sqp.get('query', '')}' 검색에서 클릭 점유율 ÷ 노출 점유율이 "
        f"{sqp.get('ratio', 0):.2f}배에서 {sqp.get('kpi_goal', 0.8):.1f}배 이상으로 오를 것이다."
    )


def _hypothesis_scenario_fill(sqp: dict) -> None:
    """'이 가설 문장을 위 칸에 넣기' 콜백. 위젯이 다시 그려지기 전에 실행되어 textarea 값을 바꿀 수 있습니다."""
    st.session_state["hypothesis-draft-text"] = hypothesis_scenario_sentence(sqp)


def hypothesis_scenario_table(rows) -> str:
    """두 칸짜리 마크다운 표 (긴 문장도 줄바꿈되도록 dataframe 대신 사용)."""
    body = "\n".join(f"| **{k}** | {str(v).replace('|', '/')} |" for k, v in rows)
    return f"| 칸 | 내용 |\n| --- | --- |\n{body}"


def hypothesis_scenario_section(report: dict | None) -> None:
    sqp = report.get("sqp") if isinstance(report, dict) else None
    if not isinstance(sqp, dict) or not sqp.get("query"):
        return
    listing = sqp.get("listing") or {}
    problems = report.get("problems") if isinstance(report.get("problems"), list) else []
    first = problems[0] if problems and isinstance(problems[0], dict) else {}
    review = str(first.get("competitor_review") or "").strip()
    goal = sqp.get("kpi_goal", 0.8)

    with st.container(border=True, key="hypothesis-scenario-card"):
        st.markdown(f"**📐 문제 1 가설** · '{sqp['query']}' 검색에서 보이는 만큼 눌리게 하기")
        st.caption(f"데이터: {sqp.get('source', '')}")

        because = (f"클릭 이후 전환은 시장과 비슷하다 (클릭 대비 장바구니 우리 {sqp.get('cart_rate_ours')}% vs "
                   f"시장 {sqp.get('cart_rate_market')}%) → 문제는 첫인상이다. 저가 제품과 비슷해 보이는 사진으로는 "
                   f"클릭된 상품 중앙 가격보다 €{sqp.get('price_gap', 0):.0f} 더 비싼 이유가 안 보인다.")
        if review:
            because += f" 경쟁 제품 약점({review})이 두께·원단과 관련 있다면 그것이 곧 차별점이다."
        st.markdown(hypothesis_scenario_table([
            ("타깃", f"amazon.de '{sqp['query']}' 검색 결과"),
            ("액션 (If)", f"메인 이미지를 {listing.get('main_image', '현재 사진')}(A)에서 펼친 패드의 모서리를 살짝 들어 "
                          "두께와 냉감 원단 질감이 보이는 각도(B)로 바꾼다"),
            ("이유 (Because)", because),
            ("결과 (Then) KPI", f"클릭 점유율 ÷ 노출 점유율 {sqp.get('ratio', 0):.2f}배 → {goal:.1f}배 이상"),
            ("고정 요소", f"흰 배경 실제 사진, 제목, 가격 €{listing.get('price', 0):.2f}, 쿠폰 없음"),
            ("테스트 방법", "Manage Your Experiments, 메인 이미지 A/B"),
        ]))
        st.caption("근거의 경쟁 제품 약점은 경쟁사 DB 값이고 실제 리뷰 원문이 아닙니다. 경쟁 제품 리뷰 30~50개를 모아 "
                   "가장 많이 나오는 불만으로 바꿔 넣어야 하고, 불만이 다르게 나오면 액션도 바뀝니다 "
                   "(예: '미끄러진다'가 많으면 바닥 미끄럼 방지면이 보이는 각도).")
        st.markdown(f"> {hypothesis_scenario_sentence(sqp)}")
        st.button("이 가설 문장을 위 칸에 넣기", key="hypothesis-btn-scenario-fill",
                  on_click=_hypothesis_scenario_fill, args=(sqp,), type="secondary")

        st.markdown("**대안 가설 (메인이 안 될 때)**")
        st.markdown("- 제목 앞부분에 OEKO-TEX 인증과 두께를 넣는다. 모바일 검색 결과에서는 제목 앞부분만 보여서, "
                    "인증을 내세우는 Novilla·RIBECO와 같은 조건에서 비교되게 하려는 것이다.\n"
                    "- 메인 가설과 동시에 돌리면 변수가 두 개가 되니, 메인 테스트가 끝난 뒤에 시작한다.")

        p2 = sqp.get("problem2")
        if isinstance(p2, dict):
            st.markdown("**문제 2 운영 가설 (참고, 소재 외 → ④ 광고 타이밍)**")
            st.markdown(f"- 독일 기상청(DWD) 최고기온 {p2.get('heat_temp', 28):.0f}°C 이상인 날에 '{p2.get('query')}' 입찰을 올리면, "
                        f"노출 점유율이 {p2.get('imp_share')}%에서 {p2.get('goal_imp_share')}%로 오르고 배수는 1.2배 이상을 "
                        f"유지할 것이다. {p2.get('month')} 기준 약 {p2.get('extra_clicks'):,}회 클릭이 는다.\n"
                        "- 광고 소재가 필요 없는 가설이라 ③ 광고 소재가 아니라 ④ 광고 타이밍으로 보낸다.")

    with st.container(border=True, key="hypothesis-scenario-kpi"):
        st.markdown("**📏 KPI와 최종 판단** · 클릭 단계 문제라 메인 KPI는 CTR, 나머지는 진단·안전장치")
        st.markdown("| 역할 | KPI | 쓰는 법 |\n| --- | --- | --- |\n"
                    + "\n".join(f"| {a} | {b} | {c} |" for a, b, c in HYPOTHESIS_SCENARIO_KPIS))
        st.markdown(
            "**승자는 CTR로, 사업 효과는 CAC로**\n"
            f"1. **승자 결정**: 클릭 점유율 ÷ 노출 점유율이 높은 쪽 ({goal:.1f}배 이상 목표). 단, CVR이 떨어지지 않아야 한다.\n"
            "2. **사업 효과 확인**: 이긴 이미지를 적용하기 전 4주와 후 4주의 CAC를 비교한다. "
            "계산이 어려우면 주문당 광고비나 ACoS로 대신한다.\n"
            "3. **발표 논리**: CTR이 오르면 같은 노출에서 클릭이 늘고, 클릭률이 높으면 클릭당 비용도 내려가는 경향이 있다. "
            "CVR까지 유지되면 주문당 비용이 줄고 결국 CAC가 낮아진다.")
        st.caption("CAC로 A/B 승자를 고르지 않는 이유: Manage Your Experiments 결과에는 버전별 광고비·신규 고객 수가 없고, "
                   "신규 고객 구분은 광고 주문 일부에서만 나오며, 입찰·시즌·경쟁사 할인에도 크게 흔들립니다.")
