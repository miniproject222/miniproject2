# 3-1. 솔루션 제안
from pathlib import Path

import streamlit as st

import ui_theme as ui

SOLUTION_DIR = Path(__file__).resolve().parent   # 내 폴더 (images/, data/ 경로 만들 때 사용)


def solution_render():
    """'3-1. 솔루션 제안' 탭을 열 때마다 실행됩니다. 화면은 전부 이 함수 안에서 그립니다."""
    ui.page_header("3-1. 솔루션 제안", "매체 외에 실행할 수 있는 솔루션 제안")

    ui.progress_list(
        "솔루션 우선순위 (샘플)", "3개",
        [("상세페이지 개선", "높음", 0.9), ("번들 구성", "중간", 0.6), ("리뷰 이벤트", "낮음", 0.3)],
    )
