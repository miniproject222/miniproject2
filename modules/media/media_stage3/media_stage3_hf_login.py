# 3. 매체 제작 > 3단계: Higgsfield 계정 로그인 (컴퓨터마다 처음 한 번)
# ④ '영상 초안 제작'의 'Higgsfield 로그인 창 열기' 버튼을 누르면 시크릿 창으로 로그인 화면이 뜹니다.
# 터미널로도 할 수 있어요:  python -m modules.media.media_stage3.media_stage3_hf_login [--no-browser]
# 로그인하면 로그인 열쇠(토큰)를 .streamlit/hf_mcp_token.json에 저장합니다.
# 이 파일은 계정 비밀번호와 같아서 .gitignore에 넣어 GitHub에 올라가지 않게 합니다.
# 이후 ④ '영상 초안 만들기'는 이 열쇠로 Higgsfield MCP에 연결해 구독(울트라 등) 크레딧으로 영상을 만듭니다.
# 2026-10-27: 열쇠를 Supabase(common_store의 "media-hf-token")에도 올려 팀 공용으로 씁니다.
#   배포된 앱(Streamlit Cloud)은 로그인 창을 열 수 없어서, 한 컴퓨터에서 한 번 로그인한 열쇠를 같이 씀.
#   열쇠를 갱신하면(만료 시 자동) 공용 열쇠도 바꿔 두어 모든 컴퓨터가 최신 열쇠를 씀.
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
MEDIA_S3_HF_STORE = "media-hf-token"   # 팀 공용 열쇠를 저장하는 common_store 키
MEDIA_S3_HF_SHARED_TTL = 30            # 화면 상태 확인용으로 공용 열쇠를 다시 읽는 간격(초). 영상을 만들 때는 매번 새로 읽음
# Streamlit Cloud는 코드를 /mount/src 아래에 둠 → 서버에는 브라우저가 없어 로그인 창을 열 수 없음 (공용 열쇠만 씀)
MEDIA_S3_HF_CAN_LOGIN = not Path("/mount/src").exists()
MEDIA_S3_HF_RELOGIN = ("Higgsfield 로그인이 만료됐어요. 앱을 내 컴퓨터에서 켜고 'Higgsfield 로그인 창 열기'로 "
                       "한 번 다시 로그인해 주세요 (팀 전체에 바로 적용돼요).")

# 지금 진행 중인 로그인 (앱이 다시 그려져도 같은 것을 씀): {"thread", "url", "error"}
_media_s3_hf_login = {}
# 마지막으로 읽은 공용 열쇠 {"at": 읽은 시각, "value": 열쇠 dict 또는 None}
_media_s3_hf_shared = {}


def media_s3_hf_register() -> str:
    """이 앱을 Higgsfield 로그인 서버에 등록하고 client_id를 받습니다."""
    res = requests.post(f"{MEDIA_S3_HF_AUTH}/register", timeout=30, json={
        "client_name": "miniproject2-media", "redirect_uris": [MEDIA_S3_HF_REDIRECT],
        "grant_types": ["authorization_code", "refresh_token"], "response_types": ["code"],
        "token_endpoint_auth_method": "none", "scope": MEDIA_S3_HF_SCOPE})
    res.raise_for_status()
    return res.json()["client_id"]


def _media_s3_hf_age(data: dict | None) -> float:
    """열쇠를 저장한 시각 (어느 쪽이 더 최근인지 비교용). 예전 파일에는 saved_at이 없어서 0
    (공용 열쇠가 비어 있으면 그대로 올라가고, 공용 열쇠가 있으면 공용을 씀)."""
    return (data or {}).get("saved_at", 0)


def _media_s3_hf_write_file(data: dict) -> None:
    MEDIA_S3_HF_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEDIA_S3_HF_TOKEN_FILE.write_text(json.dumps(data), encoding="utf-8")


def _media_s3_hf_read_file() -> dict | None:
    try:
        data = json.loads(MEDIA_S3_HF_TOKEN_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("access_token") else None


def _media_s3_hf_read_shared(fresh: bool = False) -> dict | None:
    """Supabase의 공용 열쇠. 화면 확인용은 MEDIA_S3_HF_SHARED_TTL초 동안 마지막 값을 다시 씀 (3초마다 그리는 로그인 칸 때문)."""
    if not fresh and time.time() - _media_s3_hf_shared.get("at", 0) < MEDIA_S3_HF_SHARED_TTL:
        return _media_s3_hf_shared.get("value")
    try:   # common_store를 쓰지 않고 바로 읽음: 이번 접속(session_state)에 기억해 두지 않아야 다른 사람이 갱신한 열쇠를 받음
        from common.common_db import db_read
        rows = db_read("common_store", ttl=0, key=MEDIA_S3_HF_STORE)
        value = rows[0]["value"] if rows else None
    except Exception as err:   # Supabase 연결 전이어도 내 컴퓨터 열쇠로는 동작하게
        print(f"[Higgsfield] 공용 열쇠 읽기 실패: {err}")
        return _media_s3_hf_shared.get("value")
    value = value if isinstance(value, dict) and value.get("access_token") else None
    _media_s3_hf_shared.update(at=time.time(), value=value)
    return value


def _media_s3_hf_write_shared(data: dict | None) -> None:
    try:
        from common.common_db import db_upsert
        db_upsert("common_store", {"key": MEDIA_S3_HF_STORE, "value": data})
        _media_s3_hf_shared.update(at=time.time(), value=data)
    except Exception as err:
        print(f"[Higgsfield] 공용 열쇠 저장 실패: {err}")


def media_s3_hf_load(fresh: bool = False) -> dict | None:
    """쓸 열쇠: 내 컴퓨터 파일과 공용 열쇠 중 더 최근에 저장한 것 (saved_at이 늦은 쪽).
    내 파일이 더 새것이면(방금 로그인·갱신) 공용 열쇠로 올리고, 공용이 더 새것이면(다른 컴퓨터가 갱신) 내 파일을 바꿈."""
    mine, shared = _media_s3_hf_read_file(), _media_s3_hf_read_shared(fresh)
    if mine and (not shared or _media_s3_hf_age(mine) > _media_s3_hf_age(shared)):
        _media_s3_hf_write_shared(mine)
        return mine
    if shared and shared != mine:
        try:
            _media_s3_hf_write_file(shared)
        except OSError:
            pass
    return shared


def media_s3_hf_save(client_id: str, token: dict) -> None:
    """새로 받은 열쇠를 내 파일에 저장하고 공용 열쇠도 바꿉니다
    (로그인 대기는 뒤 작업에서 돌아서 공용 저장이 실패할 수 있음 → 다음 화면에서 media_s3_hf_load가 올림)."""
    data = {"client_id": client_id, "access_token": token["access_token"],
            "refresh_token": token.get("refresh_token", ""),
            "expires_at": time.time() + int(token.get("expires_in", 3600)) - 60, "saved_at": time.time()}
    _media_s3_hf_write_file(data)
    _media_s3_hf_write_shared(data)


def media_s3_hf_expire() -> None:
    """열쇠가 거절됐을 때(401): 지우지 않고 만료로 표시 → 다음 호출에서 refresh_token으로 새로 받음."""
    data = media_s3_hf_load(fresh=True)
    if data:
        data = {**data, "expires_at": 0, "saved_at": time.time()}
        try:
            _media_s3_hf_write_file(data)
        except OSError:
            pass
        _media_s3_hf_write_shared(data)


def media_s3_hf_logout() -> None:
    """로그인 열쇠를 지웁니다 (다른 계정으로 다시 로그인할 때, 갱신도 안 될 때). 공용 열쇠도 같이 지움."""
    MEDIA_S3_HF_TOKEN_FILE.unlink(missing_ok=True)
    _media_s3_hf_write_shared(None)


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
    """앱 화면용 로그인 상태: ("done", "") / ("waiting", 주소) / ("error", 이유) / ("none", "").
    내 컴퓨터 파일이 없어도 공용 열쇠가 있으면 "done" (배포된 앱·다른 컴퓨터)."""
    if media_s3_hf_load():
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
