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
#   store_get("media")      = {"results": [...]}
#   store_get("solution")   = {"solutions": [...]}
#   store_get("weather")    = {"ad_multiplier": 2.0, "reason": "...",
#                              "alerts": [{"level": "high", "text": "...", "detail": "..."}]}   # level: high(팝업) / info
from common.common_store import store_get

# 작업 단계 (모듈 코드 순서 = 왼쪽 탭 순서)
HOME_STEPS = ["report", "hypothesis", "media", "solution", "weather"]
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
        out.append({**p, "temp": float(now), "feels": float(feels), "tomorrow": float(tomorrow),
                    "week_max": float(week), "week_day": "토"})
    return out


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
        if not value and code in HOME_DEMO:
            value = HOME_DEMO[code]
            demo.add(code)
        stores[code] = value
    return stores, demo


def home_ad_multiplier(stores, temps):
    """광고 빈도 추천 (배수, 근거, ④ 값 여부). 날씨·광고 빈도 탭이 저장한 값이 있으면 그 값을 씀"""
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

    # ④ 날씨·광고 빈도 탭 알림
    for w in (stores.get("weather") or {}).get("alerts", []):
        level = w.get("level", "info")
        todos.append({"level": level, "title": w.get("text", ""), "detail": w.get("detail", ""),
                      "goto": "weather", "action": "광고 빈도 조정 보기",
                      "when": w.get("when", "지금" if level == "high" else "오늘"), "next": "광고 노출을 늘리면 결과는 ① 문제 분석으로"})

    return sorted(todos, key=lambda t: (HOME_WHEN_RANK.get(t["when"], 9), t["level"] != "high"))
