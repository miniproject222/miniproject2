# 3. 매체 제작 > 3단계 ⑤: 외주 정리 (3단계 담당 · DH 브랜치)
# 2단계가 넘긴 프롬프트·찍지 말 것·넣을 것과 ④에서 만든 사진·스토리보드·영상을 모아
# 외주 촬영 업체 또는 사내 촬영팀에 보낼 zip 하나로 묶습니다. 화면은 media_stage3_export_render() 안에서만 그립니다.
# 이름 규칙: 함수 media_s3_..., 위젯 key·session_state 키·CSS class media-s3-...
import csv
import io
import json
import zipfile

import streamlit as st

from modules.media.media_handoff import media_handoff_check, media_handoff_prompt
from modules.media.media_stage3.media_stage3 import (MEDIA_S3_MEDIA_NOTE, MEDIA_S3_PHOTOS, MEDIA_S3_STORYBOARD,
                                                     MEDIA_S3_STORYBOARD_SAMPLE, MEDIA_S3_VIDEOS)

MEDIA_S3_EXPORT_TAB_LABEL = "외주 정리"   # 하위 탭 이름 (여기서 바꾸면 탭과 이전/다음 버튼 글자가 함께 바뀜)


def media_s3_brief(src: dict) -> str:
    """촬영 브리프 (사람이 읽는 안내문). 맨 위에 단일 변수."""
    lines = [
        "[촬영 브리프] SEORI 냉감패드 · amazon.de 메인 이미지 A/B",
        "",
        f"■ A와 B는 이것만 다르게: {src['variable']}",
        f"  A: {src['slot_a']}",
        f"  B: {src['slot_b']}",
        "■ 조명, 배경, 보정은 A·B 똑같이",
        "■ 고정 요소: " + ", ".join(src["fixed"]),
        "",
        "■ 찍지 말 것",
        *[f"  - {x}" for x in (src["avoid"] or ["(2단계 AI 다듬기 결과가 들어갈 자리)"])],
        "■ 넣을 것",
        *[f"  - {x}" for x in (src["include"] or ["(2단계 AI 다듬기 결과가 들어갈 자리)"])],
        "",
        "■ 받을 것: 메인 이미지 A·B 각 3컷 (원본 + 흰 배경 보정본), 가능하면 서브 이미지도 같이",
        f"■ 참고: {MEDIA_S3_MEDIA_NOTE}",
        "※ 참고용 가이드이며 법률 자문이 아닙니다. 법률 확인을 권장합니다.",
    ]
    return "\n".join(lines)


def media_s3_package(src: dict, storyboard: list, photos: list, videos: list) -> bytes:
    """외주 전달 묶음(zip): 브리프, 프롬프트 A/B, 스토리보드, 사진, 영상."""
    sb = io.StringIO()
    if storyboard:
        w = csv.DictWriter(sb, fieldnames=list(storyboard[0].keys()))
        w.writeheader()
        w.writerows(storyboard)
    data = {k: src[k] for k in ("variable", "slot_a", "slot_b", "fixed", "prompt_a", "prompt_b",
                                "changes", "avoid", "include")}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README_촬영브리프.txt", media_s3_brief(src))
        z.writestr("prompt_A.txt", src["prompt_a"])
        z.writestr("prompt_B.txt", src["prompt_b"])
        z.writestr("prompts.json", json.dumps(data, ensure_ascii=False, indent=2))
        z.writestr("video_storyboard.csv", "﻿" + sb.getvalue())   # 엑셀에서 한글이 안 깨지게 BOM
        for name, content in photos:
            z.writestr(f"photo_reference/{name}", content)
        for name, content in videos:
            z.writestr(f"video_draft/{name}", content)
    return buf.getvalue()


def media_stage3_export_render():
    """3단계 ⑤ 하위 탭(이름은 MEDIA_S3_EXPORT_TAB_LABEL, 탭 이름이 제목 역할). 반드시 media_render() 안에서 부릅니다."""
    src = media_handoff_prompt()
    storyboard = st.session_state.get(MEDIA_S3_STORYBOARD, MEDIA_S3_STORYBOARD_SAMPLE)
    photos = st.session_state.get(MEDIA_S3_PHOTOS, [])
    videos = st.session_state.get(MEDIA_S3_VIDEOS, [])
    st.caption("외주 촬영 업체 또는 사내 촬영팀에 보낼 자료를 zip 하나로 묶어요.")

    with st.container(border=True):
        st.markdown("**촬영 브리프 (미리 보기)**")
        st.code(media_s3_brief(src), language=None, wrap_lines=True)
    st.markdown(f"- 사진 레퍼런스 {len(photos)}장 · 영상 스토리보드 {len(storyboard)}장면 · 영상 초안 {len(videos)}개")

    ready = media_handoff_check(src, src["prompt_a"], src["prompt_b"])["ok"]
    st.download_button("외주 전달 파일 다운로드 (.zip)", media_s3_package(src, storyboard, photos, videos),
                       file_name="media_outsourcing_reference.zip", mime="application/zip",
                       key="media-s3-btn-export", disabled=not ready,
                       help=None if ready else "2단계에서 프롬프트 확인을 통과해야 내려받을 수 있어요.")
