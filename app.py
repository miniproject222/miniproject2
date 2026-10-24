# 대시보드 시작 파일 (PM)
# 로컬 실행: 프로젝트 맨 위 폴더에서 streamlit run app.py
# 배포: GitHub main에 올리면 Streamlit Community Cloud가 이 파일로 자동 배포합니다
# 디자인 규칙은 design.md, 공통 디자인 함수는 ui_theme.py에 있습니다
import inspect

import streamlit as st

import ui_theme as ui
from common.common_layout import LAYOUT_TABS, layout_load_css

# 1) 반드시 맨 위에서 1번만
ui.apply_theme(page_title="마케팅 솔루션 대시보드", page_icon="📊")
layout_load_css()   # common_style.css + 각 모듈의 모듈코드_style.css

# 지도를 쓰는 탭은 st.session_state["temps"]를 읽어 ui.hero_layout(temps=...)에 넘깁니다
# (사이드바 온도 토글을 없앴으므로 기본값 None = 지도만 표시. 기온이 필요한 탭은 탭 안에서 직접 불러옵니다)
st.session_state["temps"] = None

# 탭: common_style.css가 화면 왼쪽 세로 아이콘 줄로 배치합니다. 각 모듈의 모듈코드_render()가 탭 안을 그립니다
# 이름의 띄어쓰기를 줄바꿈 없는 공백( )으로 바꿔, 아이콘 아래에 이름이 한 줄로 오게 합니다
# key + bind="query-params"가 없으면, 다른 탭 안의 버튼을 눌러 화면이 다시 그려질 때마다
# 선택된 탭이 유지되지 않고 첫 번째 탭(홈)으로 돌아가 버립니다. URL에 선택된 탭을 저장해 두면
# 새로고침하거나 다른 위젯을 눌러도 보던 탭이 그대로 유지됩니다.
# bind는 Streamlit 1.66 이상에만 있으므로(requirements.txt), 그보다 낮은 버전에서는 빼고 실행해 오류를 막습니다.
# (이 경우 탭 유지만 안 될 뿐 앱은 열립니다. pip install -r requirements.txt 로 맞추면 해결)
NBSP = "\u00a0"
tab_params = inspect.signature(st.tabs).parameters
tab_options = {k: v for k, v in {"key": "main_tabs", "bind": "query-params"}.items() if k in tab_params}
tabs = st.tabs([f"{t['icon']} {t['label'].replace(' ', NBSP)}" for t in LAYOUT_TABS], **tab_options)
for tab, t in zip(tabs, LAYOUT_TABS):
    with tab:
        t["render"]()
