# ① 리포트 PDF 맨 아래에 ② 가설 붙이기 — report 담당자(PM) 적용용 수정안

> **2026-10-25 적용 완료**: ② 담당 요청("1번 탭 리포트를 2번 탭에서도 수정 가능하게 하고 가설을 하단에 추가")으로
> 아래 코드를 `report_pdf.py`, `report_download.py`에 그대로 넣었습니다. report 담당자·PM은 PR에서 이 두 파일 변경을 확인해 주세요.

- 요청: "1번 리포트에 2번 탭 가설을 하단에 추가" (② 가설 담당, 2026-10-25)
- 고칠 파일: `modules/report/report_pdf.py`, `modules/report/report_download.py` (report 모듈 — ② 담당은 수정 권한 없음)
- 읽는 값: `store_get("hypothesis")["selected"]` — ② 탭에서 "선택하기"를 누르면 저장됨
  (`if`, `because`, `then`, `sentence`, `execution`{항목: 내용}, `problem`{title …}, `saved_at`)
- 가설을 아직 선택하지 않았으면 지금과 똑같은 PDF가 나옵니다 (섹션을 건너뜀).
- 확인: 실제 ① 데이터로 아래 코드를 메모리에서만 붙여 3양식 모두 생성 확인
  (기안 보고서형 3쪽 — 마지막 쪽 경쟁사 비교 아래에 이어짐 / 경영진 보고형 5쪽 / 원페이지형 2쪽 — 둘째 쪽에 가설).

## 1. `report_pdf.py` — 함수 1개 추가 (`REPORT_PDF_BUILDERS = ...` 줄 바로 위)

```python
def report_pdf_hypothesis(pdf, h, new_page):
    """② 가설 수립 탭에서 선택한 가설(store "hypothesis"의 selected)을 PDF 맨 아래에 붙입니다."""
    def clean(text):
        return str(text or "-").replace("—", "-").replace("–", "-")   # SUIT 글꼴에 긴 줄표가 없음

    W, L = pdf.epw, pdf.l_margin
    if new_page:
        pdf.set_auto_page_break(True, margin=pdf.b_margin)   # 원페이지형은 자동 쪽 넘김이 꺼져 있음
        pdf.add_page()
        y = pdf.t_margin
    else:
        y = pdf.ensure_space(pdf.get_y() + 6, 40)
    y = pdf.text_at(L, y, W, "□ 가설 (② 가설 수립에서 선택)", size=11.5, bold=True, line_h=7)
    title = (h.get("problem") or {}).get("title")
    if title:
        y = pdf.text_at(L + 3, y + 1, W - 3, f"대상 문제: {clean(title)}", size=9, bold=True)
    pdf.set_y(y + 1.5)
    pdf.table_at(L, W, [("구분", "내용"), ("If (만약)", clean(h.get("if"))),
                        ("Because (왜냐하면)", clean(h.get("because"))), ("Then (그러면)", clean(h.get("then")))],
                 (1.3, 6), size=8.5)
    execution = h.get("execution") or {}
    if execution:
        y = pdf.text_at(L, pdf.ensure_space(pdf.get_y() + 3, 20), W, "실행 방법", size=10, bold=True, line_h=6)
        pdf.set_y(y)
        pdf.table_at(L, W, [("항목", "내용")] + [(k, clean(v)) for k, v in execution.items()], (1.3, 6), size=8)
    pdf.text_at(L, pdf.get_y() + 2, W, f"※ 가설 선택 {h.get('saved_at') or '-'} (② 가설 수립 탭 저장값)",
                size=7.5, color="muted")
```

## 2. `report_pdf.py` — `report_build_pdf` 수정 (인자 1개 추가, 마지막 줄 교체)

```python
def report_build_pdf(style, data, kpis, summary, steps=None, utm_rows=None, hypothesis=None):
    ...  # content = {...} 는 그대로
    pdf = REPORT_PDF_BUILDERS[style](content)
    if hypothesis:   # ② 탭에서 가설을 선택했을 때만
        report_pdf_hypothesis(pdf, hypothesis, new_page=style != "formal")
    return bytes(pdf.output())
```

## 3. `report_download.py` — 저장된 가설을 읽어 넘김

```python
from common.common_store import store_get   # 파일 위쪽 import에 추가

    # report_download_pdf() 안, st.download_button 위에
    saved = store_get("hypothesis")
    hypothesis = saved.get("selected") if isinstance(saved, dict) and isinstance(saved.get("selected"), dict) else None

    # data=... 줄을 아래로 교체
        data=report_build_pdf(style, data, kpis, summary, steps, utm_rows, hypothesis),
```

※ 다른 모듈 파일 import가 아니라 공용 저장소(`common.common_store`)만 읽으므로 RULES.md 규칙 안입니다.
