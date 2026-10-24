# 1. 분석 리포트 (실제 데이터만 표시, 샘플 없음)
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

import ui_theme as ui

from common.common_store import store_set
from modules.report.report_data import REPORT_UTM_MIN_SHARE, report_load_data, report_utm_rows
from modules.report.report_download import report_download_pdf
from modules.report.report_ga4 import REPORT_SHOP_URL, report_utm_link
from modules.report.report_keepa import (
    report_keepa_can_fetch, report_keepa_estimate, report_keepa_fetch_and_save, report_keepa_usage,
)

REPORT_DIR = Path(__file__).resolve().parent   # 내 폴더 (images/, data/ 경로 만들 때 사용)

REPORT_LEVEL_DOTS = {"높음": "●●●", "중간": "●●○", "낮음": "●○○"}
REPORT_LEVEL_CLASS = {"높음": "high", "중간": "mid", "낮음": "low"}


def report_render():
    """'1. 분석 리포트' 탭을 열 때마다 실행됩니다. 화면은 전부 이 함수 안에서 그립니다."""
    data = report_load_data()
    ga4 = data["ga4"]
    steps = report_funnel_steps(ga4["funnel"]) if ga4 else []
    worst = min(steps, key=lambda s: s["diff"]) if steps else None
    utm_rows, utm_worst = report_utm_rows(ga4["utm"]) if ga4 else ([], None)
    summary = report_build_summary(data, worst)
    report_save_store(data, summary, worst, utm_rows, utm_worst)

    ui.page_header("1. 분석 리포트", "결과 데이터 요약, 문제 분석 (실제 데이터: 경쟁사 DB·독일 DB·Keepa·Open-Meteo"
                                      + (" · GA4)" if ga4 else ") · 매출·퍼널·유입 채널은 GA4 연결 후 표시"))
    if data["source_error"]:
        st.caption(f"GA4 연결 실패: {data['source_error']}")

    kpis = report_ga4_kpis(ga4) if ga4 else data["position_kpis"]
    report_show_kpis(kpis)

    left, right = st.columns(2)
    with left:
        report_show_internal(data, steps, worst)
    with right:
        report_show_external(data)

    report_show_competitors(data)
    report_show_utm(utm_rows, utm_worst, bool(ga4))
    report_show_ab(data["ab_tests"])

    report_show_key_problems(data, summary, kpis, steps, utm_rows)


def report_pct(part, whole):
    """비율(%) 계산. 분모가 0이면 0 (GA4를 막 연결해 지난 기간 데이터가 없을 때)."""
    return part / whole * 100 if whole else 0.0


def report_funnel_steps(funnel):
    """퍼널 단계 사이(이전 → 다음)마다 이번 기간/지난 기간 전환율과 차이를 계산합니다."""
    steps = []
    for a, b in zip(funnel, funnel[1:]):
        now = report_pct(b["now"], a["now"])
        prev = report_pct(b["prev"], a["prev"])
        steps.append({"name": f"{a['stage']} → {b['stage']}", "to": b["stage"],
                      "now": now, "prev": prev, "diff": now - prev})
    return steps


def report_build_summary(data, worst):
    """핵심 문제 요약: 내부 1순위 + 외부 위협 1순위 (+ GA4 퍼널이 있으면 가장 떨어진 단계)."""
    parts = []
    if data["internal"]:
        parts.append(f"내부: {data['internal'][0]['title']}")
    if worst:
        parts.append(f"퍼널: '{worst['name']}' 전환율 {worst['prev']:.1f}% → {worst['now']:.1f}%")
    threat = next((f for f in data["external"] if f["kind"] == "위협"), None)
    if threat:
        parts.append(f"외부 위협: {threat['title']}")
    return " / ".join(parts) or "표시할 데이터가 없습니다."


def report_save_store(data, summary, worst, utm_rows, utm_worst):
    """홈·가설·광고 소재·광고 타이밍 탭이 읽을 결과를 저장합니다. 내용이 바뀔 때만 다시 저장합니다.
    매출 값(yesterday_sales 등)은 실제 매출 데이터(GA4)가 없어서 넣지 않습니다."""
    payload = {
        # 공통 (홈: problems / 가설: key_problems·problems·opportunities)
        "summary": summary,
        "key_problems": data["key_problems"],          # 핵심 문제 Top 3 + 가설용 질문(question)
        "problems": data["problems"],                  # 핵심 문제 Top 3가 맨 앞 + 나머지 (가설 탭은 problems[0] 사용)
        "opportunities": [{"title": f["title"], "level": f["level"], "detail": f["detail"]}
                          for f in data["external"] if f["kind"] == "기회"],
        # 가설·광고 소재: 서리·경쟁사 프로필 (경쟁사 약점 → 우리 홍보 포인트), 표현 규칙
        "seori_profile": data["seori_profile"],
        "competitor_profiles": data["competitor_profiles"],
        "marketing_rules": data["marketing_rules"],
        # 광고 타이밍: 경쟁사 품절·가격 변화 (Keepa 마지막 조회)
        "competitor_signals": data["competitor_signals"],
        "competitors": data["competitors"],            # 간단 비교표 (열 6개)
        # GA4·A/B (연결·결과가 있을 때만 값이 들어감)
        "funnel_worst": worst["name"] if worst else "",
        "utm": utm_rows,
        "utm_worst": utm_worst["channel"] if utm_worst else "",
        "ab_tests": [{"name": t["name"], "winner": t["result"]["winner"], "lift": round(t["result"]["lift"], 1),
                      "p_value": round(t["result"]["p"], 4), "significant": t["result"]["significant"]}
                     for t in data["ab_tests"]],
        "data_source": "경쟁사 DB·독일 DB·Keepa·Open-Meteo" + (" · GA4" if data["ga4"] else ""),
    }
    if st.session_state.get("report-stored-payload") != payload:
        store_set("report", payload)
        st.session_state["report-stored-payload"] = payload


def report_show_key_problems(data, summary, kpis, steps, utm_rows):
    """문제 도출: 핵심 문제 Top 3 (근거 + 가설 탭에서 다룰 질문) + PDF 리포트 다운로드."""
    key_problems = data["key_problems"]
    with st.container(border=True):
        st.markdown(f"**🎯 문제 도출** · 핵심 문제 Top {len(key_problems)}  \n"
                    f'<span class="report-desc">요약: {summary}</span>', unsafe_allow_html=True)
        for p in key_problems:
            st.markdown(
                f'<div class="report-factor">'
                f'<span class="report-level report-level-{REPORT_LEVEL_CLASS[p["level"]]}">{p["rank"]}순위 · {p["type"]}</span>'
                f'<span class="report-tag">{p["group"]}</span><b>{p["title"]}</b>'
                f'<div class="report-desc">근거: {p["detail"]}</div>'
                f'<div class="report-desc">→ 가설 탭 질문: <b>{p["question"]}</b></div></div>',
                unsafe_allow_html=True,
            )
        st.caption("이 결과는 다른 탭(홈, 가설, 광고 소재, 광고 타이밍)에서 store_get(\"report\")로 읽을 수 있습니다.")
        report_download_pdf(data, kpis, summary, steps, utm_rows)


def report_ga4_kpis(ga4):
    """GA4 연결 시 KPI 4개: 방문, 주문, 전환율(이전 기간 대비), 매출."""
    funnel, utm = ga4["funnel"], ga4["utm"]
    visits, orders = funnel[0], funnel[-1]
    conv_now, conv_prev = report_pct(orders["now"], visits["now"]), report_pct(orders["prev"], visits["prev"])

    def delta(now, prev):
        return f"{report_pct(now, prev) - 100:+.0f}%" if prev else "이전 기간 없음"

    return [
        {"label": "방문 (30일)", "value": f"{visits['now']:,}", "badge": delta(visits["now"], visits["prev"]),
         "good": visits["now"] >= visits["prev"]},
        {"label": "주문 (30일)", "value": f"{orders['now']:,}", "badge": delta(orders["now"], orders["prev"]),
         "good": orders["now"] >= orders["prev"]},
        {"label": "전환율", "value": f"{conv_now:.2f}%", "badge": f"{conv_now - conv_prev:+.2f}%p",
         "good": conv_now >= conv_prev},
        {"label": "매출 (30일)", "value": f"€{sum(r['revenue'] for r in utm):,}", "badge": "GA4", "good": True},
    ]


def report_show_kpis(kpis):
    """한 줄 높이의 작은 KPI 카드 (아래 분석 내용이 첫 화면에 보이도록)."""
    for col, k in zip(st.columns(len(kpis) or 1), kpis):
        with col:
            badge = f'<span class="ui-delta {"up" if k["good"] else "down"}">{k["badge"]}</span>' if k["badge"] else ""
            st.markdown(f'<div class="report-kpi"><span class="report-kpi-label">{k["label"]}</span>'
                        f'<span class="report-kpi-value">{k["value"]}</span>{badge}</div>', unsafe_allow_html=True)


def report_show_internal(data, steps, worst):
    """내부 요인: 서리가 경쟁사 대비 부족한 점 (+ GA4가 있으면 구매 퍼널)."""
    with st.container(border=True):
        st.markdown("**🔎 내부 요인** · 서리가 경쟁사 대비 부족한 점")
        if worst:
            report_show_funnel(data["ga4"]["funnel"], worst)
        st.markdown("".join(report_factor_html(f, f["group"]) for f in data["internal"]), unsafe_allow_html=True)
        if not worst:
            st.caption("구매 퍼널(어느 단계에서 이탈하는지)은 GA4 연결 후 함께 표시됩니다.")


def report_show_funnel(funnel, worst):
    # 오렌지(accent)는 화면당 1곳: 가장 크게 떨어진 단계에만 사용 (design.md 2-3)
    colors = [ui.THEME["accent"] if f["stage"] == worst["to"] else ui.THEME["primary_soft"] for f in funnel]
    colors[0] = ui.THEME["primary"]
    fig = go.Figure(go.Funnel(y=[f["stage"] for f in funnel], x=[f["now"] for f in funnel],
                              textinfo="value+percent previous", marker=dict(color=colors),
                              connector=dict(fillcolor=ui.THEME["line"])))
    fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=ui.THEME["text"]))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key="report-chart-funnel")
    st.markdown(f'<div class="report-desc">이전 기간보다 가장 크게 떨어진 단계: <b>{worst["name"]}</b> '
                f'({worst["prev"]:.1f}% → {worst["now"]:.1f}%, {worst["diff"]:+.1f}%p, GA4)</div>',
                unsafe_allow_html=True)


def report_show_external(data):
    """외부 요인: 위협(문제)과 기회를 나눠서 표시."""
    with st.container(border=True):
        st.markdown("**🌍 외부 요인** · 경쟁사, 날씨, 시장, 플랫폼, 규제")
        for kind in ("위협", "기회"):
            items = [f for f in data["external"] if f["kind"] == kind]
            if items:
                st.markdown(f"**{'⚠️ 위협' if kind == '위협' else '✨ 기회'}** ({len(items)})")
                st.markdown("".join(report_factor_html(f, f["group"]) for f in items), unsafe_allow_html=True)


def report_show_competitors(data):
    """경쟁사 DB + Keepa 비교표, 경쟁우위 항목별 점수, 브랜드별 강점·약점."""
    rows = data["competitors_full"]
    with st.container(border=True):
        st.markdown(f"**🏷 경쟁사 비교** · 경쟁사 DB + Keepa(Amazon.de)  \n"
                    f'<span class="report-desc">{data["keepa_status"]} · 화면을 열 때는 Keepa를 호출하지 않음</span>',
                    unsafe_allow_html=True)
        report_show_keepa_fetch()
        if not rows:
            st.info("공통 경쟁사 DB(data/common_competitor_seori_202610.csv)가 없습니다.")
            return
        table = []
        for r in rows:
            k = r.get("keepa") or {}
            sign = "€" if r["currency"] == "EUR" else r["currency"] + " "
            table.append({
                "구분": r["kind"], "브랜드": r["brand"], "유형": r["type"],
                "DB 판매가": f"{sign}{r['db_price']:.2f}" if r["db_price"] else "-",
                "Amazon 현재가": f"€{k['price']:.2f}" if k.get("price") else ("품절" if k else "-"),
                "90일 평균 대비": f"{k['change'] * 100:+.0f}%" if k.get("change") is not None else "-",
                "평점": f"{k['rating']:.1f}" if k.get("rating") else "-",
                "리뷰 수": f"{k['reviews']:,}" if k.get("reviews") is not None else "-",
                "판매 순위": f"{k['rank']:,}" if k.get("rank") else "-",
                "㎡당 가격": (f"€{r['keepa_sqm']:.1f}" if r.get("keepa_sqm")
                            else f"{sign}{r['sqm_price']:.1f}" if r["sqm_price"] else "-"),
                "Q-max": r["qmax"] or "-",
                "경쟁우위 점수": f"{r['score']:.2f}" if r["score"] else "-",
                "ASIN": r["asin"] or "-",
            })
        st.dataframe(table, hide_index=True, width="stretch", key="report-table-competitors")
        st.markdown('<div class="report-desc">㎡당 가격: Keepa 현재가가 있으면 Amazon 가격 기준, 없으면 DB 기준 · '
                    '경쟁우위 점수: DB 경쟁우위 비교 시트 가중 합계(5점 만점, 서리는 목표치)</div>',
                    unsafe_allow_html=True)
        with st.expander("경쟁우위 항목별 점수 (서리 목표 vs 경쟁사 최고)", expanded=False):
            st.dataframe([{"항목": c["item"], "가중치": f"{c['weight']:.0%}", "서리 (목표)": c["seori"],
                           "경쟁사 최고": f"{c['best_brand']} {c['best']:.0f}",
                           "차이": f"{c['seori'] - c['best']:+.0f}" if c["seori"] is not None else "-", "메모": c["memo"]}
                          for c in data["criteria"]], hide_index=True, width="stretch", key="report-table-criteria")
        with st.expander("브랜드별 강점·약점 (경쟁사 DB)", expanded=False):
            for r in rows:
                st.markdown(f"**{r['brand']}** · {r['product']}  \n"
                            f'<span class="report-desc">강점: {r["strength"]}<br>약점: {r["weakness"]}</span>',
                            unsafe_allow_html=True)


def report_show_keepa_fetch():
    """Keepa 최신값 조회: 예상 토큰·남은 한도 안내 → PIN + 동의 → 1회 조회. (토큰 한도 보호)"""
    usage = report_keepa_usage()
    left = usage["budget"] - usage["used"]
    with st.expander(f"🔄 Keepa 최신값 조회 (남은 한도 {left}/{usage['budget']}토큰)", expanded=False):
        ok, reason = report_keepa_can_fetch()
        st.caption(f"이번 조회 예상 사용량: 약 {report_keepa_estimate()}토큰 · 꼭 필요할 때만 조회하세요.")
        if not ok:
            st.caption(f"조회 불가: {reason}")
        else:
            pin = st.text_input("확인 PIN", type="password", key="report-keepa-pin")
            agree = st.checkbox(f"약 {report_keepa_estimate()}토큰을 사용해 조회하는 데 동의합니다", key="report-keepa-agree")
            if st.button("Keepa 조회 실행", key="report-btn-keepa-fetch", disabled=not (pin and agree)):
                try:
                    used = report_keepa_fetch_and_save(pin)
                    st.success(f"조회했습니다. 사용 토큰 {used}")
                    st.rerun()
                except Exception as err:   # RuntimeError만 문구를 보여 주고, 그 밖의 오류는 종류만 (키 노출 방지)
                    st.error(str(err) if isinstance(err, RuntimeError) else f"조회 실패 ({type(err).__name__})")
        st.caption("사용 기록: " + " / ".join(f"{x['date']} {x['tokens']}토큰 ({x['what']})" for x in usage["log"]))


def report_show_ab(ab_tests):
    """해결안 A/B 테스트: 실제 결과가 있을 때만 표시 (data/report_ab_tests.json)."""
    with st.container(border=True):
        st.markdown("**🧪 해결안 A/B 테스트** · 문제 → 해결안 A vs B → 결과")
        if not ab_tests:
            st.caption("아직 진행한 A/B 테스트 결과가 없습니다. 실제 결과를 modules/report/data/report_ab_tests.json에 "
                       "넣으면 전환율, 차이, 유의확률(두 비율 z-검정)을 계산해 표시합니다.")
            return
        for i, t in enumerate(ab_tests):
            a, b = t["variants"]
            r = t["result"]
            st.markdown(f'<div class="report-desc"><b>{t["name"]}</b> · 문제: {t["problem"]} · 가설: {t["hypothesis"]} · '
                        f'지표: {t["metric"]} · 기간: {t["period"]}</div>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                ui.kpi_card(a["name"], f"{r['rate_a']:.1f}%", sub=f"{a['desc']} · {a['conversions']:,}/{a['users']:,}")
            with c2:
                ui.kpi_card(b["name"], f"{r['rate_b']:.1f}%", f"{r['lift']:+.1f}%",
                            sub=f"{b['desc']} · {b['conversions']:,}/{b['users']:,}")
            with c3:
                ui.kpi_card("유의확률 (p)", f"{r['p']:.4f}",
                            sub="유의수준 0.05 기준 " + ("유의함" if r["significant"] else "유의하지 않음"))


def report_show_utm(utm_rows, utm_worst, connected):
    """유입 채널(UTM)별 성과 표 (GA4 연결 시) + 광고 링크(UTM) 만들기."""
    with st.container(border=True):
        st.markdown("**📊 유입 채널 (UTM)** · 어느 광고 채널이 구매로 이어지는지")
        if connected and utm_rows:
            total_sessions = sum(r["sessions"] for r in utm_rows) or 1
            total_cvr = sum(r["orders"] for r in utm_rows) / total_sessions * 100
            st.markdown(f'<span class="report-desc">GA4 최근 30일 · 전체 전환율 {total_cvr:.2f}%</span>',
                        unsafe_allow_html=True)
            st.dataframe([{"채널 (source / medium)": r["channel"], "캠페인": r["campaign"], "방문": f"{r['sessions']:,}",
                           "주문": f"{r['orders']:,}", "매출 (€)": f"{r['revenue']:,}", "전환율": f"{r['cvr']:.2f}%",
                           "방문 비중": f"{r['share']:.0f}%", "비고": "▼ 전환율 최저" if r is utm_worst else ""}
                          for r in utm_rows], hide_index=True, width="stretch", key="report-table-utm")
            if utm_worst:
                st.markdown(f'<div class="report-desc">전환율이 가장 낮은 채널: <b>{utm_worst["channel"]}</b> '
                            f'(전환율 {utm_worst["cvr"]:.2f}%, 방문 비중 {utm_worst["share"]:.0f}%) '
                            f'· 방문 비중 {REPORT_UTM_MIN_SHARE * 100:.0f}% 미만 채널은 판정에서 제외</div>',
                            unsafe_allow_html=True)
        else:
            st.caption("GA4가 연결되면 채널별 방문·주문·매출·전환율이 표시됩니다. 지금은 아래에서 광고 링크를 만들어 두세요.")

        with st.expander("🔗 광고 링크(UTM) 만들기", expanded=False):
            st.caption("광고 링크 끝에 UTM을 붙이면 GA4가 유입 채널을 자동으로 나눕니다. "
                       "값은 영어 소문자, 띄어쓰기 대신 _ 를 씁니다.")
            base = st.text_input("자사몰 주소", value=REPORT_SHOP_URL, key="report-utm-base")
            c1, c2, c3, c4 = st.columns(4)
            source_in = c1.text_input("utm_source", "instagram", key="report-utm-source")
            medium_in = c2.text_input("utm_medium", "paid_social", key="report-utm-medium")
            campaign_in = c3.text_input("utm_campaign", "", key="report-utm-campaign", placeholder="예: summer_2027")
            content_in = c4.text_input("utm_content (선택)", "", key="report-utm-content")
            link = report_utm_link(base.strip(), source_in, medium_in, campaign_in, content_in)
            if link:
                st.code(link, language=None)
            else:
                st.caption("자사몰 주소와 utm_source·utm_medium·utm_campaign을 넣으면 링크가 만들어집니다.")


def report_factor_html(item, group=""):
    level = item["level"]
    tag = f'<span class="report-tag">{group}</span>' if group else ""
    return (
        f'<div class="report-factor">'
        f'<span class="report-level report-level-{REPORT_LEVEL_CLASS[level]}">{REPORT_LEVEL_DOTS[level]} {level}</span>'
        f'{tag}<b>{item["title"]}</b>'
        f'<div class="report-desc">{item["detail"]}</div>'
        f'</div>'
    )
