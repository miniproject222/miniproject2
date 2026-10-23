# AI 호출 (PM)
# 사용: from server.shared.shared_ai import ask_ai
import os

AI_API_KEY = os.getenv("AI_API_KEY")


def ask_ai(prompt: str) -> str:
    """프롬프트를 AI에 보내고 답변 텍스트를 돌려줍니다. (AI 확정 후 구현)"""
    raise NotImplementedError("AI 서비스 확정 후 구현 예정")
