# 3. 매체 제작 > 3단계: Higgsfield 계정 로그인 (컴퓨터마다 처음 한 번)
# ④ '영상 초안 제작'의 'Higgsfield 로그인 창 열기' 버튼을 누르면 시크릿 창으로 로그인 화면이 뜹니다.
# 터미널로도 할 수 있어요:  python -m modules.media.media_stage3.media_stage3_hf_login [--no-browser]
# 로그인하면 로그인 열쇠(토큰)를 .streamlit/hf_mcp_token.json에 저장합니다.
# 이 파일은 계정 비밀번호와 같아서 .gitignore에 넣어 GitHub에 올라가지 않게 합니다.
# 이후 ④ '영상 초안 만들기'는 이 열쇠로 Higgsfield MCP에 연결해 구독(울트라 등) 크레딧으로 영상을 만듭니다.
import base64
import hashlib
import http.server
import json
import os
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path

import requests

MEDIA_S3_HF_MCP_URL = "https://mcp.higgsfield.ai/mcp"
MEDIA_S3_HF_AUTH = "https://mcp.higgsfield.ai/oauth2"
MEDIA_S3_HF_TOKEN_FILE = Path(__file__).resolve().parents[3] / ".streamlit" / "hf_mcp_token.json"
MEDIA_S3_HF_PORT = 8765
MEDIA_S3_HF_REDIRECT = f"http://127.0.0.1:{MEDIA_S3_HF_PORT}/callback"
MEDIA_S3_HF_SCOPE = "openid email offline_access"
MEDIA_S3_HF_LOGIN_WAIT = 600   # 로그인 창을 연 뒤 기다리는 최대 시간(초)

# 지금 진행 중인 로그인 (앱이 다시 그려져도 같은 것을 씀): {"thread", "url", "error"}
_media_s3_hf_login = {}


def media_s3_hf_register() -> str:
    """이 앱을 Higgsfield 로그인 서버에 등록하고 client_id를 받습니다."""
    res = requests.post(f"{MEDIA_S3_HF_AUTH}/register", timeout=30, json={
        "client_name": "miniproject2-media", "redirect_uris": [MEDIA_S3_HF_REDIRECT],
        "grant_types": ["authorization_code", "refresh_token"], "response_types": ["code"],
        "token_endpoint_auth_method": "none", "scope": MEDIA_S3_HF_SCOPE})
    res.raise_for_status()
    return res.json()["client_id"]


def media_s3_hf_save(client_id: str, token: dict) -> None:
    MEDIA_S3_HF_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEDIA_S3_HF_TOKEN_FILE.write_text(json.dumps({
        "client_id": client_id, "access_token": token["access_token"],
        "refresh_token": token.get("refresh_token", ""),
        "expires_at": time.time() + int(token.get("expires_in", 3600)) - 60}), encoding="utf-8")


def media_s3_hf_logout() -> None:
    """로그인 열쇠를 지웁니다 (다른 계정으로 다시 로그인할 때)."""
    MEDIA_S3_HF_TOKEN_FILE.unlink(missing_ok=True)


def media_s3_hf_open_private(url: str) -> None:
    """로그인 주소를 시크릿 창으로 엽니다 (이미 로그인된 다른 계정이 끼어들지 않게). 크롬·엣지가 없으면 기본 브라우저."""
    candidates = [("chrome", "--incognito"), ("msedge", "--inprivate")]
    win_paths = {"chrome": [r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
                            r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
                            r"%LocalAppData%\Google\Chrome\Application\chrome.exe"],
                 "msedge": [r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
                            r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"]}
    mac_paths = {"chrome": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                 "msedge": "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"}
    for name, flag in candidates:
        found = [os.path.expandvars(p) for p in win_paths[name]] + [mac_paths[name]]
        found += [shutil.which(n) or "" for n in (name, "google-chrome", "chromium")]
        for exe in found:
            if exe and Path(exe).exists():
                subprocess.Popen([exe, flag, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
    webbrowser.open(url)


def _media_s3_hf_login_url():
    """등록하고 로그인 주소를 만듭니다. (주소, client_id, state, verifier)"""
    client_id = media_s3_hf_register()
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    url = f"{MEDIA_S3_HF_AUTH}/authorize?" + urllib.parse.urlencode({
        "response_type": "code", "client_id": client_id, "redirect_uri": MEDIA_S3_HF_REDIRECT,
        "scope": MEDIA_S3_HF_SCOPE, "state": state, "code_challenge": challenge,
        "code_challenge_method": "S256", "resource": MEDIA_S3_HF_MCP_URL,
        "prompt": "login"})   # 이미 로그인된 계정이 있어도 로그인 화면부터 (계정을 바꿀 수 있게)
    return url, client_id, state, verifier


def _media_s3_hf_login_wait(server, client_id: str, state: str, verifier: str) -> None:
    """로그인 창에서 돌아오는 주소(callback)를 기다렸다가 열쇠를 받아 저장합니다."""
    got = {}

    class Callback(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("Higgsfield 로그인 완료. 이 창을 닫고 앱으로 돌아가세요.".encode("utf-8"))

        def log_message(self, *args):
            pass

    server.RequestHandlerClass = Callback
    server.timeout = 5
    start = time.time()
    with server:
        while "code" not in got and "error" not in got:
            if time.time() - start > MEDIA_S3_HF_LOGIN_WAIT:
                raise RuntimeError("로그인 시간이 지났어요. 버튼을 다시 눌러 주세요.")
            server.handle_request()
    if got.get("error") or got.get("state") != state:
        raise RuntimeError(f"로그인이 취소되었거나 실패했어요: {got.get('error_description') or got.get('error') or 'state 불일치'}")
    res = requests.post(f"{MEDIA_S3_HF_AUTH}/token", timeout=30, data={
        "grant_type": "authorization_code", "code": got["code"], "redirect_uri": MEDIA_S3_HF_REDIRECT,
        "client_id": client_id, "code_verifier": verifier, "resource": MEDIA_S3_HF_MCP_URL})
    res.raise_for_status()
    media_s3_hf_save(client_id, res.json())


def media_s3_hf_login_start(open_window: bool = True) -> str:
    """앱 버튼용: 로그인 창을 열고 뒤에서 결과를 기다립니다 (화면은 멈추지 않음). 로그인 주소를 돌려줍니다.
    이미 기다리는 중이면 같은 주소를 돌려줍니다 (버튼을 여러 번 눌러도 창만 다시 열림)."""
    t = _media_s3_hf_login.get("thread")
    if t and t.is_alive():
        if open_window:
            media_s3_hf_open_private(_media_s3_hf_login["url"])
        return _media_s3_hf_login["url"]
    url, client_id, state, verifier = _media_s3_hf_login_url()
    server = http.server.HTTPServer(("127.0.0.1", MEDIA_S3_HF_PORT), http.server.BaseHTTPRequestHandler)

    def run():
        try:
            _media_s3_hf_login_wait(server, client_id, state, verifier)
        except Exception as err:   # 실패 이유는 앱 화면에 보여 줌
            _media_s3_hf_login["error"] = str(err)

    _media_s3_hf_login.clear()
    _media_s3_hf_login.update(url=url, error="", thread=threading.Thread(target=run, daemon=True))
    _media_s3_hf_login["thread"].start()
    if open_window:
        media_s3_hf_open_private(url)
    return url


def media_s3_hf_login_status() -> tuple[str, str]:
    """앱 화면용 로그인 상태: ("done", "") / ("waiting", 주소) / ("error", 이유) / ("none", "")."""
    if MEDIA_S3_HF_TOKEN_FILE.exists():
        return "done", ""
    t = _media_s3_hf_login.get("thread")
    if t and t.is_alive():
        return "waiting", _media_s3_hf_login["url"]
    if _media_s3_hf_login.get("error"):
        return "error", _media_s3_hf_login["error"]
    return "none", ""


def main() -> None:
    url, client_id, state, verifier = _media_s3_hf_login_url()
    if "--no-browser" in sys.argv:   # 창을 자동으로 열지 않고 주소만 출력 (시크릿 창 등에 직접 붙여 넣기)
        print("이 주소를 브라우저에 붙여 넣고 로그인한 뒤 허용을 눌러 주세요:\n" + url)
    else:
        print("시크릿 창으로 Higgsfield 로그인 화면이 열려요. 로그인하고 허용을 눌러 주세요.")
        print("창이 안 열리면 이 주소를 브라우저에 붙여 넣으세요:\n" + url)
        media_s3_hf_open_private(url)
    server = http.server.HTTPServer(("127.0.0.1", MEDIA_S3_HF_PORT), http.server.BaseHTTPRequestHandler)
    try:
        _media_s3_hf_login_wait(server, client_id, state, verifier)
    except RuntimeError as err:
        raise SystemExit(str(err)) from err
    print(f"완료! 로그인 열쇠를 저장했어요: {MEDIA_S3_HF_TOKEN_FILE}")


if __name__ == "__main__":
    main()
