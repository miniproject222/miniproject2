# 3. 매체 제작 > 3단계 ④·⑤: 작업물 보관
# 만든 결과 기록(history), 고른 목록, 만드는 중인 영상 작업 번호 등을 data/workspace/ 폴더에 저장하고,
# 화면을 그릴 때 session_state가 비어 있으면 여기서 다시 읽어 옵니다.
# 사진·영상 초안 제작 탭의 작업물(사진·영상·스토리보드)은 이번 접속 동안만 둡니다 (MEDIA_S3_SESSION_ONLY):
# 탭을 옮겨도 남지만, 앱을 새로 열거나 새로고침하면 빈 상태로 시작하고 만든 것은 '만든 결과 보기'에만 남습니다.
# 이 폴더는 각자 컴퓨터의 작업물이라 .gitignore에 넣어 GitHub에 올리지 않습니다.
import json
from pathlib import Path

import streamlit as st

MEDIA_S3_WORK_DIR = Path(__file__).resolve().parent / "data" / "workspace"
MEDIA_S3_WORK_FILES = {"media-s3-assets-photos": "photos", "media-s3-assets-videos": "videos"}   # session 키 → 폴더
MEDIA_S3_WORK_JSON = {"media-s3-storyboard": "storyboard.json", "media-s3-storyboard-done": "storyboard_done.json",
                      "media-s3-video-job": "video_job.json",
                    "media-s3-video-links": "video_links.json",   # 영상 파일 이름 → Higgsfield 주소
                    "media-s3-file-group": "file_group.json",     # 작업 공간 파일 이름 → 만든 가설 묶음 id
                    "media-s3-history": "history.json",           # 만든 결과 기록 목록 (session 키 → 파일)
                    "media-s3-pick": "pick.json",                 # '만든 결과 보기'에서 ⑤로 보내려고 고른 기록(file) 목록
                    "media-s3-group-storyboard": "group_storyboard.json",   # 가설 묶음 id → 그 가설로 확정한 스토리보드
                    "media-s3-send-group": "send_group.json"}     # '만든 결과 보기'에서 외주로 보내려고 고른 가설 묶음 id
MEDIA_S3_SESSION_ONLY = {"media-s3-assets-photos", "media-s3-assets-videos",   # 폴더에서 읽지도, 폴더에 쓰지도 않는 키
                         "media-s3-storyboard", "media-s3-storyboard-done"}
MEDIA_S3_HISTORY_DIR = MEDIA_S3_WORK_DIR / "history"   # 만든 결과 사본 (작업 공간에서 지우거나 바꿔도 남음)
MEDIA_S3_HISTORY_KEEP = 5   # 만든 결과 기록은 최근 가설 묶음 5개까지만 남김 (오래된 묶음은 사본까지 지움)


def media_s3_store_load() -> None:
    """session_state에 없는 작업물을 폴더에서 읽어 옵니다. 화면 맨 위에서 한 번 부릅니다."""
    for key in MEDIA_S3_WORK_FILES:
        st.session_state.setdefault(key, [])   # 사진·영상 작업물은 이번 접속에서 만든 것만 (빈 상태로 시작)
    for key, name in MEDIA_S3_WORK_JSON.items():
        path = MEDIA_S3_WORK_DIR / name
        if key not in st.session_state and key not in MEDIA_S3_SESSION_ONLY and path.exists():
            try:
                st.session_state[key] = json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                pass


def media_s3_store_file(key: str, name: str, content: bytes | None) -> None:
    """파일 하나를 저장합니다 (content가 None이면 지움). 이번 접속에만 두는 작업물은 저장하지 않습니다."""
    if key in MEDIA_S3_SESSION_ONLY:
        return
    path = MEDIA_S3_WORK_DIR / MEDIA_S3_WORK_FILES[key] / Path(name).name
    if content is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def media_s3_store_json(key: str, value) -> None:
    """작업 번호·기록 등을 저장합니다 (value가 None이면 지움). 이번 접속에만 두는 스토리보드는 저장하지 않습니다."""
    if key in MEDIA_S3_SESSION_ONLY:
        return
    path = MEDIA_S3_WORK_DIR / MEDIA_S3_WORK_JSON[key]
    if value is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1), encoding="utf-8")


def media_s3_store_history_add(entry: dict, content: bytes) -> None:
    """만든 결과 하나를 기록하고 사본을 history/ 폴더에 남깁니다. entry에는 file(사본 이름)이 들어 있어야 합니다."""
    path = MEDIA_S3_HISTORY_DIR / Path(entry["file"]).name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    history = media_s3_store_history_trim(list(st.session_state.get("media-s3-history") or []) + [entry])
    st.session_state["media-s3-history"] = history
    media_s3_store_json("media-s3-history", history)


def media_s3_store_history_groups(history: list) -> list:
    """기록을 가설 묶음별로 나눠 최근 묶음부터 [(묶음 id, 결과 목록)]으로 돌려줍니다."""
    groups = {}
    for e in history:
        groups.setdefault(e["group"].get("id", ""), []).append(e)
    return sorted(groups.items(), key=lambda g: max(e["created"] for e in g[1]), reverse=True)


def media_s3_store_history_trim(history: list) -> list:
    """최근 가설 묶음 MEDIA_S3_HISTORY_KEEP개만 남기고, 더 오래된 묶음은 기록과 사본 파일을 지웁니다."""
    groups = media_s3_store_history_groups(history)
    keep = {gid for gid, _ in groups[:MEDIA_S3_HISTORY_KEEP]}
    for gid, entries in groups[MEDIA_S3_HISTORY_KEEP:]:
        for e in entries:
            (MEDIA_S3_HISTORY_DIR / Path(e["file"]).name).unlink(missing_ok=True)
    return [e for e in history if e["group"].get("id", "") in keep]


def media_s3_store_history_find(files: list) -> list:
    """기록 file 이름 목록에 해당하는 기록을 [(기록, 내용)]으로 돌려줍니다 (지워진 것은 빠짐). ⑤가 zip에 넣을 때 씁니다."""
    by_file = {e["file"]: e for e in st.session_state.get("media-s3-history") or []}
    found = [(by_file[f], media_s3_store_history_read(by_file[f])) for f in files if f in by_file]
    return [(e, c) for e, c in found if c is not None]


def media_s3_store_history_read(entry: dict) -> bytes | None:
    """기록에 있는 결과 사본을 읽습니다 (파일이 없으면 None)."""
    path = MEDIA_S3_HISTORY_DIR / Path(entry["file"]).name
    return path.read_bytes() if path.exists() else None


def media_s3_store_history_remove(file: str) -> None:
    """만든 결과 기록 하나를 지웁니다 (사본 파일까지). '만든 결과 보기'의 지우기 버튼에서 부릅니다."""
    (MEDIA_S3_HISTORY_DIR / Path(file).name).unlink(missing_ok=True)
    history = [e for e in st.session_state.get("media-s3-history") or [] if e["file"] != file]
    st.session_state["media-s3-history"] = history
    media_s3_store_json("media-s3-history", history)
