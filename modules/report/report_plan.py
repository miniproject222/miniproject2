# 1. 문제 분석 - 가설 재료 (② 가설 탭이 문장을 만들 때 쓰는 값)
# 문제마다 행동·이유·지표(지금 값 → 목표 값)·테스트 방법·기간을 "그 문제의 데이터"로 만듭니다.
# 고정 개선율(8%·10% 등)이나 키워드로 고르는 고정 문구는 쓰지 않습니다.
# 데이터로 목표를 정할 수 없는 문제는 plan=None + plan_none(이유)으로 보내고, ② 탭은 후보에서 뺍니다.
import math
import re

from modules.report.report_competitor import (
    REPORT_REVIEW_HIGH, REPORT_REVIEW_MID, REPORT_UWG_FORBIDDEN, REPORT_UWG_REQUIRED, report_seori_assumption,
)

REPORT_PLAN_ALPHA_Z = 1.96   # A/B 판정 기준: 유의수준 5% (양측) - 통계 표준값
REPORT_PLAN_POWER_Z = 0.84   # 검정력 80% - 통계 표준값
REPORT_PLAN_MYE_MIN_WEEKS = 4   # Amazon Manage Your Experiments 최소 실행 기간 (아마존 규칙, 문제 시나리오.md "4~10주")

# 데이터로 목표를 정할 수 없어 가설 재료를 만들지 않는 문제 분류와 이유
REPORT_PLAN_NONE = {
    "판매": "판매량은 결과 지표라, 원인 문제(리뷰·검색 클릭)의 가설로 개선",
    "가격": "서리 가격은 가정값이라 가격 실험의 근거 데이터가 없음",
    "채널": "채널을 늘리는 데 필요한 비용·수요 데이터가 없음",
    "경쟁력": "경쟁우위 점수는 서리 목표 점수라 측정 가능한 지금 값이 없음",
    "제품·물류": "물류 거점 비용·배송 기간 데이터가 없음",
    "경쟁사": "경쟁사 행동은 우리가 바꿀 수 없어 우리 지표의 지금 값이 없음",
    "날씨": "날씨는 바꿀 수 없음 (광고 시점은 ④ 광고 타이밍 탭)",
    "시장": "시장 상황은 바꿀 수 없어 우리 지표의 지금 값이 없음",
    "플랫폼": "결제 수단 추가 효과를 잴 우리 결제 데이터(GA4)가 없음",
    "제외 검토": "검색 의도가 달라 가설 없이 광고 제외 키워드로 처리",
}


def report_plan_sample_size(p1, p2):
    """두 비율 차이를 잡아내는 데 필요한 안별 표본 수 (유의수준 5%, 검정력 80%)."""
    if not (0 < p1 < 1 and 0 < p2 < 1) or p1 == p2:
        return None
    pbar = (p1 + p2) / 2
    n = ((REPORT_PLAN_ALPHA_Z * math.sqrt(2 * pbar * (1 - pbar))
          + REPORT_PLAN_POWER_Z * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) / (p2 - p1)) ** 2
    return math.ceil(n)


def report_plan_sqp_goal(sqp):
    """검색어 클릭 목표 배수 = 우리 상품이 문제 없는 검색어(같은 상품·같은 사진)에서 내는 배수의 중앙값."""
    normal = sorted(x["total"]["ratio"] for x in sqp["queries"] if not x["type"])
    if not normal:
        return None, ""
    mid = len(normal) // 2
    goal = normal[mid] if len(normal) % 2 else (normal[mid - 1] + normal[mid]) / 2
    return round(goal, 2), f"문제 없는 검색어 {len(normal)}개에서 우리 상품의 배수 중앙값"


def report_plan_sqp_main(x, sqp, store):
    """'소재 개선' (보이는데 안 눌림): 메인 이미지 A/B."""
    t, listing = x["total"], sqp["listing"]
    goal, goal_basis = report_plan_sqp_goal(sqp)
    if not goal or goal <= t["ratio"]:
        return None
    p1 = t["our_clk"] / t["our_imp"] if t["our_imp"] else 0
    p2 = p1 * goal / t["ratio"]
    n = report_plan_sample_size(p1, p2)
    weekly = t["our_imp"] / len(x["weeks"]) if x["weeks"] else 0
    weeks = math.ceil(2 * n / weekly) if n and weekly else None
    return {
        "action": f"메인 이미지 B안(지금 '{listing['main_image']}'의 문제인 '{listing['main_image_issue']}'을 고친 사진)",
        "because": (f"클릭 뒤 장바구니 비율은 우리 {store['cart_rate_ours']}%·시장 {store['cart_rate_market']}%로 비슷해 "
                    f"문제는 첫인상이고 클릭된 상품 중앙 가격보다 €{store['price_gap']:.0f} 비싼 이유가 사진에서 안 보이기"),
        "kpi": "클릭 점유율 ÷ 노출 점유율", "now": round(t["ratio"], 2), "goal": goal, "unit": "배", "better": "up",
        "goal_basis": goal_basis,
        "visual": True,
        "material": "메인 이미지 A안(지금 사진)·B안 각 1장",
        "fixed": f"흰 배경 실제 사진, 제목, 가격 €{listing['price']:.2f}, 쿠폰 {'있음' if listing.get('coupon') else '없음'}",
        "test": "Amazon Manage Your Experiments로 메인 이미지 A/B 50:50 분할 노출",
        "period": (f"안별 {n:,}노출 (클릭률 {p1 * 100:.2f}% → {p2 * 100:.2f}% 차이를 유의수준 5%·검정력 80%로 확인) · "
                   f"지금 주 {weekly:,.0f}노출 기준 약 {weeks}주 → Amazon 실험 도구 최소 기간에 맞춰 "
                   f"{max(weeks, REPORT_PLAN_MYE_MIN_WEEKS)}주" if n and weeks else "표본 계산 불가 (노출 데이터 없음)"),
    }


def report_plan_sqp_exposure(x, heat_temp):
    """'노출 확대' (잘 눌리는데 덜 보임): 더운 날 입찰 상향."""
    t, e = x["total"], x["extra"]
    return {
        "action": f"최고기온 {heat_temp:.0f}°C 이상인 날 '{x['query']}' 입찰 상향",
        "because": (f"'{x['query']}'는 배수 {t['ratio']:.2f}배로 잘 눌리지만 노출 점유율이 {t['imp_share'] * 100:.1f}%라 "
                    f"{e['month']}에만 약 {e['clicks']:,.0f}회 클릭을 놓치기"),
        "kpi": "노출 점유율", "now": round(t["imp_share"] * 100, 1), "goal": round(e["goal"] * 100, 1), "unit": "%",
        "better": "up", "goal_basis": "같은 검색어에서 상위 노출 상품들의 점유율 기준 (검색어 분석)",
        "visual": False,
        "material": "추가 소재 없음 (광고 입찰 설정)",
        "fixed": "메인 이미지·제목·가격 그대로",
        "test": f"최고기온 {heat_temp:.0f}°C 이상인 날 입찰 상향 vs 같은 기온의 평소 입찰일 노출 점유율 비교",
        "period": f"{e['month']} 더운 날 기준 (DWD 최고기온)",
    }


def report_plan_review(ra, price):
    """리뷰 부족: Amazon이 허용하는 방법(Vine·정식 리뷰 요청)으로 리뷰 확보."""
    own, leader = ra["seori"]["reviews"] or 0, ra["leader"]
    if not leader["reviews"] or own >= leader["reviews"]:
        return None
    ratio = own / leader["reviews"]
    step = REPORT_REVIEW_HIGH if ratio < REPORT_REVIEW_HIGH else REPORT_REVIEW_MID if ratio < REPORT_REVIEW_MID else 1.0
    goal = math.ceil(leader["reviews"] * step)
    allowed = ra["rule"].split("→")[-1].strip().rstrip("만").strip()   # 리뷰 규칙의 허용 방법 (예: Amazon Vine·구매 후 정식 리뷰 요청)
    seori_row = next((r for r in ra["rows"] if r["kind"] == "자사"), {})
    per_year = seori_row.get("reviews_1y")
    months = math.ceil((goal - own) / per_year * 12) if per_year and per_year > 0 else None
    return {
        "action": f"{allowed} (리뷰 대가 제공 없이)",
        "because": (f"서리 리뷰가 1위 {leader['brand']} {leader['reviews']:,}건의 {ratio * 100:.0f}%({own}건)라 "
                    "구매 전 리뷰를 확인하는 독일 쇼핑객에게 신뢰가 낮기"),
        "kpi": "Amazon 리뷰 수", "now": own, "goal": goal, "unit": "건", "better": "up",
        "goal_basis": f"리뷰 위험도가 한 단계 내려가는 기준 (1위 대비 {step * 100:.0f}%)",
        "visual": False,
        "material": "Vine 등록 수량, 구매 고객 정식 리뷰 요청 (추가 소재 없음)",
        "fixed": f"가격 €{price:.2f}·메인 이미지·쿠폰 그대로" if price else "가격·메인 이미지·쿠폰 그대로",
        "test": "Vine 등록 전 30일과 등록 후 30일의 리뷰 증가 수 비교 (같은 기간 경쟁사 증가와 함께)",
        "period": (f"지금 속도(1년 +{per_year}건)로는 약 {months}개월 걸림 → Vine 등록 후 30일 증가량으로 판단"
                   if months else "Vine 등록 후 30일 증가량으로 판단"),
    }


def report_plan_uwg(assume):
    """UWG 광고 표기: 비어 있는 필수 표기를 채움 (지금 표기 수 → 전체)."""
    claims = (assume.get("ad_claims") or {}).get("claims") or []
    q = next((c for c in claims if "Q-max" in c.get("topic", "")), None)
    if not q:
        return None
    text = " ".join(c.get("de", "") for c in claims)
    bad = [w for w in REPORT_UWG_FORBIDDEN if w.lower() in text.lower()]
    missing = [name for name, pat in REPORT_UWG_REQUIRED if not re.search(pat, q["de"])]
    if not bad and not missing:
        return None
    total = len(REPORT_UWG_REQUIRED)
    fix = ([f"{'·'.join(missing)} 표기"] if missing else []) + ([f"금지 표현({', '.join(bad)}) 삭제"] if bad else [])
    return {
        "action": "Q-max 광고 문구에 " + "와 ".join(fix),
        "because": (f"독일에서는 Q-max 숫자 옆에 필수 표기 {total}개가 없거나 금지 표현을 쓰면 오인 광고(Abmahnung) 대상인데 "
                    f"지금 {'·'.join(missing) or '표기'}{'가 비어 있고' if missing else '는 갖췄지만'}"
                    + (f" 금지 표현이 있기" if bad else " 입증할 수 없기")),
        "kpi": "Q-max 광고 문구 필수 표기", "now": total - len(missing), "goal": total, "unit": "개", "better": "up",
        "goal_basis": "독일 DB LNG-005 필수 표기 항목 수",
        "visual": False,
        "material": "시험성적서 (시험기관·성적서 번호)",
        "fixed": "Q-max 숫자 0.207 (완제품, 온도차 10℃) 그대로",
        "test": f"광고·상세페이지 문구를 필수 표기 {total}개 점검표로 게시 전 확인",
        "period": "게시 전 1회 점검 (광고 문구가 바뀔 때마다)",
    }


def report_plan_test(tests, problem):
    """완제품 시험 미완료: 남은 시험을 끝냄 (완료 수 → 전체)."""
    done = sum(t["done"] for t in tests)
    if not tests or done >= len(tests):
        return None
    pending = [t["item"] for t in tests if not t["done"]]
    name = problem["title"].split(" 미측정")[0]
    return {
        "action": f"{name} 측정 시험 (시험기관 의뢰)",
        "because": f"{name} 측정값이 없어 냉감이 오래가는지 보여 줄 근거가 부족하기 ({problem['detail'].split(' →')[0].split(' (경쟁사')[0]})",
        "kpi": "완제품 시험 완료 항목", "now": done, "goal": len(tests), "unit": "개", "better": "up",
        "goal_basis": "경쟁사 DB 'SEORI 시험·표시' 시험 항목 수",
        "visual": False,
        "material": "완제품 시료, 시험기관 의뢰서",
        "fixed": "완제품 사양(원단·두께) 그대로",
        "test": "시험기관 결과서로 확인 후 가정 파일 결과 입력",
        "period": f"남은 시험 {len(pending)}개" + (f": {', '.join(pending[:3])}" if pending else ""),
    }


def report_attach_plans(data):
    """problems·key_problems에 가설 재료(plan)를 붙입니다. 같은 제목이면 같은 plan."""
    assume = report_seori_assumption() or {}
    price = data["seori_profile"].get("amazon_price")
    plans = {}
    sqp, store = data.get("sqp"), data.get("sqp_store")
    if sqp and store:
        from modules.report.report_sqp import REPORT_SQP_HEAT_TEMP
        for x in sqp["problems"]:
            if x["type"] == "소재 개선":
                plans[("sqp", x["query"])] = report_plan_sqp_main(x, sqp, store)
            elif x["type"] == "노출 확대":
                plans[("sqp", x["query"])] = report_plan_sqp_exposure(x, REPORT_SQP_HEAT_TEMP)
    by_title = {}
    for p in data["problems"]:
        group = p.get("sqp_type") or p.get("group")
        if p.get("sqp_type"):
            plan = plans.get(("sqp", p.get("query")))
        elif group == "신뢰" and data.get("review_analysis"):
            plan = report_plan_review(data["review_analysis"], price)
        elif group == "규제" and "UWG" in p["title"]:
            plan = report_plan_uwg(assume)
        elif group == "시험":
            plan = report_plan_test(data["seori_profile"].get("tests") or [], p)
        else:
            plan = None
        p["plan"] = plan
        p["plan_none"] = "" if plan else REPORT_PLAN_NONE.get(group, "데이터로 지금 값·목표 값을 정할 수 없음")
        by_title[p["title"]] = (p["plan"], p["plan_none"])
    for k in data["key_problems"]:   # 핵심 문제 Top 3도 같은 제목의 plan
        k["plan"], k["plan_none"] = by_title.get(k["title"], (None, "데이터로 지금 값·목표 값을 정할 수 없음"))
    if store:   # ③ 탭이 읽는 검색어 목표 배수도 같은 데이터 기준
        main = next((p["plan"] for p in data["problems"] if p.get("sqp_type") == "소재 개선" and p.get("plan")), None)
        store["kpi_goal"] = main["goal"] if main else None
        store["kpi_goal_basis"] = main["goal_basis"] if main else ""
    return data
