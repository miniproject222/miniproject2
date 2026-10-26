# 홈 = 관제실: "오늘 뭘 먼저 해야 하는지" 알려 주는 출발점
# 배치 (2026-10-26 레퍼런스 'General statistics' 모양): 왼쪽(제목 → 큰 숫자 광고 빈도 → 아이콘 숫자 2개 → 카드 3개)
#   → 오른쪽(하얀 입체 지구본, 독일 위주) → 오른쪽 아래(지금 할 일 아이콘, 누르면 팝업)
# 위 "가장 먼저" 줄·아래 "마케팅 사이클" 줄은 지금 할 일과 내용이 겹쳐 삭제, 지금 할 일은 아이콘 팝업으로
# 할 일 버튼을 누르면 해당 탭으로 바로 이동 (HOME_NAV_JS)
# 홈 탭이 열려 있으면 화면 전체를 채웁니다 (home_style.css)
# 다른 탭이 구현 전이면 샘플 데이터로 채우고 "샘플" 표시 (데이터 모양은 home_data.py 맨 위 참고)
from datetime import date
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from modules.home.home_data import (
    HOME_HEAT_TEMP, HOME_HEAT_WARN, home_ad_multiplier, home_city_warning, home_heat_scenario, home_read_stores,
    home_todos,
)
from modules.home.home_globe import (
    HOME_TEMP_COLD, HOME_TEMP_HOT, HOME_TEMP_STEPS, HOME_TEMP_WARM, HOME_WEEKDAYS, home_city_layer, home_get_temps,
    home_globe_svg, home_heat_color, home_svg_img, home_temp_color,
)

HOME_DIR = Path(__file__).resolve().parent   # 내 폴더 (images/, data/ 경로 만들 때 사용)

# 레퍼런스와 같게 보이도록 쓰는 색 (홈 탭 안에서만 적용)
HOME_COLORS = {
    "board": "#F5F6FB", "card": "#FFFFFF", "text": "#2B2D4F", "sub": "#A3A5BD", "line": "#ECEDF4",
    "purple": "#7B6CF2", "pink": "#F2708F", "orange": "#F9A65A", "green": "#3CC58A", "blue": "#46A6F5",
    "red": "#F2546B", "up": "#2DB67C", "down": "#F2708F",
}
C = HOME_COLORS
HOME_WHEN_COLOR = {"지금": C["red"], "오늘": C["orange"], "이번 주": C["blue"]}

# 탭 이동 버튼(data-home-goto="탭 번호")을 누르면 왼쪽 탭을 대신 눌러 주는 스크립트.
# 할 일 팝업 안의 ×(data-home-close)나 탭 이동 버튼을 누르면 팝업(details.home-fab)을 닫습니다.
# st.html은 스크립트를 지우므로, 보이지 않는 components.html 안에서 부모 화면에 클릭 처리기를 한 번만 붙입니다.
# (이름을 __homeNav3로 바꿔, 예전 처리기가 붙어 있던 브라우저에도 새 처리기가 붙게 함)
# 할 일 팝업은 아이콘에 마우스를 올리면 열림 (2026-10-26 요청: 버튼 대신 호버)
HOME_NAV_JS = """
<script>
const P = window.parent;
if (!P.__homeNav3) {
  P.__homeNav3 = true;
  P.document.addEventListener("click", (e) => {
    const go = e.target.closest("[data-home-goto]");
    if (go) {
      e.preventDefault();
      const list = P.document.querySelector('[data-testid="stTabs"] [role="tablist"]');
      const tab = list && list.querySelectorAll('[role="tab"]')[Number(go.dataset.homeGoto)];
      if (tab) tab.click();
    }
    const close = e.target.closest("[data-home-close], [data-home-goto]");
    const fab = close && close.closest("details.home-fab");
    if (fab) fab.open = false;
    // 팝업 바깥을 누르면 닫기
    if (!e.target.closest("details.home-fab")) {
      P.document.querySelectorAll("details.home-fab[open]").forEach((d) => { d.open = false; });
    }
  });
  // Esc 키로 팝업 닫기
  P.document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") P.document.querySelectorAll("details.home-fab[open]").forEach((d) => { d.open = false; });
  });
  // 할 일 팝업 열림 상태 유지: 화면이 다시 그려지면(st.html 교체) 팝업이 닫히므로, 마지막 상태를 기억했다가 다시 적용.
  // 페이지를 처음 열었을 때는 할 일이 있으면 한 번 열어 둠 (예전 '처음 접속 팝업'을 대신함)
  P.__homeTodoOpen = true;
  const sync = () => P.document.querySelectorAll("details.home-fab:not([data-home-hover])").forEach((d) => {
    d.dataset.homeHover = "1";
    d.open = P.__homeTodoOpen && !!d.querySelector(".home-fab-count");
    d.addEventListener("toggle", () => { P.__homeTodoOpen = d.open; });
    // 마우스를 올리면 열고, 벗어나면 잠깐 뒤 닫음 (아이콘 → 팝업으로 옮기는 사이 빈틈에서 닫히지 않게 0.3초 기다림)
    let timer = null;
    d.addEventListener("mouseenter", () => { clearTimeout(timer); d.open = true; });
    d.addEventListener("mouseleave", () => { timer = setTimeout(() => { d.open = false; }, 300); });
    // 아이콘을 눌러도 닫히지 않고 열리기만 (터치 화면용, 마우스로 열린 상태에서 누르면 닫혀 버리는 것 방지)
    d.querySelector("summary").addEventListener("click", (e) => { e.preventDefault(); d.open = true; });
  });
  sync();
  new P.MutationObserver(sync).observe(P.document.body, {childList: true, subtree: true});
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
def home_delta(value, unit="%"):
    up = value >= 0
    color = C["up"] if up else C["down"]
    shown = f"{abs(value) * 100:.0f}%" if unit == "%" else f"{abs(value):.1f}{unit}"
    return f'<span class="home-delta" style="color:{color}">{"▲" if up else "▼"} {shown}</span>'


def home_demo_tag(is_demo):
    return '<span class="home-demo">샘플</span>' if is_demo else ""


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


# ── 영역별 HTML ──────────────────────────────
def home_todo_html(todos, tabs):
    """할 일 팝업 안 내용: 지금 할 일 (급한 순, 큰 카드 ①·④ + 나머지 한 줄씩)"""
    if not todos:
        return f"""
  <div class="home-float home-first home-first-empty">{home_icon("bell", C["blue"])}<div><b>지금 할 일이 없어요</b>
  <div class="home-sub">A/B 결과, 폭염 예보, 광고 빈도 알림이 오면 여기에 순서대로 표시됩니다</div></div></div>"""
    # 큰 카드 2개: 위 ① 문제 분석 핵심 요약, 아래 ④ 광고 타이밍 알림 (slot). 나머지는 한 줄씩 접어서
    cards = [t for t in todos if t.get("slot")][:2] or todos[:1]
    rest = [t for t in todos if t not in cards][:3]

    def card(n, t):
        accent = "home-first" if n == 1 else "home-first home-second"
        return f"""
  <div class="home-float {accent}">
    <div class="home-first-top"><span class="home-num-badge home-num-first">{n}</span>{home_when(t["when"])}<span class="home-sub">{tabs[t["goto"]][1]}</span></div>
    <div class="home-first-body">{home_todo_icon(t)}<div class="home-first-title">{t["title"]}</div></div>
    <p class="home-first-why"><b>왜?</b> {t["detail"]}</p>
    <div class="home-row-between home-first-foot">
      {home_go(tabs, t["goto"], t["action"], "home-go home-go-lg")}
      <span class="home-next">다음 → {t["next"]}</span>
    </div>
  </div>"""

    rest_html = "".join(
        f'<details class="home-fold home-todo"><summary>'
        f'<span class="home-num-badge">{i}</span>'
        f'<div><div class="home-todo-title">{home_when(t["when"])}{t["title"]}</div>'
        f'<span class="home-sub">{tabs[t["goto"]][1]}</span></div>'
        f'{home_go(tabs, t["goto"], "보기", "home-go home-go-sm")}</summary>'
        f'<p>{t["detail"]}<br><span class="home-next">다음 → {t["next"]}</span></p></details>'
        for i, t in enumerate(rest, start=len(cards) + 1)
    )
    return "".join(card(n, t) for n, t in enumerate(cards, start=1)) + rest_html


def home_fab_html(todos, tabs):
    """오른쪽 아래: 지금 할 일 아이콘(할 일 개수) + 꺾인 화살표 안내. 누르면 할 일이 팝업으로 열림.
    페이지를 처음 열면 한 번 자동으로 열리고, 열림/닫힘 상태는 다시 그려져도 유지됨 (HOME_NAV_JS)"""
    s ='fill="none" stroke="#FFFFFF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"'
    icon = home_svg_img(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M9 6h11M9 12h11M9 18h11" {s}/>'
        f'<path d="M3.5 6l1.3 1.3L7 5M3.5 12l1.3 1.3L7 11M3.5 18l1.3 1.3L7 17" {s}/></svg>', "home-fab-img")
    # 꺾인 화살표: 안내 글씨에서 아래로 내려와 오른쪽 아이콘을 가리킴
    a = f'stroke="{C["purple"]}" stroke-width="2.4" fill="none" stroke-linecap="round" stroke-linejoin="round"'
    arrow = home_svg_img(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 50"><path d="M8 4 Q6 40 50 40" {a}/>'
        f'<path d="M42 32 L51 40 L42 48" {a}/></svg>', "home-fab-arrow")
    count = f'<span class="home-fab-count">{len(todos)}</span>' if todos else ""
    return f"""
<details class="home-fab">
  <summary aria-label="지금 할 일 열기">
    <span class="home-fab-hint">지금 할 일 확인하기{arrow}</span>
    <span class="home-fab-btn">{icon}{count}</span>
  </summary>
  <div class="home-fab-panel">
    <div class="home-row-between home-fab-head">
      <span class="home-label">지금 할 일 <span class="home-count">{len(todos)}</span></span>
      <button type="button" class="home-pop-x" data-home-close="1" aria-label="닫기">×</button>
    </div>
    {home_todo_html(todos, tabs)}
  </div>
</details>"""


def home_bars_html(rows):
    """막대 목록 [(이름, 값 글자, 0~1 비율, 색)] (레퍼런스 'January 613' 막대 모양)"""
    return "".join(
        f'<div class="home-bar-row"><div class="home-row-between"><span>{name}</span><b>{value}</b></div>'
        f'<div class="home-ab-bar"><span style="width:{ratio * 100:.0f}%;background:{color}"></span></div></div>'
        for name, value, ratio, color in rows)


def home_card_head(title, tabs, code):
    """카드 맨 위 줄: 제목 + 오른쪽 '자세히 →' (누르면 그 내용을 자세히 보는 탭으로)"""
    return f'<div class="home-row-between"><span class="home-sub">{title}</span>{home_go(tabs, code, "자세히", "home-go home-go-sm")}</div>'


def home_card_sales_html(report, is_demo, temps, tabs):
    """작은 카드 1: 전날 매출 (데이터가 없으면 내일 평균 최고 기온, 오늘과 비교)"""
    sales = report.get("yesterday_sales")
    if sales is not None:
        return f"""
  <div class="home-float home-card-sm">
    {home_card_head(f"전날 매출 {home_demo_tag(is_demo)}", tabs, "report")}
    <div class="home-card-num">€{sales:,.0f}{home_delta(report.get("sales_delta", 0))}</div>
    <div class="home-sub">전일 대비</div>
  </div>"""
    now = sum(p["temp"] for p in temps) / len(temps)
    tomorrow = sum(p.get("tomorrow", p["temp"]) for p in temps) / len(temps)
    return f"""
  <div class="home-float home-card-sm">
    {home_card_head("내일 평균 최고 기온", tabs, "weather")}
    <div class="home-card-num">{tomorrow:.0f}°C{home_delta(tomorrow - now, "°")}</div>
    <div class="home-sub">지금 평균 {now:.0f}°C 대비 · 독일 {len(temps)}개 도시</div>
  </div>"""


def home_card_bars_html(report, is_demo, temps, tabs):
    """작은 카드 2: A/B 테스트 클릭률 막대 (데이터가 없으면 이번 주 가장 더운 도시 3곳)"""
    ab = report.get("ab_test") or {}
    a, b = ab.get("a") or {}, ab.get("b") or {}
    if a.get("ctr") and b.get("ctr"):
        top = max(a["ctr"], b["ctr"])
        better = "A안" if a["ctr"] >= b["ctr"] else "B안"
        rows = [(v.get("label", k), f'{v["ctr"]:.1f}%', v["ctr"] / top, color)
                for k, v, color in [("A안", a, C["purple"]), ("B안", b, C["pink"])]]
        return f"""
  <div class="home-float home-card-sm">
    {home_card_head(f"A/B 테스트 클릭률 {home_demo_tag(is_demo)}", tabs, "report")}
    <div class="home-card-num">{max(a["ctr"], b["ctr"]):.1f}%<span class="home-sub"> {better} 우세</span></div>
    {home_bars_html(rows)}
  </div>"""
    hot = sorted(temps, key=lambda p: -p.get("week_max", p["temp"]))[:3]
    top = max(hot[0].get("week_max", hot[0]["temp"]), 1)
    rows = [(f'{p["city"]} ({p.get("week_day", "")})', f'{p.get("week_max", p["temp"]):.0f}°',
             max(p.get("week_max", p["temp"]), 0) / top, home_temp_color(p.get("week_max", p["temp"]))) for p in hot]
    return f"""
  <div class="home-float home-card-sm">
    {home_card_head("이번 주 가장 더운 도시", tabs, "weather")}
    <div class="home-card-num">{hot[0].get("week_max", hot[0]["temp"]):.0f}°C<span class="home-sub"> {hot[0]["city"]}</span></div>
    {home_bars_html(rows)}
  </div>"""


def home_heatmap_html(temps, tabs):
    """세로로 긴 카드: 7일 최고 기온 예보 (도시 × 요일 칸, 레퍼런스 'Total activity' 모양). 30°C↑ 칸은 테두리"""
    days = [d["day"] for d in (temps[0].get("daily") or [])][:7]
    values = [d["max"] for p in temps for d in (p.get("daily") or [])[:7]]
    lo, hi = min(values, default=0), max(values, default=1)
    head = '<span></span>' + "".join(f'<span class="home-heat-day">{"오늘" if i == 0 else d}</span>' for i, d in enumerate(days))

    def cell(p, d):
        hot = d["max"] >= HOME_HEAT_TEMP
        light = not hot and (d["max"] - lo) / ((hi - lo) or 1) < 0.45   # 연한 칸은 진한 글씨
        cls = "home-heat-cell" + (" home-heat-hot" if hot else "") + (" home-heat-light" if light else "")
        return (f'<span class="{cls}" style="background:{home_heat_color(d["max"], lo, hi)}" '
                f'title="{p["city"]} {d["day"]} 최고 {d["max"]:.0f}°C">{d["max"]:.0f}</span>')

    rows = "".join(f'<span class="home-heat-city">{p["city"]}</span>' + "".join(cell(p, d) for d in (p.get("daily") or [])[:7])
                   for p in temps)
    week_top = max(temps, key=lambda p: p.get("week_max", p["temp"]))
    return f"""
  <div class="home-float home-card-heat">
    {home_card_head("7일 최고 기온 예보", tabs, "weather")}
    <div class="home-card-num">{week_top.get("week_max", week_top["temp"]):.0f}°C<span class="home-sub"> 이번 주 최고 · {week_top["city"]}</span></div>
    <div class="home-heat" style="--days:{len(days)}">{head}{rows}</div>
    <div class="home-sub home-heat-note">진할수록 더움 · 빨간 칸 = {HOME_HEAT_TEMP}°C 이상 (광고 빈도 올릴 날)</div>
  </div>"""


def home_left_html(stores, demo, temps, ad, tabs):
    """왼쪽 (레퍼런스 배치): 제목 → 큰 숫자(광고 빈도 추천) → 아이콘 숫자 2개(최고 기온·더위 경보) → 카드 3개"""
    report = stores.get("report") or {}
    is_demo = "report" in demo
    today = date.today()
    mult, reason, linked = ad

    top = max(temps, key=lambda p: p["temp"])
    warns = [home_city_warning(p)[0] for p in temps]
    heat_n, warn_n = warns.count("폭염경보"), sum(1 for w in warns if w)
    alert = (f'폭염경보 {heat_n}곳' if heat_n else f'더위 주의 {warn_n}곳') if warn_n else "경보 없음"
    # 아이콘 숫자는 누르면 ④ 광고 타이밍으로 (기온·경보를 자세히 보는 곳)
    stats = "".join(
        f'<button type="button" class="home-mini" data-home-goto="{tabs["weather"][0]}" title="④ 광고 타이밍에서 자세히">'
        f'{home_icon(kind, color)}<div><div class="home-mini-label">{label}</div><b>{value}</b></div></button>'
        for kind, color, label, value in [
            ("sun", C["orange"], "지금 최고 기온", f'{top["city"]} {top["temp"]:.0f}°C'),
            ("bell", C["red"] if warn_n else C["blue"], f"더위 경보 ({HOME_HEAT_TEMP}°C↑)", alert),
        ])
    return f"""
<div class="home-left">
  <div class="home-title">독일 시장 한눈에 보기 <span class="home-sub">{today:%Y-%m-%d} ({HOME_WEEKDAYS[today.weekday()]})</span></div>
  <div class="home-hero-label">광고 빈도 추천 {home_demo_tag(linked and "weather" in demo)}
    {home_go(tabs, "weather", "조정", "home-go home-go-sm")}</div>
  <div class="home-hero">x{mult:.1f}</div>
  <div class="home-hero-why"><b>평소보다 광고 노출을 {mult:.1f}배로</b> 올리기 추천 <span class="home-sub">· {reason}</span></div>
  <div class="home-minis">{stats}</div>
  <div class="home-cards">
    <div class="home-cards-col">
      {home_card_sales_html(report, is_demo, temps, tabs)}
      {home_card_bars_html(report, is_demo, temps, tabs)}
    </div>
    {home_heatmap_html(temps, tabs)}
  </div>
</div>"""


def home_legend_html():
    """지구본 아래: 도시 점 색이 뜻하는 것"""
    warm, hot = HOME_TEMP_STEPS
    dots = "".join(f'<span><i style="background:{color}"></i>{name}</span>' for name, color in [
        (f"시원 {warm}°↓", HOME_TEMP_COLD), (f"따뜻 {warm}~{hot - 1}°", HOME_TEMP_WARM), (f"더움 {hot}°↑", HOME_TEMP_HOT)])
    return (f'<div class="home-legend" title="핀 아래 원이 클수록 더운 도시">{dots}'
            f'<span class="home-sub">폭염경보 {HOME_HEAT_WARN}°C↑</span></div>')


def home_render():
    """'홈' 탭을 열 때마다 실행됩니다. 화면은 전부 이 함수 안에서 그립니다."""
    temps, live = home_get_temps()
    scenario = st.query_params.get("scenario") == "heat"   # 시연용: 주소 끝에 ?scenario=heat
    if scenario:
        temps = home_heat_scenario(temps)
    stores, demo = home_read_stores()
    tabs = home_tab_info()
    todos = home_todos(stores, temps)
    ad = home_ad_multiplier(stores, temps)

    source = "시연용 폭염 시나리오" if scenario else "실시간 기온 · Weather data by Open-Meteo.com" if live else "샘플 기온 (실시간 조회 실패)"
    css_vars = ";".join(f"--home-{k}:{v}" for k, v in C.items())
    st.html(
        f"""
<div class="home-board" style="{css_vars}">
  {home_left_html(stores, demo, temps, ad, tabs)}
  <div class="home-globe">
    <div class="home-globe-wrap">{home_globe_svg()}{home_city_layer(temps, home_city_warning)}</div>
    {home_legend_html()}
    <div class="home-globe-cap">{source}{" · 일부 샘플 데이터" if demo else ""} · 도시에 마우스를 올려 보세요</div>
  </div>
  {home_fab_html(todos, tabs)}
</div>"""
    )
    components.html(HOME_NAV_JS, height=0)
