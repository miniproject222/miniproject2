# 3. 매체 제작 > 3단계 ⑤: 외주 정리 (3단계 담당 · DH 브랜치)
# 2단계가 넘긴 프롬프트·찍지 말 것·넣을 것과 ④에서 만든 사진·스토리보드·영상을 모아
# 외주 촬영 업체 또는 사내 촬영팀에 보낼 zip 하나로 묶습니다. 글로 된 부분(브리프·프롬프트·스토리보드)은
# 보고서 형식 PDF 한 장(media_stage3_pdf.py)으로, 사진·영상은 파일 그대로 넣습니다. 화면은 media_stage3_export_render() 안에서만 그립니다.
# 이름 규칙: 함수 media_s3_..., 위젯 key·session_state 키·CSS class media-s3-...
import base64
import html
import io
import time
import zipfile

import streamlit as st

from modules.media.media_handoff import media_handoff_assets, media_handoff_check, media_handoff_prompt
from modules.media.media_stage3.media_stage3 import (MEDIA_S3_MEDIA_NOTE, media_s3_group, media_s3_guide,
                                                    media_s3_storyboard_dialog, media_s3_text_dialog)
from modules.media.media_stage3.media_stage3_pdf import media_s3_build_pdf
from modules.media.media_stage3.media_stage3_store import media_s3_store_history_find, media_s3_store_load

MEDIA_S3_EXPORT_TAB_LABEL = "외주 정리"   # 하위 탭 이름 (여기서 바꾸면 탭과 이전/다음 버튼 글자가 함께 바뀜)
MEDIA_S3_EXPORT_PDF_NAME = "외주_촬영_브리프.pdf"
# 예전 zip에 따로 있던 글 파일들 → 지금은 PDF 한 파일로 합침 (화면에 '어떻게 줄였는지' 보여 줌)
MEDIA_S3_EXPORT_MERGED = [("README_촬영브리프.txt", "1. 이번 촬영의 목적 · 2. 촬영 지시"),
                          ("prompt_A.txt · prompt_B.txt · prompts.json", "3. 참고 이미지 프롬프트"),
                          ("video_storyboard.csv", "4. 영상 스토리보드 표")]


def media_s3_pdf(src: dict, storyboard: list, photos: list, videos: list) -> bytes:
    """글로 된 부분(가설·단일 변수·촬영 지시·프롬프트 A/B·스토리보드·첨부 목록)을 보고서 형식 PDF로."""
    return media_s3_build_pdf(src, media_s3_group(src), storyboard, photos, videos,
                              time.strftime("%Y-%m-%d"), MEDIA_S3_MEDIA_NOTE)


def media_s3_package(src: dict, storyboard: list, photos: list, videos: list) -> bytes:
    """외주 전달 묶음(zip): 브리프 PDF 한 장 + 사진 레퍼런스 + 영상 초안."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(MEDIA_S3_EXPORT_PDF_NAME, media_s3_pdf(src, storyboard, photos, videos))
        for name, content in photos:
            z.writestr(f"photo_reference/{name}", content)
        for name, content in videos:
            z.writestr(f"video_draft/{name}", content)
    return buf.getvalue()


def _media_s3_export_list(items: list) -> str:
    return "".join(f"<li>{html.escape(str(x))}</li>" for x in items) or "<li>-</li>"


def media_s3_export_brief(src: dict, group: dict, storyboard: list) -> None:
    """왼쪽 카드: PDF에 들어가는 내용을 읽기 좋게 (목적 → A·B 차이 → 촬영 지시). 프롬프트·스토리보드는 팝업으로."""
    with st.container(horizontal=True, vertical_alignment="center"):
        st.markdown(f"**📄 {MEDIA_S3_EXPORT_PDF_NAME}에 들어가는 내용**")
        st.space("stretch")
        if st.button("프롬프트 A", key="media-s3-btn-view-exA", icon=":material/open_in_new:"):
            media_s3_text_dialog("사진 A 프롬프트", src.get("prompt_a") or "-", f"A안: {src['slot_a']}")
        if st.button("프롬프트 B", key="media-s3-btn-view-exB", icon=":material/open_in_new:"):
            media_s3_text_dialog("사진 B 프롬프트", src.get("prompt_b") or "-", f"B안: {src['slot_b']}")
        if st.button(f"스토리보드 {len(storyboard)}장면", key="media-s3-btn-view-exSB", icon=":material/open_in_new:",
                     disabled=not storyboard):
            media_s3_storyboard_dialog(storyboard, "PDF의 '4. 영상 스토리보드' 표와 같아요.")
    avoid = src["avoid"] or ["(2단계 AI 다듬기 결과가 들어갈 자리)"]
    include = src["include"] or ["(2단계 AI 다듬기 결과가 들어갈 자리)"]
    st.markdown(f"""<div class="media-s3-ex-body">
<div class="media-s3-ex-sec"><b>1. 이번 촬영의 목적</b>
<div class="media-s3-ex-hypo">{html.escape(group.get("hypothesis") or "가설 문장이 기록되지 않았어요")}</div>
<table class="media-s3-ex-table">
<tr><th>A와 B에서 바꾸는 것</th><td>{html.escape(src["variable"])}</td></tr>
<tr><th>A안</th><td>{html.escape(src["slot_a"])}</td></tr>
<tr><th>B안</th><td>{html.escape(src["slot_b"])}</td></tr>
</table>
<div class="media-s3-ex-note">A와 B는 이 한 가지만 다르고 조명·배경·보정·제품은 똑같아야 어느 쪽이 더 잘 팔리는지 비교할 수 있어요.</div></div>
<div class="media-s3-ex-sec"><b>2. 촬영 지시</b>
<div class="media-s3-ex-cols">
<div><i>공통</i><ul>{_media_s3_export_list(["조명, 배경, 보정은 A·B 똑같이", "고정 요소: " + (", ".join(src["fixed"]) or "-"),
                                          "받을 것: 메인 이미지 A·B 각 3컷 (원본 + 흰 배경 보정본)"])}</ul></div>
<div><i>찍지 말 것</i><ul>{_media_s3_export_list(avoid)}</ul></div>
<div><i>넣을 것</i><ul>{_media_s3_export_list(include)}</ul></div>
</div></div>
<div class="media-s3-ex-note">PDF에는 3. 참고 프롬프트 A·B, 4. 영상 스토리보드, 5. 함께 보내는 파일 목록도 들어가요 (위 버튼으로 미리 보기).</div>
</div>""", unsafe_allow_html=True)


def media_s3_export_files(photos: list, videos: list) -> None:
    """오른쪽 카드: zip에 들어가는 파일 (PDF 한 장으로 합친 것 · 사진 썸네일 · 영상 목록)."""
    st.markdown("**🗂 보낼 파일 (zip)**")
    merged = "".join(f"<li><s>{html.escape(old)}</s> → {html.escape(where)}</li>" for old, where in MEDIA_S3_EXPORT_MERGED)
    thumbs = "".join(f'<img title="{html.escape(n)}" src="data:image/png;base64,{base64.b64encode(c).decode()}">'
                     for n, c in photos)
    vids = _media_s3_export_list([n for n, _ in videos]) if videos else "<li>없음</li>"
    st.markdown(f"""<div class="media-s3-ex-files">
<div class="media-s3-ex-file"><b>📄 {MEDIA_S3_EXPORT_PDF_NAME}</b> · 글로 된 것을 전부 이 한 파일로 합쳤어요
<ul class="media-s3-ex-merged">{merged}</ul></div>
<div class="media-s3-ex-file"><b>🖼 photo_reference/</b> · 사진 {len(photos)}장
<div class="media-s3-ex-thumbs">{thumbs or '<span>없음</span>'}</div></div>
<div class="media-s3-ex-file"><b>🎬 video_draft/</b> · 영상 {len(videos)}개<ul>{vids}</ul></div>
</div>""", unsafe_allow_html=True)


def media_stage3_export_render():
    """3단계 ⑤ 하위 탭(이름은 MEDIA_S3_EXPORT_TAB_LABEL, 탭 이름이 제목 역할). 반드시 media_render() 안에서 부릅니다.
    사진·영상 탭처럼 100% 화면에서 스크롤 없이: 왼쪽은 PDF에 들어가는 내용, 오른쪽은 zip에 들어가는 파일과 내려받기."""
    media_s3_store_load()   # ④를 거치지 않고 바로 열어도 보관된 작업물을 씀
    src = media_handoff_prompt()
    assets = media_handoff_assets()   # ④에서 '⑤로 넘기기'로 넘긴 스토리보드·고른 기록 이름
    storyboard = assets["storyboard"]
    # 파일 자체는 크기 때문에 Supabase에 넣지 않고, 이 컴퓨터의 '만든 결과' 기록 폴더에서 이름으로 찾음
    # zip 안 이름은 기록 이름(만든 시각_파일 이름)이라 다른 가설의 같은 이름 파일도 겹치지 않음
    photos = [(e["file"], c) for e, c in media_s3_store_history_find(assets["photos"])]
    videos = [(e["file"], c) for e, c in media_s3_store_history_find(assets["videos"])]
    ready = not assets["sample"] and media_handoff_check(src, src["prompt_a"], src["prompt_b"])["ok"]
    if assets["sample"]:
        notice = ":orange[④에서 '⑤로 넘기기'를 눌러야 사진·영상·스토리보드가 들어와요]"
    elif len(photos) < len(assets["photos"]) or len(videos) < len(assets["videos"]):
        notice = (":orange[넘긴 파일 중 일부를 이 컴퓨터에서 찾을 수 없어요 (다른 컴퓨터에서 만들었거나 최근 가설 5개를 넘어 지워짐). "
                  "④ '만든 결과 보기'에서 다시 골라 넘겨 주세요]")
    else:
        notice = "외주 촬영 업체 또는 사내 촬영팀에 보낼 자료를 zip 하나로 묶어요 (글은 PDF 보고서, 사진·영상은 파일)"

    with st.container(horizontal=True, gap="medium", key="media-s3-export-row"):
        left = st.container(border=True, key="media-s3-export-left")
        right = st.container(border=True, width=440, key="media-s3-export-right")
    with left:
        media_s3_export_brief(src, media_s3_group(src), storyboard)
    with right:
        media_s3_export_files(photos, videos)
    # 내려받기는 아래 줄에 두어 작은 화면에서도 늘 보이게 (카드 안 스크롤에 숨지 않게)
    with st.container(horizontal=True, vertical_alignment="center", key="media-s3-export-foot"):
        st.caption(notice)
        st.space("stretch")
        media_s3_guide("export")
        st.download_button("브리프 PDF만 내려받기", media_s3_pdf(src, storyboard, photos, videos),
                           file_name=MEDIA_S3_EXPORT_PDF_NAME, mime="application/pdf",
                           key="media-s3-btn-export-pdf", type="primary", disabled=not ready)
        st.download_button("외주 전달 파일 다운로드 (.zip)", media_s3_package(src, storyboard, photos, videos),
                           file_name="media_outsourcing_reference.zip", mime="application/zip",
                           key="media-s3-btn-export", type="primary", disabled=not ready,
                           help=None if ready else "④에서 '⑤로 넘기기'를 누르고, 프롬프트 확인을 통과해야 내려받을 수 있어요.")
