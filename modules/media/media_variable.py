# 3. 매체 제작 > 가설에서 변수 도출
# 2번 탭이 저장한 가설(store "hypothesis")을 받아 If/Because/Then으로 나누고,
# 바꿀 수 있는 후보 중 A/B로 돌릴 변수 하나를 고릅니다. 3번 탭의 하위 탭 ①(가설 확인)·②(변수 도출)에서 부릅니다.
import streamlit as st

from common.common_store import store_get

# 담당자가 정한 기준 가설. 아래 후보·선정 표는 이 문장 기준이고,
# ② 탭에 아직 저장된 가설이 없으면 이 문장을 대신 씁니다.
MEDIA_VARIABLE_HYPOTHESIS = (
    "만약 메인 이미지를 펼친 패드의 냉감 원단 질감과 두께가 보이는 각도로 바꾸면, "
    "저가 제품과의 품질 차이가 바로 보여서, 'kühlende matratzenauflage' 검색에서 "
    "클릭 점유율 ÷ 노출 점유율이 0.63배에서 0.8배 이상으로 오를 것이다."
)
# 가설 콜아웃 각 줄 앞에 붙는 배지 (Streamlit 마크다운 배지 문법)
MEDIA_VARIABLE_BADGES = [":blue-badge[If]", ":violet-badge[Because]", ":green-badge[Then]"]
MEDIA_VARIABLE_TEMPLATE = ("만약 [타깃/지점]에 [구체적인 액션]을 적용한다면(If), [이유/고객 심리] 때문에(Because), "
                           "[측정 가능한 지표/KPI]가 [얼마나] 개선될 것이다(Then).")

# 후보 변수: (후보, 판정, 이유) · 기준은 가설의 If와 연결, 아마존 메인 이미지 규칙, Manage Your Experiments로 테스트 가능
MEDIA_VARIABLE_CANDIDATES = [
    ("메인 이미지 촬영 구도 (접힌 → 펼친 패드, 45도, 모서리 들기)", "✅ 선정", "If 그대로 · 흰 배경 실제 사진 · 메인 이미지 테스트 가능"),
    ("원단만 크게 찍은 클로즈업", "제외 → 서브 이미지", "두께가 빠지고 제품 85% 이상 기준에 걸림"),
    ("두께 숫자·화살표 표기", "제외 → 서브 이미지", "메인 이미지에는 텍스트 금지"),
    ("AI로 만든 침실 연출 장면", "제외 → 스폰서드 브랜드 광고", "메인 이미지는 실제 사진만"),
    ("제목 앞에 OEKO-TEX·두께", "제외 → 다음 테스트", "가설의 If가 아님 (대안 가설)"),
    ("가격·쿠폰", "제외 → 고정 요소", "가설과 무관"),
]


def media_variable_hypothesis() -> tuple[str, str]:
    """② 탭에 저장된 가설 문장과 상태. 상태: "same"(기준 가설과 같음) / "other"(다른 가설) / "none"(저장 전)."""
    saved = store_get("hypothesis")
    text = str(saved.get("text") or "").strip() if isinstance(saved, dict) else ""
    if not text:
        return MEDIA_VARIABLE_HYPOTHESIS, "none"
    return text, ("same" if text == MEDIA_VARIABLE_HYPOTHESIS else "other")


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
    parts = media_variable_split(text)
    if parts:
        parts[2] = f"**{parts[2]}**"
        body = "  \n".join(f"{badge} {part}" for badge, part in zip(MEDIA_VARIABLE_BADGES, parts))
    else:
        body = text
    st.info(body, icon="📥")



def media_variable_listing() -> tuple[str, str]:
    """1번 리포트의 우리 상품 정보에서 (현재 메인 이미지 설명, 가격 문구). 없으면 기본 문구."""
    report = store_get("report")
    sqp = report.get("sqp") if isinstance(report, dict) else None
    listing = (sqp.get("listing") or {}) if isinstance(sqp, dict) else {}
    price = f"€{listing['price']:.2f}" if isinstance(listing.get("price"), (int, float)) else "현재 가격"
    return listing.get("main_image") or "현재 메인 이미지", price


def media_variable_hypothesis_step():
    """하위 탭 ① 가설 확인: ② 탭에서 가져온 가설 콜아웃. 반드시 media_render() 안에서 부릅니다."""
    text, status = media_variable_hypothesis()
    media_variable_callout(text)
    st.caption(f"가설 구조 · {MEDIA_VARIABLE_TEMPLATE}")
    if status == "none":
        st.caption("② 가설 탭에 저장된 가설이 없어 기준 가설을 대신 보여 줍니다. ② 탭에서 가설을 저장하면 여기에 바로 반영됩니다.")
    elif status == "other":
        st.warning("② 탭에 저장된 가설이 기준 가설과 다릅니다. 다음 단계의 후보·선정 표는 기준 가설 기준이라, "
                   "② 탭에서 '이 가설 문장을 위 칸에 넣기'로 기준 가설을 저장하거나 표를 새 가설에 맞게 바꿔야 합니다.")
        with st.expander("기준 가설 보기", expanded=False):
            media_variable_callout(MEDIA_VARIABLE_HYPOTHESIS)


def media_variable_derive_step():
    """하위 탭 ② 가설에서 변수 도출: 후보 변수 걸러내기 → 단일 변수 선정. 반드시 media_render() 안에서 부릅니다."""
    current, price = media_variable_listing()
    c1, c2 = st.columns([1, 1], gap="medium")
    with c1:
        st.markdown("**후보 변수 걸러내기**")
        st.caption("가설의 If와 맞고, 아마존 메인 이미지 규칙 안이며, Manage Your Experiments로 돌릴 수 있어야 함")
        st.markdown("| 후보 | 판정 | 이유 |\n| --- | --- | --- |\n"
                    + "\n".join(f"| {' | '.join(row)} |" for row in MEDIA_VARIABLE_CANDIDATES))
    with c2:
        st.markdown("**선정한 단일 변수**")
        st.markdown("| 구분 | 내용 |\n| --- | --- |\n"
                    "| **독립 변수 (바꾸는 것 1개)** | 메인 이미지의 촬영 구도 |\n"
                    f"| **A · 대조군** | {current} (지금 그대로) |\n"
                    "| **B · 실험군** | 같은 패드를 펼쳐 45도 위에서, 한쪽 모서리를 살짝 들어 두께와 냉감 원단 결이 보이게 |\n"
                    f"| **통제 변수 (고정)** | 같은 제품·색상, 흰 배경, 같은 조명과 보정, 제품 85% 이상 · 제목, 가격 {price}, 쿠폰 없음, "
                    "불릿, A+ 콘텐츠, 서브 이미지, 광고 입찰 |\n"
                    "| **종속 변수 (메인 KPI)** | 클릭 점유율 ÷ 노출 점유율 (= 시장 대비 CTR) 0.63배 → 0.8배 이상 |\n"
                    "| **안전장치** | CVR(단위 세션 비율)이 A보다 0.5%p 넘게 떨어지면 B 실패 |")
    st.caption("두께와 원단 질감을 변수 두 개로 나누지 않는 이유: 가설이 말하는 원인은 '품질 차이가 안 보인다' 하나이고, "
               "모서리를 든 사진 한 장에 둘 다 담깁니다. Manage Your Experiments는 한 번에 두 안(A/B)만 비교하므로, "
               "둘을 따로 보려면 이 테스트가 끝난 뒤 B 안에서 다시 나눠 테스트합니다.")