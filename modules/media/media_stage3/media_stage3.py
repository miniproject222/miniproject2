# 3. 매체 제작 > 3단계: 솔루션 제안 (3단계 담당 · DH 브랜치)
# 2단계 판정 결과(media_handoff_result())를 받아 매체 외에 실행할 수 있는 솔루션을 제안합니다.
# 화면은 media_stage3_render() 안에서만 그립니다.
# 이름 규칙: 함수 media_s3_..., 위젯 key·session_state 키·CSS class media-s3-...
from pathlib import Path

import streamlit as st

import ui_theme as ui
from modules.media.media_handoff import media_handoff_result

MEDIA_S3_TAB_LABEL = "솔루션 제안"   # 하위 탭 이름 (여기서 바꾸면 탭과 이전/다음 버튼 글자가 함께 바뀜)
MEDIA_S3_DIR = Path(__file__).resolve().parent   # 3단계 폴더 (data/ 경로 만들 때 사용)


def media_stage3_render():
    """3단계 하위 탭(이름은 MEDIA_S3_TAB_LABEL, 탭 이름이 제목 역할). 반드시 media_render() 안에서 부릅니다."""
    result = media_handoff_result()   # 2단계 판정 결과 (아직 없으면 예시 값, result["sample"] == True)
    st.caption("매체 외에 실행할 수 있는 솔루션 제안")

    ui.progress_list(
        "솔루션 우선순위 (샘플)", "3개",
        [("상세페이지 개선", "높음", 0.9), ("번들 구성", "중간", 0.6), ("리뷰 이벤트", "낮음", 0.3)],
    )
