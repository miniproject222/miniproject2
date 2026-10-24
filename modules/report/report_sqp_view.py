# 1. 분석 리포트 - 검색어 클릭 분석 화면 (report_render() 안에서 부름)
# 문제 문장 → 검색어별 점유율 비교 → 주별 흐름 → 1단계 문제 Top 3 → 원인 분석 → 데이터 출처·한계
from datetime import date, timedelta

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import ui_theme as ui

from modules.report.report_sqp import (
    REPORT_SQP_ALERT_WEEKS, REPORT_SQP_HEAT_DAYS, REPORT_SQP_HEAT_TEMP, REPORT_SQP_RATIO_ALERT,
    REPORT_SQP_TYPE_DIRECTION, report_sqp_main_reasons, report_sqp_month_range, report_sqp_statement,
)

REPORT_SQP_TYPE_LABEL = {"소재 개선": "보이는 만큼 안 눌림 (문제)", "노출 확대": "보이는 것보다 더 눌림",
                         "제외 검토": "검색 의도 다름", "": "정상"}


def report_sqp_source(text):
    """출처 표시 배지 (가상 / 실제 / 가정)."""
    return f'<span class="report-src">{text}</span>'


def report_sqp_show(sqp):
    """검색어 클릭 분석 전체. sqp는 report_sqp_analyze() 결과."""
    report_sqp_show_statement(sqp)
    report_sqp_show_queries(sqp)
    report_sqp_show_trend(sqp)
    report_sqp_show_problems(sqp)
    report_sqp_show_causes(sqp)
    report_sqp_show_sources(sqp)


def report_sqp_show_statement(sqp):
    with st.container(border=True):
        st.markdown(f"**📌 문제 문장** · amazon.de 검색어 성과 ({sqp['period']}) "
                    + report_sqp_source("노출·클릭: 가상"), unsafe_allow_html=True)
        st.markdown(f'<div class="report-statement">{report_sqp_statement(sqp)}</div>', unsafe_allow_html=True)
        st.markdown('<div class="report-desc">배수 = 클릭 점유율 ÷ 노출 점유율 = 우리 CTR ÷ 시장 CTR. '
                    '1배보다 낮으면 보이는 만큼 눌리지 않는다는 뜻입니다. 시장 평균은 특정 경쟁사가 아니라 검색어 전체 값입니다.</div>',
                    unsafe_allow_html=True)


def report_sqp_show_queries(sqp):
    with st.container(border=True):
        st.markdown(f"**🔎 검색어별 점유율 비교** · {len(sqp['queries'])}개 검색어, {sqp['weeks_count']}주 합계 "
                    + report_sqp_source("가상 SQP"), unsafe_allow_html=True)
        rows = []
        for x in sqp["queries"]:
            t = x["total"]
            rows.append({
                "검색어": x["query"], "검색량 순위": x["volume_rank"],
                "시장 CTR": f"{t['mkt_ctr'] * 100:.1f}%", "우리 CTR": f"{t['our_ctr'] * 100:.1f}%",
                "노출 점유율": f"{t['imp_share'] * 100:.1f}%", "클릭 점유율": f"{t['click_share'] * 100:.1f}%",
                "배수": f"{t['ratio']:.2f}배", f"{REPORT_SQP_RATIO_ALERT}배 미만 연속": f"{x['streak']}주",
                "클릭된 상품 중앙 가격": f"€{x['median_price']:.2f}",
                "판정": REPORT_SQP_TYPE_LABEL[x["type"]],
            })
        st.dataframe(rows, hide_index=True, width="stretch", key="report-sqp-table-queries")
        st.markdown(f'<div class="report-desc">감지 규칙: 배수 {REPORT_SQP_RATIO_ALERT}배 미만이 {REPORT_SQP_ALERT_WEEKS}주 이상 이어지면 문제 '
                    '(시작값, 데이터를 보며 조정) · CTR은 클릭 ÷ 노출로 직접 계산 (리포트의 클릭률 Click Rate는 클릭 ÷ 검색 횟수라 쓰지 않음)</div>',
                    unsafe_allow_html=True)


def report_sqp_show_trend(sqp):
    queries = [x["query"] for x in sqp["queries"]]
    with st.container(border=True):
        st.markdown("**📈 주별 흐름** · 배수 + 검색량 + 기온 + 경쟁사 이벤트 "
                    + report_sqp_source("기온: DWD 실제") + report_sqp_source(f"이벤트: {sqp['event_source']}"),
                    unsafe_allow_html=True)
        q = st.selectbox("검색어", queries, index=queries.index(sqp["main"]["query"]), key="report-sqp-query")
        x = next(v for v in sqp["queries"] if v["query"] == q)
        report_sqp_chart(x, sqp)
        st.markdown(f'<div class="report-desc">주황 점: 배수 {REPORT_SQP_RATIO_ALERT}배 미만 주 · 노란 띠: 폭염 주 '
                    f'(5개 도시 평균 최고기온 {REPORT_SQP_HEAT_TEMP:.0f}°C 이상인 날이 {REPORT_SQP_HEAT_DAYS}일 이상) · '
                    f'검색량 모양: {x["shape_source"]} · 경쟁사 할인 주에는 우리 클릭 점유율을 낮추고 품절 주에는 올린 시나리오 가정 '
                    f'(메인 검색어만)</div>', unsafe_allow_html=True)


def report_sqp_chart(x, sqp):
    weeks = [w["week"] for w in x["weeks"]]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.55, 0.45],
                        specs=[[{}], [{"secondary_y": True}]])
    for w in weeks:
        if sqp["temps"].get(w, {}).get("heat_days", 0) >= REPORT_SQP_HEAT_DAYS:
            d = date.fromisoformat(w)
            fig.add_vrect(x0=(d - timedelta(days=3)).isoformat(), x1=(d + timedelta(days=3)).isoformat(),
                          fillcolor=ui.PALETTE["peach"], opacity=0.45, line_width=0, layer="below", row="all", col=1)
    ratios = [w["ratio"] for w in x["weeks"]]
    fig.add_trace(go.Scatter(x=weeks, y=ratios, mode="lines+markers", name="배수 (클릭 ÷ 노출 점유율)",
                             line=dict(color=ui.THEME["primary"], width=2.5),
                             marker=dict(size=9, color=[ui.THEME["accent"] if r < REPORT_SQP_RATIO_ALERT
                                                        else ui.THEME["primary"] for r in ratios])), row=1, col=1)
    fig.add_hline(y=REPORT_SQP_RATIO_ALERT, line_dash="dash", line_color=ui.THEME["muted"], row=1, col=1,
                  annotation_text=f"기준 {REPORT_SQP_RATIO_ALERT}배", annotation_position="top left")
    fig.add_hline(y=1.0, line_dash="dot", line_color=ui.THEME["line"], row=1, col=1)
    for e in sqp["events"]:
        if e["week"] in weeks:
            fig.add_annotation(x=e["week"], y=max(ratios + [1.0]) * 1.08, text=f"{e['brand']} {e['kind']}", showarrow=False,
                               font=dict(size=10, color=ui.THEME["muted"]), row=1, col=1)
    fig.add_trace(go.Bar(x=weeks, y=[w["mkt_clk"] for w in x["weeks"]], name="시장 클릭 (검색량 크기)",
                         marker_color=ui.THEME["primary_soft"]), row=2, col=1)
    temps = [sqp["temps"].get(w, {}).get("avg") for w in weeks]
    fig.add_trace(go.Scatter(x=weeks, y=temps, mode="lines", name="평균 최고기온 °C (DWD)",
                             line=dict(color=ui.THEME["muted"], width=1.5, dash="dot")), row=2, col=1, secondary_y=True)
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10), legend=dict(orientation="h", y=-0.12),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=ui.THEME["text"]))
    fig.update_yaxes(title_text="배수", row=1, col=1, gridcolor=ui.THEME["line"])
    fig.update_yaxes(title_text="클릭", row=2, col=1, gridcolor=ui.THEME["line"])
    fig.update_yaxes(title_text="°C", row=2, col=1, secondary_y=True, showgrid=False)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key="report-sqp-chart-trend")


def report_sqp_show_problems(sqp):
    with st.container(border=True):
        st.markdown("**🎯 1단계 문제 Top 3** · 자동 판정 " + report_sqp_source("가상 SQP"), unsafe_allow_html=True)
        rows = []
        for i, x in enumerate(sqp["problems"], 1):
            lo_i, hi_i = report_sqp_month_range(x, "imp_share")
            lo_r, hi_r = report_sqp_month_range(x, "ratio")
            nums = f"노출 점유율 {lo_i * 100:.1f}~{hi_i * 100:.1f}%"
            if x["type"] == "소재 개선":
                lo_c, hi_c = report_sqp_month_range(x, "click_share")
                nums += f", 클릭 점유율 {lo_c * 100:.1f}~{hi_c * 100:.1f}%"
            rows.append({"순위": i, "검색어": x["query"], "수치 (월별 범위)": f"{nums}, 배수 {lo_r:.2f}~{hi_r:.2f}",
                         "유형": x["type"], "해결 방향": REPORT_SQP_TYPE_DIRECTION[x["type"]]})
        st.dataframe(rows, hide_index=True, width="stretch", key="report-sqp-table-problems")

        main = sqp["main"]
        st.markdown(f"**문제 1 (메인, 선정 추천)** · {main['query']}")
        st.markdown("".join(f'<div class="report-factor"><b>{title}</b><div class="report-desc">{text}</div></div>'
                            for title, text in report_sqp_main_reasons(sqp)), unsafe_allow_html=True)
        for x in sqp["problems"]:
            if x["type"] == "노출 확대":
                e = x["extra"]
                st.markdown(f'<div class="report-desc"><b>문제 2 · {x["query"]}</b>: 눌리는 힘은 있는데(배수 {x["total"]["ratio"]:.2f}배) '
                            f'덜 보여요(노출 점유율 {x["total"]["imp_share"] * 100:.1f}%). 노출 점유율을 {e["goal"] * 100:.0f}%로 올리면 '
                            f'{e["month"]}에만 약 {e["clicks"]:,.0f}회 클릭이 늘어요. 소재보다 광고 예산 문제라 소재 외 문제로 분류해요.</div>',
                            unsafe_allow_html=True)
            elif x["type"] == "제외 검토":
                st.markdown(f'<div class="report-desc"><b>문제 3 · {x["query"]}</b>: 클릭된 상품 중앙 가격이 €{x["median_price"]:.2f}로 '
                            f'우리(€{sqp["listing"]["price"]:.2f})보다 €{-x["price_gap"]:.0f} 비싼 두꺼운 토퍼를 찾는 검색어예요. '
                            '검색 의도가 달라서 가설 없이 광고 제외로 처리해요.</div>', unsafe_allow_html=True)


def report_sqp_show_causes(sqp):
    listing, main = sqp["listing"], sqp["main"]
    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.markdown("**🔎 원인: 내부** · 검색 결과에서 보이는 것 " + report_sqp_source("가상"), unsafe_allow_html=True)
            rivals = [c for c in sqp["competitors"] if c["source"] == "Keepa 실제" and c["reviews"]]
            most = max(rivals, key=lambda c: c["reviews"]) if rivals else None
            items = [
                ("메인 이미지", f"{listing['main_image']} → {listing['main_image_issue']}"),
                ("리뷰 수", f"{listing['reviews']}건 (평점 {listing['rating']:.1f})"
                           + (f" · {most['brand']} {most['reviews']:,}건 (Keepa 실제)보다 적음" if most else "")),
                ("가격", f"€{listing['price']:.2f} · 클릭된 상품 중앙 가격 €{main['median_price']:.2f}보다 €{main['price_gap']:+.0f}"),
                ("제목", listing["title"]),
            ]
            st.markdown("".join(f'<div class="report-factor"><b>{k}</b><div class="report-desc">{v}</div></div>'
                                for k, v in items), unsafe_allow_html=True)
            ads = sqp["ads"]
            if ads:
                st.markdown(f'<div class="report-desc">진단 (광고 리포트, 가상): 검색 상단 노출 비율 주별 {ads["top_min"] * 100:.0f}~'
                            f'{ads["top_max"] * 100:.0f}%로 고르게 유지 → 위치가 아니라 첫인상 문제 · CPC €{ads["cpc"]:.2f}, '
                            f'ACoS {ads["acos"] * 100:.0f}%, 주문당 광고비 €{ads["spend_per_order"]:.2f}</div>', unsafe_allow_html=True)
    with right:
        with st.container(border=True):
            st.markdown("**🌍 원인: 외부** · 경쟁 제품, 날씨 " + report_sqp_source("Keepa·DWD 실제"), unsafe_allow_html=True)
            st.dataframe([{"역할": c["role"], "브랜드": c["brand"],
                           "가격": f"€{c['price']:.2f}" if c["price"] else "-",
                           "우리와 차이": f"€{listing['price'] - c['price']:+.0f}" if c["price"] and c["role"] != "우리" else "-",
                           "평점": f"{c['rating']:.1f}" if c["rating"] else "-",
                           "리뷰": f"{c['reviews']:,}" if c["reviews"] is not None else "-",
                           "출처": c["source"], "메모": c["note"]} for c in sqp["competitors"]],
                         hide_index=True, width="stretch", key="report-sqp-table-rivals")
            events = " · ".join(f"{e['week']} {e['brand']} {e['detail']}" for e in sqp["events"])
            st.markdown(f'<div class="report-desc">경쟁사 할인·품절 ({sqp["event_source"]}): {events}</div>', unsafe_allow_html=True)
            heat = sqp["heat"]
            if heat:
                up = heat["clk_hot"] / heat["clk_cool"] - 1
                st.markdown(f'<div class="report-desc">폭염 주 {len(heat["weeks"])}개 (DWD 실제): 검색량(시장 클릭)은 다른 주보다 {up * 100:+.0f}%, '
                            f'우리 배수는 {heat["ratio_cool"]:.2f} → {heat["ratio_hot"]:.2f}배 '
                            f'({"오히려 줄었어요" if heat["ratio_hot"] < heat["ratio_cool"] else "줄지 않았어요"}). '
                            '폭염 주의 배수 변화는 경쟁사 할인 가정이 겹친 결과예요.</div>', unsafe_allow_html=True)
            st.caption("Keepa에는 노출·클릭 데이터가 없어 '왜 경쟁 제품이 더 눌렸는지'를 설명하는 데만 씁니다. "
                       "Keepa 리뷰 수 기록은 2025년 4월 이후 갱신되지 않아 현재 리뷰 수는 상품 페이지에서 직접 확인합니다.")


def report_sqp_show_sources(sqp):
    with st.expander("📚 데이터 출처와 한계, 발표 대비", expanded=False):
        st.dataframe([
            {"데이터": "검색어별 노출·클릭·장바구니·구매", "출처": "가상 (SP-API 검색어 성과 리포트 형식)",
             "파일": "data/report_sqp_weekly_dummy_202608.json"},
            {"데이터": "검색량 모양 (주별 오르내림)", "출처": sqp["main"]["shape_source"] + " (Google Trends CSV를 넣으면 교체)",
             "파일": "data/report_trends_google_*.csv"},
            {"데이터": "광고 성과", "출처": "가상 (스폰서드 프로덕트 리포트 형식)", "파일": "data/report_ads_keywords_dummy_202608.csv"},
            {"데이터": "우리 상품 정보", "출처": "가상", "파일": "data/report_listing_dummy_202608.json"},
            {"데이터": "경쟁 제품 가격·평점·리뷰", "출처": "Keepa 실제 (마지막 조회 스냅샷)", "파일": "data/report_keepa_snapshot.json"},
            {"데이터": "경쟁사 할인·품절 주", "출처": sqp["event_source"], "파일": "data/report_sqp_events_202608.json"},
            {"데이터": "일 최고기온 (베를린·함부르크·뮌헨·쾰른·프랑크푸르트)", "출처": "DWD 실제 (Bright Sky API)",
             "파일": "data/report_temp_dwd_202608.csv"},
        ], hide_index=True, width="stretch", key="report-sqp-table-sources")
        st.markdown(
            "- 더미는 모양·크기·사건을 실제 데이터에서 가져오고 우리 계정 안의 숫자만 채운 값입니다. "
            "할인 주에 우리 점유율을 낮춘 것은 정한 시나리오라 실제 인과처럼 말하지 않고, "
            "\"실제 계정을 연결하면 이런 패턴을 찾아낸다\"고 설명합니다.\n"
            "- 검색량 모양을 Google Trends로 바꾸면 구글 검색 기준 상대 지수라 아마존 안 검색과 모양이 비슷하다는 가정이 들어갑니다.\n"
            "- 더미를 다시 만들 때: `python -m modules.report.report_sqp_make`")
        st.dataframe([
            {"예상 질문": "시장 평균이 경쟁사인가요?", "답변": "아니요. 검색어 전체 값이에요. 특정 경쟁사 비교는 Keepa로 따로 해요."},
            {"예상 질문": "검색 결과 아래쪽에 나오면 원래 덜 눌리지 않나요?",
             "답변": "맞아요. 그래서 광고 리포트의 검색 상단 노출 비율을 같이 보고, 위치가 비슷한 주끼리 비교해요."},
            {"예상 질문": "Keepa로 클릭률을 알 수 있나요?", "답변": "없어요. 노출·클릭은 판매자 계정(검색어 성과)에서만 나와요."},
            {"예상 질문": "데이터는 진짜인가요?", "답변": "노출·클릭은 가상, 경쟁 제품·기온은 Keepa·DWD 실제 값이에요. 화면에 표시해요."},
        ], hide_index=True, width="stretch", key="report-sqp-table-faq")
