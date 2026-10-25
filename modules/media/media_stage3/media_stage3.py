# 3. 매체 제작 > 3단계 ④: 사진·영상 초안 (3단계 담당 · DH 브랜치)
# 2단계가 다듬어 넘긴 프롬프트(media_handoff_prompt())로
# 사진 레퍼런스 A·B → 영상 스토리보드 → 영상 초안을 만듭니다. 만든 것은 ⑤ 외주 정리(media_stage3_export.py)가 묶습니다.
# 화면은 media_stage3_render() 안에서만 그립니다.
# 이름 규칙: 함수 media_s3_..., 위젯 key·session_state 키·CSS class media-s3-...
from pathlib import Path

import streamlit as st

from common.common_store import store_get
from modules.media.media_handoff import media_handoff_check, media_handoff_prompt

MEDIA_S3_TAB_LABEL = "사진·영상 초안"   # 하위 탭 이름 (여기서 바꾸면 탭과 이전/다음 버튼 글자가 함께 바뀜)
MEDIA_S3_DIR = Path(__file__).resolve().parent   # 3단계 폴더 (data/ 경로 만들 때 사용)
MEDIA_S3_MEDIA_NOTE = ("AI로 만든 사진·영상은 아마존 메인 이미지로 쓰지 않습니다. "
                       "외주 촬영 레퍼런스, 서브 이미지, 광고 초안으로만 씁니다.")
# ④에서 만든 것을 ⑤로 넘기는 session_state 키 (탭을 옮기면 위젯 값이 지워져서 따로 보관)
MEDIA_S3_PHOTOS = "media-s3-assets-photos"
MEDIA_S3_VIDEOS = "media-s3-assets-videos"
MEDIA_S3_STORYBOARD = "media-s3-storyboard"
# 영상 스토리보드 틀: 문제 → 해결 → 증거 → 신뢰 → 마무리 (AI가 리포트 값으로 채울 자리, 지금은 예시)
MEDIA_S3_STORYBOARD_SAMPLE = [
    {"장면": "1 문제", "길이(초)": 3, "화면": "여름밤 독일식 침실, 이불을 걷어 내는 손", "움직임": "이불을 천천히 걷어 냄",
     "자막": "„Über 26 °C im Schlafzimmer?\"", "피할 것": "과장된 표정, 공포 연출"},
    {"장면": "2 해결", "길이(초)": 3, "화면": "접힌 냉감패드를 침대 위에서 펼침 (레퍼런스 A)", "움직임": "두 손으로 펼침",
     "자막": "", "피할 것": "얼음, 서리, 차가운 김"},
    {"장면": "3 증거: 두께", "길이(초)": 4, "화면": "모서리를 들어 단면 두께를 보여 줌 (레퍼런스 B)", "움직임": "모서리를 천천히 들기",
     "자막": "두께 수치 (시험값 확보 후)", "피할 것": "실제보다 두꺼워 보이는 연출"},
    {"장면": "4 증거: 원단", "길이(초)": 4, "화면": "손바닥으로 원단을 쓸고 면 뒷면을 보여 줌", "움직임": "쓸기 → 뒤집기",
     "자막": "피부 표면 기준 표현만", "피할 것": "체온을 낮춘다, 천연"},
    {"장면": "5 신뢰·마무리", "길이(초)": 3, "화면": "90×200 침대에 깔린 모습, 인증 라벨 클로즈업", "움직임": "위에서 내려오는 카메라",
     "자막": "90 × 200 cm · OEKO-TEX® (인증 번호)", "피할 것": "친환경 아이콘, 직접 만든 인증 마크"},
]


def media_s3_input() -> dict:
    """2단계가 다듬어 넘긴 프롬프트. 아직 넘기지 않았으면 예시 값(src["sample"] == True)이 옵니다."""
    return media_handoff_prompt()


def media_s3_keep_files(files, key: str) -> list:
    """올린 파일을 (이름, 내용)으로 session_state에 보관합니다. ⑤ 외주 정리 탭에서 읽어요."""
    if files:
        st.session_state[key] = [(f.name, f.getvalue()) for f in files]
    return st.session_state.get(key, [])


def media_s3_photo_section():
    """사진 레퍼런스 A·B: 다듬은 프롬프트로 만든 '이렇게 찍어 주세요' 견본."""
    st.markdown("**사진 레퍼런스 A·B**")
    st.button("사진 레퍼런스 생성", key="media-s3-btn-photo", disabled=True,
              help="이미지 생성 AI가 정해지면 연결합니다. 지금은 만든 사진을 아래에 올려 주세요.")
    files = st.file_uploader("사진 올리기 (파일 이름에 A 또는 B)", type=["png", "jpg", "jpeg", "webp"],
                             accept_multiple_files=True, key="media-s3-photo-files")
    kept = media_s3_keep_files(files, MEDIA_S3_PHOTOS)
    st.caption(f"보관된 사진 {len(kept)}장")


def media_s3_storyboard_section():
    """영상 스토리보드: 문제 → 해결 → 증거 → 신뢰 → 마무리 틀에 리포트 값을 채운 장면 목록."""
    st.markdown("**영상 스토리보드**")
    claims = (store_get("report") or {}).get("ad_claims") or {}
    if claims.get("allowed_scenes"):
        st.caption(f"리포트 허용 장면: {claims['allowed_scenes']}")
    st.button("스토리보드 생성", key="media-s3-btn-storyboard", disabled=True,
              help="AI 키가 들어오면 리포트 값(ad_claims)으로 장면을 채웁니다. 지금은 예시 틀을 직접 고칠 수 있어요.")
    rows = st.session_state.get(MEDIA_S3_STORYBOARD, MEDIA_S3_STORYBOARD_SAMPLE)
    edited = st.data_editor(rows, num_rows="dynamic", hide_index=True, width="stretch", key="media-s3-storyboard-editor")
    st.session_state[MEDIA_S3_STORYBOARD] = list(edited)


def media_s3_video_section():
    """영상 초안: 스토리보드를 따라 만든 짧은 초안 영상."""
    st.markdown("**영상 초안**")
    st.button("영상 초안 생성", key="media-s3-btn-video", disabled=True,
              help="영상 생성 도구가 정해지면 연결합니다. 지금은 만든 영상을 아래에 올려 주세요.")
    files = st.file_uploader("영상 올리기", type=["mp4", "mov"], accept_multiple_files=True,
                             key="media-s3-video-files")
    kept = media_s3_keep_files(files, MEDIA_S3_VIDEOS)
    st.caption(f"보관된 영상 {len(kept)}개")


def media_stage3_render():
    """3단계 ④ 하위 탭(이름은 MEDIA_S3_TAB_LABEL, 탭 이름이 제목 역할). 반드시 media_render() 안에서 부릅니다."""
    src = media_s3_input()
    st.caption("2단계에서 다듬은 프롬프트로 사진 레퍼런스와 영상 스토리보드·초안을 만들어요. " + MEDIA_S3_MEDIA_NOTE)
    if src.get("sample"):
        st.caption("2단계에서 프롬프트를 아직 넘기지 않아 예시 프롬프트로 보여 줘요.")
    if not media_handoff_check(src, src["prompt_a"], src["prompt_b"])["ok"]:
        st.warning("받은 프롬프트 A·B가 빈칸 말고도 달라요. 2단계에서 다시 확인해 주세요.")

    c1, c2 = st.columns(2)
    for col, name in ((c1, "A"), (c2, "B")):
        with col:
            st.markdown(f"**다듬은 프롬프트 {name}**")
            st.code(src[f"prompt_{name.lower()}"], language=None, wrap_lines=True)

    media_s3_photo_section()
    media_s3_storyboard_section()
    media_s3_video_section()
