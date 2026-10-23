# 1. 분석 리포트
from pathlib import Path

import streamlit as st

from modules.report.report_download import report_download_button

REPORT_DIR = Path(__file__).resolve().parent   # 내 폴더 (images/, data/ 경로 만들 때 사용)


def report_render():
    """사이드바에서 '1. 분석 리포트' 탭을 열 때마다 실행됩니다. 화면은 전부 이 함수 안에서 그립니다."""
    st.header("1. 분석 리포트")
    st.markdown(
        '<div class="report-card"><p class="report-desc">결과 데이터 요약, 문제 분석, 리포트 다운로드</p></div>',
        unsafe_allow_html=True,
    )

    # 리포트 다운로드 버튼 (내용이 준비되면 아래 줄의 주석을 풀어 사용)
    # report_download_button("리포트 내용")
