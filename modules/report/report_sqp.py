# 1. 분석 리포트 - 검색어별 '보이는 만큼 눌리는지' 분석 (문제 시나리오.md 1단계)
# - 노출·클릭·장바구니·구매: 검색어 성과(SQP) 더미 (가상, report_sqp_make.py로 생성)
# - 우리 상품 정보, 광고 성과: 더미 (가상)
# - 경쟁 제품 가격·평점·리뷰: Keepa 스냅샷 (실제) / 할인·품절 주: Keepa events가 없으면 가정 파일
# - 기온: DWD 실제 일 최고기온 (Bright Sky API로 받아 저장)
# 화면 문구마다 출처(가상/실제/가정)를 함께 표시합니다.
import csv
import json
from datetime import date, timedelta
from pathlib import Path

from modules.report.report_competitor import report_knowledge

REPORT_SQP_DIR = Path(__file__).resolve().parent / "data"
REPORT_SQP_FILE = REPORT_SQP_DIR / "report_sqp_weekly_dummy_202608.json"
REPORT_SQP_ADS_FILE = REPORT_SQP_DIR / "report_ads_keywords_dummy_202608.csv"
REPORT_SQP_LISTING_FILE = REPORT_SQP_DIR / "report_listing_dummy_202608.json"
REPORT_SQP_EVENTS_FILE = REPORT_SQP_DIR / "report_sqp_events_202608.json"
REPORT_SQP_TEMP_FILE = REPORT_SQP_DIR / "report_temp_dwd_202608.csv"

# 감지 규칙 (시작값, 데이터를 보며 조정)
REPORT_SQP_RATIO_ALERT = 0.7      # 클릭 점유율 ÷ 노출 점유율이 이보다 낮으면
REPORT_SQP_ALERT_WEEKS = 2        # 이만큼 연속되면 문제로 표시
REPORT_SQP_RATIO_STRONG = 1.2     # 이 이상이면 '눌리는 힘은 있음'
REPORT_SQP_INTENT_GAP = 10.0      # 클릭된 상품 중앙 가격이 우리보다 이만큼(€) 비싸면 검색 의도가 다르다고 봄
REPORT_SQP_HEAT_TEMP = 28.0       # 폭염일: 5개 도시 평균 최고기온
REPORT_SQP_HEAT_DAYS = 3          # 폭염일이 이만큼 있는 주를 '폭염 주'로 표시
REPORT_SQP_ROLES = {              # 경쟁 제품 역할 (Keepa 조회값이 있는 브랜드)
    "Mara Vital": "같은 자리 경쟁자", "RIBECO Germany": "같은 자리 경쟁자",   # 냉감패드 실적 1·2위 (2026 여름 순위, Keepa 상세)
}
REPORT_SQP_TYPE_DIRECTION = {
    "소재 개선": "메인 이미지·제목 A/B (③ 광고 소재)",
    "노출 확대": "광고 입찰 (소재 외 → ④ 광고 타이밍)",
    "제외 검토": "제외 키워드 (운영)",
}
REPORT_SQP_MONTHS = {"06": "6월", "07": "7월", "08": "8월"}


def report_sqp_ready():
    return REPORT_SQP_FILE.exists() and REPORT_SQP_LISTING_FILE.exists()


def report_sqp_read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def report_sqp_weeks_by_query(raw):
    """SQP 행을 검색어별 주 목록으로 바꿉니다. 점유율·CTR은 개수로 다시 계산합니다."""
    out = {}
    for r in raw["dataByAsin"]:
        imp, clk = r["impressionData"], r["clickData"]
        out.setdefault(r["searchQueryData"]["searchQuery"], []).append({
            "week": r["startDate"], "searches": r["searchQueryData"]["searchQueryVolume"],
            "mkt_imp": imp["totalQueryImpressionCount"], "our_imp": imp["asinImpressionCount"],
            "mkt_clk": clk["totalClickCount"], "our_clk": clk["asinClickCount"],
            "mkt_cart": r["cartAddData"]["totalCartAddCount"], "our_cart": r["cartAddData"]["asinCartAddCount"],
            "mkt_buy": r["purchaseData"]["totalPurchaseCount"], "our_buy": r["purchaseData"]["asinPurchaseCount"],
            "median_price": clk["totalMedianClickPrice"]["amount"],
        })
    for weeks in out.values():
        weeks.sort(key=lambda w: w["week"])
        for w in weeks:
            report_sqp_rates(w)
    return out


def report_sqp_rates(x):
    """노출 점유율, 클릭 점유율, 배수(= 우리 CTR ÷ 시장 CTR), 놓친 클릭을 붙입니다."""
    x["imp_share"] = x["our_imp"] / x["mkt_imp"] if x["mkt_imp"] else 0.0
    x["click_share"] = x["our_clk"] / x["mkt_clk"] if x["mkt_clk"] else 0.0
    x["ratio"] = x["click_share"] / x["imp_share"] if x["imp_share"] else 0.0
    x["mkt_ctr"] = x["mkt_clk"] / x["mkt_imp"] if x["mkt_imp"] else 0.0
    x["our_ctr"] = x["our_clk"] / x["our_imp"] if x["our_imp"] else 0.0
    x["missed"] = x["mkt_clk"] * x["imp_share"] - x["our_clk"]    # 보이는 만큼 눌렸다면 더 받았을 클릭
    return x


def report_sqp_sum(weeks):
    keys = ("searches", "mkt_imp", "our_imp", "mkt_clk", "our_clk", "mkt_cart", "our_cart", "mkt_buy", "our_buy")
    return report_sqp_rates({k: sum(w[k] for w in weeks) for k in keys})


def report_sqp_streak(weeks):
    """배수가 기준 미만인 주가 가장 길게 이어진 길이."""
    best = cur = 0
    for w in weeks:
        cur = cur + 1 if w["ratio"] < REPORT_SQP_RATIO_ALERT else 0
        best = max(best, cur)
    return best


def report_sqp_temps():
    """DWD 일 최고기온 → 주별 평균·최고·폭염일 수."""
    if not REPORT_SQP_TEMP_FILE.exists():
        return {}
    rows = list(csv.DictReader(REPORT_SQP_TEMP_FILE.open(encoding="utf-8")))
    out = {}
    for r in rows:
        d = date.fromisoformat(r["date"])
        week = (d - timedelta(days=d.weekday())).isoformat()
        out.setdefault(week, []).append(float(r["tmax_avg"]))
    return {w: {"avg": sum(v) / len(v), "max": max(v), "heat_days": sum(t >= REPORT_SQP_HEAT_TEMP for t in v)}
            for w, v in out.items()}


def report_sqp_events(snapshot_items):
    """경쟁사 할인·품절 주. Keepa 스냅샷에 events가 있으면 실제 값, 없으면 가정 파일."""
    keepa = [e for item in (snapshot_items or {}).values() for e in item.get("events") or []]
    if keepa:
        return keepa, "Keepa 실제"
    data = report_sqp_read_json(REPORT_SQP_EVENTS_FILE)
    return data["events"], data["source"]


def report_sqp_ads(query):
    """광고 성과 (가상): 검색어의 주별 검색 상단 노출 비율 평균, CPC, ACoS."""
    if not REPORT_SQP_ADS_FILE.exists():
        return None
    rows = [r for r in csv.DictReader(REPORT_SQP_ADS_FILE.open(encoding="utf-8")) if r["targeting"] == query]
    if not rows:
        return None
    by_week = {}
    for r in rows:
        d = date.fromisoformat(r["date"])
        by_week.setdefault((d - timedelta(days=d.weekday())).isoformat(), []).append(float(r["top_of_search_impression_share"]))
    clicks = sum(int(r["clicks"]) for r in rows)
    spend = sum(float(r["spend"]) for r in rows)
    sales = sum(float(r["sales_7d"]) for r in rows)
    orders = sum(int(r["orders_7d"]) for r in rows)
    tops = {w: sum(v) / len(v) for w, v in by_week.items()}
    return {"top_share": tops, "top_min": min(tops.values()), "top_max": max(tops.values()),
            "cpc": spend / clicks if clicks else 0.0, "acos": spend / sales if sales else 0.0,
            "spend": spend, "orders": orders, "spend_per_order": spend / orders if orders else 0.0}


def report_sqp_months(weeks):
    months = {}
    for w in weeks:
        months.setdefault(w["week"][5:7], []).append(w)
    return {m: report_sqp_sum(ws) for m, ws in sorted(months.items())}


def report_sqp_classify(total, streak, price, our_price, top_imp_share):
    """검색어 판정: 소재 개선 / 노출 확대 / 제외 검토 / 정상.
    노출 확대 = 잘 눌리는데(배수 1.2배 이상) 검색량 1위 검색어보다 덜 보이는(노출 점유율이 낮은) 검색어."""
    gap = price - our_price
    if total["ratio"] < REPORT_SQP_RATIO_ALERT and streak >= REPORT_SQP_ALERT_WEEKS:
        return "제외 검토" if gap >= REPORT_SQP_INTENT_GAP else "소재 개선"
    if total["ratio"] >= REPORT_SQP_RATIO_STRONG and total["imp_share"] < top_imp_share:
        return "노출 확대"
    return ""


def report_sqp_analyze(rivals, snapshot_items):
    """화면·다른 탭에 쓸 SQP 분석 결과 전부. 데이터 파일이 없으면 None."""
    if not report_sqp_ready():
        return None
    raw = report_sqp_read_json(REPORT_SQP_FILE)
    listing = report_sqp_read_json(REPORT_SQP_LISTING_FILE)
    by_query = report_sqp_weeks_by_query(raw)
    temps = report_sqp_temps()
    events, event_source = report_sqp_events(snapshot_items)
    our_price = listing["price"]

    queries = []
    for q, weeks in by_query.items():
        total = report_sqp_sum(weeks)
        months = report_sqp_months(weeks)
        queries.append({"query": q, "weeks": weeks, "total": total, "months": months,
                        "streak": report_sqp_streak(weeks), "median_price": weeks[-1]["median_price"],
                        "shape_source": raw.get("shape_source", {}).get(q, "")})
    queries.sort(key=lambda x: x["total"]["searches"], reverse=True)
    top_imp = queries[0]["total"]["imp_share"]
    for i, x in enumerate(queries, 1):
        x["volume_rank"] = i
        x["type"] = report_sqp_classify(x["total"], x["streak"], x["median_price"], our_price, top_imp)
        x["price_gap"] = our_price - x["median_price"]

    problems = report_sqp_problems(queries, listing)
    main = next((x for x in queries if x["type"] == "소재 개선"), queries[0])
    heat = report_sqp_heat(main, temps)
    return {
        "queries": queries, "problems": problems, "main": main, "listing": listing,
        "temps": temps, "heat": heat, "events": events, "event_source": event_source,
        "ads": report_sqp_ads(main["query"]),
        "competitors": report_sqp_competitors(rivals, listing),
        "period": f"{queries[0]['weeks'][0]['week']} ~ {queries[0]['weeks'][-1]['week']} 주",
        "weeks_count": len(queries[0]["weeks"]),
    }


def report_sqp_problems(queries, listing):
    """1단계 문제 Top 3: 소재 개선(놓친 클릭 순) → 노출 확대(늘릴 수 있는 클릭 순) → 제외 검토."""
    out = []
    for kind in ("소재 개선", "노출 확대", "제외 검토"):
        items = [x for x in queries if x["type"] == kind]
        if kind == "노출 확대":
            for x in items:
                x["extra"] = report_sqp_extra_clicks(x, queries)
            items.sort(key=lambda x: x["extra"]["clicks"], reverse=True)
        else:
            items.sort(key=lambda x: x["total"]["missed"], reverse=True)
        out += items
    return out[:3]


def report_sqp_extra_clicks(x, queries):
    """노출 확대: 노출 점유율을 메인 검색어 수준으로 올리고 배수를 유지하면 가장 많은 달에 늘어날 클릭."""
    goal = max((q["total"]["imp_share"] for q in queries if q["type"] == "소재 개선"), default=0.09)
    month, m = max(x["months"].items(), key=lambda kv: kv[1]["mkt_clk"])
    clicks = m["mkt_clk"] * max(goal - m["imp_share"], 0) * m["ratio"]
    return {"goal": goal, "month": REPORT_SQP_MONTHS.get(month, month), "clicks": clicks}


def report_sqp_heat(main, temps):
    """폭염 주 vs 나머지 주: 검색량(시장 클릭)과 우리 배수 비교."""
    hot = [w for w in main["weeks"] if temps.get(w["week"], {}).get("heat_days", 0) >= REPORT_SQP_HEAT_DAYS]
    cool = [w for w in main["weeks"] if w not in hot]
    if not hot or not cool:
        return None
    def avg(ws, k):
        return sum(w[k] for w in ws) / len(ws)

    return {"weeks": [w["week"] for w in hot], "clk_hot": avg(hot, "mkt_clk"), "clk_cool": avg(cool, "mkt_clk"),
            "ratio_hot": avg(hot, "ratio"), "ratio_cool": avg(cool, "ratio")}


def report_sqp_competitors(rivals, listing):
    """경쟁 제품 (역할별): Keepa 실제 값 + 우리 상품(가상). 저가 대표는 ASIN이 정해지면 추가."""
    out = [{"role": "우리", "brand": listing["brand"], "price": listing["price"], "rating": listing["rating"],
            "reviews": listing["reviews"], "source": "가상", "note": listing["main_image"]}]
    for r in rivals:
        role = REPORT_SQP_ROLES.get(r["brand"])
        k = r.get("keepa")
        if role and k:
            out.append({"role": role, "brand": r["brand"], "price": k.get("price"), "rating": k.get("rating"),
                        "reviews": k.get("reviews"), "source": "Keepa 실제",
                        "note": f"90일 평균 대비 {k['change'] * 100:+.0f}%" if k.get("change") is not None else ""})
    out.append({"role": "저가 대표", "brand": "(ASIN 미정)", "price": None, "rating": None, "reviews": None,
                "source": "확인 필요", "note": "검색 상위 무명 저가 제품 중 판매 1위를 Keepa로 찾아 report_keepa_asin에 추가"})
    return out


def report_sqp_month_range(x, key):
    vals = [m[key] for m in x["months"].values()]
    return min(vals), max(vals)


def report_sqp_main_reasons(sqp):
    """문제 1 선정 이유 3가지 (숫자는 데이터에서 계산)."""
    main, queries = sqp["main"], sqp["queries"]
    lo, hi = report_sqp_month_range(main, "ratio")
    t = main["total"]
    peak_m, peak = max(main["months"].items(), key=lambda kv: kv[1]["mkt_clk"])
    our_cart = peak["our_cart"] / peak["our_clk"] * 100 if peak["our_clk"] else 0
    mkt_cart = peak["mkt_cart"] / peak["mkt_clk"] * 100 if peak["mkt_clk"] else 0
    strong = next((x for x in queries if x["type"] == "노출 확대"), None)
    price = (f"여기서는 클릭된 상품 중앙 가격보다 {main['price_gap']:+.0f}유로"
             + (f"지만, {strong['query']}에서는 {strong['price_gap']:+.0f}유로여도 배수 {strong['total']['ratio']:.2f}배로 잘 눌려요."
                if strong else "예요."))
    return [
        ("가장 큰 문제", f"검색량 {main['volume_rank']}위 검색어이고, {len(main['months'])}개월 내내 배수가 {lo:.2f}~{hi:.2f}배예요. "
                       f"놓친 클릭은 약 {t['missed']:,.0f}회예요."),
        ("클릭 이후는 괜찮다", f"{REPORT_SQP_MONTHS.get(peak_m, peak_m)}(검색 가장 많은 달) 클릭 대비 장바구니가 우리 {our_cart:.1f}%, "
                           f"시장 {mkt_cart:.1f}%로 비슷해요. 상품이 아니라 검색 결과의 첫인상이 문제예요."),
        ("가격이 주원인은 아니다", price),
    ]


def report_sqp_statement(sqp):
    """문제 문장 (발표용 한 줄)."""
    main = sqp["main"]
    t = main["total"]
    months = list(main["months"])
    span = f"2026년 {int(months[0])}~{int(months[-1])}월"
    peak_m, peak = max(main["months"].items(), key=lambda kv: kv[1]["missed"])
    rank = "가장 많은" if main["volume_rank"] == 1 else f"{main['volume_rank']}위인"
    return (f"{span}, 검색량이 {rank} '{main['query']}'에서 우리 냉감패드는 노출 점유율 {t['imp_share'] * 100:.1f}%에 비해 "
            f"클릭 점유율이 {t['click_share'] * 100:.1f}%로, 보이는 만큼의 {t['ratio']:.2f}배만 눌렸다. "
            f"보이는 만큼 눌렸다면 {len(months)}개월 동안 약 {t['missed']:,.0f}회를 더 클릭받았을 것이다 "
            f"({REPORT_SQP_MONTHS.get(peak_m, peak_m)}에만 약 {peak['missed']:,.0f}회).")


def report_sqp_kpis(sqp):
    """상단 KPI 4개: 메인 검색어 기준."""
    t = sqp["main"]["total"]
    return [
        {"label": "노출 점유율", "value": f"{t['imp_share'] * 100:.1f}%", "badge": "가상 SQP", "good": True},
        {"label": "클릭 점유율", "value": f"{t['click_share'] * 100:.1f}%", "badge": "가상 SQP", "good": False},
        {"label": "클릭 ÷ 노출 배수", "value": f"{t['ratio']:.2f}배", "badge": f"기준 {REPORT_SQP_RATIO_ALERT}배 미만",
         "good": t["ratio"] >= REPORT_SQP_RATIO_ALERT},
        {"label": "놓친 클릭", "value": f"{t['missed']:,.0f}회", "badge": f"{sqp['weeks_count']}주 합계", "good": False},
    ]


def report_sqp_handoff(sqp, rivals):
    """다른 탭용: problems 맨 앞에 넣을 SQP 문제(가설 탭 계약 필드 포함)와 store의 'sqp' 값."""
    main, listing = sqp["main"], sqp["listing"]
    kb = report_knowledge({"SHP-006"})
    ctx = kb.get("SHP-006")
    eur = [r for r in rivals if r["kind"] != "자사" and r["currency"] == "EUR"]
    weak = [f"{r['brand'].split()[0]} {r['weakness'].split(',')[0].strip()}" for r in eur[:3] if r["weakness"]]
    review = " / ".join(weak) + " (경쟁사 DB 약점, 실제 리뷰 원문 아님)" if weak else ""

    problems, key_problems = [], []
    for rank, x in enumerate(sqp["problems"], 1):
        t = x["total"]
        if x["type"] == "소재 개선":
            title = f"'{x['query']}' 검색에서 보이는 만큼 안 눌림 (클릭 ÷ 노출 {t['ratio']:.2f}배)"
            detail = report_sqp_statement(sqp)
            question = "검색 결과 첫인상(메인 이미지·제목)을 어떻게 바꾸면 보이는 만큼 눌릴까?"
        elif x["type"] == "노출 확대":
            e = x["extra"]
            title = f"'{x['query']}'는 잘 눌리는데 덜 보임 (노출 점유율 {t['imp_share'] * 100:.1f}%, 배수 {t['ratio']:.2f}배)"
            detail = (f"노출 점유율을 {e['goal'] * 100:.0f}%로 올리면 {e['month']}에만 약 {e['clicks']:,.0f}회 클릭 증가 예상. "
                      f"소재보다 광고 예산 문제라 소재 외 문제로 분류 (가상 SQP)")
            question = "더운 날 입찰을 올리면 노출 점유율을 얼마나 올릴 수 있을까?"
        else:
            title = f"'{x['query']}'는 검색 의도가 다름 (클릭된 상품 중앙 가격 €{x['median_price']:.2f})"
            detail = (f"배수 {t['ratio']:.2f}배지만 클릭된 상품이 우리보다 €{-x['price_gap']:.0f} 비싼 두꺼운 토퍼라 "
                      f"가설 없이 광고 제외 키워드로 처리 (가상 SQP)")
            question = "이 검색어를 광고 제외 키워드로 돌리면 광고비가 얼마나 줄까?"
        level = "높음" if rank == 1 else "중간"
        key_problems.append({"rank": rank, "type": "내부", "level": level, "group": x["type"], "title": title,
                             "detail": detail, "question": question})
        problems.append({
            "title": title, "type": "내부", "level": level, "group": "검색 클릭", "detail": detail,
            "target": f"amazon.de '{x['query']}' 검색 결과",
            "metric": "클릭 점유율 ÷ 노출 점유율",
            "local_context": f"{ctx['내용 (한국어)']} (독일 DB {ctx['ID']})" if ctx else "",
            "competitor_review": review,
            "sqp_type": x["type"], "query": x["query"],
        })

    t = main["total"]
    lo, hi = report_sqp_month_range(main, "ratio")
    sub = next((x for x in sqp["problems"] if x["type"] == "노출 확대"), None)
    store = {
        "source": "노출·클릭·장바구니·구매·광고·우리 상품 = 가상 / 경쟁 제품 = Keepa 실제 / 기온 = DWD 실제 / "
                  f"경쟁사 할인·품절 주 = {sqp['event_source']}",
        "period": sqp["period"],
        "query": main["query"],
        "imp_share": round(t["imp_share"] * 100, 2), "click_share": round(t["click_share"] * 100, 2),
        "ratio": round(t["ratio"], 2), "ratio_range": [round(lo, 2), round(hi, 2)],
        "missed_clicks": round(t["missed"]),
        "cart_rate_ours": round(t["our_cart"] / t["our_clk"] * 100, 1) if t["our_clk"] else None,
        "cart_rate_market": round(t["mkt_cart"] / t["mkt_clk"] * 100, 1) if t["mkt_clk"] else None,
        "our_price": listing["price"], "median_click_price": main["median_price"], "price_gap": round(main["price_gap"], 2),
        "listing": {k: listing[k] for k in ("title", "price", "rating", "reviews", "main_image", "main_image_issue", "certs")},
        "competitors": [c for c in sqp["competitors"] if c["source"] == "Keepa 실제"],
        "kpi_goal": 0.8,
        "problem2": ({"query": sub["query"], "imp_share": round(sub["total"]["imp_share"] * 100, 1),
                      "ratio": round(sub["total"]["ratio"], 2), "goal_imp_share": round(sub["extra"]["goal"] * 100, 1),
                      "extra_clicks": round(sub["extra"]["clicks"]), "month": sub["extra"]["month"],
                      "heat_temp": REPORT_SQP_HEAT_TEMP} if sub else None),
        "problems": [{"rank": p["rank"], "type": p["group"], "title": p["title"]} for p in key_problems],
    }
    return problems, key_problems, store
