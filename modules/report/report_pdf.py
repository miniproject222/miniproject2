# 1. 분석 리포트 - PDF 양식 3가지 (실제 데이터만)
# 화면 내용(결과 요약 KPI, 문제 도출, 내부/외부 요인, 경쟁사 비교, GA4·A/B가 있으면 그 값)을 그대로 옮기고 양식만 다르게 만듭니다.
# 팀에서 양식을 하나로 정하기 전까지 화면에서 골라 내려받을 수 있게 둡니다.
from datetime import date
from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace

import ui_theme as ui

REPORT_FONT_DIR = Path(__file__).resolve().parents[2] / "common" / "fonts"   # 공통 폰트 (읽기만)
REPORT_COMPANY = "SEORI(서리)"
REPORT_SOURCES = "출처: 경쟁사 DB·독일 DB(2026-10-23), Keepa(Amazon.de), Open-Meteo"

REPORT_PDF_STYLES = {
    "formal": "① 기안 보고서형 (결재란 + 개조식)",
    "executive": "② 경영진 보고형 (Executive Summary)",
    "onepage": "③ 원페이지 대시보드형",
}


def report_rgb(hex_color):
    """ui_theme의 색('#RRGGBB')을 PDF용 (R, G, B)로 바꿉니다."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


REPORT_PDF_COLORS = {name: report_rgb(ui.THEME[key]) for name, key in {
    "text": "text", "muted": "muted", "line": "line", "soft": "primary_soft", "primary": "primary",
    "accent": "accent", "card": "card", "bg": "bg",
    "up_bg": "up_bg", "up_text": "up_text", "down_bg": "down_bg", "down_text": "down_text",
}.items()}
REPORT_LEVEL_DOTS = {"높음": "●●●", "중간": "●●○", "낮음": "●○○"}


REPORT_PDF_UMLAUT = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss"})


def report_short(text, limit):
    return text if len(text) <= limit else text[:limit - 1] + "…"


class ReportPdf(FPDF):
    """공통 폰트, 색, 쪽 번호 꼬리말을 가진 PDF."""

    def __init__(self, orientation, footer_text, margin=15):
        super().__init__(orientation=orientation, format="A4")
        self.footer_text = footer_text
        self.add_font("SUIT", "", str(REPORT_FONT_DIR / "SUIT-Regular.otf"))
        self.add_font("SUIT", "B", str(REPORT_FONT_DIR / "SUIT-Bold.otf"))
        self.set_margins(margin, margin, margin)
        self.set_auto_page_break(auto=True, margin=margin)

    def normalize_text(self, text):
        # SUIT 글꼴에 독일어 움라우트가 없어 PDF에서는 ue·oe·ae·ss로 바꿔 씁니다 (예: kühlmatte → kuehlmatte)
        return super().normalize_text(text.translate(REPORT_PDF_UMLAUT))

    def footer(self):
        self.set_y(-11)
        self.font(7, color="muted")
        self.cell(0, 4, self.footer_text)
        self.set_x(self.l_margin)
        self.cell(0, 4, f"{self.page_no()} / {{nb}}", align="R")

    # 작은 도우미
    def font(self, size, bold=False, color="text"):
        self.set_font("SUIT", "B" if bold else "", size)
        self.set_text_color(*REPORT_PDF_COLORS[color])

    def fill(self, color):
        self.set_fill_color(*REPORT_PDF_COLORS[color])

    def draw(self, color, width=0.2):
        self.set_draw_color(*REPORT_PDF_COLORS[color])
        self.set_line_width(width)

    def text_at(self, x, y, w, text, size=9, bold=False, color="text", line_h=None, align="L"):
        """(x, y)에서 폭 w 안에 글을 쓰고, 끝난 y를 돌려줍니다."""
        self.set_xy(x, y)
        self.font(size, bold, color)
        self.multi_cell(w, line_h or size * 0.5, text, align=align, new_x="LMARGIN", new_y="NEXT")
        return self.get_y()

    def ensure_space(self, y, need):
        """남은 공간이 need(mm)보다 작으면 새 쪽으로 넘기고 새 y를 돌려줍니다."""
        if self.auto_page_break and y + need > self.page_break_trigger:
            self.add_page()
            return self.t_margin
        return y

    def table_at(self, x, w, rows, widths, size=8, padding=1.2):
        """x 위치에 폭 w 표를 그립니다. 첫 줄은 제목 줄입니다."""
        old = self.l_margin
        self.set_left_margin(x)
        self.set_x(x)
        self.font(size)
        self.draw("soft")
        self.fill("card")   # 앞에서 쓴 채우기 색(배지, 막대)이 표 칸에 남지 않게
        head = FontFace(emphasis="BOLD", fill_color=REPORT_PDF_COLORS["bg"], color=REPORT_PDF_COLORS["text"])
        with self.table(width=w, col_widths=widths, align="LEFT", headings_style=head, line_height=size * 0.62,
                        padding=padding, borders_layout="HORIZONTAL_LINES", cell_fill_mode="NONE") as t:
            for row in rows:
                r = t.row()
                for value in row:
                    r.cell(str(value))
        self.set_left_margin(old)
        return self.get_y()

    def badge(self, x, y, label, style="primary", size=7):
        """둥근 배지. style: primary(진한 채움) / outline / soft / up / down. 배지 폭을 돌려줍니다."""
        self.font(size, bold=True)
        w = self.get_string_width(label) + 3
        h = size * 0.55
        if style in ("primary", "up", "down"):
            self.fill({"primary": "primary", "up": "up_bg", "down": "down_bg"}[style])
            self.rect(x, y, w, h, style="F", round_corners=True, corner_radius=h / 2)
            self.font(size, bold=True, color={"primary": "card", "up": "up_text", "down": "down_text"}[style])
        else:
            self.draw("primary" if style == "outline" else "soft")
            self.rect(x, y, w, h, style="D", round_corners=True, corner_radius=h / 2)
            self.font(size, bold=True, color="primary" if style == "outline" else "muted")
        self.set_xy(x, y)
        self.cell(w, h, label, align="C")
        return w

    def level_badge(self, x, y, level, size=7):
        style = {"높음": "primary", "중간": "outline", "낮음": "soft"}[level]
        return self.badge(x, y, f"{REPORT_LEVEL_DOTS[level]} {level}", style, size)

    def factor_list(self, x, y, w, items, size=8, detail_limit=None, gap=2):
        """요인 목록: 배지 + [분류] 제목 + 근거. 끝난 y를 돌려줍니다."""
        for item in items:
            y = self.ensure_space(y, size * 1.6)
            bw = self.level_badge(x, y, item["level"], size=size - 1)
            self.text_at(x + bw + 2, y - 0.2, w - bw - 2, f"[{item['group']}] {item['title']}", size=size, bold=True)
            detail = report_short(item["detail"], detail_limit) if detail_limit else item["detail"]
            y = self.text_at(x, y + size * 0.55 + 0.8, w, detail, size=size - 1, color="muted") + gap
        return y

    def problem_list(self, x, y, w, problems, size=9, detail_limit=None):
        """문제 도출 Top N: 순위 배지 + 제목 + 근거 + 가설 탭 질문."""
        for p in problems:
            y = self.ensure_space(y, size * 2.4)
            bw = self.badge(x, y, f"{p['rank']}순위 · {p['type']}", "primary" if p["level"] == "높음" else "outline", size - 1)
            self.text_at(x + bw + 2, y - 0.2, w - bw - 2, p["title"], size=size, bold=True)
            detail = report_short(p["detail"], detail_limit) if detail_limit else p["detail"]
            y = self.text_at(x, y + size * 0.55 + 0.8, w, f"근거: {detail}", size=size - 1.5, color="muted")
            y = self.text_at(x, y + 0.5, w, f"→ 가설 질문: {p['question']}", size=size - 1, bold=True, color="primary") + 2.5
        return y

    def kpi_tile(self, x, y, w, h, k, value_size=16):
        self.fill("bg")
        self.rect(x, y, w, h, style="F", round_corners=True, corner_radius=2.5)
        self.text_at(x + 4, y + 3, w - 8, k["label"], size=8, color="muted", line_h=4)
        self.text_at(x + 4, y + 8, w - 8, k["value"], size=value_size, bold=True, line_h=value_size * 0.5)
        if k["badge"]:
            self.badge(x + 4, y + h - 6.5, k["badge"], "up" if k["good"] else "down", 7)

    def competitor_table(self, x, w, c, size=7.5, compact=False, padding=1.2):
        if compact:
            head = ("브랜드", "Amazon 현재가", "90일", "평점", "리뷰", "㎡당")
            widths = (3.2, 1.8, 1.1, 1, 1, 1.2)
        else:
            head = ("구분", "브랜드", "DB 판매가", "Amazon 현재가", "90일 평균 대비", "평점", "리뷰 수", "㎡당 가격", "경쟁우위")
            widths = (2.2, 3.4, 1.7, 1.8, 1.6, 1, 1.2, 1.5, 1.4)
        rows = [head]
        # 원페이지(compact)는 공간이 좁아 Keepa 값이 있는 경쟁사와 서리만
        brands = [r for r in c["competitors"] if not compact or r.get("keepa") or r["kind"] == "자사"]
        for r in brands:
            k = r.get("keepa") or {}
            sign = "€" if r["currency"] == "EUR" else r["currency"] + " "
            vals = {
                "kind": report_short(r["kind"], 12), "brand": report_short(r["brand"], 22),
                "db": f"{sign}{r['db_price']:.2f}" if r["db_price"] else "-",
                "amazon": f"€{k['price']:.2f}" if k.get("price") else ("품절" if k else "-"),
                "change": f"{k['change'] * 100:+.0f}%" if k.get("change") is not None else "-",
                "rating": f"{k['rating']:.1f}" if k.get("rating") else "-",
                "reviews": f"{k['reviews']:,}" if k.get("reviews") is not None else "-",
                "sqm": (f"€{r['keepa_sqm']:.1f}" if r.get("keepa_sqm") else f"{sign}{r['sqm_price']:.1f}" if r["sqm_price"] else "-"),
                "score": f"{r['score']:.2f}" if r["score"] else "-",
            }
            keys = (("brand", "amazon", "change", "rating", "reviews", "sqm") if compact
                    else ("kind", "brand", "db", "amazon", "change", "rating", "reviews", "sqm", "score"))
            rows.append(tuple(vals[k] for k in keys))
        return self.table_at(x, w, rows, widths, size=size, padding=padding)

    def criteria_table(self, x, w, c, size=7.5):
        rows = [("경쟁우위 항목", "가중치", "서리 (목표)", "경쟁사 최고", "차이")]
        rows += [(ct["item"], f"{ct['weight']:.0%}", f"{ct['seori']:.0f}" if ct["seori"] is not None else "-",
                  f"{ct['best_brand']} {ct['best']:.0f}", f"{ct['seori'] - ct['best']:+.0f}" if ct["seori"] is not None else "-")
                 for ct in c["criteria"]]
        return self.table_at(x, w, rows, (4, 1.2, 1.4, 2.2, 1), size=size)

    def ga4_section(self, x, y, w, c, size=8):
        """GA4가 연결된 경우에만: 퍼널 단계별 전환율 + 유입 채널 표."""
        if not c["ga4"]:
            return y
        y = self.ensure_space(y, 40)
        y = self.text_at(x, y, w, "GA4 (최근 30일): 구매 퍼널", size=size + 1, bold=True, line_h=6)
        self.set_y(y)
        y = self.table_at(x, w, [("단계", "이번 기간", "이전 기간", "차이")]
                          + [(s["name"], f"{s['now']:.1f}%", f"{s['prev']:.1f}%", f"{s['diff']:+.1f}%p") for s in c["steps"]],
                          (4, 2, 2, 2), size=size) + 2
        if c["utm_rows"]:
            y = self.text_at(x, y, w, "GA4: 유입 채널 (UTM)", size=size + 1, bold=True, line_h=6)
            self.set_y(y)
            y = self.table_at(x, w, [("채널", "방문", "주문", "매출", "전환율", "비중")]
                              + [(r["channel"], f"{r['sessions']:,}", f"{r['orders']:,}", f"€{r['revenue']:,}",
                                  f"{r['cvr']:.2f}%", f"{r['share']:.0f}%") for r in c["utm_rows"]],
                              (3.5, 1.4, 1.2, 1.4, 1.2, 1), size=size) + 2
        return y

    def ab_section(self, x, y, w, c, size=8):
        """실제 A/B 결과가 있을 때만."""
        if not c["ab_tests"]:
            return y
        y = self.ensure_space(y, 25)
        y = self.text_at(x, y, w, "해결안 A/B 테스트", size=size + 1, bold=True, line_h=6)
        rows = [("테스트", "A안", "B안", "차이", "유의확률(p)", "판정")]
        for t in c["ab_tests"]:
            r = t["result"]
            rows.append((t["name"], f"{r['rate_a']:.1f}%", f"{r['rate_b']:.1f}%", f"{r['lift']:+.1f}%", f"{r['p']:.4f}",
                         "유의함" if r["significant"] else "유의하지 않음"))
        self.set_y(y)
        return self.table_at(x, w, rows, (3.5, 1.2, 1.2, 1.2, 1.5, 1.6), size=size) + 2


# ─────────────────────────────────────────────
# 양식 ① 기안 보고서형: 국내 기업 내부 보고서 (결재란, 표제 이중선, □ ○ - 개조식)
# ─────────────────────────────────────────────
def report_pdf_formal(c):
    pdf = ReportPdf("P", f"{REPORT_COMPANY}  ·  문제 분석 보고서  ·  대외비  ·  {REPORT_SOURCES}")
    pdf.add_page()
    W, L = pdf.epw, pdf.l_margin

    # 결재란 (오른쪽 위)
    sign_w, x0 = 20, L + W - 60
    pdf.draw("text", 0.3)
    pdf.font(8, bold=True)
    for i, role in enumerate(("담당", "팀장", "본부장")):
        pdf.set_xy(x0 + i * sign_w, 15)
        pdf.cell(sign_w, 6, role, border=1, align="C")
        pdf.set_xy(x0 + i * sign_w, 21)
        pdf.cell(sign_w, 14, "", border=1)
    pdf.text_at(L, 16, 80, REPORT_COMPANY, size=10, bold=True)
    pdf.text_at(L, 22, 80, "대외비", size=8, color="muted")

    # 표제 (이중선)
    for yy, wd in ((42, 0.6), (43.2, 0.2), (64, 0.2), (65.2, 0.6)):
        pdf.draw("text", wd)
        pdf.line(L, yy, L + W, yy)
    pdf.text_at(L, 47, W, "문제 분석 보고서", size=18, bold=True, align="C", line_h=9)
    pdf.text_at(L, 57, W, f"({c['period']} · 결과 데이터 요약 및 내/외부 요인 분석, 문제 도출)", size=9, color="muted", align="C")
    pdf.text_at(L, 67, W, f"보고일자  {c['today']}      작성  ____________", size=8, color="muted", align="R")

    def head(title):
        pdf.ln(3)
        return pdf.text_at(L, pdf.ensure_space(pdf.get_y(), 20), W, f"□ {title}", size=11.5, bold=True, line_h=7)

    def sub(title, y):
        return pdf.text_at(L + 3, pdf.ensure_space(y, 15), W - 3, f"○ {title}", size=10, bold=True, line_h=6)

    pdf.set_y(74)
    y = head("핵심 요약")
    pdf.draw("text", 0.3)
    pdf.set_xy(L, y + 1)
    pdf.font(9.5)
    pdf.multi_cell(W, 6, c["summary"], border=1, padding=3, new_x="LMARGIN", new_y="NEXT")

    head("결과 데이터 요약")
    pdf.table_at(L, W, [("지표", "값", "비교")] + [(k["label"], k["value"], k["badge"] or "-") for k in c["kpis"]],
                 (2.5, 2, 3.5), size=9)

    y = head("문제 도출 (핵심 문제)")
    y = pdf.problem_list(L + 3, y + 1, W - 3, c["key_problems"])

    pdf.set_y(y)
    y = head("문제 요인 분석")
    y = sub("내부 요인: 서리가 경쟁사 대비 부족한 점", y + 1)
    y = pdf.factor_list(L + 6, y + 1, W - 6, c["internal"])
    y = sub("외부 요인 - 위협", y + 1)
    y = pdf.factor_list(L + 6, y + 1, W - 6, c["threats"])
    y = sub("외부 요인 - 기회", y + 1)
    y = pdf.factor_list(L + 6, y + 1, W - 6, c["opportunities"])

    pdf.set_y(y)
    head("경쟁사 비교")
    pdf.text_at(L, pdf.get_y(), W, c["keepa_status"], size=7.5, color="muted")
    pdf.competitor_table(L, W, c, size=7)
    pdf.ln(2)
    pdf.criteria_table(L, W, c, size=7.5)
    y = pdf.ga4_section(L, pdf.get_y() + 3, W, c)
    y = pdf.ab_section(L, y, W, c)
    pdf.text_at(L, pdf.ensure_space(y + 2, 8), W, f"※ {REPORT_SOURCES}. 서리 경쟁우위 점수는 목표치입니다.", size=8, color="muted")
    return pdf


# ─────────────────────────────────────────────
# 양식 ② 경영진 보고형: 결론 먼저 (가로, 쪽마다 한 줄 결론 제목 + 근거, 출처 표기)
# ─────────────────────────────────────────────
def report_pdf_executive(c):
    pdf = ReportPdf("L", f"{REPORT_SOURCES}  ·  대외비")
    W, L = pdf.epw, pdf.l_margin

    def page(section, title):
        pdf.add_page()
        pdf.text_at(L, 10, W / 2, f"{REPORT_COMPANY}  |  문제 분석 리포트 {c['period']}", size=7.5, color="muted")
        pdf.text_at(L + W / 2, 10, W / 2, section, size=7.5, bold=True, color="primary", align="R")
        y = pdf.text_at(L, 17, W, title, size=15, bold=True, line_h=7.5)
        pdf.draw("primary", 0.8)
        pdf.line(L, y + 2, L + 40, y + 2)
        pdf.draw("line", 0.3)
        pdf.line(L + 40, y + 2, L + W, y + 2)
        return y + 7

    # 1쪽: 요약 (KPI + 핵심 문제)
    y = page("EXECUTIVE SUMMARY", c["summary"])
    tile_w, tile_h = 60, 30
    for i, k in enumerate(c["kpis"]):
        pdf.kpi_tile(L + (i % 2) * (tile_w + 5), y + (i // 2) * (tile_h + 5), tile_w, tile_h, k)
    fx, fw = L + 2 * tile_w + 15, W - 2 * tile_w - 15
    pdf.text_at(fx, y, fw, "핵심 문제 Top 3", size=10, bold=True, color="primary")
    pdf.problem_list(fx, y + 8, fw, c["key_problems"], size=9, detail_limit=110)

    # 2쪽: 내부 요인
    top = c["internal"][0]["title"] if c["internal"] else "내부 요인"
    y = page("내부 요인", f"내부: {top} 등 {len(c['internal'])}가지가 경쟁사 대비 부족합니다")
    pdf.factor_list(L, y + 2, W, c["internal"], size=9)

    # 3쪽: 외부 요인 (위협 | 기회)
    top = c["threats"][0]["title"] if c["threats"] else "외부 요인"
    y = page("외부 요인", f"외부: 위협 {len(c['threats'])}건 (1순위 {top}), 기회 {len(c['opportunities'])}건")
    half = (W - 10) / 2
    pdf.text_at(L, y + 2, half, "위협", size=10, bold=True, color="primary")
    pdf.factor_list(L, y + 10, half, c["threats"], size=8.5)
    pdf.text_at(L + half + 10, y + 2, half, "기회", size=10, bold=True, color="primary")
    pdf.factor_list(L + half + 10, y + 10, half, c["opportunities"], size=8.5)

    # 4쪽: 경쟁사 비교
    y = page("경쟁사 비교", "경쟁사 비교: 경쟁사 DB + Keepa(Amazon.de)")
    y = pdf.text_at(L, y, W, c["keepa_status"], size=7.5, color="muted")
    pdf.set_y(y + 1)
    pdf.competitor_table(L, W, c, size=7.5)
    pdf.ln(3)
    pdf.criteria_table(L, W * 0.7, c, size=7.5)

    # GA4·A/B가 있으면 5쪽
    if c["ga4"] or c["ab_tests"]:
        y = page("GA4 · A/B", "실측 데이터: GA4와 A/B 테스트")
        y = pdf.ga4_section(L, y + 2, W, c)
        pdf.ab_section(L, y, W, c)
    return pdf


# ─────────────────────────────────────────────
# 양식 ③ 원페이지 대시보드형: 화면 배치 그대로 한 장 (가로, 상단 색 띠 + KPI + 2단 + 하단)
# ─────────────────────────────────────────────
def report_pdf_onepage(c):
    pdf = ReportPdf("L", f"{REPORT_COMPANY}  ·  {REPORT_SOURCES}  ·  생성일 {c['today']}", margin=10)
    pdf.set_auto_page_break(False)
    pdf.add_page()
    W, L = pdf.epw, pdf.l_margin

    def box(x, y, w, h, title):
        pdf.draw("soft", 0.3)
        pdf.rect(x, y, w, h, style="D", round_corners=True, corner_radius=2.5)
        pdf.text_at(x + 4, y + 3, w - 8, title, size=9.5, bold=True, line_h=5)
        return y + 10

    # 상단 색 띠
    pdf.fill("primary")
    pdf.rect(L, 8, W, 13, style="F", round_corners=True, corner_radius=2.5)
    pdf.text_at(L + 5, 11, 180, f"{REPORT_COMPANY} 문제 분석 리포트  ·  {c['period']}", size=12, bold=True, color="card", line_h=7)
    pdf.text_at(L + W - 95, 12.5, 90, "결과 요약 · 내/외부 요인 · 문제 도출", size=7.5, color="soft", align="R")

    # KPI 한 줄
    kw = (W - 3 * 4) / 4
    for i, k in enumerate(c["kpis"]):
        x = L + i * (kw + 4)
        pdf.fill("bg")
        pdf.rect(x, 24, kw, 12, style="F", round_corners=True, corner_radius=2.5)
        pdf.text_at(x + 4, 25.5, kw - 8, k["label"], size=7, color="muted", line_h=3.5)
        pdf.text_at(x + 4, 29.5, 30, k["value"], size=11, bold=True, line_h=5.5)
        if k["badge"]:
            pdf.font(6.5, bold=True)
            bw = pdf.get_string_width(k["badge"]) + 3
            pdf.badge(x + kw - 4 - bw, 30.5, k["badge"], "up" if k["good"] else "down", 6.5)

    # 내부 | 외부
    cw, top, ch = (W - 4) / 2, 39, 105
    y = box(L, top, cw, ch, "내부 요인 · 서리가 경쟁사 대비 부족한 점")
    pdf.factor_list(L + 4, y, cw - 8, c["internal"], size=7, detail_limit=95)
    ex = L + cw + 4
    y = box(ex, top, cw, ch, "외부 요인 · 위협 / 기회")
    pdf.text_at(ex + 4, y - 1, cw - 8, "위협", size=7.5, bold=True, color="primary", line_h=4)
    y = pdf.factor_list(ex + 4, y + 4, cw - 8, c["threats"], size=6.5, detail_limit=70, gap=1.2)
    pdf.text_at(ex + 4, y, cw - 8, "기회", size=7.5, bold=True, color="primary", line_h=4)
    pdf.factor_list(ex + 4, y + 5, cw - 8, c["opportunities"], size=6.5, detail_limit=70, gap=1.2)

    # 하단: 경쟁사 비교 | 문제 도출
    bt, bh = top + ch + 3, 46
    sw = W * 0.55
    y = box(L, bt, sw, bh, "경쟁사 비교 (Keepa · 경쟁사 DB)")
    pdf.set_y(y - 1)
    pdf.competitor_table(L + 4, sw - 8, c, size=6, compact=True, padding=0.6)
    px = L + sw + 4
    pdf.fill("bg")
    pdf.rect(px, bt, W - sw - 4, bh, style="F", round_corners=True, corner_radius=2.5)
    pdf.text_at(px + 4, bt + 3, W - sw - 12, "문제 도출 · 핵심 문제 Top 3", size=9.5, bold=True, line_h=5)
    pdf.problem_list(px + 4, bt + 9, W - sw - 12, c["key_problems"], size=7, detail_limit=60)
    return pdf


REPORT_PDF_BUILDERS = {"formal": report_pdf_formal, "executive": report_pdf_executive, "onepage": report_pdf_onepage}


def report_build_pdf(style, data, kpis, summary, steps=None, utm_rows=None):
    """화면 데이터(report_load_data 결과)를 고른 양식(style)의 PDF로 만듭니다."""
    content = {
        "period": data["period"],
        "today": date.today().isoformat(),
        "summary": summary,
        "kpis": kpis,
        "key_problems": data["key_problems"],
        "internal": data["internal"],
        "threats": [f for f in data["external"] if f["kind"] == "위협"],
        "opportunities": [f for f in data["external"] if f["kind"] == "기회"],
        "competitors": data["competitors_full"],
        "criteria": data["criteria"],
        "keepa_status": data["keepa_status"],
        "ga4": data["ga4"], "steps": steps or [], "utm_rows": utm_rows or [],
        "ab_tests": data["ab_tests"],
    }
    return bytes(REPORT_PDF_BUILDERS[style](content).output())
