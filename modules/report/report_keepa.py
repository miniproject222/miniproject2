# 1. 분석 리포트 - Keepa 연결 (Amazon.de 경쟁사 가격·평점·리뷰·재고)
# 토큰이 한정되어 있어 화면을 열 때는 조회하지 않고, 마지막 조회값(스냅샷)만 보여 줍니다.
# 새로 조회하려면 화면에서 조회 버튼 + 확인 PIN 입력이 필요하고, 사용량은 한도(budget) 안에서만 허용합니다.
# secrets.toml의 report 칸:
#   KEEPA_API_KEY = "..."      (Keepa API 키)
#   KEEPA_FETCH_PIN = "..."    (조회 확인용 PIN, 없으면 조회 버튼이 꺼짐)
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import median

import requests
import streamlit as st

REPORT_DATA_DIR = Path(__file__).resolve().parent / "data"
REPORT_KEEPA_ASIN_FILE = REPORT_DATA_DIR / "report_keepa_asin_202610.json"
REPORT_KEEPA_SNAPSHOT_FILE = REPORT_DATA_DIR / "report_keepa_snapshot.json"
REPORT_KEEPA_USAGE_FILE = REPORT_DATA_DIR / "report_keepa_usage.json"
REPORT_KEEPA_DETAIL_FILE = REPORT_DATA_DIR / "report_keepa_detail_202610.json"   # 하위 카테고리 순위·여름 순위·리뷰 추이 (2026-10-24 조회)
REPORT_KEEPA_DOMAIN = 3            # Amazon.de
REPORT_KEEPA_STATS_DAYS = 90       # 평균 가격 비교 기간
REPORT_KEEPA_TOKENS_PER_PRODUCT = 2   # 예상치: 상품 1토큰 + 평점·리뷰 최대 1토큰
REPORT_KEEPA_AUTO_DAILY_MAX = 10      # 아침 자동 갱신 하루 최대 토큰 (넘으면 자동 갱신 안 함)
# Keepa 가격 배열 순서: 0 Amazon 직판, 1 신품(마켓플레이스), 3 판매 순위, 16 평점(x10), 17 리뷰 수, 18 바이박스(배송비 포함)
REPORT_KEEPA_PRICE_ORDER = (18, 1, 0)
# 검색어 클릭 분석 기간 (report_sqp.py): 이 기간의 주별 할인·품절을 가격 이력에서 찾아 스냅샷에 같이 저장합니다
REPORT_KEEPA_EVENT_START = date(2026, 6, 1)
REPORT_KEEPA_EVENT_WEEKS = 13
REPORT_KEEPA_EVENT_DROP = 0.10


def report_keepa_secret(name):
    try:
        return st.secrets.get(name) or ""
    except Exception:   # secrets.toml이 없거나 형식 오류일 때
        return ""


def report_keepa_products(brands=None):
    """조회할 경쟁사 상품 목록 (브랜드, ASIN, 사이즈). brands가 있으면 그 브랜드만 (대시보드 상위 경쟁사만 조회해 토큰 절약)."""
    products = json.loads(REPORT_KEEPA_ASIN_FILE.read_text(encoding="utf-8"))["products"]
    return [p for p in products if not brands or p["db_brand"] in brands]


def report_keepa_top_brands():
    """대시보드에 보여 주는 경쟁사(경쟁사 DB 판매 순위 상위) 브랜드. 이 브랜드만 Keepa로 조회합니다."""
    from modules.report.report_competitor import REPORT_SEORI_PROXY, report_competitor_load
    return [r["brand"] for r in report_competitor_load() if r["kind"] != "자사"] + [REPORT_SEORI_PROXY]


def report_keepa_snapshot():
    """마지막 조회값. 없으면 None."""
    if not REPORT_KEEPA_SNAPSHOT_FILE.exists():
        return None
    return json.loads(REPORT_KEEPA_SNAPSHOT_FILE.read_text(encoding="utf-8"))


def report_keepa_detail():
    """냉감패드 실적 상세 (ASIN별 하위 카테고리 순위, 여름 순위, 판매 신호, 리뷰 1년 변화). 없으면 {}."""
    if not REPORT_KEEPA_DETAIL_FILE.exists():
        return {}
    return json.loads(REPORT_KEEPA_DETAIL_FILE.read_text(encoding="utf-8"))


def report_keepa_usage():
    return json.loads(REPORT_KEEPA_USAGE_FILE.read_text(encoding="utf-8"))


def report_keepa_estimate():
    """다음 조회의 예상 토큰 수."""
    return len(report_keepa_products(report_keepa_top_brands())) * REPORT_KEEPA_TOKENS_PER_PRODUCT


def report_keepa_can_fetch():
    """조회 가능 여부와 이유. (가능, 메시지)"""
    usage = report_keepa_usage()
    left = usage["budget"] - usage["used"]
    if not report_keepa_secret("KEEPA_API_KEY"):
        return False, "Keepa 키가 없습니다 (secrets의 KEEPA_API_KEY)."
    if not report_keepa_secret("KEEPA_FETCH_PIN"):
        return False, "조회 확인용 PIN이 없어 조회를 막았습니다 (secrets의 KEEPA_FETCH_PIN)."
    if report_keepa_estimate() > left:
        return False, f"남은 한도 {left}토큰이 예상 사용량 {report_keepa_estimate()}토큰보다 적습니다."
    return True, ""


def report_keepa_fetch_and_save(pin):
    """PIN이 맞을 때만 Keepa를 1회 조회하고, 스냅샷과 사용량을 저장합니다. 사용한 토큰 수를 돌려줍니다."""
    ok, reason = report_keepa_can_fetch()
    if not ok:
        raise RuntimeError(reason)
    if pin != report_keepa_secret("KEEPA_FETCH_PIN"):
        raise RuntimeError("PIN이 맞지 않습니다.")

    asins = [p["asin"] for p in report_keepa_products(report_keepa_top_brands())]
    return report_keepa_save(report_keepa_request(asins), asins, "경쟁사 상품 조회 (화면 버튼)")


def report_keepa_request(asins):
    """Keepa 상품 조회 1회 (가격·평점·리뷰 + 순위·리뷰·구매 배지 기록). 응답 본문을 돌려줍니다."""
    # 오류 문구에 요청 주소(키 포함)가 들어가지 않도록, 원래 오류 대신 짧은 메시지로 바꿉니다
    try:
        resp = requests.get("https://api.keepa.com/product", timeout=30, params={
            "key": report_keepa_secret("KEEPA_API_KEY"), "domain": REPORT_KEEPA_DOMAIN,
            "asin": ",".join(asins), "stats": REPORT_KEEPA_STATS_DAYS, "rating": 1, "history": 1,
        })
    except requests.RequestException as err:
        raise RuntimeError(f"Keepa 연결 오류 ({type(err).__name__})") from None
    if resp.status_code != 200:
        raise RuntimeError(f"Keepa 응답 오류 (HTTP {resp.status_code})")
    body = resp.json()
    if body.get("error"):
        raise RuntimeError(body["error"].get("message", "Keepa 오류"))
    return body


def report_keepa_save(body, asins, what, auto_day=None):
    """조회 결과를 스냅샷(합치기)·상세(구매 배지·판매 신호·리뷰·순위)·사용량에 저장하고, 사용한 토큰 수를 돌려줍니다."""
    used = int(body.get("tokensConsumed") or report_keepa_estimate())
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    brands = {p["asin"]: p["db_brand"] for p in report_keepa_products()}
    snapshot = report_keepa_snapshot() or {"items": {}}
    detail = report_keepa_detail() or {"items": {}}
    for p in body.get("products") or []:
        snapshot["items"][p["asin"]] = {**report_keepa_parse(p), "events": report_keepa_events(p, brands.get(p["asin"], p["asin"]))}
        if p["asin"] in detail.get("items", {}):
            report_keepa_detail_update(detail["items"][p["asin"]], p)
    snapshot.update({"fetched_at": now, "tokens_left": body.get("tokensLeft")})
    if auto_day:
        snapshot["auto_day"] = auto_day   # 아침 자동 갱신을 한 날 (하루 1번)
    REPORT_KEEPA_SNAPSHOT_FILE.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if detail.get("items"):
        REPORT_KEEPA_DETAIL_FILE.write_text(json.dumps(detail, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    usage = report_keepa_usage()
    usage["used"] += used
    usage["log"].append({"date": now, "tokens": used, "what": f"{what}: 상품 {len(asins)}개"})
    REPORT_KEEPA_USAGE_FILE.write_text(json.dumps(usage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return used


def report_keepa_detail_update(item, product):
    """상세 항목의 '지금 값'만 새로 고침: 현재 순위, 1년 판매 신호, 월 구매 배지, 리뷰·평점, 현재가.
    여름 순위·작년 가격 같은 기준값은 그대로 둡니다 (같은 사이즈 비교 가격 basis가 있으면 가격도 그대로)."""
    def t(km):
        return (datetime(2011, 1, 1) + timedelta(minutes=int(km))).date()

    stats = product.get("stats") or {}
    root = (product.get("salesRanks") or {}).get(str(product.get("salesRankReference"))) or []
    if len(root) >= 2 and root[-1] > 0:
        item["rank_root_now"] = root[-1]
    item["rank_drops"] = {k: stats.get(f"salesRankDrops{k}") for k in ("30", "90", "180", "365")}
    ms = product.get("monthlySoldHistory") or []
    item["monthly_sold"] = [{"from": str(t(ms[i])), "badge": ms[i + 1]} for i in range(0, len(ms) - 1, 2) if ms[i + 1] > 0]
    parsed = report_keepa_parse(product)
    if parsed["reviews"] is not None:
        item["reviews_now"] = parsed["reviews"]
    if parsed["rating"]:
        item["rating_now"] = parsed["rating"]
    if parsed["price"] and not (item.get("price") or {}).get("basis"):
        item.setdefault("price", {})["now"] = parsed["price"]
    item["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")


def report_keepa_auto_daily():
    """아침 자동 갱신: secrets의 KEEPA_AUTO_DAILY가 on일 때만, 하루 1번(한국 08:00 이후 첫 접속) 경쟁사 3곳을 조회.
    (켜는 것 = 사용자의 자동 조회 승인) 결과 문구를 돌려줍니다. 화면이 멈추지 않도록 오류는 문구로만 돌려줍니다."""
    if str(report_keepa_secret("KEEPA_AUTO_DAILY")).strip().lower() not in ("on", "true", "1", "yes"):
        return "아침 자동 갱신 꺼짐 (secrets의 KEEPA_AUTO_DAILY = \"on\"으로 켬)"
    from modules.report.report_ab import report_ab_day   # 아침 기준일 (08:00 전이면 전날)
    day = report_ab_day()
    # 창 두 개가 동시에 열려도 한 번만 조회 (2026-10-26 17:37에 동시 접속으로 두 번 조회돼 12토큰 사용) - 잠근 뒤 다시 확인
    with report_keepa_auto_lock():
        return _report_keepa_auto_daily_locked(day)


@st.cache_resource
def report_keepa_auto_lock():
    """아침 자동 갱신용 잠금 (앱 서버 하나에 하나)."""
    import threading
    return threading.Lock()


def _report_keepa_auto_daily_locked(day):
    snap = report_keepa_snapshot() or {}
    if snap.get("auto_day") == day:
        return f"아침 자동 갱신 완료 ({snap.get('fetched_at', day)})"
    usage = report_keepa_usage()
    est = report_keepa_estimate()
    if not report_keepa_secret("KEEPA_API_KEY"):
        return "아침 자동 갱신 불가: Keepa 키 없음"
    if est > REPORT_KEEPA_AUTO_DAILY_MAX or est > usage["budget"] - usage["used"]:
        return f"아침 자동 갱신 안 함: 예상 {est}토큰 (하루 최대 {REPORT_KEEPA_AUTO_DAILY_MAX}, 남은 한도 {usage['budget'] - usage['used']})"
    asins = [p["asin"] for p in report_keepa_products(report_keepa_top_brands())]
    try:
        used = report_keepa_save(report_keepa_request(asins), asins, "아침 자동 갱신", auto_day=day)
    except RuntimeError as err:
        return f"아침 자동 갱신 실패: {err}"
    return f"아침 자동 갱신 완료 ({used}토큰)"


def report_keepa_events(product, brand):
    """가격 이력(신품 가격)에서 검색어 분석 기간의 주별 할인(주 최저가가 기간 중앙값보다 10% 이상 낮음)·품절 주를 찾습니다.
    Keepa 시간은 2011-01-01부터 지난 분 단위입니다. 쿠폰은 가격 이력에 없어서 할인으로만 잡힙니다."""
    history = (product.get("csv") or [])[1:2]
    if not history or not history[0]:
        return []
    points = [(datetime(2011, 1, 1) + timedelta(minutes=t), v) for t, v in zip(history[0][::2], history[0][1::2])]
    weeks = [REPORT_KEEPA_EVENT_START + timedelta(weeks=i) for i in range(REPORT_KEEPA_EVENT_WEEKS)]
    by_week = {}
    for w in weeks:
        before = [v for t, v in points if t.date() < w]
        inside = [v for t, v in points if w <= t.date() < w + timedelta(days=7)]
        by_week[w] = inside + before[-1:]          # 그 주에 바뀐 값 + 그 주 시작 때 값
    prices = [v for vals in by_week.values() for v in vals if v > 0]
    if not prices:
        return []
    base = median(prices)
    out = []
    for w, vals in by_week.items():
        if any(v < 0 for v in vals):
            out.append({"week": w.isoformat(), "brand": brand, "kind": "품절", "detail": "Amazon.de 오퍼 없음 (Keepa)"})
        elif vals and min(vals) <= base * (1 - REPORT_KEEPA_EVENT_DROP):
            out.append({"week": w.isoformat(), "brand": brand, "kind": "할인",
                        "detail": f"€{min(vals) / 100:.2f} (기간 중앙값 €{base / 100:.2f}, Keepa)"})
    return out


def report_keepa_parse(product):
    """Keepa 상품 1개를 화면용 값으로 바꿉니다. 가격은 센트 단위, -1은 판매 없음(품절)."""
    stats = product.get("stats") or {}
    cur, avg = stats.get("current") or [], stats.get("avg90") or stats.get("avg") or []

    def pick(arr, idx):
        return arr[idx] if len(arr) > idx and arr[idx] is not None and arr[idx] >= 0 else None

    price_idx = next((i for i in REPORT_KEEPA_PRICE_ORDER if pick(cur, i)), None)
    price = pick(cur, price_idx) / 100 if price_idx is not None else None
    avg_price = pick(avg, price_idx) / 100 if price_idx is not None and pick(avg, price_idx) else None
    rating = pick(cur, 16)
    return {
        "title": product.get("title") or "",
        "price": price,                                   # 현재가 (€), None = 판매 없음
        "avg90": avg_price,                               # 90일 평균가 (€)
        "change": price / avg_price - 1 if price and avg_price else None,
        "rating": rating / 10 if rating else None,        # 평점 (5점 만점)
        "reviews": pick(cur, 17),                         # 리뷰 수
        "rank": pick(cur, 3),                             # 카테고리 판매 순위
        "in_stock": price is not None,
    }


@st.cache_data(show_spinner=False)
def report_keepa_health(day: str) -> dict:
    """하루 한 번 Keepa API 키·연결 확인 (day가 바뀌면 다시 확인). 토큰 상태 조회(/token)는 토큰을 쓰지 않습니다.
    돌려주는 값: {ok, checked, tokens_left, refill_in, message}. 오류 문구에 키가 들어가지 않게 짧은 메시지만."""
    key = report_keepa_secret("KEEPA_API_KEY")
    checked = datetime.now().strftime("%Y-%m-%d %H:%M")
    if not key:
        return {"ok": False, "checked": checked, "tokens_left": None, "refill_in": None, "message": "Keepa 키가 없음 (secrets의 KEEPA_API_KEY)"}
    try:
        resp = requests.get("https://api.keepa.com/token", params={"key": key}, timeout=15)
    except requests.RequestException as err:
        return {"ok": False, "checked": checked, "tokens_left": None, "refill_in": None, "message": f"연결 오류 ({type(err).__name__})"}
    if resp.status_code != 200:
        return {"ok": False, "checked": checked, "tokens_left": None, "refill_in": None, "message": f"응답 오류 (HTTP {resp.status_code})"}
    body = resp.json()
    if body.get("error"):
        return {"ok": False, "checked": checked, "tokens_left": None, "refill_in": None,
                "message": str((body.get("error") or {}).get("message") or "Keepa 오류")[:80]}
    return {"ok": True, "checked": checked, "tokens_left": body.get("tokensLeft"),
            "refill_in": body.get("refillIn"), "message": "정상"}


def report_keepa_health_text(health: dict) -> str:
    """'Keepa 연결 확인 10/26 09:00 · 정상 (남은 토큰 N)' 한 줄."""
    when = str(health.get("checked") or "")[5:].replace("-", "/")
    if health.get("ok"):
        left = health.get("tokens_left")
        return f"Keepa 연결 확인 {when} · 정상" + (f" (남은 토큰 {left:,})" if isinstance(left, int) else "")
    return f"Keepa 연결 확인 {when} · 문제 있음: {health.get('message')}"

