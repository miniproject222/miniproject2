# 3. 매체 제작 > 솔루션 제안 (이전 solution 모듈을 media로 합침)
# 매체(광고 소재) 외에 실행할 수 있는 솔루션 제안 화면. media_render()에서 불러 씁니다.
import streamlit as st

import ui_theme as ui


def media_solution_section():
    """'솔루션 제안' 영역을 그립니다. 3번 탭의 하위 탭 ④에서 부릅니다 (탭 이름이 제목 역할)."""
    st.caption("매체 외에 실행할 수 있는 솔루션 제안")

    ui.progress_list(
        "솔루션 우선순위 (샘플)", "3개",
        [("상세페이지 개선", "높음", 0.9), ("번들 구성", "중간", 0.6), ("리뷰 이벤트", "낮음", 0.3)],
    )
