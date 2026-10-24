# 3. 매체 제작 > 2단계: 결과·판정 (2단계 담당 · JY 브랜치)
# 1단계가 정한 A/B 설계(media_handoff_plan())와 A/B 결과 데이터(data/)로 승자를 판정하고,
# 판정 결과를 media_handoff_set_result()로 3단계에 넘깁니다. 화면은 media_stage2_render() 안에서만 그립니다.
# 이름 규칙: 함수 media_s2_..., 위젯 key·session_state 키·CSS class media-s2-...
import json
import math
from pathlib import Path

import streamlit as st

import ui_theme as ui
from modules.media.media_handoff import media_handoff_plan, media_handoff_set_result

MEDIA_S2_DIR = Path(__file__).resolve().parent   # 2단계 폴더 (data/ 경로 만들 때 사용)
MEDIA_S2_FILE = MEDIA_S2_DIR / "data" / "media_ab_result_dummy_202610.json"


def media_s2_rate_test(a_hit, a_n, b_hit, b_n):
    """두 비율 z-검정. (A 비율, B 비율, 양측 유의확률)"""
    ra, rb = a_hit / a_n, b_hit / b_n
    pooled = (a_hit + b_hit) / (a_n + b_n)
    se = math.sqrt(pooled * (1 - pooled) * (1 / a_n + 1 / b_n))
    z = (rb - ra) / se if se else 0.0
    return ra, rb, math.erfc(abs(z) / math.sqrt(2))


def media_s2_judge(result, cvr_tolerance):
    """승자 판정: CTR이 유의하게 높고, CVR이 기준(cvr_tolerance %p) 넘게 떨어지지 않은 쪽."""
    a, b = result["variants"]
    ctr_a, ctr_b, p_ctr = media_s2_rate_test(a["clicks"], a["impressions"], b["clicks"], b["impressions"])
    cvr_a, cvr_b, p_cvr = media_s2_rate_test(a["units"], a["sessions"], b["units"], b["sessions"])
    cvr_ok = (cvr_b - cvr_a) * 100 >= -cvr_tolerance
    win = ctr_b > ctr_a and p_ctr < 0.05 and cvr_ok
    mkt = result["market_ctr"]
    return {"ctr": (ctr_a, ctr_b), "p_ctr": p_ctr, "cvr": (cvr_a, cvr_b), "p_cvr": p_cvr, "cvr_ok": cvr_ok,
            "ratio": (ctr_a / mkt, ctr_b / mkt), "winner": b["name"] if win else a["name"], "b_wins": win}


def media_stage2_render():
    """하위 탭 '결과·판정': 가상 결과 + 판정 (승자는 CTR, CVR은 안전장치) + 적용 전후 CAC.
    반드시 media_render() 안에서 부릅니다."""
    plan = media_handoff_plan()
    if not MEDIA_S2_FILE.exists():
        st.caption("A/B 결과 파일이 아직 없어요. 테스트가 끝나면 media_stage2/data/ 폴더에 결과를 넣어 주세요.")
        return
    result = json.loads(MEDIA_S2_FILE.read_text(encoding="utf-8"))
    j = media_s2_judge(result, plan["cvr_tolerance"])
    a, b = result["variants"]

    # 3단계(솔루션 제안)로 넘기는 판정 결과 (모양은 media_handoff.py의 MEDIA_HANDOFF_RESULT_SAMPLE)
    media_handoff_set_result({"source": result["source"], "winner": j["winner"], "b_wins": j["b_wins"],
                              "kpi": list(j["ratio"]), "cvr": list(j["cvr"]), "cvr_ok": j["cvr_ok"],
                              "p_ctr": j["p_ctr"]})

    with st.container(border=True, key="media-s2-result"):
        st.markdown(f"**🧪 A/B 결과 ({result['source']})** · {result['period']}")
        c1, c2, c3 = st.columns(3)
        with c1:
            ui.kpi_card(f"{plan['kpi']} (시장 대비 CTR)", f"{j['ratio'][0]:.2f} → {j['ratio'][1]:.2f}배",
                        sub=f"CTR {j['ctr'][0] * 100:.2f}% → {j['ctr'][1] * 100:.2f}% · p={j['p_ctr']:.4f}")
        with c2:
            ui.kpi_card("CVR (안전장치)", f"{j['cvr'][0] * 100:.1f}% → {j['cvr'][1] * 100:.1f}%",
                        sub=f"{plan['cvr_tolerance']}%p 넘게 떨어지면 실패 · " + ("통과" if j["cvr_ok"] else "실패"))
        with c3:
            ui.kpi_card("승자", j["winner"], sub=(b["desc"] if j["b_wins"] else a["desc"]))
        st.dataframe([{"안": v["name"], "설명": v["desc"], "노출": f"{v['impressions']:,}", "클릭": f"{v['clicks']:,}",
                       "세션": f"{v['sessions']:,}", "판매 수량": f"{v['units']:,}"} for v in result["variants"]],
                     hide_index=True, width="stretch", key="media-s2-table-variants")

        before, after = result["cac"]["before"], result["cac"]["after"]

        def cac(x):
            return x["spend"] / x["new_to_brand_orders"]

        def acos(x):
            return x["spend"] / x["sales"] * 100

        st.markdown(f'<div class="media-desc">사업 효과 (가상): CAC(광고비 ÷ 신규 고객 주문) {before["label"]} €{cac(before):.1f} → '
                    f'{after["label"]} €{cac(after):.1f} · ACoS {acos(before):.0f}% → {acos(after):.0f}%. '
                    'A/B 승자는 CTR로 고르고, CAC는 적용 전후 4주 비교로만 확인합니다.</div>', unsafe_allow_html=True)
