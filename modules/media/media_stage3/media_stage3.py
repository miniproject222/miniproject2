# 3. 매체 제작 > 3단계: 프롬프트 다듬기 → 매체 제작 → 외주 준비 (3단계 담당 · DH 브랜치)
# 2단계가 만든 프롬프트 재료(media_handoff_prompt(): 기본 프롬프트 + 빈칸 + A/B 빈칸 + 고정 요소)를 받아
# ① AI로 다듬고 빈칸 밖이 바뀌지 않았는지 확인 → ② 매체(사진·영상 초안) 제작 → ③ 외주용 파일로 묶습니다.
# 화면은 media_stage3_render() 안에서만 그립니다.
# 이름 규칙: 함수 media_s3_..., 위젯 key·session_state 키·CSS class media-s3-...
import io
import json
import zipfile
from pathlib import Path

import streamlit as st

from modules.media.media_handoff import MEDIA_HANDOFF_SLOT, media_handoff_prompt

MEDIA_S3_TAB_LABEL = "매체 제작·외주 준비"   # 하위 탭 이름 (여기서 바꾸면 탭과 이전/다음 버튼 글자가 함께 바뀜)
MEDIA_S3_DIR = Path(__file__).resolve().parent   # 3단계 폴더 (data/ 경로 만들 때 사용)
MEDIA_S3_MEDIA_NOTE = ("AI로 만든 사진·영상은 아마존 메인 이미지로 쓰지 않습니다. "
                       "외주 촬영 레퍼런스, 서브 이미지, 광고 초안으로만 씁니다.")


def media_s3_input() -> dict:
    """2단계 프롬프트 재료. 2단계가 아직 넘기지 않았으면 예시 값(src["sample"] == True)이 옵니다."""
    return media_handoff_prompt()


def media_s3_fill(base: str, slot: str) -> str:
    """기본 프롬프트의 빈칸을 채웁니다."""
    return base.replace(MEDIA_HANDOFF_SLOT, slot, 1)


def media_s3_check(src: dict, prompt_a: str, prompt_b: str) -> dict:
    """다듬은 A/B 확인: 빈칸 문구가 남아 있는지, 빈칸 밖이 A와 B에서 똑같은지, 고정 요소가 빠지지 않았는지."""
    slot_a, slot_b = src["slot_a"], src["slot_b"]
    slot_ok = slot_a in prompt_a and slot_b in prompt_b
    # 빈칸 문구를 다시 {slot}으로 바꿔 나머지를 비교 (빈칸이 없으면 비교할 수 없어 실패)
    rest_a = prompt_a.replace(slot_a, MEDIA_HANDOFF_SLOT, 1)
    rest_b = prompt_b.replace(slot_b, MEDIA_HANDOFF_SLOT, 1)
    same_rest = slot_ok and rest_a == rest_b
    missing = [f for f in src["fixed"] if f not in prompt_a or f not in prompt_b]
    return {"slot_ok": slot_ok, "same_rest": same_rest, "missing": missing,
            "ok": slot_ok and same_rest and not missing, "rest_a": rest_a, "rest_b": rest_b}


def media_s3_package(src: dict, prompt_a: str, prompt_b: str, files) -> bytes:
    """외주 전달 묶음(zip): 프롬프트 A/B, 고정 요소, 안내문, 올린 매체 파일."""
    readme = "\n".join([
        "[외주 레퍼런스] MODO 냉감패드 · amazon.de",
        f"단일 변수: {src['variable']}",
        "",
        "A와 B는 단일 변수만 다르고 나머지는 똑같이 촬영해 주세요.",
        "고정 요소: " + ", ".join(src["fixed"]),
        "",
        f"참고: {MEDIA_S3_MEDIA_NOTE}",
        "",
        "파일: prompt_A.txt, prompt_B.txt, prompts.json, reference/ (AI 초안)",
    ])
    data = {"variable": src["variable"], "slot_a": src["slot_a"], "slot_b": src["slot_b"],
            "fixed": src["fixed"], "prompt_a": prompt_a, "prompt_b": prompt_b}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.txt", readme)
        z.writestr("prompt_A.txt", prompt_a)
        z.writestr("prompt_B.txt", prompt_b)
        z.writestr("prompts.json", json.dumps(data, ensure_ascii=False, indent=2))
        for f in files or []:
            z.writestr(f"reference/{f.name}", f.getvalue())
    return buf.getvalue()


def _media_s3_reset(name: str, text: str) -> None:
    """'되돌리기' 버튼 콜백. 다듬은 프롬프트 칸을 빈칸만 채운 원래 문장으로 되돌립니다."""
    st.session_state[f"media-s3-prompt-{name}"] = text


def media_s3_refine_section(src: dict) -> tuple[str, str]:
    """① AI로 다듬기 + 확인. 다듬은 프롬프트 A, B를 돌려줍니다."""
    st.markdown("**① 프롬프트 다듬기 + 확인**")
    base_a, base_b = media_s3_fill(src["base"], src["slot_a"]), media_s3_fill(src["base"], src["slot_b"])
    st.button("AI로 다듬기", key="media-s3-btn-refine", disabled=True,
              help="AI 도구가 정해지면 연결합니다. 지금은 아래 칸에서 직접 고칠 수 있어요.")

    prompts = {}
    c1, c2 = st.columns(2)
    for col, name, original in ((c1, "A", base_a), (c2, "B", base_b)):
        key = f"media-s3-prompt-{name}"
        st.session_state.setdefault(key, original)
        with col:
            with st.container(border=True):
                st.markdown(f"**프롬프트 {name}** · 빈칸: {src['slot_' + name.lower()]}")
                prompts[name] = st.text_area(f"프롬프트 {name}", key=key, height=160, label_visibility="collapsed")
                st.button("되돌리기", key=f"media-s3-btn-reset-{name}",
                          on_click=_media_s3_reset, args=(name, original))

    check = media_s3_check(src, prompts["A"], prompts["B"])
    if check["ok"]:
        st.success("A와 B는 빈칸만 다르고, 고정 요소도 모두 남아 있어요.")
    else:
        if not check["slot_ok"]:
            st.warning("빈칸 문구가 바뀌었어요. 단일 변수가 흔들리니 되돌려 주세요.")
        elif not check["same_rest"]:
            st.warning("빈칸 밖에서 A와 B가 서로 달라요. 바뀐 쪽을 되돌려 주세요.")
        if check["missing"]:
            st.warning("빠진 고정 요소: " + ", ".join(check["missing"]))
    return prompts["A"], prompts["B"]


def media_s3_make_section():
    """② 매체(사진·영상 초안) 제작. 생성 도구 연결 전에는 만든 파일을 직접 올립니다."""
    st.markdown("**② 매체 제작 (사진·영상 초안)**")
    st.caption(MEDIA_S3_MEDIA_NOTE)
    st.button("A/B 매체 생성", key="media-s3-btn-make", disabled=True,
              help="이미지·영상 생성 도구가 정해지면 연결합니다. 지금은 아래에서 만든 파일을 올려 주세요.")
    return st.file_uploader("만든 사진·영상 올리기 (파일 이름에 A 또는 B를 넣어 주세요)",
                            type=["png", "jpg", "jpeg", "webp", "mp4", "mov"],
                            accept_multiple_files=True, key="media-s3-files")


def media_s3_package_section(src: dict, prompt_a: str, prompt_b: str, files, ready: bool):
    """③ 외주 레퍼런스 취합 → 외주용 파일 준비."""
    st.markdown("**③ 외주 레퍼런스 정리**")
    st.markdown("- 프롬프트 A, B와 고정 요소, 안내문, 올린 매체를 zip 하나로 묶어요.\n"
                f"- 올린 매체: {len(files or [])}개")
    st.download_button("외주 전달 파일 다운로드 (.zip)", media_s3_package(src, prompt_a, prompt_b, files),
                       file_name="media_outsourcing_reference.zip", mime="application/zip",
                       key="media-s3-btn-export", disabled=not ready,
                       help=None if ready else "① 확인을 통과해야 내려받을 수 있어요.")


def media_stage3_render():
    """3단계 하위 탭(이름은 MEDIA_S3_TAB_LABEL, 탭 이름이 제목 역할). 반드시 media_render() 안에서 부릅니다."""
    src = media_s3_input()   # 2단계 프롬프트 재료 (2단계가 아직 안 넘겼으면 예시 값, src["sample"] == True)
    st.caption("다듬은 프롬프트로 매체 초안을 만들고, 외주에 넘길 파일로 정리해요.")
    if src.get("sample"):
        st.caption("2단계에서 프롬프트를 아직 만들지 않아 예시 프롬프트로 보여 줘요.")
    st.markdown(f"단일 변수: **{src['variable']}** · 고정 요소: {', '.join(src['fixed'])}")

    prompt_a, prompt_b = media_s3_refine_section(src)
    files = media_s3_make_section()
    ready = media_s3_check(src, prompt_a, prompt_b)["ok"]
    media_s3_package_section(src, prompt_a, prompt_b, files, ready)
