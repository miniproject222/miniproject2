# 1. 분석 리포트 - 데이터 불러오기
# - 검색어 클릭 분석: 검색어 성과·광고·우리 상품은 가상(더미), 경쟁 제품은 Keepa 실제, 기온은 DWD 실제 (report_sqp.py)
# - 경쟁사·내부/외부 요인: 공통 경쟁사 DB·독일 DB(루트 data/) + Keepa 마지막 조회값 + Open-Meteo 현재 기온
# - 매출 KPI·구매 퍼널·유입 채널(UTM): GA4가 연결되면 표시, 연결 전에는 빈 상태
# - A/B 테스트: data/report_ab_tests.json에 실제 결과를 넣으면 표시
import json
import math
from datetime import date
from pathlib import Path

import streamlit as st

from modules.report.report_competitor import (
    REPORT_SEORI_PROXY, report_seori_assumption,
    report_competitor_checklist, report_competitor_criteria, report_competitor_load, report_competitor_merge,
    report_competitor_slim, report_competitor_tests, report_external_factors, report_internal_factors,
    report_four_problems, report_hypothesis_problems, report_marketing_rules, report_position_kpis,
    report_severity_key,
    report_team_handoff,
)
# [보류] ③ 탭 결과 아침 자동 분석 (아래 report_load_data의 [보류] 주석과 함께 풀기)
# from modules.report.report_ab import report_ab_daily
from modules.report.report_review import report_cooling_sales, report_review_analysis
from common.common_store import store_get
from modules.report.report_ga4 import report_ga4_fetch, report_ga4_ready
from modules.report.report_image import report_image_fixes, report_image_rank, report_stage3_check
from modules.report.report_plan import report_attach_plans
from modules.report.report_keepa import report_keepa_auto_daily, report_keepa_detail, report_keepa_products, report_keepa_snapshot, report_keepa_usage
from modules.report.report_sqp import report_sqp_analyze, report_sqp_handoff

REPORT_AB_FILE = Path(__file__).resolve().parent / "data" / "report_ab_tests.json"
REPORT_KEEPA_FRESH_DAYS = 7   # Keepa 마지막 조회가 이보다 오래되면 '새로 조회 권장'
REPORT_UTM_MIN_SHARE = 0.05   # 방문 비중이 이보다 작은 채널은 '전환율 최저' 판정에서 뺍니다 (표본이 작아서)


def report_utm_rows(utm):
    """유입 채널별 전환율, 방문 비중을 계산하고 전환율이 가장 낮은 채널을 돌려줍니다."""
    total = sum(r["sessions"] for r in utm) or 1
    rows = [{"channel": f"{r['source']} / {r['medium']}", "campaign": r["campaign"],
             "sessions": r["sessions"], "orders": r["orders"], "revenue": r["revenue"],
             "cvr": r["orders"] / r["sessions"] * 100 if r["sessions"] else 0.0,
             "share": r["sessions"] / total * 100}
            for r in utm]
    big = [r for r in rows if r["share"] >= REPORT_UTM_MIN_SHARE * 100]
    worst = min(big, key=lambda r: r["cvr"]) if big else None
    return rows, worst


def report_ab_result(ab):
    """A/B 테스트 결과: 안별 전환율, 차이(lift), 두 비율 z-검정 유의확률(p)."""
    a, b = ab["variants"]
    ra, rb = a["conversions"] / a["users"], b["conversions"] / b["users"]
    pooled = (a["conversions"] + b["conversions"]) / (a["users"] + b["users"])
    se = math.sqrt(pooled * (1 - pooled) * (1 / a["users"] + 1 / b["users"]))
    z = (rb - ra) / se if se else 0.0
    p = math.erfc(abs(z) / math.sqrt(2))     # 양측 검정
    return {"rate_a": ra * 100, "rate_b": rb * 100, "lift": (rb / ra - 1) * 100 if ra else 0.0,
            "z": z, "p": p, "significant": p < 0.05, "winner": b["name"] if rb > ra else a["name"]}


def report_add_keepa_detail(data, rivals):
    """Keepa 상세(같은 조회 응답)의 쿠폰·월 구매 배지 → 경쟁사 신호(④), 상세페이지 특징 문구 → 경쟁사 프로필(③),
    수수료 → 서리 Amazon 순수익 추정. 상세 조회가 없는 상품은 건너뜁니다."""
    detail = report_keepa_detail().get("items", {})
    by_brand = {r["brand"]: detail.get(r.get("asin") or "") for r in rivals}
    for sig in data["competitor_signals"]:
        d = by_brand.get(sig["brand"])
        if d:
            sig["coupon"] = d["coupons"]                       # 쿠폰 횟수·최대 할인율·마지막 쿠폰·지금 진행 여부
            sig["monthly_sold"] = d["monthly_sold"][-1] if d["monthly_sold"] else None
    for prof in data["competitor_profiles"]:
        d = by_brand.get(prof["brand"])
        if d:
            prof["listing_features"], prof["listing_images"] = d["features"], d["images"]
    fees = [d["fees"] for d in detail.values() if d and d["fees"]["fba_eur"]]
    seori = data["seori_profile"]
    price = seori.get("amazon_price")
    if fees and price:
        ref = sorted(f["referral_pct"] for f in fees)[len(fees) // 2]
        fba = sorted(f["fba_eur"] for f in fees)[len(fees) // 2]
        net = price / 1.19 - price * ref / 100 - fba     # 부가세 19% 제외 - 판매 수수료 - FBA 배송비 (원가·광고비 전)
        seori["amazon_fees"] = {"price": price, "vat_pct": 19, "referral_pct": ref, "fba_eur": fba, "net_before_cost": round(net, 2),
                                "basis": "Keepa 상세 조회 상품의 판매 수수료·FBA 배송비 중앙값 · 원가·광고비 전 추정"}


def report_data_rules(keepa_time):
    """지표별 비교 기준·출처·날짜·구분. 같은 지표는 항상 같은 기준으로 계산해 결과가 흔들리지 않게 합니다."""
    try:
        age = (date.today() - date.fromisoformat(str(keepa_time)[:10])).days
    except ValueError:
        age = None
    fresh = "-" if age is None else (f"{age}일 전" + (" → 새로 조회 권장" if age > REPORT_KEEPA_FRESH_DAYS else ""))
    k = str(keepa_time)[:10] or "-"
    return [
        {"지표": "판매 순위", "비교 기준": "냉감 전용 상품의 1년 판매 신호(Keepa 순위가 좋아진 횟수), 보조로 2026년 6~8월 순위 중앙값 · 양면(2-in-1)·비냉감 혼재 제외",
         "출처": "Keepa 상세", "기준일": k, "신선도": fresh, "구분": "실제 (냉감 전용 5개 상품)"},
        {"지표": "가격 변화", "비교 기준": "작년 같은 날 가격 대비 ±10% 이상만 인하·인상 (90일 평균은 계절이 섞여 보조로만)",
         "출처": "Keepa", "기준일": k, "신선도": fresh, "구분": "실제"},
        {"지표": "리뷰", "비교 기준": "현재 리뷰 수 + 최근 1년 증가", "출처": "Keepa", "기준일": k, "신선도": fresh, "구분": "실제"},
        {"지표": "자사몰 리뷰", "비교 기준": "서리 리뷰 수 = Amazon + 자사몰 합산 (경쟁사는 Amazon만이라 기준이 다름) · 냉감 리뷰 주제",
         "출처": "Trusted Shops (sleepcool.de)", "기준일": "2026-10-25", "신선도": "-", "구분": "실제 (서리 자사몰 = SleepCOOL 공식몰 가정)"},
        {"지표": "㎡당 가격", "비교 기준": "현재가 ÷ 면적, 냉감패드 10개사 중앙값과 비교", "출처": "Keepa·경쟁사 DB", "기준일": k,
         "신선도": fresh, "구분": "실제 (서리는 가정 실적)"},
        {"지표": "검색어 노출·클릭", "비교 기준": "2026년 6~8월 주별, 배수 0.7 미만 2주 연속이면 문제", "출처": "가상 SQP",
         "기준일": "2026-08-24", "신선도": "-", "구분": "가상"},
        {"지표": "기온", "비교 기준": "5개 도시 평균 최고기온 28℃ 이상 3일 = 폭염 주", "출처": "DWD", "기준일": "2026-08-31",
         "신선도": "-", "구분": "실제"},
        {"지표": "서리 Q-max·인증·시험", "비교 기준": "국내 기업 공개 자료 기반 가정", "출처": "가정 파일", "기준일": "2026-10-24",
         "신선도": "-", "구분": "가정"},
    ]


def report_load_data():
    """화면에 필요한 실제 데이터를 한 번에 돌려줍니다."""
    # 아침 자동 갱신 (구매 배지·판매 신호·가격·리뷰·재고): 켜져 있고 오늘 아직 안 했을 때만 Keepa 1회 조회, 그 뒤 아래 분석이 새 값으로 계산됨
    keepa_auto = report_keepa_auto_daily()
    snapshot = report_keepa_snapshot()
    usage = report_keepa_usage()
    keepa_time = snapshot["fetched_at"] if snapshot else ""
    loaded = report_competitor_load()                        # 판매 순위 상위 2개사 + 서리(가정 3위)
    rivals = report_competitor_merge(loaded, report_keepa_products([r["brand"] for r in loaded] + [REPORT_SEORI_PROXY]),
                                     snapshot["items"] if snapshot else None)
    criteria = report_competitor_criteria([r["brand"] for r in loaded if r["kind"] != "자사"])
    checklist = report_competitor_checklist()
    tests = report_competitor_tests()
    last = f"Keepa 마지막 조회: {keepa_time}" if snapshot else "Keepa 조회값 없음"

    ab_tests = json.loads(REPORT_AB_FILE.read_text(encoding="utf-8"))["tests"] if REPORT_AB_FILE.exists() else []
    data = {
        "period": date.today().strftime("%Y-%m"),
        "keepa_status": f"{last} · 토큰 사용 {usage['used']}/{usage['budget']}",
        "keepa_time": keepa_time,                                # Keepa 마지막 조회 시각 (현재 순위의 기준 달)
        "keepa_auto": keepa_auto,                                # 아침 자동 갱신 상태 문구
        "data_rules": report_data_rules(keepa_time),              # 지표별 비교 기준·출처·날짜·구분·신선도
        "seori_proxy": REPORT_SEORI_PROXY,                       # 서리 판매 실적에 쓰는 가정 브랜드
        "competitors_full": rivals,                               # 화면 경쟁사 비교표
        "competitors": report_competitor_slim(rivals),            # 홈·가설 탭용 간단 표
        "criteria": criteria,                                     # 경쟁우위 항목별 점수
        "position_kpis": report_position_kpis(rivals, checklist),
        "internal": report_internal_factors(rivals, criteria, checklist, tests, keepa_time),
        "external": report_external_factors(rivals, keepa_time),
        "marketing_rules": report_marketing_rules(),                # 광고·상세페이지 표현 규칙 (독일 DB)
        **report_team_handoff(rivals, keepa_time),                  # 서리·경쟁사 프로필, 경쟁사 신호
        "ab_tests": [{**t, "result": report_ab_result(t)} for t in ab_tests],
        "ga4": None,                                              # GA4 연결 시 {"funnel", "utm"}
        "source_error": "",
    }
    data["seori_profile"]["certs"] = checklist          # 서리 인증·규제 현황 (가정 반영)
    data["seori_profile"]["tests"] = tests              # 서리 완제품 시험 결과 (가정 반영)
    assume = report_seori_assumption() or {}
    data["seori_profile"]["data_check"] = assume.get("data_check", [])   # 국내 기업 데이터 사용 가능 여부
    data["seori_profile"]["body_temp"] = assume.get("body_temp", {})     # 체감(피부 표면) vs 실제 체온
    data["seori_profile"]["finished_qmax_ref"] = assume.get("finished_qmax_ref", {})   # 국내 다른 기업 완제품 Q-max 비교
    data["ad_claims"] = assume.get("ad_claims", {})   # 나중에 광고에 넣을 서리 문구 (③ 광고 소재)
    data["seori_profile"]["ad_check"] = assume.get("ad_check", {})   # Q-max 0.207 광고 사용 가능 여부 (가상 광고 O, 실제 광고 X)
    data["cooling_sales"] = report_cooling_sales()   # 냉감패드 실적만 (하위 카테고리·여름 순위)
    report_add_keepa_detail(data, rivals)
    data["review_analysis"] = report_review_analysis(rivals, snapshot["items"] if snapshot else None, keepa_time)
    # 흐름: ① 모든 문제 파악 (경쟁 포지션 내부·외부 + 검색어 분석) → ② 내부 상위 2 + 외부(위협) 상위 2 = 카드에 보이는 4개
    #       → ③ 4개를 다시 위험도 → 심각도 순으로 1~4순위 (결과 박스 = 1·2순위) → ④ 다른 탭 problems도 이 순서가 맨 앞
    position_internal = list(data["internal"])
    data["sqp"] = report_sqp_analyze(rivals, snapshot["items"] if snapshot else None)
    data["sqp_store"] = None
    sqp_problems, sqp_key_problems = [], []
    if data["sqp"]:
        sqp_problems, sqp_key_problems, data["sqp_store"] = report_sqp_handoff(data["sqp"], rivals)
        # 검색어 문제(소재 개선·노출 확대)도 내부 요인 (제외 검토는 가설 없이 광고 제외 키워드로 처리라 뺌)
        data["internal"] = sorted(data["internal"] + [
            {"title": k["title"], "level": k["level"], "group": k["group"], "detail": k["detail"] + " (가상 SQP)",
             "gap": k.get("gap"), "question": k["question"]} for k in sqp_key_problems if k["group"] != "제외 검토"],
            key=report_severity_key)
    data["key_problems"] = report_four_problems(data["internal"], data["external"])
    sqp_titles = {k["title"] for k in sqp_key_problems}
    base_problems = report_hypothesis_problems([k for k in data["key_problems"] if k["title"] not in sqp_titles],
                                               position_internal, data["external"], rivals)
    merged = sqp_problems + base_problems
    first = [p for k in data["key_problems"] for p in merged if p["title"] == k["title"]]
    data["problems"] = first + [p for p in merged if p not in first]
    ra = data["review_analysis"]
    if ra:   # 리뷰 문제에 분석 결과(지표·목표·근거)를 붙여 가설 탭에서 바로 쓰게 합니다
        for p in data["key_problems"] + data["problems"]:
            if p.get("group") == "신뢰":
                p["metric"], p["target_value"], p["analysis"] = ra["metric"], ra["target"], ra["findings"]
    report_attach_plans(data)   # ② 가설 재료: 문제마다 행동·이유·지금 값→목표 값·테스트 (데이터로, 고정값 없음)
    data["image_fixes"] = report_image_fixes(data)   # 이미지로 고칠 수 있는 문제 (② 가설·③ 광고 소재용)
    report_image_rank(data)   # 1·2순위 = ② 가설 가능 + ③ 이미지로 개선 가능한 문제 (3순위부터는 다른 문제여도 됨)
    report_stage3_check(data)   # 문제마다 ① → ② → ③ 연결 판정 (problems[*].stage3, ② 후보 순서·배지)
    saved = store_get("report")
    # [보류] 해결안 A/B: ③ 탭이 UTM·GA4·A/B 실행 결과를 store("media")에 저장하면, 매일 아침(한국 08:00 이후 첫 접속)
    # 한 번 읽어 분석하고 전날 분석과 비교해 보여 주는 기능. ③ 탭에서 저장 기능을 아직 만들지 않아 꺼 둠.
    # ③ 탭 준비 후: 아래 줄과 위의 import 주석을 풀고, data["ab_daily"] = None 줄을 지우면 됨 (저장 형식: report_handoff.md)
    # data["ab_daily"] = report_ab_daily(saved, report_utm_rows)
    data["ab_daily"] = None
    # 직접 올린 A/B 결과 파일 (바로 분석): 이번 접속에서 올린 값 > 저장된 값
    data["ab_upload"] = st.session_state.get("report-ab-upload") or ((saved or {}).get("ab_upload") if isinstance(saved, dict) else None)
    if report_ga4_ready():
        try:
            ga4 = report_ga4_fetch()
            if ga4["funnel"][0]["now"]:        # 세션이 0이면 아직 수집 전
                data["ga4"] = ga4
        except Exception as err:               # 라이브러리 미설치, 권한 오류 등 → 빈 상태로 계속
            data["source_error"] = str(err)
    return data
