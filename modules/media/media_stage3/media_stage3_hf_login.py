# 3. 매체 제작 > 3단계: Higgsfield 계정 로그인 (처음 한 번만, 터미널에서 실행)
#   python -m modules.media.media_stage3.media_stage3_hf_login
# 브라우저에서 Higgsfield에 로그인하면, 로그인 열쇠(토큰)를 .streamlit/hf_mcp_token.json에 저장합니다.
# 이 파일은 계정 비밀번호와 같아서 .gitignore에 넣어 GitHub에 올라가지 않게 합니다.
# 이후 ④ '영상 초안 만들기'는 이 열쇠로 Higgsfield MCP에 연결해 구독(울트라 등) 크레딧으로 영상을 만듭니다.
import base64
import hashlib
import http.server
import json
import secrets
import sys
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


def media_s3_hf_register() -> str:
    """이 앱을 Higgsfield 로그인 서버에 등록하고 client_id를 받습니다."""
    res = requests.post(f"{MEDIA_S3_HF_AUTH}/register", timeout=30, json={
        "client_name": "miniproject2-media", "redirect_uris": [MEDIA_S3_HF_REDIRECT],
        "grant_types": ["authorization_code", "refresh_token"], "response_types": ["code"],
        "token_endpoint_auth_method": "none", "scope": MEDIA_S3_HF_SCOPE})
    res.raise_for_status()
    return res.json()["client_id"]


def media_s3_hf_save(client_id: str, token: dict) -> None:
    MEDIA_S3_HF_TOKEN_FILE.write_text(json.dumps({
        "client_id": client_id, "access_token": token["access_token"],
        "refresh_token": token.get("refresh_token", ""),
        "expires_at": time.time() + int(token.get("expires_in", 3600)) - 60}), encoding="utf-8")


def main() -> None:
    client_id = media_s3_hf_register()
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    url = f"{MEDIA_S3_HF_AUTH}/authorize?" + urllib.parse.urlencode({
        "response_type": "code", "client_id": client_id, "redirect_uri": MEDIA_S3_HF_REDIRECT,
        "scope": MEDIA_S3_HF_SCOPE, "state": state, "code_challenge": challenge,
        "code_challenge_method": "S256", "resource": MEDIA_S3_HF_MCP_URL,
        "prompt": "login"})   # 이미 로그인된 계정이 있어도 로그인 화면부터 (계정을 바꿀 수 있게)
    got = {}

    class Callback(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("Higgsfield 로그인 완료. 이 창을 닫고 터미널로 돌아가세요.".encode("utf-8"))

        def log_message(self, *args):
            pass

    if "--no-browser" in sys.argv:   # 창을 자동으로 열지 않고 주소만 출력 (시크릿 창 등에 직접 붙여 넣기)
        print("이 주소를 브라우저에 붙여 넣고 로그인한 뒤 허용을 눌러 주세요:\n" + url)
    else:
        print("브라우저에서 Higgsfield 로그인 창이 열려요. 로그인하고 허용을 눌러 주세요.")
        print("창이 안 열리면 이 주소를 브라우저에 붙여 넣으세요:\n" + url)
        webbrowser.open(url)
    with http.server.HTTPServer(("127.0.0.1", MEDIA_S3_HF_PORT), Callback) as server:
        while "code" not in got and "error" not in got:
            server.handle_request()
    if got.get("error") or got.get("state") != state:
        raise SystemExit(f"로그인이 취소되었거나 실패했어요: {got.get('error_description') or got.get('error') or 'state 불일치'}")
    res = requests.post(f"{MEDIA_S3_HF_AUTH}/token", timeout=30, data={
        "grant_type": "authorization_code", "code": got["code"], "redirect_uri": MEDIA_S3_HF_REDIRECT,
        "client_id": client_id, "code_verifier": verifier, "resource": MEDIA_S3_HF_MCP_URL})
    res.raise_for_status()
    media_s3_hf_save(client_id, res.json())
    print(f"완료! 로그인 열쇠를 저장했어요: {MEDIA_S3_HF_TOKEN_FILE}")


if __name__ == "__main__":
    main()
