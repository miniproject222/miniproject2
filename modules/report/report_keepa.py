# 1. 분석 리포트 - Keepa 연결 (Amazon.de 경쟁사 가격·평점·리뷰·재고)
# 토큰이 한정되어 있어 화면을 열 때는 조회하지 않고, 마지막 조회값(스냅샷)만 보여 줍니다.
# 새로 조회하려면 화면에서 조회 버튼 + 확인 PIN 입력이 필요하고, 사용량은 한도(budget) 안에서만 허용합니다.
# secrets.toml의 report 칸:
#   KEEPA_API_KEY = "..."      (Keepa API 키)
#   KEEPA_FETCH_PIN = "..."    (조회 확인용 PIN, 없으면 조회 버튼이 꺼짐)
import json
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st

REPORT_DATA_DIR = Path(__file__).resolve().parent / "data"
REPORT_KEEPA_ASIN_FILE = REPORT_DATA_DIR / "report_keepa_asin_202610.json"
REPORT_KEEPA_SNAPSHOT_FILE = REPORT_DATA_DIR / "report_keepa_snapshot.json"
REPORT_KEEPA_USAGE_FILE = REPORT_DATA_DIR / "report_keepa_usage.json"
REPORT_KEEPA_DOMAIN = 3            # Amazon.de
REPORT_KEEPA_STATS_DAYS = 90       # 평균 가격 비교 기간
REPORT_KEEPA_TOKENS_PER_PRODUCT = 2   # 예상치: 상품 1토큰 + 평점·리뷰 최대 1토큰
# Keepa 가격 배열 순서: 0 Amazon 직판, 1 신품(마켓플레이스), 3 판매 순위, 16 평점(x10), 17 리뷰 수, 18 바이박스(배송비 포함)
REPORT_KEEPA_PRICE_ORDER = (18, 1, 0)


def report_keepa_secret(name):
    try:
        return st.secrets.get(name) or ""
    except Exception:   # secrets.toml이 없거나 형식 오류일 때
        return ""


def report_keepa_products():
    """조회할 경쟁사 상품 목록 (브랜드, ASIN, 사이즈)."""
    return json.loads(REPORT_KEEPA_ASIN_FILE.read_text(encoding="utf-8"))["products"]


def report_keepa_snapshot():
    """마지막 조회값. 없으면 None."""
    if not REPORT_KEEPA_SNAPSHOT_FILE.exists():
        return None
    return json.loads(REPORT_KEEPA_SNAPSHOT_FILE.read_text(encoding="utf-8"))


def report_keepa_usage():
    return json.loads(REPORT_KEEPA_USAGE_FILE.read_text(encoding="utf-8"))


def report_keepa_estimate():
    """다음 조회의 예상 토큰 수."""
    return len(report_keepa_products()) * REPORT_KEEPA_TOKENS_PER_PRODUCT


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

    asins = [p["asin"] for p in report_keepa_products()]
    # 오류 문구에 요청 주소(키 포함)가 들어가지 않도록, 원래 오류 대신 짧은 메시지로 바꿉니다
    try:
        resp = requests.get("https://api.keepa.com/product", timeout=30, params={
            "key": report_keepa_secret("KEEPA_API_KEY"), "domain": REPORT_KEEPA_DOMAIN,
            "asin": ",".join(asins), "stats": REPORT_KEEPA_STATS_DAYS, "rating": 1,
        })
    except requests.RequestException as err:
        raise RuntimeError(f"Keepa 연결 오류 ({type(err).__name__})") from None
    if resp.status_code != 200:
        raise RuntimeError(f"Keepa 응답 오류 (HTTP {resp.status_code})")
    body = resp.json()
    if body.get("error"):
        raise RuntimeError(body["error"].get("message", "Keepa 오류"))

    used = int(body.get("tokensConsumed") or report_keepa_estimate())
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    snapshot = {"fetched_at": now, "tokens_left": body.get("tokensLeft"),
                "items": {p["asin"]: report_keepa_parse(p) for p in body.get("products") or []}}
    REPORT_KEEPA_SNAPSHOT_FILE.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    usage = report_keepa_usage()
    usage["used"] += used
    usage["log"].append({"date": now, "tokens": used, "what": f"경쟁사 상품 {len(asins)}개 조회 (화면 버튼)"})
    REPORT_KEEPA_USAGE_FILE.write_text(json.dumps(usage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return used


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
