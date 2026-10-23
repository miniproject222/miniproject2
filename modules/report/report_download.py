# 1. 분석 리포트 - 리포트 다운로드
import streamlit as st


def report_download_button(content: str, file_name: str = "report.txt"):
    """report_render()에서 호출합니다."""
    st.download_button(
        "리포트 다운로드",
        data=content,
        file_name=file_name,
        key="report-btn-download",
    )
