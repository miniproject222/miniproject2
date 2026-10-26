# 3. 매체 제작 > 가설에서 변수 도출: 확정한 솔루션 PDF (보고서에 붙이는 한 장)
# 솔루션 팝업의 '보고서용 PDF 저장' 버튼이 씁니다. 내용·순서는 .md 파일(media_variable_solution_markdown)과 같습니다.
# 다른 모듈 파일은 import할 수 없어서(RULES.md) ①·② PDF와 같은 공통 폰트·색으로 따로 만듭니다.
import re
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

import ui_theme as ui

MEDIA_VARIABLE_PDF_FONT_DIR = Path(__file__).resolve().parents[2] / "common" / "fonts"   # 공통 폰트 (읽기만)
MEDIA_VARIABLE_PDF_COLORS = {name: tuple(int(ui.THEME[key].lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
                             for name, key in {"text": "text", "muted": "muted", "soft": "primary_soft",
                                               "primary": "primary"}.items()}
# SUIT 글꼴에 긴 줄표·특수 따옴표·이모지가 없어 바꾸거나 뺍니다
MEDIA_VARIABLE_PDF_TRANS = str.maketrans({"—": "-", "–": "-", "“": '"', "”": '"', "‘": "'", "’": "'", "…": "..."})
MEDIA_VARIABLE_PDF_EMOJI = re.compile("[\U0001F000-\U0001FFFF☀-➿️‍]")


class MediaVariablePdf(FPDF):
    """공통 폰트, 색, 쪽 번호 꼬리말을 가진 A4 한 장."""

    def __init__(self):
        super().__init__(orientation="P", format="A4")
        self.add_font("SUIT", "", str(MEDIA_VARIABLE_PDF_FONT_DIR / "SUIT-Regular.otf"))
        self.add_font("SUIT", "B", str(MEDIA_VARIABLE_PDF_FONT_DIR / "SUIT-Bold.otf"))
        self.set_margins(18, 18, 18)
        self.set_auto_page_break(auto=True, margin=18)

    def normalize_text(self, text):
        return super().normalize_text(MEDIA_VARIABLE_PDF_EMOJI.sub("", str(text or "")).translate(MEDIA_VARIABLE_PDF_TRANS))

    def footer(self):
        self.set_y(-12)
        self.font(7, color="muted")
        self.cell(0, 4, "매체 제작 대신 솔루션 · 가설에서 변수 도출")
        self.set_x(self.l_margin)
        self.cell(0, 4, f"{self.page_no()} / {{nb}}", align="R")

    def font(self, size, bold=False, color="text"):
        self.set_font("SUIT", "B" if bold else "", size)
        self.set_text_color(*MEDIA_VARIABLE_PDF_COLORS[color])

    def para(self, text, size=10, bold=False, color="text", indent=0, gap=1.5):
        """왼쪽 여백(+indent)부터 폭 끝까지 글을 쓰고 gap만큼 띄웁니다."""
        self.set_x(self.l_margin + indent)
        self.font(size, bold, color)
        self.multi_cell(self.epw - indent, size * 0.55, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(gap)

    def head(self, title):
        """□ 소제목. 남은 공간이 적으면 새 쪽에서 시작합니다."""
        self.ln(3)
        if self.get_y() + 20 > self.page_break_trigger:
            self.add_page()
        self.para(f"□ {title}", size=11.5, bold=True, gap=1)


def media_variable_solution_pdf(solution: dict) -> bytes:
    """확정한 솔루션을 PDF로 (solution 모양은 media_handoff_set_solution()과 같음)."""
    pdf = MediaVariablePdf()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.para("매체 제작 대신 솔루션", size=9, color="primary", gap=0.5)
    pdf.para(solution.get("title", "솔루션"), size=17, bold=True, gap=2)
    pdf.set_draw_color(*MEDIA_VARIABLE_PDF_COLORS["soft"])
    pdf.set_line_width(0.4)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + pdf.epw, pdf.get_y())
    pdf.ln(3)
    for label, value in (("가설", solution.get("hypothesis", "-")), ("변수", solution.get("variable", "-")),
                         ("작성", f"{solution.get('source', '-')} · {datetime.now().strftime('%Y-%m-%d')}")):
        pdf.para(f"{label}  {value}", size=9, color="muted", gap=0.5)
    pdf.head("요약")
    pdf.para(solution.get("summary", ""))
    pdf.head("실행 단계")
    for i, step in enumerate(solution.get("steps") or [], start=1):
        pdf.para(f"{i}. {step['action']}", bold=True, indent=2, gap=0.5)
        if step.get("detail"):
            pdf.para(step["detail"], size=9.5, color="muted", indent=6, gap=1.5)
    for head, key in (("기대 효과", "effect"), ("확인할 것", "check")):
        if solution.get(key):
            pdf.head(head)
            pdf.para(solution[key])
    return bytes(pdf.output())
