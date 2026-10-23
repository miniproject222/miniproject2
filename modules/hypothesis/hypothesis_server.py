# 2. 가설 수립
from fastapi import APIRouter

router = APIRouter(prefix="/hypothesis")   # 내 주소는 전부 /hypothesis/...


@router.get("/ping")                 # → /hypothesis/ping
def hypothesis_ping():
    return {"module": "hypothesis", "ok": True}
