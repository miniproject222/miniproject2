# 3. 매체 제작 > 단계 사이 데이터 주고받기 (1단계 담당 파일 · 2·3단계는 읽고 부르기만)
# 1단계(단일 변수 추출 ~ A/B 소재 선정) → 2단계(프롬프트 만들기·AI 다듬기) → 3단계(사진·영상 초안 → 외주 정리)로 넘기는 값의 모양을 여기서 정합니다.
# 모양(키 이름)을 바꿀 때는 세 담당자가 같이 정하고 이 파일만 고칩니다.
#
# 넘긴 값은 각 단계 폴더의 JSON 파일로 저장됩니다. 그 파일을 커밋·푸시하면, 다른 컴퓨터에서 풀 받은 사람에게 자동으로 이어집니다.
#   1단계 → modules/media/data/media_handoff_plan.json              (min이 올림)
#   2단계 → modules/media/media_stage2/data/media_stage2_prompt.json (JY가 올림)
# 단계마다 자기 폴더의 파일 하나만 쓰므로 합칠 때 충돌이 나지 않습니다.
# 앞 단계 파일이 아직 없으면 아래 예시 값이 와서 각자 먼저 개발할 수 있습니다.
import json
from pathlib import Path

MEDIA_HANDOFF_DIR = Path(__file__).resolve().parent
MEDIA_HANDOFF_FILES = {
    "plan": MEDIA_HANDOFF_DIR / "data" / "media_handoff_plan.json",
    "prompt": MEDIA_HANDOFF_DIR / "media_stage2" / "data" / "media_stage2_prompt.json",
    "result": MEDIA_HANDOFF_DIR / "media_stage2" / "data" / "media_stage2_result.json",   # (새 흐름에서는 안 씀)
}
MEDIA_HANDOFF_SLOT = "{slot}"   # 기본 프롬프트 안의 빈칸 표시

# 1단계 → 2단계: A/B 테스트 설계 기본값. 1단계(media_variable.py)가 1번 리포트 값으로 덮어쓴 뒤
# '가설 불러오기'를 마친 화면에서 media_handoff_set_plan()으로 자동 저장하면 그 값이 대신 쓰입니다.
MEDIA_HANDOFF_PLAN = {
    "query": "kühlende matratzenauflage",          # 검색어
    "variable": "메인 이미지 촬영 구도",              # 독립 변수 (바꾸는 것 1개)
    "a": "접힌 패드 (위에서 찍은 사진)",              # A · 대조군 (지금 그대로)
    "b": "펼친 패드를 45도 위에서, 모서리를 살짝 들어 두께와 냉감 원단 결이 보이게",   # B · 실험군
    "kpi": "노출 대비 클릭률",                      # 종속 변수 이름 (= 클릭 점유율 ÷ 노출 점유율, media_variable.py도 이 값을 씀)
    "kpi_now": 0.63,                               # 지금 값 (배)
    "kpi_goal": 0.8,                               # 목표 값 (배 이상)
    "cvr_tolerance": 0.5,                          # 안전장치: B의 CVR이 A보다 이만큼(%p) 넘게 떨어지면 B 실패
}

# 2단계 → 3단계: 프롬프트 재료 예시. 2단계가 아직 넣지 않았을 때 3단계가 이 값으로 먼저 개발합니다.
# 완성된 A/B 두 줄이 아니라 기본 프롬프트와 빈칸을 따로 넘겨야 3단계가 "빈칸 밖이 바뀌었나"를 확인할 수 있습니다.
MEDIA_HANDOFF_PROMPT_SAMPLE = {
    "variable": "메인 이미지 촬영 구도",           # 단일 변수
    "base": "Product photo reference, white seamless background, a cooling mattress pad 90x200 cm "
            "{slot}, soft even studio light, no text, no props",   # 기본 프롬프트 (빈칸 자리는 {slot})
    "slot_a": "folded, seen from above",          # A 빈칸
    "slot_b": "laid flat, camera 45 degrees above, one corner gently lifted to show the edge thickness "
              "and the knitted cooling fabric texture",           # B 빈칸
    # 고정 요소: 기본 프롬프트 안의 문구 그대로 (다듬은 뒤에도 남아 있어야 함)
    "fixed": ["white seamless background", "90x200 cm", "soft even studio light", "no text", "no props"],
    # 2단계 AI 다듬기 결과 (다듬기 전이면 빈칸만 채운 문장, 바꾼 곳 없음)
    "prompt_a": "",                                # 다듬은 프롬프트 A (비어 있으면 base + slot_a)
    "prompt_b": "",                                # 다듬은 프롬프트 B (비어 있으면 base + slot_b)
    "changes": [],                                 # 바꾼 곳 [{"where", "kind": "뺌"|"더함", "reason", "basis": DB ID}]
    "avoid": [],                                   # 찍지 말 것 (외주 브리프로 그대로 감)
    "include": [],                                 # 넣을 것 (외주 브리프로 그대로 감)
}

# (새 흐름에서는 쓰지 않음) 판정 결과 예시. 2단계가 아직 결과를 넣지 않았을 때 3단계가 이 값으로 먼저 개발합니다.
# (지금 숫자는 2단계 가상 데이터 media_ab_result_dummy_202610.json으로 계산한 값)
MEDIA_HANDOFF_RESULT_SAMPLE = {
    "source": "가상",                # 데이터 출처 ("가상" / "실제")
    "winner": "B",                   # 승자 안 이름
    "b_wins": True,                  # B(실험군)가 이겼는지
    "kpi": [0.63, 0.84],             # 노출 대비 클릭률 [A, B] (배)
    "cvr": [0.0861, 0.0847],         # CVR [A, B] (0~1 비율)
    "cvr_ok": True,                  # 안전장치 통과 여부
    "p_ctr": 0.0001,                 # CTR 차이의 유의확률 (0.05 미만이면 의미 있는 차이)
}


def _media_handoff_get(name: str):
    """name 단계 파일을 읽습니다. 풀 받은 최신 파일을 쓰도록 매번 새로 읽고, 없거나 깨져 있으면 None."""
    path = MEDIA_HANDOFF_FILES[name]
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _media_handoff_put(name: str, value: dict) -> None:
    """name 단계 파일에 저장합니다. 값이 그대로면 쓰지 않습니다 (화면이 다시 그려질 때마다 파일이 바뀌지 않게)."""
    if _media_handoff_get(name) == value:
        return
    path = MEDIA_HANDOFF_FILES[name]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def media_handoff_set_plan(plan: dict) -> None:
    """1단계가 A/B 설계를 정하면 부릅니다. 모양은 MEDIA_HANDOFF_PLAN과 같게 넣습니다."""
    _media_handoff_put("plan", plan)


def media_handoff_plan() -> dict:
    """1단계 → 2단계: A/B 테스트 설계. 1단계가 아직 저장하지 않았으면 예시 값(MEDIA_HANDOFF_PLAN)에 "sample": True."""
    saved = _media_handoff_get("plan")
    if saved:
        return {**MEDIA_HANDOFF_PLAN, **saved, "sample": False}
    return {**MEDIA_HANDOFF_PLAN, "sample": True}


def media_handoff_set_prompt(prompt: dict) -> None:
    """2단계가 프롬프트 재료를 다 만들면 부릅니다. 모양은 MEDIA_HANDOFF_PROMPT_SAMPLE과 같게 넣습니다."""
    _media_handoff_put("prompt", prompt)


def media_handoff_prompt() -> dict:
    """2단계 → 3단계: 프롬프트 재료와 다듬은 결과. 2단계가 아직 넣지 않았으면 예시 값에 "sample": True를 붙여 돌려줍니다.
    다듬은 프롬프트(prompt_a/prompt_b)가 비어 있으면 빈칸만 채운 문장으로 채워서 돌려줍니다."""
    saved = _media_handoff_get("prompt")
    src = {**MEDIA_HANDOFF_PROMPT_SAMPLE, **saved, "sample": False} if saved else \
        {**MEDIA_HANDOFF_PROMPT_SAMPLE, "sample": True}
    src = {**src, **{k: list(src[k]) for k in ("fixed", "changes", "avoid", "include")}}
    src["prompt_a"] = src["prompt_a"] or media_handoff_fill(src["base"], src["slot_a"])
    src["prompt_b"] = src["prompt_b"] or media_handoff_fill(src["base"], src["slot_b"])
    return src


def media_handoff_fill(base: str, slot: str) -> str:
    """기본 프롬프트의 빈칸({slot})을 채웁니다."""
    return base.replace(MEDIA_HANDOFF_SLOT, slot, 1)


def media_handoff_check(src: dict, prompt_a: str, prompt_b: str) -> dict:
    """A/B 확인 (2단계 다듬기 직후, 3단계 받을 때 둘 다 씀):
    빈칸 문구가 남아 있는지, 빈칸 밖이 A와 B에서 똑같은지, 고정 요소가 빠지지 않았는지."""
    slot_a, slot_b = src["slot_a"], src["slot_b"]
    slot_ok = slot_a in prompt_a and slot_b in prompt_b
    # 빈칸 문구를 다시 {slot}으로 바꿔 나머지를 비교 (빈칸이 없으면 비교할 수 없어 실패)
    rest_a = prompt_a.replace(slot_a, MEDIA_HANDOFF_SLOT, 1)
    rest_b = prompt_b.replace(slot_b, MEDIA_HANDOFF_SLOT, 1)
    same_rest = slot_ok and rest_a == rest_b
    missing = [f for f in src["fixed"] if f not in prompt_a or f not in prompt_b]
    return {"slot_ok": slot_ok, "same_rest": same_rest, "missing": missing,
            "ok": slot_ok and same_rest and not missing}


def media_handoff_set_result(result: dict) -> None:
    """(새 흐름에서는 쓰지 않음) 판정을 마치면 부릅니다. 모양은 MEDIA_HANDOFF_RESULT_SAMPLE과 같게 넣습니다."""
    _media_handoff_put("result", result)


def media_handoff_result() -> dict:
    """(새 흐름에서는 쓰지 않음) 판정 결과. 아직 없으면 예시 값에 "sample": True를 붙여 돌려줍니다."""
    saved = _media_handoff_get("result")
    if saved:
        return {**saved, "sample": False}
    return {**MEDIA_HANDOFF_RESULT_SAMPLE, "sample": True}
