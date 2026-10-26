# 3. 매체 제작 > 단계 사이 데이터 주고받기 (1단계 담당 파일 · 2·3단계는 읽고 부르기만)
# 1단계(가설에서 변수 도출) → 2단계(A/B 소재 준비: 프롬프트 만들기·AI 다듬기) → 3단계(사진·영상 초안 → 외주 정리)로 넘기는 값의 모양을 여기서 정합니다.
# 모양(키 이름)을 바꿀 때는 세 담당자가 같이 정하고 이 파일만 고칩니다.
#
# 넘긴 값은 Supabase의 공용 저장소(store "media"의 "handoff" 칸)에 저장됩니다. 프로젝트 파일은 바뀌지 않습니다.
#   store("media") = {"results": [...], "handoff": {"plan": {...}, "prompt": {...}, "assets": {...}}}
#   plan   : 1단계 B안 체크(체크 = 확정, 체크를 풀면 지움) → 2단계가 읽음
#   prompt : 2단계 'A/B 소재 준비'의 '다음' 버튼 (media_page.py → media_s2_handoff_now()) → 3단계 '사진·영상 초안 제작'이 읽음
#   assets : 3단계 '사진·영상 초안 제작'의 넘기기 버튼                               → 3단계 '외주 정리'가 읽음
# 단계 사이 값이 아닌 것: 1단계에서 이미지로 진행할 수 없는 변수의 줄글 솔루션을 확정하면 store("media")의 "solution" 칸
#   (handoff 밖, 확정한 솔루션 기록 · 모양은 media_handoff_set_solution(). 사용자는 팝업에서 보고서용 .md 파일로 내려받음)
# 저장은 각 단계의 확정(1단계는 B안 체크)·넘기기 버튼을 눌렀을 때만 합니다. (화면을 열기만 해서는 저장되지 않음)
# 앞 단계가 아직 넘기지 않았으면 아래 예시 값에 "sample": True가 붙어 와서 각자 먼저 개발할 수 있습니다.
# Supabase에 연결할 수 없으면 같은 브라우저 접속 안에서만 이어집니다.
import time

import streamlit as st

from common.common_store import store_get, store_set

MEDIA_HANDOFF_STORE = "media"      # store 키 (media 모듈 키 하나에 같이 저장)
MEDIA_HANDOFF_FRESH_SEC = 3        # 이 시간(초)이 지나면 Supabase에서 다시 읽음 (다른 사람이 넘긴 값 받기)
MEDIA_HANDOFF_SLOT = "{slot}"   # 기본 프롬프트 안의 빈칸 표시

# 1단계 → 2단계: A/B 테스트 설계 기본값. 1단계(media_variable.py)가 '이 변수로 확정' 버튼으로
# media_handoff_set_plan()을 부르면 그 값이 대신 쓰입니다.
MEDIA_HANDOFF_PLAN = {
    "query": "kühlende matratzenauflage",          # 검색어
    "variable": "메인 이미지 촬영 구도",              # 독립 변수 (바꾸는 것 1개)
    "a": "접힌 패드 (위에서 찍은 사진)",              # A · 대조군 (지금 그대로)
    "b": "펼친 패드를 45도 위에서, 모서리를 살짝 들어 두께와 냉감 원단 결이 보이게",   # B · 실험군
    "kpi": "노출 대비 클릭률",                      # 종속 변수 이름 (= 클릭 점유율 ÷ 노출 점유율, media_variable.py도 이 값을 씀)
    "kpi_now": 0.63,                               # 지금 값 (배)
    "kpi_goal": 0.8,                               # 목표 값 (배 이상)
    "cvr_tolerance": 0.5,                          # 안전장치: B의 CVR이 A보다 이만큼(%p) 넘게 떨어지면 B 실패
    "b_ref": "",                                   # 고른 B안의 영어 레퍼런스 프롬프트 (후보 파일의 ref_prompt, 2단계가 빈칸 B로 잘라 씀)
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


def _media_handoff_all(fresh: bool) -> dict:
    """store("media")의 handoff 칸 전체. fresh면 (MEDIA_HANDOFF_FRESH_SEC마다 한 번) Supabase에서 다시 읽습니다."""
    last = st.session_state.get("media-handoff-read-at", 0.0)
    if fresh and time.time() - last < MEDIA_HANDOFF_FRESH_SEC:
        fresh = False   # 한 번 화면을 그리는 동안 여러 번 불러도 Supabase는 한 번만 읽음
    if fresh:
        st.session_state["media-handoff-read-at"] = time.time()
    saved = store_get(MEDIA_HANDOFF_STORE, fresh=fresh)
    handoff = saved.get("handoff") if isinstance(saved, dict) else None
    return handoff if isinstance(handoff, dict) else {}


def _media_handoff_get(name: str):
    """name 단계 값. 다른 사람이 방금 넘긴 값도 받도록 Supabase에서 새로 읽고, 없으면 None."""
    value = _media_handoff_all(fresh=True).get(name)
    return value if isinstance(value, dict) else None


def _media_handoff_put(name: str, value: dict) -> None:
    """name 단계 값을 저장합니다. media 키의 다른 칸(results 등)과 다른 단계 값은 그대로 둡니다.
    반드시 넘기기 버튼의 콜백에서만 부릅니다."""
    saved = store_get(MEDIA_HANDOFF_STORE, fresh=True)
    data = dict(saved) if isinstance(saved, dict) else {}
    handoff = dict(data.get("handoff") or {})
    if handoff.get(name) == value:
        return
    handoff[name] = dict(value)
    data["handoff"] = handoff
    store_set(MEDIA_HANDOFF_STORE, data)


def media_handoff_set_plan(plan: dict) -> None:
    """1단계가 A/B 설계를 정하면 부릅니다. 모양은 MEDIA_HANDOFF_PLAN과 같게 넣습니다."""
    _media_handoff_put("plan", plan)


def media_handoff_clear_plan() -> None:
    """1단계가 확정을 취소하면(체크한 B안을 다시 눌러 체크를 풂) 부릅니다. 넘긴 A/B 설계만 지우고 다른 단계 값은 그대로 둡니다.
    지운 뒤에는 media_handoff_plan()이 다시 예시 값("sample": True)을 돌려줍니다. 반드시 체크박스 콜백에서만 부릅니다."""
    saved = store_get(MEDIA_HANDOFF_STORE, fresh=True)
    data = dict(saved) if isinstance(saved, dict) else {}
    handoff = dict(data.get("handoff") or {})
    if handoff.pop("plan", None) is None:
        return
    data["handoff"] = handoff
    store_set(MEDIA_HANDOFF_STORE, data)


def media_handoff_plan() -> dict:
    """1단계 → 2단계: A/B 테스트 설계. 1단계가 아직 저장하지 않았으면 예시 값(MEDIA_HANDOFF_PLAN)에 "sample": True."""
    saved = _media_handoff_get("plan")
    if saved:
        return {**MEDIA_HANDOFF_PLAN, **saved, "sample": False}
    return {**MEDIA_HANDOFF_PLAN, "sample": True}


def media_handoff_set_solution(solution: dict) -> None:
    """1단계에서 진행 불가 변수의 솔루션을 확정하면 부릅니다 (store("media")의 "solution" 칸, 다른 칸은 그대로).
    모양: {"hypothesis", "variable", "kind", "title", "summary", "steps": [{"action", "detail"}], "effect", "check", "source"}. 반드시 확정 버튼의 콜백에서만 부릅니다."""
    saved = store_get(MEDIA_HANDOFF_STORE, fresh=True)
    data = dict(saved) if isinstance(saved, dict) else {}
    if data.get("solution") == solution:
        return
    data["solution"] = dict(solution)
    store_set(MEDIA_HANDOFF_STORE, data)


def media_handoff_solution() -> dict:
    """확정해 둔 솔루션 (없으면 빈 dict)."""
    saved = store_get(MEDIA_HANDOFF_STORE)
    solution = saved.get("solution") if isinstance(saved, dict) else None
    return solution if isinstance(solution, dict) else {}


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


# 3단계 사진·영상 초안 제작 → 외주 정리: 넘긴 영상 스토리보드와 파일 이름 (사진·영상 파일 자체는 크기 때문에 같은 브라우저 접속 안에만 둠)
MEDIA_HANDOFF_ASSETS_SAMPLE = {
    "storyboard": [],   # 확정한 스토리보드 장면 목록
    "photos": [],       # 넘긴 사진 파일 이름
    "videos": [],       # 넘긴 영상 파일 이름
}


def media_handoff_set_assets(assets: dict) -> None:
    """3단계 '사진·영상 초안 제작'에서 넘기기 버튼을 누르면 부릅니다. 모양은 MEDIA_HANDOFF_ASSETS_SAMPLE과 같게 넣습니다."""
    _media_handoff_put("assets", assets)


def media_handoff_assets() -> dict:
    """3단계 사진·영상 초안 제작 → 외주 정리: 넘긴 스토리보드·파일 이름. 아직 안 넘겼으면 빈 예시 값에 "sample": True."""
    saved = _media_handoff_get("assets")
    return {**MEDIA_HANDOFF_ASSETS_SAMPLE, **saved, "sample": False} if saved else         {**MEDIA_HANDOFF_ASSETS_SAMPLE, "sample": True}


def media_handoff_set_result(result: dict) -> None:
    """(새 흐름에서는 쓰지 않음) 판정을 마치면 부릅니다. 모양은 MEDIA_HANDOFF_RESULT_SAMPLE과 같게 넣습니다."""
    _media_handoff_put("result", result)


def media_handoff_result() -> dict:
    """(새 흐름에서는 쓰지 않음) 판정 결과. 아직 없으면 예시 값에 "sample": True를 붙여 돌려줍니다."""
    saved = _media_handoff_get("result")
    if saved:
        return {**saved, "sample": False}
    return {**MEDIA_HANDOFF_RESULT_SAMPLE, "sample": True}
