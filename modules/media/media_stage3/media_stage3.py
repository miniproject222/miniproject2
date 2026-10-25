# 3. 매체 제작 > 3단계 ④: 사진·영상 초안 제작 (3단계 담당 · DH 브랜치)
# 2단계가 다듬어 넘긴 프롬프트(media_handoff_prompt())로
# 하위 탭 2개로 나눠 사진 초안 A·B(프롬프트 A·B로 생성)와 영상 초안(스토리보드 확정 → 영상 프롬프트로 생성)을 만듭니다. '⑤로 넘기기' 버튼을 누르면 ⑤ 외주 정리(media_stage3_export.py)가 받아 묶습니다.
# 화면은 media_stage3_render() 안에서만 그립니다.
# 이름 규칙: 함수 media_s3_..., 위젯 key·session_state 키·CSS class media-s3-...
from pathlib import Path

import streamlit as st

from common.common_store import store_get
from modules.media.media_stage3.media_stage3_hf_mcp import (MediaS3HFError, media_s3_hf_check, media_s3_hf_download,
                                                           media_s3_hf_submit)
from modules.media.media_stage3.media_stage3_ai import (MEDIA_S3_VIDEO_ASPECT, MEDIA_S3_VIDEO_SECONDS, MediaS3AIError, media_s3_ai_ready, media_s3_forbidden_hits,
                                                       media_s3_make_image, media_s3_make_storyboard, media_s3_make_video,
                                                       media_s3_video_ready)
from modules.media.media_stage3.media_stage3_store import media_s3_store_file, media_s3_store_json, media_s3_store_load
from modules.media.media_handoff import (media_handoff_assets, media_handoff_check, media_handoff_prompt,
                                         media_handoff_set_assets)

MEDIA_S3_TAB_LABEL = "사진·영상 초안 제작"   # 하위 탭 이름 (여기서 바꾸면 탭과 이전/다음 버튼 글자가 함께 바뀜)
MEDIA_S3_DIR = Path(__file__).resolve().parent   # 3단계 폴더 (data/ 경로 만들 때 사용)
MEDIA_S3_MEDIA_NOTE = ("AI로 만든 사진·영상은 아마존 메인 이미지로 쓰지 않습니다. "
                       "외주 촬영 레퍼런스, 서브 이미지, 광고 초안으로만 씁니다.")
# ④에서 만든 것을 ⑤로 넘기는 session_state 키 (탭을 옮기면 위젯 값이 지워져서 따로 보관)
MEDIA_S3_PHOTOS = "media-s3-assets-photos"
MEDIA_S3_VIDEOS = "media-s3-assets-videos"
MEDIA_S3_STORYBOARD = "media-s3-storyboard"
MEDIA_S3_STORYBOARD_DONE = "media-s3-storyboard-done"   # 확정한 스토리보드 (영상 초안은 이걸로 만듦)
MEDIA_S3_VIDEO_JOB = "media-s3-video-job"               # 만드는 중인 Higgsfield 영상 작업 {"job_id", "prompt"}
MEDIA_S3_VIDEO_LINKS = "media-s3-video-links"           # 영상 파일 이름 → {"job_id", "url"} (Higgsfield에서 보기)
MEDIA_S3_HF_SITE = "https://higgsfield.ai"
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


def media_s3_put_file(key: str, name: str, content: bytes) -> None:
    """(이름, 내용)을 session_state 목록에 넣습니다. 같은 이름이 있으면 바꿔 끼웁니다."""
    files = [f for f in st.session_state.get(key, []) if f[0] != name]
    st.session_state[key] = files + [(name, content)]
    media_s3_store_file(key, name, content)   # 탭을 옮기거나 새로고침해도 남게 폴더에도 저장


def media_s3_keep_files(files, key: str) -> list:
    """올린 파일을 (이름, 내용)으로 session_state에 보관합니다 (AI로 만든 파일은 그대로 두고 더함). ⑤ 외주 정리 탭에서 읽어요."""
    for f in files or []:
        media_s3_put_file(key, f.name, f.getvalue())
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


def media_s3_ai_help(ready: bool, what: str, key: str = "OPENAI_API_KEY") -> str | None:
    return None if ready else f"secrets.toml에 {key}를 넣으면 {what}를 AI로 만들 수 있어요. 지금은 만든 파일을 작업 공간에 올려 주세요."


def _media_s3_remove_file(key: str, name: str, uploader: str) -> None:
    """작업 공간 '지우기' 콜백. 보관 목록에서 빼고, 올리기 칸을 비워 같은 파일이 다시 들어오지 않게 합니다."""
    st.session_state[key] = [f for f in st.session_state.get(key, []) if f[0] != name]
    media_s3_store_file(key, name, None)
    links = st.session_state.get(MEDIA_S3_VIDEO_LINKS, {})
    if name in links:
        links = {k: v for k, v in links.items() if k != name}
        st.session_state[MEDIA_S3_VIDEO_LINKS] = links
        media_s3_store_json(MEDIA_S3_VIDEO_LINKS, links)
    st.session_state[f"{uploader}-ver"] = st.session_state.get(f"{uploader}-ver", 0) + 1


def media_s3_workspace(kind: str, key: str, uploader: str, types: list, cols: int):
    """작업 공간: AI로 만들거나 올린 파일을 한곳에 모아 미리 보기·내려받기·지우기. 여기 있는 파일이 ⑤ 외주 정리로 갑니다."""
    with st.container(border=True, key=f"{uploader}-space"):
        st.markdown(f"**{kind} 작업 공간** · 여기 있는 {kind}이 ⑤ 외주 정리로 가요")
        files = st.file_uploader(f"직접 만든 {kind} 올리기", type=types, accept_multiple_files=True,
                                 key=f"{uploader}-{st.session_state.get(f'{uploader}-ver', 0)}")
        kept = media_s3_keep_files(files, key)
        if not kept:
            st.caption(f"아직 {kind}이 없어요. 위에서 AI로 만들거나 여기에 올려 주세요.")
            return
        grid = st.columns(cols)
        for i, (name, content) in enumerate(kept):
            with grid[i % cols]:
                with st.container(border=True):
                    try:   # 깨진 파일 하나 때문에 탭 전체가 멈추지 않게
                        if kind == "사진":
                            st.image(content, width="stretch")
                        else:
                            st.video(content)
                    except Exception:
                        st.caption("미리 보기를 할 수 없는 파일이에요")
                    st.caption(("🤖 AI · " if "_ai." in name else "📁 올림 · ") + name)
                    with st.container(horizontal=True):
                        st.download_button("내려받기", content, file_name=name, key=f"{uploader}-dl-{name}", type="primary")
                        st.button("지우기", key=f"{uploader}-rm-{name}", type="tertiary",
                                  on_click=_media_s3_remove_file, args=(key, name, uploader))


def media_s3_photo_section(src: dict):
    """④-1 사진 초안 제작: 프롬프트 A·B로 OpenAI 이미지 AI가 '이렇게 찍어 주세요' 견본을 만들고, 작업 공간에 모읍니다."""
    ready = media_s3_ai_ready("OPENAI_API_KEY")
    st.markdown("**사진 만들기** (OpenAI)")
    c1, c2 = st.columns(2)
    for col, name in ((c1, "A"), (c2, "B")):
        with col:
            with st.container(border=True):
                st.markdown(f"**사진 {name}** · 프롬프트 {name}")
                st.code(src[f"prompt_{name.lower()}"], language=None, wrap_lines=True)
                if st.button(f"사진 {name} 만들기", key=f"media-s3-btn-photo-{name}", type="primary", disabled=not ready,
                             help=media_s3_ai_help(ready, "사진") or "OpenAI 이미지 AI로 만들어요. 다시 누르면 새 사진으로 바꿔요"):
                    with st.spinner(f"사진 {name}를 만드는 중이에요 (10~30초)"):
                        try:
                            media_s3_put_file(MEDIA_S3_PHOTOS, f"photo_{name}_ai.png",
                                              media_s3_make_image(src[f"prompt_{name.lower()}"]))
                            st.toast(f"사진 {name}를 작업 공간에 넣었어요", icon="🖼️")
                        except MediaS3AIError as err:
                            st.warning(str(err))
    media_s3_workspace("사진", MEDIA_S3_PHOTOS, "media-s3-photo-files", ["png", "jpg", "jpeg", "webp"], cols=3)


def _media_s3_confirm_storyboard() -> None:
    """'스토리보드 확정' 버튼 콜백. 지금 표를 확정본으로 보관합니다."""
    st.session_state[MEDIA_S3_STORYBOARD_DONE] = list(st.session_state.get(MEDIA_S3_STORYBOARD, MEDIA_S3_STORYBOARD_SAMPLE))
    media_s3_store_json(MEDIA_S3_STORYBOARD_DONE, st.session_state[MEDIA_S3_STORYBOARD_DONE])


def media_s3_storyboard_section(src: dict):
    """④-2 영상 초안 제작의 1단계: 문제 → 해결 → 증거 → 신뢰 → 마무리 틀로 스토리보드를 만들고 확정합니다."""
    st.markdown("**1단계 · 스토리보드 만들기**")
    report = store_get("report") or {}
    claims = report.get("ad_claims") or {}
    if claims.get("allowed_scenes"):
        st.caption(f"리포트 허용 장면: {claims['allowed_scenes']}")
    ready = media_s3_ai_ready("OPENAI_API_KEY")
    if st.button("스토리보드 만들기", key="media-s3-btn-storyboard", type="primary", disabled=not ready,
                 help=media_s3_ai_help(ready, "스토리보드") or "리포트 값(허용 장면·쓸 수 있는 문구·금지 표현)으로 장면을 채워요"):
        with st.spinner("스토리보드를 만드는 중이에요 (10~20초)"):
            try:
                st.session_state[MEDIA_S3_STORYBOARD] = media_s3_make_storyboard(src, report)
                # 표 위젯을 새로 그려 AI 결과가 바로 보이게 (key를 바꿈)
                st.session_state["media-s3-storyboard-ver"] = st.session_state.get("media-s3-storyboard-ver", 0) + 1
            except MediaS3AIError as err:
                st.warning(str(err))
    rows = st.session_state.get(MEDIA_S3_STORYBOARD, MEDIA_S3_STORYBOARD_SAMPLE)
    edited = st.data_editor(rows, num_rows="dynamic", hide_index=True, width="stretch",
                            key=f"media-s3-storyboard-editor-{st.session_state.get('media-s3-storyboard-ver', 0)}")
    if list(edited) != rows or not st.session_state.get(MEDIA_S3_STORYBOARD):
        media_s3_store_json(MEDIA_S3_STORYBOARD, list(edited))   # 고친 표를 폴더에도 저장
    st.session_state[MEDIA_S3_STORYBOARD] = list(edited)
    hits = media_s3_forbidden_hits(st.session_state[MEDIA_S3_STORYBOARD], report)
    if hits:
        st.warning("스토리보드에 금지 표현이 있어요: " + ", ".join(hits))
    done = st.session_state.get(MEDIA_S3_STORYBOARD_DONE)
    st.button("스토리보드 확정", key="media-s3-btn-storyboard-done", type="primary", on_click=_media_s3_confirm_storyboard)
    if done is not None and done != st.session_state[MEDIA_S3_STORYBOARD]:
        st.caption("확정한 뒤 표가 바뀌었어요. 영상 프롬프트에 반영하려면 다시 확정해 주세요.")


def media_s3_video_section(src: dict):
    """④-2 영상 초안 제작의 2단계: 확정한 스토리보드로 만든 영상 프롬프트로 짧은 초안 영상을 만듭니다."""
    st.markdown("**2단계 · 영상 초안 만들기** (Higgsfield)")
    storyboard = st.session_state.get(MEDIA_S3_STORYBOARD_DONE)
    if storyboard is None:
        st.info("먼저 위에서 스토리보드를 확정해 주세요. 확정한 장면으로 영상 프롬프트를 만들어요.")
        return
    route = media_s3_video_ready()   # "mcp"(계정 로그인, 구독 크레딧) / "api"(HF_KEY) / ""
    ready = bool(route)
    prompt = media_s3_video_prompt(src, storyboard)
    with st.container(border=True):
        st.markdown("**영상 프롬프트** (확정한 스토리보드에서 자동으로 만듦)")
        st.code(prompt, language=None, wrap_lines=True)
        if st.button("영상 초안 만들기", key="media-s3-btn-video", type="primary",
                     disabled=not ready or bool(st.session_state.get(MEDIA_S3_VIDEO_JOB)),
                     help=("터미널에서 python -m modules.media.media_stage3.media_stage3_hf_login 을 한 번 실행해 "
                           "Higgsfield 계정으로 로그인하면 구독 크레딧으로 만들 수 있어요." if not ready else
                           "Higgsfield 계정(구독 크레딧)으로 만들어요. 완성까지 1~5분" if route == "mcp" else
                           "Higgsfield API 잔액으로 만들어요. 완성까지 1~5분")):
            if route == "mcp":
                try:
                    job_id = media_s3_hf_submit(prompt, MEDIA_S3_VIDEO_SECONDS, MEDIA_S3_VIDEO_ASPECT)
                    st.session_state[MEDIA_S3_VIDEO_JOB] = {"job_id": job_id, "prompt": prompt}
                    media_s3_store_json(MEDIA_S3_VIDEO_JOB, st.session_state[MEDIA_S3_VIDEO_JOB])
                except MediaS3HFError as err:
                    st.warning(str(err))
                except Exception as err:   # 네트워크 등 예상 못 한 오류도 화면을 멈추지 않게
                    st.warning(f"영상 요청 중 오류가 났어요: {err}")
            else:
                status = st.empty()
                with st.spinner("영상 초안을 만드는 중이에요 (1~5분, 창을 닫지 마세요)"):
                    try:
                        media_s3_put_file(MEDIA_S3_VIDEOS, "video_draft_ai.mp4",
                                          media_s3_make_video(prompt, on_status=lambda t: status.caption(f"진행: {t}")))
                        st.toast("영상 초안을 작업 공간에 넣었어요", icon="🎬")
                    except MediaS3AIError as err:
                        st.warning(str(err))
                    finally:
                        status.empty()
    media_s3_video_job_step()
    media_s3_latest_video()


def media_s3_latest_video():
    """방금 만든 영상(가장 최근 AI 영상)을 영상 만들기 바로 아래에 크게 보여 줍니다. 완성되면 자동 재생."""
    made = [(n, c) for n, c in st.session_state.get(MEDIA_S3_VIDEOS, []) if "_ai." in n]
    if not made:
        return
    name, content = made[-1]
    fresh = st.session_state.pop("media-s3-video-fresh", False)   # 방금 완성됐으면 자동 재생
    with st.container(border=True, key="media-s3-latest-video"):
        st.markdown(f"**🎬 방금 만든 영상** · {name}")
        try:
            st.video(content, autoplay=fresh, muted=fresh)   # 브라우저는 소리 없이만 자동 재생을 허용
        except Exception:
            st.caption("영상을 재생할 수 없어요. 아래 작업 공간에서 내려받아 확인해 주세요.")


def _media_s3_clear_job() -> None:
    st.session_state.pop(MEDIA_S3_VIDEO_JOB, None)
    media_s3_store_json(MEDIA_S3_VIDEO_JOB, None)


@st.fragment(run_every=10)
def media_s3_video_job_step():
    """만드는 중인 영상이 있으면 10초마다 상태를 보고, 완성되면 작업 공간에 넣습니다 (다른 탭에 다녀와도 이어짐)."""
    job = st.session_state.get(MEDIA_S3_VIDEO_JOB)
    if not job:
        return
    try:
        status, url = media_s3_hf_check(job["job_id"])
    except Exception as err:
        st.caption(f"영상 상태를 확인하지 못했어요 (10초 뒤 다시 확인): {err}")
        return
    if status == "completed" and url:
        name = f"video_{job['job_id'][:8]}_ai.mp4"
        try:
            media_s3_put_file(MEDIA_S3_VIDEOS, name, media_s3_hf_download(url))
        except MediaS3HFError as err:
            st.warning(str(err))
            return
        links = {**st.session_state.get(MEDIA_S3_VIDEO_LINKS, {}), name: {"job_id": job["job_id"], "url": url}}
        st.session_state[MEDIA_S3_VIDEO_LINKS] = links
        media_s3_store_json(MEDIA_S3_VIDEO_LINKS, links)
        _media_s3_clear_job()
        st.session_state["media-s3-video-fresh"] = True
        st.toast("영상 초안이 완성됐어요. 바로 아래에서 재생돼요", icon="🎬")
        st.rerun()   # 작업 공간을 다시 그려 영상이 바로 보이게
    elif status == "ip_detected":
        st.warning("Higgsfield가 저작권 확인을 기다리고 있어요. Higgsfield 사이트 기록(History)에서 이 영상을 열어 확인을 눌러 주세요. "
                   "확인하면 여기에 자동으로 들어와요.")
    elif status == "not_found":
        _media_s3_clear_job()
        st.warning("Higgsfield에 이 작업이 없어요 (요청이 영상으로 이어지지 않았어요). '영상 초안 만들기'를 다시 눌러 주세요.")
    elif status in ("failed", "canceled", "cancelled", "nsfw", "error"):
        _media_s3_clear_job()
        st.warning(f"영상이 만들어지지 않았어요 ({status}). 프롬프트를 바꿔 다시 눌러 주세요.")
    else:
        st.info(f"🎬 영상을 만드는 중이에요 ({status or '대기'}). 보통 3~5분 걸려요. 다른 탭에 다녀와도 계속 만들어지고, "
                "완성되면 아래 작업 공간에 자동으로 들어가요.")


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
    media_s3_store_load()   # 탭을 옮기거나 새로고침해도 작업물이 남게 폴더에서 다시 읽음
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
        media_s3_storyboard_section(src)
        media_s3_video_section(src)
        media_s3_workspace("영상", MEDIA_S3_VIDEOS, "media-s3-video-files", ["mp4", "mov"], cols=2)
    media_s3_handoff_step()
