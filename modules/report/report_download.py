# 1. 분석 리포트 - 리포트 다운로드 (PDF)
import streamlit as st


def report_download_pdf(data, kpis, summary, steps=None, utm_rows=None):
    """report_render()에서 호출합니다. 양식을 고르면 그 양식의 PDF를 다운로드 버튼으로 보여 줍니다."""
    try:
        from modules.report.report_pdf import REPORT_PDF_STYLES, report_build_pdf
    except ImportError:
        st.warning("PDF를 만들려면 fpdf2 라이브러리가 필요합니다. `pip install -r requirements.txt`를 실행해 주세요.")
        return

    # 팀에서 양식을 하나로 정하면 이 선택 칸을 지우고 그 양식만 남깁니다
    style = st.radio(
        "PDF 양식", list(REPORT_PDF_STYLES), format_func=REPORT_PDF_STYLES.get,
        horizontal=True, key="report-radio-pdf-style",
    )
    st.download_button(
        "리포트 다운로드 (PDF)",
        data=report_build_pdf(style, data, kpis, summary, steps, utm_rows),
        file_name=f"report_{data['period']}_{style}.pdf",
        mime="application/pdf",
        key="report-btn-download",
    )
