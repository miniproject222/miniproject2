# 3-1. 솔루션 제안
from fastapi import APIRouter

router = APIRouter(prefix="/solution")   # 내 주소는 전부 /solution/...


@router.get("/ping")                 # → /solution/ping
def solution_ping():
    return {"module": "solution", "ok": True}
