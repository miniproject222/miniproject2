# 3. 매체 제작 > 3단계 ⑤: 외주 촬영 브리프 PDF (보고서 형식)
# 외주 묶음(zip) 중 글로 된 부분(브리프·찍지 말 것/넣을 것·프롬프트 A/B·영상 스토리보드·첨부 목록)을 PDF 한 장으로 만듭니다.
# 사진·영상 파일은 zip에 따로 들어갑니다. 다른 모듈 파일은 import할 수 없어서(RULES.md) ①·② PDF와 같은 공통 폰트·색으로 따로 만듭니다.
import re
from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace

import ui_theme as ui

MEDIA_S3_PDF_FONT_DIR = Path(__file__).resolve().parents[3] / "common" / "fonts"   # 공통 폰트 (읽기만)
MEDIA_S3_PDF_COMPANY = "SEORI(서리)"
MEDIA_S3_PDF_COLORS = {name: tuple(int(ui.THEME[key].lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
                       for name, key in {"text": "text", "muted": "muted", "soft": "primary_soft",
                                         "primary": "primary", "bg": "bg", "card": "card"}.items()}
# SUIT 글꼴에 움라우트·긴 줄표·특수 따옴표·이모지가 없어 바꾸거나 뺍니다 (예: Kühlgarn → Kuehlgarn)
MEDIA_S3_PDF_TRANS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss",
                                    "—": "-", "–": "-", "„": '"', "“": '"', "”": '"', "‘": "'", "’": "'",
                                    "®": "(R)", "²": "2", "Δ": "d", "…": "..."})
MEDIA_S3_PDF_EMOJI = re.compile("[\U0001F000-\U0001FFFF☀-➿️‍]")


class MediaS3Pdf(FPDF):
    """공통 폰트, 색, 쪽 번호 꼬리말을 가진 A4 보고서."""

    def __init__(self):
        super().__init__(orientation="P", format="A4")
        self.add_font("SUIT", "", str(MEDIA_S3_PDF_FONT_DIR / "SUIT-Regular.otf"))
        self.add_font("SUIT", "B", str(MEDIA_S3_PDF_FONT_DIR / "SUIT-Bold.otf"))
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=15)

    def normalize_text(self, text):
        return super().normalize_text(MEDIA_S3_PDF_EMOJI.sub("", str(text or "")).translate(MEDIA_S3_PDF_TRANS))

    def footer(self):
        self.set_y(-11)
        self.font(7, color="muted")
        self.cell(0, 4, f"{MEDIA_S3_PDF_COMPANY}  ·  외주 촬영 브리프  ·  대외비")
        self.set_x(self.l_margin)
        self.cell(0, 4, f"{self.page_no()} / {{nb}}", align="R")

    def font(self, size, bold=False, color="text"):
        self.set_font("SUIT", "B" if bold else "", size)
        self.set_text_color(*MEDIA_S3_PDF_COLORS[color])

    def text_at(self, x, y, w, text, size=9, bold=False, color="text", line_h=None, align="L"):
        """(x, y)에서 폭 w 안에 글을 쓰고, 끝난 y를 돌려줍니다."""
        self.set_xy(x, y)
        self.font(size, bold, color)
        self.multi_cell(w, line_h or size * 0.5, text, align=align, new_x="LMARGIN", new_y="NEXT")
        return self.get_y()

    def head(self, title):
        """□ 큰 제목. 남은 공간이 적으면 새 쪽에서 시작합니다."""
        y = self.get_y() + 4
        if y + 22 > self.page_break_trigger:
            self.add_page()
            y = self.t_margin
        return self.text_at(self.l_margin, y, self.epw, f"□ {title}", size=11.5, bold=True, line_h=7)

    def box(self, text, size=9):
        """테두리 상자 안 글 (프롬프트 등 긴 글)."""
        self.set_x(self.l_margin)
        self.font(size)
        self.set_draw_color(*MEDIA_S3_PDF_COLORS["soft"])
        self.set_line_width(0.3)
        self.multi_cell(self.epw, size * 0.55, text, border=1, padding=3, new_x="LMARGIN", new_y="NEXT")
        return self.get_y()

    def bullets(self, items, size=9):
        y = self.get_y() + 1
        for item in items:
            y = self.text_at(self.l_margin + 3, y, self.epw - 3, f"·  {item}", size=size, line_h=size * 0.55) + 0.5
        self.set_y(y)
        return y

    def table_rows(self, rows, widths, size=8):
        """첫 줄이 제목 줄인 표."""
        self.font(size)
        self.set_draw_color(*MEDIA_S3_PDF_COLORS["soft"])
        self.set_line_width(0.2)
        head = FontFace(emphasis="BOLD", fill_color=MEDIA_S3_PDF_COLORS["bg"], color=MEDIA_S3_PDF_COLORS["text"])
        with self.table(width=self.epw, col_widths=widths, align="LEFT", headings_style=head, line_height=size * 0.6,
                        padding=1.4, borders_layout="HORIZONTAL_LINES", cell_fill_mode="NONE", text_align="LEFT") as t:
            for row in rows:
                r = t.row()
                for value in row:
                    r.cell(str(value if value not in (None, "") else "-"))
        return self.get_y()


def media_s3_build_pdf(src: dict, group: dict, storyboard: list, photos: list, videos: list,
                       today: str, note: str) -> bytes:
    """외주 촬영 브리프 PDF. 순서: 개요(가설·단일 변수·A/B) → 촬영 지시 → 프롬프트 A·B → 영상 스토리보드 → 첨부 파일."""
    pdf = MediaS3Pdf()
    pdf.add_page()
    W, L = pdf.epw, pdf.l_margin

    pdf.text_at(L, 16, 80, MEDIA_S3_PDF_COMPANY, size=10, bold=True)
    pdf.text_at(L, 22, 80, "대외비", size=8, color="muted")
    pdf.set_draw_color(*MEDIA_S3_PDF_COLORS["text"])
    for yy, wd in ((32, 0.6), (33.2, 0.2), (54, 0.2), (55.2, 0.6)):   # 표제 이중선 (①·② 보고서와 같은 모양)
        pdf.set_line_width(wd)
        pdf.line(L, yy, L + W, yy)
    pdf.text_at(L, 37, W, "외주 촬영 브리프", size=18, bold=True, align="C", line_h=9)
    pdf.text_at(L, 47, W, "(SEORI 냉감패드 · amazon.de 메인 이미지 A/B 테스트용 촬영 요청)", size=9, color="muted", align="C")
    pdf.text_at(L, 57, W, f"보고일자 {today}", size=8, color="muted", align="R")
    pdf.set_y(64)

    # 1. 개요
    pdf.head("1. 이번 촬영의 목적")
    if group.get("hypothesis"):
        pdf.text_at(L + 3, pdf.get_y() + 1, W - 3, "검증할 가설", size=8.5, bold=True, color="muted")
        pdf.box(group["hypothesis"], size=9)
    pdf.set_y(pdf.get_y() + 2)
    pdf.table_rows([("구분", "내용"),
                    ("두 사진에서 바꾸는 것", group.get("variable") or src["variable"]),
                    ("지금 사진 (지금 아마존에 올라간 것)", group.get("a") or src["slot_a"]),
                    ("새로 찍을 사진", group.get("b") or src["slot_b"])], widths=(32, 68))
    pdf.text_at(L, pdf.get_y() + 1.5, W, "두 사진은 위 한 가지만 다르고 나머지(조명·배경·보정·제품)는 똑같아야 "
                "어느 쪽이 더 잘 팔리는지 정확히 비교할 수 있습니다.", size=8, color="muted")

    # 2. 촬영 지시
    pdf.head("2. 촬영 지시")
    pdf.bullets(["조명, 배경, 보정은 A·B 똑같이",
                 "고정 요소: " + (", ".join(src["fixed"]) or "-"),
                 "받을 것: 메인 이미지 A·B 각 3컷 (원본 + 흰 배경 보정본), 가능하면 서브 이미지도 같이"])
    pdf.text_at(L, pdf.get_y() + 1, W, "찍지 말 것", size=9, bold=True)
    pdf.bullets(src["avoid"] or ["(2단계 AI 다듬기 결과가 들어갈 자리)"])
    pdf.text_at(L, pdf.get_y() + 1, W, "넣을 것", size=9, bold=True)
    pdf.bullets(src["include"] or ["(2단계 AI 다듬기 결과가 들어갈 자리)"])

    # 3. 프롬프트
    pdf.head("3. 참고 이미지 프롬프트 (AI 초안을 만든 문장)")
    for name in ("A", "B"):
        pdf.text_at(L, pdf.get_y() + 1.5, W, f"사진 {name}", size=9, bold=True)
        pdf.box(src.get(f"prompt_{name.lower()}") or "-", size=8.5)

    # 4. 영상 스토리보드
    pdf.head("4. 영상 스토리보드")
    if storyboard:
        cols = ["장면", "길이(초)", "화면", "움직임", "자막", "피할 것"]
        rows = [tuple(cols)] + [tuple(r.get(c, "") for c in cols) for r in storyboard]
        pdf.table_rows(rows, widths=(12, 8, 26, 18, 20, 16), size=7.5)
    else:
        pdf.text_at(L + 3, pdf.get_y() + 1, W - 3, "넘긴 스토리보드가 없습니다 (사진만 요청).", size=9, color="muted")

    # 5. 첨부 파일
    pdf.head("5. 함께 보내는 파일 (zip 안)")
    files = [f"photo_reference/{n}" for n, _ in photos] + [f"video_draft/{n}" for n, _ in videos]
    pdf.bullets(files or ["첨부 파일 없음"], size=8.5)

    pdf.text_at(L, pdf.get_y() + 4, W, f"참고: {note}", size=8, color="muted")
    pdf.text_at(L, pdf.get_y() + 1, W, "※ 참고용 가이드이며 법률 자문이 아닙니다. 법률 확인을 권장합니다.", size=8, color="muted")
    return bytes(pdf.output())
