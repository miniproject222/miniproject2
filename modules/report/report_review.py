# 1. 분석 리포트 - 리뷰 분석 (내부 요인 '리뷰 20건'을 숫자로 풀어 봅니다)
# - 대상: 경쟁사 2곳 + 서리(가정: SleepCOOL 실적) + 냉감패드 10개사 중 Keepa 마지막 조회값이 있는 상품
# - 값: Keepa 마지막 조회값(리뷰 수, 평점, 판매 순위) + 상세 조회(리뷰 1년 변화, 여름 순위) · 리뷰 원문은 조회하지 않음
import math

from modules.report.report_competitor import REPORT_SEORI_PROXY, report_market10
from modules.report.report_keepa import report_keepa_detail

REPORT_REVIEW_RATING_GOALS = (4.0, 4.1)   # 서리 평점 목표: 경쟁사 2곳 수준 (Mara Vital 4.0, Traumnacht 4.1)


def report_review_need(reviews, rating, goal):
    """평점 goal에 닿으려면 별 5개 리뷰가 몇 건 더 필요한지 (단순 평균 기준, Amazon 표시 평점은 가중 평균이라 근사값)."""
    if rating >= goal:
        return 0
    return math.ceil(round((goal - rating) * reviews / (5 - goal), 6))   # 부동소수 오차로 4.0000001 → 5가 되지 않게


def report_spearman(xs, ys):
    """순위 상관계수 (같은 값 없다고 가정한 간단 계산)."""
    n = len(xs)
    if n < 3:
        return None
    rx = {v: i for i, v in enumerate(sorted(xs))}
    ry = {v: i for i, v in enumerate(sorted(ys))}
    d2 = sum((rx[x] - ry[y]) ** 2 for x, y in zip(xs, ys))
    return 1 - 6 * d2 / (n * (n * n - 1))


def report_review_analysis(rivals, snapshot_items, keepa_time):
    """서리 리뷰 수·평점을 냉감패드 상품과 비교하고, 목표까지 필요한 리뷰 수를 계산합니다."""
    rows = []
    for r in rivals:
        k = r.get("keepa") or {}
        if k.get("reviews") is None:
            continue
        rows.append({"brand": r["brand"] + (f" (가정: {r['proxy']} 실적)" if r.get("proxy") else ""), "asin": r.get("asin"),
                     "kind": r["kind"], "reviews": k["reviews"], "rating": k.get("rating"), "rank": k.get("rank")})
    seen = {r.get("asin") for r in rivals}
    market = report_market10() or {"companies": []}
    for c in market["companies"]:
        k = (snapshot_items or {}).get(c["asin"])
        if c["asin"] and c["asin"] not in seen and k and k.get("reviews") is not None:
            rows.append({"brand": c["brand"], "asin": c["asin"], "kind": "냉감패드 10개사", "reviews": k["reviews"],
                         "rating": k.get("rating"), "rank": k.get("rank")})
    detail = report_keepa_detail().get("items", {})
    for r in rows:   # 상세 조회가 있는 상품: 1년 리뷰 증가, 여름(6~8월) 순위 중앙값
        d = detail.get(r.get("asin") or "", {})
        r["reviews_1y"] = (r["reviews"] - d["reviews_1y_ago"]) if d.get("reviews_1y_ago") is not None else None
        r["summer_rank"] = d.get("rank_root_summer_median")
        r["sales_signal"] = (d.get("rank_drops") or {}).get("365")
        r["note"] = d.get("note", "")
    seori = next((r for r in rows if r["kind"] == "자사"), None)
    others = [r for r in rows if r["kind"] != "자사"]
    if not seori or not others:
        return None

    rivals_only = [r for r in others if r["kind"] != "냉감패드 10개사"]   # 냉감패드 실적 1·2위 경쟁사
    # 냉감패드 실적 1위 = 1년 판매 신호가 가장 많은 경쟁사 (없으면 현재 순위)
    leader = max(rivals_only or others, key=lambda r: (r.get("sales_signal") or 0, -(r["rank"] or 10**9)))
    counts = sorted(r["reviews"] for r in others)
    median = counts[len(counts) // 2] if len(counts) % 2 else (counts[len(counts) // 2 - 1] + counts[len(counts) // 2]) / 2
    ranked = [r for r in rows if r["rank"]]
    rho = report_spearman([r["reviews"] for r in ranked], [-r["rank"] for r in ranked])   # 순위는 작을수록 좋음 → 부호 반대
    needs = {f"{g:.1f}": report_review_need(seori["reviews"], seori["rating"], g) for g in REPORT_REVIEW_RATING_GOALS}
    many = max(others, key=lambda r: r["reviews"])

    findings = [
        f"서리 리뷰 {seori['reviews']}건 · 평점 {seori['rating']} → 냉감패드 실적 1위 {leader['brand']} {leader['reviews']}건 · 평점 {leader['rating']}"
        f" (리뷰 {max(leader['reviews'] - seori['reviews'], 0)}건 차이)",
        f"비교 상품 {len(others)}개의 리뷰 수 중앙값 {median:g}건 · 서리는 그 {seori['reviews'] / median * 100:.0f}%",
        f"리뷰가 가장 많은 {many['brand']}({many['reviews']}건)의 판매 순위는 {many['rank']:,}위"
        + (f" (리뷰 수와 판매 순위의 순위 상관 {rho:+.2f}, 상품 {len(ranked)}개라 참고용)" if rho is not None else ""),
        *[f"{r['brand']}: {r['note']}" for r in rows if r.get("note")],
        *[f"{r['brand']} 최근 1년 리뷰 {r['reviews_1y']:+d}건" + (f" · 여름(6~8월) 판매 순위 중앙값 {r['summer_rank']:,}위" if r["summer_rank"] else "")
          for r in rows if r.get("reviews_1y") is not None],
        f"평점 4.0까지 별 5개 리뷰 약 {needs['4.0']}건, 4.1까지 약 {needs['4.1']}건 추가 필요 (단순 평균 기준 근사)",
    ]
    return {
        "rows": rows,
        "seori": {"reviews": seori["reviews"], "rating": seori["rating"], "rank": seori["rank"]},
        "leader": {"brand": leader["brand"], "reviews": leader["reviews"], "rating": leader["rating"], "rank": leader["rank"]},
        "median_reviews": median,
        "review_gap_to_leader": max(leader["reviews"] - seori["reviews"], 0),
        "five_star_needed": needs,                      # {"4.0": 건수, "4.1": 건수}
        "rank_corr": round(rho, 2) if rho is not None else None,
        "findings": findings,
        # 가설 탭에서 그대로 쓰는 지표·목표
        "metric": "Amazon 리뷰 수",   # 가설 문장에 그대로 들어가는 지표 이름 (출처는 limits·data_rules에)
        "target": f"평점 {REPORT_REVIEW_RATING_GOALS[0]} 이상 + 리뷰 {leader['reviews']}건 이상 (냉감패드 실적 1위 수준)",
        "rule": "리뷰 대가 할인·사은품, '별 5개' 요청, 가짜·구매 리뷰는 금지 (독일 DB REV-106, UWG 부속서 23b·23c) → Amazon Vine·구매 후 정식 리뷰 요청만",
        "limits": f"Keepa {keepa_time} 값 · 리뷰 원문은 미조회 · 평점 계산은 단순 평균 근사",
    }


def report_cooling_sales():
    """냉감패드 실적만 보기: Keepa 상세 조회 상품의 하위 카테고리 순위, 여름 순위, 1년 판매 신호, 월 구매 배지."""
    detail = report_keepa_detail()
    items = list(detail.get("items", {}).values())
    if not items:
        return None
    rows = []
    for i in items:
        badges = [m["badge"] for m in i["monthly_sold"] if m["from"] >= "2026-01-01"]
        brand = i["brand"]
        if brand.lower() == REPORT_SEORI_PROXY.lower():   # 서리 실적으로 쓰는 브랜드는 서리로 표시 (다른 표와 같게)
            brand = f"SEORI (서리) · {REPORT_SEORI_PROXY} 실적"
        rows.append({**i, "brand": brand, "badge": f"{max(badges)}+ (2026)" if badges else "-"})
    rows.sort(key=lambda r: -((r.get("rank_drops") or {}).get("365") or 0))
    pure = [r for r in rows if r.get("type") == "냉감 전용"]
    findings = [
        "판매 순위는 한 상품 페이지(사이즈·색상 변형 포함) 단위라, 비냉감 변형이 섞이면 냉감패드만의 실적이 아님",
        *[f"{r['brand']}: {r['note']}" for r in rows if r.get("note")],
        "냉감 전용 상품 순위 (1년 판매 신호): "
        + " > ".join(f"{r['brand']} {r['rank_drops']['365']}회" for r in pure if r["rank_drops"].get("365") is not None),
        "순위 제외: " + ", ".join(f"{r['brand']} ({r['type']})" for r in rows if r.get("type") != "냉감 전용"),
        "여름(2026년 6~8월) 순위 중앙값 (보조): " + ", ".join(f"{r['brand']} {r['rank_root_summer_median']:,}위"
                                                     for r in pure if r["rank_root_summer_median"]),
        "하위 카테고리가 서로 달라(매트리스 패드 / 매트리스 보호 / 토퍼) 하위 순위는 같은 카테고리끼리만 비교 가능",
    ]
    return {"rows": rows, "findings": findings, "note": detail.get("note", "") + f" · 조회 {detail.get('fetched_at', '')}"}
