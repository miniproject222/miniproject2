# 4. 날씨 광고 타이밍
# 화면 구성 (2단): [본문: 권역 날씨 4칸 → 예산·채널 액션 → 30°C 이상 권역 그래프] | [오른쪽: 경쟁사 재고 → 오늘의 추천]
import json
from datetime import date
from html import escape

import plotly.graph_objects as go
import streamlit as st

import ui_theme as ui
from common.common_store import store_get, store_set
from modules.weather.weather_data import (
    WEATHER_HOT_C,
    WEATHER_STOCK_LABEL,
    weather_build_plan,
    weather_eur,
    weather_fetch_regions,
    weather_get_competitors,
    weather_reco_items,
    WEATHER_AMAZON_ONLY,
    weather_amazon_days,
    weather_sample_regions,
    weather_short_date,
    weather_stock_checked,
    weather_stock_text,
    weather_weekday,
    weather_wmo_emoji,
    weather_wmo_text,
)
from modules.weather.weather_report import weather_make_pdf, weather_temp_color

P = ui.PALETTE
T = ui.THEME
WEATHER_SOFT_LAVENDER = f"color-mix(in srgb, {P['lavender']} 35%, {T['card']})"
WEATHER_BUDGET_DEFAULT = (1000, 20000, 5000)   # 슬라이더 최소, 최대, 처음 값 (€)
WEATHER_FONT_FAMILY = '"Source Sans", sans-serif'   # 그래프 글꼴: ① 문제 분석 탭과 같은 앱 기본 글꼴


def _weather_tile_colors(tmax):
    """7일 최고기온 → 권역 카드 (배경, 글자) 색. 글자는 ① 탭과 같은 글자색으로 통일하고 배경만 기온별로."""
    if tmax >= 33:
        return T["down_bg"], T["text"]
    if tmax >= WEATHER_HOT_C:
        return P["peach"], T["text"]
    if tmax >= 25:
        return P["beige"], T["text"]
    return T["card"], T["text"]


def _weather_html(html):
    st.markdown(html, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 본문
# ─────────────────────────────────────────────
WEATHER_HELP_ABOUT = "독일 4개 권역 예보와 경쟁사 재고로 이번 주 아마존 광고 예산을 날짜별로 나눕니다."


def _weather_header():
    """① 탭과 같은 제목 줄: 제목 칸(공통 ui.page_header) · 물음표(설명·데이터 출처) · 오른쪽 끝 폭염 시나리오 토글."""
    with st.container(horizontal=True, vertical_alignment="center", key="weather-head"):
        with st.container(key="weather-head-title"):
            ui.page_header("4. 광고 타이밍")
        with st.container(key="weather-help"):
            # 내용(설명 + 데이터 출처)은 weather_render 끝에서 채움
            src = st.popover("", icon=":material/help:", type="tertiary", help="이 탭 안내 · 데이터 출처")
        on = st.toggle(
            "폭염 시나리오(샘플)", key="weather-toggle-sample", value=True,   # 처음부터 켜짐 (끄면 실제 예보)
            help="실제 예보 대신 여름 폭염 샘플 데이터로 화면과 보고서를 확인합니다. 끄면 Open-Meteo 실제 예보.",
            width="content",
        )
    return on, src


def _weather_region_tiles(regions, failed):
    """권역 날씨 카드 4개를 가로 한 줄로."""
    tiles = []
    for r in regions:
        bg, fg = _weather_tile_colors(r["max7"])
        hot = len([d for d in r["days"] if d["tmax"] >= WEATHER_HOT_C])
        chip = f"7일 최고 {r['max7']:.0f}°" + (f" · {WEATHER_HOT_C}°C+ {hot}일" if hot else "")
        cities = " · ".join(f"{escape(c['city'])} <b>{c['now']:.0f}°</b>" for c in r.get("cities", []))
        plain = " · ".join(f"{c['city']} {c['now']:.0f}°" for c in r.get("cities", []))
        tiles.append(
            f'<div class="weather-kpi" style="background:{bg};color:{fg}">'
            f'<div class="weather-kpi-head"><span>{r["name"]} <em>{r["de"]}</em></span>'
            f'<span class="weather-kpi-emoji" title="{weather_wmo_text(r["wcode"])}">{weather_wmo_emoji(r["wcode"])}</span></div>'
            f'<div class="weather-kpi-temp">{r["now"]:.0f}°<small>{weather_wmo_text(r["wcode"])}</small></div>'
            f'<span class="weather-kpi-chip">{chip}</span>'
            f'<div class="weather-kpi-cities" title="{escape(plain)}">{cities}</div></div>'
        )
    for r in failed:
        tiles.append(
            f'<div class="weather-kpi weather-kpi-fail"><div class="weather-kpi-head"><span>{r["name"]} <em>{r["de"]}</em></span></div>'
            '<div class="weather-kpi-cities">날씨를 불러오지 못했어요</div></div>'
        )
    _weather_html(f'<div class="weather-kpis">{"".join(tiles)}</div>')


def _weather_budget_card(competitors):
    """예산 카드: 주간 예산(범위는 '범위 설정'에서 입력) → 아마존 결과 금액. 메타는 운영하지 않음 (아마존만)."""
    lo_def, hi_def, val_def = WEATHER_BUDGET_DEFAULT
    with st.container(border=True, key="weather-card-budget"):
        h1, h2 = st.columns([3, 1], vertical_alignment="center")
        with h1:
            _weather_html('<div class="weather-card-title weather-flat">이번 주 광고 예산<span class="weather-chip">7일 합계</span></div>'
                          '<div class="weather-card-desc">주간 예산을 설정하면 아마존 날짜별 예산을 계산합니다.</div>')
        with h2, st.popover("범위 설정", icon=":material/tune:", width="stretch", key="weather-pop-range"):
            lo = st.number_input("최소 (€)", min_value=0, value=lo_def, step=500, key="weather-budget-min")
            hi = st.number_input("최대 (€)", min_value=0, value=hi_def, step=500, key="weather-budget-max")
        if hi <= lo:
            hi = lo + 1000
        step = next(s for s in (10, 50, 100, 500, 1000, 5000) if (hi - lo) / s <= 200)
        # 범위를 바꿨을 때 슬라이더 값이 범위 밖이면 안쪽으로 맞춤
        cur = st.session_state.get("weather-budget-week", val_def)
        st.session_state["weather-budget-week"] = min(max(cur, lo), hi)

        budget_head = st.empty()
        budget = st.slider("주간 예산", min_value=int(lo), max_value=int(hi), step=step, format="€%d",
                           key="weather-budget-week", label_visibility="collapsed")
        budget_head.markdown(
            f'<div class="weather-field"><span>주간 예산</span><b>{weather_eur(budget)}</b></div>'
            f'<div class="weather-note weather-range-note">설정 범위 {weather_eur(lo)} ~ {weather_eur(hi)}</div>',
            unsafe_allow_html=True,
        )
        summary_slot = st.empty()
    return int(budget), WEATHER_AMAZON_ONLY, summary_slot


def _weather_budget_summary(slot, plan):
    days = weather_amazon_days(plan)
    peak = max(days, key=lambda d: d["eur"]) if days else None
    slot.markdown(
        '<div class="weather-results">'
        f'<div class="weather-result"><span><i style="background:{P["peach"]}"></i>아마존 · 전국</span>'
        f'<b>{weather_eur(plan["amazon"])}</b><em>주간 예산 전부</em></div>'
        + (f'<div class="weather-result"><span><i style="background:{weather_temp_color(peak["tmax"])}"></i>가장 많이 쓰는 날</span>'
           f'<b>{weather_eur(peak["eur"])}</b><em>{weather_short_date(peak["date"])} · 최고 {peak["tmax"]:.0f}°</em></div>' if peak else "")
        + '</div>',
        unsafe_allow_html=True,
    )


def _weather_channel_card(plan):
    """추천 집행 액션 (아마존만): 권역별 막대(주간 예산을 권역 날씨로 나눈 비중) + 경쟁사 ASIN 타겟.
    날짜별 금액은 아래 '아마존 7일 예산' 그래프."""
    top = max((r["week"] for r in plan["regions"]), default=1) or 1
    rows = []
    for r in sorted(plan["regions"], key=lambda r: -r["week"]):
        diff = r["vs_even"]
        diff_html = (f'<em class="weather-diff up">+{diff}%</em>' if diff > 0
                     else f'<em class="weather-diff">{diff}%</em>' if diff < 0 else '<em class="weather-diff">균등</em>')
        rows.append(
            f'<div class="weather-alloc"><span class="weather-alloc-name">{r["name"]}</span>'
            f'<span class="weather-alloc-track"><span style="width:{r["week"] / top * 100:.0f}%;'
            f'background:{weather_temp_color(r["max7"])}"></span></span>'
            f'<b>{weather_eur(r["week"])}</b>{diff_html}</div>'
        )
    # 경쟁사 분석 (예전 '경쟁사 ASIN 타겟' 칸 → 품절일 때만 쓰는 ASIN 타겟은 '경쟁사 재고 시그널' 카드 한 줄로 옮김)
    rivals = []
    for c in plan["competitors"][:2]:
        if c.get("price") is None:
            continue
        ch = c.get("change")
        ch_html = (f'<em class="weather-diff{" up" if ch > 0 else ""}">90일 평균 대비 {ch * 100:+.0f}%</em>'
                   if isinstance(ch, (int, float)) and ch else '<em class="weather-diff">90일 평균과 같음</em>')
        meta = " · ".join(x for x in (
            f"★{c['rating']:.1f} ({c['reviews']:,})" if c.get("rating") and c.get("reviews") else "",
            f"판매 순위 {c['sales_rank']:,}위" if c.get("sales_rank") else "") if x)
        rivals.append(f'<div class="weather-rival"><b>{escape(c["competitor"])}</b><span>{weather_eur(c["price"])}</span>{ch_html}'
                      f'<small>{escape(meta)}</small></div>')
    checked = weather_stock_checked(plan["competitors"])
    rival_html = "".join(rivals) or '<span class="weather-note">Keepa 값이 있는 경쟁사가 없어요</span>'
    with st.container(border=True, key="weather-card-channel"):
        _weather_html(
            '<div class="weather-card-title">추천 집행 액션<span class="weather-chip">7일 합계</span></div>'
            f'<div class="weather-channel-head"><span title="더운 권역에 더 배정 (지역 타겟 기준 · 균등 대비 %)">🛒 아마존 · 권역별 비중</span><b>{weather_eur(plan["amazon"])}</b></div>'

            f'{"".join(rows)}'
            f'<div class="weather-channel-head weather-gap"><span>🔎 경쟁사 분석</span>'
            f'<b class="weather-note">Keepa {escape(checked) or "샘플"}</b></div>{rival_html}'
        )


def _weather_amazon_chart(plan):
    """아마존 7일 예산(전국) 막대: 날짜별 예산, 막대 색은 그날 4개 권역 중 가장 높은 최고기온."""
    ok = [r for r in plan["regions"]]
    days = plan["dates"]
    tmax = [max(r["days"][i]["tmax"] for r in ok) for i in range(len(days))]
    daily = plan["amazon_daily"]
    fig = go.Figure(go.Bar(
        x=[f"{weather_weekday(d)} {d[5:].replace('-', '/')}<br><b>{t:.0f}°</b>" for d, t in zip(days, tmax)],
        y=daily,
        marker=dict(color=[weather_temp_color(t) for t in tmax], cornerradius=10, line=dict(width=0)),
        text=[weather_eur(v) for v in daily],
        textposition="outside",
        textfont=dict(color=T["text"], size=12),
        cliponaxis=False,
        customdata=[[weather_short_date(d), t] for d, t in zip(days, tmax)],
        hovertemplate="%{customdata[0]}<br>4개 권역 중 최고 %{customdata[1]:.0f}°<br>아마존 예산 %{text}<extra></extra>",
    ))
    fig.update_layout(
        height=112, margin=dict(l=4, r=4, t=14, b=18), bargap=0.34,   # 한 화면에 들어오게 낮춤 (예전 250)
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=WEATHER_FONT_FAMILY, color=T["text"]),
        hoverlabel=dict(bgcolor=T["card"], bordercolor=T["line"], font=dict(color=T["text"])),
    )
    fig.update_xaxes(showgrid=False, showline=False, fixedrange=True, tickfont=dict(size=12, color=T["muted"]))
    fig.update_yaxes(visible=False, range=[0, (max(daily) if daily else 1) * 1.18], fixedrange=True)
    return fig


def _weather_forecast_section(plan):
    """아마존 7일 예산 (전국): 날짜별 가중치 = 1 + 0.1 × 그날 권역 폭염 점수 합 → 더운 날에 더 배정."""
    if not plan["amazon_daily"]:
        return
    hot_days = sum(1 for i in range(len(plan["dates"])) if any(r["days"][i]["tmax"] >= WEATHER_HOT_C for r in plan["regions"]))
    with st.container(border=True, key="weather-card-chart-amazon"):
        _weather_html(
            f'<div class="weather-chart-head"><div class="weather-card-title">아마존 7일 예산 · 전국'
            f'<span>{f"{WEATHER_HOT_C}°C 이상 예보일 {hot_days}일에 더 배정" if hot_days else f"{WEATHER_HOT_C}°C 이상 예보 없음 · 날짜별 고르게"}'
            ' · 막대 색 = 그날 4개 권역 중 최고기온</span></div>'
            f'<div class="weather-chart-total">주간 <b>{weather_eur(plan["amazon"])}</b></div></div>'
        )
        st.plotly_chart(_weather_amazon_chart(plan), config={"displayModeBar": False}, key="weather-chart-amazon", width="stretch")


def _weather_same(saved, payload) -> bool:
    """Supabase에 저장된 값과 새 값이 같은지 (JSON으로 바꿔 비교: 저장 뒤 키 순서·튜플↔리스트 차이는 무시)."""
    def norm(value):
        return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return saved is not None and norm(saved) == norm(payload)


def weather_save_store(plan, is_sample_weather=False):
    """홈 탭이 읽는 store("weather"): 광고 빈도 배수·근거·알림(오늘의 추천 첫 줄). 내용이 바뀔 때만 저장."""
    days = weather_amazon_days(plan)
    peak = max(days, key=lambda d: d["eur"]) if days else None
    hot_n = sum(1 for d in days if d["hot_regions"])
    mult = round(1 + max(0, peak["vs_avg"]) / 100, 1) if peak else 1.0   # 가장 많이 쓰는 날 ÷ 평균 (아마존)
    reason = (f"{weather_short_date(peak['date'])} 최고 {peak['tmax']:.0f}° · 폭염일 {hot_n}일 아마존 상향" if hot_n
              else f"{WEATHER_HOT_C}°C 이상 예보 없음") \
        + (f" + 경쟁사 품절 {len(plan['soldout'])}곳" if plan["soldout"] else "")         + (" (폭염 시나리오 샘플)" if is_sample_weather else "")
    items = weather_reco_items(plan)
    sample = " (폭염 시나리오 샘플)" if is_sample_weather else ""
    alerts = [{"level": "high" if i["tone"] in ("hot", "stock") else "info",
               "text": f"④ 광고 타이밍 · {i['text'].split('.')[0]}", "detail": f"{i['text']} ({i['tag']}){sample}",
               "when": "오늘"} for i in items[:1]]
    payload = {"ad_multiplier": mult, "reason": reason, "alerts": alerts,
               "channel": "amazon", "amazon": plan["amazon"], "amazon_daily": plan["amazon_daily"], "dates": plan["dates"],
               # 홈이 같은 날씨로 보이게: 폭염 시나리오(샘플)인지와 도시별 지금·7일 최고 기온
               "sample": bool(is_sample_weather),
               "cities": {c["city"]: {"now": c["now"], "max7": c["max7"]}
                          for r in plan["regions"] for c in r.get("cities", []) if "now" in c and "max7" in c}}
    if st.session_state.get("weather-stored-payload") != payload:
        first = "weather-stored-payload" not in st.session_state
        st.session_state["weather-stored-payload"] = payload
        # 이미 저장된 값(홈이 이번 실행에서 먼저 읽어 둔 값)과 같으면 다시 저장·다시 그리기를 하지 않음
        # (예전: 접속할 때마다 같은 값을 Supabase에 쓰고 화면 전체를 한 번 더 그려 첫 화면이 늦어짐)
        if _weather_same(store_get("weather"), payload):
            return
        store_set("weather", payload)
        if first:
            # 홈 탭은 ④보다 먼저 그려져 첫 화면에서는 아직 이 값이 없음 → 이번 접속 처음 저장할 때만 한 번 다시 그려 홈에 반영
            st.rerun()


# ─────────────────────────────────────────────
# 오른쪽 열
# ─────────────────────────────────────────────
def _weather_stock_card(plan, is_sample_stock):
    badge = {"soldout": (T["down_bg"], T["down_text"]), "low": (P["peach"], T["text"]),
             "normal": (T["up_bg"], T["up_text"])}
    # Keepa 실제 값은 품절/정상만 알 수 있어 '재고 낮음' 칸은 샘플에서만 보여 줌
    keys = ("soldout", "low", "normal") if is_sample_stock else ("soldout", "normal")
    counts = {k: sum(c["status"] == k for c in plan["competitors"]) for k in keys}
    summary = "".join(f'<div><b>{counts[k]}</b><span>{WEATHER_STOCK_LABEL[k]}</span></div>' for k in keys)
    rows = []
    for c in plan["competitors"]:
        bg, fg = badge.get(c["status"], (T["line"], T["text"]))
        rows.append(
            f'<div class="weather-row"><span><b>{escape(c["competitor"])}</b><br><small>{escape(c["product"])}</small></span>'
            f'<span class="weather-badge" style="background:{bg};color:{fg}">{escape(weather_stock_text(c))}</span></div>'
        )
    if is_sample_stock:
        chip = '<span class="weather-chip">샘플</span>'
    else:
        chip = f'<span class="weather-chip">Keepa · {escape(weather_stock_checked(plan["competitors"]))} 기준</span>'
    with st.container(border=True, key="weather-card-stock"):
        _weather_html(
            f'<div class="weather-card-title">경쟁사 재고 시그널{chip}</div>'
            f'<div class="weather-stock-summary" style="grid-template-columns:repeat({len(keys)}, 1fr)">{summary}</div>'
            f'{"".join(rows)}'
            f'<div class="weather-asin-line" title="경쟁사가 품절되면 그 상품 검색 결과에 우리 광고(ASIN 타겟)를 켜요">🎯 품절 시 ASIN 타겟 · '
            + (" · ".join(f"<b>{escape(c['competitor'])}</b> 품절 → 그 상품 ASIN 타겟 광고 ON" for c in plan["soldout"])
               or "품절 없음 → 대기") + '</div>'
        )


def _weather_reco_card(plan, is_sample_weather, is_sample_stock):
    with st.container(border=True, key="weather-card-reco"):
        c1, c2 = st.columns([1.4, 1], vertical_alignment="center")
        with c1:
            _weather_html('<div class="weather-card-title weather-flat">오늘의 추천</div>')
        with c2:
            st.download_button(
                "PDF",
                data=lambda: weather_make_pdf(plan, is_sample_weather, is_sample_stock),
                file_name=f"weather_report_{date.today():%Y%m%d}.pdf",
                mime="application/pdf",
                icon=":material/download:",
                on_click="ignore",
                width="stretch",
                key="weather-btn-pdf",
                help="A4 1장 예산 집행 권고서",
            )
        items = "".join(
            f'<div class="weather-task" style="background:{WEATHER_SOFT_LAVENDER}">'
            f'<div class="weather-task-tag">{escape(i["tag"])}</div>'
            f'<div class="weather-task-text">{escape(i["text"])}</div></div>'
            for i in weather_reco_items(plan)
        )
        _weather_html(f'<div class="weather-tasks">{items}</div>')


# ─────────────────────────────────────────────
# 탭 진입점
# ─────────────────────────────────────────────
def weather_render():
    """'4. 날씨 광고 타이밍' 탭을 열 때마다 실행됩니다. 화면은 전부 이 함수 안에서 그립니다."""
    with st.container(key="weather-root"):
        is_sample_weather, src_box = _weather_header()

        if is_sample_weather:
            regions = weather_sample_regions()
        else:
            with st.spinner("독일 날씨를 불러오는 중..."):
                regions = weather_fetch_regions()
        competitors, is_sample_stock = weather_get_competitors()

        ok = [r for r in regions if "error" not in r]
        if not ok:
            st.error("Open-Meteo에서 날씨를 불러오지 못했어요. 잠시 뒤 새로고침하거나 샘플 시나리오를 켜 주세요.")
            return
        for r in ok:
            r["max7"] = max(d["tmax"] for d in r["days"])

        main_col, side_col = st.columns([3.1, 1], gap="medium")
        main = main_col.container(key="weather-main")
        side = side_col.container(key="weather-side")
        with main:
            _weather_region_tiles(ok, [r for r in regions if "error" in r])
            m1, m2 = st.columns(2, gap="small")
            with m2:   # 넓은 칸: 예산 설정 (값을 먼저 읽어야 계산 가능)
                budget, amazon_share, summary_slot = _weather_budget_card(competitors)
            plan = weather_build_plan(regions, competitors, budget, amazon_share)
            _weather_budget_summary(summary_slot, plan)
            with m1:   # 좁은 칸: 채널별 추천 액션
                _weather_channel_card(plan)
            _weather_forecast_section(plan)
        with side:
            _weather_stock_card(plan, is_sample_stock)
            _weather_reco_card(plan, is_sample_weather, is_sample_stock)
        weather_save_store(plan, is_sample_weather)   # 홈 '지금 할 일'이 읽는 값 (광고 빈도 배수·알림)

        source = "폭염 시나리오 샘플 데이터 (실제 예보 아님)" if is_sample_weather else "Weather data by Open-Meteo.com"
        stock = ("샘플 데이터" if is_sample_stock
                 else f"경쟁사 DB 상위 경쟁사 + Keepa 마지막 조회값 ({weather_stock_checked(competitors)}, report 탭에서 갱신)")
        with src_box:
            st.markdown(f"{WEATHER_HELP_ABOUT}\n\n**데이터 출처**\n\n- 날씨: {source} · 기준 {plan['regions'][0]['updated'].replace('T', ' ')} · 권역 기온은 3개 도시 평균"
                        f"\n- 경쟁사 재고: {stock}")
