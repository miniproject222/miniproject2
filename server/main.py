# 서버 실행, 6개 모듈 서버 연결 (PM)
# 실행: 프로젝트 맨 위 폴더에서 uvicorn server.main:app --reload
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")   # 모듈을 불러오기 전에 .env를 먼저 읽습니다

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from modules.home.home_server import router as home_router  # noqa: E402
from modules.report.report_server import router as report_router  # noqa: E402
from modules.hypothesis.hypothesis_server import router as hypothesis_router  # noqa: E402
from modules.media.media_server import router as media_router  # noqa: E402
from modules.solution.solution_server import router as solution_router  # noqa: E402
from modules.weather.weather_server import router as weather_router  # noqa: E402

app = FastAPI(title="마케팅 솔루션 대시보드")

# Live Server 등 다른 주소에서 index.html을 열어도 호출되도록 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 모듈 서버 연결
app.include_router(home_router)
app.include_router(report_router)
app.include_router(hypothesis_router)
app.include_router(media_router)
app.include_router(solution_router)
app.include_router(weather_router)

# 화면 파일 (http://localhost:8000 에서 대시보드 열기)
app.mount("/common", StaticFiles(directory=ROOT_DIR / "common"), name="common")
app.mount("/modules", StaticFiles(directory=ROOT_DIR / "modules"), name="modules")


@app.get("/")
def index():
    return FileResponse(ROOT_DIR / "index.html")
