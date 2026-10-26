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


# ① 분석에서 '상세 정보 없음'으로 나온 항목 → 여분으로 찍어 둘 영상 컷 (다음 가설 대비, 재촬영 방지)
MEDIA_S3_EXTRA_CUTS = {"세탁": "세탁기에 넣고 빼는 장면", "고정 밴드": "고정 밴드가 매트리스 모서리를 잡는 장면",
                       "인증": "인증 라벨 클로즈업", "두께·사이즈": "줄자로 두께·사이즈를 재는 장면"}


def media_s3_brief(src: dict, group: dict, ctx: dict) -> dict:
    """외주 브리프 1·2번 내용 (⑤ 화면 카드와 PDF가 같이 씀). 값은 전부 ctx(리포트·가설·스토리보드)에서 가져오고,
    없는 값은 그 줄을 뺍니다. ctx: sqp, kpi_photo, hooks{"A","B"}, common, video_sec, hook_sec, fixed_ko, forbidden, image_fixes."""
    sqp = ctx.get("sqp") or {}
    why = []
    if sqp.get("query") and isinstance(sqp.get("ratio"), (int, float)):
        why.append(f"amazon.de 검색어 '{sqp['query']}'에서 우리 상품은 보이는 것에 비해 덜 눌립니다 "
                   f"(노출 대비 클릭 {sqp['ratio']:g}배).")
    if sqp.get("cart_rate_ours") is not None and sqp.get("cart_rate_market") is not None:
        why.append(f"클릭한 뒤 장바구니 비율은 시장과 비슷합니다 (우리 {sqp['cart_rate_ours']}% vs 시장 {sqp['cart_rate_market']}%). "
                   "그래서 문제는 첫인상입니다.")
    if isinstance(sqp.get("price_gap"), (int, float)) and sqp["price_gap"] > 0:
        why.append(f"클릭된 상품보다 €{sqp['price_gap']:.0f} 비싼데, 비싼 이유가 화면에서 안 보입니다.")
    hooks, common = ctx.get("hooks"), ctx.get("common") or []
    video_sec, hook_sec = ctx.get("video_sec", 10), ctx.get("hook_sec", 3)
    variable, a, b = group.get("variable") or src["variable"], group.get("a") or src["slot_a"], group.get("b") or src["slot_b"]
    if hooks:
        exp = [("어디서", "아마존 메인 이미지", "자사몰 상품 영상"),
               ("바꾸는 것", variable, f"첫 {hook_sec}초 장면"),
               ("A (지금 방식)", a, hooks["A"].get("화면", "")),
               ("B (가설)", b, hooks["B"].get("화면", "")),
               ("같게 둘 것", "배경·조명·보정·제품", f"나머지 {video_sec - hook_sec}초·길이·자막·음악"),
               ("목표", ctx.get("kpi_photo") or "-", "영상 클릭률 B > A")]
        result = f"사진 2장 + 영상 2버전({video_sec}초)을 한 번의 촬영으로 만듭니다."
    else:
        exp = [("어디서", "아마존 메인 이미지", "-"), ("바꾸는 것", variable, "-"), ("A (지금 방식)", a, "-"),
               ("B (가설)", b, "-"), ("같게 둘 것", "배경·조명·보정·제품", "-"), ("목표", ctx.get("kpi_photo") or "-", "-")]
        result = "사진 2장을 촬영합니다 (영상 A·B 스토리보드가 없어 영상은 이번 요청에서 빠짐)."
    common_txt = " → ".join(str(r.get("화면", "")) for r in common)
    cuts = ([("컷 1 · 공통", f"{common_txt} ({video_sec - hook_sec}초)", "A·B 둘 다"),
             ("컷 2 · A 첫 3초", hooks["A"].get("화면", ""), "영상 A"),
             ("컷 3 · B 첫 3초", hooks["B"].get("화면", ""), "영상 B")] if hooks else [])
    edit_rules = (["편집: 영상 A = 컷 2 + 컷 1, 영상 B = 컷 3 + 컷 1",
                   "컷 2와 컷 3은 같은 위치·조명·인물. 컷 1은 두 버전이 완전히 같은 파일",
                   "소리 없이 자동 재생: 자막은 독일어 존댓말(Sie)로 짧게, 첫 3초에는 자막 없음 (차이가 화면에만 있게)"]
                  if hooks else [])
    rules = ["'체온을 낮춘다' 금지 → '피부 표면이 시원하게 느껴진다'만",
             "숫자 옆에는 시험 조건을 꼭 같이 (완제품·온도차 10 °C·시험기관·성적서 번호)"]
    rules += [f"쓰지 말 것: {f}" for f in (ctx.get("forbidden") or [])[1:5]]
    extra, seen = [], []   # 순서 유지 (세탁 → 고정 밴드 → …)
    for fix in ctx.get("image_fixes") or []:
        for key, cut in MEDIA_S3_EXTRA_CUTS.items():
            if key in str(fix.get("title", "")) and key not in seen:
                seen.append(key)
                extra.append(cut)
    extra_note = ("① 분석에서 '상세페이지에 " + "·".join(seen) + " 정보 없음'이 다음 문제로 나왔어요. "
                  "가설이 틀리면 다시 찍지 않고 편집만 바꿔요.") if seen else ""
    return {"why": why, "hypothesis": group.get("hypothesis") or "", "exp": exp, "result": result,
            "common": ["실제 SEORI 냉감패드 90×200 cm 사용. 색·원단·누빔은 실물 그대로, 두께 과장 금지",
                       "사진과 영상은 같은 날, 같은 세트, 같은 조명에서 촬영"],
            "photo": [("사진 A", a), ("사진 B", b),
                      ("규칙", "흰 배경(RGB 255), 글자·로고·소품·사람·손 없음 (아마존 메인 이미지 규칙)"),
                      ("고정 요소", ctx.get("fixed_ko") or ", ".join(src["fixed"]) or "-"),
                      ("받을 것", "A·B 각 3컷 (원본 + 흰 배경 보정본)")],
            "cuts": cuts, "edit": edit_rules, "rules": rules, "extra": extra, "extra_note": extra_note}


def media_s3_build_pdf(src: dict, group: dict, storyboard: list, photos: list, videos: list,
                       today: str, note: str, ctx: dict | None = None) -> bytes:
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
    pdf.text_at(L, 47, W, "(SEORI 냉감패드 · 아마존 메인 이미지 A/B + 자사몰 영상 A/B 촬영 요청)", size=9, color="muted", align="C")
    pdf.text_at(L, 57, W, f"보고일자 {today}", size=8, color="muted", align="R")
    pdf.set_y(64)

    brief = media_s3_brief(src, group, ctx or {})

    # 1. 이번 촬영의 목적: 왜 찍나(데이터) → 무엇을 확인하나(가설) → 어떻게 확인하나(사진·영상 실험 2개) → 결과물
    pdf.head("1. 이번 촬영의 목적")
    pdf.text_at(L, pdf.get_y() + 1, W, "① 왜 찍나 (1번 문제 분석 데이터)", size=9, bold=True)
    pdf.bullets(brief["why"] or ["1번 리포트 값이 없어 생략"])
    if brief["hypothesis"]:
        pdf.text_at(L, pdf.get_y() + 1.5, W, "② 무엇을 확인하나 (가설)", size=9, bold=True)
        pdf.box(brief["hypothesis"], size=9)
    pdf.text_at(L, pdf.get_y() + 1.5, W, "③ 어떻게 확인하나 (같은 가설, 실험 2개)", size=9, bold=True)
    pdf.table_rows([("구분", "사진 A/B", "영상 A/B"), *brief["exp"]], widths=(18, 41, 41))
    pdf.text_at(L, pdf.get_y() + 1.5, W, "④ " + brief["result"], size=9, bold=True)

    # 2. 촬영 지시
    pdf.head("2. 촬영 지시")
    pdf.text_at(L, pdf.get_y() + 1, W, "① 공통 (사진·영상 모두)", size=9, bold=True)
    pdf.bullets(brief["common"])
    pdf.text_at(L, pdf.get_y() + 1, W, "② 사진 (아마존 메인 이미지)", size=9, bold=True)
    pdf.table_rows([("항목", "내용"), *brief["photo"]], widths=(18, 82))
    if src["avoid"]:
        pdf.text_at(L, pdf.get_y() + 1, W, "사진에서 찍지 말 것", size=8.5, bold=True, color="muted")
        pdf.bullets(src["avoid"], size=8)
    if src["include"]:
        pdf.text_at(L, pdf.get_y() + 1, W, "사진에 넣을 것", size=8.5, bold=True, color="muted")
        pdf.bullets(src["include"], size=8)
    if brief["cuts"]:
        pdf.text_at(L, pdf.get_y() + 1.5, W, "③ 영상 (자사몰, 한 번 촬영 → 두 버전 편집)", size=9, bold=True)
        pdf.table_rows([("컷", "내용", "쓰는 곳"), *brief["cuts"]], widths=(18, 66, 16))
        pdf.bullets(brief["edit"], size=8.5)
    pdf.text_at(L, pdf.get_y() + 1.5, W, "④ 독일 광고 규칙 (어기면 재촬영)", size=9, bold=True)
    pdf.bullets(brief["rules"], size=8.5)
    if brief["extra"]:
        pdf.text_at(L, pdf.get_y() + 1.5, W, "⑤ 여분 컷 (재촬영 방지)", size=9, bold=True)
        pdf.bullets(brief["extra"] + [brief["extra_note"]], size=8.5)

    # 3. 프롬프트
    pdf.head("3. 참고 이미지 프롬프트 (AI 초안을 만든 문장)")
    for name in ("A", "B"):
        pdf.text_at(L, pdf.get_y() + 1.5, W, f"사진 {name}", size=9, bold=True)
        pdf.box(src.get(f"prompt_{name.lower()}") or "-", size=8.5)

    # 4. 영상 스토리보드
    pdf.head("4. 영상 스토리보드")
    if storyboard and any("첫" in str(r.get("장면", "")) and str(r.get("장면", "")).strip()[-1:] in ("A", "B") for r in storyboard):
        pdf.text_at(L + 3, pdf.get_y() + 1, W - 3, "자사몰 A/B 영상 2버전: 한 번 촬영해서 두 버전으로 편집해 주세요. "
                    "첫 3초만 A·B가 다르고, 나머지 장면·길이·자막·음악은 두 버전이 완전히 같아야 합니다.", size=8.5, bold=True)
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
