# 3. 매체 제작 > 3단계 ④: Higgsfield MCP로 영상 만들기 (구독 크레딧 사용, API 잔액 불필요)
# 로그인 열쇠는 ④의 로그인 버튼(media_stage3_hf_login.py)이 저장한 .streamlit/hf_mcp_token.json을 씁니다 (만료되면 자동 갱신).
# MCP 서버(https://mcp.higgsfield.ai/mcp)의 도구 generate_video → job_status(sync)를 차례로 부릅니다.
import json
import time

import requests

from modules.media.media_stage3.media_stage3_hf_login import (MEDIA_S3_HF_AUTH, MEDIA_S3_HF_MCP_URL,
                                                               MEDIA_S3_HF_TOKEN_FILE, media_s3_hf_logout,
                                                               media_s3_hf_save)

MEDIA_S3_HF_MODEL = "seedance_2_0"   # Higgsfield 모델 이름 (MCP 카탈로그 기준). 2026-10-26 실측: 10초 A·B 동시 약 2분 (2.5는 약 5분)
MEDIA_S3_HF_MODE = "fast"            # seedance_2_0의 빠른 모드 (480p·720p만, 10초 10크레딧)
MEDIA_S3_HF_WAIT = 600               # 영상 완성까지 최대 기다리는 시간(초)
MEDIA_S3_HF_RESOLUTION = "480p"      # 초안이라 480p
MEDIA_S3_HF_AUDIO = False            # 자사몰 자동 재생은 소리 없이 → 소리 안 만듦


class MediaS3HFError(Exception):
    """Higgsfield MCP 호출 실패 (화면에 경고로 보여 줌)."""


def media_s3_hf_ready() -> bool:
    """로그인 열쇠 파일이 있는지 (컴퓨터마다 처음 한 번 ④에서 로그인 필요)."""
    return MEDIA_S3_HF_TOKEN_FILE.exists()


def _media_s3_hf_token() -> str:
    """저장된 열쇠를 읽고, 만료됐으면 refresh_token으로 새로 받습니다."""
    saved = json.loads(MEDIA_S3_HF_TOKEN_FILE.read_text(encoding="utf-8"))
    if time.time() < saved.get("expires_at", 0):
        return saved["access_token"]
    if not saved.get("refresh_token"):
        media_s3_hf_logout()   # 지워야 화면에 로그인 버튼이 다시 나옴
        raise MediaS3HFError("Higgsfield 로그인이 만료됐어요. 'Higgsfield 로그인 창 열기'로 다시 로그인해 주세요.")
    res = requests.post(f"{MEDIA_S3_HF_AUTH}/token", timeout=30, data={
        "grant_type": "refresh_token", "refresh_token": saved["refresh_token"],
        "client_id": saved["client_id"], "resource": MEDIA_S3_HF_MCP_URL})
    if not res.ok:
        media_s3_hf_logout()
        raise MediaS3HFError("Higgsfield 로그인 갱신에 실패했어요. 'Higgsfield 로그인 창 열기'로 다시 로그인해 주세요.")
    token = res.json()
    token.setdefault("refresh_token", saved["refresh_token"])
    media_s3_hf_save(saved["client_id"], token)
    return token["access_token"]


class MediaS3HFSession:
    """MCP 연결 하나 (initialize → tools/call). 요청·응답은 JSON 또는 SSE로 옵니다."""

    def __init__(self):
        self.headers = {"Authorization": f"Bearer {_media_s3_hf_token()}", "Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream"}
        self.next_id = 0
        res = self._post({"method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "miniproject2-media", "version": "1"}}})
        sid = res.headers.get("Mcp-Session-Id")
        if sid:
            self.headers["Mcp-Session-Id"] = sid
        self._post({"method": "notifications/initialized"}, notify=True)

    def _post(self, body: dict, notify: bool = False):
        body = {"jsonrpc": "2.0", **body}
        if not notify:
            self.next_id += 1
            body["id"] = self.next_id
        res = requests.post(MEDIA_S3_HF_MCP_URL, headers=self.headers, json=body, timeout=60)
        if res.status_code == 401:
            media_s3_hf_logout()
            raise MediaS3HFError("Higgsfield 로그인이 풀렸어요. 'Higgsfield 로그인 창 열기'로 다시 로그인해 주세요.")
        if not res.ok:
            raise MediaS3HFError(f"Higgsfield 연결 오류 ({res.status_code}): {res.text[:200]}")
        return res

    @staticmethod
    def _message(res) -> dict:
        """응답 본문에서 JSON-RPC 메시지를 꺼냅니다 (SSE면 data: 줄)."""
        # 본문은 항상 UTF-8로 읽음 (requests가 SSE를 다른 인코딩으로 읽으면 한글 일부가 줄바꿈처럼 잘려 JSON이 깨짐)
        body = res.content.decode("utf-8", errors="replace")
        try:
            if "text/event-stream" not in res.headers.get("Content-Type", ""):
                return json.loads(body) if body.strip() else {}
            # SSE: 이벤트는 빈 줄로 나뉘고, 한 이벤트의 data: 줄이 여러 개면 이어 붙임 (줄은 \n으로만 나눔)
            for event in body.replace("\r\n", "\n").split("\n\n"):
                data = "\n".join(line[5:].lstrip() for line in event.split("\n") if line.startswith("data:"))
                if data:
                    msg = json.loads(data)
                    if "result" in msg or "error" in msg:
                        return msg
            return {}
        except ValueError as err:
            raise MediaS3HFError(f"Higgsfield 응답을 읽지 못했어요: {err}") from err

    def call(self, tool: str, arguments: dict) -> dict:
        """도구를 부르고, 결과 안의 글(JSON)을 dict로 돌려줍니다."""
        msg = self._message(self._post({"method": "tools/call", "params": {"name": tool, "arguments": arguments}}))
        if "error" in msg:
            raise MediaS3HFError(f"Higgsfield 오류: {msg['error'].get('message', msg['error'])}")
        result = msg.get("result") or {}
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return {**structured, "_is_error": result.get("isError", False)}
        text = "\n".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")
        try:
            data = json.loads(text)
        except ValueError:
            data = {"text": text}
        return {**(data if isinstance(data, dict) else {"data": data}), "_is_error": result.get("isError", False)}


def _media_s3_hf_find(obj, keys: tuple):
    """중첩된 결과에서 keys 중 하나의 첫 값을 찾습니다 (응답 모양이 조금 달라도 동작하게)."""
    if isinstance(obj, dict):
        for k in keys:
            if obj.get(k):
                return obj[k]
        for v in obj.values():
            found = _media_s3_hf_find(v, keys)
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _media_s3_hf_find(v, keys)
            if found:
                return found
    return None


def media_s3_hf_cost(prompt: str, seconds: int, aspect: str) -> dict:
    """돈(크레딧)을 쓰지 않고 이 영상의 크레딧 비용만 물어봅니다."""
    return MediaS3HFSession().call("generate_video", {"params": {
        "model": MEDIA_S3_HF_MODEL, "prompt": prompt, "duration": seconds, "aspect_ratio": aspect,
        "mode": MEDIA_S3_HF_MODE, "resolution": MEDIA_S3_HF_RESOLUTION, "generate_audio": MEDIA_S3_HF_AUDIO, "get_cost": True, "use_unlim": False}})


def media_s3_hf_make_video(prompt: str, seconds: int, aspect: str, on_status=None) -> bytes:
    """구독 크레딧으로 영상을 만들고 MP4를 돌려줍니다."""
    s = MediaS3HFSession()
    sent = s.call("generate_video", {"params": {"model": MEDIA_S3_HF_MODEL, "prompt": prompt, "duration": seconds,
                                                "aspect_ratio": aspect, "mode": MEDIA_S3_HF_MODE, "resolution": MEDIA_S3_HF_RESOLUTION,
                                                "generate_audio": MEDIA_S3_HF_AUDIO, "use_unlim": False},
                                     "context": "Draft product video for an outsourcing reference"})
    job_id = _media_s3_hf_find(sent, ("job_id", "id"))
    if sent.get("_is_error") or not job_id:
        raise MediaS3HFError(f"영상 요청이 받아들여지지 않았어요: {str(sent)[:300]}")
    start = time.time()
    while True:
        # job_status(sync)가 진행 상황과 결과 주소(generation.results.rawUrl)를 줌 (jobs_wait에는 주소가 없음)
        done = s.call("job_status", {"jobId": job_id, "sync": True})
        gen = done.get("generation") if isinstance(done.get("generation"), dict) else done
        status = str(gen.get("status") or "")
        if on_status:
            on_status(status or "진행 중")
        url = (gen.get("results") or {}).get("rawUrl") if isinstance(gen.get("results"), dict) else None
        if status.lower() == "completed" and url:
            break
        if status.lower() in ("failed", "canceled", "cancelled", "nsfw", "error"):
            raise MediaS3HFError(f"영상이 만들어지지 않았어요 ({status}). 프롬프트를 바꿔 다시 눌러 주세요.")
        if time.time() - start > MEDIA_S3_HF_WAIT:
            raise MediaS3HFError(f"영상이 너무 오래 걸려요. 조금 뒤 Higgsfield 사이트 기록(History)에서 작업 {job_id}를 확인해 주세요.")
        time.sleep(5)
    res = requests.get(url, timeout=180)
    if not res.ok:
        raise MediaS3HFError("만든 영상을 내려받지 못했어요.")
    return res.content


def media_s3_hf_submit(prompt: str, seconds: int, aspect: str) -> str:
    """영상 요청만 보내고 작업 번호를 돌려줍니다 (완성을 기다리지 않음 → 탭을 옮겨도 계속 만들어짐).
    Higgsfield가 비슷한 프리셋을 추천하면(영상을 만들지 않고 되물음) 추천을 거절하고 프롬프트 그대로 다시 요청합니다."""
    s = MediaS3HFSession()
    params = {"model": MEDIA_S3_HF_MODEL, "prompt": prompt, "duration": seconds, "aspect_ratio": aspect,
              "mode": MEDIA_S3_HF_MODE, "resolution": MEDIA_S3_HF_RESOLUTION, "generate_audio": MEDIA_S3_HF_AUDIO, "use_unlim": False}
    for _ in range(3):
        sent = s.call("generate_video", {"params": params, "context": "Draft product video for an outsourcing reference"})
        notice = sent.get("notice") if isinstance(sent.get("notice"), dict) else {}
        declined = ((notice.get("data") or {}).get("retry_literal_with") or {}).get("declined_preset_id")
        if notice.get("type") == "preset_recommendation" and declined:
            params = {**params, "declined_preset_id": declined}   # 프리셋 말고 프롬프트 그대로
            continue
        # 진짜 작업은 results[].id에만 있음 (notice 안의 id는 프리셋 번호라 쓰면 안 됨)
        results = sent.get("results") if isinstance(sent.get("results"), list) else []
        job_id = results[0].get("id") if results and isinstance(results[0], dict) else None
        if sent.get("_is_error") or not job_id:
            raise MediaS3HFError(f"영상 요청이 받아들여지지 않았어요: {(notice.get('message') or str(sent))[:300]}")
        return job_id
    raise MediaS3HFError("Higgsfield가 계속 프리셋을 추천해서 요청하지 못했어요. 프롬프트를 조금 바꿔 다시 눌러 주세요.")


def media_s3_hf_check(job_id: str) -> tuple[str, str]:
    """작업 상태와 (완성됐으면) 영상 주소를 바로 돌려줍니다. ("completed", url) / ("in_progress", "") / ("failed", "")."""
    done = MediaS3HFSession().call("job_status", {"jobId": job_id, "sync": False})
    if done.get("_is_error") and done.get("errorCode") == 404:   # 없는 작업 번호 → 더 기다리지 않음
        return "not_found", ""
    gen = done.get("generation") if isinstance(done.get("generation"), dict) else done
    results = gen.get("results") if isinstance(gen.get("results"), dict) else {}
    return str(gen.get("status") or "").lower(), results.get("rawUrl") or ""


def media_s3_hf_download(url: str) -> bytes:
    res = requests.get(url, timeout=180)
    if not res.ok:
        raise MediaS3HFError("만든 영상을 내려받지 못했어요.")
    return res.content

