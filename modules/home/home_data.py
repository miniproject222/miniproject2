# 홈이 다른 탭에서 읽어 오는 데이터와 알림 규칙
# 다른 탭이 아직 구현 전이면 HOME_DEMO(샘플 데이터)로 채우고 화면에 "샘플"이라고 표시합니다.
# 각 탭이 store_set()으로 저장하면 그 값이 샘플 대신 자동으로 쓰입니다.
#
# 홈이 읽는 store 데이터 모양 (각 탭 담당자와 맞춘 약속, 바뀌면 home 담당에게 알려 주세요)
#   store_get("report")  = {"yesterday_sales": 1284.0, "sales_delta": -0.18,         # 전날 매출(€), 전일 대비 증감(비율)
#                           "sales_7d": [1180, ...],                                 # 최근 7일 매출 (오래된 날 → 어제)
#                           "problems": [{"title": "...", "type": "내부", "detail": "..."}]}
#   store_get("hypothesis") = {"hypothesis": "..."}
#   store_get("media")      = {"results": [...], "solutions": [...]}   # 매체 결과 + 솔루션 제안 (solution 모듈을 media로 합침)
#   store_get("weather")    = {"ad_multiplier": 1.8, "reason": "...",
#                              "alerts": [{"level": "high", "text": "...", "detail": "..."}]}   # level: high(팝업) / info
from common.common_store import store_get

# 작업 단계 (왼쪽 탭 순서와 같게)
HOME_STEPS = [
    ("report", "① 문제 분석"),
    ("hypothesis", "② 가설 세우기"),
    ("media", "③ 광고 소재·솔루션"),
    ("weather", "④ 광고 타이밍"),
]
HOME_HEAT_TEMP = 30   # 폭염 기준 (°C)

# 다른 탭 구현 전까지 보여 줄 샘플 데이터 (가정값)
HOME_DEMO = {
    "report": {
        "yesterday_sales": 1284.0,
        "sales_delta": -0.18,
        "sales_7d": [1180, 1240, 1310, 1495, 1620, 1566, 1284],
        "problems": [
            {"title": "장바구니 이탈 증가", "type": "내부", "detail": "결제 단계 이탈률 68% (+9%p). 배송비가 마지막 단계에 보이는 것이 원인으로 추정됩니다."},
            {"title": "경쟁사 가격 인하", "type": "외부", "detail": "경쟁사 B가 냉감패드 가격을 €39 → €29로 내렸습니다 (3일 전)."},
            {"title": "배송 지연 리뷰", "type": "내부", "detail": "최근 7일 부정 리뷰 12건 중 7건이 배송 지연을 언급했습니다."},
        ],
    },
    "hypothesis": {"hypothesis": "배송비를 상품 페이지에서 먼저 보여 주면 결제 이탈이 줄어든다"},
    "weather": {
        "ad_multiplier": 1.8,
        "reason": "주말 폭염 예보 + 경쟁사 품절",
        "alerts": [
            {"level": "high", "text": "경쟁사 A 아마존 품절",
             "detail": "Amazon.de 냉감패드 판매 1위 경쟁사의 재고가 없습니다 (2시간 전 감지). 우리 광고 노출을 늘릴 기회예요."},
            {"level": "info", "text": "주말 30°C 이상 예보",
             "detail": "토·일 München, Stuttgart 최고 31~32°C 예보. 금요일부터 광고 빈도를 올리는 것을 추천합니다."},
        ],
    },
}


def home_read_stores():
    """({모듈코드: dict 또는 None}, 샘플로 채운 모듈코드 set)"""
    stores, demo = {}, set()
    for code, _ in HOME_STEPS:
        value = store_get(code)
        if not value and code in HOME_DEMO:
            value = HOME_DEMO[code]
            demo.add(code)
        stores[code] = value
    return stores, demo


def home_step_status(stores):
    """단계별 완료 여부 [(이름, 완료?)]"""
    return [(name, bool(stores.get(code))) for code, name in HOME_STEPS]


def home_ad_multiplier(stores, temps):
    """광고 빈도 추천 (배수, 근거, ④ 값 여부). ④ 광고 타이밍이 저장한 값이 있으면 그 값을 씀"""
    weather = stores.get("weather") or {}
    if weather.get("ad_multiplier"):
        return float(weather["ad_multiplier"]), weather.get("reason", ""), True
    # ④ 연결 전 임시 규칙: 가장 더운 도시 기온 기준
    hottest = max(temps, key=lambda p: p["temp"])
    if hottest["temp"] >= HOME_HEAT_TEMP:
        return 1.5, f"폭염 ({hottest['city']} {hottest['temp']:.0f}°C)", False
    if hottest["temp"] >= 27:
        return 1.2, f"더위 시작 ({hottest['city']} {hottest['temp']:.0f}°C)", False
    return 1.0, f"평년 기온 (최고 {hottest['city']} {hottest['temp']:.0f}°C)", False


def home_alerts(stores, temps):
    """알림 목록 [{"level", "text", "detail", "step"}] (중요한 것 먼저)"""
    alerts = []
    hot = sorted((p for p in temps if p["temp"] >= HOME_HEAT_TEMP), key=lambda p: -p["temp"])
    if hot:
        cities = ", ".join(f"{p['city']} {p['temp']:.0f}°" for p in hot[:3])
        alerts.append({"level": "high", "text": f"폭염: {cities}", "step": "④ 광고 타이밍",
                       "detail": f"30°C 이상 도시 {len(hot)}곳. 냉감 제품 검색이 늘어나는 시점이라 메타·아마존 광고 빈도를 올리는 것을 검토하세요."})

    report = stores.get("report") or {}
    delta = report.get("sales_delta")
    if delta is not None and delta <= -0.1:
        sales = report.get("yesterday_sales")
        before = f"€{sales / (1 + delta):,.0f} → €{sales:,.0f}. " if sales else ""
        alerts.append({"level": "high", "text": f"전날 매출 {abs(delta) * 100:.0f}% 하락", "step": "① 문제 분석",
                       "detail": f"{before}① 문제 분석에서 내부/외부 원인을 확인하세요."})

    for a in (stores.get("weather") or {}).get("alerts", []):
        alerts.append({"level": a.get("level", "info"), "text": a.get("text", ""), "detail": a.get("detail", ""),
                       "step": "④ 광고 타이밍"})

    return sorted(alerts, key=lambda a: a["level"] != "high")
