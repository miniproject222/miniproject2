# 3. 매체 제작 > 3단계 ④·⑤: 작업물 보관 (탭을 옮기거나 새로고침해도 유지)
# 만든 사진·영상, 스토리보드, 만드는 중인 영상 작업 번호를 data/workspace/ 폴더에 저장하고,
# 화면을 그릴 때 session_state가 비어 있으면 여기서 다시 읽어 옵니다.
# 이 폴더는 각자 컴퓨터의 작업물이라 .gitignore에 넣어 GitHub에 올리지 않습니다.
import json
from pathlib import Path

import streamlit as st

MEDIA_S3_WORK_DIR = Path(__file__).resolve().parent / "data" / "workspace"
MEDIA_S3_WORK_FILES = {"media-s3-assets-photos": "photos", "media-s3-assets-videos": "videos"}   # session 키 → 폴더
MEDIA_S3_WORK_JSON = {"media-s3-storyboard": "storyboard.json", "media-s3-storyboard-done": "storyboard_done.json",
                      "media-s3-video-job": "video_job.json",
                    "media-s3-video-links": "video_links.json"}   # session 키 → 파일 (영상 파일 이름 → Higgsfield 주소)


def media_s3_store_load() -> None:
    """session_state에 없는 작업물을 폴더에서 읽어 옵니다. 화면 맨 위에서 한 번 부릅니다."""
    for key, folder in MEDIA_S3_WORK_FILES.items():
        if key not in st.session_state:
            path = MEDIA_S3_WORK_DIR / folder
            files = sorted(path.iterdir(), key=lambda f: f.stat().st_mtime) if path.exists() else []
            st.session_state[key] = [(f.name, f.read_bytes()) for f in files if f.is_file()]
    for key, name in MEDIA_S3_WORK_JSON.items():
        path = MEDIA_S3_WORK_DIR / name
        if key not in st.session_state and path.exists():
            try:
                st.session_state[key] = json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                pass


def media_s3_store_file(key: str, name: str, content: bytes | None) -> None:
    """파일 하나를 저장합니다 (content가 None이면 지움)."""
    path = MEDIA_S3_WORK_DIR / MEDIA_S3_WORK_FILES[key] / Path(name).name
    if content is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def media_s3_store_json(key: str, value) -> None:
    """스토리보드·작업 번호 등을 저장합니다 (value가 None이면 지움)."""
    path = MEDIA_S3_WORK_DIR / MEDIA_S3_WORK_JSON[key]
    if value is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1), encoding="utf-8")
