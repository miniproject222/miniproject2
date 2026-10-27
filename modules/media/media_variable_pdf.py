# 3. 매체 제작 > 가설에서 변수 도출: 확정한 솔루션 PDF (보고서에 붙이는 가로 A4 한 장)
# 솔루션 팝업의 '보고서용 PDF 저장' 버튼이 씁니다. 1번 리포트의 '한 장 요약' PDF와 같은 모양으로 그립니다:
# 위 색 띠 → 요약 칸 3개(독립 변수 · 목표 KPI · 작성) → 솔루션 제안 | 기대 효과·확인할 것 → 가설 표(If · Because · Then)
# 다른 모듈 파일은 import할 수 없어서(RULES.md) 같은 공통 폰트·색으로 따로 만듭니다.
import re
from datetime import datetime
from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace

import ui_theme as ui

MEDIA_VARIABLE_PDF_FONT_DIR = Path(__file__).resolve().parents[2] / "common" / "fonts"   # 공통 폰트 (읽기만)
MEDIA_VARIABLE_PDF_COMPANY = "SEORI(서리)"
MEDIA_VARIABLE_PDF_COLORS = {name: tuple(int(ui.THEME[key].lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
                             for name, key in {"text": "text", "muted": "muted", "soft": "primary_soft",
                                               "primary": "primary", "bg": "bg", "card": "card",
                                               "down_bg": "down_bg", "down_text": "down_text"}.items()}
# SUIT 글꼴에 움라우트·긴 줄표·특수 따옴표·이모지가 없어 바꾸거나 뺍니다 (예: kühlmatte → kuehlmatte)
MEDIA_VARIABLE_PDF_TRANS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss",
                                          "—": "-", "–": "-", "“": '"', "”": '"', "‘": "'", "’": "'", "…": "..."})
MEDIA_VARIABLE_PDF_EMOJI = re.compile("[\U0001F000-\U0001FFFF☀-➿️‍]")


class MediaVariablePdf(FPDF):
    """공통 폰트, 색, 꼬리말(회사 · 생성일 · 쪽 번호)을 가진 가로 A4."""

    def __init__(self):
        super().__init__(orientation="L", format="A4")
        self.add_font("SUIT", "", str(MEDIA_VARIABLE_PDF_FONT_DIR / "SUIT-Regular.otf"))
        self.add_font("SUIT", "B", str(MEDIA_VARIABLE_PDF_FONT_DIR / "SUIT-Bold.otf"))
        self.set_margins(10, 10, 10)
        self.set_auto_page_break(False)   # 한 장에 고정된 칸으로 그림

    def normalize_text(self, text):
        return super().normalize_text(MEDIA_VARIABLE_PDF_EMOJI.sub("", str(text or "")).translate(MEDIA_VARIABLE_PDF_TRANS))

    def footer(self):
        self.set_y(-11)
        self.font(7, color="muted")
        self.cell(0, 4, f"{MEDIA_VARIABLE_PDF_COMPANY}  ·  매체 제작 대신 솔루션 (3번 탭 ① 가설에서 변수 도출)  ·  "
                        f"생성일 {datetime.now().strftime('%Y-%m-%d')}")
        self.set_x(self.l_margin)
        self.cell(0, 4, f"{self.page_no()} / {{nb}}", align="R")

    def font(self, size, bold=False, color="text"):
        self.set_font("SUIT", "B" if bold else "", size)
        self.set_text_color(*MEDIA_VARIABLE_PDF_COLORS[color])

    def fill(self, color):
        self.set_fill_color(*MEDIA_VARIABLE_PDF_COLORS[color])

    def text_at(self, x, y, w, text, size=9, bold=False, color="text", line_h=None, align="L"):
        """(x, y)에서 폭 w 안에 글을 쓰고, 끝난 y를 돌려줍니다."""
        self.set_xy(x, y)
        self.font(size, bold, color)
        self.multi_cell(w, line_h or size * 0.5, text, align=align, new_x="LMARGIN", new_y="NEXT")
        return self.get_y()

    def box(self, x, y, w, h, title, filled=False):
        """둥근 칸 (filled면 연한 배경, 아니면 테두리) + 제목. 내용을 쓸 y를 돌려줍니다."""
        if filled:
            self.fill("bg")
            self.rect(x, y, w, h, style="F", round_corners=True, corner_radius=2.5)
        else:
            self.set_draw_color(*MEDIA_VARIABLE_PDF_COLORS["soft"])
            self.set_line_width(0.3)
            self.rect(x, y, w, h, style="D", round_corners=True, corner_radius=2.5)
        self.text_at(x + 4, y + 3, w - 8, title, size=9.5, bold=True, line_h=5)
        return y + 10

    def badge(self, x, y, label, style="primary", size=7):
        """둥근 배지. style: primary(진한 채움) / outline / down(주황). 배지 폭을 돌려줍니다."""
        self.font(size, bold=True)
        w = self.get_string_width(label) + 3
        h = size * 0.55
        if style == "outline":
            self.set_draw_color(*MEDIA_VARIABLE_PDF_COLORS["primary"])
            self.set_line_width(0.2)
            self.rect(x, y, w, h, style="D", round_corners=True, corner_radius=h / 2)
            self.font(size, bold=True, color="primary")
        else:
            self.fill("primary" if style == "primary" else "down_bg")
            self.rect(x, y, w, h, style="F", round_corners=True, corner_radius=h / 2)
            self.font(size, bold=True, color="card" if style == "primary" else "down_text")
        self.set_xy(x, y)
        self.cell(w, h, label, align="C")
        return w

    def table_at(self, x, w, rows, widths, size=8, padding=1.6):
        """x 위치에 폭 w 표 (첫 줄은 제목 줄, 가로줄만)."""
        old = self.l_margin
        self.set_left_margin(x)
        self.set_x(x)
        self.font(size)
        self.set_draw_color(*MEDIA_VARIABLE_PDF_COLORS["soft"])
        self.set_line_width(0.2)
        self.fill("card")
        head = FontFace(emphasis="BOLD", fill_color=MEDIA_VARIABLE_PDF_COLORS["bg"], color=MEDIA_VARIABLE_PDF_COLORS["text"])
        with self.table(width=w, col_widths=widths, align="LEFT", headings_style=head, line_height=size * 0.62,
                        padding=padding, borders_layout="HORIZONTAL_LINES", cell_fill_mode="NONE") as t:
            for row in rows:
                r = t.row()
                for value in row:
                    r.cell(str(value))
        self.set_left_margin(old)
        return self.get_y()


def media_variable_solution_pdf(solution: dict, parts: list[str] | None = None, goal: str = "") -> bytes:
    """확정한 솔루션을 가로 A4 한 장 PDF로 (solution 모양은 media_handoff_set_solution()과 같음).
    parts는 가설의 [If, Because, Then] (나눌 수 없으면 None → 가설 문장 한 줄), goal은 목표 KPI 한 줄."""
    pdf = MediaVariablePdf()
    pdf.alias_nb_pages()
    pdf.add_page()
    W, L = pdf.epw, pdf.l_margin
    today = datetime.now().strftime("%Y-%m-%d")

    # 상단 색 띠
    pdf.fill("primary")
    pdf.rect(L, 8, W, 13, style="F", round_corners=True, corner_radius=2.5)
    pdf.text_at(L + 5, 11, 180, f"{MEDIA_VARIABLE_PDF_COMPANY} 솔루션 제안  ·  {today[:7]}", size=12, bold=True,
                color="card", line_h=7)
    pdf.text_at(L + W - 95, 12.5, 90, "매체 제작 대신 솔루션 · 실행 단계 · 가설", size=7.5, color="soft", align="R")

    # 요약 칸 3개: 독립 변수 | 목표 KPI | 작성
    tiles = [("독립 변수", solution.get("variable", "-"), "매체 외 해결", 0.3),
             ("목표 KPI", goal.replace("**", "") or "-", "", 0.45),
             ("작성", solution.get("source", "-"), today, 0.25)]
    x, gap = L, 4
    for label, value, tag, ratio in tiles:
        tw = (W - gap * (len(tiles) - 1)) * ratio
        pdf.fill("bg")
        pdf.rect(x, 24, tw, 12, style="F", round_corners=True, corner_radius=2.5)
        pdf.text_at(x + 4, 25.5, tw - 8, label, size=7, color="muted", line_h=3.5)
        bw = 0
        if tag:
            pdf.font(6.5, bold=True)
            bw = pdf.get_string_width(tag) + 3
            pdf.badge(x + tw - 4 - bw, 30.5, tag, "down" if label == "독립 변수" else "outline", 6.5)
        pdf.set_xy(x + 4, 29.5)
        pdf.font(10.5, bold=True)
        pdf.cell(tw - 12 - bw, 5.5, value, new_x="LMARGIN", new_y="NEXT")   # 한 줄 (넘치면 칸 안에서 잘림)
        x += tw + gap

    # 가운데: 솔루션 제안 | 기대 효과 · 확인할 것
    top, ch = 39, 92
    lw = W * 0.6
    y = pdf.box(L, top, lw, ch, "솔루션 제안")
    y = pdf.text_at(L + 4, y, lw - 8, solution.get("title", "솔루션"), size=13, bold=True, color="primary", line_h=6.5) + 1.5
    y = pdf.text_at(L + 4, y, lw - 8, solution.get("summary", ""), size=9, line_h=5) + 4
    pdf.text_at(L + 4, y, lw - 8, "실행 단계", size=8, bold=True, color="primary", line_h=4.5)
    y += 6.5
    for i, step in enumerate(solution.get("steps") or [], start=1):
        bw = pdf.badge(L + 4, y + 0.6, f"{i}단계", "primary" if i == 1 else "outline", 7)
        y = pdf.text_at(L + 7 + bw, y, lw - 11 - bw, step["action"], size=9, bold=True, line_h=5)
        if step.get("detail"):
            y = pdf.text_at(L + 7 + bw, y + 0.5, lw - 11 - bw, step["detail"], size=8, color="muted", line_h=4.3)
        y += 3.5
    rx, rw = L + lw + 4, W - lw - 4
    y = pdf.box(rx, top, rw, ch, "기대 효과 · 확인할 것", filled=True)
    for head, key in (("기대 효과", "effect"), ("확인할 것", "check")):
        pdf.text_at(rx + 4, y, rw - 8, head, size=8, bold=True, color="primary", line_h=4.5)
        y = pdf.text_at(rx + 4, y + 5.5, rw - 8, solution.get(key) or "-", size=9, line_h=5) + 5

    # 아래: 가설 표
    bt = top + ch + 3
    y = pdf.box(L, bt, W, 190 - bt, "가설 (② 가설 수립에서 선택)")
    rows = [("구분", "내용")]
    rows += (list(zip(("If (만약)", "Because (왜냐하면)", "Then (그러면)"), (p.strip().rstrip(",") for p in parts)))
             if parts else [("가설", solution.get("hypothesis", "-"))])
    pdf.set_y(y - 1)
    pdf.table_at(L + 4, W - 8, rows, (40, W - 48), size=8)
    return bytes(pdf.output())
