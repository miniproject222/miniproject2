# 홈: 날씨 + 각 탭 데이터 보고 → 팝업 알림
# 배치는 레퍼런스(General statistics 대시보드) 그대로: [좌측 현황 | 중앙 우주에서 본 독일 + 기온 | 우측 알림·추천·진행]
# 홈 탭이 열려 있으면 판이 왼쪽 아이콘 줄 오른쪽 화면 전체를 채웁니다 (home_style.css)
# 다른 탭이 구현 전이면 샘플 데이터로 채우고 "샘플" 표시 (데이터 모양은 home_data.py 맨 위 참고)
from datetime import date
from pathlib import Path

import streamlit as st

from modules.home.home_data import home_ad_multiplier, home_alerts, home_read_stores, home_step_status
from modules.home.home_globe import home_city_layer, home_get_temps, home_globe_svg, home_svg_img

HOME_DIR = Path(__file__).resolve().parent   # 내 폴더 (images/, data/ 경로 만들 때 사용)

# 레퍼런스와 같게 보이도록 쓰는 색 (홈 탭 안에서만 적용)
HOME_COLORS = {
    "board": "#F5F6FB", "card": "#FFFFFF", "text": "#2B2D4F", "sub": "#A3A5BD", "line": "#ECEDF4",
    "purple": "#7B6CF2", "pink": "#F2708F", "orange": "#F9A65A", "green": "#3CC58A", "blue": "#46A6F5",
    "up": "#2DB67C", "down": "#F2708F",
}
C = HOME_COLORS
HOME_SERIES = [C["orange"], C["pink"], C["purple"], C["blue"], C["green"]]


# ── 작은 HTML 조각 ───────────────────────────
def home_delta(ratio):
    up = ratio >= 0
    color = C["up"] if up else C["down"]
    return f'<span class="home-delta" style="color:{color}">{"▲" if up else "▼"} {abs(ratio) * 100:.0f}%</span>'


def home_demo_tag(is_demo):
    return '<span class="home-demo">샘플</span>' if is_demo else ""


def _home_smooth_path(values, w, h, top):
    pts = [(i * w / (len(values) - 1), h - v / top * h) for i, v in enumerate(values)]
    d = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        mx = (x0 + x1) / 2
        d += f" C{mx:.1f} {y0:.1f} {mx:.1f} {y1:.1f} {x1:.1f} {y1:.1f}"
    return d, pts[-1]


def home_trend_chart(values):
    """최근 7일 매출 곡선 (그려지는 애니메이션 + 마지막 날 점 깜빡임)"""
    w, h = 200, 56
    if not values or len(values) < 2:
        return home_svg_img(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" preserveAspectRatio="none">'
            f'<path d="M0 {h * 0.6} H{w}" stroke="{C["line"]}" stroke-width="2" stroke-dasharray="5 5"/></svg>',
            "home-chart home-chart-sm",
        )
    d, (lx, ly) = _home_smooth_path(values, w, h - 4, max(values) * 1.1)
    return home_svg_img(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" preserveAspectRatio="none">'
        f'<path d="{d} L{w} {h} L0 {h}Z" fill="{C["purple"]}" fill-opacity="0">'
        f'<animate attributeName="fill-opacity" from="0" to="0.1" begin="0.6s" dur="0.8s" fill="freeze"/></path>'
        f'<path d="{d}" fill="none" stroke="{C["purple"]}" stroke-width="2" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1">'
        f'<animate attributeName="stroke-dashoffset" from="1" to="0" dur="1.4s" fill="freeze"/></path>'
        f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="3" fill="{C["purple"]}">'
        f'<animate attributeName="r" values="3;5;3" dur="1.6s" repeatCount="indefinite"/></circle></svg>',
        "home-chart home-chart-sm",
    )


def home_donut(ratio):
    r, sw = 26, 5
    circ = 2 * 3.14159 * r
    return home_svg_img(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" font-family="Pretendard, Malgun Gothic, sans-serif">'
        f'<circle cx="32" cy="32" r="{r}" fill="none" stroke="{C["line"]}" stroke-width="{sw}"/>'
        f'<circle cx="32" cy="32" r="{r}" fill="none" stroke="{C["purple"]}" stroke-width="{sw}" '
        f'stroke-linecap="round" stroke-dasharray="0 {circ:.1f}" transform="rotate(-90 32 32)">'
        f'<animate attributeName="stroke-dasharray" from="0 {circ:.1f}" to="{circ * ratio:.1f} {circ:.1f}" dur="1.2s" fill="freeze"/></circle>'
        f'<text x="32" y="36.5" text-anchor="middle" font-size="13" fill="{C["text"]}">{ratio * 100:.0f}%</text></svg>',
        "home-donut",
    )


def home_icon(kind, bg):
    """알림 아이콘 (해 / 종)"""
    s = 'fill="none" stroke="#FFFFFF" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"'
    if kind == "sun":
        rays = "".join(f'<path d="M{11 + 7 * x:.1f} {11 + 7 * y:.1f} L{11 + 9 * x:.1f} {11 + 9 * y:.1f}" {s}/>'
                       for x, y in [(1, 0), (-1, 0), (0, 1), (0, -1), (0.7, 0.7), (-0.7, 0.7), (0.7, -0.7), (-0.7, -0.7)])
        shape = f'<circle cx="11" cy="11" r="4" {s}/>{rays}'
    else:
        shape = f'<path d="M6 15V10a5 5 0 0 1 10 0v5l1.5 2h-13z" {s}/><path d="M9.5 19a1.6 1.6 0 0 0 3 0" {s}/>'
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 22 22">{shape}</svg>'
    return f'<span class="home-icon" style="background:{bg}">{home_svg_img(svg, "home-icon-img")}</span>'


# ── 영역별 HTML ──────────────────────────────
def home_left_html(stores, demo, temps, steps):
    report = stores.get("report") or {}
    is_demo = "report" in demo

    # 전날 매출 (① 문제 분석)
    if report.get("yesterday_sales") is not None:
        sales = f'<div class="home-big">€{report["yesterday_sales"]:,.0f}{home_delta(report.get("sales_delta", 0))}</div>'
    else:
        sales = '<div class="home-big home-muted">—</div>'

    # 도시별 기온 (실시간, 높은 순 4곳)
    hot = sorted(temps, key=lambda p: -p["temp"])[:4]
    total = sum(max(p["temp"], 1) for p in hot)
    seg = "".join(f'<span style="flex:{max(p["temp"], 1) / total:.3f};background:{HOME_SERIES[i]}"></span>' for i, p in enumerate(hot))
    rows = "".join(
        f'<div class="home-act-row"><span><i class="home-dot" style="background:{HOME_SERIES[i]}"></i>{p["city"]}</span>'
        f'<span class="home-sub">내일 {p.get("tomorrow", p["temp"]):.0f}°</span><span>{p["temp"]:.0f}°C</span></div>'
        for i, p in enumerate(hot)
    )

    # 주요 문제 (누르면 내용 펼침)
    problems = report.get("problems") or []
    prob_rows = "".join(
        f'<details class="home-fold"><summary><b>{p.get("title", "")}</b><span class="home-tag">{p.get("type", "")}</span></summary>'
        f'<p>{p.get("detail", "")}</p></details>'
        for p in problems[:3]
    )

    # 최근 7일 매출
    sales_7d = report.get("sales_7d") or []
    trend_value = f'<b class="home-num-sm">€{sum(sales_7d):,.0f}</b>' if sales_7d else '<b class="home-num-sm home-muted">—</b>'

    done = sum(ok for _, ok in steps)
    return f"""
<div class="home-left">
  <div class="home-title">오늘의 현황</div>
  <div class="home-label">전날 매출 {home_demo_tag(is_demo)}<span class="home-link">① 문제 분석</span></div>
  {sales}
  <div class="home-label home-strong">도시별 기온 <span class="home-link">높은 순 · 실시간</span></div>
  <div class="home-seg">{seg}</div>
  {rows}
  <div class="home-bottom">
    <div class="home-float home-earn">
      <div class="home-label">주요 문제 {home_demo_tag(is_demo)}</div>
      <div class="home-num">{len(problems)}건</div>
      <div class="home-sub">눌러서 자세히 보기</div>
      {prob_rows}
    </div>
    <div class="home-stack">
      <div class="home-float">
        <div class="home-row-between"><div><div class="home-label">매출 추이 {home_demo_tag(is_demo)}</div>
        <div class="home-sub">최근 7일 합계</div></div>{trend_value}</div>
        {home_trend_chart(sales_7d)}
      </div>
      <div class="home-float home-cover">
        {home_donut(done / len(steps))}
        <div><div class="home-label">전체 진행률</div><div class="home-num-md">{done} / {len(steps)} 단계</div>
        <div class="home-sub">각 탭에 결과가 저장되면 올라갑니다</div></div>
      </div>
    </div>
  </div>
</div>"""


def home_right_html(alerts, ad, steps, demo):
    if alerts:
        alert_rows = "".join(
            f'<details class="home-fold home-alert"><summary>'
            f'{home_icon("sun" if a["text"].startswith("폭염") else "bell", C["orange"] if a["level"] == "high" else C["blue"])}'
            f'<div><div class="home-label">{a["text"]}</div><span class="home-sub">{a["step"]}</span></div></summary>'
            f'<p>{a["detail"]}</p></details>'
            for a in alerts[:3]
        )
    else:
        alert_rows = f'<div class="home-engage">{home_icon("bell", C["blue"])}<div><div class="home-label">새 알림 없음</div>' \
                     f'<span class="home-sub">폭염, 매출 하락, 광고 타이밍 알림이 여기에 표시됩니다</span></div></div>'

    mult, reason, linked = ad
    step_rows = "".join(
        f'<div class="home-row-between home-sub home-time-row"><span>{name}</span><span>{"완료" if ok else "대기"}</span></div>'
        f'<div class="home-track"><span style="width:{100 if ok else 0}%;background:{HOME_SERIES[i]}"></span></div>'
        for i, (name, ok) in enumerate(steps)
    )
    return f"""
<div class="home-side">
  <div class="home-label">알림 <span class="home-link">{len(alerts)}건 · 눌러서 자세히</span></div>
  {alert_rows}

  <div class="home-label home-gap">광고 빈도 추천 {home_demo_tag(linked and "weather" in demo)}</div>
  <div class="home-sub">오늘</div>
  <div class="home-num">x{mult:.1f}</div>
  <div class="home-sub">{reason}</div>
  <div class="home-sub home-gap-sm">{"⑤ 광고 타이밍 추천값" if linked else "임시 규칙 (⑤ 광고 타이밍 연결 전)"}</div>

  <div class="home-float home-time">
    <div class="home-label">단계별 진행</div>
    <div class="home-num">{sum(ok for _, ok in steps)}<span class="home-sub"> / {len(steps)} 완료</span></div>
    {step_rows}
  </div>
</div>"""


def home_popup(alerts):
    """중요 알림은 접속마다 한 번씩 팝업(토스트)으로 띄움"""
    shown = st.session_state.setdefault("home-alerts-shown", [])
    for a in alerts:
        if a["level"] == "high" and a["text"] not in shown:
            st.toast(f'{a["text"]} ({a["step"]})', icon="🔥" if a["text"].startswith("폭염") else "🔔")
            shown.append(a["text"])


def home_render():
    """'홈' 탭을 열 때마다 실행됩니다. 화면은 전부 이 함수 안에서 그립니다."""
    temps, live = home_get_temps()
    stores, demo = home_read_stores()
    steps = home_step_status(stores)
    alerts = home_alerts(stores, temps)
    home_popup(alerts)

    source = "실시간 기온 · Weather data by Open-Meteo.com" if live else "샘플 기온 (실시간 조회 실패)"
    demo_note = " · 일부 샘플 데이터" if demo else ""
    css_vars = ";".join(f"--home-{k}:{v}" for k, v in C.items())
    st.html(
        f"""
<div class="home-board" style="{css_vars}">
  {home_left_html(stores, demo, temps, steps)}
  <div class="home-globe">
    <div class="home-globe-cap">{date.today():%Y-%m-%d} · {source}{demo_note} · 도시에 마우스를 올려 보세요</div>
    <div class="home-globe-wrap">{home_globe_svg()}{home_city_layer(temps)}</div>
  </div>
  {home_right_html(alerts, home_ad_multiplier(stores, temps), steps, demo)}
</div>"""
    )
