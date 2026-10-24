# 3. 매체 제작 > 메인 이미지 A/B (문제 시나리오.md '가설과 소재 연결')
# 1번 리포트의 검색어 클릭 분석(store "report"의 sqp)과 2번 가설(store "hypothesis")을 읽어
# 메인 이미지 A/B 안, 촬영 브리프, Manage Your Experiments 안내, 판정 규칙을 보여 줍니다. 3번 탭의 하위 탭 ③(A/B 소재 준비)·④(결과·판정)에서 부릅니다.
import json
import math
from pathlib import Path

import streamlit as st

import ui_theme as ui
from common.common_store import store_get

MEDIA_AB_FILE = Path(__file__).resolve().parent / "data" / "media_ab_result_dummy_202610.json"
MEDIA_AB_CVR_TOLERANCE = 0.5     # B의 CVR이 A보다 이만큼(%p) 넘게 낮으면 실패로 봅니다
MEDIA_AB_RULES = [
    "흰 배경(RGB 255, 255, 255)에 텍스트·로고·워터마크 없는 실제 제품 사진",
    "AI로 만든 연출 장면은 메인 이미지에 쓰지 않음 → 서브 이미지나 스폰서드 브랜드 광고에서만 사용",
    "A/B 변수는 사진 안에서 바꿀 수 있는 것만: 각도, 구도, 접힌/펼친 상태, 두께감",
    "AI는 촬영 각도 레퍼런스와 보정에만 쓰고, 실제 촬영은 외주로 진행",
]


def media_ab_rate_test(a_hit, a_n, b_hit, b_n):
    """두 비율 z-검정. (A 비율, B 비율, 양측 유의확률)"""
    ra, rb = a_hit / a_n, b_hit / b_n
    pooled = (a_hit + b_hit) / (a_n + b_n)
    se = math.sqrt(pooled * (1 - pooled) * (1 / a_n + 1 / b_n))
    z = (rb - ra) / se if se else 0.0
    return ra, rb, math.erfc(abs(z) / math.sqrt(2))


def media_ab_judge(result):
    """승자 판정: CTR이 유의하게 높고, CVR이 기준 이상 떨어지지 않은 쪽."""
    a, b = result["variants"]
    ctr_a, ctr_b, p_ctr = media_ab_rate_test(a["clicks"], a["impressions"], b["clicks"], b["impressions"])
    cvr_a, cvr_b, p_cvr = media_ab_rate_test(a["units"], a["sessions"], b["units"], b["sessions"])
    cvr_ok = (cvr_b - cvr_a) * 100 >= -MEDIA_AB_CVR_TOLERANCE
    win = ctr_b > ctr_a and p_ctr < 0.05 and cvr_ok
    mkt = result["market_ctr"]
    return {"ctr": (ctr_a, ctr_b), "p_ctr": p_ctr, "cvr": (cvr_a, cvr_b), "p_cvr": p_cvr, "cvr_ok": cvr_ok,
            "ratio": (ctr_a / mkt, ctr_b / mkt), "winner": b["name"] if win else a["name"], "b_wins": win}


def media_ab_brief(sqp, hypothesis_text):
    """촬영 외주용 브리프 (다운로드 텍스트)."""
    listing = sqp.get("listing") or {}
    return "\n".join([
        "[메인 이미지 촬영 브리프] SEORI 냉감패드 · amazon.de",
        f"검색어: {sqp.get('query', '')}",
        f"가설: {hypothesis_text}",
        "",
        f"A (현재, 유지): {listing.get('main_image', '')}",
        "B (새로 촬영): 펼친 패드를 45도 위에서, 한쪽 모서리를 살짝 들어 올려 단면 두께와 냉감 원단 결이 보이게",
        "",
        "필수 규칙",
        *[f"- {r}" for r in MEDIA_AB_RULES],
        "- 제품이 이미지의 85% 이상을 차지, 긴 변 1000px 이상 (확대 기능, 1600px 이상 권장)",
        "",
        f"고정 요소 (바꾸지 않음): 제목, 가격 €{listing.get('price', 0):.2f}, 쿠폰 없음",
        "납품: A/B 각 3컷 (보정 전 원본 + 흰 배경 보정본)",
    ])


def media_ab_sqp():
    """1번 리포트의 검색어 클릭 분석(sqp). 없으면 None."""
    report = store_get("report")
    sqp = report.get("sqp") if isinstance(report, dict) else None
    return sqp if isinstance(sqp, dict) and sqp.get("query") else None


def media_ab_plan_step():
    """하위 탭 ③ A/B 소재 준비: A/B 안, 메인 이미지 규칙, 촬영 브리프, 테스트 도구. 반드시 media_render() 안에서 부릅니다.
    가설은 하위 탭 ①에서 이미 보여 주므로 여기서는 다시 보여 주지 않습니다."""
    sqp = media_ab_sqp()
    if not sqp:
        st.caption("1. 분석 리포트 탭의 검색어 클릭 분석이 있어야 A/B 안을 만들 수 있어요.")
        return
    saved = store_get("hypothesis")
    saved_text = str(saved.get("text") or "").strip() if isinstance(saved, dict) else ""
    listing = sqp.get("listing") or {}

    st.markdown(f'<div class="media-desc">\'{sqp["query"]}\' 검색 · 노출 점유율 {sqp.get("imp_share")}% · '
                f'클릭 점유율 {sqp.get("click_share")}% · 배수 {sqp.get("ratio")}배 → 목표 {sqp.get("kpi_goal", 0.8)}배 이상 '
                f'({sqp.get("source", "")})</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("**A · 현재 (대조군)**")
            st.markdown(f"{listing.get('main_image', '')}  \n"
                        f'<span class="media-desc">{listing.get("main_image_issue", "")}</span>', unsafe_allow_html=True)
    with c2:
        with st.container(border=True):
            st.markdown("**B · 제안 (실험군)**")
            st.markdown("펼친 패드, 모서리를 살짝 들어 두께와 냉감 원단 질감이 보이는 각도  \n"
                        '<span class="media-desc">저가 제품과의 품질 차이(두께·원단)가 검색 결과에서 바로 보이게</span>',
                        unsafe_allow_html=True)
    st.markdown(f'<div class="media-desc">고정 요소: 흰 배경 실제 사진, 제목, 가격 €{listing.get("price", 0):.2f}, 쿠폰 없음 · '
                '대안(제목 앞에 OEKO-TEX·두께)은 이 테스트가 끝난 뒤 따로 진행</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.markdown("**메인 이미지 규칙 (아마존)**")
        st.markdown("\n".join(f"- {r}" for r in MEDIA_AB_RULES))
    with c2:
        st.markdown("**테스트 도구: Manage Your Experiments**")
        st.markdown("- 아마존 공식 A/B 도구. 메인 이미지, 제목, 불릿, 상세 설명, A+ 콘텐츠를 테스트할 수 있음\n"
                    "- 브랜드 등록과 충분한 트래픽이 필요하고, 상품당 한 번에 하나의 테스트만 가능\n"
                    "- 보통 4~10주 → 실제로는 성수기(5월) 전에 시작. 시연에서는 결과도 가상 데이터로 표시")

    brief = media_ab_brief(sqp, saved_text or "검색 결과 첫인상에서 두께·원단을 보여 주면 클릭 점유율 ÷ 노출 점유율이 오른다")
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

def media_ab_result_step():
    """하위 탭 ④ 결과·판정: 가상 결과 + 판정 (승자는 CTR, CVR은 안전장치) + 적용 전후 CAC."""
    if not MEDIA_AB_FILE.exists():
        st.caption("A/B 결과 파일이 아직 없어요. 테스트가 끝나면 data/ 폴더에 결과를 넣어 주세요.")
        return
    result = json.loads(MEDIA_AB_FILE.read_text(encoding="utf-8"))
    j = media_ab_judge(result)
    a, b = result["variants"]
    with st.container(border=True, key="media-ab-result"):
        st.markdown(f"**🧪 A/B 결과 ({result['source']})** · {result['period']}")
        c1, c2, c3 = st.columns(3)
        with c1:
            ui.kpi_card("CTR 배수 (시장 대비)", f"{j['ratio'][0]:.2f} → {j['ratio'][1]:.2f}배",
                        sub=f"CTR {j['ctr'][0] * 100:.2f}% → {j['ctr'][1] * 100:.2f}% · p={j['p_ctr']:.4f}")
        with c2:
            ui.kpi_card("CVR (안전장치)", f"{j['cvr'][0] * 100:.1f}% → {j['cvr'][1] * 100:.1f}%",
                        sub=f"{MEDIA_AB_CVR_TOLERANCE}%p 넘게 떨어지면 실패 · " + ("통과" if j["cvr_ok"] else "실패"))
        with c3:
            ui.kpi_card("승자", j["winner"], sub=(b["desc"] if j["b_wins"] else a["desc"]))
        st.dataframe([{"안": v["name"], "설명": v["desc"], "노출": f"{v['impressions']:,}", "클릭": f"{v['clicks']:,}",
                       "세션": f"{v['sessions']:,}", "판매 수량": f"{v['units']:,}"} for v in result["variants"]],
                     hide_index=True, width="stretch", key="media-ab-table-variants")

        before, after = result["cac"]["before"], result["cac"]["after"]

        def cac(x):
            return x["spend"] / x["new_to_brand_orders"]

        def acos(x):
            return x["spend"] / x["sales"] * 100

        st.markdown(f'<div class="media-desc">사업 효과 (가상): CAC(광고비 ÷ 신규 고객 주문) {before["label"]} €{cac(before):.1f} → '
                    f'{after["label"]} €{cac(after):.1f} · ACoS {acos(before):.0f}% → {acos(after):.0f}%. '
                    'A/B 승자는 CTR로 고르고, CAC는 적용 전후 4주 비교로만 확인합니다.</div>', unsafe_allow_html=True)
