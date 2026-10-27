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

from modules.media.media_handoff import (media_handoff_assets, media_handoff_check, media_handoff_prompt,
                                         media_handoff_set_assets)
from modules.media.media_stage3.media_stage3 import (MEDIA_S3_MEDIA_NOTE, MEDIA_S3_PICK, media_s3_group, media_s3_guide,
                                                    media_s3_nice_files, media_s3_nice_name,
                                                    media_s3_video_burned, media_s3_video_subtitles, media_s3_video_versions,
                                                    media_s3_set_pick,
                                                    media_s3_storyboard_dialog, media_s3_text_dialog)
from modules.media.media_stage3.media_stage3_pdf import media_s3_brief, media_s3_build_pdf
from common.common_store import store_get
from modules.media.media_stage3.media_stage3_ai import MediaS3AIError, media_s3_ai_ready, media_s3_translate
from modules.media.media_stage3.media_stage3_store import media_s3_store_history_find, media_s3_store_load

MEDIA_S3_EXPORT_TAB_LABEL = "외주 정리"   # 하위 탭 이름 (여기서 바꾸면 탭과 이전/다음 버튼 글자가 함께 바뀜)
MEDIA_S3_EXPORT_PDF_NAME = "외주_촬영_브리프.pdf"

def media_s3_brief_ctx(src: dict, storyboard: list, group: dict) -> dict:
    """브리프 1·2번에 쓸 값: 1번 리포트(검색어 클릭 분석·금지 표현·이미지 문제) + 1단계 KPI + 영상 스토리보드 A·B."""
    from modules.media.media_stage3.media_stage3_ai import MEDIA_S3_VIDEO_HOOK, MEDIA_S3_VIDEO_SECONDS
    from modules.media.media_handoff import media_handoff_plan
    report = store_get("report") or {}
    plan = media_handoff_plan()
    kpi = (f"{plan['kpi']} {plan['kpi_now']:g} → {plan['kpi_goal']:g}배"
           if isinstance(plan.get("kpi_now"), (int, float)) and isinstance(plan.get("kpi_goal"), (int, float))
           else plan.get("kpi") or "")
    versions = media_s3_video_versions(storyboard or [])
    hooks = {v: versions[v][0] for v in ("A", "B")} if set(versions) == {"A", "B"} else None
    return {"sqp": report.get("sqp") if isinstance(report.get("sqp"), dict) else {}, "kpi_photo": kpi,
            "hooks": hooks, "common": versions["A"][1:] if hooks else [],
            "video_sec": MEDIA_S3_VIDEO_SECONDS, "hook_sec": MEDIA_S3_VIDEO_HOOK,
            "fixed_ko": media_s3_export_ko(src, group)["fixed"],
            "forbidden": (report.get("ad_claims") or {}).get("forbidden") or [],
            "image_fixes": report.get("image_fixes") or []}


def media_s3_pdf(src: dict, group: dict, storyboard: list, photos: list, videos: list) -> bytes:
    """글로 된 부분(목적·촬영 지시·프롬프트 A/B·스토리보드·첨부 목록)을 보고서 형식 PDF로. group = ④에서 보낸 가설 묶음."""
    return media_s3_build_pdf(src, group, storyboard, photos, videos,
                              time.strftime("%Y-%m-%d"), MEDIA_S3_MEDIA_NOTE, media_s3_brief_ctx(src, storyboard, group))


def media_s3_package(src: dict, group: dict, storyboard: list, photos: list, videos: list) -> bytes:
    """외주 전달 묶음(zip): 브리프 PDF 한 장 + 사진 레퍼런스 + 영상 초안. photos·videos는 media_s3_export_named()로 바꾼 것."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(MEDIA_S3_EXPORT_PDF_NAME, media_s3_pdf(src, group, storyboard, photos, videos))
        for name, content in photos:
            z.writestr(f"photo_reference/{name}", content)
        for name, content in videos:
            z.writestr(f"video_draft/{name}", content)
    return buf.getvalue()


def media_s3_export_named(photos: list, videos: list) -> tuple:
    """zip·PDF에 넣는 사진·영상 (2026-10-27): 이름은 'A안 사진.png'·'B안 영상.mp4',
    영상은 앱에서 보던 그대로 한국어 설명 자막을 구워 넣은 것 하나만 (예전: 원본 + .srt + _한국어설명.mp4 세 개).
    자막이 없거나 굽기에 실패하면 원본 영상."""
    videos = [(n, (media_s3_video_burned(n, c) if media_s3_video_subtitles(n, "srt") else None) or c) for n, c in videos]
    return media_s3_nice_files(photos), media_s3_nice_files(videos)


def _media_s3_export_list(items: list) -> str:
    return "".join(f"<li>{html.escape(str(x))}</li>" for x in items) or "<li>-</li>"


def media_s3_export_ko(src: dict, group: dict) -> dict:
    """사람이 읽는 한국어 값: 바꾸는 것, 지금 사진(A), 새로 찍을 사진(B), 고정 요소.
    A·B 설명은 1단계에서 고른 한국어 설명(가설 묶음)을 쓰고, 영어인 고정 요소는 번역 (키가 없으면 원문)."""
    fixed = ", ".join(src["fixed"]) or "-"
    if fixed != "-" and media_s3_ai_ready("OPENAI_API_KEY"):
        try:
            fixed = media_s3_translate(fixed)
        except MediaS3AIError:
            pass
    return {"variable": group.get("variable") or src["variable"], "a": group.get("a") or src["slot_a"],
            "b": group.get("b") or src["slot_b"], "fixed": fixed}


def _media_s3_export_rows(rows: list, head: tuple | None = None) -> str:
    """표 HTML (첫 칸은 제목 칸)."""
    esc = html.escape
    top = ("<tr>" + "".join(f"<th>{esc(str(h))}</th>" for h in head) + "</tr>") if head else ""
    return (f'<table class="media-s3-ex-table">{top}'
            + "".join("<tr><th>" + esc(str(r[0])) + "</th>" + "".join(f"<td>{esc(str(c))}</td>" for c in r[1:]) + "</tr>"
                      for r in rows) + "</table>")


def media_s3_export_brief_html(src: dict, group: dict, storyboard: list | None = None) -> str:
    """PDF 1·2번과 같은 내용(목적: 데이터 → 가설 → 사진·영상 실험 → 결과물 / 촬영 지시: 공통 → 사진 → 영상 컷 → 규칙 → 여분 컷)을
    읽기 좋은 HTML로. 카드와 '크게 보기' 팝업이 같이 씀. 내용은 media_stage3_pdf.media_s3_brief() 한 곳에서 만듦."""
    b = media_s3_brief(src, group, media_s3_brief_ctx(src, storyboard or [], group))
    lst = _media_s3_export_list
    video = (f"""<i>③ 영상 (자사몰, 한 번 촬영 → 두 버전 편집)</i>{_media_s3_export_rows(b["cuts"], ("컷", "내용", "쓰는 곳"))}
<ul>{lst(b["edit"])}</ul>""" if b["cuts"] else "")
    extra = (f'<i>⑤ 여분 컷 (재촬영 방지)</i><ul>{lst(b["extra"] + [b["extra_note"]])}</ul>' if b["extra"] else "")
    return f"""<div class="media-s3-ex-body">
<div class="media-s3-ex-sec"><b>1. 이번 촬영의 목적</b>
<i>① 왜 찍나 (1번 문제 분석 데이터)</i><ul>{lst(b["why"] or ["1번 리포트 값이 없어 생략"])}</ul>
<i>② 무엇을 확인하나 (가설)</i>
<div class="media-s3-ex-hypo">{html.escape(b["hypothesis"] or "가설 문장이 기록되지 않았어요")}</div>
<i>③ 어떻게 확인하나 (같은 가설, 실험 2개)</i>{_media_s3_export_rows(b["exp"], ("구분", "사진 A/B", "영상 A/B"))}
<div class="media-s3-ex-note"><b>④ {html.escape(b["result"])}</b></div></div>
<div class="media-s3-ex-sec"><b>2. 촬영 지시</b>
<i>① 공통 (사진·영상 모두)</i><ul>{lst(b["common"])}</ul>
<i>② 사진 (아마존 메인 이미지)</i>{_media_s3_export_rows(b["photo"])}
{video}
<i>④ 독일 광고 규칙 (어기면 재촬영)</i><ul>{lst(b["rules"])}</ul>
{extra}</div>
<div class="media-s3-ex-note">PDF에는 3. 참고 프롬프트, 4. 영상 스토리보드, 5. 함께 보내는 파일 목록도 들어가요 (위 버튼으로 미리 보기).</div>
</div>"""


@st.dialog("외주 촬영 브리프 크게 보기", width="large")
def media_s3_export_brief_dialog(body: str):
    """왼쪽 카드 '크게 보기': 카드 안에서 스크롤하던 내용을 팝업에 한 번에."""
    st.markdown(body, unsafe_allow_html=True)


def media_s3_export_brief(src: dict, group: dict, storyboard: list) -> None:
    """왼쪽 카드: PDF에 들어가는 내용. 제목 옆 '크게 보기'(팝업), 프롬프트·스토리보드도 팝업으로."""
    ko = media_s3_export_ko(src, group)
    body = media_s3_export_brief_html(src, group, storyboard)
    with st.container(horizontal=True, vertical_alignment="center", key="media-s3-ex-head"):
        st.markdown(f"**📄 {MEDIA_S3_EXPORT_PDF_NAME}에 들어가는 내용**")
        if st.button("크게 보기", key="media-s3-btn-view-exBig", icon=":material/open_in_full:"):
            media_s3_export_brief_dialog(body)
        st.space("stretch")
        if st.button("지금 사진 프롬프트", key="media-s3-btn-view-exA", icon=":material/open_in_new:"):
            media_s3_text_dialog("지금 사진 프롬프트", src.get("prompt_a") or "-", f"지금 사진: {ko['a']}")
        if st.button("새 사진 프롬프트", key="media-s3-btn-view-exB", icon=":material/open_in_new:"):
            media_s3_text_dialog("새로 찍을 사진 프롬프트", src.get("prompt_b") or "-", f"새로 찍을 사진: {ko['b']}")
        if st.button(f"스토리보드 {len(storyboard)}장면", key="media-s3-btn-view-exSB", icon=":material/open_in_new:",
                     disabled=not storyboard):
            media_s3_storyboard_dialog(storyboard, "PDF의 '4. 영상 스토리보드' 표와 같아요.")
    st.markdown(body, unsafe_allow_html=True)


def _media_s3_export_remove(kind: str, file: str) -> None:
    """보낼 파일에서 하나 빼기 (⑤로 넘긴 목록과 ④ '⑤로 보내기' 체크에서 뺌). 만든 결과 기록·파일은 지우지 않음."""
    assets = media_handoff_assets()
    if assets["sample"]:
        return
    media_handoff_set_assets({"storyboard": assets["storyboard"],
                              "photos": [f for f in assets["photos"] if not (kind == "photos" and f == file)],
                              "videos": [f for f in assets["videos"] if not (kind == "videos" and f == file)],
                              **({"group": assets["group"]} if assets.get("group") else {})})   # 보낸 가설은 그대로
    if MEDIA_S3_PICK in st.session_state:
        media_s3_set_pick([f for f in st.session_state[MEDIA_S3_PICK] if f != file])
    st.session_state["media-s3-ex-removed-toast"] = True


def media_s3_export_files(photos: list, videos: list) -> None:
    """오른쪽 카드: zip에 실제로 들어가는 것만 (브리프 PDF · 사진 · 영상). 사진·영상에 마우스를 올리면 🗑로 이번 보내기에서 뺌."""
    if st.session_state.pop("media-s3-ex-removed-toast", False):
        st.toast("보낼 파일에서 뺐어요 (만든 결과 보기에는 그대로 있어요)", icon="🗑️")
    st.markdown("**🗂 보낼 파일 (zip)**", help="사진·영상에 마우스를 올리면 🗑로 이번 외주 보내기에서 뺄 수 있어요. "
                                                "만든 결과 보기의 기록은 지워지지 않아요.")
    st.markdown(f'<div class="media-s3-ex-file"><b>📄 {MEDIA_S3_EXPORT_PDF_NAME}</b> · 촬영 브리프 1개</div>',
                unsafe_allow_html=True)
    with st.container(key="media-s3-ex-photos"):
        st.markdown(f"**🖼 사진** · {len(photos)}장")
        if not photos:
            st.caption("없음")
        with st.container(horizontal=True, gap="small", key="media-s3-ex-thumbs"):
            for n, c in photos:
                with st.container(key=f"media-s3-ex-ph-{n}", width="content"):
                    st.markdown(f'<img class="media-s3-ex-thumb" title="{html.escape(media_s3_nice_name(n))}" '
                                f'src="data:image/png;base64,{base64.b64encode(c).decode()}">', unsafe_allow_html=True)
                    st.button("", key=f"media-s3-ex-rm-ph-{n}", icon=":material/delete:", type="tertiary",
                              help="이번 외주 보내기에서 빼기", on_click=_media_s3_export_remove, args=("photos", n))
    with st.container(key="media-s3-ex-videos"):
        st.markdown(f"**🎬 영상** · {len(videos)}개")
        if not videos:
            st.caption("없음")
        for n, _ in videos:
            with st.container(horizontal=True, vertical_alignment="center", key=f"media-s3-ex-vd-{n}"):
                st.caption(f"🎞 {media_s3_nice_name(n)}")
                st.space("stretch")
                st.button("", key=f"media-s3-ex-rm-vd-{n}", icon=":material/delete:", type="tertiary",
                          help="이번 외주 보내기에서 빼기", on_click=_media_s3_export_remove, args=("videos", n))


def media_stage3_export_render():
    """3단계 ⑤ 하위 탭(이름은 MEDIA_S3_EXPORT_TAB_LABEL, 탭 이름이 제목 역할). 반드시 media_render() 안에서 부릅니다.
    사진·영상 탭처럼 100% 화면에서 스크롤 없이: 왼쪽은 PDF에 들어가는 내용, 오른쪽은 zip에 들어가는 파일과 내려받기."""
    media_s3_store_load()   # ④를 거치지 않고 바로 열어도 보관된 작업물을 씀
    src = media_handoff_prompt()
    assets = media_handoff_assets()   # 사진·영상 초안 제작에서 '외주 정리로 넘기기'로 넘긴 스토리보드·고른 기록 이름
    storyboard = assets["storyboard"]
    group = assets.get("group") or media_s3_group(src)   # '만든 결과 보기'에서 보낸 가설 (예전 넘김 값에는 없어서 지금 가설)
    # 파일 자체는 크기 때문에 Supabase에 넣지 않고, 이 컴퓨터의 '만든 결과' 기록 폴더에서 이름으로 찾음
    # zip 안 이름은 기록 이름(만든 시각_파일 이름)이라 다른 가설의 같은 이름 파일도 겹치지 않음
    photos = [(e["file"], c) for e, c in media_s3_store_history_find(assets["photos"])]
    videos = [(e["file"], c) for e, c in media_s3_store_history_find(assets["videos"])]
    ready = not assets["sample"] and media_handoff_check(src, src["prompt_a"], src["prompt_b"])["ok"]
    if assets["sample"]:
        notice = ":orange[사진·영상 초안 제작에서 '외주 정리로 넘기기'를 눌러야 사진·영상·스토리보드가 들어와요]"
    elif len(photos) < len(assets["photos"]) or len(videos) < len(assets["videos"]):
        notice = (":orange[넘긴 파일 중 일부를 이 컴퓨터에서 찾을 수 없어요 (다른 컴퓨터에서 만들었거나 최근 가설 5개를 넘어 지워짐). "
                  "'만든 결과 보기'에서 다시 골라 넘겨 주세요]")
    else:
        notice = "외주 촬영 업체 또는 사내 촬영팀에 보낼 자료를 zip 하나로 묶어요 (글은 PDF 보고서, 사진·영상은 파일)"

    with st.container(horizontal=True, gap="medium", key="media-s3-export-row"):
        left = st.container(border=True, key="media-s3-export-left")
        right = st.container(border=True, width=440, key="media-s3-export-right")
    with left:
        media_s3_export_brief(src, group, storyboard)
    with right:
        media_s3_export_files(photos, videos)
    # 내려받기는 아래 줄에 두어 작은 화면에서도 늘 보이게 (카드 안 스크롤에 숨지 않게)
    with st.container(horizontal=True, vertical_alignment="center", key="media-s3-export-foot"):
        st.caption(notice)
        st.space("stretch")
        media_s3_guide("export")
        zp, zv = media_s3_export_named(photos, videos)   # zip·PDF 첨부 목록은 'A안 사진.png'·'B안 영상.mp4' 이름으로
        st.download_button("브리프 PDF만 내려받기", media_s3_pdf(src, group, storyboard, zp, zv),
                           file_name=MEDIA_S3_EXPORT_PDF_NAME, mime="application/pdf",
                           key="media-s3-btn-export-pdf", type="primary", disabled=not ready)
        st.download_button("외주 전달 파일 다운로드 (.zip)", media_s3_package(src, group, storyboard, zp, zv),
                           file_name="media_outsourcing_reference.zip", mime="application/zip",
                           key="media-s3-btn-export", type="primary", disabled=not ready,
                           help=None if ready else "사진·영상 초안 제작에서 '외주 정리로 넘기기'를 누르고, 프롬프트 확인을 통과해야 내려받을 수 있어요.")
