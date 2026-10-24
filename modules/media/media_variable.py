# 3. 매체 제작 > 가설에서 변수 도출
# 2번 탭이 저장한 가설(store "hypothesis")을 받아 If/Because/Then으로 나누고,
# 바꿀 수 있는 후보 중 A/B로 돌릴 변수 하나를 고릅니다. 3번 탭의 하위 탭 ①(가설에서 변수 도출)에서 부릅니다.
# 고른 A/B 설계(plan)는 1번 리포트 값으로 채워 화면에 보여 주고, 사용자가 확정하면 2단계로 넘깁니다 (media_handoff.py).
# 바깥 값을 읽는 곳은 두 함수뿐입니다: 가설 media_variable_hypothesis(), 리포트 media_variable_report_sqp()
# (나중에 DB 등으로 출처가 바뀌면 이 두 함수만 고칩니다)
import time

import streamlit as st

from common.common_store import store_get
from modules.media.media_handoff import MEDIA_HANDOFF_PLAN, media_handoff_plan, media_handoff_set_plan

MEDIA_VARIABLE_LOAD_SECONDS = 1.2   # '가설 불러오기' 연출 시간 (실제 불러오기는 즉시 끝남)

# 담당자가 정한 기준 가설. 아래 후보·선정 표는 이 문장 기준이고,
# ② 탭에 아직 저장된 가설이 없으면 이 문장을 대신 씁니다.
MEDIA_VARIABLE_HYPOTHESIS = (
    "만약 메인 이미지를 펼친 패드의 냉감 원단 질감과 두께가 보이는 각도로 바꾸면, "
    "저가 제품과의 품질 차이가 바로 보여서, 'kühlende matratzenauflage' 검색에서 "
    "클릭 점유율 ÷ 노출 점유율이 0.63배에서 0.8배 이상으로 오를 것이다."
)
# 가설 콜아웃 각 줄 앞에 붙는 배지 (Streamlit 마크다운 배지 문법)
MEDIA_VARIABLE_BADGES = [":blue-badge[If]", ":violet-badge[Because]", ":green-badge[Then]"]
# KPI 이름: 가설 문장(2번 탭과 같은 원문)은 그대로 두고, 화면에 보일 때만 쉬운 이름으로 바꿉니다
MEDIA_VARIABLE_KPI_RAW = "클릭 점유율 ÷ 노출 점유율"
MEDIA_VARIABLE_KPI = MEDIA_HANDOFF_PLAN["kpi"]   # "노출 대비 클릭률"

MEDIA_VARIABLE_PICKED = "✅ 선정"   # 선정된 후보의 판정 값
# 후보 변수: (후보, 판정, 이유) · 기준은 가설의 If와 연결, 아마존 메인 이미지 규칙, Manage Your Experiments로 테스트 가능
# 순서 = 화면에 보일 우선순위. 화면에는 선정 1개 + 앞쪽 제외 후보만 MEDIA_VARIABLE_SHOW개까지 보여 줍니다
# (제외 이유가 서로 다른 후보를 앞에 두어 걸러내는 기준이 3줄로도 보이게 함)
MEDIA_VARIABLE_CANDIDATES = [
    ("메인 이미지 촬영 구도 (접힌 → 펼친 패드, 45도, 모서리 들기)", MEDIA_VARIABLE_PICKED, "If 그대로 · 흰 배경 실제 사진 · 메인 이미지 테스트 가능"),
    ("제목 앞에 OEKO-TEX·두께", "제외 → 다음 테스트", "가설의 If가 아님 (대안 가설)"),
    ("원단만 크게 찍은 클로즈업", "제외 → 서브 이미지", "두께가 빠지고 제품 85% 이상 기준에 걸림"),
    ("두께 숫자·화살표 표기", "제외 → 서브 이미지", "메인 이미지에는 텍스트 금지"),
    ("AI로 만든 침실 연출 장면", "제외 → 스폰서드 브랜드 광고", "메인 이미지는 실제 사진만"),
    ("가격·쿠폰", "제외 → 고정 요소", "가설과 무관"),
]
MEDIA_VARIABLE_SHOW = 3   # 후보 표에 보여 줄 줄 수 (가설·후보 목록이 바뀌어도 이 수만큼만)


def media_variable_hypothesis() -> tuple[str, str]:
    """② 탭에 저장된 가설 문장과 상태. 상태: "same"(기준 가설과 같음) / "other"(다른 가설) / "none"(저장 전)."""
    saved = store_get("hypothesis")
    text = str(saved.get("text") or "").strip() if isinstance(saved, dict) else ""
    if not text:
        return MEDIA_VARIABLE_HYPOTHESIS, "none"
    # KPI를 원래 이름으로 쓰든 쉬운 이름으로 쓰든 같은 가설로 봅니다
    same = media_variable_kpi_name(text) == media_variable_kpi_name(MEDIA_VARIABLE_HYPOTHESIS)
    return text, ("same" if same else "other")


def media_variable_kpi_name(text: str) -> str:
    """화면 표시용: 'A ÷ B' KPI 표현을 쉬운 이름(노출 대비 클릭률)으로 바꿉니다."""
    return text.replace(MEDIA_VARIABLE_KPI_RAW, MEDIA_VARIABLE_KPI)


def media_variable_split(text: str) -> list[str] | None:
    """가설 문장을 If / Because / Then 세 덩어리로 나눕니다. 나눌 수 없으면 None.
    - "만약 ~바꾸면, ~보여서, ~것이다."처럼 쉼표가 두 번 이상이면: 첫 덩어리 / 가운데 / 마지막
    - "만약 ~적용한다면, ~ 때문에 ~것이다."처럼 쉼표가 한 번이면: 뒤쪽을 마지막 "때문에"에서 나눔"""
    pieces = [p.strip() for p in text.split(", ") if p.strip()]
    if len(pieces) >= 3:
        return [pieces[0] + ",", ", ".join(pieces[1:-1]) + ",", pieces[-1]]
    if len(pieces) == 2 and " 때문에 " in pieces[1]:
        because, then = pieces[1].rsplit(" 때문에 ", 1)
        return [pieces[0] + ",", because + " 때문에", then]
    return None


def media_variable_callout(text: str) -> None:
    """가설 콜아웃(st.info). If / Because / Then을 배지 붙은 줄로 나누고, Then(KPI)은 굵게 표시합니다.
    나눌 수 없는 문장은 한 덩어리로 보여 줍니다."""
    text = media_variable_kpi_name(text)
    parts = media_variable_split(text)
    if parts:
        parts[2] = f"**{parts[2]}**"
        body = "  \n".join(f"{badge} {part}" for badge, part in zip(MEDIA_VARIABLE_BADGES, parts))
    else:
        body = text
    st.info(body, icon="📥")



def media_variable_shown_candidates(rows: list) -> list:
    """후보 표에 보여 줄 줄: 선정된 후보를 맨 위에, 나머지는 목록 순서대로 채워 MEDIA_VARIABLE_SHOW개까지."""
    picked = [r for r in rows if r[1] == MEDIA_VARIABLE_PICKED]
    others = [r for r in rows if r[1] != MEDIA_VARIABLE_PICKED]
    return (picked + others)[:MEDIA_VARIABLE_SHOW]


def media_variable_report_sqp() -> dict:
    """1번 리포트의 검색어 클릭 분석(store "report"의 sqp). 없으면 빈 dict."""
    report = store_get("report")
    sqp = report.get("sqp") if isinstance(report, dict) else None
    return sqp if isinstance(sqp, dict) else {}


def media_variable_plan() -> tuple[dict, str, list[str]]:
    """(A/B 설계 plan, 가격 문구, 기본값을 쓴 항목 이름 목록).
    plan은 media_handoff.py의 기본값(MEDIA_HANDOFF_PLAN)에서 시작해, 1번 리포트에 값이 있으면 덮어씁니다."""
    sqp = media_variable_report_sqp()
    listing = sqp.get("listing") if isinstance(sqp.get("listing"), dict) else {}
    plan, defaults = dict(MEDIA_HANDOFF_PLAN), []
    # (plan 키, 리포트 값, 맞는 자료형, 화면에 보일 이름)
    for key, value, kind, label in [
        ("query", sqp.get("query"), str, "검색어"),
        ("a", listing.get("main_image"), str, "A · 대조군"),
        ("kpi_now", sqp.get("ratio"), (int, float), "지금 KPI"),
        ("kpi_goal", sqp.get("kpi_goal"), (int, float), "목표 KPI"),
    ]:
        if isinstance(value, kind) and value != "":
            plan[key] = value
        else:
            defaults.append(label)
    if isinstance(listing.get("price"), (int, float)):
        price = f"€{listing['price']:.2f}"
    else:
        price = "현재 가격"
        defaults.append("가격")
    return plan, price, defaults


def media_variable_hypothesis_step(plan: dict, text: str, status: str):
    """2번 가설 탭에서 가져온 가설 콜아웃 + 핵심 요약 카드 (media_variable_step()의 윗부분)."""
    # 넓은 화면: 왼쪽(하위 탭 바 아래 빈자리)에 핵심 요약, 오른쪽(탭 바와 같은 줄)에 가설 콜아웃 (media_style.css)
    with st.container(horizontal=True, key="media-hypo-top"):
        with st.container(key="media-hypo-summary"):
            st.markdown(f":violet-badge[독립 변수] {plan['variable']} (접힌 → 펼친 패드)  \n"
                        f":green-badge[KPI] {plan['kpi']} {plan['kpi_now']:g}배 → **{plan['kpi_goal']:g}배 이상**")
        with st.container(key="media-hypo-callout"):
            media_variable_callout(text)
    # status == "none"(2번 탭 저장 전)이면 기준 가설을 그대로 보여 줍니다. '가설 불러오기' 연출과 맞도록 따로 안내하지 않습니다.
    if status == "other":
        st.warning("2번 가설 탭에 저장된 가설이 기준 가설과 다릅니다. 아래 후보·선정 표는 기준 가설 기준이라, "
                   "2번 탭에서 '이 가설 문장을 위 칸에 넣기'로 기준 가설을 저장하거나 표를 새 가설에 맞게 바꿔야 합니다. "
                   "그 전까지는 2단계로 넘기는 A/B 설계를 새로 저장하지 않습니다.")
        with st.expander("기준 가설 보기", expanded=False):
            media_variable_callout(MEDIA_VARIABLE_HYPOTHESIS)


def media_variable_derive_step(plan: dict, price: str, defaults: list[str]):
    """후보 변수 걸러내기 → 단일 변수 선정 (media_variable_step()의 아랫부분). 선정 표의 값은 plan에서 가져옵니다."""
    c1, c2 = st.columns([1, 1], gap="medium")
    with c1:
        # 걸러내는 기준은 제목 옆 ⓘ에 마우스를 올리면 보임 (설명 줄이 빠져 오른쪽 선정 표와 위쪽 끝이 맞음)
        st.markdown("**후보 변수 걸러내기**",
                    help="가설의 If와 맞고, 아마존 메인 이미지 규칙 안이며, Manage Your Experiments로 돌릴 수 있어야 함")
        # key="media-variable-candidates": media_style.css가 판정 칸을 한 줄로 유지 (줄 높이가 들쭉날쭉하지 않게)
        with st.container(key="media-variable-candidates"):
            st.markdown("| 후보 | 판정 | 이유 |\n| --- | --- | --- |\n"
                        + "\n".join(f"| {' | '.join(row)} |"
                                    for row in media_variable_shown_candidates(MEDIA_VARIABLE_CANDIDATES)))
    with c2:
        st.markdown("**선정한 단일 변수**")
        st.markdown("| 구분 | 내용 |\n| --- | --- |\n"
                    f"| **독립 변수 (바꾸는 것 1개)** | {plan['variable']} |\n"
                    f"| **A · 대조군** | {plan['a']} (지금 그대로) |\n"
                    f"| **B · 실험군** | {plan['b']} |\n"
                    f"| **통제 변수 (고정)** | 같은 제품·색상, 흰 배경, 같은 조명과 보정, 제품 85% 이상 · 제목, 가격 {price}, 쿠폰 없음, "
                    "불릿, A+ 콘텐츠, 서브 이미지, 광고 입찰 |\n"
                    f"| **종속 변수 (메인 KPI)** | {plan['kpi']} {plan['kpi_now']:g}배 → {plan['kpi_goal']:g}배 이상 "
                    f"(= {MEDIA_VARIABLE_KPI_RAW}, 시장 대비 CTR) |\n"
                    f"| **안전장치** | CVR(단위 세션 비율)이 A보다 {plan['cvr_tolerance']:g}%p 넘게 떨어지면 B 실패 |")
        if defaults:   # 리포트 탭을 아직 안 열었거나 리포트 칸 이름이 바뀌었을 때 바로 알아차리도록
            st.caption(f"1번 리포트 값이 없어 기본값으로 보여 줘요: {', '.join(defaults)}")
    st.caption("두께와 원단 질감을 변수 두 개로 나누지 않는 이유: 가설이 말하는 원인은 '품질 차이가 안 보인다' 하나이고, "
               "모서리를 든 사진 한 장에 둘 다 담깁니다. Manage Your Experiments는 한 번에 두 안(A/B)만 비교하므로, "
               "둘을 따로 보려면 이 테스트가 끝난 뒤 B 안에서 다시 나눠 테스트합니다.")


def _media_variable_confirm(plan: dict) -> None:
    """'이 변수로 확정' 버튼 콜백. A/B 설계를 2단계로 넘기고(modules/media/data/media_handoff_plan.json), 다음 화면에서 토스트를 띄웁니다."""
    media_handoff_set_plan(plan)
    st.session_state["media-variable-confirmed-toast"] = True


def media_variable_confirm_step(plan: dict, status: str):
    """선정 표 아래 확정 줄: 사용자가 추천된 단일 변수를 확인하고 확정해야 2단계로 넘어갑니다."""
    saved = media_handoff_plan()
    confirmed = not saved["sample"] and all(saved.get(k) == v for k, v in plan.items())
    if st.session_state.pop("media-variable-confirmed-toast", False):
        st.toast("단일 변수를 확정해 2단계로 넘겼어요", icon="✅")
    if status == "other":   # 2번 탭 가설이 기준 가설과 달라 선정 표가 그 가설에 맞지 않음
        note = "2번 탭 가설이 기준 가설과 달라 확정할 수 없어요"
    elif confirmed:
        note = ":green-badge[✅ 확정됨] 2단계(프롬프트 만들기)가 이 값을 받아요"
    elif not saved["sample"]:   # 확정한 뒤 리포트 값 등이 바뀜
        note = ":orange-badge[다시 확정 필요] 확정한 뒤 값이 바뀌었어요. 2단계는 아직 이전 값을 받아요"
    else:
        note = "추천된 변수를 확인하고 확정하면 2단계(프롬프트 만들기)로 넘어가요"
    with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center",
                      key="media-variable-confirm-row"):
        st.markdown(note)
        if not confirmed:   # 확정된 뒤에는 버튼을 숨기고, 값이 바뀌면 '다시 확정'으로 다시 보여 줌
            st.button("다시 확정" if not saved["sample"] else "이 변수로 확정", key="media-btn-variable-confirm",
                      type="primary", disabled=status == "other",
                      on_click=_media_variable_confirm, args=(plan,))


def _media_variable_start_load() -> None:
    """'가설 불러오기' 버튼 콜백. 다음 화면 그리기에서 불러오는 연출(스피너)을 보여 주도록 표시만 해 둡니다."""
    st.session_state["media-hypo-loading"] = True


def media_variable_step():
    """하위 탭 '가설에서 변수 도출': 오른쪽 위 '가설 불러오기' 버튼 → 가설 콜아웃 → 후보 걸러내기·단일 변수 선정.
    반드시 media_render() 안에서 부릅니다."""
    loading = st.session_state.pop("media-hypo-loading", False)
    loaded = loading or st.session_state.get("media-hypo-loaded", False)
    with st.container(horizontal=True, horizontal_alignment="right", key="media-hypo-load-row"):
        st.button("↻ 다시 불러오기" if loaded else "📥 가설 불러오기", key="media-btn-hypo-load",
                  type="secondary" if loaded else "primary", on_click=_media_variable_start_load)

    # 버튼을 누른 직후 한 번만: 2번 탭에서 가져오는 것처럼 잠깐 스피너를 보여 준 뒤 가설을 표시
    if loading:
        with st.spinner("2번 가설 탭에서 가설을 불러오는 중…"):
            time.sleep(MEDIA_VARIABLE_LOAD_SECONDS)
        st.session_state["media-hypo-loaded"] = True
        st.toast("가설을 불러왔어요", icon="📥")

    if not loaded:
        with st.container(border=True, key="media-hypo-empty"):
            st.markdown("**아직 불러온 가설이 없어요**")
            st.caption("오른쪽 위 '가설 불러오기'를 누르면 2번 가설 탭의 가설을 가져와 A/B로 바꿀 변수를 도출해요.")
        return

    # key="media-hypo-box": media_style.css의 나타나는 애니메이션(.st-key-media-hypo-box)
    text, status = media_variable_hypothesis()
    plan, price, defaults = media_variable_plan()
    with st.container(key="media-hypo-box"):
        media_variable_hypothesis_step(plan, text, status)
        # key="media-hypo-divider": media_style.css가 구분선 위아래 기본 여백(2em)을 줄여 윗줄 바로 아래에 붙임
        with st.container(key="media-hypo-divider"):
            st.divider()
        media_variable_derive_step(plan, price, defaults)
        media_variable_confirm_step(plan, status)
