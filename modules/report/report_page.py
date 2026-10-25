# 1. 문제 분석 (검색어 클릭 분석은 가상 SQP + 실제 Keepa·DWD, 경쟁 포지션 분석은 실제 데이터만)
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

import ui_theme as ui

from common.common_store import store_set
from modules.report.report_ab import REPORT_AB_TEMPLATE, report_ab_analyze, report_ab_p, report_ab_parse_csv, report_ab_verdict
from modules.report.report_competitor import REPORT_SEORI_PROXY
from modules.report.report_data import report_load_data, report_utm_rows
from modules.report.report_download import report_download_pdf
from modules.report.report_keepa import (
    report_keepa_can_fetch, report_keepa_detail, report_keepa_estimate, report_keepa_fetch_and_save, report_keepa_usage,
)
from modules.report.report_sqp import report_sqp_kpis
from modules.report.report_sqp_view import report_sqp_show

REPORT_DIR = Path(__file__).resolve().parent   # 내 폴더 (images/, data/ 경로 만들 때 사용)

REPORT_LEVEL_DOTS = {"높음": "●●●", "중간": "●●○", "낮음": "●○○"}
REPORT_LEVEL_CLASS = {"높음": "high", "중간": "mid", "낮음": "low"}
REPORT_FACTOR_HEIGHT = 250   # 내부·외부 요인 카드 높이(px): 두 카드를 같게 고정 (결과 박스와 함께 한 화면에 들어오도록)
REPORT_FACTOR_ORDER = {"높음": 0, "중간": 1, "낮음": 2}


def report_render():
    """'1. 분석 리포트' 탭을 열 때마다 실행됩니다. 화면은 전부 이 함수 안에서 그립니다."""
    data = report_load_data()
    ga4, sqp = data["ga4"], data["sqp"]
    steps = report_funnel_steps(ga4["funnel"]) if ga4 else []
    worst = min(steps, key=lambda s: s["diff"]) if steps else None
    utm_rows, utm_worst = report_utm_rows(ga4["utm"]) if ga4 else ([], None)
    summary = report_build_summary(data, worst)
    report_save_store(data, summary, worst, utm_rows, utm_worst)

    ui.page_header("1. 문제 분석", "노출·클릭: 가상 SQP · 경쟁 제품: Keepa 실제 · 기온: DWD 실제")
    if data["source_error"]:
        st.caption(f"GA4 연결 실패: {data['source_error']}")

    position_kpis = report_ga4_kpis(ga4) if ga4 else data["position_kpis"]
    kpis = report_sqp_kpis(sqp) if sqp else position_kpis

    # 본문: 문제 분석 결과(1·2순위) → 내부·외부 요인. 세부 내용은 오른쪽 끝 아이콘을 누르면 지금 화면 위에 창으로 열림
    report_show_key_problems(data)
    left, right = st.columns(2)
    with left:
        report_show_internal(data)
    with right:
        report_show_external(data)

    # 오른쪽 끝 아이콘 (① 탭 안에서만 보이고 화면에 고정: report_style.css .st-key-report-side)
    # 아이콘: 테마 색 한 가지로 보이는 Material 아이콘 (마우스를 올리면 이름)
    # 마우스를 올렸을 때 이름은 report_style.css의 말풍선 (.st-key-report-btn-side-이름)
    buttons = [("pdf", ":material/picture_as_pdf:", report_dialog_problems, (data, summary, kpis, steps, utm_rows)),
               ("sqp", ":material/manage_search:", report_dialog_sqp, (sqp, kpis)),
               ("comp", ":material/leaderboard:", report_dialog_competitors, (data, position_kpis, sqp)),
               ("ab", ":material/science:", report_dialog_ab, (data,))]
    if worst:
        buttons.insert(2, ("funnel", ":material/filter_alt:", report_dialog_funnel, (ga4["funnel"], worst)))
    with st.container(key="report-side"):
        for name, icon, dialog, args in buttons:
            if st.button("", icon=icon, key=f"report-btn-side-{name}", type="tertiary"):
                dialog(*args)


@st.dialog("핵심 문제 전체 · 리포트 다운로드", width="large", icon=":material/picture_as_pdf:")
def report_dialog_problems(data, summary, kpis, steps, utm_rows):
    with st.container(key="report-dialog-body-pdf"):
        report_show_problem_rest(data, summary, kpis, steps, utm_rows)


@st.dialog("검색어 클릭 분석 (노출·클릭: 가상 SQP)", width="large", icon=":material/manage_search:")
def report_dialog_sqp(sqp, kpis):
    with st.container(key="report-dialog-body-sqp"):
        with st.container(key="report-dialog-kpis-sqp"):   # 창 안에서 스크롤해도 KPI 줄은 위에 고정
            report_show_kpis(kpis)
        if sqp:
            report_sqp_show(sqp)
        else:
            st.info("검색어 성과 더미(data/report_sqp_weekly_dummy_202608.json)가 없습니다. "
                    "python -m modules.report.report_sqp_make 로 만들어 주세요.")


@st.dialog("구매 퍼널 (GA4)", width="large", icon=":material/filter_alt:")
def report_dialog_funnel(funnel, worst):
    with st.container(key="report-dialog-body-funnel"):
        report_show_funnel(funnel, worst)


@st.dialog("경쟁 포지션 · 경쟁사 비교", width="large", icon=":material/leaderboard:")
def report_dialog_competitors(data, position_kpis, sqp):
    with st.container(key="report-dialog-body-comp"):
        if sqp:
            with st.container(key="report-dialog-kpis-comp"):   # 창 안에서 스크롤해도 KPI 줄은 위에 고정
                report_show_kpis(position_kpis)
        report_show_competitors(data)


@st.dialog("해결안 A/B 테스트", width="large", icon=":material/science:")
def report_dialog_ab(data):
    with st.container(key="report-dialog-body-ab"):
        report_show_ab(data["ab_tests"], data["ab_daily"], data["ab_upload"])


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
    """핵심 문제 요약: 검색어 클릭 문제 1순위 + 내부 1순위 + 외부 위협 1순위 (+ GA4 퍼널이 있으면 가장 떨어진 단계)."""
    parts = []
    if data["sqp_store"]:
        s = data["sqp_store"]
        parts.append(f"검색 클릭: '{s['query']}' 클릭 ÷ 노출 {s['ratio']:.2f}배, 놓친 클릭 약 {s['missed_clicks']:,}회 (가상 SQP)")
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
        # 가설·광고 소재: 검색어 클릭 분석 (문제 1 수치, 우리 상품, 경쟁 제품, 문제 2) / 없으면 None
        "sqp": data["sqp_store"],
        # 리뷰 분석 (내부 요인 '리뷰' 문제의 근거·목표) / 해결안 A/B 아침 분석 (③ 탭 결과)
        "review_analysis": data["review_analysis"],
        "cooling_sales": data["cooling_sales"],     # 냉감패드 실적만 (하위 카테고리·여름 순위·판매 신호)
        "ab_daily": data["ab_daily"],               # [보류] ③ 탭 결과 아침 분석 (지금은 None)
        "ab_upload": data["ab_upload"],             # 직접 올린 A/B 결과 파일 분석
        # ③ 광고 소재: 나중에 광고에 넣을 서리 문구 (독일어·한국어, 필수 표기, 금지 표현)
        "ad_claims": data["ad_claims"],
        "data_rules": data["data_rules"],            # 지표별 비교 기준·출처·날짜·구분(실제/가정/가상)·신선도
        "data_source": ("검색어 성과 가상 SQP · DWD · " if data["sqp_store"] else "")
                       + "경쟁사 DB·독일 DB·Keepa·Open-Meteo" + (" · GA4" if data["ga4"] else ""),
    }
    if st.session_state.get("report-stored-payload") != payload:
        store_set("report", payload)
        st.session_state["report-stored-payload"] = payload


def report_problem_html(p):
    return (f'<div class="report-factor">'
            f'<span class="report-level report-level-{REPORT_LEVEL_CLASS[p["level"]]}">{p["rank"]}순위 · {p["type"]}</span>'
            f'<span class="report-tag">{p["group"]}</span><b>{p["title"]}</b>'
            f'<div class="report-desc">근거: {p["detail"]}</div>'
            f'<div class="report-desc">→ 가설 탭 질문: <b>{p["question"]}</b></div></div>')


def report_row_html(badge, tag, title, detail, extra=""):
    """읽기 쉬운 한 줄: 왼쪽 배지, 오른쪽 [분류] 제목 / 근거 2줄 (마우스를 올리면 전체) / 덧붙임."""
    full = str(detail).replace('"', "&quot;")
    return (f'<div class="report-row"><div class="report-row-badge">{badge}</div><div>'
            f'<div class="report-row-title"><span class="report-tag">{tag}</span>{title}</div>'
            f'<div class="report-desc report-clamp" title="{full}">{detail}</div>{extra}</div></div>')


def report_show_key_problems(data):
    """문제 분석 결과: 핵심 문제 1·2순위를 한 박스에 세로로. 전체(3순위)·PDF는 오른쪽 PDF 아이콘."""
    with st.container(border=True, key="report-card-result"):
        st.markdown(':material/flag: **문제 분석 결과** <span class="report-desc">핵심 문제 1·2순위 → ② 가설 탭에서 사용</span>',
                    unsafe_allow_html=True)
        st.markdown("".join(
            report_row_html(f'<span class="report-level report-level-{REPORT_LEVEL_CLASS[p["level"]]}">{p["rank"]}순위 · {p["type"]}</span>',
                            p["group"], p["title"], f'근거: {p["detail"]}',
                            f'<div class="report-row-q">→ 가설 탭 질문: <b>{p["question"]}</b></div>')
            for p in data["key_problems"][:2]), unsafe_allow_html=True)


def report_show_problem_rest(data, summary, kpis, steps, utm_rows):
    """토글 안: 핵심 문제 전체, 경쟁 포지션 핵심 문제, PDF 리포트 다운로드."""
    with st.container(border=True):
        st.markdown("".join(report_problem_html(p) for p in data["key_problems"]), unsafe_allow_html=True)
        if data["sqp"]:
            st.markdown('<div class="report-desc">경쟁 포지션 분석의 핵심 문제 (출시 준비): '
                        + " / ".join(p["title"] for p in data["position_key_problems"]) + "</div>", unsafe_allow_html=True)
        st.caption("이 결과는 다른 탭(홈, 가설, 광고 소재, 광고 타이밍)에서 store_get(\"report\")로 읽을 수 있습니다.")
        with st.expander(":material/rule: 데이터 기준·신뢰도 (같은 지표는 항상 같은 기준으로 계산)", expanded=False):
            st.dataframe(data["data_rules"], hide_index=True, width="stretch", key="report-table-data-rules")
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
            tip = str(k.get("tip") or k["badge"]).replace('"', "&quot;")
            badge = (f'<span class="ui-delta {"up" if k["good"] else "down"}" title="{tip}">{k["badge"]}</span>'
                     if k["badge"] else "")
            st.markdown(f'<div class="report-kpi" title="{tip}"><span class="report-kpi-label">{k["label"]}</span>'
                        f'<span class="report-kpi-value">{k["value"]}</span>{badge}</div>', unsafe_allow_html=True)


def report_factor_split(items):
    """심각도 순으로 상위 2개, 3번째도 '높음'이면 3개까지. 나머지는 더보기."""
    ordered = sorted(items, key=lambda f: REPORT_FACTOR_ORDER[f["level"]])
    top = ordered[:2] + [f for f in ordered[2:3] if f["level"] == "높음"]
    return top, ordered[len(top):]


def report_factor_row(f, tag):
    return report_row_html(f'<span class="report-level report-level-{REPORT_LEVEL_CLASS[f["level"]]}">'
                           f'{REPORT_LEVEL_DOTS[f["level"]]} {f["level"]}</span>', tag, f["title"], f["detail"])


def report_factor_card(title, desc, items, render, key, tag=lambda f: f["group"]):
    """같은 높이 카드: 상위 항목(읽기 쉬운 줄) + 오른쪽 아래 '더보기' (나머지 항목은 전체 내용으로)."""
    top, rest = report_factor_split(items)
    with st.container(border=True, height=REPORT_FACTOR_HEIGHT, key=f"report-card-{key}"):
        st.markdown(f'{title} <span class="report-desc">{desc}</span>', unsafe_allow_html=True)
        st.markdown("".join(report_factor_row(f, tag(f)) for f in top) or "표시할 항목이 없습니다.", unsafe_allow_html=True)
        with st.container(key=f"report-more-{key}"):
            with st.popover(f"더보기 {len(rest)}", type="tertiary", disabled=not rest):
                st.markdown(render(rest), unsafe_allow_html=True)


def report_show_internal(data):
    """내부 요인: 서리가 경쟁사 대비 부족한 점. 가장 큰 문제 2개(최대 3개) + 더보기."""
    items = data["internal"]
    if not items:
        st.caption("표시할 내부 요인이 없습니다. (경쟁사 DB에서 서리 행을 찾지 못하면 비어 보입니다. 앱을 다시 켜 주세요.)")
        return
    report_factor_card(":material/domain: **내부 요인**", f'서리 = {data["seori_proxy"] or "-"} 실적 가정 · {data["keepa_status"].split(" · ")[0]}', items,
                       lambda fs: "".join(report_factor_html(f, f["group"]) for f in fs), "internal")


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
    """외부 요인: 위협과 기회. 가장 큰 문제 2개(최대 3개) + 더보기."""
    items = data["external"]

    def block(group):
        html = ""
        for kind in ("위협", "기회"):
            sub = [f for f in group if f["kind"] == kind]
            if sub:
                html += f"<p><b>{'⚠️ 위협' if kind == '위협' else '✨ 기회'}</b> ({len(sub)})</p>"
                html += "".join(report_factor_html(f, f["group"]) for f in sub)
        return html

    report_factor_card(":material/public: **외부 요인**", f'위협 {sum(f["kind"] == "위협" for f in items)}개 · 기회 {sum(f["kind"] == "기회" for f in items)}개 · '
                       "Keepa·Open-Meteo·독일 DB", items, block, "external", tag=lambda f: f"{f['kind']} · {f['group']}")


def report_show_competitors(data):
    """냉감패드 경쟁사 비교: 판매 순위 상위 2개사 + 서리(가정 3위). 냉감패드 제품 정보만 (경쟁사 DB + Keepa)."""
    rows = data["competitors_full"]
    with st.container(border=True):
        st.markdown(f":material/leaderboard: **냉감패드 경쟁사 비교** · 판매 순위 상위 2개사 + 서리(가정 3위)  \n"
                    f'<span class="report-desc">{data["keepa_status"]} · {data["keepa_auto"]}</span>',
                    unsafe_allow_html=True)
        report_show_keepa_fetch()
        if not rows:
            st.info("공통 경쟁사 DB(data/common_competitor_seori_202610.csv)가 없습니다.")
            return
        detail = report_keepa_detail().get("items", {})
        summer = {a: d.get("rank_root_summer_median") for a, d in detail.items()}   # 보조: 2026년 6~8월 순위 중앙값
        sig = {a: (d.get("rank_drops") or {}).get("365") for a, d in detail.items()}   # 순위 기준: 1년 판매 신호
        yago = {a: (d.get("price") or {}).get("year_ago") for a, d in detail.items()}   # 작년 같은 날 가격
        table = []
        for r in rows:
            k = r.get("keepa") or {}
            seori = r["kind"] == "자사"
            table.append({
                "순위": "3위 (가정)" if seori else (f"{r['rank']}위" if r.get("rank") else r["label"]),
                "브랜드": r["brand"], "냉감패드 제품": r["product"],
                "1년 판매 신호": f"{sig[r.get('asin')]}회" if sig.get(r.get("asin")) is not None else "-",
                "여름 순위 (6~8월)": f"{summer[r.get('asin')]:,}" if summer.get(r.get("asin")) else "-",
                "10월 순위": f"{k['rank']:,}" if k.get("rank") else ("가정 3위 (판매 전)" if seori else "-"),
                "현재가": f"€{k['price']:.2f}" if k.get("price") else (f"€{r['db_price']:.2f} (권장가)" if seori and r["db_price"] else "-"),
                # 가격 변화는 계절이 섞이지 않게 작년 같은 날과 비교 (데이터 기준: 가격 변화)
                "작년 대비": (f"{(k['price'] / yago[r.get('asin')] - 1) * 100:+.0f}%"
                              if k.get("price") and yago.get(r.get("asin")) else "-"),
                "평점": f"{k['rating']:.1f}" if k.get("rating") else "-",
                "리뷰 수": f"{k['reviews']:,}" if k.get("reviews") is not None else ("0건" if seori else "-"),
                "㎡당 가격": (f"€{r['keepa_sqm']:.1f}" if r.get("keepa_sqm") else f"€{r['sqm_price']:.1f}" if r["sqm_price"] else "-"),
                "Q-max": (r["qmax"] or "-").split(" · ")[0].split(" (")[0],
            })
        st.dataframe(table, hide_index=True, width="stretch", key="report-table-competitors",
                     column_config={"냉감패드 제품": st.column_config.TextColumn(width="medium")})
        st.markdown('<div class="report-desc">순위 기준: 냉감 전용 상품의 1년 판매 신호(Keepa 순위가 좋아진 횟수 = 판매 횟수 추정), 양면(2-in-1)·비냉감 혼재 상품 제외 · '
                    '현재 순위는 비수기(10월) 값이라 순서가 다를 수 있음 · '
                    f'서리 = 독일 냉감패드 실적 3위 {REPORT_SEORI_PROXY}라고 가정해 판매 순위·가격·평점·리뷰·㎡당 가격은 {REPORT_SEORI_PROXY}의 Keepa 실적을 표시 '
                    '(제품명·냉감 방식·Q-max·강점·약점은 서리 기획) · ㎡당 가격: Keepa 현재가 기준</div>',
                    unsafe_allow_html=True)
        with st.expander("냉감패드 항목별 비교 (서리 목표 vs 상위 2개사 최고)", expanded=False):
            st.dataframe([{"항목": c["item"], "가중치": f"{c['weight']:.0%}", "서리 (목표)": c["seori"],
                           "상위 2개사 최고": f"{c['best_brand']} {c['best']:.0f}",
                           "차이": f"{c['seori'] - c['best']:+.0f}" if c["seori"] is not None else "-", "메모": c["memo"]}
                          for c in data["criteria"]], hide_index=True, width="stretch", key="report-table-criteria")
        report_show_seori_status(data)
        report_show_review(data["review_analysis"])
        report_show_cooling_sales(data.get("cooling_sales"))
        with st.expander("냉감패드 강점·약점 (경쟁사 DB)", expanded=False):
            for r in rows:
                st.markdown(f"**{r['brand']}** · {r['product']} · 소재: {r['material'] or '-'}  \n"
                            f'<span class="report-desc">강점: {r["strength"]}<br>약점: {r["weakness"]}</span>',
                            unsafe_allow_html=True)


def report_show_seori_status(data):
    """서리 인증·시험 현황 (가정: 국내 기업 자료 기반 완제품 판매 중). 보완이 남은 항목은 내부/외부 요인으로 분석에 반영."""
    profile = data["seori_profile"]
    with st.expander("서리 인증·시험 현황 (가정: 국내 기업 자료 기반 완제품)", expanded=False):
        st.dataframe([{"인증·규제": c["item"], "구분": c["group"], "상태": c["status"], "근거": c.get("basis", "")}
                      for c in profile.get("certs", [])], hide_index=True, width="stretch", key="report-table-seori-certs")
        st.dataframe([{"시험 항목": t["item"], "결과": t["result"] or "미실시", "완료": "O" if t["done"] else "보완 필요"}
                      for t in profile.get("tests", [])], hide_index=True, width="stretch", key="report-table-seori-tests")
        if profile.get("data_check"):
            st.markdown("**국내 기업 데이터로 채울 수 있는지**")
            st.dataframe([{"항목": d["item"], "국내 데이터": d["domestic"], "국내 내용": d["detail"],
                           "다른 기업·해외": d.get("other", "-"), "적용": d["use"]}
                          for d in profile["data_check"]], hide_index=True, width="stretch", key="report-table-seori-check")
        ref = profile.get("finished_qmax_ref")
        if ref:
            st.markdown("**국내 다른 기업 Q-max 광고 수치 vs 완제품 실측 등급**")
            st.dataframe([{"브랜드": r["brand"], "광고 Q-max": r["value"], "조건": r["cond"], "완제품 실측(10℃) 등급": r["grade"]}
                          for r in ref["rows"]], hide_index=True, width="stretch", key="report-table-seori-qmaxref")
            st.markdown(f'<div class="report-desc">{ref["finding"]}<br>서리: {ref["seori_estimate"]}<br>'
                        f'광고 시정 사례: {ref["ad_cases"]}<br>사용 범위: {ref.get("usage", "")}<br>출처: {ref["source"]}</div>', unsafe_allow_html=True)
        ad = profile.get("ad_check")
        if ad:
            st.markdown("**완제품 Q-max 0.207 광고 사용 가능 여부**")
            st.markdown(f'<div class="report-desc">가상 광고(AI 시안): {ad["mock_ad"]}<br>실제 광고: {ad["real_ad"]}<br>'
                        f'쓰면 안 되는 것: {ad.get("not_ok", "-")}<br>독일어 표기 형식: {ad["claim_de"]}<br>근거: {ad["rules"]}</div>',
                        unsafe_allow_html=True)
        claims = data.get("ad_claims") or {}
        if claims.get("claims"):
            st.markdown("**나중에 광고에 넣을 서리 문구** (③ 광고 소재로 전달: `ad_claims`)")
            st.dataframe([{"주제": c["topic"], "독일어": c["de"], "한국어": c["ko"], "필수 표기": c["must"]} for c in claims["claims"]],
                         hide_index=True, width="stretch", key="report-table-ad-claims")
            st.markdown(f'<div class="report-desc">금지: {" · ".join(claims["forbidden"])}<br>장면: {claims["allowed_scenes"]}</div>',
                        unsafe_allow_html=True)
        bt = profile.get("body_temp")
        if bt:
            st.markdown("**체감(피부 표면) 온도 vs 실제 체온**")
            st.dataframe([{"구분": r["type"], "대상": r["target"], "하강 값": r["value"], "방법": r["method"],
                           "측정 주체": r["by"], "출처": r["source"]} for r in bt["rows"]],
                         hide_index=True, width="stretch", key="report-table-seori-bodytemp")
            st.markdown(f'<div class="report-desc">{bt["summary"]}<br>{bt["rule"]}</div>', unsafe_allow_html=True)
            if bt.get("health"):
                st.markdown("**실제 체온 변화가 몸에 주는 영향**")
                st.dataframe([{"연구": h["study"], "체온 변화": h["core"], "영향": h["effect"]} for h in bt["health"]],
                             hide_index=True, width="stretch", key="report-table-seori-health")
                st.markdown(f'<div class="report-desc">{bt["health_summary"]}</div>', unsafe_allow_html=True)
            if bt.get("steps"):
                st.markdown("**실제 체온 0.5℃ 단위 영향**")
                st.dataframe([{"체온 변화": x["change"], "의미": x["meaning"], "근거": x["basis"]} for x in bt["steps"]],
                             hide_index=True, width="stretch", key="report-table-seori-steps")
                st.markdown(f'<div class="report-desc">{bt.get("expert_note", "")}<br>{bt.get("apply", "")}<br>{bt.get("skin_note", "")}</div>', unsafe_allow_html=True)
        st.caption("가정 파일: modules/report/data/report_seori_assumption_202610.json · 상태가 '일부·미착수·보완 필요'인 항목은 "
                   "내부 요인(서리가 고칠 것)과 외부 위협(규제·시장이 요구하는 것)으로 나눠 위 분석에 반영했습니다.")


def report_show_keepa_fetch():
    """Keepa 최신값 조회: 예상 토큰·남은 한도 안내 → PIN + 동의 → 1회 조회. (토큰 한도 보호)"""
    usage = report_keepa_usage()
    left = usage["budget"] - usage["used"]
    with st.expander(f":material/refresh: Keepa 최신값 조회 (남은 한도 {left}/{usage['budget']}토큰)", expanded=False):
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


def report_show_ab(ab_tests, daily, upload=None):
    """해결안 A/B: ③ 광고 소재 탭 결과를 매일 아침 분석한 값 + data/report_ab_tests.json의 실제 결과."""
    with st.container(border=True):
        if daily:
            st.markdown(":material/science: **③ 탭 실행 결과 분석** · 매일 아침(한국 08:00 이후 첫 접속)  \n"
                        f'<span class="report-desc">분석 기준일 {daily["day"]} · 분석 {daily["analyzed_at"]}'
                        + (f' · ③ 탭 저장 {daily["media_updated_at"]}' if daily.get("media_updated_at") else "")
                        + "</span>", unsafe_allow_html=True)
        else:
            # [보류] ③ 탭 결과 아침 자동 분석은 꺼져 있음 (report_data.py의 [보류] 주석 참고)
            st.markdown(":material/science: **해결안 A/B 분석** · 결과 파일(CSV)을 올려 바로 분석  \n"
                        '<span class="report-desc">③ 탭 실행 결과(UTM·GA4·A/B)의 매일 아침 자동 분석은 ③ 탭 연동 후 사용 예정 (지금은 꺼짐)</span>',
                        unsafe_allow_html=True)
        report_show_ab_upload(upload)
        daily = daily or {}
        r = daily.get("result")
        if r:
            st.markdown(f'<div class="report-desc">검색어 {r["query"]} · 기간 {r["period"]} · 출처 {r["source"]}</div>',
                        unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                ui.kpi_card("클릭률 A → B", f"{r['ctr_a']}% → {r['ctr_b']}%",
                            f"{r['ctr_lift']:+.1f}%" if r["ctr_lift"] is not None else None, sub=f"유의확률 p={report_ab_p(r['p_ctr'])}")
            with c2:
                ui.kpi_card("구매 전환율 (안전장치)", f"{r['cvr_a']}% → {r['cvr_b']}%",
                            sub="기준 통과" if r["cvr_ok"] else "기준 미달")
            with c3:
                cac = (f"CAC €{r['cac_before']} → €{r['cac_after']}" if r.get("cac_before") and r.get("cac_after") else "")
                ui.kpi_card("판정", f"{r['winner']} 안", sub=cac or " ")
            st.markdown(f"**결과** · {daily['verdict']}")
            if daily.get("change"):
                st.caption(daily["change"])
            if daily.get("history"):
                with st.expander(f"지난 분석 ({len(daily['history'])}일)", expanded=False):
                    st.dataframe([{"기준일": h["day"], "판정": h["winner"], "B 클릭률(%)": h["ctr_b"], "유의확률": h["p_ctr"]}
                                  for h in daily["history"]], hide_index=True, width="stretch", key="report-table-ab-history")
        elif daily:
            st.caption("아직 ③ 광고 소재 탭이 저장한 A/B 결과가 없습니다. ③ 탭에서 store_set(\"media\", {\"ab_result\": ..., "
                       "\"utm\": ..., \"updated_at\": ...})로 저장하면 다음 날 아침부터 여기서 분석합니다 (형식: report.md).")
        if daily.get("utm"):
            st.markdown("**유입 채널(UTM) 성과** · ③ 탭 저장값" + (f" · 전환율 최저: {daily['utm_worst']}" if daily["utm_worst"] else ""))
            st.dataframe([{"채널": u["channel"], "캠페인": u["campaign"], "방문": u["sessions"], "주문": u["orders"],
                           "전환율(%)": round(u["cvr"], 2), "방문 비중(%)": round(u["share"], 1)} for u in daily["utm"]],
                         hide_index=True, width="stretch", key="report-table-ab-utm")
        for t in ab_tests:
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


def report_show_cooling_sales(cs):
    """냉감패드 실적만 보기: 하위 카테고리 순위·여름 순위·판매 신호 (Keepa 상세 조회)."""
    if not cs:
        return
    with st.expander(":material/trending_up: 냉감패드 실적만 보기 (하위 카테고리·여름 순위, Keepa 상세)", expanded=False):
        st.dataframe([{"브랜드": c["brand"], "하위 카테고리": c["sub_category"],
                       "하위 순위 (지금 / 여름 중앙값)": f"{c['rank_sub_now'] or '-'} / {c['rank_sub_summer_median'] or '-'}",
                       "전체 순위 여름 중앙값": f"{c['rank_root_summer_median']:,}" if c["rank_root_summer_median"] else "-",
                       "1년 판매 신호": c["rank_drops"]["365"], "월 구매 배지": c["badge"],
                       "냉감 변형 / 전체": f"{c['cooling_variations']} / {c['variations']}", "출시": c["listed_since"]}
                      for c in cs["rows"]], hide_index=True, width="stretch", key="report-table-cooling-sales")
        st.markdown("\n".join(f"- {f}" for f in cs["findings"]))
        st.caption(cs["note"])


def report_show_ab_upload(upload):
    """A/B 결과 CSV를 올리면 바로 분석합니다 (Amazon 실험 도구·광고·판매 리포트 값을 양식에 옮겨 적은 파일)."""
    with st.expander(":material/upload_file: 결과 파일 올려서 바로 분석 (CSV)", expanded=bool(upload)):
        st.download_button("양식 내려받기 (.csv)", REPORT_AB_TEMPLATE.encode("utf-8-sig"), file_name="report_ab_template.csv",
                           key="report-btn-ab-template")
        f = st.file_uploader("A/B 결과 CSV", type=["csv"], key="report-upload-ab")
        if f is not None and (not upload or upload.get("file") != f.name):
            try:
                ab = report_ab_parse_csv(f.getvalue().decode("utf-8-sig"))
                r = report_ab_analyze(ab)
                upload = {"file": f.name, "result": r, "verdict": report_ab_verdict(r, None)[0]}
                st.session_state["report-ab-upload"] = upload   # 다음 실행부터 store에도 저장
            except (ValueError, KeyError) as err:
                st.error(f"파일을 읽지 못했습니다: {err}")
        if upload:
            r = upload["result"]
            st.markdown(f"**{upload['file']}** · 클릭률 {r['ctr_a']}% → {r['ctr_b']}% (p={report_ab_p(r['p_ctr'])}) · "
                        f"구매 전환율 {r['cvr_a']}% → {r['cvr_b']}% ({r['cvr_basis']})  \n**결과** · {upload['verdict']}")


def report_show_review(ra):
    """리뷰 분석: 서리 리뷰 수·평점을 냉감패드 상품과 비교 (Keepa 마지막 조회값)."""
    with st.expander(":material/star: 리뷰 분석 (내부 요인 '리뷰' 근거)", expanded=False):
        if not ra:
            st.caption("Keepa 조회값이 없어 리뷰 분석을 할 수 없습니다.")
            return
        st.markdown("\n".join(f"- {f}" for f in ra["findings"]))
        st.dataframe([{"브랜드": x["brand"], "구분": x["kind"], "리뷰 수": x["reviews"],
                       "1년 증가": f"{x['reviews_1y']:+d}" if x.get("reviews_1y") is not None else "-", "평점": x["rating"],
                       "Amazon 판매 순위": f"{x['rank']:,}" if x["rank"] else "-"}
                      for x in sorted(ra["rows"], key=lambda x: x["rank"] or 10**9)],
                     hide_index=True, width="stretch", key="report-table-review")
        st.markdown(f'<div class="report-desc">지표: {ra["metric"]} · 목표: {ra["target"]}<br>규칙: {ra["rule"]}<br>한계: {ra["limits"]}</div>',
                    unsafe_allow_html=True)


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
