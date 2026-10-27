# 홈(관제실)이 다른 탭에서 읽어 오는 데이터, 폭염경보 판단, "지금 할 일" 알림 규칙
# 다른 탭이 아직 구현 전이면 HOME_DEMO(샘플 데이터)로 채우고 화면에 "샘플"이라고 표시합니다.
# 각 탭이 store_set()으로 저장하면 그 값이 샘플 대신 자동으로 쓰입니다.
#
# 홈이 읽는 store 데이터 모양 (각 탭 담당자와 맞춘 약속, 바뀌면 home 담당에게 알려 주세요)
#   store_get("report") = {
#       "yesterday_sales": 1284.0, "sales_delta": -0.18,                  # 전날 매출(€), 전일 대비 증감(비율)
#       "sales_7d": [1180, ...],                                          # 최근 7일 매출 (오래된 날 → 어제)
#       "kpi": {"ctr": 2.4, "ctr_delta": -0.6, "cvr": 1.6, "cvr_delta": -0.4, "spend": 840},   # 클릭률·전환율(%), 변화(%p), 광고비(€)
#       "ab_test": {"name": "...", "a": {"ctr": 3.4, "cvr": 2.1}, "b": {"ctr": 2.4, "cvr": 1.5}, "summary": "..."},
#       "problems": [{"title": "...", "type": "내부", "detail": "..."}]}
#   store_get("hypothesis") = {"hypothesis": "..."}
#   store_get("media")      = {"results": [...], "solutions": [...]}   # 광고 소재 결과 + 솔루션 제안 (solution 모듈을 media로 합침)
#   store_get("weather")    = {"ad_multiplier": 2.0, "reason": "...",
#                              "alerts": [{"level": "high", "text": "...", "detail": "..."}]}   # level: high(팝업) / info
from common.common_store import store_get
from modules.home.home_globe import home_sample_daily

# 작업 단계 (모듈 코드 순서 = 왼쪽 탭 순서)
HOME_STEPS = ["report", "hypothesis", "media", "weather"]
HOME_HEAT_WARN = 33   # 폭염경보 기준 (°C, 오늘 또는 내일 최고)
HOME_HEAT_TEMP = 30   # 더위 주의 기준 (°C)
HOME_WHEN_RANK = {"지금": 0, "오늘": 1, "이번 주": 2}   # 할 일 정렬: 급한 것부터

# 다른 탭 구현 전까지 보여 줄 샘플 데이터 (가정값)
HOME_DEMO = {
    "report": {
        "yesterday_sales": 1284.0,
        "sales_delta": -0.18,
        "sales_7d": [1180, 1240, 1310, 1495, 1620, 1566, 1284],
        "kpi": {"ctr": 2.4, "ctr_delta": -0.6, "cvr": 1.6, "cvr_delta": -0.4, "spend": 840},
        "ab_test": {
            "name": "메타 광고 소재 A/B",
            "a": {"label": "A안 · 시원함 강조", "ctr": 3.5, "cvr": 2.1},
            "b": {"label": "B안 · 가격 강조", "ctr": 2.45, "cvr": 1.5},
            "summary": "B안은 클릭률이 낮고 구매 전환도 낮음. 원인 후보: 가격 표시 방식, 소재 거부감",
        },
        "problems": [
            {"title": "B안 전환율 하락", "type": "내부", "detail": "가격을 앞세운 B안이 A안보다 전환율이 29% 낮습니다."},
            {"title": "경쟁사 가격 인하", "type": "외부", "detail": "경쟁사 B가 냉감패드 가격을 €39 → €29로 내렸습니다 (3일 전)."},
            {"title": "배송 지연 리뷰", "type": "내부", "detail": "최근 7일 부정 리뷰 12건 중 7건이 배송 지연을 언급했습니다."},
        ],
    },
    "hypothesis": {"hypothesis": "합성인데도 통기성 시험을 통과했다는 점을 보여 주면 전환율이 오른다"},
    "weather": {
        "ad_multiplier": 2.0,
        "reason": "폭염 예보 + 경쟁사 품절",
        "alerts": [
            {"level": "high", "text": "경쟁사 A 아마존 품절",
             "detail": "Amazon.de 냉감패드 판매 1위 경쟁사의 재고가 없습니다 (2시간 전 감지). 메타·아마존 광고 노출을 2배로 늘릴 기회예요."},
        ],
    },
}

# 시연용 폭염 시나리오 (주소 끝에 ?scenario=heat 를 붙이면 실제 기온 대신 사용)
HOME_HEAT_SCENARIO = {
    "Hamburg": (27, 28, 29, 31), "Berlin": (31, 33, 34, 35), "Köln": (30, 31, 32, 33), "Dresden": (32, 34, 35, 35),
    "Frankfurt": (31, 32, 33, 34), "Stuttgart": (30, 31, 32, 33), "München": (29, 30, 31, 32),
}   # 도시: (현재, 체감, 내일 최고, 이번 주 최고)


def home_heat_scenario(temps):
    """실제 기온 목록을 시연용 폭염 값으로 바꿈"""
    out = []
    for p in temps:
        now, feels, tomorrow, week = HOME_HEAT_SCENARIO.get(p["city"], (p["temp"],) * 4)
        daily = home_sample_daily([now, tomorrow, (tomorrow + week) / 2, week - 1, week, week - 1, (tomorrow + week) / 2])
        out.append({**p, "temp": float(now), "feels": float(feels), "tomorrow": float(tomorrow),
                    "week_max": float(week), "week_day": daily[4]["day"], "daily": daily})
    return out


# 지역별 광고 비중: ④ 광고 타이밍과 같은 규칙(weather_data.weather_build_plan)을 홈 도시 예보로 계산
#   60%는 4개 지역에 똑같이, 40%는 30°C 이상 예보일에 (최고기온 - 29)점 비례로 추가. 30°C 이상 예보가 없으면 4개 지역 똑같이.
# ④는 지역별 비중을 store에 저장하지 않아(배수·근거·알림·날짜별 아마존 예산만 저장) 홈이 같은 규칙으로 계산합니다.
# ④ 지역(3개 도시 평균) 대신 홈 지도의 권역 대표 도시 1곳씩 씀 (home_globe.HOME_CITIES)
HOME_REGIONS = [("북부", ["Hamburg"]), ("서부", ["Köln"]), ("동부", ["Berlin"]), ("남부", ["München"])]
HOME_HEAT_POOL = 0.40


def home_region_shares(temps):
    """[{"name", "share"(%), "max7", "hot_days"}] (비중 큰 순) + 30°C 이상 예보가 있었는지"""
    by_city = {p["city"]: p for p in temps}
    rows = []
    for name, cities in HOME_REGIONS:
        days = [[d["max"] for d in (by_city[c].get("daily") or [])][:7] for c in cities if c in by_city]
        days = [d for d in days if d]
        if not days:
            continue
        tmax = [sum(col) / len(col) for col in zip(*days)]   # 지역 기온 = 도시 평균
        points = sum(max(0.0, t - (HOME_HEAT_TEMP - 1)) for t in tmax)
        rows.append({"name": name, "points": points, "max7": max(tmax), "hot_days": sum(1 for t in tmax if t >= HOME_HEAT_TEMP)})
    total = sum(r["points"] for r in rows)
    pool = HOME_HEAT_POOL if total else 0
    for r in rows:
        r["share"] = ((1 - pool) / len(rows) + (pool * r["points"] / total if total else 0)) * 100
    return sorted(rows, key=lambda r: -r["share"]), bool(total)


def home_city_warning(p):
    """도시별 경보: ("폭염경보" / "더위 주의" / "", 기준 기온)"""
    peak = max(p["temp"], p.get("tomorrow", p["temp"]))
    if peak >= HOME_HEAT_WARN:
        return "폭염경보", peak
    if peak >= HOME_HEAT_TEMP:
        return "더위 주의", peak
    return "", peak


def home_read_stores():
    """({모듈코드: dict 또는 None}, 샘플로 채운 모듈코드 set)"""
    stores, demo = {}, set()
    for code in HOME_STEPS:
        value = store_get(code)
        # ④ 광고 타이밍은 이제 실제 값을 저장하므로 샘플(가짜 '경쟁사 A 품절' 알림)을 쓰지 않음.
        # 홈이 ④보다 먼저 그려져 첫 화면에서 아직 저장 전이면, 광고 배수는 홈의 기온 규칙으로 대신함 (home_ad_multiplier)
        if not value and code in HOME_DEMO and code != "weather":
            value = HOME_DEMO[code]
            demo.add(code)
        stores[code] = value
    return stores, demo


def home_ad_multiplier(stores, temps):
    """광고 빈도 추천 (배수, 근거, ④ 값 여부). ④ 광고 타이밍 탭이 저장한 값이 있으면 그 값을 씀"""
    weather = stores.get("weather") or {}
    if weather.get("ad_multiplier"):
        return float(weather["ad_multiplier"]), weather.get("reason", ""), True
    # 연결 전 임시 규칙: 가장 더운 도시의 오늘·내일 최고 기온 기준
    hottest = max(temps, key=lambda p: home_city_warning(p)[1])
    level, peak = home_city_warning(hottest)
    mult = 1.5 if level == "폭염경보" else 1.2 if level else 1.0
    return mult, f"{hottest['city']} 최고 {peak:.0f}°C", False


def home_todos(stores, temps):
    """지금 할 일 [{"level", "when": 지금/오늘/이번 주, "title", "detail", "goto": 모듈코드, "action": 버튼 글자,
                   "next": 끝나면 이어지는 일}] (급한 것 먼저)"""
    todos = []
    report = stores.get("report") or {}

    # ① 문제 분석 핵심 요약 (맨 위): ① 탭이 '다음으로'로 저장한 1·2순위를 간략히
    keys = [k for k in (report.get("key_problems") or []) if isinstance(k, dict) and k.get("title")]
    if not report.get("version"):
        # ① 탭이 아직 저장 전 (샘플 report) → 샘플 A/B·매출 할 일 대신 ① 먼저 하라는 할 일만
        todos.append({"slot": "report", "level": "high", "when": "지금", "title": "① 1순위 · 문제 분석 결과가 아직 없어요",
                      "detail": "① 문제 분석 탭에서 '불러오기' → '다음으로'를 누르면 핵심 문제 1·2순위가 여기에 나와요.",
                      "goto": "report", "action": "문제 분석 하러 가기", "next": "저장하면 ② 가설 세우기로"})
        report = {}
    if keys and report:
        first = keys[0]
        second = f" · 2순위: {keys[1]['title']}" if len(keys) > 1 else ""
        todos.append({"slot": "report", "level": "high", "when": "지금",
                      "title": f"① 1순위 · {first.get('type', '')} | {first['title']}",
                      "detail": f"{str(first.get('detail', ''))[:90]}{'…' if len(str(first.get('detail', ''))) > 90 else ''}{second}",
                      "goto": "report", "action": "문제 분석 보기", "next": "확인 후 ② 가설 세우기로"})

    # ① A/B 테스트 결과
    ab = report.get("ab_test") or {}
    a, b = ab.get("a") or {}, ab.get("b") or {}
    if a.get("ctr") and b.get("ctr"):
        gap = (b["ctr"] - a["ctr"]) / a["ctr"]
        if abs(gap) >= 0.1:
            worse, better = ("B안", "A안") if gap < 0 else ("A안", "B안")
            todos.append({"level": "high", "title": f"{worse} 광고 클릭률이 {better}보다 {abs(gap) * 100:.0f}% 낮아요",
                          "detail": ab.get("summary", ""), "goto": "report", "action": "원인 분석 보기",
                          "when": "오늘", "next": "원인을 찾으면 ② 가설 세우기로"})

    # ① 매출 하락
    delta = report.get("sales_delta")
    if delta is not None and delta <= -0.1:
        todos.append({"level": "info", "title": f"전날 매출 {abs(delta) * 100:.0f}% 하락",
                      "detail": "내부 요인(우리 광고)과 외부 요인(경쟁사, 날씨)을 나눠서 확인하세요.",
                      "goto": "report", "action": "원인 분석 보기",
                      "when": "오늘", "next": "원인을 찾으면 ② 가설 세우기로"})

    # 날씨: 이번 주 폭염 예보 (실시간 예보 기준)
    week_hot = sorted((p for p in temps if p.get("week_max", p["temp"]) >= HOME_HEAT_TEMP), key=lambda p: -p.get("week_max", 0))
    if week_hot:
        top = week_hot[0]
        names = ", ".join(p["city"] for p in week_hot[:3])
        todos.append({"level": "high", "title": f"이번 주 폭염 예보 ({top['city']} {top.get('week_day', '')} {top['week_max']:.0f}°C)",
                      "detail": f"{names} 등 {len(week_hot)}개 도시가 30°C를 넘을 예정이에요. 냉감 제품 검색이 늘어나는 시점이라 광고 빈도를 미리 조정하세요.",
                      "goto": "weather", "action": "광고 빈도 조정 보기",
                      "when": "이번 주", "next": "폭염 전에 광고 빈도를 올려 두기"})

    # ④ 광고 타이밍 탭 알림 (첫 알림 = 아래 큰 카드)
    alerts = [w for w in (stores.get("weather") or {}).get("alerts", []) if isinstance(w, dict)]
    for i, w in enumerate(alerts):
        level = w.get("level", "info")
        todos.append({"slot": "weather" if i == 0 else None, "level": level, "title": w.get("text", ""), "detail": w.get("detail", ""),
                      "goto": "weather", "action": "광고 타이밍 보기",
                      "when": w.get("when", "지금" if level == "high" else "오늘"), "next": "광고 노출을 늘리면 결과는 ① 문제 분석으로"})
    if not alerts:
        todos.append({"slot": "weather", "level": "info", "when": "오늘", "title": "④ 광고 타이밍 · 날씨 분석 결과가 아직 없어요",
                      "detail": "④ 광고 타이밍 탭을 열면 독일 4개 권역 예보로 이번 주 아마존 예산 추천이 여기에 나와요.",
                      "goto": "weather", "action": "광고 타이밍 보기", "next": "예산을 정하면 ① 문제 분석으로 결과 확인"})

    # 정렬: 위 ① 핵심 요약, 아래 ④ 날씨 알림 (큰 카드 2개), 나머지는 급한 순 (같으면 넣은 순서 유지)
    slot_rank = {"report": 0, "weather": 1}
    return sorted(todos, key=lambda t: (slot_rank.get(t.get("slot"), 2),
                                         HOME_WHEN_RANK.get(t["when"], 9), t["level"] != "high"))
