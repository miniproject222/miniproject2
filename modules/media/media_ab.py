# 3. 매체 제작 > 메인 이미지 A/B (문제 시나리오.md '가설과 소재 연결')
# 하위 탭 ①과 같은 A/B 설계(plan, media_variable_plan())로 메인 이미지 A/B 안, 촬영 브리프,
# Manage Your Experiments 안내를 보여 줍니다. 3번 탭의 하위 탭 'A/B 소재 준비'(1단계)에서 부릅니다.
# 가설·리포트는 직접 읽지 않고 media_variable.py의 함수를 거칩니다 (출처가 바뀌면 그쪽만 고침).
# 이전 결과·판정 코드는 media_stage2/media_stage2_judge.py에 보관합니다 (지금 흐름에서는 안 씀).
import streamlit as st

from modules.media.media_variable import media_variable_hypothesis, media_variable_plan, media_variable_report_sqp

MEDIA_AB_RULES = [
    "흰 배경(RGB 255, 255, 255)에 텍스트·로고·워터마크 없는 실제 제품 사진",
    "AI로 만든 연출 장면은 메인 이미지에 쓰지 않음 → 서브 이미지나 스폰서드 브랜드 광고에서만 사용",
    "A/B 변수는 사진 안에서 바꿀 수 있는 것만: 각도, 구도, 접힌/펼친 상태, 두께감",
    "AI는 촬영 각도 레퍼런스와 보정에만 쓰고, 실제 촬영은 외주로 진행",
]


def media_ab_brief(plan, price, hypothesis_text):
    """촬영 외주용 브리프 (다운로드 텍스트). A/B와 검색어는 하위 탭 ①과 같은 plan에서 가져옵니다."""
    return "\n".join([
        "[메인 이미지 촬영 브리프] SEORI 냉감패드 · amazon.de",
        f"검색어: {plan['query']}",
        f"가설: {hypothesis_text}",
        "",
        f"A (현재, 유지): {plan['a']}",
        f"B (새로 촬영): {plan['b']}",
        "",
        "필수 규칙",
        *[f"- {r}" for r in MEDIA_AB_RULES],
        "- 제품이 이미지의 85% 이상을 차지, 긴 변 1000px 이상 (확대 기능, 1600px 이상 권장)",
        "",
        f"고정 요소 (바꾸지 않음): 제목, 가격 {price}, 쿠폰 없음",
        "납품: A/B 각 3컷 (보정 전 원본 + 흰 배경 보정본)",
    ])


def media_ab_plan_step():
    """하위 탭 ② A/B 소재 준비: A/B 안, 메인 이미지 규칙, 촬영 브리프, 테스트 도구. 반드시 media_render() 안에서 부릅니다.
    가설은 하위 탭 ①에서 이미 보여 주므로 여기서는 다시 보여 주지 않습니다."""
    plan, price, defaults = media_variable_plan()
    hypothesis_text, _ = media_variable_hypothesis()   # 2번 탭 가설 (없으면 기준 가설)
    # plan에 없는 값(노출·클릭 점유율, 지금 이미지의 문제점, 데이터 출처)만 리포트에서 따로 읽습니다
    sqp = media_variable_report_sqp()
    listing = sqp.get("listing") if isinstance(sqp.get("listing"), dict) else {}

    kpi = f"{plan['kpi']} {plan['kpi_now']:g}배 → 목표 {plan['kpi_goal']:g}배 이상"
    if sqp.get("imp_share") is not None and sqp.get("click_share") is not None:
        kpi = (f"노출 점유율 {sqp['imp_share']}% · 클릭 점유율 {sqp['click_share']}% · "
               f"{kpi} ({sqp.get('source', '')})")
    st.markdown(f'<div class="media-desc">\'{plan["query"]}\' 검색 · {kpi}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("**A · 현재 (대조군)**")
            st.markdown(f"{plan['a']}  \n"
                        f'<span class="media-desc">{listing.get("main_image_issue", "")}</span>', unsafe_allow_html=True)
    with c2:
        with st.container(border=True):
            st.markdown("**B · 제안 (실험군)**")
            st.markdown(f"{plan['b']}  \n"
                        '<span class="media-desc">저가 제품과의 품질 차이(두께·원단)가 검색 결과에서 바로 보이게</span>',
                        unsafe_allow_html=True)
    st.markdown(f'<div class="media-desc">고정 요소: 흰 배경 실제 사진, 제목, 가격 {price}, 쿠폰 없음 · '
                '대안(제목 앞에 OEKO-TEX·두께)은 이 테스트가 끝난 뒤 따로 진행</div>', unsafe_allow_html=True)
    if defaults:   # 하위 탭 ①과 같은 안내
        st.caption(f"1번 리포트 값이 없어 기본값으로 보여 줘요: {', '.join(defaults)}")

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.markdown("**메인 이미지 규칙 (아마존)**")
        st.markdown("\n".join(f"- {r}" for r in MEDIA_AB_RULES))
    with c2:
        st.markdown("**테스트 도구: Manage Your Experiments**")
        st.markdown("- 아마존 공식 A/B 도구. 메인 이미지, 제목, 불릿, 상세 설명, A+ 콘텐츠를 테스트할 수 있음\n"
                    "- 브랜드 등록과 충분한 트래픽이 필요하고, 상품당 한 번에 하나의 테스트만 가능\n"
                    "- 보통 4~10주 → 실제로는 성수기(5월) 전에 시작. 시연에서는 결과도 가상 데이터로 표시")

    brief = media_ab_brief(plan, price, hypothesis_text)
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        with st.expander("📷 촬영 브리프 (외주용)", expanded=False):
            st.code(brief, language=None)
            st.download_button("브리프 다운로드 (.txt)", brief, file_name="media_ab_brief.txt", key="media-btn-ab-brief")
    with c2:
        with st.expander("🤖 AI 각도 레퍼런스 프롬프트 (메인 이미지로 쓰지 않음)", expanded=False):
            st.code("Product photo reference, white seamless background, a cooling mattress pad 90x200 cm laid flat, "
                    "camera 45 degrees above, one corner gently lifted to show the edge thickness and the knitted "
                    "cooling fabric texture, soft even studio light, no text, no props", language=None)
