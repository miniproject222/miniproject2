# 홈 = 관제실: "오늘 뭘 먼저 해야 하는지" 알려 주는 출발점
# 배치 (2026-10-26 레퍼런스 'General statistics' 그대로): 왼쪽(제목 → 큰 숫자 자리에 독일 시간 → 지금 할 일 아이콘 세로
#   (마우스를 올리면 팝업) → 아래 작은 카드 2개 + 긴 카드 1개) → 가운데(테두리 있는 하얀 지구본, 독일 중심 + 도시 핀)
#   → 오른쪽 위(지역별 광고 비중: 큰 % · 7일 아마존 예산 꺾은선 · 지역 표 · 고리 2개)
# 진행 카드: ② 선택한 가설 / ③ A/B 소재 / 경쟁사 가격 — 들어오자마자 "지금 어디까지 왔는지"를 보게 (날씨만 보이던 카드 교체)
# 위 "가장 먼저" 줄·아래 "마케팅 사이클" 줄·오른쪽 아래 할 일 아이콘은 지금 할 일 아이콘과 겹쳐 삭제
# 카드·아이콘을 누르면 해당 탭으로 바로 이동 (HOME_NAV_JS)
# 홈 탭이 열려 있으면 화면 전체를 채웁니다 (home_style.css)
# 다른 탭이 구현 전이면 샘플 데이터로 채우고 지구본 아래에 "일부 샘플 데이터"로 알림 (데이터 모양은 home_data.py 맨 위 참고)
import html
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit.components.v1 as components

from modules.home.home_data import (
    HOME_HEAT_TEMP, HOME_HEAT_WARN, home_ad_multiplier, home_city_warning, home_heat_scenario, home_read_stores,
    home_region_shares, home_todos,
)
from modules.home.home_globe import (
    HOME_PIN, HOME_PIN_HOT, HOME_PIN_WARN, HOME_POP_SOURCE, HOME_WEEKDAYS, home_city_layer, home_get_temps, home_globe_svg,
    home_svg_img,
)

HOME_DIR = Path(__file__).resolve().parent   # 내 폴더 (images/, data/ 경로 만들 때 사용)

# 색은 보라 한 계열 + 경고(주황·빨강)만 (홈 탭 안에서만 적용)
HOME_COLORS = {
    "board": "#F5F6FB", "card": "#FFFFFF", "text": "#2B2D4F", "sub": "#9A9CB8", "line": "#ECEDF4",
    "purple": "#7B6CF2", "soft": "#EEEBFE", "orange": "#F9A65A", "red": "#F2546B", "up": "#2DB67C", "down": "#F2546B",
}
C = HOME_COLORS
HOME_WHEN_COLOR = {"지금": C["red"], "오늘": C["orange"], "이번 주": C["purple"]}

# 카드·버튼(data-home-goto="탭 번호")을 누르면 왼쪽 탭을 대신 눌러 주는 스크립트.
# st.html은 스크립트를 지우므로, 보이지 않는 components.html 안에서 부모 화면에 클릭 처리기를 한 번만 붙입니다.
# (이름을 __homeNav5로 바꿔, 예전 처리기가 붙어 있던 브라우저에도 새 처리기가 붙게 함)
# 지금 할 일 팝업은 CSS 호버로 열림 (home_style.css .home-tpin)
# 독일 시간(.home-clock)은 1초마다 베를린 시간으로 고침
HOME_NAV_JS = """
<script>
const P = window.parent;
if (!P.__homeNav5) {
  P.__homeNav5 = true;
  const days = "일월화수목금토";
  const tick = () => {
    const parts = {};
    new Intl.DateTimeFormat("en-GB", {timeZone: "Europe/Berlin", hour12: false, year: "numeric", month: "numeric",
      day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit", weekday: "short"})
      .formatToParts(new Date()).forEach((p) => { parts[p.type] = p.value; });
    const wd = {Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6}[parts.weekday];
    P.document.querySelectorAll(".home-clock").forEach((c) => {
      c.querySelector('[data-home-clock="time"]').firstChild.nodeValue = parts.hour + ":" + parts.minute;
      c.querySelector('[data-home-clock="sec"]').textContent = ":" + parts.second;
      c.querySelector('[data-home-clock="date"]').textContent = parts.month + "월 " + parts.day + "일 (" + days[wd] + ")";
    });
  };
  tick();
  P.setInterval(tick, 1000);
  P.document.addEventListener("click", (e) => {
    const go = e.target.closest("[data-home-goto]");
    if (go) {
      e.preventDefault();
      const list = P.document.querySelector('[data-testid="stTabs"] [role="tablist"]');
      const tab = list && list.querySelectorAll('[role="tab"]')[Number(go.dataset.homeGoto)];
      if (tab) tab.click();
    }
  });
}
</script>
"""


def home_tab_info():
    """{모듈코드: (탭 번호, "① 문제 분석")} - 탭 이름은 common_layout의 LAYOUT_TABS를 그대로 씀"""
    from common.common_layout import LAYOUT_TABS   # 여기서 불러야 순환 import가 생기지 않음
    return {t["code"]: (i, f'{t["icon"]} {t["label"]}') for i, t in enumerate(LAYOUT_TABS)}


def home_go(tabs, code, text, cls="home-go"):
    """누르면 해당 탭으로 이동하는 버튼"""
    return f'<button type="button" class="{cls}" data-home-goto="{tabs[code][0]}">{text} →</button>'


# ── 작은 HTML 조각 ───────────────────────────
def home_esc(text):
    return html.escape(str(text or ""), quote=False)


def home_when(when):
    return f'<span class="home-when" style="--w:{HOME_WHEN_COLOR.get(when, C["sub"])}">{when}</span>'


def home_icon(kind, bg):
    """아이콘 (해 / 종 / 차트)"""
    s = 'fill="none" stroke="#FFFFFF" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"'
    if kind == "sun":
        rays = "".join(f'<path d="M{11 + 7 * x:.1f} {11 + 7 * y:.1f} L{11 + 9 * x:.1f} {11 + 9 * y:.1f}" {s}/>'
                       for x, y in [(1, 0), (-1, 0), (0, 1), (0, -1), (0.7, 0.7), (-0.7, 0.7), (0.7, -0.7), (-0.7, -0.7)])
        shape = f'<circle cx="11" cy="11" r="4" {s}/>{rays}'
    elif kind == "chart":
        shape = f'<path d="M4 17V11M9 17V6M14 17V9M19 17V4" {s}/>'
    else:
        shape = f'<path d="M6 15V10a5 5 0 0 1 10 0v5l1.5 2h-13z" {s}/><path d="M9.5 19a1.6 1.6 0 0 0 3 0" {s}/>'
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 22 22">{shape}</svg>'
    return f'<span class="home-icon" style="background:{bg}">{home_svg_img(svg, "home-icon-img")}</span>'


def home_todo_icon(todo):
    return home_icon("sun" if todo["goto"] == "weather" else "chart", HOME_WHEN_COLOR.get(todo["when"], C["purple"]))


def home_card(tabs, code, title, body, cls=""):
    """누르면 해당 탭으로 가는 카드 (예전 '자세히 →' 버튼 대신 카드 전체가 버튼, 마우스를 올리면 → 표시)"""
    return f"""
  <div class="home-float home-card home-click {cls}" data-home-goto="{tabs[code][0]}" title="{tabs[code][1]}에서 자세히">
    <div class="home-row-between"><span class="home-card-title">{title}</span><span class="home-card-go">→</span></div>
    {body}
  </div>"""


# ── 지금 할 일: 아이콘 (마우스를 올리면 팝업) ─────────────
def home_todo_card(n, t, tabs):
    """팝업 안 할 일 카드 (왜? + 바로가기 + 다음 단계)"""
    return f"""
  <div class="home-todo-card">
    <div class="home-first-top"><span class="home-num-badge" style="background:{HOME_WHEN_COLOR.get(t["when"], C["purple"])}">{n}</span>{home_when(t["when"])}<span class="home-sub">{tabs[t["goto"]][1]}</span></div>
    <div class="home-first-title">{home_esc(t["title"])}</div>
    <p class="home-first-why"><b>왜?</b> {home_esc(t["detail"])}</p>
    <div class="home-row-between home-first-foot">
      {home_go(tabs, t["goto"], t["action"], "home-go home-go-lg")}
      <span class="home-next">다음 → {home_esc(t["next"])}</span>
    </div>
  </div>"""


def home_todo_pins_html(todos, tabs):
    """지금 할 일을 급한 순서대로 아이콘으로. 마우스를 올리면(또는 Tab으로 고르면) 그 할 일 카드가 팝업으로 뜸"""
    if not todos:
        return '<div class="home-sub">지금 할 일이 없어요. A/B 결과·폭염 예보·광고 알림이 오면 여기에 떠요.</div>'
    pins = []
    for n, t in enumerate(todos[:3], start=1):
        short = t["title"].split(" · ", 1)[-1].split(" | ", 1)[-1]   # '① 1순위 · 내부 | 제목' → '제목'
        pins.append(f"""
  <div class="home-tpin" tabindex="0">
    <span class="home-tpin-icon">{home_todo_icon(t)}<span class="home-tpin-num" style="background:{HOME_WHEN_COLOR.get(t["when"], C["purple"])}">{n}</span></span>
    <span class="home-tpin-text">{home_when(t["when"])}<b>{home_esc(short)}</b></span>
    <div class="home-tpin-pop">{home_todo_card(n, t, tabs)}</div>
  </div>""")
    return "".join(pins)


# ── 진행 카드 3개: ② 가설 / ③ A/B 소재 / 경쟁사 가격 ────────
def home_card_hypothesis(stores, tabs):
    hyp = stores.get("hypothesis") or {}
    sel = hyp.get("selected") if isinstance(hyp.get("selected"), dict) else {}
    then, if_ = sel.get("then") or hyp.get("then_text"), sel.get("if") or hyp.get("if_text")
    problem = (sel.get("problem") or {}).get("title") or hyp.get("problem_title")
    if then and if_:
        body = (f'<div class="home-card-main home-clamp-2">{home_esc(then)}</div>'
                f'<div class="home-card-sub home-clamp-2"><b>If</b> {home_esc(if_)}</div>'
                + (f'<div class="home-chip home-clamp-1">문제 · {home_esc(problem)}</div>' if problem else ""))
    elif hyp.get("hypothesis") or hyp.get("text"):
        body = f'<div class="home-card-main home-clamp-3">{home_esc(hyp.get("text") or hyp.get("hypothesis"))}</div>'
    else:
        body = ('<div class="home-card-main">아직 고른 가설이 없어요</div>'
                '<div class="home-card-sub">② 가설 세우기에서 가설 1·2·3 중 하나를 골라 주세요.</div>')
    return home_card(tabs, "hypothesis", "② 선택한 가설", body)


def home_card_media(stores, tabs):
    media = stores.get("media") or {}
    plan = (media.get("handoff") or {}).get("plan") if isinstance(media.get("handoff"), dict) else None
    if isinstance(plan, dict) and plan.get("variable"):
        kpi = (f'<div class="home-chip">노출 대비 클릭률 {plan["kpi_now"]}배 → {plan["kpi_goal"]}배 목표</div>'
               if plan.get("kpi_now") and plan.get("kpi_goal") else "")
        body = (f'<div class="home-card-main home-clamp-1">{home_esc(plan["variable"])}</div>'
                f'<div class="home-ab"><span class="home-ab-tag">A</span><span class="home-clamp-1">{home_esc(plan.get("a"))}</span></div>'
                f'<div class="home-ab"><span class="home-ab-tag home-ab-b">B</span><span class="home-clamp-1">{home_esc(plan.get("b"))}</span></div>'
                f'{kpi}')
    else:
        body = ('<div class="home-card-main">아직 A/B 변수를 정하지 않았어요</div>'
                '<div class="home-card-sub">③ 광고 소재에서 바꿔 볼 변수 하나를 확정하면 A안·B안이 여기에 보여요.</div>')
    return home_card(tabs, "media", "③ A/B 소재", body)


def home_card_competitors(stores, tabs):
    """경쟁사 가격 (Amazon.de, ① 리포트의 Keepa 값): 우리와 경쟁사 현재가 막대 + 한 줄 요약"""
    report = stores.get("report") or {}
    seori = report.get("seori_profile") or {}
    profiles = {p.get("brand"): p for p in report.get("competitor_profiles") or [] if isinstance(p, dict)}
    rows = [{"brand": s["brand"], "price": s["price"], "change": s.get("price_change_90d"), "stock": s.get("in_stock"), "us": False,
             "rating": (profiles.get(s["brand"]) or {}).get("rating"), "reviews": (profiles.get(s["brand"]) or {}).get("reviews")}
            for s in report.get("competitor_signals") or [] if isinstance(s, dict) and s.get("price")]
    if seori.get("amazon_price"):
        rows.append({"brand": "SEORI (우리)", "price": seori["amazon_price"], "change": seori.get("price_change_90d"),
                     "stock": True, "us": True, "rating": seori.get("rating"), "reviews": seori.get("reviews")})
    if len(rows) < 2:
        body = ('<div class="home-card-main">경쟁사 가격이 아직 없어요</div>'
                '<div class="home-card-sub">① 문제 분석을 열면 Amazon.de 경쟁사 현재가(Keepa)가 여기에 보여요.</div>')
        return home_card(tabs, "report", "경쟁사 가격 · Amazon.de", body, "home-card-tall")
    rows.sort(key=lambda r: r["price"])
    top = max(r["price"] for r in rows)
    us = next((r for r in rows if r["us"]), None)
    cheapest = next((r for r in rows if not r["us"]), None)
    gap = us["price"] - cheapest["price"] if us and cheapest else 0
    summary = (f'최저가 {home_esc(cheapest["brand"])}보다 <b>€{gap:.2f} 비싸요</b>' if gap > 0
               else "우리가 가장 싸요") if us and cheapest else ""
    bars = "".join(
        f'<div class="home-price-row{" home-price-us" if r["us"] else ""}">'
        f'<div class="home-row-between"><span>{home_esc(r["brand"])}{" <i>품절</i>" if r["stock"] is False else ""}</span>'
        f'<b>€{r["price"]:.2f}</b></div>'
        f'<div class="home-bar"><span style="width:{r["price"] / top * 100:.0f}%"></span></div>'
        + (f'<div class="home-sub">평점 {r["rating"]:.1f} · 리뷰 {r["reviews"]:,}건</div>' if r.get("rating") and r.get("reviews") is not None else "")
        + '</div>'
        for r in rows[:5])
    fetched = str((report.get("competitor_signals") or [{}])[0].get("fetched_at") or "")[:10]
    body = (f'<div class="home-card-main">{summary}</div>{bars}'
            f'<div class="home-card-sub">현재가 · Keepa{f" {fetched}" if fetched else ""} 기준</div>')
    return home_card(tabs, "report", "경쟁사 가격 · Amazon.de", body, "home-card-tall")


def home_left_html(stores, temps, tabs, todos):
    """왼쪽 (레퍼런스 'General statistics' 배치): 제목 → 큰 숫자 자리에 독일 시간 → 지금 할 일 아이콘(세로) → 진행 카드 3개"""
    return f"""
<div class="home-left">
  <div class="home-title">독일 시장 한눈에 보기</div>
  {home_clock_html()}
  <div class="home-tpins">{home_todo_pins_html(todos, tabs)}</div>
  <div class="home-cards">
    <div class="home-cards-col">
      {home_card_hypothesis(stores, tabs)}
      {home_card_media(stores, tabs)}
    </div>
    {home_card_competitors(stores, tabs)}
  </div>
</div>"""


def home_clock_html():
    """큰 숫자 자리(예전 '광고 빈도 추천'): 독일(베를린) 지금 시간. 처음 값은 서버가 넣고, 브라우저가 1초마다 고침 (HOME_NAV_JS)"""
    try:
        now = datetime.now(ZoneInfo("Europe/Berlin"))
    except Exception:   # 시간대 정보가 없는 환경이면 UTC+1로 대신
        now = datetime.now(timezone(timedelta(hours=1)))
    # 한국(UTC+9)과의 시차 (서버 시간대와 상관없이): 독일 겨울 8시간, 여름 7시간
    gap = round(9 - now.utcoffset().total_seconds() / 3600)
    gap_text = f"한국보다 {gap}시간 느려요" if gap > 0 else "한국과 같은 시간" if gap == 0 else f"한국보다 {-gap}시간 빨라요"
    return f"""
<div class="home-clock">
  <div class="home-clock-label"><i></i>독일 시간 · 베를린</div>
  <div class="home-clock-time" data-home-clock="time">{now:%H:%M}<span data-home-clock="sec">:{now:%S}</span></div>
  <div class="home-clock-sub"><span data-home-clock="date">{now.month}월 {now.day}일 ({HOME_WEEKDAYS[now.weekday()]})</span> · {gap_text}</div>
</div>"""


def home_line_svg(values):
    """작은 꺾은선 (레퍼런스 'Sales trend' 모양): 보라 선 + 옅은 면"""
    if len(values) < 2:
        return ""
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    pts = [(i / (len(values) - 1) * 200, 52 - (v - lo) / span * 40) for i, v in enumerate(values)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 60" preserveAspectRatio="none">'
           f'<polygon points="0,60 {line} 200,60" fill="{C["purple"]}" fill-opacity="0.10"/>'
           f'<polyline points="{line}" fill="none" stroke="{C["purple"]}" stroke-width="2.5" stroke-linejoin="round" '
           f'stroke-linecap="round" vector-effect="non-scaling-stroke"/></svg>')
    return home_svg_img(svg, "home-line-img")


def home_ring_svg(ratio, color):
    """동그란 진행 고리 (레퍼런스 '27% Active users' 모양)"""
    r, c = 20, 2 * 3.14159 * 20
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">'
           f'<circle cx="24" cy="24" r="{r}" fill="none" stroke="#E6E6F0" stroke-width="3.5"/>'
           f'<circle cx="24" cy="24" r="{r}" fill="none" stroke="{color}" stroke-width="3.5" stroke-linecap="round" '
           f'stroke-dasharray="{c * min(max(ratio, 0), 1):.1f} {c:.1f}" transform="rotate(-90 24 24)"/></svg>')
    return home_svg_img(svg, "home-ring-img")


def home_ad_panel_html(temps, weather, ad, tabs):
    """지구본 오른쪽 위: 지역별 광고 비중 (레퍼런스 'Quantity of data' 자리). 글씨는 모두 독일 시간 글씨보다 작게.
    지역 비중은 ④와 같은 규칙으로 홈 도시 예보에서 계산(home_region_shares), 7일 꺾은선은 ④가 저장한 날짜별 아마존 예산"""
    rows, hot = home_region_shares(temps)
    if not rows:
        return ""
    weather = weather or {}
    amazon = weather.get("amazon")
    top = rows[0]
    big = (f'{top["share"]:.0f}<small>%</small>' if hot else "25<small>%</small>")
    big_label = f'{top["name"]} 지역이 가장 많이' if hot else "4개 지역 똑같이"
    note = (f"{HOME_HEAT_TEMP}°C↑ 예보 지역에 더" if hot else f"{HOME_HEAT_TEMP}°C↑ 예보 없음")
    daily = weather.get("amazon_daily") or []
    trend = home_line_svg(daily) if daily else ""
    def share_row(r):
        eur = "€{:,.0f}".format(amazon * r["share"] / 100) if amazon else ""
        cls, arrow = ("home-up", "▲") if r["share"] > 25.5 else ("home-down", "▼") if r["share"] < 24.5 else ("home-flat", "–")
        return (f'<div class="home-share-row"><span>{r["name"]}</span><span class="home-sub">최고 {r["max7"]:.0f}°</span>'
                f'<b>{r["share"]:.0f}%</b><span class="home-sub">{eur}</span><i class="{cls}">{arrow}</i></div>')

    table = "".join(share_row(r) for r in rows)
    hot_days = len({i for p in temps for i, d in enumerate((p.get("daily") or [])[:7]) if d["max"] >= HOME_HEAT_TEMP})
    mult = ad[0]
    rings = "".join(
        f'<div class="home-ring">{home_ring_svg(ratio, color)}<span class="home-ring-num">{num}</span>'
        f'<div><b>{value}</b><span class="home-sub">{label}</span></div></div>'
        for ratio, color, num, value, label in [
            (hot_days / 7, C["orange"], f"{hot_days}/7", f"폭염 예보 {hot_days}일", f"{HOME_HEAT_TEMP}°C 이상 · 7일 중"),
            (min(mult - 1, 1), C["purple"], f"x{mult:.1f}", f"광고 빈도 +{(mult - 1) * 100:.0f}%", "가장 많이 쓰는 날 ÷ 평균"),
        ])
    return f"""
<div class="home-adpanel home-click" data-home-goto="{tabs["weather"][0]}" title="{tabs["weather"][1]}에서 자세히">
  <div class="home-adpanel-title">지역별 광고 비중 <span class="home-card-go">→</span></div>
  <div class="home-sub">이번 주 아마존 예산 · 지역 타겟</div>
  <div class="home-adpanel-big">{big}</div>
  <div class="home-sub">{big_label} · {note}</div>
  {f'<div class="home-line">{trend}<div class="home-row-between home-sub"><span>오늘</span><span>7일 아마존 예산</span></div></div>' if trend else ""}
  <div class="home-share">{table}</div>
  {f'<div class="home-sub">주간 아마존 예산 €{amazon:,.0f} (④ 저장값)</div>' if amazon else ""}
  <div class="home-rings">{rings}</div>
</div>"""


def home_legend_html():
    """지구본 아래: 핀 색이 뜻하는 것 (평소 보라, 경고일 때만 주황·빨강)"""
    dots = "".join(f'<span><i style="background:{color}"></i>{name}</span>' for name, color in [
        ("평소", HOME_PIN), (f"더위 주의 {HOME_HEAT_TEMP}°↑", HOME_PIN_WARN), (f"폭염경보 {HOME_HEAT_WARN}°↑", HOME_PIN_HOT)])
    return f'<div class="home-legend">{dots}<span class="home-legend-pop"><i></i>원 크기 = 도시 인구</span></div>'


def home_render():
    """'홈' 탭을 열 때마다 실행됩니다. 화면은 전부 이 함수 안에서 그립니다."""
    temps, live = home_get_temps()
    scenario = st.query_params.get("scenario") == "heat"   # 시연용: 주소 끝에 ?scenario=heat
    if scenario:
        temps = home_heat_scenario(temps)
    stores, demo = home_read_stores()
    tabs = home_tab_info()
    todos = home_todos(stores, temps)
    # 진행 카드는 실제 저장값만 보여 줌 (샘플 가설을 진짜 선택한 가설처럼 보이지 않게)
    real = {code: (None if code in demo else value) for code, value in stores.items()}

    source = "시연용 폭염 시나리오" if scenario else "실시간 기온 · Open-Meteo" if live else "샘플 기온 (실시간 조회 실패)"
    css_vars = ";".join(f"--home-{k}:{v}" for k, v in C.items())
    st.html(
        f"""
<div class="home-board" style="{css_vars}">
  {home_left_html(real, temps, tabs, todos)}
  <div class="home-globe">
    <div class="home-globe-wrap">{home_globe_svg()}{home_city_layer(temps, home_city_warning)}</div>
    <div class="home-globe-shadow"></div>
  </div>
  {home_ad_panel_html(temps, real.get("weather"), home_ad_multiplier(stores, temps), tabs)}
  <div class="home-globe-foot">
    {home_legend_html()}
    <div class="home-globe-cap">{source}{" · 일부 샘플 데이터" if demo else ""} · {HOME_POP_SOURCE} · 핀에 마우스를 올리면 예보</div>
  </div>
</div>"""
    )
    components.html(HOME_NAV_JS, height=0)
