# 1. 분석 리포트 - 데이터 불러오기
# - 검색어 클릭 분석: 검색어 성과·광고·우리 상품은 가상(더미), 경쟁 제품은 Keepa 실제, 기온은 DWD 실제 (report_sqp.py)
# - 경쟁사·내부/외부 요인: 공통 경쟁사 DB·독일 DB(루트 data/) + Keepa 마지막 조회값 + Open-Meteo 현재 기온
# - 매출 KPI·구매 퍼널·유입 채널(UTM): GA4가 연결되면 표시, 연결 전에는 빈 상태
# - A/B 테스트: data/report_ab_tests.json에 실제 결과를 넣으면 표시
import json
import math
from datetime import date
from pathlib import Path

from modules.report.report_competitor import (
    report_competitor_checklist, report_competitor_criteria, report_competitor_load, report_competitor_merge,
    report_competitor_slim, report_competitor_tests, report_external_factors, report_internal_factors,
    report_hypothesis_problems, report_key_problems, report_marketing_rules, report_position_kpis, report_team_handoff,
)
from modules.report.report_ga4 import report_ga4_fetch, report_ga4_ready
from modules.report.report_keepa import report_keepa_products, report_keepa_snapshot, report_keepa_usage
from modules.report.report_sqp import report_sqp_analyze, report_sqp_handoff

REPORT_AB_FILE = Path(__file__).resolve().parent / "data" / "report_ab_tests.json"
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


def report_load_data():
    """화면에 필요한 실제 데이터를 한 번에 돌려줍니다."""
    snapshot = report_keepa_snapshot()
    usage = report_keepa_usage()
    keepa_time = snapshot["fetched_at"] if snapshot else ""
    rivals = report_competitor_merge(report_competitor_load(), report_keepa_products(),
                                     snapshot["items"] if snapshot else None)
    criteria = report_competitor_criteria()
    checklist = report_competitor_checklist()
    tests = report_competitor_tests()
    last = f"Keepa 마지막 조회: {keepa_time}" if snapshot else "Keepa 조회값 없음"

    ab_tests = json.loads(REPORT_AB_FILE.read_text(encoding="utf-8"))["tests"] if REPORT_AB_FILE.exists() else []
    data = {
        "period": date.today().strftime("%Y-%m"),
        "keepa_status": f"{last} · 토큰 사용 {usage['used']}/{usage['budget']}",
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
    data["position_key_problems"] = report_key_problems(data["internal"], data["external"])
    data["key_problems"] = data["position_key_problems"]
    data["problems"] = report_hypothesis_problems(data["key_problems"], data["internal"], data["external"], rivals)

    # 검색어 클릭 분석 (문제 시나리오.md): 있으면 문제 도출·다른 탭 문제의 맨 앞을 이 결과로 바꿉니다
    data["sqp"] = report_sqp_analyze(rivals, snapshot["items"] if snapshot else None)
    data["sqp_store"] = None
    if data["sqp"]:
        sqp_problems, sqp_key_problems, data["sqp_store"] = report_sqp_handoff(data["sqp"], rivals)
        data["key_problems"] = sqp_key_problems
        data["problems"] = sqp_problems + data["problems"]
    if report_ga4_ready():
        try:
            ga4 = report_ga4_fetch()
            if ga4["funnel"][0]["now"]:        # 세션이 0이면 아직 수집 전
                data["ga4"] = ga4
        except Exception as err:               # 라이브러리 미설치, 권한 오류 등 → 빈 상태로 계속
            data["source_error"] = str(err)
    return data
