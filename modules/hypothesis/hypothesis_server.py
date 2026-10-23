# 2. 가설 수립
from fastapi import APIRouter
from pydantic import BaseModel

from server.shared.shared_ai import ask_ai

router = APIRouter(prefix="/hypothesis")   # 내 주소는 전부 /hypothesis/...


@router.get("/ping")                 # → /hypothesis/ping
def hypothesis_ping():
    return {"module": "hypothesis", "ok": True}


# 1. 분석 리포트 탭이 저장하는 문제 하나의 모양 (report 탭 담당자와 이 모양을 맞춰 주세요)
class HypothesisProblem(BaseModel):
    id: str
    title: str
    description: str
    factor: str | None = None   # "internal" | "external"
    target: str | None = None
    metric: str | None = None


class HypothesisGenerateRequest(BaseModel):
    problem: HypothesisProblem


def hypothesis_build_prompt(problem: HypothesisProblem) -> str:
    factor_label = "외부 요인(경쟁사 포함)" if problem.factor == "external" else "내부 요인"
    return (
        "다음은 매장 판매 데이터 분석에서 찾은 문제입니다.\n"
        f"- 문제: {problem.title}\n"
        f"- 설명: {problem.description}\n"
        f"- 요인: {factor_label}\n"
        f"- 관련 타깃/지점: {problem.target or '미지정'}\n"
        f"- 관련 지표: {problem.metric or '미지정'}\n\n"
        "아래 형식에 맞춰 마케팅 가설을 한국어 한 문장으로만 작성해 주세요. 다른 설명은 쓰지 마세요.\n"
        "형식: 만약 [타깃/지점]에 [구체적인 액션]을 적용한다면, "
        "[이유/고객 심리] 때문에 [측정 가능한 지표]가 [얼마나] 개선될 것이다."
    )


# → /hypothesis/generate : 리포트 문제 하나로 가설 문장을 AI에게 만들어 달라고 요청합니다.
# AI가 아직 연결되지 않았으면(ok=False) 화면(hypothesis_script.js)이 규칙 기반으로 대신 채웁니다.
@router.post("/generate")
def hypothesis_generate(body: HypothesisGenerateRequest):
    prompt = hypothesis_build_prompt(body.problem)
    try:
        text = ask_ai(prompt)
        return {"ok": True, "text": text.strip()}
    except NotImplementedError:
        return {"ok": False, "reason": "ai_not_ready"}
