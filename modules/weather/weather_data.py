# 4. 날씨 광고 타이밍 - 데이터 불러오기와 추천 계산 (화면 코드 없음)
import csv
import json
import re
from datetime import date, timedelta
from pathlib import Path

import requests
import streamlit as st

# 권역별 주요 도시 3곳 (첫 번째가 대표 도시). 권역 기온 = 3개 도시 평균
WEATHER_REGIONS = [
    {"code": "nord", "name": "북부", "de": "Nord", "cities": [
        {"city": "Hamburg", "lat": 53.55, "lon": 9.99},
        {"city": "Bremen", "lat": 53.08, "lon": 8.80},
        {"city": "Kiel", "lat": 54.32, "lon": 10.14},
    ]},
    {"code": "west", "name": "서부", "de": "West", "cities": [
        {"city": "Köln", "lat": 50.94, "lon": 6.96},
        {"city": "Düsseldorf", "lat": 51.23, "lon": 6.78},
        {"city": "Dortmund", "lat": 51.51, "lon": 7.47},
    ]},
    {"code": "ost", "name": "동부", "de": "Ost", "cities": [
        {"city": "Berlin", "lat": 52.52, "lon": 13.40},
        {"city": "Leipzig", "lat": 51.34, "lon": 12.37},
        {"city": "Dresden", "lat": 51.05, "lon": 13.74},
    ]},
    {"code": "sued", "name": "남부", "de": "Süd", "cities": [
        {"city": "München", "lat": 48.14, "lon": 11.58},
        {"city": "Stuttgart", "lat": 48.78, "lon": 9.18},
        {"city": "Nürnberg", "lat": 49.45, "lon": 11.08},
    ]},
]

WEATHER_HOT_C = 30            # 이 온도 이상이면 '폭염일'

WEATHER_STOCK_LABEL = {"soldout": "품절", "low": "재고 낮음", "normal": "정상"}

# WMO 날씨 코드 → 짧은 설명
WEATHER_WMO_TEXT = {
    0: "맑음", 1: "대체로 맑음", 2: "구름 조금", 3: "흐림", 45: "안개", 48: "안개",
    51: "이슬비", 53: "이슬비", 55: "이슬비", 61: "비", 63: "비", 65: "강한 비",
    71: "눈", 73: "눈", 75: "강한 눈", 80: "소나기", 81: "소나기", 82: "강한 소나기",
    95: "뇌우", 96: "뇌우", 99: "뇌우",
}


# ─────────────────────────────────────────────
# 1. 날씨 (Open-Meteo, 키 불필요)
# ─────────────────────────────────────────────
def _weather_fetch_one(coords):
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={coords['lat']}&longitude={coords['lon']}"
        f"&current=temperature_2m,weather_code&timezone=Europe%2FBerlin"
        f"&daily=temperature_2m_max,temperature_2m_min,weather_code&forecast_days=7"
    )
    res = requests.get(url, timeout=8)
    res.raise_for_status()
    data = res.json()
    daily = data["daily"]
    return {
        **coords,
        "now": float(data["current"]["temperature_2m"]),
        "wcode": int(data["current"]["weather_code"]),
        "updated": data["current"]["time"],
        "days": [
            {"date": d, "tmax": float(hi), "tmin": float(lo), "wcode": int(w)}
            for d, hi, lo, w in zip(
                daily["time"], daily["temperature_2m_max"], daily["temperature_2m_min"], daily["weather_code"]
            )
        ],
    }


def _weather_region_from_cities(region, cities, updated):
    """도시별 값 → 권역 값 (현재 기온·날짜별 최고/최저는 도시 평균, 날씨 코드는 대표 도시)."""
    n = len(cities)
    days = [
        {
            "date": cities[0]["days"][i]["date"],
            "tmax": round(sum(c["days"][i]["tmax"] for c in cities) / n, 1),
            "tmin": round(sum(c["days"][i]["tmin"] for c in cities) / n, 1),
            "wcode": cities[0]["days"][i]["wcode"],
        }
        for i in range(min(len(c["days"]) for c in cities))
    ]
    return {
        "code": region["code"], "name": region["name"], "de": region["de"],
        "city": cities[0]["city"],
        "cities": [{"city": c["city"], "now": c["now"], "max7": max(d["tmax"] for d in c["days"])} for c in cities],
        "now": round(sum(c["now"] for c in cities) / n, 1),
        "wcode": cities[0]["wcode"],
        "updated": updated,
        "days": days,
    }


@st.cache_data(ttl=1800, show_spinner=False)
def weather_fetch_regions():
    """4개 권역(권역당 3개 도시)의 현재 기온 + 7일 예보.
    도시 12곳을 동시에 조회하고, 모두 실패한 권역은 {'error': ...}로 돌려줍니다."""
    from concurrent.futures import ThreadPoolExecutor

    def one(coords):
        try:
            return _weather_fetch_one(coords)
        except Exception as err:
            return {**coords, "error": str(err)}

    all_cities = [c for r in WEATHER_REGIONS for c in r["cities"]]
    with ThreadPoolExecutor(max_workers=6) as pool:
        fetched = dict(zip([c["city"] for c in all_cities], pool.map(one, all_cities)))

    result = []
    for r in WEATHER_REGIONS:
        ok = [fetched[c["city"]] for c in r["cities"] if "error" not in fetched[c["city"]]]
        if not ok:
            result.append({"code": r["code"], "name": r["name"], "de": r["de"],
                           "city": r["cities"][0]["city"], "error": "조회 실패"})
            continue
        result.append(_weather_region_from_cities(r, ok, ok[0]["updated"]))
    return result


def weather_sample_regions():
    """폭염 시나리오 샘플 (화면·보고서 시연용, 실제 예보 아님). 도시별로 ±1~2°C 차이를 둠."""
    today = date.today()
    sample = {
        "nord": (22, [24, 25, 24, 23, 22, 23, 24], [14, 15, 14, 13, 13, 14, 14]),
        "west": (27, [28, 29, 29, 28, 27, 27, 26], [17, 18, 18, 17, 16, 16, 16]),
        "ost": (29, [30, 31, 31, 30, 29, 28, 27], [19, 20, 21, 19, 18, 18, 17]),
        "sued": (31, [27, 30, 33, 35, 34, 29, 26], [17, 19, 21, 22, 21, 18, 16]),
    }
    offsets = [0, 1, -1]
    result = []
    for r in WEATHER_REGIONS:
        now, highs, lows = sample[r["code"]]
        cities = [
            {"city": c["city"], "now": float(now + off), "wcode": 0,
             "days": [{"date": (today + timedelta(days=i)).isoformat(), "tmax": float(h + off),
                       "tmin": float(lo + off), "wcode": 0} for i, (h, lo) in enumerate(zip(highs, lows))]}
            for c, off in zip(r["cities"], offsets)
        ]
        result.append(_weather_region_from_cities(r, cities, f"{today.isoformat()} (샘플)"))
    return result


# ─────────────────────────────────────────────
# 2. 경쟁사 재고 (경쟁사 DB + Keepa 마지막 조회값, 읽기만)
# ─────────────────────────────────────────────
# - 경쟁사 DB: 루트 data/의 공용 CSV에서 구분이 "독일 N위"인 경쟁사 (report 대시보드와 같은 상위 경쟁사)
# - 재고: report 탭이 Keepa로 조회해 저장한 스냅샷의 in_stock (weather는 Keepa를 직접 부르지 않아 토큰을 쓰지 않음)
#   스냅샷은 report 탭의 조회 버튼이나 아침 자동 갱신(하루 1번) 때 바뀝니다.
# - Keepa 값으로는 품절/정상만 알 수 있어 "재고 낮음"과 "품절 N일째"는 샘플에만 있습니다.
# 화면과 보고서는 아래 모양만 사용합니다.
#   [{"competitor": "Novilla", "product": "...", "asin": "B0...", "status": "soldout" | "low" | "normal",
#     "days": 2 또는 None, "checked": "2026-10-24 08:10" (Keepa 조회 시점, 샘플은 "")}]
WEATHER_ROOT = Path(__file__).resolve().parents[2]
WEATHER_COMPETITOR_DB = WEATHER_ROOT / "data" / "common_competitor_seori_202610.csv"
WEATHER_KEEPA_SNAPSHOT = WEATHER_ROOT / "modules" / "report" / "data" / "report_keepa_snapshot.json"

WEATHER_SAMPLE_COMPETITORS = [
    {"competitor": "경쟁사 B", "product": "쿨링매트 L", "asin": "B0SAMPLE01", "status": "soldout", "days": 2, "checked": ""},
    {"competitor": "경쟁사 A", "product": "쿨링패드", "asin": "B0SAMPLE02", "status": "low", "days": 1, "checked": ""},
    {"competitor": "경쟁사 C", "product": "토퍼", "asin": "B0SAMPLE03", "status": "normal", "days": 0, "checked": ""},
]


def _weather_read_competitors():
    """경쟁사 DB의 "독일 N위" 경쟁사 중 Keepa 스냅샷에 있는 상품만, 순위 순서로 돌려줍니다."""
    snapshot = json.loads(WEATHER_KEEPA_SNAPSHOT.read_text(encoding="utf-8"))
    items = snapshot.get("items") or {}
    checked = str(snapshot.get("fetched_at") or "")
    out = []
    with WEATHER_COMPETITOR_DB.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            rank = re.match(r"독일 (\d+)위", r.get("구분") or "")
            asin = (r.get("ASIN (Keepa 자동 갱신용)") or "").strip()
            if r.get("원본시트") != "경쟁사DB" or not rank or asin not in items:
                continue
            out.append({
                "competitor": r["기업/브랜드"], "product": r["제품명"], "asin": asin, "rank": int(rank.group(1)),
                "status": "normal" if items[asin].get("in_stock") else "soldout",
                "days": None, "checked": checked,
                # 경쟁사 분석용 Keepa 값 (현재가·90일 평균 대비 변화·평점·리뷰·판매 순위)
                "price": items[asin].get("price"), "change": items[asin].get("change"),
                "rating": items[asin].get("rating"), "reviews": items[asin].get("reviews"),
                "sales_rank": items[asin].get("rank"),
            })
    return sorted(out, key=lambda c: c["rank"])


def weather_get_competitors():
    """(목록, 샘플 여부)를 돌려줍니다. 파일을 못 읽거나 맞는 경쟁사가 없으면 샘플을 씁니다."""
    try:
        rows = _weather_read_competitors()
    except (OSError, ValueError, KeyError, csv.Error):
        rows = []
    return (rows, False) if rows else (WEATHER_SAMPLE_COMPETITORS, True)


def weather_checked_label(checked):
    """Keepa 조회 시점을 짧게: '2026-10-24 08:10' → '10/24 08:10'."""
    day, _, time = str(checked).partition(" ")
    try:
        d = date.fromisoformat(day)
    except ValueError:
        return str(checked)
    return f"{d.month}/{d.day}" + (f" {time}" if time else "")


def weather_stock_checked(competitors):
    """실제 데이터의 Keepa 조회 시점 (짧은 형식). 샘플이면 ''."""
    return next((weather_checked_label(c["checked"]) for c in competitors if c.get("checked")), "")


def weather_stock_text(c):
    """상태 문구: '품절 2일째'(샘플) / '품절 (10/24 확인)'(Keepa) / '정상'."""
    label = WEATHER_STOCK_LABEL.get(c["status"], c["status"])
    if c["status"] == "normal":
        return label
    if c.get("days"):
        return f"{label} {c['days']}일째"
    if c.get("checked"):
        return f"{label} ({weather_checked_label(c['checked'])} 확인)"
    return label


# ─────────────────────────────────────────────
# 3. 예산 추천 계산 (규칙 기반, 금액은 유로)
# ─────────────────────────────────────────────
WEATHER_AMAZON_ONLY = 1.0            # 2026-10-25: 메타는 운영하지 않고 아마존만 (예산 전부 아마존, 날짜별 배분)
WEATHER_AMAZON_SHARE = 0.40          # (예전) 기본 아마존 비중 - 메타를 함께 쓸 때만
WEATHER_AMAZON_SHARE_LOW = 0.45      # 경쟁사 재고 낮음일 때
WEATHER_AMAZON_SHARE_SOLDOUT = 0.50  # 경쟁사 품절일 때


WEATHER_HEAT_POOL = 0.40             # 메타 예산 중 30°C 이상 예보일에 몰아줄 비중


def weather_heat_points(tmax):
    """30°C 이상인 날의 추가 배정 점수: 최고기온 - 29 (30°C=1점, 35°C=6점). 30°C 미만은 0점."""
    return max(0.0, tmax - (WEATHER_HOT_C - 1))


def weather_split(total, weights):
    """total(정수 €)을 weights 비율로 나누되, 반올림해도 합계가 정확히 total이 되게 합니다."""
    s = sum(weights)
    if not weights or s <= 0:
        return [0] * len(weights)
    raw = [total * w / s for w in weights]
    out = [int(x) for x in raw]
    order = sorted(range(len(raw)), key=lambda i: raw[i] - out[i], reverse=True)
    for i in order[: total - sum(out)]:
        out[i] += 1
    return out


def _weather_longest_hot_streak(days):
    best = run = 0
    for d in days:
        run = run + 1 if d["tmax"] >= WEATHER_HOT_C else 0
        best = max(best, run)
    return best


def weather_recommended_amazon_share(competitors):
    """경쟁사 재고로 정한 추천 아마존 비중 (0~1)."""
    if any(c["status"] == "soldout" for c in competitors):
        return WEATHER_AMAZON_SHARE_SOLDOUT
    if any(c["status"] == "low" for c in competitors):
        return WEATHER_AMAZON_SHARE_LOW
    return WEATHER_AMAZON_SHARE


def weather_build_plan(regions, competitors, budget, amazon_share=None):
    """권역 날씨 + 경쟁사 재고 + 주간 예산(€) → 채널·권역·일별 예산.
    amazon_share를 주면 그 비중(0~1)을 쓰고, 없으면 경쟁사 재고로 정한 추천 비중을 씁니다."""
    ok = [r for r in regions if "error" not in r]
    soldout = [c for c in competitors if c["status"] == "soldout"]
    low = [c for c in competitors if c["status"] == "low"]

    # 1) 채널 나누기: 직접 정한 비중, 없으면 추천 비중 (경쟁사 품절이면 아마존을 올림)
    recommended = weather_recommended_amazon_share(competitors)
    manual = amazon_share is not None and abs(amazon_share - recommended) > 1e-9
    amazon_share = recommended if amazon_share is None else amazon_share
    amazon = round(budget * amazon_share)
    meta = budget - amazon

    # 2) 권역 배분: 60%는 권역·날짜에 똑같이, 40%는 30°C 이상 예보일에 (최고기온-29)점 비례로 추가
    #    메타를 안 쓰면(아마존만) 아마존 예산을 권역 날씨로 나눈 값 = 권역별 아마존 비중 (지역 타겟 기준)
    region_total = meta if meta > 0 else amazon
    n_days = min((len(r["days"]) for r in ok), default=7)
    cells = [(r["code"], i) for r in ok for i in range(n_days)]
    heat = [weather_heat_points(r["days"][i]["tmax"]) for r in ok for i in range(n_days)]
    pool = round(region_total * WEATHER_HEAT_POOL) if sum(heat) else 0
    base = [v for part in weather_split(region_total - pool, [1] * len(ok)) for v in weather_split(part, [1] * n_days)]
    boost = weather_split(pool, heat) if pool else [0] * len(cells)
    cell_eur = {c: b + h for c, b, h in zip(cells, base, boost)}
    even = region_total / len(ok) if ok else 0   # 4개 권역에 똑같이 나눴을 때 금액

    scored = []
    for r in ok:
        daily = [cell_eur[(r["code"], i)] for i in range(n_days)]
        week = sum(daily)
        scored.append({
            **r,
            "daily": daily,
            "week": week,
            "vs_even": round((week / even - 1) * 100) if even else 0,
            "max7": max(d["tmax"] for d in r["days"]),
            "hot_days": [d for d in r["days"] if d["tmax"] >= WEATHER_HOT_C],
            "streak": _weather_longest_hot_streak(r["days"]),
        })

    # 3) 아마존: 전국 단위, 날짜별 가중치 = 1 + 0.1 × (그날 4개 권역 추가 배정 점수 합)
    day_w = [1 + 0.1 * sum(weather_heat_points(r["days"][i]["tmax"]) for r in ok) for i in range(n_days)]
    amazon_daily = weather_split(amazon, day_w) if ok else []

    hot_regions = sorted((r for r in scored if r["hot_days"]), key=lambda r: -r["week"])
    triggers = [f"{r['name']} {r['streak']}일 연속 {WEATHER_HOT_C}°C 이상 예보" for r in scored if r["streak"] >= 3]
    triggers += [f"{c['competitor']} {c['product']} {weather_stock_text(c)}" for c in soldout]

    return {
        "budget": budget,
        "meta": meta,
        "amazon": amazon,
        "region_total": region_total,
        "amazon_share": amazon_share,
        "recommended_share": recommended,
        "share_manual": manual,
        "amazon_daily": amazon_daily,
        "even": even,
        "regions": scored,
        "failed": [r for r in regions if "error" in r],
        "competitors": competitors,
        "soldout": soldout,
        "low": low,
        "hot_regions": hot_regions,
        "hot_total": sum(r["week"] for r in hot_regions),
        "triggers": triggers,
        "dates": [d["date"] for d in ok[0]["days"]] if ok else [],
    }


def weather_eur(value):
    return f"€{value:,.0f}"


def weather_amazon_days(plan):
    """아마존 날짜별 배분 [{date, tmax(4개 권역 중 최고), hot_regions, eur, vs_avg(평균 대비 %)}]."""
    days = plan["dates"]
    avg = plan["amazon"] / len(days) if days else 0
    out = []
    for i, d in enumerate(days):
        tmax = max(r["days"][i]["tmax"] for r in plan["regions"])
        eur = plan["amazon_daily"][i]
        out.append({"date": d, "tmax": tmax, "eur": eur,
                    "hot_regions": [r["name"] for r in plan["regions"] if r["days"][i]["tmax"] >= WEATHER_HOT_C],
                    "vs_avg": round((eur / avg - 1) * 100) if avg else 0})
    return out


def weather_headline(plan):
    """배너 제목 한 줄 (아마존만)."""
    days = weather_amazon_days(plan)
    hot = [d for d in days if d["hot_regions"]]
    if hot:
        peak = max(hot, key=lambda d: d["eur"])
        return f"아마존 {weather_eur(plan['amazon'])} · 폭염일 {len(hot)}일 상향 (최고 {weather_short_date(peak['date'])} {weather_eur(peak['eur'])})"
    return f"아마존 {weather_eur(plan['amazon'])} · 날짜별 고르게 운영"


def weather_wmo_text(code):
    return WEATHER_WMO_TEXT.get(code, "-")


def weather_weekday(iso):
    return "월화수목금토일"[date.fromisoformat(iso).weekday()]


def weather_short_date(iso):
    d = date.fromisoformat(iso)
    return f"{d.month}/{d.day}({weather_weekday(iso)})"


def weather_wmo_emoji(code):
    """WMO 날씨 코드 → 이모지."""
    if code in (0, 1):
        return "☀️"
    if code == 2:
        return "⛅"
    if code == 3:
        return "☁️"
    if code in (45, 48):
        return "🌫️"
    if 51 <= code <= 57 or 80 <= code <= 82:
        return "🌦️"
    if 61 <= code <= 67:
        return "🌧️"
    if 71 <= code <= 77 or code in (85, 86):
        return "❄️"
    if code >= 95:
        return "⛈️"
    return "🌤️"


def _weather_date_range(days):
    first, last = days[0]["date"], days[-1]["date"]
    return weather_short_date(first) if first == last else f"{weather_short_date(first)}~{weather_short_date(last)}"


def _weather_eur_range(lo, hi):
    """금액 범위 글자 (같으면 한 금액만)."""
    return weather_eur(lo) if round(lo) == round(hi) else f"{weather_eur(lo)}~{weather_eur(hi)}"


def weather_reco_items(plan):
    """'오늘의 추천' 할 일 목록 (아마존만): [{tag, text, tone}] (tone: hot / stock / calm)."""
    items = []
    days = weather_amazon_days(plan)
    hot = [d for d in days if d["hot_regions"]]
    cool = [d for d in days if not d["hot_regions"]]
    if hot:
        regions = "·".join(dict.fromkeys(n for d in hot for n in d["hot_regions"]))
        lo, hi = min(d["eur"] for d in hot), max(d["eur"] for d in hot)
        up = max(d["vs_avg"] for d in hot)
        items.append({
            "tag": f"아마존 · {_weather_date_range(hot)}",
            "text": f"{len(hot)}일 {WEATHER_HOT_C}°C 이상 예보({regions}). 이 날 아마존 일 예산을 "
                    f"{_weather_eur_range(lo, hi)}(평균 대비 최대 +{up}%)로 올려 집행하세요.",
            "tone": "hot",
        })
    for c in plan["soldout"]:
        items.append({
            "tag": f"아마존 · {c['competitor']}",
            "text": f"{c['product']} {weather_stock_text(c)}. 경쟁사 ASIN 타겟 광고를 켜서 그 검색 수요를 가져오세요.",
            "tone": "stock",
        })
    for c in plan["low"]:
        items.append({
            "tag": f"아마존 · {c['competitor']}",
            "text": f"{c['product']} 재고가 낮아요. 품절되면 바로 ASIN 타겟 광고를 켤 수 있게 준비하세요.",
            "tone": "calm",
        })
    if hot and cool:
        lo, hi = min(d["eur"] for d in cool), max(d["eur"] for d in cool)
        items.append({
            "tag": f"아마존 · 평소일 {len(cool)}일",
            "text": f"{WEATHER_HOT_C}°C 미만 예보일은 일 {_weather_eur_range(lo, hi)} 기본 금액으로 유지하세요.",
            "tone": "calm",
        })
    if not hot:
        items.insert(0, {
            "tag": "아마존 · 7일",
            "text": f"7일 동안 {WEATHER_HOT_C}°C 이상 예보가 없어요. 아마존 {weather_eur(plan['amazon'])}를 "
                    f"날짜별로 고르게(일 {weather_eur(plan['amazon'] / max(len(days), 1))} 안팎) 운영하세요.",
            "tone": "calm",
        })
    return items
