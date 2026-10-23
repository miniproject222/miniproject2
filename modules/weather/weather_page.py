# 4. 날씨 광고 타이밍
from pathlib import Path

import streamlit as st

import ui_theme as ui

WEATHER_DIR = Path(__file__).resolve().parent   # 내 폴더 (images/, data/ 경로 만들 때 사용)


def weather_left():
    ui.kpi_card("추천 광고 빈도", "x1.5", "+50%", "폭염 예보 기준 (샘플)", big=True)
    ui.share_list("매체별 예산", [("Meta", "€1,200", 0.6), ("Amazon", "€800", 0.4)])


def weather_right():
    temps = st.session_state.get("temps")
    if temps:
        hottest = sorted(temps, key=lambda p: p["temp"], reverse=True)[:3]
        ui.progress_list(
            "기온 상위 지역", f"{hottest[0]['city']} {hottest[0]['temp']:.0f}°",
            [(p["city"], f"{p['temp']:.0f}°C", min(p["temp"] / 40, 1)) for p in hottest],
        )
    else:
        ui.kpi_card("기온 상위 지역", "-", sub="사이드바에서 '지역별 온도 표시'를 켜세요")


def weather_render():
    """'4. 날씨 광고 타이밍' 탭을 열 때마다 실행됩니다. 화면은 전부 이 함수 안에서 그립니다."""
    ui.page_header("4. 날씨 광고 타이밍", "날씨, 상황에 따른 광고(메타, 아마존) 노출 빈도와 예산 추천")
    ui.hero_layout(weather_left, weather_right, temps=st.session_state.get("temps"), key="weather_map")
