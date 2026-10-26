# 3. 매체 제작 > 3단계 ④: 사진·영상 초안 제작 (3단계 담당 · DH 브랜치)
# 2단계가 다듬어 넘긴 프롬프트(media_handoff_prompt())로
# 하위 탭 2개로 나눠 사진 초안 A·B(프롬프트 A·B로 생성)와 영상 초안(스토리보드 확정 → 영상 프롬프트로 생성)을 만듭니다. '⑤로 넘기기' 버튼을 누르면 ⑤ 외주 정리(media_stage3_export.py)가 받아 묶습니다.
# 화면은 media_stage3_render() 안에서만 그립니다.
# 이름 규칙: 함수 media_s3_..., 위젯 key·session_state 키·CSS class media-s3-...
import base64
import hashlib
import html
import time
from pathlib import Path

import streamlit as st

from common.common_store import store_get
from modules.media.media_stage3.media_stage3_hf_login import (media_s3_hf_login_start, media_s3_hf_login_status,
                                                               media_s3_hf_logout)
from modules.media.media_stage3.media_stage3_hf_mcp import (MediaS3HFError, media_s3_hf_check, media_s3_hf_download,
                                                           media_s3_hf_submit)
from modules.media.media_stage3.media_stage3_ai import (MEDIA_S3_VIDEO_ASPECT, MEDIA_S3_VIDEO_SECONDS, MediaS3AIError, media_s3_ai_ready, media_s3_forbidden_hits,
                                                       media_s3_make_image, media_s3_make_storyboard, media_s3_make_video,
                                                       media_s3_translate,
                                                       media_s3_video_ready)
from modules.media.media_stage3.media_stage3_store import (MEDIA_S3_HISTORY_KEEP, media_s3_store_file,
                                                          media_s3_store_history_add,
                                                          media_s3_store_history_groups,
                                                          media_s3_store_history_read, media_s3_store_history_remove,
                                                          media_s3_store_json,
                                                          media_s3_store_load)
from modules.media.media_handoff import (media_handoff_plan, media_handoff_assets, media_handoff_check, media_handoff_prompt,
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
MEDIA_S3_GROUP = "media-s3-group"               # 지금 가설 묶음 {"id", "hypothesis", "variable", "a", "b"}
MEDIA_S3_FILE_GROUP = "media-s3-file-group"     # 작업 공간 파일 이름 → 만든 가설 묶음 id
MEDIA_S3_HISTORY = "media-s3-history"           # 만든 결과 기록 목록
MEDIA_S3_PICK = "media-s3-pick"                 # ⑤로 보내려고 고른 기록(file) 목록 ('만든 결과 보기'의 체크)
MEDIA_S3_NOTES = "media-s3-notes"               # 위쪽 알림(예시 프롬프트 등) → 각 탭 아래 안내 줄에 붙임
MEDIA_S3_PHOTO_IDX = "media-s3-photo-idx"       # 사진 넘겨 보기에서 지금 보는 사진 번호
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


def media_s3_group(src: dict) -> dict:
    """지금 가설 묶음: 2단계 프롬프트 A·B가 같으면 같은 묶음. 만든 결과를 '무슨 가설로 만들었는지'로 나누는 기준."""
    plan = media_handoff_plan()
    saved = store_get("hypothesis")
    hypothesis = str(saved.get("text") or saved.get("hypothesis") or "").strip() if isinstance(saved, dict) else ""
    gid = hashlib.sha1(f"{src['prompt_a']}|{src['prompt_b']}".encode("utf-8")).hexdigest()[:8]
    return {"id": gid, "hypothesis": hypothesis, "variable": src.get("variable") or plan.get("variable", ""),
            "a": plan.get("a", ""), "b": plan.get("b", "")}


def media_s3_put_file(key: str, name: str, content: bytes, prompt: str = "") -> None:
    """(이름, 내용)을 작업 공간에 넣습니다. 같은 이름이 있으면 바꿔 끼우고, 지금 가설 묶음과 만든 결과 기록에도 남깁니다."""
    old = dict(st.session_state.get(key, []))
    group = st.session_state.get(MEDIA_S3_GROUP) or {"id": ""}
    if old.get(name) == content and st.session_state.get(MEDIA_S3_FILE_GROUP, {}).get(name) == group["id"]:
        return   # 같은 파일을 다시 넣는 경우 (올리기 칸은 화면마다 다시 들어옴)
    st.session_state[key] = [f for f in st.session_state.get(key, []) if f[0] != name] + [(name, content)]
    media_s3_store_file(key, name, content)   # 탭을 옮기거나 새로고침해도 남게 폴더에도 저장
    file_group = {**st.session_state.get(MEDIA_S3_FILE_GROUP, {}), name: group["id"]}
    st.session_state[MEDIA_S3_FILE_GROUP] = file_group
    media_s3_store_json(MEDIA_S3_FILE_GROUP, file_group)
    # 기록 이름은 만든 시각_가설 묶음_파일 이름 (같은 초에 같은 이름을 만들어도 겹치지 않게 번호를 붙임)
    used = {e["file"] for e in st.session_state.get(MEDIA_S3_HISTORY) or []}
    file, n = f"{time.strftime('%Y%m%d_%H%M%S')}_{group['id']}_{name}", 1
    while file in used:
        n += 1
        file = f"{time.strftime('%Y%m%d_%H%M%S')}_{group['id']}_{n}_{name}"
    entry = {"file": file, "name": name, "kind": "사진" if key == MEDIA_S3_PHOTOS else "영상",
             "ai": "_ai." in name, "created": time.strftime("%Y-%m-%d %H:%M"), "prompt": prompt, "group": group}
    replaced = {e["file"] for e in st.session_state.get(MEDIA_S3_HISTORY) or []
                if e["name"] == name and e["group"].get("id") == group["id"]}
    media_s3_store_history_add(entry, content)
    if MEDIA_S3_PICK in st.session_state:   # 직접 고른 적이 있으면: 새로 만든 것은 넣고, 같은 이름으로 바뀐 예전 것은 뺌
        media_s3_set_pick([f for f in st.session_state[MEDIA_S3_PICK] if f not in replaced] + [entry["file"]])
    # 고른 적이 없으면 media_s3_pick()이 지금 가설로 만든 결과(같은 이름은 최신)를 자동으로 고른 것으로 봄


def media_s3_current(key: str) -> list:
    """작업 공간 파일 중 지금 가설 묶음으로 만든 것만 (예전 가설 것은 '만든 결과 보기' 탭에서 봄)."""
    gid = (st.session_state.get(MEDIA_S3_GROUP) or {}).get("id")
    file_group = st.session_state.get(MEDIA_S3_FILE_GROUP, {})
    return [f for f in st.session_state.get(key, []) if file_group.get(f[0], gid) == gid]


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


@st.dialog("자세히 보기", width="large")
def media_s3_text_dialog(title: str, text: str, note: str = ""):
    """'프롬프트 보기' 버튼으로 여는 팝업 창: 긴 글 전체 (오른쪽 위 복사 버튼으로 복사) + 아래 한국어 번역."""
    st.markdown(f"**{title}**")
    if note:
        st.caption(note)
    st.code(text, language=None, wrap_lines=True)
    st.markdown("**한국어 번역** · 이해용 (AI가 쓰는 건 위 영어 원문)")
    if not media_s3_ai_ready("OPENAI_API_KEY"):
        st.caption("secrets.toml에 OPENAI_API_KEY를 넣으면 번역이 보여요.")
        return
    with st.spinner("번역하는 중이에요"):
        try:
            st.code(media_s3_translate(text), language=None, wrap_lines=True)
        except MediaS3AIError as err:
            st.caption(str(err))


def media_s3_storyboard_rows(rows: list) -> list:
    """스토리보드 표에서 빈 줄(표의 '새 줄 추가' 칸 등, 값이 모두 비었거나 None)을 빼고 None은 빈칸으로."""
    clean = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        r = {k: ("" if v is None else v) for k, v in r.items()}
        if any(str(v).strip() for v in r.values()):
            clean.append(r)
    return clean


@st.dialog("스토리보드 크게 보기", width="large")
def media_s3_storyboard_dialog(rows: list, note: str = ""):
    """'크게 보기' 버튼으로 여는 팝업 창: 스토리보드 표 전체를 칸 안 줄바꿈으로 한 번에 (빈 줄·None 없이, 잘리지 않게).
    고치기는 화면의 표에서 합니다."""
    if note:
        st.caption(note)
    rows = media_s3_storyboard_rows(rows)
    if not rows:
        st.caption("표가 비어 있어요.")
        return
    order = ["장면", "길이(초)", "화면", "움직임", "자막", "피할 것"]   # 저장하면서 칸 순서가 섞여도 늘 이 순서로
    cols = [c for c in order if c in rows[0]] + [c for c in rows[0] if c not in order]
    head = "".join(f"<th>{html.escape(str(c))}</th>" for c in cols)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(r.get(c, '')))}</td>" for c in cols) + "</tr>" for r in rows)
    st.markdown(f'<table class="media-s3-sb-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>',
                unsafe_allow_html=True)


MEDIA_S3_GUIDE = {
    "photo": """**이 탭은 뭐 하는 곳?**
외주 촬영 업체에 "이렇게 찍어 주세요"를 보여 줄 **견본 사진**을 AI로 만드는 곳이에요.

**왜 하나요?**
A/B 테스트는 사진 A와 B가 **딱 한 가지(단일 변수)만** 달라야 어느 쪽이 더 잘 팔리는지 알 수 있어요.
말로 설명하는 것보다 견본 사진을 보여 주면 업체가 정확히 찍어요.

**순서**
1. **사진 A 만들기 → 사진 B 만들기** (프롬프트는 2단계에서 넘어온 문장, '프롬프트 보기'에 한국어 번역)
2. 팝업에서 확인 → 마음에 안 들면 다시 만들기 (예전 것은 '만든 결과 보기'에 남아요)
3. **⑤로 넘기기** → ⑤ 외주 정리에서 PDF·zip으로 받기

※ AI 사진은 아마존 메인 이미지로 쓰지 않아요 (촬영 참고용).""",
    "video": """**이 탭은 뭐 하는 곳?**
외주 업체에 보낼 **짧은 상품 영상의 설계도(스토리보드)**를 만들고, 그 설계도로 **초안 영상**을 AI로 만들어 보는 곳이에요.

**왜 하나요?**
영상은 장면 순서·길이·자막을 먼저 정해 둬야 업체와 오해가 없어요.
**문제 → 해결 → 증거 → 신뢰 → 마무리** 순서로 "왜 이 패드를 사야 하는지" 보여 줘요.

**순서**
1. **스토리보드 만들기** (AI가 리포트 값으로 채움) → 표에서 직접 고치기
2. **스토리보드 확정** (오른쪽 영상 프롬프트가 이 표로 만들어져요)
3. **영상 초안 만들기** (Higgsfield, 3~5분) → 다 되면 '만든 결과 보기'에서 확인

**표시 뜻**: 확정됨 = 지금 표로 영상을 만듦 · 다시 확정 필요 = 표가 바뀜, 확정을 다시 눌러야 반영 · 금지 표현 있음 = 리포트 금지어가 들어 있음""",
    "history": """**이 탭은 뭐 하는 곳?**
지금까지 만든 사진·영상을 **가설별로 모아 보는 곳**이에요. 최근 가설 5개까지 저장돼요.

**보는 법**
1. 왼쪽에서 **가설**을 고르면 오른쪽에 그 가설의 **사진 A | 사진 B | 영상**이 나와요
2. 같은 칸에 여러 장 만들었으면 **‹ ›** 로 넘겨 봐요 (2/3 = 3장 중 두 번째)
3. 외주에 보낼 것만 **⑤로 보내기** 체크 → 아래 **⑤로 넘기기**
4. 필요 없는 것은 🗑로 하나씩 지워요""",
    "export": """**이 탭은 뭐 하는 곳?**
외주 촬영 업체(또는 사내 촬영팀)에 보낼 자료를 **한 번에 묶는 곳**이에요.

**무엇이 들어가나요?**
- **외주_촬영_브리프.pdf**: 검증할 가설, A·B에서 바꾸는 것, 촬영 지시(찍지 말 것·넣을 것), 프롬프트 A·B, 영상 스토리보드
- **photo_reference/**: ④에서 '⑤로 보내기'로 고른 사진
- **video_draft/**: ④에서 고른 영상

**순서**: ④에서 '⑤로 넘기기' → 여기서 **zip 다운로드** → 업체에 전달""",
}


def media_s3_guide(kind: str, compact: bool = False) -> None:
    """처음 보는 사람용 '이 탭 사용법' 팝오버 버튼 (무엇을·왜·순서). compact면 ❓ 아이콘만 (좁은 칸용)."""
    with st.popover("" if compact else "이 탭 사용법", icon=":material/help:", help="이 탭 사용법" if compact else None):
        st.markdown(MEDIA_S3_GUIDE[kind])


def media_s3_notice(text: str) -> str:
    """탭 아래 안내 줄: 알림이 있으면 주황색으로 앞에 붙이고, 없으면 기본 안내만."""
    notes = st.session_state.get(MEDIA_S3_NOTES) or []
    return " · ".join(f":orange[{n}]" for n in notes) + (" · " if notes else "") + text


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


def _media_s3_photo_move(step: int, count: int) -> None:
    """사진 넘기기 ← → 버튼 콜백 (끝에서 넘기면 처음으로)."""
    st.session_state[MEDIA_S3_PHOTO_IDX] = (st.session_state.get(MEDIA_S3_PHOTO_IDX, 0) + step) % count


def media_s3_photo_list() -> list:
    """넘겨 보기 순서: AI 사진 A, B 먼저, 그다음 직접 올린 사진 (올린 순서대로)."""
    kept = media_s3_current(MEDIA_S3_PHOTOS)
    return sorted(kept, key=lambda f: (0, f[0]) if f[0].startswith("photo_") and "_ai." in f[0] else (1, ""))


def _media_s3_photo_jump(name: str) -> None:
    """방금 만들거나 올린 사진을 넘겨 보기에서 바로 보이게 합니다."""
    names = [n for n, _ in media_s3_photo_list()]
    if name in names:
        st.session_state[MEDIA_S3_PHOTO_IDX] = names.index(name)


def media_s3_photo_label(name: str, names: list) -> str:
    """넘겨 보기에서 부르는 이름: AI로 만든 photo_A_ai.png → '사진 A', 직접 올린 것 → '올림 1', '올림 2' …"""
    if name.startswith("photo_") and "_ai." in name:
        return "사진 " + name[len("photo_"):name.index("_ai.")]
    uploaded = [n for n in names if not (n.startswith("photo_") and "_ai." in n)]
    return f"올림 {uploaded.index(name) + 1}"


def media_s3_photo_frame(name: str, content: bytes) -> str:
    """사진을 3:2 틀에 꽉 채워 넣는 HTML (어느 사진인지는 아래 '사진 A / 사진 B' 고르기에 표시)."""
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "webp": "webp"}.get(name.rsplit(".", 1)[-1].lower(), "png")
    return (f'<div class="media-s3-frame"><img alt="{name}" '
            f'src="data:image/{mime};base64,{base64.b64encode(content).decode()}"></div>')


def _media_s3_photo_view() -> None:
    """아래 '사진 A / 사진 B …' 고르기 콜백: 고른 사진으로 넘깁니다."""
    picked = st.session_state.get("media-s3-photo-view")
    labels = st.session_state.get("media-s3-photo-view-labels", [])
    if picked in labels:
        st.session_state[MEDIA_S3_PHOTO_IDX] = labels.index(picked)


def media_s3_photo_carousel():
    """작업 공간 사진을 한 장씩 넘겨 봅니다. 사진이 카드 전체를 채우고 ← → 버튼은 사진 위 양옆에,
    아래 '사진 A / 사진 B'로 바로 골라 볼 수 있습니다. 여기 사진이 기본으로 ⑤에 갑니다."""
    kept = media_s3_photo_list()
    if not kept:
        st.markdown('<div class="media-s3-frame media-s3-frame-empty">아직 사진이 없어요.<br>'
                    '사진 A·B 만들기를 누르거나 직접 올려 주세요.</div>', unsafe_allow_html=True)
        return
    names = [n for n, _ in kept]
    labels = [media_s3_photo_label(n, names) for n in names]
    idx = st.session_state.get(MEDIA_S3_PHOTO_IDX, 0) % len(kept)
    st.session_state[MEDIA_S3_PHOTO_IDX] = idx
    name, content = kept[idx]
    with st.container(key="media-s3-carousel"):
        st.markdown(media_s3_photo_frame(name, content), unsafe_allow_html=True)
        st.button("←", key="media-s3-prev", on_click=_media_s3_photo_move, args=(-1, len(kept)),
                  disabled=len(kept) < 2)
        st.button("→", key="media-s3-next", on_click=_media_s3_photo_move, args=(1, len(kept)),
                  disabled=len(kept) < 2)
    st.session_state["media-s3-photo-view-labels"] = labels
    st.session_state["media-s3-photo-view"] = labels[idx]   # ← →로 넘겨도 아래 고르기가 같이 바뀌게
    with st.container(horizontal=True, vertical_alignment="center", key="media-s3-carousel-info"):
        st.segmented_control("볼 사진", labels, key="media-s3-photo-view", on_change=_media_s3_photo_view,
                             label_visibility="collapsed")
        st.space("stretch")
        with st.container(horizontal=True, gap="small", width="content", key="media-s3-photo-tools"):
            st.download_button("", content, file_name=name, key=f"media-s3-photo-files-dl-{name}", type="tertiary",
                               icon=":material/download:", help=f"{name} 내려받기")
            st.button("", key=f"media-s3-photo-files-rm-{name}", type="tertiary", icon=":material/delete:",
                      help=f"{name} 지우기", on_click=_media_s3_remove_file,
                      args=(MEDIA_S3_PHOTOS, name, "media-s3-photo-files"))


@st.dialog("만든 사진", width="large")
def media_s3_photo_dialog():
    """만든 사진 팝업 창: 넘겨 보기(← →, 사진 A/B 고르기, 내려받기·지우기). 오른쪽 위 X나 Esc로 닫고,
    '만든 사진 보기' 버튼으로 언제든 다시 엽니다."""
    with st.container(key="media-s3-photo-dialog"):
        media_s3_photo_carousel()


def _media_s3_photo_open_first(made: str) -> None:
    """방금 만든 사진을 팝업으로 보여 줄 때 처음 보일 사진: A가 있으면 A부터 (→로 B), 없으면 방금 만든 것."""
    names = [n for n, _ in media_s3_photo_list()]
    _media_s3_photo_jump("photo_A_ai.png" if "photo_A_ai.png" in names else made)


def media_s3_photo_section(src: dict):
    """④-1 사진 초안 제작: 사진 A·B 프롬프트 칸이 메인 (화면 폭 전체, 남는 높이만큼 프롬프트 칸이 커짐).
    사진을 만들면 팝업 창(media_s3_photo_dialog)으로 바로 보여 주고(A가 있으면 A부터, →로 B), X로 닫은 뒤에도
    '만든 사진 보기'로 다시 엽니다. 100% 화면에서 스크롤 없이 한 화면 (크기 계산은 media_stage3_style.css의 --media-s3-h)."""
    ready = media_s3_ai_ready("OPENAI_API_KEY")
    open_dialog = False
    with st.container(key="media-s3-photo-row"):
        left = st.container(key="media-s3-photo-left")
    with left:
        for col, name in zip(st.columns(2), ("A", "B")):
            prompt = src[f"prompt_{name.lower()}"]
            with col, st.container(border=True, key=f"media-s3-photo-card-{name}"):
                with st.container(horizontal=True, vertical_alignment="center"):
                    st.markdown(f"**사진 {name}**")
                    if st.button("프롬프트 보기", key=f"media-s3-btn-view-{name}", icon=":material/open_in_new:"):
                        media_s3_text_dialog(f"사진 {name} 프롬프트", prompt,
                                             f"{name}만 다른 점: {src[f'slot_{name.lower()}']} · {src['variable']}")
                    clicked = st.button(f"사진 {name} 만들기", key=f"media-s3-btn-photo-{name}", type="primary",
                                        disabled=not ready, help=media_s3_ai_help(ready, "사진")
                                        or "OpenAI 이미지 AI로 만들어요. 다시 누르면 새 사진으로 바꿔요")
                st.markdown(f'<div class="media-s3-prompt">{html.escape(prompt)}</div>', unsafe_allow_html=True)
                slot = html.escape(src[f"slot_{name.lower()}"])
                st.markdown(f'<div class="media-s3-slot" title="{slot}"><b>{name}만 다른 점</b> · {slot}'
                            f'<span>{html.escape(src["variable"])}</span></div>', unsafe_allow_html=True)
                if clicked:
                    with st.spinner(f"사진 {name}를 만드는 중이에요 (10~30초)"):
                        try:
                            media_s3_put_file(MEDIA_S3_PHOTOS, f"photo_{name}_ai.png", media_s3_make_image(prompt),
                                              prompt=prompt)
                            _media_s3_photo_open_first(f"photo_{name}_ai.png")
                            open_dialog = True   # 다 그린 뒤 팝업으로 보여 줌
                        except MediaS3AIError as err:
                            st.warning(str(err))
        # 만든 사진 보기 · 사용법 · ⑤로 넘기기를 한 줄에 (아래 줄을 따로 두지 않아 화면 높이를 아낌)
        # '직접 만든 사진 올리기'는 AI 만들기에 쓰이지 않고 보관만 돼 헷갈려서 뺌 (영상 탭 올리기는 시연용으로 남김)
        with st.container(horizontal=True, vertical_alignment="center", key="media-s3-photo-actions"):
            count = len(media_s3_current(MEDIA_S3_PHOTOS))
            if st.button(f"만든 사진 보기 ({count})", key="media-s3-btn-view-photos", icon=":material/photo_library:",
                         disabled=not count):
                open_dialog = True
            media_s3_guide("photo")
            media_s3_handoff_step("photo")
        st.caption(media_s3_notice("AI 사진은 아마존 메인 이미지로 쓰지 않아요 (외주 촬영 레퍼런스·서브 이미지·광고 초안용)"),
                   help=MEDIA_S3_MEDIA_NOTE)
    if open_dialog:
        media_s3_photo_dialog()


def _media_s3_confirm_storyboard() -> None:
    """'스토리보드 확정' 버튼 콜백. 지금 표를 확정본으로 보관합니다."""
    st.session_state[MEDIA_S3_STORYBOARD_DONE] = media_s3_storyboard_rows(  # 빈 줄은 빼고 확정 (영상 프롬프트·PDF에 None이 안 들어가게)
        st.session_state.get(MEDIA_S3_STORYBOARD, MEDIA_S3_STORYBOARD_SAMPLE))
    media_s3_store_json(MEDIA_S3_STORYBOARD_DONE, st.session_state[MEDIA_S3_STORYBOARD_DONE])


def media_s3_storyboard_section(src: dict):
    """④-2 영상 초안 제작 왼쪽 칸: 문제 → 해결 → 증거 → 신뢰 → 마무리 틀로 스토리보드를 만들고 확정합니다.
    제목 줄에 '스토리보드 만들기'·'스토리보드 확정'을 같이 두고, 표 높이는 화면 높이를 따라갑니다 (스크롤 없이 한 화면)."""
    report = store_get("report") or {}
    claims = report.get("ad_claims") or {}
    ready = media_s3_ai_ready("OPENAI_API_KEY")
    done = st.session_state.get(MEDIA_S3_STORYBOARD_DONE)
    with st.container(horizontal=True, vertical_alignment="center", key="media-s3-sb-head"):
        title = st.empty()   # 제목·배지는 표를 그린 뒤 채움 (고친 표 기준으로 확정됨/다시 확정 필요/금지 표현)
        st.space("stretch")
        view = st.empty()    # '크게 보기'도 표를 그린 뒤 채움
        make = st.button("스토리보드 만들기", key="media-s3-btn-storyboard", type="primary", disabled=not ready,
                         help=media_s3_ai_help(ready, "스토리보드") or "리포트 값(허용 장면·쓸 수 있는 문구·금지 표현)으로 장면을 채워요")
        confirm = st.empty()   # '스토리보드 확정'은 표를 그린 뒤에 채움 (고친 표를 확정하려고)
    if make:
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
    confirm.button("스토리보드 확정", key="media-s3-btn-storyboard-done", type="primary",
                   on_click=_media_s3_confirm_storyboard, help="이 표로 오른쪽 영상 프롬프트를 만들어요")
    if view.button("크게 보기", key="media-s3-btn-view-sb", icon=":material/open_in_new:"):
        media_s3_storyboard_dialog(st.session_state[MEDIA_S3_STORYBOARD],
                                   "고치기는 화면의 표에서 해요. 다 고치면 '스토리보드 확정'을 눌러 주세요.")
    hits = media_s3_forbidden_hits(st.session_state[MEDIA_S3_STORYBOARD], report)
    badge, tip = "", []
    if hits:
        badge = " :red-badge[금지 표현 있음]"
        tip.append("금지 표현: " + ", ".join(hits))
    if done is not None and done == media_s3_storyboard_rows(st.session_state[MEDIA_S3_STORYBOARD]):
        badge += " :green-badge[확정됨]"
    elif done is not None:
        badge += " :orange-badge[다시 확정 필요]"
        tip.append("확정한 뒤 표가 바뀌었어요. 영상 프롬프트에 반영하려면 다시 확정해 주세요")
    if claims.get("allowed_scenes"):
        tip.append(f"리포트 허용 장면: {claims['allowed_scenes']}")
    title.markdown("**① 스토리보드**" + badge, help="  \n".join(tip) or None)


@st.fragment(run_every=3)
def media_s3_hf_login_section():
    """Higgsfield 계정 로그인 칸 (컴퓨터마다 처음 한 번). 버튼을 누르면 시크릿 창으로 로그인 화면이 뜨고,
    로그인을 마치면 3초 안에 알아채고 화면을 다시 그립니다. 앱을 자기 컴퓨터에서 켰을 때만 동작합니다."""
    status, info = media_s3_hf_login_status()
    if status == "done":
        if st.session_state.pop("media-s3-hf-logged-in", None) is False:
            st.rerun()   # 로그인 칸을 보던 중 방금 로그인됨 → 영상 만들기 버튼을 켜려고 화면 전체를 다시 그림
        with st.container(horizontal=True, vertical_alignment="center"):
            st.caption("✅ Higgsfield 로그인됨 (구독 크레딧)")
            st.space("stretch")
            if st.button("계정 바꾸기", key="media-s3-hf-logout", type="tertiary",
                         help="이 컴퓨터의 로그인을 지우고 다른 계정으로 다시 로그인해요"):
                media_s3_hf_logout()
                st.rerun()
        return
    st.session_state["media-s3-hf-logged-in"] = False   # 로그인 전 (로그인되면 위에서 화면을 다시 그림)
    with st.container(border=True, key="media-s3-hf-login"):
        st.markdown("**Higgsfield 로그인** (이 컴퓨터에서 처음 한 번)")
        st.caption("버튼을 누르면 시크릿 창으로 로그인 화면이 떠요. 구독(울트라) 계정으로 로그인하고 허용을 누르면 끝이에요.")
        if st.button("Higgsfield 로그인 창 열기", key="media-s3-hf-login-btn", type="primary"):
            try:
                media_s3_hf_login_start()
                status, info = media_s3_hf_login_status()
            except OSError:
                st.warning("로그인 준비 칸(8765번 포트)을 다른 프로그램이 쓰고 있어요. 터미널 로그인 창을 닫고 다시 눌러 주세요.")
            except Exception as err:
                st.warning(f"로그인 창을 열지 못했어요: {err}")
        if status == "waiting":
            st.info("로그인 창에서 로그인을 기다리는 중이에요. 창이 안 떴으면 아래 주소를 시크릿 창에 붙여 넣으세요.")
            st.code(info, language=None, wrap_lines=True)
        elif status == "error":
            st.warning(info)


def media_s3_video_section(src: dict):
    """④-2 영상 초안 제작 오른쪽 카드: 확정한 스토리보드로 만든 영상 프롬프트로 짧은 초안 영상을 만듭니다.
    만든 영상은 '만든 결과 보기'에서 봅니다 (이 탭에는 따로 보여 주지 않음)."""
    storyboard = st.session_state.get(MEDIA_S3_STORYBOARD_DONE)
    with st.container(horizontal=True, vertical_alignment="center", key="media-s3-video-head"):
        st.markdown("**② 영상 초안 만들기** · Higgsfield")
        st.space("stretch")
        if storyboard is not None and st.button("프롬프트 보기", key="media-s3-btn-view-video",
                                                icon=":material/open_in_new:"):
            media_s3_text_dialog("영상 프롬프트", media_s3_video_prompt(src, storyboard),
                                 "확정한 스토리보드 장면을 이어 붙여 자동으로 만든 프롬프트예요")
    if storyboard is None:
        st.markdown('<div class="media-s3-vprompt media-s3-vprompt-empty">왼쪽에서 스토리보드를 확정하면<br>'
                    '그 장면으로 영상 프롬프트를 만들어요.</div>', unsafe_allow_html=True)
        return
    media_s3_hf_login_section()
    route = media_s3_video_ready()   # "mcp"(계정 로그인, 구독 크레딧) / "api"(HF_KEY) / ""
    ready = bool(route)
    prompt = media_s3_video_prompt(src, storyboard)
    st.markdown(f'<div class="media-s3-vprompt">{html.escape(prompt)}</div>', unsafe_allow_html=True)
    with st.container():
        if st.button("영상 초안 만들기", key="media-s3-btn-video", type="primary", width="stretch",
                     disabled=not ready or bool(st.session_state.get(MEDIA_S3_VIDEO_JOB)),
                     help=("위 'Higgsfield 로그인 창 열기'로 로그인하면 구독 크레딧으로 만들 수 있어요." if not ready else
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
                                          media_s3_make_video(prompt, on_status=lambda t: status.caption(f"진행: {t}")),
                                          prompt=prompt)
                        st.toast("영상 초안이 완성됐어요. '만든 결과 보기'에서 볼 수 있어요", icon="🎬")
                    except MediaS3AIError as err:
                        st.warning(str(err))
                    finally:
                        status.empty()
    media_s3_video_job_step()


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
            media_s3_put_file(MEDIA_S3_VIDEOS, name, media_s3_hf_download(url), prompt=job.get("prompt", ""))
        except MediaS3HFError as err:
            st.warning(str(err))
            return
        links = {**st.session_state.get(MEDIA_S3_VIDEO_LINKS, {}), name: {"job_id": job["job_id"], "url": url}}
        st.session_state[MEDIA_S3_VIDEO_LINKS] = links
        media_s3_store_json(MEDIA_S3_VIDEO_LINKS, links)
        _media_s3_clear_job()
        st.toast("영상 초안이 완성됐어요. '만든 결과 보기'에서 볼 수 있어요", icon="🎬")
        st.rerun()   # 넘기기 줄의 보낼 개수 등을 다시 그림
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
        st.info(f"🎬 만드는 중 ({status or '대기'}) · 보통 3~5분. 다른 탭에 다녀와도 계속 만들어지고, "
                "완성되면 '만든 결과 보기'에 들어가요.")


def media_s3_set_pick(files: list) -> None:
    st.session_state[MEDIA_S3_PICK] = files
    media_s3_store_json(MEDIA_S3_PICK, files)


def media_s3_pick() -> list:
    """⑤로 보내려고 고른 기록(file) 목록. 아직 고른 적이 없으면 지금 가설로 만든 결과(같은 이름은 최신)를 고른 것으로 봄."""
    history = st.session_state.get(MEDIA_S3_HISTORY) or []
    alive = {e["file"] for e in history}
    if MEDIA_S3_PICK in st.session_state:
        return [f for f in st.session_state[MEDIA_S3_PICK] if f in alive]   # 5개 넘어 지워진 기록은 뺌
    gid = (st.session_state.get(MEDIA_S3_GROUP) or {}).get("id")
    latest = {}
    for e in history:
        if e["group"].get("id") == gid:
            latest[e["name"]] = e["file"]   # 기록은 만든 순서라 마지막이 최신
    return list(latest.values())


def _media_s3_toggle_pick(file: str) -> None:
    """'⑤로 보내기' 체크 콜백 (탭을 옮기면 체크 값이 지워져서 고른 목록을 따로 보관)."""
    picks = media_s3_pick()
    media_s3_set_pick([f for f in picks if f != file] if file in picks else picks + [file])


def media_s3_assets_value() -> dict:
    """⑤로 넘기는 값: 확정한 스토리보드와 '만든 결과 보기'에서 고른 사진·영상의 기록 이름 (모양은 MEDIA_HANDOFF_ASSETS_SAMPLE).
    파일 자체는 이 컴퓨터의 기록 폴더(data/workspace/history/)에 있고, ⑤가 이름으로 찾아 zip에 넣습니다."""
    kinds = {e["file"]: e["kind"] for e in st.session_state.get(MEDIA_S3_HISTORY) or []}
    picks = media_s3_pick()
    return {"storyboard": st.session_state.get(MEDIA_S3_STORYBOARD_DONE) or [],
            "photos": [f for f in picks if kinds.get(f) == "사진"],
            "videos": [f for f in picks if kinds.get(f) == "영상"]}


def _media_s3_handoff() -> None:
    """'⑤로 넘기기' 버튼 콜백. 확정한 스토리보드와 파일 이름을 ⑤로 넘깁니다 (Supabase에 저장)."""
    media_handoff_set_assets(media_s3_assets_value())
    st.session_state["media-s3-handoff-toast"] = True


MEDIA_S3_HANDOFF_HELP = ("**⑤로 넘기기란?** '만든 결과 보기'에서 '⑤로 보내기'를 체크한 사진·영상과 확정한 스토리보드를 "
                         "⑤ 외주 정리로 보내는 버튼이에요. ⑤에서는 넘긴 것만 PDF·zip으로 묶어요.  \n"
                         "**보낼 것**: 지금 체크된 사진·영상 수  \n"
                         "**다시 넘기기 필요**: 넘긴 뒤에 체크나 스토리보드가 바뀌었다는 뜻. 버튼을 다시 누르면 최신으로 바뀌어요  \n"
                         "**넘김 완료**: ⑤가 지금 내용 그대로 받고 있어요")


def media_s3_handoff_step(where: str) -> None:
    """넘기기 줄: 버튼을 눌러야만 ⑤ 외주 정리로 넘어갑니다. 넘기기 전 / 넘김 완료 / 바뀌어서 다시 넘겨야 함을 보여 줍니다.
    하위 탭마다 하나씩 그립니다(where = photo / video / history). 사진 탭은 짧게 줄여 왼쪽 칸에 넣습니다."""
    if st.session_state.pop("media-s3-handoff-toast", False):
        st.toast("사진·영상 초안을 ⑤ 외주 정리로 넘겼어요", icon="✅")
    saved, now = media_handoff_assets(), media_s3_assets_value()
    sent = not saved["sample"] and all(saved.get(k) == v for k, v in now.items())
    if sent:
        note = ":green-badge[✅ 넘김 완료] ⑤ 외주 정리가 이 스토리보드와 파일을 받아요"
    elif not saved["sample"]:
        note = ":orange-badge[다시 넘기기 필요] 넘긴 뒤 스토리보드나 고른 파일이 바뀌었어요. ⑤는 아직 이전 값을 받아요"
    else:
        note = "사진·영상 초안을 다 만들면 '⑤로 넘기기'를 눌러 주세요"
    count = f"보낼 것: 사진 {len(now['photos'])} · 영상 {len(now['videos'])}"
    if where in ("photo", "video"):   # 짧게: 이름표 + 보낼 개수 (자세한 설명은 버튼에 마우스를 올리면)
        note = note.split("]")[0] + "] " + count if "badge[" in note else count
    else:
        note += f" · {count} ('만든 결과 보기'에서 고르기)"
    ready = bool(now["storyboard"] or now["photos"] or now["videos"])   # 사진만 넘겨도 됨
    suffix = "" if where == "photo" else f"-{where}"
    with st.container(horizontal=True, vertical_alignment="center", key=f"media-s3-handoff-row{suffix}",
                      horizontal_alignment="right" if where in ("photo", "video") else "left"):
        st.markdown(note, help=MEDIA_S3_HANDOFF_HELP)
        if not sent:
            st.button("다시 넘기기" if not saved["sample"] else "⑤로 넘기기", key=f"media-s3-btn-handoff{suffix}",
                      type="primary", disabled=not ready, on_click=_media_s3_handoff,
                      help=None if ready else "사진·영상을 만들거나, '만든 결과 보기'에서 보낼 것을 골라 주세요")


def media_s3_history_migrate() -> None:
    """가설 기록을 남기기 전에 만든 작업 공간 파일을 지금 가설 묶음으로 기록합니다 (한 번만).
    방금까지 지금 가설로 만든 것이라 작업 공간에 그대로 두고, '만든 결과 보기'에도 보이게 합니다."""
    file_group = dict(st.session_state.get(MEDIA_S3_FILE_GROUP, {}))
    legacy = st.session_state.get(MEDIA_S3_GROUP) or {"id": ""}
    changed = False
    for key, kind in ((MEDIA_S3_PHOTOS, "사진"), (MEDIA_S3_VIDEOS, "영상")):
        for name, content in st.session_state.get(key, []):
            if name in file_group:
                continue
            file_group[name] = legacy["id"]
            changed = True
            media_s3_store_history_add({"file": f"before_{name}", "name": name, "kind": kind, "ai": "_ai." in name,
                                        "created": time.strftime("%Y-%m-%d %H:%M"), "prompt": "", "group": legacy}, content)
    if changed:
        st.session_state[MEDIA_S3_FILE_GROUP] = file_group
        media_s3_store_json(MEDIA_S3_FILE_GROUP, file_group)


MEDIA_S3_HIST_SLOTS = {"A": "사진 A", "B": "사진 B", "V": "영상", "U": "올린 사진"}   # 만든 결과 보기의 칸 (id → 이름)


def media_s3_history_slots(entries: list) -> dict:
    """한 가설의 결과를 칸별로 나눕니다: 사진 A / 사진 B / 영상 / 올린 사진 (칸마다 만든 순서, 마지막이 최신)."""
    slots = {k: [] for k in MEDIA_S3_HIST_SLOTS}
    for e in entries:   # 기록은 만든 순서대로 쌓이므로 그대로 (같은 분에 만든 것도 순서가 맞음)
        if e["kind"] == "영상":
            slots["V"].append(e)
        elif e["name"] == "photo_A_ai.png":
            slots["A"].append(e)
        elif e["name"] == "photo_B_ai.png":
            slots["B"].append(e)
        else:
            slots["U"].append(e)
    return slots


def _media_s3_history_delete(file: str) -> None:
    """'만든 결과 보기' 지우기 콜백: 기록과 사본을 지우고, ⑤로 보낼 목록에서도 뺍니다."""
    media_s3_store_history_remove(file)
    if MEDIA_S3_PICK in st.session_state:
        media_s3_set_pick([f for f in st.session_state[MEDIA_S3_PICK] if f != file])


def _media_s3_history_open(gid: str | None) -> None:
    """가설 기록을 열거나(gid) 목록으로 돌아갑니다(None)."""
    st.session_state["media-s3-hist-open"] = gid


def media_s3_history_tile(e: dict, picks: list, latest: bool, no: int, where: str = "card") -> None:
    """버전 하나 (사진 또는 영상): 미리 보기 + '⑤로 보내기' 체크 + 내려받기·프롬프트·지우기.
    where: 'card'(화면 칸) / 'dlg'(전부 보기 팝업). 같은 버전이 두 곳에 동시에 나와도 key가 겹치지 않게 붙임."""
    content = media_s3_store_history_read(e)
    k = f"{where}-{e['file']}"
    with st.container(key=f"media-s3-hist-tile-{k}", width="content"):
        if content is None:
            st.markdown('<div class="media-s3-hist-thumb media-s3-hist-empty">파일 없음</div>', unsafe_allow_html=True)
        elif e["kind"] == "사진":
            mime = {"jpg": "jpeg", "jpeg": "jpeg", "webp": "webp"}.get(e["name"].rsplit(".", 1)[-1].lower(), "png")
            st.markdown(f'<div class="media-s3-hist-thumb"><img alt="{html.escape(e["name"])}" '
                        f'src="data:image/{mime};base64,{base64.b64encode(content).decode()}"></div>',
                        unsafe_allow_html=True)
        else:
            with st.container(key=f"media-s3-hist-vid-{k}"):
                try:
                    st.video(content)
                except Exception:
                    st.caption("재생할 수 없는 파일이에요")
        with st.container(horizontal=True, vertical_alignment="center", gap="small",
                          key=f"media-s3-hist-foot-{k}"):
            # 체크 칸은 지난번 값을 기억하므로, 고른 목록(새로 만들면 예전 것은 빠짐)에 매번 맞춤
            pick_key = f"media-s3-pick-{e['file']}" if where == "card" else f"media-s3-pick-{k}"
            st.session_state[pick_key] = e["file"] in picks
            st.checkbox("⑤", key=pick_key, on_change=_media_s3_toggle_pick, args=(e["file"],),
                        help="체크하면 ⑤ 외주 정리로 보낼 것에 들어가요")
            st.caption(f"{no}번{' · 최신' if latest else ''} · {e['created'][5:]}")
            st.space("stretch")
            with st.container(horizontal=True, gap="small", width="content", key=f"media-s3-hist-tools-{k}"):
                if content is not None:
                    st.download_button("", content, file_name=e["name"], type="tertiary", icon=":material/download:",
                                       key=f"media-s3-hist-dl-{k}")
                if e.get("prompt"):
                    with st.popover("", icon=":material/description:"):
                        st.code(e["prompt"], language=None, wrap_lines=True)
                st.button("", key=f"media-s3-hist-rm-{k}", type="tertiary", icon=":material/delete:",
                          on_click=_media_s3_history_delete, args=(e["file"],))


def media_s3_history_items(gid: str, slot: str) -> list:
    """가설 묶음 gid의 칸(A·B·V) 버전 목록 (영상 칸에는 예전에 올린 사진도 같이). 지운 뒤에도 바로 맞게 기록에서 다시 읽음."""
    entries = [e for e in st.session_state.get(MEDIA_S3_HISTORY) or [] if e["group"].get("id") == gid]
    slots = media_s3_history_slots(entries)
    return slots["V"] + slots["U"] if slot == "V" else slots[slot]


@st.dialog("만든 결과 전부 보기", width="large")
def media_s3_history_dialog(gid: str, slot: str, title: str):
    """'사진 A 전부 보기' 팝업: 그 칸의 버전을 한 번에 (최신부터). 버전마다 ⑤로 보내기·내려받기·프롬프트·지우기."""
    items = media_s3_history_items(gid, slot)
    st.markdown(f"**{title}** · {len(items)}개 (최신부터)")
    if not items:
        st.caption("남은 결과가 없어요.")
        return
    picks = media_s3_pick()
    with st.container(key="media-s3-hist-dialog"):
        cols = st.columns(3)
        for k, (no, e) in enumerate(reversed(list(enumerate(items, start=1)))):
            with cols[k % 3]:
                media_s3_history_tile(e, picks, no == len(items), no, where="dlg")


@st.dialog("가설 크게 보기", width="large")
def media_s3_hypothesis_dialog(gid: str):
    """가설 기록 카드의 '크게 보기': 날짜, 가설 전문, 단일 변수, 사진 A·B, 만든 개수."""
    entries = [e for e in st.session_state.get(MEDIA_S3_HISTORY) or [] if e["group"].get("id") == gid]
    if not entries:
        st.caption("기록이 없어요.")
        return
    g = entries[-1]["group"]
    slots = media_s3_history_slots(entries)
    st.caption(f"{min(e['created'] for e in entries)} ~ {max(e['created'] for e in entries)}")
    st.markdown(f"### {g.get('hypothesis') or '가설 문장이 기록되지 않았어요'}")
    st.markdown(f"**단일 변수** {g.get('variable') or '-'}  \n**사진 A** {g.get('a') or '-'}  \n**사진 B** {g.get('b') or '-'}")
    st.caption(f"사진 A {len(slots['A'])}장 · 사진 B {len(slots['B'])}장 · 영상 {len(slots['V'])}개")


def _media_s3_history_step(key: str, step: int, count: int) -> None:
    """칸 안 ‹ › 버전 넘기기 (끝에서 넘기면 처음으로)."""
    st.session_state[key] = (st.session_state.get(key, count - 1) + step) % count


def media_s3_history_card(gid: str, slot: str, title: str, diff: str, picks: list, empty: str) -> None:
    """열었을 때 칸 하나 (사진 A / 사진 B / 영상): 한 장씩 크게, 맨 위 한 줄에 ‹ n/전체 › · ⑤ · 내려받기 · 지우기 · 전부 보기.
    그 사진만 다른 점은 사진 아래쪽에 띠로 얹어 높이를 더 쓰지 않음 (스크롤 없이 한 화면)."""
    items = media_s3_history_items(gid, slot)
    key = f"media-s3-hist-i-{gid}-{slot}"
    idx = st.session_state.get(key, len(items) - 1) % len(items) if items else 0   # 처음엔 최신
    e = items[idx] if items else None
    content = media_s3_store_history_read(e) if e else None
    tag = ""   # 다른 점은 사진을 가리지 않게 사진 아래 한 줄 글로 (맨 끝)
    with st.container(border=True, key=f"media-s3-hist-card-{slot}"):
        with st.container(horizontal=True, vertical_alignment="center", gap="small", key=f"media-s3-hist-cardhead-{slot}"):
            st.markdown(f"**{title}**")
            if items:
                st.button("", key=f"{key}-prev", icon=":material/chevron_left:", type="tertiary", disabled=len(items) < 2,
                          on_click=_media_s3_history_step, args=(key, -1, len(items)))
                st.caption(f"{idx + 1}/{len(items)}")   # 처음엔 최신(마지막 번호)이 보임
                st.button("", key=f"{key}-next", icon=":material/chevron_right:", type="tertiary", disabled=len(items) < 2,
                          on_click=_media_s3_history_step, args=(key, 1, len(items)))
            st.space("stretch")
            if e:
                st.session_state[f"media-s3-pick-{e['file']}"] = e["file"] in picks   # 체크 칸을 고른 목록에 맞춤
                st.checkbox("⑤", key=f"media-s3-pick-{e['file']}", on_change=_media_s3_toggle_pick, args=(e["file"],))
                with st.container(horizontal=True, gap="small", width="content", key=f"media-s3-hist-tools-card-{slot}"):
                    if content is not None:
                        st.download_button("", content, file_name=e["name"], type="tertiary", icon=":material/download:",
                                           key=f"media-s3-hist-dl-card-{e['file']}", help=f"{e['created'][5:]} · 내려받기")
                    st.button("", key=f"media-s3-hist-rm-card-{e['file']}", type="tertiary", icon=":material/delete:",
                              help="이 버전 지우기", on_click=_media_s3_history_delete, args=(e["file"],))
            if st.button("", key=f"media-s3-hist-all-{slot}", icon=":material/grid_view:", type="tertiary",
                         help=f"{title} 전부 보기", disabled=not items):
                media_s3_history_dialog(gid, slot, title)
        if not e:
            st.markdown(f'<div class="media-s3-hist-big media-s3-hist-empty">{empty}{tag}</div>', unsafe_allow_html=True)
        elif content is None:
            st.markdown(f'<div class="media-s3-hist-big media-s3-hist-empty">파일이 없어요{tag}</div>', unsafe_allow_html=True)
        elif e["kind"] == "사진":
            mime = {"jpg": "jpeg", "jpeg": "jpeg", "webp": "webp"}.get(e["name"].rsplit(".", 1)[-1].lower(), "png")
            st.markdown(f'<div class="media-s3-hist-big"><img alt="{html.escape(e["name"])}" '
                        f'src="data:image/{mime};base64,{base64.b64encode(content).decode()}">{tag}</div>',
                        unsafe_allow_html=True)
        else:
            with st.container(key=f"media-s3-hist-bigvid-{slot}"):
                try:
                    st.video(content)
                except Exception:
                    st.caption("재생할 수 없는 파일이에요")
        if diff:   # 사진 아래 한 줄 칩 (넘치면 …, 마우스를 올리면 전체)
            st.markdown(f'<div class="media-s3-hist-diff" title="{html.escape(diff)}">{html.escape(diff)}</div>',
                        unsafe_allow_html=True)


def media_s3_history_list(groups: list, gid_now: str, picks: list) -> None:
    """처음 화면: 가설 기록을 세로 카드로 나란히 (맨 위 날짜 → 가설 → 개수 → 크게 보기·열기)."""
    with st.container(horizontal=True, vertical_alignment="center", key="media-s3-hist-listhead"):
        st.markdown(f"**가설 기록** · 최근 {MEDIA_S3_HISTORY_KEEP}개 · '열기'를 누르면 그 가설로 만든 사진·영상이 보여요")
        st.space("stretch")
        media_s3_guide("history", compact=True)
    with st.container(horizontal=True, gap="medium", key="media-s3-hist-list"):
        for gid, entries in groups:
            g = entries[-1]["group"]
            slots = media_s3_history_slots(entries)
            picked = sum(e["file"] in picks for e in entries)
            with st.container(border=True, key=f"media-s3-hist-item-{gid}"):
                st.markdown(f'<div class="media-s3-hist-date">{max(e["created"] for e in entries)}'
                            f'{" · 🟢 지금 가설" if gid == gid_now else ""}</div>'
                            f'<div class="media-s3-hist-item-text">{html.escape(g.get("hypothesis") or g.get("variable") or "가설 기록 없음")}</div>'
                            f'<div class="media-s3-hist-meta">단일 변수 {html.escape(g.get("variable") or "-")}<br>'
                            f'사진 A {len(slots["A"])} · 사진 B {len(slots["B"])} · 영상 {len(slots["V"])}'
                            f'{f" · ✔ {picked}개 보냄" if picked else ""}</div>', unsafe_allow_html=True)
                with st.container(horizontal=True, key=f"media-s3-hist-itembtn-{gid}"):
                    if st.button("크게 보기", key=f"media-s3-hist-big-{gid}", icon=":material/open_in_new:"):
                        media_s3_hypothesis_dialog(gid)
                    st.button("열기", key=f"media-s3-hist-openbtn-{gid}", type="primary", icon=":material/chevron_right:",
                              icon_position="right", on_click=_media_s3_history_open, args=(gid,))


def media_s3_history_detail(gid: str, entries: list, picks: list) -> None:
    """가설 하나 열기: 사진 A | 사진 B | 영상 세 칸을 세로로 길게 나란히. 칸마다 한 장씩, ‹ ›로 다른 버전, '전부 보기' 팝업."""
    g = entries[-1]["group"]
    with st.container(horizontal=True, vertical_alignment="center", key="media-s3-hist-head"):
        st.button("가설 목록", key="media-s3-hist-back", type="primary", icon=":material/arrow_back:",
                  on_click=_media_s3_history_open, args=(None,))
        st.markdown(f"**단일 변수** {html.escape(g.get('variable') or '-')} · 사진 A와 사진 B는 이것만 달라요",
                    help=f"가설: {g['hypothesis']}" if g.get("hypothesis") else None)
    with st.container(horizontal=True, gap="medium", key="media-s3-hist-cols"):
        for slot, title in (("A", "사진 A"), ("B", "사진 B"), ("V", "영상")):
            diff = g.get(slot.lower(), "") if slot in ("A", "B") else ""
            media_s3_history_card(gid, slot, title, f"{title}만 다른 점: {diff}" if diff else "", picks,
                                  "아직 영상을 만들지 않았어요" if slot == "V" else f"아직 {title}를 만들지 않았어요")


def media_s3_history_section():
    """④-3 만든 결과 보기 (100% 화면에서 스크롤 없이): 처음엔 가설 기록 목록만 보이고, 하나를 누르면
    위 반반에 사진 A 버전들 | 사진 B 버전들, 아래에 영상이 나옵니다. 버전마다 ⑤로 보내기·내려받기·지우기."""
    history = st.session_state.get(MEDIA_S3_HISTORY) or []
    if not history:
        st.caption("아직 만든 결과가 없어요. 사진 초안 제작·영상 초안 제작에서 만들면 여기에 쌓여요.")
        return
    groups = media_s3_store_history_groups(history)[:MEDIA_S3_HISTORY_KEEP]
    by_id = dict(groups)
    gid_now = (st.session_state.get(MEDIA_S3_GROUP) or {}).get("id")
    picks = media_s3_pick()
    gid = st.session_state.get("media-s3-hist-open")
    with st.container(key="media-s3-hist-area"):
        if gid in by_id:
            media_s3_history_detail(gid, by_id[gid], picks)
        else:
            media_s3_history_list(groups, gid_now, picks)


def media_s3_video_tab(src: dict):
    """④-2 영상 초안 제작: 사진 초안 제작과 같은 배치. 왼쪽은 스토리보드 카드·직접 올리기·⑤로 넘기기,
    오른쪽은 사진 넘겨 보기와 같은 크기의 영상 만들기 카드. 100% 화면에서 스크롤 없이 한 화면 (--media-s3-h)."""
    with st.container(horizontal=True, gap="medium", key="media-s3-video-row"):
        left = st.container(key="media-s3-video-left")
        right = st.container(width="content", key="media-s3-video-right")
    with left:
        with st.container(border=True, key="media-s3-sb-card"):
            media_s3_storyboard_section(src)
        # '직접 만든 영상 올리기'는 사진 탭처럼 뺌 (만들기에 쓰이지 않고 보관만 돼 헷갈림)
        with st.container(horizontal=True, vertical_alignment="center", key="media-s3-video-actions"):
            media_s3_guide("video")
            media_s3_handoff_step("video")
        with st.container(key="media-s3-video-note"):   # 한 줄로만 (넘치면 …), 낮은 화면에서도 스크롤 없게
            st.caption(media_s3_notice("AI 영상은 아마존 메인 이미지로 쓰지 않아요 · 만든 영상은 '만든 결과 보기'에서 봐요"),
                       help=MEDIA_S3_MEDIA_NOTE)
    with right:
        with st.container(border=True, key="media-s3-video-card"):
            media_s3_video_section(src)


MEDIA_S3_SUB_TABS = ["사진 초안 제작", "영상 초안 제작", "만든 결과 보기"]   # ④ 안의 하위 탭 (순서대로 '다음'으로 이어짐)


def _media_s3_go(sub: str | None = None, step: str | None = None) -> None:
    """④ 이전/다음 버튼 콜백. sub는 ④ 안의 하위 탭, step은 ③ 매체 제작의 단계 탭(media_page.py의 key="media-step")."""
    if sub:
        st.session_state["media-s3-sub"] = sub
    if step:
        st.session_state["media-step"] = step   # media_page.py의 '이전/다음 단계' 버튼과 같은 방식


def media_s3_nav(i: int) -> None:
    """④ 하위 탭 맨 아래 이전/다음 버튼: 사진 → 영상 → 만든 결과 보기 → ⑤ 외주 정리 순서로 이어짐.
    ③ 공통 이전/다음 줄(media_page.py)은 ④에서 CSS로 숨기고 이 줄을 대신 씁니다 (같은 모양·같은 높이)."""
    from modules.media.media_page import MEDIA_STEPS   # 안에서 불러옴 (media_page가 이 파일을 불러서 순환 import 방지)
    steps = [label for label, _ in MEDIA_STEPS]
    k = steps.index(MEDIA_S3_TAB_LABEL)
    prev = {"sub": MEDIA_S3_SUB_TABS[i - 1]} if i > 0 else ({"step": steps[k - 1]} if k > 0 else None)
    nxt = ({"sub": MEDIA_S3_SUB_TABS[i + 1]} if i < len(MEDIA_S3_SUB_TABS) - 1
           else ({"step": steps[k + 1]} if k + 1 < len(steps) else None))
    with st.container(horizontal=True, horizontal_alignment="distribute", key=f"media-s3-nav-{i}"):
        if prev:
            st.button(f"← {next(iter(prev.values()))}", key=f"media-s3-nav-prev-{i}", type="primary",
                      on_click=_media_s3_go, kwargs=prev)
        if nxt:
            st.button(f"다음: {next(iter(nxt.values()))} →", key=f"media-s3-nav-next-{i}", type="primary",
                      on_click=_media_s3_go, kwargs=nxt)


def media_stage3_render():
    """3단계 ④ 하위 탭(이름은 MEDIA_S3_TAB_LABEL, 탭 이름이 제목 역할). 반드시 media_render() 안에서 부릅니다."""
    media_s3_store_load()   # 탭을 옮기거나 새로고침해도 작업물이 남게 폴더에서 다시 읽음
    src = media_s3_input()
    st.session_state[MEDIA_S3_GROUP] = media_s3_group(src)   # 지금 가설 묶음 (결과를 가설별로 나누는 기준)
    media_s3_history_migrate()
    # 알림은 줄을 따로 쓰지 않고 각 탭 아래 짧은 안내 줄에 붙임 (한 화면에 스크롤 없이 보이게)
    notes = []
    if src.get("sample"):
        notes.append("2단계 프롬프트를 아직 안 넘겨 예시로 보여 줘요")
    if not media_handoff_check(src, src["prompt_a"], src["prompt_b"])["ok"]:
        notes.append("받은 프롬프트 A·B가 빈칸 말고도 달라요. 2단계에서 확인해 주세요")
    st.session_state[MEDIA_S3_NOTES] = notes

    # ④ 안의 하위 탭: 사진 초안 제작 / 영상 초안 제작 (영상은 스토리보드 확정 → 영상 초안 순서)
    # on_change="rerun": 고른 탭만 그리고, 아래 '다음' 버튼으로 하위 탭을 바꿀 수 있게 (선택 상태를 기억)
    tabs = st.tabs(MEDIA_S3_SUB_TABS, key="media-s3-sub", on_change="rerun")
    renders = [lambda: media_s3_photo_section(src), lambda: media_s3_video_tab(src),
               lambda: (media_s3_history_section(), media_s3_handoff_step("history"))]
    for i, (tab, render) in enumerate(zip(tabs, renders)):
        if tab.open:
            with tab:
                render()
                media_s3_nav(i)
