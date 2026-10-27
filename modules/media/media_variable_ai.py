# 3. 매체 제작 > 가설에서 변수 도출: 가설 하나로 후보 변수 묶음 만들기 (화면 코드 없음)
# 화면(표·버튼)은 media_variable.py에서 그립니다. 가설을 불러올 때만 부릅니다.
# - 어떤 가설이 와도 후보 묶음을 돌려줍니다: AI(Gemini/OpenAI)로 만들고, 키가 없거나 실패하면 규칙으로 만듭니다.
# - 묶음 모양은 예시 파일 data/media_variable_candidates.json의 한 묶음과 같습니다 {"kpi", "note", "variables"}.
#   AI 묶음에는 가설 콜아웃에 보일 짧은 If·Because("short")가 더 붙습니다 (규칙 묶음은 빈 dict).
# - AI 답은 믿지 않고 코드로 다시 확인합니다 (변수 종류, B안 모양, 메인 이미지 규칙에 걸리는 말).
# - 키는 secrets.toml의 GEMINI_API_KEY / OPENAI_API_KEY를 함수 안에서만 읽습니다 (2단계와 같은 키). 새 라이브러리 없이 requests로 부릅니다.
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

import requests
import streamlit as st

# 모델 이름은 2단계(media_stage2_ai.py)와 같게 둡니다 (2026-10-25 2단계 담당 확인 값)
MEDIA_VARIABLE_AI_GEMINI_MODEL = "gemini-3.8-flash"
MEDIA_VARIABLE_AI_OPENAI_MODEL = "gpt-6.1-sol"
MEDIA_VARIABLE_AI_TIMEOUT = 60   # 응답 기다리는 시간 (초)
MEDIA_VARIABLE_AI_PROVIDERS = {"Gemini": "GEMINI_API_KEY", "OpenAI": "OPENAI_API_KEY"}   # 이 순서로 시도
# AI에게 모양을 보여 줄 예시 묶음 (예전 냉감패드 메인 이미지 가설의 후보, 손으로 쓴 것)
MEDIA_VARIABLE_AI_EXAMPLE_FILE = Path(__file__).resolve().parent / "data" / "media_variable_candidates.json"
MEDIA_VARIABLE_AI_RULE_SOURCE = "규칙"   # AI 없이 만든 묶음의 출처 이름
MEDIA_VARIABLE_SHORT_MAX = 30   # 가설 콜아웃에 보일 짧은 If·Because 최대 글자 수 (넘으면 AI 답을 버리고 규칙으로 줄임)

# 변수 종류: kind → (표에 보일 이름, 가설 If에서 찾을 말). 위에서부터 먼저 맞는 종류로 봅니다.
# 메인 이미지는 '이미지'만으로도 걸리므로, '상세 이미지'처럼 메인이 아닌 이미지 종류를 먼저 둡니다.
MEDIA_VARIABLE_KINDS = {
    "title": ("제목", ["제목", "타이틀", "상품명"]),
    "bullet": ("불릿·상세 설명", ["불릿", "상세 설명", "설명 문구"]),
    "a_plus": ("A+·상세 이미지", ["A+", "상세 이미지", "상세 페이지", "서브 이미지"]),
    "price": ("가격·쿠폰", ["가격", "할인", "쿠폰"]),
    "main_image": ("메인 이미지", ["메인 이미지", "대표 이미지", "썸네일", "사진", "이미지"]),
    # 광고·입찰: 이미지가 아닌 광고 설정 가설 (예: 고온일 키워드 입찰 상향)이 메인 이미지 변수로 잘못 이어지지 않게 따로 둠
    "ad": ("광고·입찰", ["입찰", "광고", "키워드", "캠페인", "CPC"]),
    "other": ("가설의 If", []),
}
# 메인 이미지 B안에서 아마존 규칙에 걸리는 말: (찾을 말, 어긴 규칙, 대신 쓸 곳). AI 답과 규칙 묶음 모두 이걸로 다시 확인합니다.
MEDIA_VARIABLE_MAIN_RULES = [
    (["텍스트", "문구", "글자", "로고", "워터마크", "화살표"], "메인 이미지에는 텍스트·로고 금지", "서브 이미지"),
    (["손으로", "손이", "사람", "모델", "소품"], "메인 이미지에는 제품 말고 손·소품 금지", "서브 이미지"),
    (["AI로", "연출", "침실", "라이프스타일"], "메인 이미지는 흰 배경 실제 사진만", "스폰서드 브랜드 광고"),
]
# 단일 변수 확인: 메인 이미지 B안이 통제 변수까지 바꾸는 말 (찾을 말, 이유). 걸리면 B로 쓰지 않고 '다음 테스트'로 돌림.
# (다른 종류 변수 말 - 제목·가격·광고 등 - 이 B안에 들어가도 단일 변수가 아님 → media_variable_single_break())
MEDIA_VARIABLE_CONTROL_RULES = [
    (["조명", "보정", "필터", "밝기"], "통제 변수(조명·보정)까지 바뀜"),
    (["배경색", "색 배경", "컬러 배경", "회색 배경", "검은 배경", "배경을"], "통제 변수(흰 배경)까지 바뀜"),
    (["다른 색상", "색상을", "색상 변경", "다른 제품", "다른 사이즈"], "통제 변수(제품·색상)까지 바뀜"),
]
MEDIA_VARIABLE_B_MIN = 2            # 진행 가능한 메인 이미지 변수에 보여 줄 B안 최소 수 (모자라면 AI에게 다시 요청)
MEDIA_VARIABLE_B_MAX = 3            # 변수 하나에 B로 쓸 수 있는 안 최대 수 (넘으면 앞에서부터)
MEDIA_VARIABLE_B_RETRY = 2          # B안이 MEDIA_VARIABLE_B_MIN개보다 적을 때 다시 요청하는 횟수 (AI 하나당)
MEDIA_VARIABLE_B_SIMILAR = 0.7      # B안 문장끼리 비슷한 정도(difflib 0~1)가 이 이상이면 뒤의 안을 뺌
MEDIA_VARIABLE_AI_VERSION = 4       # 후보 묶음 만드는 규칙의 판. 올리면 같은 가설도 다시 불러올 때 새로 만듦
# 화면(요약 칩·변수 블럭·A/B 표)에 보이는 칸의 최대 글자 수. AI에게는 더 짧게 쓰라고 하고, 넘으면 코드가 줄임
# (name: 괄호 설명을 빼고, 그래도 길면 종류 이름 / label: 잘라서 … / b: B로 쓰지 않음)
MEDIA_VARIABLE_TEXT_MAX = {"name": 16, "label": 12, "b": 60}

MEDIA_VARIABLE_AI_SYSTEM = """너는 amazon.de(독일)에서 냉감패드를 파는 브랜드의 A/B 테스트 설계자야.
가설 하나를 받아, Amazon Manage Your Experiments로 실험할 "후보 변수" 목록을 만들어.

반드시 지킬 것
0. 화면에 보이는 칸(name, label, b, short)은 무조건 짧게, 핵심만 써. 꾸밈말·이유·괄호 설명은 빼고, 글자 수를 꼭 지켜.
1. 변수 하나 = 바꿀 것 하나. 후보는 3~5개.
   name은 "바꿀 곳 + 무엇"만 담은 명사구 (12자 안쪽).
   예: "메인 이미지 촬영 구도" (O), "두께와 원단 질감을 드러내는 메인 이미지 구도" (X), "제목 앞 문구 (OEKO-TEX·두께)" (X)
2. 가설의 If가 바꾸라고 한 변수 딱 하나만 맨 앞에 두고 if_match를 true로 해.
   그 변수의 kind는 If가 말하는 곳과 반드시 같아야 해 (If가 광고·입찰을 바꾸면 ad, 제목이면 title …).
   If가 이미지를 말하지 않으면 main_image 변수를 if_match true로 만들지 마.
   나머지(가설과 다른 대안, 고정해야 할 요소)는 if_match를 false로, reason에 이유, fallback에 대신 쓸 곳("다음 테스트", "고정 요소" 등)을 써.
3. kind는 main_image, title, bullet, a_plus, price, ad, other 중 하나만 써.
4. if_match가 true인 변수에만 b_options를 만들어. 규칙 안에서 쓸 수 있는 B안(b가 있는 안)은 반드시 정확히 3개.
   (화면에는 최소 2개, 최대 3개를 보여 줘. 아래 조건에 걸리는 안은 코드가 빼므로, 3개 모두 조건을 지켜야 해.)
   규칙에 어긋나 B로 못 쓰는 안(rule_break)은 이 3개와 따로 덧붙여도 돼.
   - 단일 변수: B안마다 A(지금 그대로)에서 이 변수 하나만 바꿔. 통제 변수(같은 제품·색상, 흰 배경, 같은 조명과 보정,
     제품 85% 이상, 제목·가격·쿠폰·불릿·A+·광고)는 바꾸지 마. b에는 바뀌는 것만 쓰고, 그대로 두는 것은 쓰지 마.
   - 가설에 맞게: 모든 B안은 가설의 If가 말한 변화를 Because의 이유대로 실현해야 해. If와 다른 방향의 안은 만들지 마.
   - 서로 다르게: 각도 숫자나 표현만 바꾼 비슷한 안은 금지. 같은 If를 실현하는 서로 다른 방법이어야 해.
     예: "모서리를 들어 두께 보이기" / "반 접어 단면 보이기" (O), "45도에서 두께 보이기" / "30도에서 두께 보이기" (X)
   B안마다 label(버튼 이름, 10자 안쪽 명사구)과 b(바꾼 안, 한국어 한 문장 40자 안쪽)를 써.
   main_image 변수의 B안에는 ref_prompt(영어 레퍼런스 사진 프롬프트: white seamless background, no text, no props 포함)도 붙여.
   아마존 메인 이미지 규칙에 어긋나는 안은 b 대신 rule_break(어긴 규칙)와 fallback(대신 쓸 곳)을 써.
5. kpi에는 가설의 Then이 말하는 측정 지표 이름만 짧게 써.
6. 가설·문제·리포트에 없는 수치, 인증, 효과를 지어내지 마.
7. short에는 화면에 보일 짧은 If와 Because를 써. 가설 문장을 옮기거나 잘라 붙이지 말고, 읽자마자 이해되는 한 줄로 새로 써. 각각 25자 안쪽.
   - if: "{바꿀 곳} → {바꾼 모습}" 모양 하나. 대상, 괄호 설명, "B안", "지금 ~의 문제", "만약", "~을 적용한다면"은 빼.
     예: "메인 이미지 → 펼친 패드 사진"
   - because: 바꾸면 고객에게 무엇이 좋아지는지(가설의 이유)를 쉬운 말 한 문장으로, "~할 수 있음"·"~이 보임" 같은 명사형 끝맺음.
     근거 숫자(점유율, 비율, 가격 차이)는 옮기지 말고 그 숫자가 말하는 뜻만 써. "때문에"로 끝내지 마.
     예: "첫인상에서 가격이 합리적이라 판단할 수 있음"
   - 가설에 없는 사실·효과·숫자는 넣지 마.
8. JSON만 답해. 형식은 [예시]와 같고 short를 더해: {"kpi": "...", "note": "...", "short": {"if": "...", "because": "..."}, "variables": [...]}"""


# 이미지로 진행할 수 없는 변수(media_variable.py의 '진행 불가' 판정)를 매체 제작 대신 풀어 줄 솔루션
# 팝업에서 칸별로 정리해 보여 주도록 나눠 받습니다: 제목 · 한 줄 요약 · 실행 단계 · 기대 효과 · 확인할 것
# 팝업이 스크롤 없이 한 화면에 들어오도록 짧게 받습니다 (AI에게는 아래보다 짧게 쓰라고 하고, 조금 넘는 것까지는 받아 줌)
MEDIA_VARIABLE_SOLUTION_TEXT_MAX = {"title": 30, "summary": 70, "action": 25, "detail": 70, "effect": 70, "check": 70}
MEDIA_VARIABLE_SOLUTION_STEPS = (2, 3)   # 실행 단계 수 (최소, 최대)
MEDIA_VARIABLE_SOLUTION_SYSTEM = """너는 amazon.de(독일)에서 냉감패드를 파는 브랜드의 마케팅 컨설턴트야.
가설 하나와, 그 가설에서 고른 변수 하나를 받아. 이 변수는 메인 이미지(사진·영상 제작)로는 해결할 수 없어서,
매체 제작 대신 할 수 있는 솔루션을 칸별로 정리해 제안해야 해.

반드시 지킬 것
한 화면에 스크롤 없이 보여 줄 거라, 모든 칸을 짧게 써. 글자 수를 꼭 지켜.
1. title: 솔루션을 한 줄로 (20자 안쪽, 명사형).
2. summary: 무엇을 바꾸는지 한 문장 (50자 안쪽).
3. steps: 셀러가 Amazon Seller Central에서 직접 할 실행 단계 2~3개, 하는 순서대로.
   단계마다 action(할 일, 15자 안쪽 명사형)과 detail(어디서 무엇을 어떻게, 50자 안쪽).
   예: 제목·불릿·A+ 수정, 가격·쿠폰 조정, 광고 설정.
4. effect: 이렇게 하면 가설의 Then(목표 지표)에 왜 도움이 되는지 (50자 안쪽).
5. check: 실행 뒤 확인할 지표나 주의할 점 (50자 안쪽).
6. 모든 문장은 한국어, 마크다운·번호 없이. "~함", "~하기"처럼 짧게 끝내.
7. 가설·문제·리포트에 없는 수치, 인증, 효과를 지어내지 마.
8. JSON만 답해: {"title": "...", "summary": "...", "steps": [{"action": "...", "detail": "..."}], "effect": "...", "check": "..."}"""

# ─────────────────────────────────────────────
# 키 · AI 부르기
# ─────────────────────────────────────────────
def media_variable_ai_secret(name: str) -> str:
    """secrets.toml 값 (없거나 파일이 없으면 빈 문자열)."""
    try:
        return str(st.secrets.get(name) or "").strip()
    except Exception:
        return ""


def media_variable_ai_call(provider: str, message: str, system: str = MEDIA_VARIABLE_AI_SYSTEM) -> str:
    """AI 한 번 부르기 → 답 문자열 (system: 지시문, 기본은 후보 변수 묶음). 실패하면 키가 들어가지 않은 짧은 문구로 RuntimeError."""
    key = media_variable_ai_secret(MEDIA_VARIABLE_AI_PROVIDERS[provider])
    try:
        if provider == "Gemini":
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{MEDIA_VARIABLE_AI_GEMINI_MODEL}:generateContent",
                headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                json={"systemInstruction": {"parts": [{"text": system}]},
                      "contents": [{"role": "user", "parts": [{"text": message}]}],
                      "generationConfig": {"responseMimeType": "application/json"}},
                timeout=MEDIA_VARIABLE_AI_TIMEOUT)
        else:
            resp = requests.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": MEDIA_VARIABLE_AI_OPENAI_MODEL,
                      "input": [{"role": "system", "content": system},
                                {"role": "user", "content": message}]},
                timeout=MEDIA_VARIABLE_AI_TIMEOUT)
    except requests.Timeout:
        raise RuntimeError(f"{provider} 응답 시간 초과 ({MEDIA_VARIABLE_AI_TIMEOUT}초)") from None
    except requests.RequestException as err:
        raise RuntimeError(f"{provider} 연결 오류 ({type(err).__name__})") from None   # 오류 문구에 키가 섞이지 않게
    if resp.status_code != 200:
        raise RuntimeError(f"{provider} 응답 오류 (HTTP {resp.status_code})")
    try:
        body = resp.json()
    except ValueError:
        raise RuntimeError(f"{provider} 응답을 읽지 못했어요") from None
    if provider == "Gemini":
        parts = ((body.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
        return "".join(p.get("text", "") for p in parts)
    return body.get("output_text") or "".join(
        c.get("text", "") for item in body.get("output") or [] if item.get("type") == "message"
        for c in item.get("content") or [] if c.get("type") == "output_text")


def media_variable_ai_message(hypo: dict, listing: dict) -> str:
    """AI에게 보내는 글. 가설 · 문제 · 지금 메인 이미지 · 아마존 규칙 · 예시 묶음을 칸마다 제목을 붙여 나눕니다."""
    # 아마존 메인 이미지 규칙: 2026-10-25 media_ab.py가 media_stage2로 합쳐지면서 규칙도 media_stage2_ai.py로 옮김 (PM)
    # (media_stage2가 media_variable을 불러오므로 여기서 불러옴, 순환 방지)
    from modules.media.media_stage2.media_stage2_ai import MEDIA_S2_AMAZON_RULES as MEDIA_AB_RULES

    def block(title, lines):
        lines = [str(x) for x in lines if x]
        return f"[{title}]\n" + ("\n".join(lines) if lines else "(없음)")

    problem = hypo.get("problem") or {}
    try:
        example = json.loads(MEDIA_VARIABLE_AI_EXAMPLE_FILE.read_text(encoding="utf-8"))["sets"][0]
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        example = {}
    return "\n\n".join([
        block("가설", [hypo["text"]]),
        block("If / Because / Then", [f"If: {hypo.get('if')}", f"Because: {hypo.get('because')}",
                                       f"Then: {hypo.get('then')}"] if hypo.get("if") else []),
        block("문제 (1번 리포트)", [f"{k}: {problem[k]}" for k in ("title", "detail", "target", "metric") if problem.get(k)]),
        block("지금 메인 이미지", [listing.get("main_image"), listing.get("main_image_issue")]),
        block("아마존 메인 이미지 규칙", [f"- {r}" for r in MEDIA_AB_RULES]),
        block("예시", [json.dumps(example, ensure_ascii=False, indent=1)] if example else []),
    ])


# ─────────────────────────────────────────────
# 받은 답 확인 (규칙 묶음도 같은 확인을 거침)
# ─────────────────────────────────────────────
def media_variable_rule_break(text: str) -> tuple[str, str] | None:
    """메인 이미지 B안 문장이 아마존 규칙에 걸리면 (어긴 규칙, 대신 쓸 곳), 아니면 None."""
    for words, rule, fallback in MEDIA_VARIABLE_MAIN_RULES:
        if any(w in text for w in words):
            return rule, fallback
    return None


def media_variable_single_break(text: str, kind: str) -> str | None:
    """B안 문장이 고른 변수(kind) 말고 다른 것까지 바꾸면 그 이유 (단일 변수가 아님), 아니면 None.
    메인 이미지는 통제 변수(조명·배경·제품 색상) 말을, 모든 종류는 다른 변수 종류의 말(제목·가격·광고 등)을 찾습니다.
    다른 종류의 말이 내 종류 말 안에 들어 있으면(예: A+의 '상세 이미지' 안의 '이미지') 건너뜁니다."""
    if kind == "main_image":
        for words, reason in MEDIA_VARIABLE_CONTROL_RULES:
            if any(w in text for w in words):
                return reason
    own = MEDIA_VARIABLE_KINDS.get(kind, MEDIA_VARIABLE_KINDS["other"])[1]
    for other, (name, words) in MEDIA_VARIABLE_KINDS.items():
        if other in (kind, "other"):
            continue
        if any(w in text and not any(w in o and o in text for o in own) for w in words):
            return f"다른 변수({name})까지 바뀜"
    return None


def media_variable_similar(a: str, b: str) -> bool:
    """B안 두 문장이 표현만 다른 비슷한 안인지 (difflib 비율이 MEDIA_VARIABLE_B_SIMILAR 이상)."""
    return SequenceMatcher(None, a, b).ratio() >= MEDIA_VARIABLE_B_SIMILAR


def media_variable_clean_short(raw, source: str) -> dict:
    """AI가 줄인 If·Because {"if", "because"}. 칸마다 MEDIA_VARIABLE_SHORT_MAX자를 넘거나
    원문(source)에 없는 숫자가 들어 있으면 그 칸은 버립니다 (화면이 규칙으로 줄인 모양을 대신 씀)."""
    if not isinstance(raw, dict):
        return {}
    out = {}
    for k in ("if", "because"):
        text = str(raw.get(k) or "").strip().rstrip(".")
        numbers = re.findall(r"\d+(?:[.,]\d+)?", text)
        if text and len(text) <= MEDIA_VARIABLE_SHORT_MAX and all(n in source for n in numbers):
            out[k] = text
    return out


def media_variable_cut(text: str, limit: int) -> str:
    """limit자를 넘으면 잘라서 끝에 … (넘지 않으면 그대로)."""
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def media_variable_short_name(name: str, kind: str, taken: list[str]) -> str:
    """요약 칩·변수 블럭에 보일 변수 이름을 MEDIA_VARIABLE_TEXT_MAX["name"]자 안으로 줄입니다.
    괄호 설명을 빼고, 그래도 길면 종류 이름(예: '메인 이미지'). 종류 이름이 이미 다른 변수 이름이면 잘라서 …
    (변수 이름으로 고른 변수를 찾으므로 이름이 겹치지 않게 함)"""
    limit = MEDIA_VARIABLE_TEXT_MAX["name"]
    short = re.sub(r"\s*\([^)]*\)", "", name).strip() or name
    if len(short) <= limit:
        return short
    kind_name = MEDIA_VARIABLE_KINDS.get(kind, MEDIA_VARIABLE_KINDS["other"])[0]
    return kind_name if kind_name not in taken and kind != "other" else media_variable_cut(short, limit)


def media_variable_clean_set(raw, source: str = "", if_text: str = "") -> dict | None:
    """후보 묶음(dict 또는 AI 답 문자열)을 정리합니다. 변수가 하나도 안 남으면 None.
    kind는 정해진 종류로만, B안은 이름 + (b 또는 rule_break)가 있는 것만, 메인 이미지 B안은 규칙에 걸리는 말이 있으면 rule_break로 바꿈.
    가설에 맞는지: 가설 If(if_text)의 종류를 알 수 있으면, 종류가 다른 변수는 AI가 맞다고 해도 if_match를 false로 바꿈.
    if_match가 아닌 변수의 B안은 버림 (가설과 다른 변수로 실험하지 않게).
    단일 변수: 고른 변수 말고 다른 것까지 바꾸는 B안은 rule_break로 돌림 (media_variable_single_break()).
    서로 다르게: 앞의 B안과 비슷한 B안은 빼고, B로 쓸 수 있는 안은 MEDIA_VARIABLE_B_MAX개까지.
    간결하게: 변수 이름·B안 이름·B안 문장이 MEDIA_VARIABLE_TEXT_MAX를 넘으면 줄이거나 B로 쓰지 않음.
    short(짧은 If·Because)는 원문 source와 맞춰 본 것만 남김 (source가 없으면 빈 dict)."""
    if_kind = media_variable_kind(if_text) if if_text else "other"
    if isinstance(raw, str):
        start, end = raw.find("{"), raw.rfind("}")
        try:
            raw = json.loads(raw[start:end + 1]) if 0 <= start < end else None
        except ValueError:
            raw = None
    if not isinstance(raw, dict) or not isinstance(raw.get("variables"), list):
        return None
    variables = []
    for v in raw["variables"]:
        if not isinstance(v, dict) or not str(v.get("name") or "").strip():
            continue
        kind = v.get("kind") if v.get("kind") in MEDIA_VARIABLE_KINDS else "other"
        if_match, reason = v.get("if_match") is True, str(v.get("reason") or "")
        if if_match and if_kind != "other" and kind != if_kind:   # AI가 맞다고 해도 가설 If와 종류가 다르면 아님
            if_match, reason = False, f"가설의 If는 {MEDIA_VARIABLE_KINDS[if_kind][0]} 변수"
        options, kept = [], []   # kept: B로 쓸 수 있는 안의 문장 (비슷한 안 거르기용)
        for o in (v.get("b_options") or []) if if_match else []:
            if not isinstance(o, dict) or not str(o.get("label") or "").strip():
                continue
            o = {k: str(o[k]).strip() for k in ("label", "b", "ref_prompt", "rule_break", "fallback") if o.get(k)}
            o["label"] = media_variable_cut(o["label"], MEDIA_VARIABLE_TEXT_MAX["label"])
            if len(o.get("b", "")) > MEDIA_VARIABLE_TEXT_MAX["b"] and not o.get("rule_break"):   # 길면 A/B 표가 늘어나 B로 쓰지 않음
                o = {"label": o["label"], "rule_break": "설명이 길어 한눈에 안 읽힘", "fallback": "다시 불러오기"}
            broken = media_variable_rule_break(o.get("b", "")) if kind == "main_image" and not o.get("rule_break") else None
            if broken:
                o = {"label": o["label"], "rule_break": broken[0], "fallback": broken[1]}
            single = media_variable_single_break(o["b"], kind) if o.get("b") and not o.get("rule_break") else None
            if single:
                o = {"label": o["label"], "rule_break": single, "fallback": "다음 테스트"}
            if o.get("b") and not o.get("rule_break"):
                if len(kept) >= MEDIA_VARIABLE_B_MAX or any(media_variable_similar(o["b"], b) for b in kept):
                    continue   # 넘치거나 앞의 안과 비슷한 안은 뺌
                kept.append(o["b"])
            if o.get("b") or o.get("rule_break"):
                options.append(o)
        name = media_variable_short_name(str(v["name"]).strip(), kind, [x["name"] for x in variables])
        variables.append({"name": name, "kind": kind, "if_match": if_match,
                          "fallback": str(v.get("fallback") or ("다음 테스트" if not if_match else "")), "reason": reason,
                          "b_options": options})
    if not variables:
        return None
    return {"kpi": str(raw.get("kpi") or "").strip(), "note": str(raw.get("note") or "").strip(),
            "short": media_variable_clean_short(raw.get("short"), source) if source else {}, "variables": variables}


def media_variable_kind(text: str) -> str:
    """가설 If 문장이 바꾸는 변수 종류 (MEDIA_VARIABLE_KINDS에서 먼저 맞는 것, 없으면 other)."""
    for kind, (_, words) in MEDIA_VARIABLE_KINDS.items():
        if any(w in text for w in words):
            return kind
    return "other"


def media_variable_rule_set(hypo: dict) -> dict:
    """AI 없이 만드는 후보 묶음: 가설의 If를 그대로 독립 변수 하나 + B안 하나로 쓰고,
    걸러내는 예시로 다른 종류 변수 두 개를 '가설의 If가 아님'으로 붙입니다."""
    from modules.media.media_variable import media_variable_short_if   # 순환 방지로 여기서 불러옴
    # If가 따로 없으면(예전 저장값) 문장의 첫 쉼표 앞까지를 If로 봅니다. B안은 콜아웃과 같은 짧은 모양 (대상·문장 틀 뺌)
    _, if_text = media_variable_short_if(str(hypo.get("if") or hypo["text"].split(", ")[0]),
                                         str((hypo.get("problem") or {}).get("target") or ""))
    kind = media_variable_kind(if_text)
    others = [k for k in ("title", "price", "main_image") if k != kind][:2]
    return media_variable_clean_set({
        "kpi": (hypo.get("problem") or {}).get("metric") or "",
        "note": "AI 없이 규칙으로 만든 후보예요. 가설의 If를 그대로 B안으로 써요.",
        "variables": [{"name": MEDIA_VARIABLE_KINDS[kind][0], "kind": kind, "if_match": True,
                       "b_options": [{"label": "가설의 If 그대로", "b": if_text}]}]
                     + [{"name": MEDIA_VARIABLE_KINDS[k][0], "kind": k, "if_match": False,
                         "fallback": "고정 요소" if k == "price" else "다음 테스트", "reason": "가설의 If가 아님"}
                        for k in others],
    })


def media_variable_b_shortage(cset: dict) -> tuple[int, list[str]] | None:
    """가설에 맞는 메인 이미지 변수(2·3단계로 진행할 변수)의 B안이 MEDIA_VARIABLE_B_MIN개보다 적으면
    (B로 쓸 수 있는 안 수, 빠진 안의 이유 목록), 충분하거나 그런 변수가 없으면 None."""
    for v in cset["variables"]:
        if v["if_match"] and v["kind"] == "main_image":
            ok = [o for o in v["b_options"] if o.get("b")]
            if len(ok) < MEDIA_VARIABLE_B_MIN:
                return len(ok), [f"{o['label']}: {o['rule_break']}" for o in v["b_options"] if o.get("rule_break")]
    return None


def media_variable_generate(hypo: dict, listing: dict) -> tuple[dict, str, str]:
    """가설 하나 → (후보 묶음, 출처 이름, AI를 못 쓴 이유). 키가 있는 AI를 차례로 시도하고, 모두 안 되면 규칙으로 만듭니다.
    진행할 메인 이미지 변수의 B안이 코드 확인 뒤 MEDIA_VARIABLE_B_MIN개보다 적으면, 빠진 이유를 붙여 MEDIA_VARIABLE_B_RETRY번까지
    다시 요청합니다. 한 AI가 끝내 모자라면 다음 AI도 시도하고, 모두 모자라면 B안이 가장 많은 묶음을 씁니다
    (그래도 모자라면 있는 만큼, 지어내지 않음)."""
    errors = []
    best, best_provider = None, ""   # 모든 AI를 통틀어 B안이 가장 많은 묶음
    source = " ".join(str(hypo.get(k) or "") for k in ("text", "if", "because", "then"))
    if_text = str(hypo.get("if") or hypo["text"].split(", ")[0])   # 규칙 묶음과 같은 방법으로 If를 고름
    for provider, key_name in MEDIA_VARIABLE_AI_PROVIDERS.items():
        if not media_variable_ai_secret(key_name):
            continue
        message = media_variable_ai_message(hypo, listing)
        for _ in range(1 + MEDIA_VARIABLE_B_RETRY):
            try:
                cset = media_variable_clean_set(media_variable_ai_call(provider, message), source, if_text)
            except RuntimeError as err:
                errors.append(str(err))
                break
            if not cset:
                errors.append(f"{provider} 답 형식이 맞지 않음")
                continue
            short = media_variable_b_shortage(cset)
            if not short:
                return cset, provider, ""
            if not best or short[0] > media_variable_b_shortage(best)[0]:
                best, best_provider = cset, provider
            # 다시 요청: 앞 답에서 B로 쓸 수 있는 안이 몇 개였고 왜 빠졌는지 알려 줌
            message = media_variable_ai_message(hypo, listing) + "\n\n" + "\n".join([
                "[다시 요청]",
                f"앞 답에서 규칙 안에서 B로 쓸 수 있는 안이 {short[0]}개뿐이었어. 지시 4번대로 서로 다른 B안을 정확히 3개 만들어.",
                *(f"- 빠진 안 {r}" for r in short[1]),
                "- 비슷한 안(표현·숫자만 다른 안)과 너무 긴 b도 빠져. b는 40자 안쪽으로."])
    if best:
        return best, best_provider, f"B안이 {media_variable_b_shortage(best)[0]}개만 나옴 (최소 {MEDIA_VARIABLE_B_MIN}개)"
    return media_variable_rule_set(hypo), MEDIA_VARIABLE_AI_RULE_SOURCE, " · ".join(errors) or "AI 키가 없음"


# ─────────────────────────────────────────────
# 진행 불가 변수의 줄글 솔루션
# ─────────────────────────────────────────────
def media_variable_solution_message(hypo: dict, variable: dict, kpi: str) -> str:
    """솔루션을 만들 때 AI에게 보내는 글. 가설 · 문제 · 고른 변수 · 목표 지표를 칸마다 나눕니다."""
    problem = hypo.get("problem") or {}
    kind = MEDIA_VARIABLE_KINDS.get(variable.get("kind"), MEDIA_VARIABLE_KINDS["other"])[0]
    blocks = [("가설", [hypo.get("text")]),
              ("If / Because / Then", [f"If: {hypo.get('if')}", f"Because: {hypo.get('because')}",
                                       f"Then: {hypo.get('then')}"] if hypo.get("if") else []),
              ("문제 (1번 리포트)", [f"{k}: {problem[k]}" for k in ("title", "detail", "target", "metric") if problem.get(k)]),
              ("고른 변수", [f"이름: {variable.get('name')}", f"종류: {kind}",
                         f"이미지로 진행할 수 없는 이유: {variable.get('why')}", variable.get("reason")]),
              ("목표 지표", [kpi])]
    return "\n\n".join(f"[{title}]\n" + ("\n".join(str(x) for x in lines if x) or "(없음)") for title, lines in blocks)


def media_variable_clean_solution(raw: str) -> dict | None:
    """AI 답 문자열 → {"title", "summary", "steps": [{"action", "detail"}], "effect", "check"}.
    제목·요약이 비었거나, 칸이 MEDIA_VARIABLE_SOLUTION_TEXT_MAX의 그 칸 글자 수를 넘거나, 쓸 수 있는 단계 수가 MEDIA_VARIABLE_SOLUTION_STEPS 밖이면 None.
    단계가 최대보다 많으면 앞에서부터 최대 개수만 씁니다. effect·check는 비어도 됩니다 (팝업에서 그 칸만 빠짐)."""
    start, end = raw.find("{"), raw.rfind("}")
    try:
        data = json.loads(raw[start:end + 1]) if 0 <= start < end else None
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    text = {k: str(data.get(k) or "").strip() for k in ("title", "summary", "effect", "check")}
    steps = [{"action": str(s.get("action") or "").strip(), "detail": str(s.get("detail") or "").strip()}
             for s in data.get("steps") or [] if isinstance(s, dict)]
    steps = [s for s in steps if s["action"]][:MEDIA_VARIABLE_SOLUTION_STEPS[1]]
    limit = MEDIA_VARIABLE_SOLUTION_TEXT_MAX
    too_long = (any(len(t) > limit[k] for k, t in text.items())
                or any(len(s[k]) > limit[k] for s in steps for k in ("action", "detail")))
    if not text["title"] or not text["summary"] or too_long or len(steps) < MEDIA_VARIABLE_SOLUTION_STEPS[0]:
        return None
    return {**text, "steps": steps}


def media_variable_solution_generate(hypo: dict, variable: dict, kpi: str) -> tuple[dict | None, str, str]:
    """진행 불가 변수 하나 → (솔루션 {"title", "summary", "steps", "effect", "check"}, 출처 이름, AI를 못 쓴 이유).
    키가 있는 AI를 차례로 시도하고, 모두 안 되면 (None, "", 이유). 규칙으로 대신 만들지 않습니다 (지어낸 솔루션이 되지 않게)."""
    errors = []
    for provider, key_name in MEDIA_VARIABLE_AI_PROVIDERS.items():
        if not media_variable_ai_secret(key_name):
            continue
        try:
            raw = media_variable_ai_call(provider, media_variable_solution_message(hypo, variable, kpi),
                                         MEDIA_VARIABLE_SOLUTION_SYSTEM)
        except RuntimeError as err:
            errors.append(str(err))
            continue
        solution = media_variable_clean_solution(raw)
        if solution:
            return solution, provider, ""
        errors.append(f"{provider} 답 형식이 맞지 않음")
    return None, "", " · ".join(errors) or "AI 키가 없음"
