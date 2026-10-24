# 홈 = 관제실: "오늘 뭘 먼저 해야 하는지" 알려 주는 출발점
# 읽는 순서대로 배치: 위(한 줄 상황 요약) → 왼쪽(지금 할 일, 급한 순) → 가운데(날씨 지구본) → 오른쪽(지금 상황 숫자)
#                    → 아래(마케팅 사이클: 지금 어디까지 왔고 다음은 무엇인지)
# 팝업·할 일·단계 버튼을 누르면 해당 탭으로 바로 이동 (HOME_NAV_JS)
# 홈 탭이 열려 있으면 화면 전체를 채웁니다 (home_style.css)
# 다른 탭이 구현 전이면 샘플 데이터로 채우고 "샘플" 표시 (데이터 모양은 home_data.py 맨 위 참고)
from datetime import date
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from modules.home.home_data import (
    HOME_STEPS, home_ad_multiplier, home_city_warning, home_heat_scenario, home_read_stores, home_todos,
)
from modules.home.home_globe import HOME_WEEKDAYS, home_city_layer, home_get_temps, home_globe_svg, home_svg_img

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
# st.html은 스크립트를 지우므로, 보이지 않는 components.html 안에서 부모 화면에 클릭 처리기를 한 번만 붙입니다.
HOME_NAV_JS = """
<script>
const P = window.parent;
if (!P.__homeNav) {
  P.__homeNav = true;
  P.document.addEventListener("click", (e) => {
    const go = e.target.closest("[data-home-goto]");
    if (go) {
      e.preventDefault();
      const list = P.document.querySelector('[data-testid="stTabs"] [role="tablist"]');
      const tab = list && list.querySelectorAll('[role="tab"]')[Number(go.dataset.homeGoto)];
      if (tab) tab.click();
    }
    const close = e.target.closest("[data-home-close], [data-home-goto]");
    const pop = close && close.closest(".home-pop");
    if (pop) pop.remove();
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
def home_head_html(todos, tabs):
    """맨 위: 날짜 + 한 줄 상황 요약 (가장 먼저 할 일)"""
    today = date.today()
    if todos:
        first = todos[0]
        rest = f'<span class="home-sub"> · 그다음 {len(todos) - 1}건 대기</span>' if len(todos) > 1 else ""
        line = f'가장 먼저 <b>{first["title"]}</b> {home_go(tabs, first["goto"], first["action"], "home-go home-go-sm")}{rest}'
    else:
        line = "오늘은 급한 일이 없어요. 마케팅 사이클을 이어서 진행하세요."
    return f"""
<div class="home-head">
  <div class="home-title">오늘의 관제실 <span class="home-sub">{today:%Y-%m-%d} ({HOME_WEEKDAYS[today.weekday()]})</span></div>
  <div class="home-headline">{line}</div>
</div>"""


def home_todo_html(todos, tabs):
    """왼쪽 주인공: 지금 할 일 (급한 순, 1번은 크게)"""
    if not todos:
        return f"""
<div class="home-todo-col">
  <div class="home-label">지금 할 일 <span class="home-count">0</span></div>
  <div class="home-float home-first">{home_icon("bell", C["blue"])}<div><b>지금 할 일이 없어요</b>
  <div class="home-sub">A/B 결과, 폭염 예보, 광고 빈도 알림이 오면 여기에 순서대로 표시됩니다</div></div></div>
</div>"""
    first, rest = todos[0], todos[1:4]
    rest_html = "".join(
        f'<details class="home-fold home-todo"><summary>'
        f'<span class="home-num-badge">{i}</span>'
        f'<div><div class="home-todo-title">{home_when(t["when"])}{t["title"]}</div>'
        f'<span class="home-sub">{tabs[t["goto"]][1]}</span></div>'
        f'{home_go(tabs, t["goto"], "보기", "home-go home-go-sm")}</summary>'
        f'<p>{t["detail"]}<br><span class="home-next">다음 → {t["next"]}</span></p></details>'
        for i, t in enumerate(rest, start=2)
    )
    return f"""
<div class="home-todo-col">
  <div class="home-label">지금 할 일 <span class="home-count">{len(todos)}</span><span class="home-link">위에서부터 순서대로</span></div>
  <div class="home-float home-first">
    <div class="home-first-top"><span class="home-num-badge home-num-first">1</span>{home_when(first["when"])}<span class="home-sub">가장 먼저</span></div>
    <div class="home-first-body">{home_todo_icon(first)}<div class="home-first-title">{first["title"]}</div></div>
    <p class="home-first-why"><b>왜?</b> {first["detail"]}</p>
    <div class="home-row-between home-first-foot">
      {home_go(tabs, first["goto"], first["action"], "home-go home-go-lg")}
      <span class="home-next">다음 → {first["next"]}</span>
    </div>
  </div>
  {rest_html}
</div>"""


def home_status_html(stores, demo, temps, ad, tabs):
    """오른쪽: 지금 상황 (광고 성과, 날씨, 광고 빈도)"""
    report = stores.get("report") or {}
    is_demo = "report" in demo

    sales = report.get("yesterday_sales")
    big = f'€{sales:,.0f}{home_delta(report.get("sales_delta", 0))}' if sales is not None else "—"
    kpi = report.get("kpi") or {}
    kpis = "".join(
        f'<div class="home-kpi"><span class="home-sub">{name}</span><b>{val}</b>{delta}</div>'
        for name, val, delta in [
            ("클릭률", f'{kpi["ctr"]:.1f}%' if "ctr" in kpi else "—", home_delta(kpi["ctr_delta"], "%p") if "ctr_delta" in kpi else ""),
            ("전환율", f'{kpi["cvr"]:.1f}%' if "cvr" in kpi else "—", home_delta(kpi["cvr_delta"], "%p") if "cvr_delta" in kpi else ""),
            ("광고비", f'€{kpi["spend"]:,.0f}' if "spend" in kpi else "—", ""),
        ]
    )
    ab = report.get("ab_test") or {}
    a, b = ab.get("a") or {}, ab.get("b") or {}
    ab_html = ""
    if a and b:
        top = max(a.get("ctr", 0), b.get("ctr", 0)) or 1
        ab_html = '<div class="home-sub home-mt">A/B 테스트 클릭률</div>' + "".join(
            f'<div class="home-ab-row"><span>{v.get("label", k)}</span>'
            f'<div class="home-ab-bar"><span style="width:{v.get("ctr", 0) / top * 100:.0f}%;background:{color}"></span></div>'
            f'<b>{v.get("ctr", 0):.1f}%</b></div>'
            for k, v, color in [("A안", a, C["purple"]), ("B안", b, C["pink"])]
        )

    warns = [(p, *home_city_warning(p)) for p in temps]
    hot = sorted((w for w in warns if w[1]), key=lambda w: -w[2])
    if hot:
        cities = ", ".join(f"{p['city']} {peak:.0f}°" for p, _, peak in hot[:3])
        weather_line = f'<b class="home-hot">폭염경보 {sum(1 for w in hot if w[1] == "폭염경보")}곳</b> · {cities}'
    else:
        top = max(temps, key=lambda p: p["temp"])
        weather_line = f'경보 없음 · 최고 {top["city"]} {top["temp"]:.0f}°C'

    mult, reason, linked = ad
    return f"""
<div class="home-status">
  <div class="home-label">지금 상황</div>
  <div class="home-float home-stat">
    <div class="home-row-between"><span class="home-sub">최근 광고 성과 {home_demo_tag(is_demo)}</span><span class="home-sub">전날 매출</span></div>
    <div class="home-big">{big}</div>
    <div class="home-kpis">{kpis}</div>
    {ab_html}
  </div>
  <div class="home-float home-stat">
    <div class="home-sub">날씨 (7일 예보)</div>
    <div class="home-weather-line">{weather_line}</div>
  </div>
  <div class="home-float home-stat">
    <div class="home-row-between"><span class="home-sub">광고 빈도 추천 {home_demo_tag(linked and "weather" in demo)}</span>
    {home_go(tabs, "weather", "조정", "home-go home-go-sm")}</div>
    <div class="home-num">x{mult:.1f}</div>
    <div class="home-sub">{reason}</div>
  </div>
</div>"""


def home_cycle_html(stores, ad, tabs):
    """아래: 마케팅 사이클 (완료 ✓ / 지금 여기 / 대기) + ④ 광고 타이밍은 따로 계속 감시"""
    current = next((code for code in HOME_STEPS[:-1] if not stores.get(code)), None)
    steps = []
    for code in HOME_STEPS[:-1]:   # ①~③ (④는 사이클 밖에서 계속 감시)
        done = bool(stores.get(code))
        state = "done" if done else "now" if code == current else "wait"
        mark = "✓" if done else "지금 여기" if state == "now" else "대기"
        steps.append(f'<button type="button" class="home-step home-step-{state}" data-home-goto="{tabs[code][0]}">'
                     f'<span>{tabs[code][1]}</span><em>{mark}</em></button>')
    steps.append('<span class="home-step home-step-wait home-step-plain"><span>광고 집행 · A/B 테스트</span><em>대기</em></span>')
    arrow = '<span class="home-arrow">→</span>'
    mult = ad[0]
    return f"""
<div class="home-cycle">
  <span class="home-label home-cycle-label">마케팅 사이클</span>
  {arrow.join(steps)}{arrow}<span class="home-sub">다시 ①</span>
  <button type="button" class="home-watch" data-home-goto="{tabs["weather"][0]}"><i></i>{tabs["weather"][1]} · 계속 감시 중 · 광고 빈도 x{mult:.1f}</button>
</div>"""


def home_popup_html(todos, tabs):
    """접속 후 처음 한 번, 급한 할 일을 팝업으로 (누르면 해당 탭으로 이동, ×로 닫기)"""
    if st.session_state.get("home-popup-shown"):
        return ""
    st.session_state["home-popup-shown"] = True
    urgent = [t for t in todos if t["level"] == "high"][:2]
    return "".join(
        f'<div class="home-pop" style="animation-delay:{0.6 + i * 0.25:.2f}s">{home_todo_icon(t)}'
        f'<div><b>{t["title"]}</b>{home_go(tabs, t["goto"], t["action"])}</div>'
        f'<button type="button" class="home-pop-x" data-home-close="1" aria-label="닫기">×</button></div>'
        for i, t in enumerate(urgent)
    )


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
  {home_head_html(todos, tabs)}
  {home_todo_html(todos, tabs)}
  <div class="home-globe">
    <div class="home-globe-wrap">{home_globe_svg()}{home_city_layer(temps, home_city_warning)}</div>
    <div class="home-globe-cap">{source}{" · 일부 샘플 데이터" if demo else ""} · 도시에 마우스를 올려 보세요</div>
  </div>
  {home_status_html(stores, demo, temps, ad, tabs)}
  {home_cycle_html(stores, ad, tabs)}
  <div class="home-pops">{home_popup_html(todos, tabs)}</div>
</div>"""
    )
    components.html(HOME_NAV_JS, height=0)
