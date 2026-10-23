# 4. 날씨 광고 타이밍
from fastapi import APIRouter

router = APIRouter(prefix="/weather")   # 내 주소는 전부 /weather/...


@router.get("/ping")                 # → /weather/ping
def weather_ping():
    return {"module": "weather", "ok": True}
