# 3. 매체 제작 > 2단계 AI 다듬기: 재료 모으기 → 지시문 만들기 → AI 부르기 → 받은 답 확인 (화면 코드 없음)
# 화면(버튼·결과 표)은 media_stage2.py에서 그립니다.
# - 재료는 전부 리포트(store_get("report"))와 아마존 메인 이미지 규칙(MEDIA_S2_AMAZON_RULES)에서 가져오고 새로 지어내지 않습니다.
# - AI 답은 믿지 않고 코드로 다시 확인합니다 ({slot} 1개, 고정 요소, A/B 확인, 금지 단어, 근거 ID).
# - AI는 OpenAI만 씁니다 (PM 결정 2026-10-25). 키는 secrets.toml의 OPENAI_API_KEY를 함수 안에서만 읽고,
#   새 라이브러리 없이 requests로 부릅니다.
import json
import re

import requests
import streamlit as st

from common.common_store import store_get
from modules.media.media_handoff import MEDIA_HANDOFF_SLOT, media_handoff_check, media_handoff_fill

# 아마존 메인 이미지 규칙 (옛 media_ab.py의 MEDIA_AB_RULES를 그대로 옮김, 2026-10-25 A/B 소재 준비 탭을 2단계로 합치면서)
# AI 다듬기 재료로 AMZ-1, AMZ-2 … 순서대로 ID를 붙여 보냅니다.
MEDIA_S2_AMAZON_RULES = [
    "흰 배경(RGB 255, 255, 255)에 텍스트·로고·워터마크 없는 실제 제품 사진",
    "AI로 만든 연출 장면은 메인 이미지에 쓰지 않음 → 서브 이미지나 스폰서드 브랜드 광고에서만 사용",
    "A/B 변수는 사진 안에서 바꿀 수 있는 것만: 각도, 구도, 접힌/펼친 상태, 두께감",
    "AI는 촬영 각도 레퍼런스와 보정에만 쓰고, 실제 촬영은 외주로 진행",
]

# 모델 이름 (2026-10-25 공식 문서 확인: OpenAI 비용·성능 균형 모델, 같은 날 실제 호출 확인)
MEDIA_S2_OPENAI_MODEL = "gpt-6.1-sol"
MEDIA_S2_AI_KEY = "OPENAI_API_KEY"            # secrets.toml 키 이름
MEDIA_S2_AI_TIMEOUT = 60                      # 응답 기다리는 시간 (초)
MEDIA_S2_PHOTO_RULE_IDS = ("LNG-002", "LNG-004", "LNG-006")   # 사진에 해당하는 독일 광고 규칙 (나머지는 광고 문구용)

MEDIA_S2_AI_SYSTEM = """너는 amazon.de(독일)에서 파는 냉감패드의 "사진 프롬프트 편집자"야.
아마존 메인 이미지 A/B 테스트용 레퍼런스 사진을 만들 기본 프롬프트 하나를 다듬어.
이 사진은 촬영팀에게 주는 견본이고, 광고에 바로 쓰는 사진이 아니야.

반드시 지킬 것
1. 기본 프롬프트에는 {slot}이 딱 한 번 있어. {slot}은 글자 그대로, 한 번만 남겨. 빈칸 안에 들어갈 내용은 건드리지 마.
2. 고정 요소는 글자 하나 바꾸지 말고 그대로 남겨.
3. {slot} 밖의 공통 부분만 고쳐.
4. 피할 것 규칙과 아마존 메인 이미지 규칙에 걸리는 표현은 빼.
5. 넣을 것은 "사실" 목록에 있는 것만 넣어. 수치·인증·효과를 지어내지 마.
   더한 내용도 흰 배경, 글자 없음, 소품 없음 조건을 지켜야 해.
6. 바꾼 곳마다 근거 ID를 붙여. 근거가 없으면 바꾸지 마.
7. A 문구·B 문구가 규칙에 걸려도 고치지 말고 slot_warnings에 알려만 줘.
8. 다듬은 프롬프트는 영어로, 이유는 한국어로 써.
9. JSON만 답해. 형식:
   {"base": "...", "changes": [{"where": "...", "kind": "뺌 또는 더함", "reason": "...", "basis": "ID"}],
    "avoid": ["..."], "include": ["..."], "slot_warnings": ["..."]}"""

MEDIA_S2_AI_RETRY_NOTE = "\n\n[다시 요청] 앞 답이 JSON 형식이 아니었어. 설명 없이 위 형식의 JSON만 다시 답해."


# ─────────────────────────────────────────────
# 키
# ─────────────────────────────────────────────
def media_s2_ai_secret(name: str) -> str:
    """secrets.toml 값 (없거나 파일이 없으면 빈 문자열)."""
    try:
        return str(st.secrets.get(name) or "").strip()
    except Exception:
        return ""


def media_s2_ai_ready() -> bool:
    """OpenAI 키가 들어 있으면 True."""
    return bool(media_s2_ai_secret(MEDIA_S2_AI_KEY))


# ─────────────────────────────────────────────
# 재료 (이 함수 하나에서만 리포트를 읽음)
# ─────────────────────────────────────────────
def media_s2_ai_material(draft: dict) -> dict:
    """AI에게 보낼 재료. 리포트 값이 없으면(① 탭을 안 열었으면) 아마존 규칙만 들어 있고 has_report=False.
    각 항목은 {"id", "text"}이고, AI가 근거로 붙일 수 있는 ID는 ids에 모읍니다."""
    report = store_get("report") or {}
    claims = report.get("ad_claims") if isinstance(report.get("ad_claims"), dict) else {}
    forbidden = [{"id": f"BAN-{i}", "text": str(t)} for i, t in enumerate(claims.get("forbidden") or [], 1)]
    rules = [{"id": r["id"], "text": f'{r.get("topic", "")}: {r.get("rule", "")}'}
             for r in report.get("marketing_rules") or [] if isinstance(r, dict) and r.get("id") in MEDIA_S2_PHOTO_RULE_IDS]
    amazon = [{"id": f"AMZ-{i}", "text": t} for i, t in enumerate(MEDIA_S2_AMAZON_RULES, 1)]

    facts = []
    seori = report.get("seori_profile") if isinstance(report.get("seori_profile"), dict) else {}
    if seori.get("strength"):
        facts.append({"id": "SEORI-1", "text": f"서리 강점: {seori['strength']}"})
    for i, c in enumerate(report.get("competitor_profiles") or [], 1):
        if isinstance(c, dict) and c.get("weakness"):
            facts.append({"id": f"RIVAL-{i}", "text": f"{c.get('brand') or '경쟁사'} 약점: {c['weakness']}"})
    sqp = report.get("sqp") if isinstance(report.get("sqp"), dict) else {}
    listing = sqp.get("listing") if isinstance(sqp.get("listing"), dict) else {}
    if listing.get("main_image_issue"):
        facts.append({"id": "LISTING-1", "text": f"지금 메인 이미지 문제: {listing['main_image_issue']}"})

    return {
        "draft": {k: draft[k] for k in ("base", "variable", "slot_a", "slot_b", "fixed")},
        "forbidden": forbidden, "rules": rules, "amazon": amazon, "facts": facts,
        "has_report": bool(forbidden or rules or facts),
        "ids": [x["id"] for x in forbidden + rules + amazon + facts],
    }


def media_s2_ai_message(material: dict) -> str:
    """AI에게 보내는 글. 칸마다 제목을 붙여 나눕니다."""
    d = material["draft"]

    def block(title, lines):
        return f"[{title}]\n" + ("\n".join(lines) if lines else "(없음)")

    def ided(items):
        return [f"- {x['id']}: {x['text']}" for x in items]

    return "\n\n".join([
        block("기본 프롬프트", [d["base"]]),
        block("단일 변수", [d["variable"]]),
        block("A 문구", [d["slot_a"]]),
        block("B 문구", [d["slot_b"]]),
        block("고정 요소", [f"- {f}" for f in d["fixed"]]),
        block("피할 것 - 리포트 금지 표현", ided(material["forbidden"])),
        block("피할 것 - 독일 광고 규칙", ided(material["rules"])),
        block("아마존 메인 이미지 규칙", ided(material["amazon"])),
        block("넣을 것 - 사실", ided(material["facts"])),
    ])


# ─────────────────────────────────────────────
# AI 부르기
# ─────────────────────────────────────────────
def media_s2_ai_call(system: str, message: str) -> str:
    """OpenAI 한 번 부르기 → 답 문자열. 실패하면 키가 들어가지 않은 짧은 문구로 RuntimeError."""
    key = media_s2_ai_secret(MEDIA_S2_AI_KEY)
    if not key:
        raise RuntimeError(f"OpenAI 키({MEDIA_S2_AI_KEY})가 없어요")
    try:
        resp = requests.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": MEDIA_S2_OPENAI_MODEL,
                  "input": [{"role": "system", "content": system}, {"role": "user", "content": message}]},
            timeout=MEDIA_S2_AI_TIMEOUT)
    except requests.Timeout:
        raise RuntimeError(f"OpenAI 응답 시간 초과 ({MEDIA_S2_AI_TIMEOUT}초)") from None
    except requests.RequestException as err:
        raise RuntimeError(f"OpenAI 연결 오류 ({type(err).__name__})") from None   # 오류 문구에 키가 섞이지 않게

    if resp.status_code in (401, 403):
        raise RuntimeError(f"OpenAI 키 오류 (HTTP {resp.status_code}) · 키가 맞는지 확인해 주세요")
    if resp.status_code == 429:
        raise RuntimeError("OpenAI 사용량 초과 (HTTP 429) · 잠시 뒤 다시 눌러 주세요")
    if resp.status_code != 200:
        raise RuntimeError(f"OpenAI 응답 오류 (HTTP {resp.status_code})")
    try:
        body = resp.json()
    except ValueError:
        raise RuntimeError("OpenAI 응답을 읽지 못했어요") from None

    text = body.get("output_text") or "".join(
        c.get("text", "") for item in body.get("output") or [] if item.get("type") == "message"
        for c in item.get("content") or [] if c.get("type") == "output_text")
    if not text.strip():
        raise RuntimeError("OpenAI가 빈 답을 보냈어요")
    return text


# ─────────────────────────────────────────────
# 금지 단어 검사 (키가 없어도 항상 씀)
# ─────────────────────────────────────────────
def media_s2_forbidden_terms(forbidden: list) -> list[str]:
    """금지 표현 목록 → 영어 프롬프트에서 찾을 단어. 괄호 안 한국어 설명은 빼고, '/'·'·'·','로 나눈 뒤
    한국어가 대부분인 조각(설명 문장)과 'X °C'처럼 자리만 표시한 조각은 검사에서 뺍니다."""
    terms = []
    for item in forbidden:
        text = re.sub(r"\([^)]*\)", " ", str(item.get("text", item) if isinstance(item, dict) else item))
        for seg in re.split(r"[/·,]", text):
            hangul = len(re.findall(r"[가-힣]", seg))
            latin = len(re.findall(r"[A-Za-zÄÖÜäöüß]", seg))
            word = " ".join(re.sub(r"[가-힣]+", " ", seg).split()).strip(" -")
            if latin > hangul and re.search(r"[A-Za-zÄÖÜäöüß]{3,}", word) and word not in terms:
                terms.append(word)
    return terms


def media_s2_forbidden_hits(text: str, forbidden: list) -> list[str]:
    """text 안에 남은 금지 단어 (대소문자 무시)."""
    low = text.lower()
    return [t for t in media_s2_forbidden_terms(forbidden) if t.lower() in low]


# ─────────────────────────────────────────────
# 받은 답 확인
# ─────────────────────────────────────────────
def media_s2_ai_parse(raw: str):
    """AI 답 → dict. ```json 울타리나 앞뒤 설명이 있어도 가장 바깥 { } 만 읽고, 못 읽으면 None."""
    text = str(raw or "").strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _media_s2_str_list(value) -> list[str]:
    return [str(v).strip() for v in value if str(v).strip()] if isinstance(value, list) else []


def media_s2_ai_validate(raw: str, draft: dict, material: dict) -> dict:
    """AI 답을 코드로 다시 확인합니다.
    돌려주는 값: ok(통과), broken(JSON이 깨짐 → 한 번 다시 요청), errors(버린 이유), warnings, result(통과했을 때)."""
    data = media_s2_ai_parse(raw)
    if data is None:
        return {"ok": False, "broken": True, "errors": ["AI 답이 JSON 형식이 아니에요"], "warnings": [], "result": None}

    errors = []
    base = data.get("base") if isinstance(data.get("base"), str) else ""
    n_slot = base.count(MEDIA_HANDOFF_SLOT)
    if not base:
        errors.append("다듬은 기본 프롬프트(base)가 비어 있어요")
    elif n_slot != 1:
        errors.append(f"빈칸 {MEDIA_HANDOFF_SLOT}이 {n_slot}개예요 (정확히 1개여야 해요)")
    missing = [f for f in draft["fixed"] if f not in base]
    if base and missing:
        errors.append("고정 요소가 빠지거나 바뀌었어요: " + ", ".join(missing))
    prompt_a = media_handoff_fill(base, draft["slot_a"])
    prompt_b = media_handoff_fill(base, draft["slot_b"])
    if not errors and not media_handoff_check(draft, prompt_a, prompt_b)["ok"]:
        errors.append("A/B 확인(빈칸만 다른가, 고정 요소가 남았나)을 통과하지 못했어요")
    if errors:
        return {"ok": False, "broken": False, "errors": errors, "warnings": [], "result": None}

    ids = set(material["ids"])
    changes = []
    for c in data.get("changes") or []:
        if not isinstance(c, dict):
            continue
        basis = str(c.get("basis", "")).strip()
        cited = [b.strip() for b in re.split(r"[,\s/·]+", basis) if b.strip()]
        changes.append({"where": str(c.get("where", "")).strip(), "kind": str(c.get("kind", "")).strip(),
                        "reason": str(c.get("reason", "")).strip(), "basis": basis,
                        "basis_ok": bool(cited) and all(b in ids for b in cited)})
    warnings = []
    hits = media_s2_forbidden_hits(prompt_a + "\n" + prompt_b, material["forbidden"])
    if hits:
        warnings.append("금지 표현이 남아 있어요: " + ", ".join(hits))
    return {"ok": True, "broken": False, "errors": [], "warnings": warnings, "result": {
        "base": base, "prompt_a": prompt_a, "prompt_b": prompt_b, "changes": changes,
        "avoid": _media_s2_str_list(data.get("avoid")), "include": _media_s2_str_list(data.get("include")),
        "slot_warnings": _media_s2_str_list(data.get("slot_warnings")),
        "used_report": material["has_report"],
    }}


def media_s2_ai_run(draft: dict) -> dict:
    """재료 → 지시문 → OpenAI 부르기 → 확인. JSON이 깨졌으면 한 번만 다시 요청하고, 또 깨지면 취소.
    호출 자체가 실패하면 RuntimeError를 그대로 올립니다 (화면에서 경고로 보여 줌)."""
    material = media_s2_ai_material(draft)
    message = media_s2_ai_message(material)
    check = media_s2_ai_validate(media_s2_ai_call(MEDIA_S2_AI_SYSTEM, message), draft, material)
    if check["broken"]:
        check = media_s2_ai_validate(media_s2_ai_call(MEDIA_S2_AI_SYSTEM, message + MEDIA_S2_AI_RETRY_NOTE),
                                     draft, material)
        if check["broken"]:
            check["errors"] = ["AI 답이 두 번 모두 JSON 형식이 아니어서 취소했어요"]
    if check["result"] is not None:
        check["result"]["provider"] = f"OpenAI ({MEDIA_S2_OPENAI_MODEL})"
    return check
