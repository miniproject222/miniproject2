# 4. 날씨 광고 타이밍 - 데이터 불러오기와 추천 계산 (화면 코드 없음)
from datetime import date, timedelta

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
# 2. 경쟁사 재고 (DB 연결 전에는 샘플)
# ─────────────────────────────────────────────
# DB를 넣으면 이 함수 안만 바꾸면 됩니다. 화면과 보고서는 아래 모양만 사용합니다.
#   [{"competitor": "경쟁사 B", "product": "쿨링매트 L", "asin": "B0XXXXXXX",
#     "status": "soldout" | "low" | "normal", "days": 2}]   # days = 그 상태가 이어진 일수
# 예: rows = db_read("weather_competitor_stock")  (from common.common_db import db_read)
WEATHER_SAMPLE_COMPETITORS = [
    {"competitor": "경쟁사 B", "product": "쿨링매트 L", "asin": "B0SAMPLE01", "status": "soldout", "days": 2},
    {"competitor": "경쟁사 A", "product": "쿨링패드", "asin": "B0SAMPLE02", "status": "low", "days": 1},
    {"competitor": "경쟁사 C", "product": "토퍼", "asin": "B0SAMPLE03", "status": "normal", "days": 0},
]


def weather_get_competitors():
    """(목록, 샘플 여부)를 돌려줍니다."""
    return WEATHER_SAMPLE_COMPETITORS, True


# ─────────────────────────────────────────────
# 3. 예산 추천 계산 (규칙 기반, 금액은 유로)
# ─────────────────────────────────────────────
WEATHER_AMAZON_SHARE = 0.40          # 기본 아마존 비중 (나머지는 메타)
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

    # 2) 메타: 60%는 권역·날짜에 똑같이, 40%는 30°C 이상 예보일에 (최고기온-29)점 비례로 추가
    n_days = min((len(r["days"]) for r in ok), default=7)
    cells = [(r["code"], i) for r in ok for i in range(n_days)]
    heat = [weather_heat_points(r["days"][i]["tmax"]) for r in ok for i in range(n_days)]
    pool = round(meta * WEATHER_HEAT_POOL) if sum(heat) else 0
    base = [v for part in weather_split(meta - pool, [1] * len(ok)) for v in weather_split(part, [1] * n_days)]
    boost = weather_split(pool, heat) if pool else [0] * len(cells)
    cell_eur = {c: b + h for c, b, h in zip(cells, base, boost)}
    even = meta / len(ok) if ok else 0   # 4개 권역에 똑같이 나눴을 때 금액

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
    triggers += [f"{c['competitor']} {c['product']} 품절 {c['days']}일째" for c in soldout]

    return {
        "budget": budget,
        "meta": meta,
        "amazon": amazon,
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


def weather_headline(plan):
    """배너 제목 한 줄."""
    if plan["hot_regions"]:
        top = plan["hot_regions"][0]
        head = f"{top['name']} 메타 {weather_eur(top['week'])}"
        if top["vs_even"] > 0:
            head += f" (균등 대비 +{top['vs_even']}%)"
    else:
        head = f"메타 {weather_eur(plan['meta'])} 권역 균등 운영"
    return f"{head} · 아마존 {weather_eur(plan['amazon'])}"


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


def weather_reco_items(plan):
    """'오늘의 추천' 할 일 목록: [{tag, text, tone}] (tone: hot / stock / calm)."""
    items = []
    for r in plan["hot_regions"]:
        streak = f"{r['streak']}일 연속" if r["streak"] >= 2 else f"{len(r['hot_days'])}일"
        up = f"(균등 대비 +{r['vs_even']}%)" if r["vs_even"] > 0 else ""
        items.append({
            "tag": f"{r['name']} · {_weather_date_range(r['hot_days'])}",
            "text": f"{streak} {WEATHER_HOT_C}°C 이상 예보. 메타 {r['name']} 예산을 {weather_eur(r['week'])}{up}로 올려 집행하세요.",
            "tone": "hot",
        })
    for c in plan["soldout"]:
        items.append({
            "tag": f"아마존 · {c['competitor']}",
            "text": f"{c['product']} 품절 {c['days']}일째. ASIN 타겟 광고를 켜고 아마존에 {weather_eur(plan['amazon'])}를 배정하세요.",
            "tone": "stock",
        })
    for c in plan["low"]:
        items.append({
            "tag": f"아마존 · {c['competitor']}",
            "text": f"{c['product']} 재고가 낮아요. 품절로 바뀌면 아마존 비중을 50%까지 올리세요.",
            "tone": "calm",
        })
    cool = [r for r in plan["regions"] if not r["hot_days"]]
    if plan["hot_regions"] and cool:
        names = "·".join(r["name"] for r in cool)
        items.append({
            "tag": f"{names} · 7일",
            "text": f"{WEATHER_HOT_C}°C 미만 예보. 권역별 {weather_eur(min(r['week'] for r in cool))} 안팎 기본 금액으로 유지하세요.",
            "tone": "calm",
        })
    if not plan["hot_regions"]:
        items.insert(0, {
            "tag": "메타 · 4개 권역",
            "text": f"7일 동안 {WEATHER_HOT_C}°C 이상 예보가 없어요. 메타 {weather_eur(plan['meta'])}를 권역별로 고르게 운영하세요.",
            "tone": "calm",
        })
    return items
