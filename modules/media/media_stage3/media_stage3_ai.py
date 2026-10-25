# 3. 매체 제작 > 3단계 ④: AI로 사진 초안·스토리보드(OpenAI), 영상 초안(Higgsfield Seedance 2.5) 만들기
# 키는 .streamlit/secrets.toml의 OPENAI_API_KEY, HF_KEY("키ID:키시크릿") ([connections.supabase] 줄 위)에서 함수 안에서 읽습니다.
# 화면 코드는 media_stage3.py가 이 파일의 함수만 부릅니다. 모델을 바꾸려면 아래 상수만 고칩니다.
import base64
import json
import os

import streamlit as st

MEDIA_S3_IMAGE_MODEL = "gpt-image-1-mini"   # 사진 초안 (레퍼런스용이라 싼 모델)
MEDIA_S3_IMAGE_QUALITY = "low"              # low / medium / high (높을수록 비쌈)
MEDIA_S3_TEXT_MODEL = "gpt-4.1-mini"        # 스토리보드, 프롬프트 한국어 번역
MEDIA_S3_VIDEO_MODEL = "bytedance/seedance-2.5/text-to-video"   # 영상 초안 (Higgsfield API, 선불 잔액에서 차감)
MEDIA_S3_VIDEO_SECONDS = 5                  # 4~30초 (길수록 비쌈)
MEDIA_S3_VIDEO_RESOLUTION = "720p"          # 480p / 720p / 1080p (높을수록 비쌈)
MEDIA_S3_VIDEO_ASPECT = "16:9"              # 가로 영상
MEDIA_S3_VIDEO_AUDIO = False                # 초안이라 소리 없이
MEDIA_S3_STORYBOARD_COLS = ["장면", "길이(초)", "화면", "움직임", "자막", "피할 것"]

MEDIA_S3_STORYBOARD_SYSTEM = """너는 amazon.de(독일)에서 파는 냉감패드의 상품 영상 스토리보드 작가야.
외주 영상팀이 보고 촬영할 15~20초 스토리보드를 만들어.

반드시 지킬 것
1. 장면은 4~6개, 순서는 문제 → 해결 → 증거 → 신뢰 → 마무리 흐름을 따라.
2. 사진 프롬프트 A(지금 사진)와 B(바꿀 사진)의 구도를 해결·증거 장면에 그대로 써.
3. 넣을 것은 아래 "허용 장면"과 "쓸 수 있는 문구", "서리 강점"에 있는 것만 써. 수치·인증·효과를 지어내지 마.
4. "금지 표현"과 "찍지 말 것"에 걸리는 연출·자막은 쓰지 마. (예: 얼음·서리 연출, 체온을 낮춘다, 친환경 포괄 표현)
5. 자막은 독일어 존댓말(Sie)로, 쓸 수 있는 문구를 그대로 쓰거나 비워 둬.
6. 각 장면의 "피할 것"에는 그 장면에서 촬영팀이 실수하기 쉬운 금지 연출을 한국어로 적어.
7. JSON만 답해. 형식: {"scenes": [{"장면": "1 문제", "길이(초)": 3, "화면": "...", "움직임": "...", "자막": "...", "피할 것": "..."}]}
"""


class MediaS3AIError(Exception):
    """AI 호출 실패 (화면에 경고로 보여 줌)."""


def media_s3_ai_ready(key: str = "OPENAI_API_KEY") -> bool:
    """secrets.toml에 key(기본 OPENAI_API_KEY, 영상은 HF_KEY)가 들어 있는지."""
    try:
        return bool(str(st.secrets.get(key, "")).strip())
    except Exception:   # secrets.toml이 아예 없을 때
        return False


def _media_s3_client():
    try:
        from openai import OpenAI
    except ImportError as err:
        raise MediaS3AIError("openai 라이브러리가 없어요. 터미널에서 pip install -r requirements.txt 를 실행해 주세요.") from err
    return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


def media_s3_make_image(prompt: str) -> bytes:
    """프롬프트로 사진 초안 1장(PNG)을 만듭니다."""
    try:
        res = _media_s3_client().images.generate(model=MEDIA_S3_IMAGE_MODEL, prompt=prompt, size="1536x1024",
                                                 quality=MEDIA_S3_IMAGE_QUALITY, n=1)
        return base64.b64decode(res.data[0].b64_json)
    except MediaS3AIError:
        raise
    except Exception as err:
        raise MediaS3AIError(f"사진을 만들지 못했어요: {err}") from err


def media_s3_storyboard_message(src: dict, report: dict) -> str:
    """스토리보드 AI에게 보내는 재료 (2단계 프롬프트 + 리포트 값)."""
    claims = report.get("ad_claims") or {}
    strength = (report.get("seori_profile") or {}).get("strength", "")
    lines = [f"[단일 변수] {src['variable']}",
             f"[사진 프롬프트 A] {src['prompt_a']}",
             f"[사진 프롬프트 B] {src['prompt_b']}",
             f"[허용 장면] {claims.get('allowed_scenes', '')}",
             "[쓸 수 있는 문구]", *[f"- {c.get('topic', '')}: {c.get('de', '')} (필수 표기: {c.get('must', '')})"
                                    for c in claims.get("claims") or []],
             f"[서리 강점] {strength}",
             "[금지 표현]", *[f"- {f}" for f in claims.get("forbidden") or []],
             "[찍지 말 것]", *[f"- {a}" for a in src.get("avoid") or []]]
    return "\n".join(lines)


def media_s3_make_storyboard(src: dict, report: dict) -> list:
    """리포트 값으로 스토리보드 장면 목록을 만듭니다. 형식이 틀리면 오류."""
    try:
        res = _media_s3_client().chat.completions.create(
            model=MEDIA_S3_TEXT_MODEL, response_format={"type": "json_object"}, temperature=0.4,
            messages=[{"role": "system", "content": MEDIA_S3_STORYBOARD_SYSTEM},
                      {"role": "user", "content": media_s3_storyboard_message(src, report)}])
        scenes = json.loads(res.choices[0].message.content)["scenes"]
    except MediaS3AIError:
        raise
    except Exception as err:
        raise MediaS3AIError(f"스토리보드를 만들지 못했어요: {err}") from err
    rows = []
    for s in scenes if isinstance(scenes, list) else []:
        if isinstance(s, dict) and s.get("화면"):
            row = {c: s.get(c, "") for c in MEDIA_S3_STORYBOARD_COLS}
            try:
                row["길이(초)"] = int(row["길이(초)"] or 0)
            except (TypeError, ValueError):
                row["길이(초)"] = 0
            rows.append(row)
    if not rows:
        raise MediaS3AIError("AI가 장면을 돌려주지 않았어요. 다시 눌러 주세요.")
    return rows


def media_s3_forbidden_hits(rows: list, report: dict) -> list:
    """스토리보드에 금지 표현(독일어 단어 부분)이 남았는지 찾습니다."""
    words = []
    for f in ((report.get("ad_claims") or {}).get("forbidden") or []):
        head = f.split("(")[0]
        words += [w.strip() for w in head.replace("/", "·").split("·") if len(w.strip()) > 3]
    text = " ".join(" ".join(str(v) for v in r.values()) for r in rows).lower()
    return [w for w in words if w.lower() in text]


def _media_s3_video_url(result) -> str:
    """Higgsfield 결과에서 영상 주소를 찾습니다 (결과는 video 칸에 들어옴)."""
    video = result.get("video") if isinstance(result, dict) else None
    if isinstance(video, list):
        video = video[0] if video else None
    if isinstance(video, dict):
        return video.get("url", "")
    return video if isinstance(video, str) else ""


def _media_s3_make_video_api(prompt: str, on_status=None) -> bytes:
    """(API 잔액 사용) 영상 프롬프트로 영상 초안(MP4)을 만듭니다 (Higgsfield Seedance 2.5)."""
    try:
        import higgsfield_client
        import requests
    except ImportError as err:
        raise MediaS3AIError("higgsfield-client 라이브러리가 없어요. 터미널에서 pip install -r requirements.txt 를 실행해 주세요.") from err
    os.environ["HF_KEY"] = st.secrets["HF_KEY"]   # SDK가 환경 변수 HF_KEY를 읽음 (값은 화면·로그에 쓰지 않음)
    try:
        result = higgsfield_client.subscribe(
            MEDIA_S3_VIDEO_MODEL,
            arguments={"prompt": prompt, "duration": MEDIA_S3_VIDEO_SECONDS, "resolution": MEDIA_S3_VIDEO_RESOLUTION,
                       "aspect_ratio": MEDIA_S3_VIDEO_ASPECT, "generate_audio": MEDIA_S3_VIDEO_AUDIO},
            on_queue_update=(lambda status: on_status(type(status).__name__)) if on_status else None)
    except Exception as err:
        if isinstance(err, higgsfield_client.InsufficientCreditsError) or "credit" in str(err).lower():
            raise MediaS3AIError("Higgsfield API 잔액이 부족해요. 사이트 구독(울트라 등) 크레딧과는 별개라, "
                                 "API 콘솔의 Billing에서 따로 충전해야 해요 (최소 $5). "
                                 "또는 아래 영상 프롬프트를 higgsfield.ai 사이트에 붙여 만들고 작업 공간에 올려 주세요.") from err
        raise MediaS3AIError(f"영상을 만들지 못했어요: {err}") from err
    url = _media_s3_video_url(result)
    if not url:   # 실패·취소·검열(NSFW)이면 영상 주소가 없음
        raise MediaS3AIError("영상이 만들어지지 않았어요 (실패·취소·검열). 프롬프트를 바꿔 다시 눌러 주세요.")
    try:
        res = requests.get(url, timeout=120)
        res.raise_for_status()
        return res.content
    except Exception as err:
        raise MediaS3AIError(f"만든 영상을 내려받지 못했어요: {err}") from err


def media_s3_video_ready() -> str:
    """영상을 만들 수 있는 길: "mcp"(Higgsfield 계정 로그인, 구독 크레딧) / "api"(HF_KEY, API 잔액) / ""(없음)."""
    from modules.media.media_stage3.media_stage3_hf_mcp import media_s3_hf_ready
    if media_s3_hf_ready():
        return "mcp"
    return "api" if media_s3_ai_ready("HF_KEY") else ""


def media_s3_make_video(prompt: str, on_status=None) -> bytes:
    """영상 초안(MP4)을 만듭니다. Higgsfield 계정으로 로그인해 두었으면 구독 크레딧(MCP), 아니면 API 잔액(HF_KEY)을 씁니다."""
    if media_s3_video_ready() == "mcp":
        from modules.media.media_stage3.media_stage3_hf_mcp import MediaS3HFError, media_s3_hf_make_video
        try:
            return media_s3_hf_make_video(prompt, MEDIA_S3_VIDEO_SECONDS, MEDIA_S3_VIDEO_ASPECT, on_status)
        except MediaS3HFError as err:
            raise MediaS3AIError(str(err)) from err
        except Exception as err:
            raise MediaS3AIError(f"영상을 만들지 못했어요: {err}") from err
    return _media_s3_make_video_api(prompt, on_status)


@st.cache_data(show_spinner=False, max_entries=100)
def media_s3_translate(text: str) -> str:
    """프롬프트를 한국어로 번역합니다 ('프롬프트 보기' 팝업용). 같은 문장은 다시 부르지 않고 기억한 번역을 씀."""
    try:
        res = _media_s3_client().chat.completions.create(
            model=MEDIA_S3_TEXT_MODEL, temperature=0,
            messages=[{"role": "system", "content": "다음 이미지·영상 생성 프롬프트를 자연스러운 한국어로 번역해. "
                                                    "줄 바꿈과 번호는 그대로 두고, 이미 한국어인 부분은 그대로 둬. 번역문만 답해."},
                      {"role": "user", "content": text}])
        return res.choices[0].message.content.strip()
    except MediaS3AIError:
        raise
    except Exception as err:
        raise MediaS3AIError(f"번역하지 못했어요: {err}") from err
