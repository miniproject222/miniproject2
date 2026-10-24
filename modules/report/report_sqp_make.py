# 1. 분석 리포트 - 검색어 성과(SQP) 더미 데이터 만들기 (화면에서는 실행하지 않음, 필요할 때 직접 한 번 실행)
# 실행: 프로젝트 맨 위 폴더에서  python -m modules.report.report_sqp_make
#
# 검색어 성과 리포트는 판매자 본인 계정에서만 나오므로 더미로 만들되,
# 모양·크기·사건은 실제 데이터에서 가져오고 우리 계정 안의 숫자만 더미로 채웁니다. (문제 시나리오.md)
# - 주별 검색량 모양: Google Trends CSV가 data/에 있으면 그 지수, 없으면 DWD 실제 최고기온으로 만든 지수
# - 경쟁사 할인·품절 주: Keepa 스냅샷의 events (없으면 data/report_sqp_events_202608.json 가정 값)
# - 우리 노출·클릭 점유율, 장바구니, 구매, 광고 성과: 아래 계수로 만든 가상 값 (같은 실행이면 항상 같은 값)
import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

REPORT_MAKE_DIR = Path(__file__).resolve().parent / "data"
REPORT_MAKE_SEED = 202608
REPORT_MAKE_START = date(2026, 6, 1)    # 월요일
REPORT_MAKE_WEEKS = 13                  # 6~8월
REPORT_MAKE_IMP_PER_SEARCH = 24         # 검색 1회당 노출되는 상품 수 (가정)

# 검색어별 가정: 주 평균 시장 클릭, 시장 CTR, 우리 노출 점유율, 배수(클릭 점유율 ÷ 노출 점유율), 클릭된 상품 중앙 가격, CPC
# 문제 시나리오.md '1단계: 더미 데이터로 찾는 문제'의 범위에 맞춘 값입니다.
REPORT_MAKE_KEYWORDS = [
    {"query": "kühlende matratzenauflage", "clicks": 3300, "ctr": 0.030, "imp_share": 0.090, "ratio": 0.645, "median_price": 59.99, "cpc": 0.95, "events": True},
    {"query": "kühlmatte bett", "clicks": 2000, "ctr": 0.025, "imp_share": 0.068, "ratio": 1.26, "median_price": 54.99, "cpc": 0.80},
    {"query": "matratzenauflage kühlend", "clicks": 1500, "ctr": 0.032, "imp_share": 0.075, "ratio": 0.95, "median_price": 62.99, "cpc": 0.90},
    {"query": "kühltopper", "clicks": 1200, "ctr": 0.028, "imp_share": 0.0295, "ratio": 0.695, "median_price": 79.99, "cpc": 1.10},
    {"query": "kühlauflage matratze", "clicks": 1000, "ctr": 0.029, "imp_share": 0.080, "ratio": 1.02, "median_price": 59.99, "cpc": 0.85},
    {"query": "kühlmatte sommer", "clicks": 900, "ctr": 0.024, "imp_share": 0.040, "ratio": 1.05, "median_price": 39.99, "cpc": 0.60},
    {"query": "cooling matratzenauflage", "clicks": 700, "ctr": 0.031, "imp_share": 0.060, "ratio": 0.92, "median_price": 49.99, "cpc": 0.75},
    {"query": "matratzenauflage 90x200 kühl", "clicks": 600, "ctr": 0.033, "imp_share": 0.100, "ratio": 0.98, "median_price": 64.99, "cpc": 0.90},
]
REPORT_MAKE_EVENT_FACTOR = {"할인": 0.85, "품절": 1.15}   # 경쟁사 할인 주면 우리 클릭 점유율 ↓, 품절 주면 ↑ (시나리오 가정)
REPORT_MAKE_CART = {"market": 0.171, "ours": 0.162}       # 클릭 → 장바구니 (7월 기준 시나리오 값)
REPORT_MAKE_BUY = {"market": 0.090, "ours": 0.086}        # 클릭 → 구매
REPORT_MAKE_ADS_SHARE = 0.55                              # 우리 노출 중 광고 노출 비중 (가정)


def report_make_noise(rng, pct):
    return 1 + rng.uniform(-pct, pct)


def report_make_weeks():
    return [REPORT_MAKE_START + timedelta(weeks=i) for i in range(REPORT_MAKE_WEEKS)]


def report_make_temp_index(weeks):
    """DWD 일 최고기온(5개 도시 평균)의 주 평균으로 검색량 지수를 만듭니다. 더울수록 검색이 늘어난다는 가정."""
    rows = list(csv.DictReader((REPORT_MAKE_DIR / "report_temp_dwd_202608.csv").open(encoding="utf-8")))
    out = []
    for w in weeks:
        temps = [float(r["tmax_avg"]) for r in rows if w <= date.fromisoformat(r["date"]) < w + timedelta(days=7)]
        out.append(max(sum(temps) / len(temps) - 14, 2) ** 1.5)
    return out


def report_make_trends_index(weeks, query):
    """data/report_trends_google_*.csv (Google Trends 내보내기)에 이 검색어 열이 있으면 주별 지수를 돌려줍니다."""
    for path in sorted(REPORT_MAKE_DIR.glob("report_trends_google_*.csv")):
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        start = next((i for i, line in enumerate(lines) if line.split(",")[0] in ("Week", "Woche", "Time", "Zeit")), None)
        if start is None:
            continue
        table = list(csv.reader(lines[start:]))
        col = next((i for i, h in enumerate(table[0]) if h.lower().startswith(query)), None)
        if col is None:
            continue
        values = {date.fromisoformat(r[0]): float(r[col].replace("<1", "0.5")) for r in table[1:] if r and r[col]}
        if all(w in values for w in weeks):
            return [values[w] for w in weeks], path.name
    return None, ""


def report_make_events():
    """경쟁사 할인·품절 주. Keepa 스냅샷에 events가 있으면 실제 값, 없으면 가정 파일."""
    snap_path = REPORT_MAKE_DIR / "report_keepa_snapshot.json"
    snap = json.loads(snap_path.read_text(encoding="utf-8")) if snap_path.exists() else {}
    keepa = [e for item in (snap.get("items") or {}).values() for e in item.get("events") or []]
    if keepa:
        return keepa, "Keepa 실제"
    data = json.loads((REPORT_MAKE_DIR / "report_sqp_events_202608.json").read_text(encoding="utf-8"))
    return data["events"], data["source"]


def report_make_sqp(rng, weeks, events):
    listing = json.loads((REPORT_MAKE_DIR / "report_listing_dummy_202608.json").read_text(encoding="utf-8"))
    temp_index = report_make_temp_index(weeks)
    rows, shape_source = [], {}
    for kw in REPORT_MAKE_KEYWORDS:
        index, src = report_make_trends_index(weeks, kw["query"])
        shape_source[kw["query"]] = f"Google Trends ({src})" if index else "DWD 기온 기반 가정"
        index = index or temp_index
        mean = sum(index) / len(index)
        for w, idx in zip(weeks, index):
            factor = 1.0
            if kw.get("events"):
                for e in events:
                    if e["week"] == w.isoformat():
                        factor *= REPORT_MAKE_EVENT_FACTOR.get(e["kind"], 1.0)
            clicks = round(kw["clicks"] * idx / mean * report_make_noise(rng, 0.04))
            imps = round(clicks / (kw["ctr"] * report_make_noise(rng, 0.03)))
            imp_share = kw["imp_share"] * report_make_noise(rng, 0.025)
            click_share = imp_share * kw["ratio"] * factor * report_make_noise(rng, 0.03)
            our_imps, our_clicks = round(imps * imp_share), round(clicks * click_share)
            carts = round(clicks * REPORT_MAKE_CART["market"] * report_make_noise(rng, 0.03))
            buys = round(clicks * REPORT_MAKE_BUY["market"] * report_make_noise(rng, 0.03))
            cart_rate = REPORT_MAKE_CART["ours"] if kw.get("events") else REPORT_MAKE_CART["market"]
            buy_rate = REPORT_MAKE_BUY["ours"] if kw.get("events") else REPORT_MAKE_BUY["market"]
            our_carts = round(our_clicks * cart_rate * report_make_noise(rng, 0.04))
            our_buys = round(our_clicks * buy_rate * report_make_noise(rng, 0.04))
            searches = round(imps / REPORT_MAKE_IMP_PER_SEARCH)
            rows.append({
                "startDate": w.isoformat(), "endDate": (w + timedelta(days=6)).isoformat(), "asin": listing["asin"],
                "searchQueryData": {"searchQuery": kw["query"], "searchQueryVolume": searches},
                "impressionData": {"totalQueryImpressionCount": imps, "asinImpressionCount": our_imps,
                                   "asinImpressionShare": round(our_imps / imps * 100, 2)},
                "clickData": {"totalClickCount": clicks, "clickRate": round(clicks / searches * 100, 2),
                              "asinClickCount": our_clicks, "asinClickShare": round(our_clicks / clicks * 100, 2),
                              "totalMedianClickPrice": {"amount": kw["median_price"], "currencyCode": "EUR"},
                              "asinMedianClickPrice": {"amount": listing["price"], "currencyCode": "EUR"}},
                "cartAddData": {"totalCartAddCount": carts, "asinCartAddCount": our_carts,
                                "asinCartAddShare": round(our_carts / carts * 100, 2)},
                "purchaseData": {"totalPurchaseCount": buys, "asinPurchaseCount": our_buys,
                                 "asinPurchaseShare": round(our_buys / buys * 100, 2)},
            })
    return rows, shape_source


def report_make_ads(rng, sqp_rows):
    """스폰서드 프로덕트 키워드 리포트 형식 (날짜 × 키워드). 우리 주별 노출·클릭을 날짜로 나눈 가상 값."""
    cpc = {k["query"]: k["cpc"] for k in REPORT_MAKE_KEYWORDS}
    price = json.loads((REPORT_MAKE_DIR / "report_listing_dummy_202608.json").read_text(encoding="utf-8"))["price"]
    out = []
    for r in sqp_rows:
        q = r["searchQueryData"]["searchQuery"]
        start = date.fromisoformat(r["startDate"])
        top_share = 0.21 if q == REPORT_MAKE_KEYWORDS[0]["query"] else 0.16
        for d in range(7):
            imps = round(r["impressionData"]["asinImpressionCount"] * REPORT_MAKE_ADS_SHARE / 7 * report_make_noise(rng, 0.15))
            clicks = round(r["clickData"]["asinClickCount"] * REPORT_MAKE_ADS_SHARE / 7 * report_make_noise(rng, 0.15))
            orders = round(clicks * 0.085 * report_make_noise(rng, 0.3))
            out.append({
                "date": (start + timedelta(days=d)).isoformat(), "campaign_name": "SP_Kuehlauflage_Exact",
                "targeting": q, "match_type": "EXACT", "impressions": imps, "clicks": clicks,
                "spend": round(clicks * cpc[q] * report_make_noise(rng, 0.08), 2),
                "orders_7d": orders, "sales_7d": round(orders * price, 2),
                "top_of_search_impression_share": round(top_share * report_make_noise(rng, 0.08), 3),
            })
    return out


def report_make_all():
    rng = random.Random(REPORT_MAKE_SEED)
    weeks = report_make_weeks()
    events, event_source = report_make_events()
    sqp_rows, shape_source = report_make_sqp(rng, weeks, events)
    sqp = {
        "note": "가상 데이터. SP-API 검색어 성과 리포트(GET_BRAND_ANALYTICS_SEARCH_QUERY_PERFORMANCE_REPORT) 필드 이름 그대로, 주 단위. "
                "점유율(Share)과 clickRate는 % 단위입니다 (실제 리포트를 연결할 때 단위를 다시 확인).",
        "source": "가상",
        "generated_by": "python -m modules.report.report_sqp_make",
        "shape_source": shape_source,
        "event_source": event_source,
        "assumptions": {"event_factor": REPORT_MAKE_EVENT_FACTOR, "cart_rate": REPORT_MAKE_CART, "buy_rate": REPORT_MAKE_BUY,
                        "keywords": REPORT_MAKE_KEYWORDS},
        "dataByAsin": sqp_rows,
    }
    (REPORT_MAKE_DIR / "report_sqp_weekly_dummy_202608.json").write_text(
        json.dumps(sqp, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    ads = report_make_ads(rng, sqp_rows)
    with (REPORT_MAKE_DIR / "report_ads_keywords_dummy_202608.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(ads[0]))
        writer.writeheader()
        writer.writerows(ads)
    print(f"SQP {len(sqp_rows)}행, 광고 {len(ads)}행 저장 (이벤트: {event_source})")


if __name__ == "__main__":
    report_make_all()
