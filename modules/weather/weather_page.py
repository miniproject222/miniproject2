# 4. 날씨 광고 타이밍
from pathlib import Path

import streamlit as st

WEATHER_DIR = Path(__file__).resolve().parent   # 내 폴더 (images/, data/ 경로 만들 때 사용)


def weather_render():
    """사이드바에서 '4. 날씨 광고 타이밍' 탭을 열 때마다 실행됩니다. 화면은 전부 이 함수 안에서 그립니다."""
    st.header("4. 날씨 광고 타이밍")
    st.markdown(
        '<div class="weather-card"><p class="weather-desc">날씨, 상황에 따른 광고(메타, 아마존) 노출 빈도와 예산 추천</p></div>',
        unsafe_allow_html=True,
    )
