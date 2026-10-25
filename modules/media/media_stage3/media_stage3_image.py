# 3. 매체 제작 > 3단계 ④ 사진 초안: Higgsfield 이미지 생성 API 연결 (화면 코드 없음)
# 2단계에서 다듬은 프롬프트 A·B를 Higgsfield에 보내 '이렇게 찍어 주세요' 견본 사진을 만듭니다.
# - 키: secrets.toml의 HF_KEY ("키ID:키시크릿" 형식)를 함수 안에서만 읽습니다. 새 라이브러리 없이 requests로 부릅니다.
# - 요청은 비동기라서 보내면 요청 번호(request_id)를 받고, 상태를 다시 물어 completed가 되면 사진 주소를 받습니다.
# - 사진 주소는 시간이 지나면 지워지므로(expires_at) 받자마자 내려받아 보관합니다.
# 공식 문서 (2026-10-25 확인): https://docs.higgsfield.ai/docs/quickstart
import uuid
from pathlib import PurePosixPath
from urllib.parse import urlparse

import requests
import streamlit as st

MEDIA_S3_HF_BASE = "https://api.higgsfield.ai"
MEDIA_S3_HF_IMAGE_PATH = "/higgsfield-ai/soul/v2/standard"   # 텍스트 → 이미지 모델 (Soul v2 Standard)
MEDIA_S3_HF_TIMEOUT = 30                                     # 요청 한 번 기다리는 시간 (초)
MEDIA_S3_HF_WAIT_MAX = 300                                   # 사진이 나오기를 기다리는 최대 시간 (초)
MEDIA_S3_HF_PENDING = ("queued", "in_progress")              # 아직 만드는 중인 상태
MEDIA_S3_HF_FAIL = {"failed": "만들지 못했어요", "nsfw": "부적절한 내용으로 판단되어 막혔어요", "canceled": "취소됐어요"}


def media_s3_hf_key() -> str:
    """secrets.toml의 HF_KEY (없으면 빈 문자열)."""
    try:
        return str(st.secrets.get("HF_KEY") or "").strip()
    except Exception:
        return ""


def _media_s3_hf_error(resp) -> RuntimeError:
    """HTTP 오류 → 키가 들어가지 않은 짧은 문구 (공식 문서의 오류 표 기준)."""
    msg = {401: "키 오류 · HF_KEY가 맞는지 확인해 주세요",
           403: "잔액 부족 · Higgsfield 콘솔(console.higgsfield.ai)에서 충전해 주세요",
           404: "요청을 찾지 못했어요", 422: "요청 형식이 맞지 않아요",
           429: "대기열이 가득 찼어요 · 잠시 뒤 다시 눌러 주세요",
           503: "모델이 잠시 쉬는 중이에요 · 잠시 뒤 다시 눌러 주세요"}.get(resp.status_code)
    return RuntimeError(f"Higgsfield {msg or '응답 오류'} (HTTP {resp.status_code})")


def _media_s3_hf_send(method: str, url: str, **kwargs):
    key = media_s3_hf_key()
    if not key:
        raise RuntimeError("secrets.toml에 HF_KEY가 없어요")
    headers = {"Authorization": f"Key {key}", **kwargs.pop("headers", {})}
    try:
        resp = requests.request(method, url, headers=headers, timeout=MEDIA_S3_HF_TIMEOUT, **kwargs)
    except requests.Timeout:
        raise RuntimeError(f"Higgsfield 응답 시간 초과 ({MEDIA_S3_HF_TIMEOUT}초)") from None
    except requests.RequestException as err:
        raise RuntimeError(f"Higgsfield 연결 오류 ({type(err).__name__})") from None   # 오류 문구에 키가 섞이지 않게
    if resp.status_code != 200:
        raise _media_s3_hf_error(resp)
    try:
        return resp.json()
    except ValueError:
        raise RuntimeError("Higgsfield 응답을 읽지 못했어요") from None


def media_s3_hf_submit(prompt: str) -> str:
    """사진 만들기 요청을 보내고 요청 번호를 돌려줍니다. (누를 때마다 Higgsfield 크레딧이 차감됨)"""
    body = _media_s3_hf_send("POST", MEDIA_S3_HF_BASE + MEDIA_S3_HF_IMAGE_PATH, json={"prompt": prompt},
                             headers={"Content-Type": "application/json", "Idempotency-Key": str(uuid.uuid4())})
    request_id = body.get("request_id")
    if not request_id:
        raise RuntimeError("Higgsfield가 요청 번호를 보내지 않았어요")
    return request_id


def media_s3_hf_status(request_id: str) -> dict:
    """요청 상태: {"status", "url"(완료 시 첫 사진 주소), "error"}."""
    body = _media_s3_hf_send("GET", f"{MEDIA_S3_HF_BASE}/requests/{request_id}/status")
    images = body.get("images") or []
    url = images[0].get("url") if images and isinstance(images[0], dict) else ""
    return {"status": str(body.get("status") or ""), "url": url or "", "error": body.get("error") or ""}


def media_s3_hf_download(url: str) -> tuple[bytes, str]:
    """완성된 사진 내려받기 → (내용, 확장자). 사진 주소는 공개 주소라 키를 보내지 않습니다."""
    try:
        resp = requests.get(url, timeout=MEDIA_S3_HF_TIMEOUT)
    except requests.RequestException as err:
        raise RuntimeError(f"사진 내려받기 오류 ({type(err).__name__})") from None
    if resp.status_code != 200 or not resp.content:
        raise RuntimeError(f"사진 내려받기 오류 (HTTP {resp.status_code})")
    ext = PurePosixPath(urlparse(url).path).suffix.lower()
    return resp.content, ext if ext in (".png", ".jpg", ".jpeg", ".webp") else ".png"
