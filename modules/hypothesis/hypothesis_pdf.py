# 2. 가설 수립 - "① 문제 분석 요약 + ② 선택한 가설" PDF
# ① 탭 PDF(modules/report/report_pdf.py)는 ① 내용만 담고, 다른 모듈 파일은 import할 수 없어서(RULES.md)
# 같은 공통 폰트·색으로 가설 탭에서 따로 만듭니다. '선택하기'로 저장한 값(store "hypothesis")만 읽으므로
# Keepa 등 외부 조회는 하지 않습니다.
import re
from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace

import ui_theme as ui

HYPOTHESIS_PDF_FONT_DIR = Path(__file__).resolve().parents[2] / "common" / "fonts"   # 공통 폰트 (읽기만)
HYPOTHESIS_PDF_COMPANY = "SEORI(서리)"
HYPOTHESIS_PDF_SOURCE = "출처: ① 문제 분석 리포트 저장값 + ② 가설 탭에서 선택한 가설"
HYPOTHESIS_PDF_COLORS = {name: tuple(int(ui.THEME[key].lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
                         for name, key in {"text": "text", "muted": "muted", "soft": "primary_soft",
                                           "primary": "primary", "bg": "bg", "card": "card"}.items()}
# SUIT 글꼴에 움라우트·긴 줄표·이모지가 없어 ① PDF와 같은 방식으로 바꾸거나 뺍니다 (예: kühlmatte → kuehlmatte)
HYPOTHESIS_PDF_UMLAUT = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss",
                                       "—": "-", "–": "-"})
HYPOTHESIS_PDF_EMOJI = re.compile("[\U0001F000-\U0001FFFF☀-➿️‍]")


def hypothesis_pdf_clean(text) -> str:
    return HYPOTHESIS_PDF_EMOJI.sub("", str(text or "")).strip()


class HypothesisPdf(FPDF):
    """공통 폰트, 색, 쪽 번호 꼬리말을 가진 PDF (① PDF와 같은 모양)."""

    def __init__(self):
        super().__init__(orientation="P", format="A4")
        self.add_font("SUIT", "", str(HYPOTHESIS_PDF_FONT_DIR / "SUIT-Regular.otf"))
        self.add_font("SUIT", "B", str(HYPOTHESIS_PDF_FONT_DIR / "SUIT-Bold.otf"))
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=15)

    def normalize_text(self, text):
        return super().normalize_text(hypothesis_pdf_clean(text).translate(HYPOTHESIS_PDF_UMLAUT))

    def footer(self):
        self.set_y(-11)
        self.font(7, color="muted")
        self.cell(0, 4, f"{HYPOTHESIS_PDF_COMPANY}  ·  문제 분석 · 가설 보고서  ·  대외비  ·  {HYPOTHESIS_PDF_SOURCE}")
        self.set_x(self.l_margin)
        self.cell(0, 4, f"{self.page_no()} / {{nb}}", align="R")

    def font(self, size, bold=False, color="text"):
        self.set_font("SUIT", "B" if bold else "", size)
        self.set_text_color(*HYPOTHESIS_PDF_COLORS[color])

    def text_at(self, x, y, w, text, size=9, bold=False, color="text", line_h=None, align="L"):
        """(x, y)에서 폭 w 안에 글을 쓰고, 끝난 y를 돌려줍니다."""
        self.set_xy(x, y)
        self.font(size, bold, color)
        self.multi_cell(w, line_h or size * 0.5, text, align=align, new_x="LMARGIN", new_y="NEXT")
        return self.get_y()

    def head(self, title):
        """□ 큰 제목. 남은 공간이 적으면 새 쪽에서 시작합니다."""
        y = self.get_y() + 3
        if y + 20 > self.page_break_trigger:
            self.add_page()
            y = self.t_margin
        return self.text_at(self.l_margin, y, self.epw, f"□ {title}", size=11.5, bold=True, line_h=7)

    def table_rows(self, rows, widths, size=8.5):
        """첫 줄이 제목 줄인 표를 왼쪽 여백부터 그립니다."""
        self.font(size)
        self.set_draw_color(*HYPOTHESIS_PDF_COLORS["soft"])
        self.set_line_width(0.2)
        self.set_fill_color(*HYPOTHESIS_PDF_COLORS["card"])
        head = FontFace(emphasis="BOLD", fill_color=HYPOTHESIS_PDF_COLORS["bg"], color=HYPOTHESIS_PDF_COLORS["text"])
        with self.table(width=self.epw, col_widths=widths, align="LEFT", headings_style=head, line_height=size * 0.62,
                        padding=1.4, borders_layout="HORIZONTAL_LINES", cell_fill_mode="NONE") as t:
            for row in rows:
                r = t.row()
                for value in row:
                    r.cell(str(value))
        return self.get_y()


def hypothesis_pdf_problems(report: dict) -> list[dict]:
    """① 핵심 문제 Top 3 (없으면 problems 앞 3개)."""
    items = report.get("key_problems") or report.get("problems") or []
    return [p for p in items if isinstance(p, dict)][:3]


def hypothesis_build_pdf(saved: dict, today: str) -> bytes:
    """'선택하기'로 저장한 값(store "hypothesis")으로 PDF를 만듭니다.
    순서: ① 핵심 요약 → ① 문제 도출 → ② 선택한 가설(If·Because·Then, 가설 문장) → ② 실행 방법."""
    report = saved.get("report") if isinstance(saved.get("report"), dict) else {}
    selected = saved.get("selected") if isinstance(saved.get("selected"), dict) else {}
    problem = selected.get("problem") if isinstance(selected.get("problem"), dict) else {}

    pdf = HypothesisPdf()
    pdf.add_page()
    W, L = pdf.epw, pdf.l_margin

    pdf.text_at(L, 16, 80, HYPOTHESIS_PDF_COMPANY, size=10, bold=True)
    pdf.text_at(L, 22, 80, "대외비", size=8, color="muted")
    pdf.set_draw_color(*HYPOTHESIS_PDF_COLORS["text"])
    for yy, wd in ((32, 0.6), (33.2, 0.2), (54, 0.2), (55.2, 0.6)):   # 표제 이중선 (① 기안 보고서형과 같은 모양)
        pdf.set_line_width(wd)
        pdf.line(L, yy, L + W, yy)
    pdf.text_at(L, 37, W, "문제 분석 · 가설 보고서", size=18, bold=True, align="C", line_h=9)
    pdf.text_at(L, 47, W, "(① 문제 분석 리포트 요약 + ② 선택한 가설과 실행 방법)", size=9, color="muted", align="C")
    as_of = f"데이터 기준 {report['as_of']}      " if report.get("as_of") else ""
    pdf.text_at(L, 57, W, f"{as_of}가설 선택 {selected.get('saved_at') or '-'}      보고일자 {today}",
                size=8, color="muted", align="R")
    pdf.set_y(64)

    # ① 문제 분석 요약
    if report.get("summary"):
        y = pdf.head("① 핵심 요약")
        pdf.set_xy(L, y + 1)
        pdf.font(9.5)
        pdf.set_draw_color(*HYPOTHESIS_PDF_COLORS["text"])
        pdf.set_line_width(0.3)
        pdf.multi_cell(W, 6, str(report["summary"]), border=1, padding=3, new_x="LMARGIN", new_y="NEXT")

    problems = hypothesis_pdf_problems(report)
    if problems:
        y = pdf.head("① 문제 도출 (핵심 문제)")
        for i, p in enumerate(problems, start=1):
            label = f"{p.get('rank') or i}순위 · {p.get('type') or '-'}"
            chosen = " (가설로 선택)" if p.get("title") and p.get("title") == problem.get("title") else ""
            y = pdf.text_at(L + 3, y + 1, W - 3, f"{label}  {p.get('title', '')}{chosen}", size=9, bold=True)
            if p.get("detail"):
                y = pdf.text_at(L + 3, y + 0.5, W - 3, f"근거: {p['detail']}", size=7.5, color="muted")
            if p.get("question"):
                y = pdf.text_at(L + 3, y + 0.5, W - 3, f"→ 가설 질문: {p['question']}", size=8, bold=True, color="primary")
            y += 2
        pdf.set_y(y)

    # ② 선택한 가설
    y = pdf.head("② 선택한 가설")
    if problem.get("title"):
        y = pdf.text_at(L + 3, y + 1, W - 3, f"대상 문제: {problem['title']}", size=9, bold=True)
    pdf.set_y(y + 1.5)
    pdf.table_rows([("구분", "내용")] + [(k, selected.get(key) or "-") for k, key in
                                        (("If (만약)", "if"), ("Because (왜냐하면)", "because"), ("Then (그러면)", "then"))],
                   (1.3, 6), size=9)
    y = pdf.text_at(L, pdf.get_y() + 2, W, "가설 문장", size=9, bold=True, line_h=5)
    pdf.set_xy(L, y + 0.5)
    pdf.font(9.5)
    pdf.set_fill_color(*HYPOTHESIS_PDF_COLORS["bg"])
    pdf.multi_cell(W, 6, str(selected.get("sentence") or saved.get("text") or "-"), fill=True, padding=3,
                   new_x="LMARGIN", new_y="NEXT")

    execution = selected.get("execution") if isinstance(selected.get("execution"), dict) else {}
    if execution:
        pdf.head("② 실행 방법")
        pdf.table_rows([("항목", "내용")] + list(execution.items()), (1.3, 6), size=8.5)

    pdf.text_at(L, pdf.get_y() + 3, W, f"※ {HYPOTHESIS_PDF_SOURCE}. 경쟁사 비교·요인 분석 전체는 ① 탭 PDF를 함께 확인해 주세요.",
                size=8, color="muted")
    return bytes(pdf.output())
