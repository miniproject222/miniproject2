# 1. 분석 리포트
from pathlib import Path

import streamlit as st

import ui_theme as ui

from modules.report.report_download import report_download_button

REPORT_DIR = Path(__file__).resolve().parent   # 내 폴더 (images/, data/ 경로 만들 때 사용)


def report_render():
    """'1. 분석 리포트' 탭을 열 때마다 실행됩니다. 화면은 전부 이 함수 안에서 그립니다."""
    ui.page_header("1. 분석 리포트", "결과 데이터 요약, 문제 분석, 리포트 다운로드 (샘플 데이터)")

    k1, k2, k3, k4 = st.columns(4)
    with k1: ui.kpi_card("월 매출", "€32,875", "+14%")
    with k2: ui.kpi_card("주문 수", "1,284", "+6%")
    with k3: ui.kpi_card("전환율", "1.6%", "-0.4%")
    with k4: ui.kpi_card("반품률", "3.2%", "-1.1%")

    with st.container(border=True):
        st.markdown("**문제 요인** (내부 / 외부 분석이 들어갈 자리)")

    # 리포트 다운로드 버튼 (내용이 준비되면 아래 줄의 주석을 풀어 사용)
    # report_download_button("리포트 내용")
