# 4. 날씨 광고 타이밍
# 화면 구성 (2단): [본문: 권역 날씨 4칸 → 예산·채널 액션 → 30°C 이상 권역 그래프] | [오른쪽: 경쟁사 재고 → 오늘의 추천]
from datetime import date
from html import escape

import plotly.graph_objects as go
import streamlit as st

import ui_theme as ui
from modules.weather.weather_data import (
    WEATHER_HOT_C,
    WEATHER_STOCK_LABEL,
    weather_build_plan,
    weather_eur,
    weather_fetch_regions,
    weather_get_competitors,
    weather_reco_items,
    weather_recommended_amazon_share,
    weather_sample_regions,
    weather_short_date,
    weather_weekday,
    weather_wmo_emoji,
    weather_wmo_text,
)
from modules.weather.weather_report import weather_make_pdf, weather_temp_color

P = ui.PALETTE
T = ui.THEME
WEATHER_SOFT_LAVENDER = f"color-mix(in srgb, {P['lavender']} 35%, {T['card']})"
WEATHER_BUDGET_DEFAULT = (1000, 20000, 5000)   # 슬라이더 최소, 최대, 처음 값 (€)
WEATHER_FONT_CSS = "https://cdn.jsdelivr.net/gh/sun-typeface/SUIT@2/fonts/static/woff2/SUIT.css"
WEATHER_FONT_FAMILY = "SUIT, Pretendard, sans-serif"


def _weather_tile_colors(tmax):
    """7일 최고기온 → 권역 카드 (배경, 글자) 색."""
    if tmax >= 33:
        return T["down_bg"], T["down_text"]
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
def _weather_header():
    c1, c2 = st.columns([4, 1.2], vertical_alignment="center")
    with c1:
        _weather_html(
            '<div class="weather-title">날씨 광고 타이밍</div>'
            '<div class="weather-subtitle">독일 4개 권역 예보와 경쟁사 재고로 이번 주 메타·아마존 예산을 나눕니다</div>'
        )
    with c2:
        return st.toggle(
            "폭염 시나리오(샘플)", key="weather-toggle-sample",
            help="실제 예보 대신 여름 폭염 샘플 데이터로 화면과 보고서를 확인합니다.",
        )


def _weather_region_tiles(regions, failed):
    """권역 날씨 카드 4개를 가로 한 줄로."""
    tiles = []
    for r in regions:
        bg, fg = _weather_tile_colors(r["max7"])
        hot = len([d for d in r["days"] if d["tmax"] >= WEATHER_HOT_C])
        chip = f"7일 최고 {r['max7']:.0f}°" + (f" · {WEATHER_HOT_C}°C+ {hot}일" if hot else "")
        cities = " · ".join(f"{escape(c['city'])} <b>{c['now']:.0f}°</b>" for c in r.get("cities", []))
        tiles.append(
            f'<div class="weather-kpi" style="background:{bg};color:{fg}">'
            f'<div class="weather-kpi-head"><span>{r["name"]} <em>{r["de"]}</em></span>'
            f'<span class="weather-kpi-emoji" title="{weather_wmo_text(r["wcode"])}">{weather_wmo_emoji(r["wcode"])}</span></div>'
            f'<div class="weather-kpi-temp">{r["now"]:.0f}°<small>{weather_wmo_text(r["wcode"])}</small></div>'
            f'<span class="weather-kpi-chip">{chip}</span>'
            f'<div class="weather-kpi-cities">{cities}</div></div>'
        )
    for r in failed:
        tiles.append(
            f'<div class="weather-kpi weather-kpi-fail"><div class="weather-kpi-head"><span>{r["name"]} <em>{r["de"]}</em></span></div>'
            '<div class="weather-kpi-cities">날씨를 불러오지 못했어요</div></div>'
        )
    _weather_html(f'<div class="weather-kpis">{"".join(tiles)}</div>')


def _weather_budget_card(competitors):
    """예산 카드: ① 주간 예산(범위는 '범위 설정'에서 입력) ② 채널 비율 ③ 결과 금액."""
    lo_def, hi_def, val_def = WEATHER_BUDGET_DEFAULT
    rec_meta = round((1 - weather_recommended_amazon_share(competitors)) * 100)
    with st.container(border=True, key="weather-card-budget"):
        h1, h2 = st.columns([3, 1], vertical_alignment="center")
        with h1:
            _weather_html('<div class="weather-card-title weather-flat">이번 주 광고 예산<span class="weather-chip">7일 합계</span></div>'
                          '<div class="weather-card-desc">주간 예산을 설정하고 채널 비율을 조정하세요.</div>')
        with h2, st.popover("범위 설정", icon=":material/tune:", width="stretch", key="weather-pop-range"):
            lo = st.number_input("최소 (€)", min_value=0, value=lo_def, step=500, key="weather-budget-min")
            hi = st.number_input("최대 (€)", min_value=0, value=hi_def, step=500, key="weather-budget-max")
        if hi <= lo:
            hi = lo + 1000
        step = next(s for s in (10, 50, 100, 500, 1000, 5000) if (hi - lo) / s <= 200)
        # 범위를 바꿨을 때 슬라이더 값이 범위 밖이면 안쪽으로 맞춤
        cur = st.session_state.get("weather-budget-week", val_def)
        st.session_state["weather-budget-week"] = min(max(cur, lo), hi)

        # ① 주간 예산
        budget_head = st.empty()
        budget = st.slider("주간 예산", min_value=int(lo), max_value=int(hi), step=step, format="€%d",
                           key="weather-budget-week", label_visibility="collapsed")
        budget_head.markdown(
            f'<div class="weather-field"><span>주간 예산</span><b>{weather_eur(budget)}</b></div>'
            f'<div class="weather-note weather-range-note">설정 범위 {weather_eur(lo)} ~ {weather_eur(hi)}</div>',
            unsafe_allow_html=True,
        )

        # ② 채널 비율
        share_head = st.empty()
        # 처음에는 경쟁사 재고에 맞춘 추천 비율로 시작하고, 이후로는 사용자가 슬라이더로 바로 조정
        if "weather-meta-share" not in st.session_state:
            st.session_state["weather-meta-share"] = rec_meta
        meta_pct = st.slider("메타 비율", min_value=0, max_value=100, step=5, format="메타 %d%%",
                             key="weather-meta-share", label_visibility="collapsed")
        share_head.markdown(
            f'<div class="weather-field weather-field-gap"><span>채널 비율</span>'
            f'<b>메타 {meta_pct}% · 아마존 {100 - meta_pct}%</b></div>',
            unsafe_allow_html=True,
        )
        summary_slot = st.empty()
    return int(budget), (100 - meta_pct) / 100, summary_slot


def _weather_budget_summary(slot, plan):
    meta_pct = (1 - plan["amazon_share"]) * 100
    slot.markdown(
        '<div class="weather-results">'
        f'<div class="weather-result"><span><i style="background:{T["primary"]}"></i>메타 · 지역 타겟</span>'
        f'<b>{weather_eur(plan["meta"])}</b><em>{meta_pct:.0f}%</em></div>'
        f'<div class="weather-result"><span><i style="background:{P["peach"]}"></i>아마존 · 전국</span>'
        f'<b>{weather_eur(plan["amazon"])}</b><em>{100 - meta_pct:.0f}%</em></div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _weather_channel_card(plan):
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
    asin = "".join(f'<span class="weather-pill">{escape(c["competitor"])} ASIN 타겟 ON</span>' for c in plan["soldout"])
    with st.container(border=True, key="weather-card-channel"):
        _weather_html(
            '<div class="weather-card-title">채널별 추천 액션<span class="weather-chip">7일 합계</span></div>'
            f'<div class="weather-channel-head"><span>∞ 메타 · 지역 타겟</span><b>{weather_eur(plan["meta"])}</b></div>'
            f'{"".join(rows)}'
            f'<div class="weather-channel-head weather-gap"><span>🛒 아마존 · 전국</span>'
            f'<b>{weather_eur(plan["amazon"])}</b></div><div class="weather-pills">{asin}</div>'
        )


def _weather_forecast_chart(region):
    days = region["days"]
    fig = go.Figure(go.Bar(
        x=[f"{weather_weekday(d['date'])} {d['date'][5:].replace('-', '/')}<br><b>{d['tmax']:.0f}°</b>" for d in days],
        y=region["daily"],
        marker=dict(color=[weather_temp_color(d["tmax"]) for d in days], cornerradius=10, line=dict(width=0)),
        text=[weather_eur(v) for v in region["daily"]],
        textposition="outside",
        textfont=dict(color=T["text"], size=12),
        cliponaxis=False,
        customdata=[[weather_short_date(d["date"]), d["tmax"], d["tmin"]] for d in days],
        hovertemplate="%{customdata[0]}<br>최고 %{customdata[1]:.0f}° · 최저 %{customdata[2]:.0f}°"
                      "<br>메타 예산 %{text}<extra></extra>",
    ))
    fig.update_layout(
        height=250, margin=dict(l=4, r=4, t=26, b=4), bargap=0.34,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=WEATHER_FONT_FAMILY, color=T["text"]),
        hoverlabel=dict(bgcolor=T["card"], bordercolor=T["line"], font=dict(color=T["text"])),
    )
    fig.update_xaxes(showgrid=False, showline=False, fixedrange=True, tickfont=dict(size=12, color=T["muted"]))
    fig.update_yaxes(visible=False, range=[0, max(region["daily"]) * 1.18], fixedrange=True)
    return fig


def _weather_forecast_section(plan):
    hot = plan["hot_regions"]
    if not hot:
        with st.container(border=True, key="weather-card-empty"):
            _weather_html(
                f'<div class="weather-card-title">{WEATHER_HOT_C}°C 이상 권역 · 7일 메타 예산</div>'
                f'<div class="weather-empty"><b>앞으로 7일 동안 {WEATHER_HOT_C}°C 이상 예보된 권역이 없어요.</b><br>'
                '메타 예산은 4개 권역에 고르게 나눠 운영합니다. 오른쪽 위 "폭염 시나리오(샘플)"를 켜면 그래프 예시를 볼 수 있어요.</div>'
            )
        return
    cols = st.columns(2 if len(hot) > 1 else 1, gap="small")
    for i, r in enumerate(hot):
        peak = max(r["days"], key=lambda d: d["tmax"])
        with cols[i % len(cols)], st.container(border=True, key=f"weather-card-chart-{r['code']}"):
            diff = f" · 균등 대비 +{r['vs_even']}%" if r["vs_even"] > 0 else ""
            _weather_html(
                f'<div class="weather-chart-head"><div class="weather-card-title">{r["name"]} 7일 메타 예산'
                f'<span>{WEATHER_HOT_C}°C 이상 {len(r["hot_days"])}일 · 최고 {peak["tmax"]:.0f}° ({weather_short_date(peak["date"])})</span></div>'
                f'<div class="weather-chart-total">주간 <b>{weather_eur(r["week"])}</b>{diff}</div></div>'
            )
            st.plotly_chart(_weather_forecast_chart(r), config={"displayModeBar": False},
                            key=f"weather-chart-{r['code']}", width="stretch")


# ─────────────────────────────────────────────
# 오른쪽 열
# ─────────────────────────────────────────────
def _weather_stock_card(plan, is_sample_stock):
    badge = {"soldout": (T["down_bg"], T["down_text"]), "low": (P["peach"], T["text"]),
             "normal": (T["up_bg"], T["up_text"])}
    counts = {k: sum(c["status"] == k for c in plan["competitors"]) for k in ("soldout", "low", "normal")}
    summary = "".join(
        f'<div><b>{counts[k]}</b><span>{WEATHER_STOCK_LABEL[k]}</span></div>' for k in ("soldout", "low", "normal")
    )
    rows = []
    for c in plan["competitors"]:
        bg, fg = badge.get(c["status"], (T["line"], T["text"]))
        label = WEATHER_STOCK_LABEL.get(c["status"], c["status"])
        if c["status"] != "normal" and c["days"]:
            label += f" {c['days']}일째"
        rows.append(
            f'<div class="weather-row"><span><b>{escape(c["competitor"])}</b><br><small>{escape(c["product"])}</small></span>'
            f'<span class="weather-badge" style="background:{bg};color:{fg}">{label}</span></div>'
        )
    sample = '<span class="weather-chip">샘플</span>' if is_sample_stock else ""
    with st.container(border=True, key="weather-card-stock"):
        _weather_html(
            f'<div class="weather-card-title">경쟁사 재고 시그널{sample}</div>'
            f'<div class="weather-stock-summary">{summary}</div>{"".join(rows)}'
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
    # 팀 공용 글꼴 SUIT (common/fonts와 같은 글꼴의 웹 버전, 이 탭 안에만 적용)
    _weather_html(f"<style>@import url('{WEATHER_FONT_CSS}');</style>")
    with st.container(key="weather-root"):
        is_sample_weather = _weather_header()

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

        source = "폭염 시나리오 샘플 데이터 (실제 예보 아님)" if is_sample_weather else "Weather data by Open-Meteo.com"
        st.caption(f"날씨: {source} · 기준 {plan['regions'][0]['updated'].replace('T', ' ')} · 권역 기온은 3개 도시 평균")
