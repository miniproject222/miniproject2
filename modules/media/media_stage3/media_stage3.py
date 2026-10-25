# 3. 매체 제작 > 3단계 ④: 사진·영상 초안 제작 (3단계 담당 · DH 브랜치)
# 2단계가 다듬어 넘긴 프롬프트(media_handoff_prompt())로
# 하위 탭 2개로 나눠 사진 초안 A·B(프롬프트 A·B로 생성)와 영상 초안(스토리보드 확정 → 영상 프롬프트로 생성)을 만듭니다. '⑤로 넘기기' 버튼을 누르면 ⑤ 외주 정리(media_stage3_export.py)가 받아 묶습니다.
# 화면은 media_stage3_render() 안에서만 그립니다.
# 이름 규칙: 함수 media_s3_..., 위젯 key·session_state 키·CSS class media-s3-...
import time
from pathlib import Path

import streamlit as st

from common.common_store import store_get
from modules.media.media_handoff import (media_handoff_assets, media_handoff_check, media_handoff_prompt,
                                         media_handoff_set_assets)
from modules.media.media_stage3.media_stage3_image import (MEDIA_S3_HF_FAIL, MEDIA_S3_HF_PENDING, MEDIA_S3_HF_WAIT_MAX,
                                                           media_s3_hf_download, media_s3_hf_key, media_s3_hf_status,
                                                           media_s3_hf_submit)

MEDIA_S3_TAB_LABEL = "사진·영상 초안 제작"   # 하위 탭 이름 (여기서 바꾸면 탭과 이전/다음 버튼 글자가 함께 바뀜)
MEDIA_S3_DIR = Path(__file__).resolve().parent   # 3단계 폴더 (data/ 경로 만들 때 사용)
MEDIA_S3_MEDIA_NOTE = ("AI로 만든 사진·영상은 아마존 메인 이미지로 쓰지 않습니다. "
                       "외주 촬영 레퍼런스, 서브 이미지, 광고 초안으로만 씁니다.")
# ④에서 만든 것을 ⑤로 넘기는 session_state 키 (탭을 옮기면 위젯 값이 지워져서 따로 보관)
MEDIA_S3_PHOTOS = "media-s3-assets-photos"            # ⑤로 넘기는 사진 전체 (올린 사진 + 만든 사진)
MEDIA_S3_PHOTO_UPLOADS = "media-s3-photo-uploads"    # 직접 올린 사진
MEDIA_S3_AI_PHOTOS = "media-s3-ai-photos"            # Higgsfield로 만든 사진 {"A": (파일 이름, 내용), "B": ...}
MEDIA_S3_PHOTO_JOB = "media-s3-photo-job"            # 만드는 중인 요청 (뒤에 -A / -B)
MEDIA_S3_VIDEOS = "media-s3-assets-videos"
MEDIA_S3_STORYBOARD = "media-s3-storyboard"
MEDIA_S3_STORYBOARD_DONE = "media-s3-storyboard-done"   # 확정한 스토리보드 (영상 초안은 이걸로 만듦)
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


def media_s3_video_prompt(src: dict, storyboard: list) -> str:
    """영상 초안 프롬프트: 스토리보드 장면을 순서대로 이어 붙이고, 2단계의 찍지 말 것을 덧붙입니다."""
    scenes = [f"{i}. ({r.get('길이(초)', '')}s) {r.get('화면', '')} / {r.get('움직임', '')}"
              + (f" / 자막: {r['자막']}" if r.get("자막") else "") + (f" / 피할 것: {r['피할 것']}" if r.get("피할 것") else "")
              for i, r in enumerate(storyboard, 1) if r.get("화면")]
    total = sum(int(r.get("길이(초)") or 0) for r in storyboard)
    return "\n".join([f"Short product video draft, about {total} seconds, 16:9, realistic and calm, no exaggeration.",
                      f"Product: cooling mattress pad 90x200 cm. Single variable shown in the photos: {src['variable']}.",
                      "Scenes:", *scenes,
                      *(["Avoid: " + ", ".join(src["avoid"])] if src["avoid"] else [])])


def _media_s3_photo_start(name: str, prompt: str) -> None:
    """'사진 A/B 만들기' 버튼 콜백: Higgsfield에 요청을 보내고 요청 번호를 보관합니다 (결과는 아래에서 기다림)."""
    try:
        job = {"id": media_s3_hf_submit(prompt), "status": "queued", "prompt": prompt, "start": time.time()}
    except RuntimeError as err:
        job = {"status": "error", "error": str(err), "prompt": prompt}
    st.session_state[f"{MEDIA_S3_PHOTO_JOB}-{name}"] = job


def _media_s3_photo_finish(name: str, job: dict, url: str) -> None:
    """완성된 사진을 내려받아 AI 사진 보관함에 넣습니다 (같은 A/B의 이전 AI 사진은 바꿈). ⑤ 외주 정리로도 넘어감."""
    data, ext = media_s3_hf_download(url)
    file_name = f"photo_{name}_higgsfield{ext}"
    st.session_state.setdefault(MEDIA_S3_AI_PHOTOS, {})[name] = (file_name, data)
    job.update(status="completed", file=file_name)


@st.fragment(run_every=3)
def _media_s3_photo_wait(name: str) -> None:
    """만드는 중인 사진을 3초마다 확인합니다. 끝나면(완성·실패) 화면 전체를 다시 그려 결과를 보여 줍니다."""
    job = st.session_state.get(f"{MEDIA_S3_PHOTO_JOB}-{name}") or {}
    if job.get("status") not in MEDIA_S3_HF_PENDING:
        return
    try:
        state = media_s3_hf_status(job["id"])
        if state["status"] == "completed" and state["url"]:
            _media_s3_photo_finish(name, job, state["url"])
        elif state["status"] in MEDIA_S3_HF_FAIL:
            job.update(status="error", error=f"Higgsfield에서 {MEDIA_S3_HF_FAIL[state['status']]} {state['error']}".strip())
        elif time.time() - job["start"] > MEDIA_S3_HF_WAIT_MAX:
            job.update(status="error", error=f"{MEDIA_S3_HF_WAIT_MAX // 60}분이 지나도 사진이 나오지 않았어요. 다시 눌러 주세요.")
        else:
            job["status"] = state["status"] or job["status"]
            st.caption(f"사진 {name} 만드는 중… ({int(time.time() - job['start'])}초)")
            return
    except RuntimeError as err:
        job.update(status="error", error=str(err))
    st.rerun()


def media_s3_photo_section(src: dict):
    """④-1 사진 초안 제작: 2단계에서 다듬은 프롬프트 A·B로 Higgsfield에서 '이렇게 찍어 주세요' 견본을 만듭니다.
    키가 없으면 버튼이 꺼지고, 다른 곳에서 만든 사진을 올릴 수 있습니다. 만든 사진과 올린 사진은 함께 ⑤로 넘어갑니다."""
    has_key = bool(media_s3_hf_key())
    ai_photos = st.session_state.get(MEDIA_S3_AI_PHOTOS, {})
    c1, c2 = st.columns(2)
    for col, name in ((c1, "A"), (c2, "B")):
        prompt = src[f"prompt_{name.lower()}"]
        job = st.session_state.get(f"{MEDIA_S3_PHOTO_JOB}-{name}") or {}
        busy = job.get("status") in MEDIA_S3_HF_PENDING
        with col:
            with st.container(border=True):
                st.markdown(f"**사진 {name}** · 프롬프트 {name}")
                st.code(prompt, language=None, wrap_lines=True)
                st.button(f"사진 {name} 다시 만들기" if name in ai_photos else f"사진 {name} 만들기",
                          key=f"media-s3-btn-photo-{name}", disabled=not has_key or busy,
                          on_click=_media_s3_photo_start, args=(name, prompt),
                          help=("secrets.toml에 HF_KEY를 넣으면 Higgsfield로 만들 수 있어요. 지금은 다른 곳에서 만든 사진을 아래에 올려 주세요."
                                if not has_key else "Higgsfield로 이 프롬프트의 견본 사진을 만들어요 (누를 때마다 크레딧 차감)"))
                if busy:
                    _media_s3_photo_wait(name)
                elif job.get("status") == "error":
                    st.warning(f"사진 {name}: {job['error']}")
                if name in ai_photos:
                    file_name, data = ai_photos[name]
                    st.image(data, caption=f"{file_name} · Higgsfield로 만든 견본 (메인 이미지에 쓰지 않음)")
                    if job.get("prompt") and job["prompt"] != prompt:
                        st.caption("프롬프트가 바뀌었어요. 새 프롬프트로 다시 만들어 주세요.")
    files = st.file_uploader("만든 사진 올리기 (파일 이름에 A 또는 B)", type=["png", "jpg", "jpeg", "webp"],
                             accept_multiple_files=True, key="media-s3-photo-files")
    uploads = media_s3_keep_files(files, MEDIA_S3_PHOTO_UPLOADS)
    # ⑤로 넘길 사진 = 올린 사진 + Higgsfield로 만든 사진
    st.session_state[MEDIA_S3_PHOTOS] = list(uploads) + [ai_photos[n] for n in ("A", "B") if n in ai_photos]
    st.caption(f"보관된 사진 {len(st.session_state[MEDIA_S3_PHOTOS])}장 (올린 사진 {len(uploads)}장 · "
               f"만든 사진 {len(ai_photos)}장)")


def _media_s3_confirm_storyboard() -> None:
    """'스토리보드 확정' 버튼 콜백. 지금 표를 확정본으로 보관합니다."""
    st.session_state[MEDIA_S3_STORYBOARD_DONE] = list(st.session_state.get(MEDIA_S3_STORYBOARD, MEDIA_S3_STORYBOARD_SAMPLE))


def media_s3_storyboard_section():
    """④-2 영상 초안 제작의 1단계: 문제 → 해결 → 증거 → 신뢰 → 마무리 틀로 스토리보드를 만들고 확정합니다."""
    st.markdown("**1단계 · 스토리보드 만들기**")
    claims = (store_get("report") or {}).get("ad_claims") or {}
    if claims.get("allowed_scenes"):
        st.caption(f"리포트 허용 장면: {claims['allowed_scenes']}")
    st.button("스토리보드 만들기", key="media-s3-btn-storyboard", disabled=True,
              help="AI 키가 들어오면 리포트 값(ad_claims)으로 장면을 채웁니다. 지금은 예시 틀을 직접 고칠 수 있어요.")
    rows = st.session_state.get(MEDIA_S3_STORYBOARD, MEDIA_S3_STORYBOARD_SAMPLE)
    edited = st.data_editor(rows, num_rows="dynamic", hide_index=True, width="stretch", key="media-s3-storyboard-editor")
    st.session_state[MEDIA_S3_STORYBOARD] = list(edited)
    done = st.session_state.get(MEDIA_S3_STORYBOARD_DONE)
    st.button("스토리보드 확정", key="media-s3-btn-storyboard-done", type="primary", on_click=_media_s3_confirm_storyboard)
    if done is not None and done != st.session_state[MEDIA_S3_STORYBOARD]:
        st.caption("확정한 뒤 표가 바뀌었어요. 영상 프롬프트에 반영하려면 다시 확정해 주세요.")


def media_s3_video_section(src: dict):
    """④-2 영상 초안 제작의 2단계: 확정한 스토리보드로 만든 영상 프롬프트로 짧은 초안 영상을 만듭니다."""
    st.markdown("**2단계 · 영상 초안 만들기**")
    storyboard = st.session_state.get(MEDIA_S3_STORYBOARD_DONE)
    if storyboard is None:
        st.info("먼저 위에서 스토리보드를 확정해 주세요. 확정한 장면으로 영상 프롬프트를 만들어요.")
        return
    with st.container(border=True):
        st.markdown("**영상 프롬프트** (확정한 스토리보드에서 자동으로 만듦)")
        st.code(media_s3_video_prompt(src, storyboard), language=None, wrap_lines=True)
        st.button("영상 초안 만들기", key="media-s3-btn-video", disabled=True,
                  help="영상 생성 도구가 정해지면 이 프롬프트로 만듭니다. 지금은 다른 곳에서 만든 영상을 아래에 올려 주세요.")
    files = st.file_uploader("만든 영상 올리기", type=["mp4", "mov"], accept_multiple_files=True,
                             key="media-s3-video-files")
    kept = media_s3_keep_files(files, MEDIA_S3_VIDEOS)
    st.caption(f"보관된 영상 {len(kept)}개")


def media_s3_assets_value() -> dict:
    """⑤로 넘기는 값: 확정한 스토리보드와 보관된 사진·영상 파일 이름 (모양은 media_handoff.py의 MEDIA_HANDOFF_ASSETS_SAMPLE)."""
    return {"storyboard": st.session_state.get(MEDIA_S3_STORYBOARD_DONE) or [],
            "photos": [name for name, _ in st.session_state.get(MEDIA_S3_PHOTOS, [])],
            "videos": [name for name, _ in st.session_state.get(MEDIA_S3_VIDEOS, [])]}


def _media_s3_handoff() -> None:
    """'⑤로 넘기기' 버튼 콜백. 확정한 스토리보드와 파일 이름을 ⑤로 넘깁니다 (Supabase에 저장)."""
    media_handoff_set_assets(media_s3_assets_value())
    st.session_state["media-s3-handoff-toast"] = True


def media_s3_handoff_step() -> None:
    """넘기기 줄: 버튼을 눌러야만 ⑤ 외주 정리로 넘어갑니다. 넘기기 전 / 넘김 완료 / 바뀌어서 다시 넘겨야 함을 보여 줍니다."""
    if st.session_state.pop("media-s3-handoff-toast", False):
        st.toast("사진·영상 초안을 ⑤ 외주 정리로 넘겼어요", icon="✅")
    saved, now = media_handoff_assets(), media_s3_assets_value()
    sent = not saved["sample"] and all(saved.get(k) == v for k, v in now.items())
    if sent:
        note = ":green-badge[✅ 넘김 완료] ⑤ 외주 정리가 이 스토리보드와 파일을 받아요"
    elif not saved["sample"]:
        note = ":orange-badge[다시 넘기기 필요] 넘긴 뒤 스토리보드나 파일이 바뀌었어요. ⑤는 아직 이전 값을 받아요"
    else:
        note = "사진·영상 초안을 다 만들면 '⑤로 넘기기'를 눌러 주세요"
    ready = bool(now["storyboard"])
    with st.container(horizontal=True, vertical_alignment="center", key="media-s3-handoff-row"):
        st.markdown(note)
        if not sent:
            st.button("다시 넘기기" if not saved["sample"] else "⑤로 넘기기", key="media-s3-btn-handoff",
                      type="primary", disabled=not ready, on_click=_media_s3_handoff,
                      help=None if ready else "영상 초안 제작 탭에서 스토리보드를 먼저 확정해 주세요")


def media_stage3_render():
    """3단계 ④ 하위 탭(이름은 MEDIA_S3_TAB_LABEL, 탭 이름이 제목 역할). 반드시 media_render() 안에서 부릅니다."""
    src = media_s3_input()
    st.caption("2단계에서 다듬은 프롬프트로 사진 초안을, 스토리보드로 영상 초안을 만들어요. " + MEDIA_S3_MEDIA_NOTE)
    if src.get("sample"):
        st.caption("2단계에서 프롬프트를 아직 넘기지 않아 예시 프롬프트로 보여 줘요.")
    if not media_handoff_check(src, src["prompt_a"], src["prompt_b"])["ok"]:
        st.warning("받은 프롬프트 A·B가 빈칸 말고도 달라요. 2단계에서 다시 확인해 주세요.")

    # ④ 안의 하위 탭: 사진 초안 제작 / 영상 초안 제작 (영상은 스토리보드 확정 → 영상 초안 순서)
    photo_tab, video_tab = st.tabs(["사진 초안 제작", "영상 초안 제작"], key="media-s3-sub")
    with photo_tab:
        media_s3_photo_section(src)
    with video_tab:
        media_s3_storyboard_section()
        media_s3_video_section(src)
    media_s3_handoff_step()
