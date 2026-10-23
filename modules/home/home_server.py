# 홈
from fastapi import APIRouter

router = APIRouter(prefix="/home")   # 내 주소는 전부 /home/...


@router.get("/ping")                 # → /home/ping
def home_ping():
    return {"module": "home", "ok": True}
