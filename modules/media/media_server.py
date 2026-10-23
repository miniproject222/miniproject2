# 3. 매체 제작
from fastapi import APIRouter

router = APIRouter(prefix="/media")   # 내 주소는 전부 /media/...


@router.get("/ping")                 # → /media/ping
def media_ping():
    return {"module": "media", "ok": True}
