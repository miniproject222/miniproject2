# 1. 분석 리포트
from fastapi import APIRouter

router = APIRouter(prefix="/report")   # 내 주소는 전부 /report/...


@router.get("/ping")                 # → /report/ping
def report_ping():
    return {"module": "report", "ok": True}
