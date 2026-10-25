# 4. 날씨 광고 타이밍 - PDF 보고서 (A4 1장, matplotlib만 사용)
import io
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib

matplotlib.use("Agg")
from matplotlib import font_manager, rc_context  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

import ui_theme as ui  # noqa: E402
from modules.weather.weather_data import (  # noqa: E402
    WEATHER_HOT_C,
    WEATHER_STOCK_LABEL,
    weather_checked_label,
    weather_eur,
    weather_short_date,
    weather_stock_checked,
)

WEATHER_FONT_DIR = Path(__file__).resolve().parents[2] / "common" / "fonts"
L, R = 0.07, 0.93          # 좌우 여백 (그림 비율)
W = R - L

C_TEXT = ui.THEME["text"]
C_MUTED = ui.THEME["muted"]
C_LINE = "#DCDBE8"          # 표 선: 보고서 인쇄용으로 조금 진하게
C_HEAD = "#ECEBF5"          # 표 머리 배경 (라벤더를 옅게)
C_HOT = "#FDE9DF"           # 30°C 이상 날 강조 (오렌지를 옅게)
C_BOX = ui.PALETTE["beige"]


def _weather_font():
    """SUIT 글꼴(한글) 등록 → 글꼴 이름."""
    name = "DejaVu Sans"
    for file in ("SUIT-Regular.otf", "SUIT-Bold.otf"):
        path = WEATHER_FONT_DIR / file
        if path.exists():
            font_manager.fontManager.addfont(str(path))
            name = font_manager.FontProperties(fname=str(path)).get_name()
    return name


def _weather_wrap(text, limit):
    """한글 1칸, 영문·숫자 0.55칸으로 세어 줄바꿈 (띄어쓰기 단위)."""
    lines, cur, width = [], "", 0.0
    for word in text.split(" "):
        ww = sum(1.0 if ord(c) > 0x2E80 else 0.55 for c in word) + 0.3
        if cur and width + ww > limit:
            lines.append(cur)
            cur, width = word, ww
        else:
            cur, width = (cur + " " + word if cur else word), width + ww
    if cur:
        lines.append(cur)
    return lines


class _WeatherSheet:
    """A4 한 장에 위에서 아래로 쌓기."""

    def __init__(self):
        self.fig = Figure(figsize=(8.27, 11.69))   # pyplot 없이: 다운로드 버튼 스레드에서도 안전
        self.y = 0.95

    def text(self, x, y, s, size=9, bold=False, color=C_TEXT, **kw):
        self.fig.text(x, y, s, fontsize=size, fontweight="bold" if bold else "normal", color=color, **kw)

    def rect(self, x, y, w, h, color, edge="none", round_=0.006):
        self.fig.add_artist(FancyBboxPatch(
            (x, y), w, h, boxstyle=f"round,pad=0,rounding_size={round_}",
            transform=self.fig.transFigure, facecolor=color, edgecolor=edge, lw=0.8,
        ))

    def hline(self, y, color=C_LINE, lw=0.8, x0=L, x1=R):
        self.fig.add_artist(Line2D([x0, x1], [y, y], color=color, lw=lw))

    def section(self, no, title):
        self.y -= 0.006
        self.text(L, self.y, f"{no}. {title}", 11.5, True, va="top")
        self.y -= 0.027

    def table(self, header, rows, widths, align=None, hot=None, bold_last=False, row_h=0.0195):
        """widths 합 = 1. align: 열별 'left'/'center'/'right'. hot: 강조할 (행, 열) 집합."""
        align = align or ["center"] * len(header)
        hot = hot or set()
        xs = [L]
        for w in widths:
            xs.append(xs[-1] + w * W)
        top = self.y
        self.fig.add_artist(Rectangle((L, top - row_h), W, row_h, transform=self.fig.transFigure,
                                      facecolor=C_HEAD, edgecolor="none"))
        for ri, row in enumerate([header] + rows):
            y_mid = top - row_h * (ri + 0.5)
            for ci, val in enumerate(row):
                if ri and (ri - 1, ci) in hot:
                    self.fig.add_artist(Rectangle((xs[ci], top - row_h * (ri + 1)), xs[ci + 1] - xs[ci], row_h,
                                                  transform=self.fig.transFigure, facecolor=C_HOT, edgecolor="none"))
                a = align[ci] if ri else "center"
                x = {"left": xs[ci] + 0.008, "right": xs[ci + 1] - 0.008}.get(a, (xs[ci] + xs[ci + 1]) / 2)
                bold = ri == 0 or (bold_last and ri == len(rows))
                self.text(x, y_mid, str(val), 8.3, bold, ha=a, va="center")
            self.hline(top - row_h * (ri + 1), C_TEXT if ri == 0 else C_LINE, 0.9 if ri == 0 else 0.6)
        self.hline(top, C_TEXT, 0.9)
        self.y = top - row_h * (len(rows) + 1) - 0.01

    def para(self, s, size=9, color=C_TEXT, indent=0.0, limit=62, gap=0.0165):
        for line in _weather_wrap(s, limit):
            self.text(L + indent, self.y, line, size, color=color, va="top")
            self.y -= gap


def _weather_recommendations(plan):
    """권고 사항 문장 (번호 목록)."""
    items = []
    for r in plan["hot_regions"][:3]:
        peak = max(r["days"], key=lambda d: d["tmax"])
        diff = f"균등 배분({weather_eur(plan['even'])})보다 {r['vs_even']}% 많은 금액입니다." if r["vs_even"] > 0 else ""
        items.append(
            f"{r['name']}({r['city']}) 메타 광고에 주간 {weather_eur(r['week'])}를 배정합니다. "
            f"7일 중 {len(r['hot_days'])}일이 {WEATHER_HOT_C}°C 이상이며, 최고 {peak['tmax']:.0f}°C"
            f"({weather_short_date(peak['date'])})로 예보되었습니다. {diff}"
        )
    if not plan["hot_regions"]:
        items.append(f"7일 동안 {WEATHER_HOT_C}°C 이상 예보된 권역이 없어, 메타 예산 {weather_eur(plan['meta'])}를 "
                     "기온에 따라 권역별로 고르게 운영합니다.")

    amazon = (f"아마존은 전국 단위로 {weather_eur(plan['amazon'])}(전체의 {plan['amazon_share'] * 100:.0f}%)를 집행합니다.")
    if plan["soldout"]:
        c = plan["soldout"][0]
        state = (f"{c['days']}일째 품절" if c.get("days")
                 else f"품절 상태({weather_checked_label(c['checked'])} Keepa 확인)" if c.get("checked") else "품절")
        amazon += (f" {c['competitor']} {c['product']}가 {state}이므로 해당 ASIN({c['asin']}) "
                   "타겟 광고를 함께 운영합니다.")
    elif plan["low"] and not plan["share_manual"]:
        c = plan["low"][0]
        amazon += f" {c['competitor']} {c['product']} 재고가 낮아 아마존 비중을 5%p 높였습니다."
    if plan["share_manual"]:
        amazon += (f" 채널 비중은 담당자가 직접 정했습니다"
                   f"(추천: 아마존 {plan['recommended_share'] * 100:.0f}%).")
    items.append(amazon)

    cool = [r for r in plan["regions"] if not r["hot_days"]]
    if plan["hot_regions"] and cool:
        items.append("·".join(r["name"] for r in cool) + f"는 7일 내내 {WEATHER_HOT_C}°C 미만으로 예보되어 기본 금액"
                     f"(권역별 {weather_eur(min(r['week'] for r in cool))} 안팎)으로 운영합니다.")
    return items


def weather_make_pdf(plan, is_sample_weather, is_sample_stock):
    """보고서 PDF(A4 1장)를 bytes로 돌려줍니다."""
    with rc_context({"font.family": [_weather_font(), "DejaVu Sans"], "axes.unicode_minus": False}):
        sheet = _weather_draw(plan, is_sample_weather, is_sample_stock)
        buf = io.BytesIO()
        with PdfPages(buf) as pdf:
            pdf.savefig(sheet.fig)
        return buf.getvalue()


def _weather_draw(plan, is_sample_weather, is_sample_stock):
    s = _WeatherSheet()
    now = datetime.now(ZoneInfo("Europe/Berlin"))
    dates = plan["dates"]
    period = f"{weather_short_date(dates[0])} ~ {weather_short_date(dates[-1])}" if dates else "-"
    regions = plan["regions"]

    # ── 머리글
    s.fig.add_artist(Rectangle((0, 0.985), 1, 0.015, transform=s.fig.transFigure,
                               facecolor=ui.THEME["primary"], edgecolor="none"))
    s.text(L, s.y, "주간 광고 예산 집행 권고서", 19, True, va="top")
    s.text(R, s.y - 0.004, f"문서 번호 WT-{now:%Y%m%d}", 8.5, color=C_MUTED, ha="right", va="top")
    s.y -= 0.045
    info = [
        ("작성일", f"{now:%Y-%m-%d}"),
        ("집행 기간", period),
        ("대상", "독일 4개 권역 · 메타, 아마존"),
        ("날씨 기준", "샘플 시나리오" if is_sample_weather else f"{regions[0]['updated'].replace('T', ' ')}"),
    ]
    cw = W / len(info)
    s.rect(L, s.y - 0.042, W, 0.042, C_BOX)
    for i, (k, v) in enumerate(info):
        x = L + cw * i + 0.015
        s.text(x, s.y - 0.012, k, 7.5, color=C_MUTED, va="top")
        s.text(x, s.y - 0.025, v, 9, True, va="top")
    s.y -= 0.06

    # ── 핵심 수치 4칸
    kpis = [
        ("주간 총예산", weather_eur(plan["budget"]), "7일 합계"),
        ("메타 · 지역 타겟", weather_eur(plan["meta"]), f"전체의 {(1 - plan['amazon_share']) * 100:.0f}%"),
        ("아마존 · 전국", weather_eur(plan["amazon"]), f"전체의 {plan['amazon_share'] * 100:.0f}%"),
        (f"{WEATHER_HOT_C}°C 이상 권역 배정", weather_eur(plan["hot_total"]),
         f"메타의 {plan['hot_total'] / plan['meta'] * 100:.0f}%" if plan["meta"] else "-"),
    ]
    gap = 0.012
    kw = (W - gap * 3) / 4
    for i, (k, v, sub) in enumerate(kpis):
        x = L + (kw + gap) * i
        s.rect(x, s.y - 0.064, kw, 0.064, "white", edge=C_LINE, round_=0.008)
        s.text(x + 0.014, s.y - 0.012, k, 8, color=C_MUTED, va="top")
        s.text(x + 0.014, s.y - 0.028, v, 15, True, va="top",
               color=ui.PALETTE["orange"] if i == 3 and plan["hot_total"] else C_TEXT)
        s.text(x + 0.014, s.y - 0.051, sub, 7.5, color=C_MUTED, va="top")
    s.y -= 0.074

    # ── 1. 권고 사항
    s.section(1, "권고 사항")
    for i, item in enumerate(_weather_recommendations(plan), 1):
        s.text(L, s.y, f"{i})", 9, True, va="top")
        s.para(item, indent=0.025)
        s.y -= 0.002

    # ── 2. 권역별 예산 배분
    s.section(2, "권역별 메타 예산 배분")
    rows = [[r["name"], f"{r['city']} 외 {len(r.get('cities', [])) - 1}" if len(r.get("cities", [])) > 1 else r["city"], f"{r['now']:.0f}°C", f"{r['max7']:.0f}°C", f"{len(r['hot_days'])}일",
             weather_eur(r["week"]), (f"+{r['vs_even']}%" if r["vs_even"] > 0 else f"{r['vs_even']}%")]
            for r in sorted(regions, key=lambda r: -r["week"])]
    rows.append(["합계", "", "", "", "", weather_eur(sum(r["week"] for r in regions)), ""])
    hot = {(i, 4) for i, r in enumerate(sorted(regions, key=lambda r: -r["week"])) if r["hot_days"]}
    s.table(["권역", "도시", "현재 기온", "7일 최고", f"{WEATHER_HOT_C}°C 이상", "주간 배정액", "균등 대비"],
            rows, [0.1, 0.16, 0.13, 0.13, 0.14, 0.18, 0.16],
            ["center", "left", "right", "right", "center", "right", "right"], hot, bold_last=True)

    # ── 3. 일별 집행 계획
    s.section(3, "일별 집행 계획")
    head = ["구분"] + [weather_short_date(d) for d in dates] + ["합계"]
    plan_rows, hot_cells = [], set()
    for ri, r in enumerate(plan["hot_regions"]):
        plan_rows.append([f"메타 {r['name']}"] + [weather_eur(v) for v in r["daily"]] + [weather_eur(r["week"])])
        hot_cells |= {(ri, ci + 1) for ci, d in enumerate(r["days"]) if d["tmax"] >= WEATHER_HOT_C}
    plan_rows.append(["아마존 전국"] + [weather_eur(v) for v in plan["amazon_daily"]] + [weather_eur(plan["amazon"])])
    n = len(dates)
    s.table(head, plan_rows, [0.15] + [0.7 / n] * n + [0.15], ["left"] + ["right"] * (n + 1), hot_cells)
    s.y += 0.004
    note = (f"색칠한 칸은 최고기온 {WEATHER_HOT_C}°C 이상 예보일입니다. "
            if hot_cells else f"{WEATHER_HOT_C}°C 이상 권역이 없어 메타 권역별 일정은 생략했습니다. ")
    s.para(note + "나머지 권역은 2번 표의 주간 배정액을 7일에 나누어 집행합니다.", 7.5, C_MUTED, limit=90, gap=0.014)
    s.y -= 0.004

    # ── 4. 경쟁사 재고 현황
    s.section(4, "경쟁사 재고 현황" + (" (샘플 데이터)" if is_sample_stock else ""))
    action = {"soldout": "ASIN 타겟 광고 운영", "low": "-" if plan["share_manual"] else "아마존 비중 +5%p",
              "normal": "-"}
    s.table(["경쟁사", "상품", "ASIN", "상태", "지속" if is_sample_stock else "확인 시점", "대응"],
            [[c["competitor"], c["product"], c["asin"], WEATHER_STOCK_LABEL.get(c["status"], c["status"]),
              f"{c['days']}일" if c.get("days") else weather_checked_label(c["checked"]) if c.get("checked") else "-",
              action.get(c["status"], "-")] for c in plan["competitors"]],
            [0.13, 0.17, 0.18, 0.13, 0.1, 0.29], ["center", "left", "center", "center", "center", "left"])

    # ── 5. 산정 기준
    s.section(5, "산정 기준")
    for line in (
        ("채널 비중: 담당자 직접 설정 (메타 {:.0f}%, 아마존 {:.0f}%). 추천 기준은 아마존 기본 40%, "
         "경쟁사 재고 낮음 45%, 품절 50%입니다.").format((1 - plan["amazon_share"]) * 100, plan["amazon_share"] * 100)
        if plan["share_manual"] else
        "채널 비중: 아마존 기본 40%, 경쟁사 재고 낮음 45%, 품절 50%. 나머지는 메타입니다.",
        f"메타 배분: 60%는 4개 권역·7일에 똑같이 나누고, 40%는 {WEATHER_HOT_C}°C 이상 예보일에만 "
        "(최고기온 - 29)점에 비례해 추가로 나눕니다. 예) 30°C = 1점, 35°C = 6점.",
        "권역 기온: 권역별 3개 도시 평균 (북부 Hamburg·Bremen·Kiel, 서부 Köln·Düsseldorf·Dortmund, "
        "동부 Berlin·Leipzig·Dresden, 남부 München·Stuttgart·Nürnberg)",
        "아마존 배분: 전국 단위로, 날짜별 가중치 1 + 0.1 × (그날 4개 권역 점수 합)에 비례해 나눕니다.",
    ):
        s.para("· " + line, 7.8, C_MUTED, limit=92, gap=0.0145)

    # ── 바닥글
    s.hline(0.045, C_LINE)
    src = "날씨: 폭염 시나리오 샘플 (실제 예보 아님)" if is_sample_weather else "날씨: Open-Meteo.com 예보"
    src += " · 경쟁사 재고: " + ("샘플 데이터" if is_sample_stock
                                 else f"경쟁사 DB + Keepa ({weather_stock_checked(plan['competitors'])} 조회)")
    s.text(L, 0.03, src, 7.5, color=C_MUTED)
    s.text(R, 0.03, f"출력 {now:%Y-%m-%d %H:%M} (독일 시간)", 7.5, color=C_MUTED, ha="right")
    return s


def weather_temp_color(tmax):
    """화면 그래프 막대 색: 30°C 미만 라벤더, 이상은 피치 → 오렌지."""
    if tmax >= 34:
        return ui.PALETTE["orange"]
    if tmax >= 32:
        return "#F58A5C"
    if tmax >= WEATHER_HOT_C:
        return "#F8B37E"
    return ui.PALETTE["lavender"]
