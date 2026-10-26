# 3. 매체 제작 > 가설에서 변수 도출: 가설 하나로 후보 변수 묶음 만들기 (화면 코드 없음)
# 화면(표·버튼)은 media_variable.py에서 그립니다. '가설 불러오기'를 누를 때만 부릅니다.
# - 어떤 가설이 와도 후보 묶음을 돌려줍니다: AI(Gemini/OpenAI)로 만들고, 키가 없거나 실패하면 규칙으로 만듭니다.
# - 묶음 모양은 예시 파일 data/media_variable_candidates.json의 한 묶음과 같습니다 {"kpi", "note", "variables"}.
#   AI 묶음에는 가설 콜아웃에 보일 짧은 If·Because("short")가 더 붙습니다 (규칙 묶음은 빈 dict).
# - AI 답은 믿지 않고 코드로 다시 확인합니다 (변수 종류, B안 모양, 메인 이미지 규칙에 걸리는 말).
# - 키는 secrets.toml의 GEMINI_API_KEY / OPENAI_API_KEY를 함수 안에서만 읽습니다 (2단계와 같은 키). 새 라이브러리 없이 requests로 부릅니다.
import json
import re
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
    "other": ("가설의 If", []),
}
# 메인 이미지 B안에서 아마존 규칙에 걸리는 말: (찾을 말, 어긴 규칙, 대신 쓸 곳). AI 답과 규칙 묶음 모두 이걸로 다시 확인합니다.
MEDIA_VARIABLE_MAIN_RULES = [
    (["텍스트", "문구", "글자", "로고", "워터마크", "화살표"], "메인 이미지에는 텍스트·로고 금지", "서브 이미지"),
    (["손으로", "손이", "사람", "모델", "소품"], "메인 이미지에는 제품 말고 손·소품 금지", "서브 이미지"),
    (["AI로", "연출", "침실", "라이프스타일"], "메인 이미지는 흰 배경 실제 사진만", "스폰서드 브랜드 광고"),
]

MEDIA_VARIABLE_AI_SYSTEM = """너는 amazon.de(독일)에서 냉감패드를 파는 브랜드의 A/B 테스트 설계자야.
가설 하나를 받아, Amazon Manage Your Experiments로 실험할 "후보 변수" 목록을 만들어.

반드시 지킬 것
1. 변수 하나 = 바꿀 것 하나. 후보는 3~5개.
2. 가설의 If가 바꾸라고 한 변수를 맨 앞에 두고 if_match를 true로 해.
   나머지(가설과 다른 대안, 고정해야 할 요소)는 if_match를 false로, reason에 이유, fallback에 대신 쓸 곳("다음 테스트", "고정 요소" 등)을 써.
3. kind는 main_image, title, bullet, a_plus, price, other 중 하나만 써.
4. if_match가 true인 변수에만 b_options를 2~4개 만들어. B안마다 label(버튼 이름, 15자 안쪽)과 b(바꾼 안, 한국어 한 문장)를 써.
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


# 이미지로 진행할 수 없는 변수(media_variable.py의 '진행 불가' 판정)를 매체 제작 대신 풀어 줄 줄글 솔루션
MEDIA_VARIABLE_SOLUTION_MAX = 600   # 솔루션 본문 최대 글자 수 (넘으면 AI 답을 버림)
MEDIA_VARIABLE_SOLUTION_SYSTEM = """너는 amazon.de(독일)에서 냉감패드를 파는 브랜드의 마케팅 컨설턴트야.
가설 하나와, 그 가설에서 고른 변수 하나를 받아. 이 변수는 메인 이미지(사진·영상 제작)로는 해결할 수 없어서,
매체 제작 대신 할 수 있는 솔루션을 줄글로 제안해야 해.

반드시 지킬 것
1. title: 솔루션을 한 줄로 (25자 안쪽, 명사형).
2. body: 무엇을 어떻게 바꾸고, 그게 가설의 Then(목표 지표)에 왜 도움이 되는지 한국어 줄글 3~5문장. 목록·번호·마크다운 없이 문장으로만.
3. 셀러가 Amazon Seller Central에서 직접 할 수 있는 일로 써 (예: 제목·불릿·A+ 수정, 가격·쿠폰 조정, 광고 설정).
4. 가설·문제·리포트에 없는 수치, 인증, 효과를 지어내지 마.
5. JSON만 답해: {"title": "...", "body": "..."}"""

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


def media_variable_clean_set(raw, source: str = "") -> dict | None:
    """후보 묶음(dict 또는 AI 답 문자열)을 정리합니다. 변수가 하나도 안 남으면 None.
    kind는 정해진 종류로만, B안은 이름 + (b 또는 rule_break)가 있는 것만, 메인 이미지 B안은 규칙에 걸리는 말이 있으면 rule_break로 바꿈.
    short(짧은 If·Because)는 원문 source와 맞춰 본 것만 남김 (source가 없으면 빈 dict)."""
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
        options = []
        for o in v.get("b_options") or []:
            if not isinstance(o, dict) or not str(o.get("label") or "").strip():
                continue
            o = {k: str(o[k]).strip() for k in ("label", "b", "ref_prompt", "rule_break", "fallback") if o.get(k)}
            broken = media_variable_rule_break(o.get("b", "")) if kind == "main_image" and not o.get("rule_break") else None
            if broken:
                o = {"label": o["label"], "rule_break": broken[0], "fallback": broken[1]}
            if o.get("b") or o.get("rule_break"):
                options.append(o)
        variables.append({"name": str(v["name"]).strip(), "kind": kind, "if_match": v.get("if_match") is True,
                          "fallback": str(v.get("fallback") or ""), "reason": str(v.get("reason") or ""),
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


def media_variable_generate(hypo: dict, listing: dict) -> tuple[dict, str, str]:
    """가설 하나 → (후보 묶음, 출처 이름, AI를 못 쓴 이유). 키가 있는 AI를 차례로 시도하고, 모두 안 되면 규칙으로 만듭니다."""
    errors = []
    for provider, key_name in MEDIA_VARIABLE_AI_PROVIDERS.items():
        if not media_variable_ai_secret(key_name):
            continue
        try:
            source = " ".join(str(hypo.get(k) or "") for k in ("text", "if", "because", "then"))
            cset = media_variable_clean_set(media_variable_ai_call(provider, media_variable_ai_message(hypo, listing)), source)
        except RuntimeError as err:
            errors.append(str(err))
            continue
        if cset:
            return cset, provider, ""
        errors.append(f"{provider} 답 형식이 맞지 않음")
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
    """AI 답 문자열 → {"title", "body"}. 칸이 비었거나 본문이 MEDIA_VARIABLE_SOLUTION_MAX자를 넘으면 None."""
    start, end = raw.find("{"), raw.rfind("}")
    try:
        data = json.loads(raw[start:end + 1]) if 0 <= start < end else None
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    title, body = str(data.get("title") or "").strip(), str(data.get("body") or "").strip()
    if not title or not body or len(body) > MEDIA_VARIABLE_SOLUTION_MAX:
        return None
    return {"title": title, "body": body}


def media_variable_solution_generate(hypo: dict, variable: dict, kpi: str) -> tuple[dict | None, str, str]:
    """진행 불가 변수 하나 → (줄글 솔루션 {"title", "body"}, 출처 이름, AI를 못 쓴 이유).
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
