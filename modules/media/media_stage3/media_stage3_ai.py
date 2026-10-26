# 3. 매체 제작 > 3단계 ④: AI로 사진 초안·스토리보드(OpenAI), 영상 초안(Higgsfield: 로그인 시 Seedance 2.0 fast, API 잔액이면 Seedance 2.5) 만들기
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
MEDIA_S3_VIDEO_SECONDS = 10                 # 4~30초 (길수록 비쌈). 초안 A·B 각 10초
MEDIA_S3_VIDEO_HOOK = 3                     # A·B가 다른 첫 장면 길이(초). 나머지 장면은 A·B 공통
MEDIA_S3_VIDEO_RESOLUTION = "480p"          # 480p / 720p / 1080p (높을수록 비쌈·느림). 초안이라 480p (10초 30크레딧)
MEDIA_S3_VIDEO_ASPECT = "16:9"              # 가로 영상
MEDIA_S3_VIDEO_AUDIO = False                # 초안이라 소리 없이
MEDIA_S3_STORYBOARD_COLS = ["장면", "길이(초)", "화면", "움직임", "자막", "피할 것"]

MEDIA_S3_STORYBOARD_SYSTEM = """너는 독일 자사몰에 올릴 냉감패드 상품 영상의 스토리보드 작가야.
같은 영상을 A·B 두 버전으로 만들어 자사몰에서 클릭률을 비교하는 실험용이야. 외주 영상팀이 이 표를 보고 한 번 촬영해서 두 버전으로 편집해.

반드시 지킬 것
1. 영상은 모두 10초. 맨 앞 3초만 A·B가 다르고, 그 뒤 7초(장면 2~3개)는 A·B가 똑같아.
2. 맨 앞 두 줄의 "장면" 이름은 정확히 "1 첫 3초 · A", "1 첫 3초 · B", 길이는 둘 다 3초.
   - 먼저 가설(If·Because)에서 "손님이 몰라서 안 누르는 제품의 장점"을 하나 찾아 (예: 두께, 원단 질감).
   - A(지금 방식): 같은 자리에서 제품을 평범하게 멀리서 보여 줘. 그 장점은 보이지 않게.
   - B(가설): 같은 자리·같은 길이로, 그 장점을 손·카메라 동작으로 눈에 바로 보이게 (예: 손으로 원단 쓸기, 모서리를 들어 두께 클로즈업).
   - A와 B는 이 차이 하나만 달라. 배경·조명·인물·제품 모양은 같게. 첫 3초 A·B에는 자막을 넣지 마 (차이가 화면에만 있게).
   - 가설·분석 문장(클릭률, 가격 차이, 장바구니 비율 등)은 실험 이유일 뿐이야. 자막·화면에 절대 쓰지 마.
3. 공통 장면 이름은 "2 공통 …", "3 공통 …"처럼 쓰고, 마지막은 제품과 자사몰 구매 안내로 끝내.
4. 사진 A/B의 '접힌 패드 vs 펼친 패드' 비교를 영상에 옮기지 마. 영상은 움직이는 장면으로 이유를 보여 줘.
5. 넣을 것은 "가설", "허용 장면", "쓸 수 있는 문구", "서리 강점"에 있는 것만. 수치·인증·효과를 지어내지 마.
6. "금지 표현"과 "찍지 말 것"에 걸리는 연출·자막은 쓰지 마. (예: 얼음·서리 연출, 체온을 낮춘다, 친환경 포괄 표현)
7. 소리 없이 자동 재생되는 영상이야. 자막은 독일어 존댓말(Sie)로 짧게, 쓸 수 있는 문구를 그대로 쓰거나 비워 둬.
   수치(Q-max, °C)를 쓰면 그 문구의 필수 표기(완제품·시험 조건 등)를 줄이지 말고 그대로 써. 길면 수치를 빼고 인증·제품명만 써.
8. 각 장면의 "피할 것"에는 그 장면에서 촬영팀이 실수하기 쉬운 금지 연출을 한국어로 적어.
9. JSON만 답해. 형식: {"scenes": [{"장면": "1 첫 3초 · A", "길이(초)": 3, "화면": "...", "움직임": "...", "자막": "...", "피할 것": "..."}]}
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


MEDIA_S3_SAME_PRODUCT = (
    "Edit this exact photo. It must stay the identical physical product: same color, same fabric texture, "
    "same quilting/stitching pattern and direction, same edge binding, same size proportions, same white background, "
    "same lighting and camera style. Change ONLY this one thing: {change}. "
    "Do not redesign, recolor or replace the product. Details for the result: {prompt}"
)


def media_s3_edit_image(base: bytes, change: str, prompt: str) -> bytes:
    """사진 A(base)를 고쳐서 사진 B를 만듭니다. 처음부터 따로 그리면 다른 제품처럼 나와서, A를 넣고
    바꿀 것(change) 하나만 바꾸게 합니다 (색·원단·누빔 무늬·배경은 A 그대로)."""
    text = MEDIA_S3_SAME_PRODUCT.format(change=change, prompt=prompt)
    image = ("photo_A.png", base, "image/png")
    try:
        client = _media_s3_client()
        try:   # input_fidelity="high": 넣은 사진의 무늬·질감을 최대한 그대로 (지원 안 하는 모델이면 빼고 다시)
            res = client.images.edit(model=MEDIA_S3_IMAGE_MODEL, image=image, prompt=text, size="1536x1024",
                                     quality=MEDIA_S3_IMAGE_QUALITY, input_fidelity="high", n=1)
        except Exception as err:
            if "input_fidelity" not in str(err):
                raise
            res = client.images.edit(model=MEDIA_S3_IMAGE_MODEL, image=image, prompt=text, size="1536x1024",
                                     quality=MEDIA_S3_IMAGE_QUALITY, n=1)
        return base64.b64decode(res.data[0].b64_json)
    except MediaS3AIError:
        raise
    except Exception as err:
        raise MediaS3AIError(f"사진 B를 만들지 못했어요: {err}") from err


def media_s3_storyboard_message(src: dict, report: dict, hypo: dict | None = None) -> str:
    """스토리보드 AI에게 보내는 재료: 2번 탭 가설(If·Because·Then) + 리포트 값(광고 문구·허용 장면·금지 표현).
    사진 프롬프트 A·B는 넣지 않습니다 (사진의 '접힘 vs 펼침'이 영상에 그대로 옮겨져 어색했음)."""
    claims = report.get("ad_claims") or {}
    strength = (report.get("seori_profile") or {}).get("strength", "")
    listing = ((report.get("sqp") or {}).get("listing") or {})
    hypo = hypo or {}
    lines = [f"[가설 문장] {hypo.get('text') or '-'}",
             f"[가설 If] {hypo.get('if') or '-'}",
             f"[가설의 이유 Because → B의 첫 3초에 보이게] {hypo.get('because') or '-'}",
             f"[가설 Then] {hypo.get('then') or '-'}",
             f"[제품] {listing.get('title') or 'SEORI 냉감패드 90×200 cm'} (사진 A와 같은 색·원단·누빔)",
             f"[허용 장면] {claims.get('allowed_scenes', '')}",
             "[쓸 수 있는 문구]", *[f"- {c.get('topic', '')}: {c.get('de', '')} (필수 표기: {c.get('must', '')})"
                                    for c in claims.get("claims") or []],
             f"[서리 강점] {strength}",
             "[금지 표현]", *[f"- {f}" for f in claims.get("forbidden") or []],
             "[찍지 말 것]", *[f"- {a}" for a in media_s3_video_avoid(src)]]
    return "\n".join(lines)


def media_s3_video_avoid(src: dict) -> list:
    """2단계 '찍지 말 것' 중 영상에도 맞는 것만. 아마존 메인 사진 전용 규칙(손·인물·텍스트·로고·메인 이미지)은 뺌
    (영상은 손으로 원단을 쓸고 자막을 넣어야 해서)."""
    photo_only = ("손", "인물", "텍스트", "로고", "워터마크", "소품", "메인 이미지", "hand", "text", "logo")
    return [a for a in src.get("avoid") or [] if not any(w in str(a) for w in photo_only)]


def media_s3_make_storyboard(src: dict, report: dict, hypo: dict | None = None) -> list:
    """가설·리포트 값으로 A·B 영상 스토리보드(첫 3초 A·B + 공통 장면)를 만듭니다. 형식이 틀리면 오류."""
    try:
        res = _media_s3_client().chat.completions.create(
            model=MEDIA_S3_TEXT_MODEL, response_format={"type": "json_object"}, temperature=0.4,
            messages=[{"role": "system", "content": MEDIA_S3_STORYBOARD_SYSTEM},
                      {"role": "user", "content": media_s3_storyboard_message(src, report, hypo)}])
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
    hooks = [r["장면"] for r in rows if media_s3_scene_version(r) in ("A", "B")]
    if sorted(media_s3_scene_version({"장면": h}) for h in hooks) != ["A", "B"]:
        raise MediaS3AIError("AI가 첫 3초 A·B 장면을 제대로 나누지 않았어요. 다시 눌러 주세요.")
    return rows


def media_s3_scene_version(row: dict) -> str:
    """스토리보드 한 줄이 어느 버전인지: '1 첫 3초 · A' → "A", '… · B' → "B", 공통 장면 → ""."""
    name = str(row.get("장면") or "").strip()
    if "첫" in name and name[-1:] in ("A", "B"):
        return name[-1]
    return ""


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
                                                    "영어뿐 아니라 독일어 등 다른 외국어(예: 자막)도 모두 한국어로 옮겨. "
                                                    "자막처럼 따옴표 안의 외국어 문장은 원문을 두고 바로 뒤 괄호에 한국어 뜻을 붙여 "
                                                    "(예: „Über 26 °C im Schlafzimmer?\" (침실이 26°C를 넘나요?)). "
                                                    "줄 바꿈과 번호는 그대로 두고, 이미 한국어인 부분은 그대로 둬. 번역문만 답해."},
                      {"role": "user", "content": text}])
        return res.choices[0].message.content.strip()
    except MediaS3AIError:
        raise
    except Exception as err:
        raise MediaS3AIError(f"번역하지 못했어요: {err}") from err
