# 홈
from pathlib import Path

import streamlit as st

import ui_theme as ui

HOME_DIR = Path(__file__).resolve().parent   # 내 폴더 (images/, data/ 경로 만들 때 사용)


def home_left():
    ui.kpi_card("전날 매출", "€1,284", "+14%", "전일 대비 (샘플)", big=True)
    ui.share_list(
        "도시별 활동",
        [("Berlin", "38,520", 0.30), ("München", "32,100", 0.25), ("Hamburg", "25,700", 0.20),
         ("Köln", "19,300", 0.15), ("Frankfurt", "12,810", 0.10)],
    )


def home_right():
    ui.kpi_card("오늘 날씨", "31°C", sub="Berlin (샘플)")
    ui.progress_list("이번 주 일정", "3건", [("프로모션", "월", 0.3), ("광고 집행", "수", 0.6), ("리포트", "금", 0.9)])


def home_render():
    """'홈' 탭을 열 때마다 실행됩니다. 화면은 전부 이 함수 안에서 그립니다."""
    ui.page_header("홈", "날씨, 달력, 전날 매출과 이슈 알림 (샘플 데이터)")
    ui.hero_layout(home_left, home_right, temps=st.session_state.get("temps"), key="home_map")
