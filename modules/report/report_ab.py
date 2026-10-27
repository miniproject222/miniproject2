# 1. 분석 리포트 - 해결안 A/B 결과 아침 분석
# ③ 광고 소재(media) 탭이 store_set("media", {...})로 저장한 A/B 결과·UTM 성과를
# 매일 아침(한국 시간 08:00 이후 첫 접속) 한 번 읽어 분석하고, 전날 분석과 비교합니다.
# 결과는 store "report"의 ab_daily로 저장되어 그날 하루 동안 같은 값을 보여 줍니다.
#
# ③ 탭과 맞춘 값 (store "media"):
#   "ab_result": {"source", "period", "query", "market_ctr",
#                 "variants": [{"name", "desc", "impressions", "clicks", "sessions", "units"}, x2],
#                 "cac": {"before": {"label", "spend", "new_to_brand_orders", "sales"}, "after": {...}}}
#   "utm": [{"source", "medium", "campaign", "sessions", "orders", "revenue"}]
#   "updated_at": "2026-10-25 07:30"
import csv
import io
import math
from datetime import datetime, timedelta, timezone

from common.common_store import store_get

REPORT_AB_TZ = timezone(timedelta(hours=9))   # 한국 시간 (서머타임 없음)
REPORT_AB_MORNING_HOUR = 8                    # 이 시각 이후 첫 접속에서 그날 분석을 새로 만듭니다
REPORT_AB_CVR_TOLERANCE = 0.5                 # B의 구매 전환율이 A보다 이만큼(%p) 넘게 낮으면 실패 (③ 탭 판정 규칙과 같게)
REPORT_AB_HISTORY = 14                        # 지난 분석 보관 일수


REPORT_AB_TEMPLATE = (   # 결과 파일 양식: Amazon 실험 도구(MYE)·광고 리포트·판매 리포트 값을 안별로 옮겨 적습니다
    "name,desc,impressions,clicks,sessions,units,orders,spend,new_to_brand_orders,market_ctr,query,period\n"
    "A,현재 메인 이미지,0,0,0,0,0,0,0,0.03,kühlende matratzenauflage,2027-03-29 ~ 2027-05-09\n"
    "B,새 메인 이미지,0,0,0,0,0,0,0,0.03,kühlende matratzenauflage,2027-03-29 ~ 2027-05-09\n"
)
REPORT_AB_REQUIRED = ("name", "impressions", "clicks", "sessions", "units")


def report_ab_parse_csv(text):
    """올린 CSV(양식: REPORT_AB_TEMPLATE) → ab_result. 형식이 틀리면 ValueError."""
    rows = list(csv.DictReader(io.StringIO(text.lstrip("﻿"))))
    if len(rows) != 2:
        raise ValueError("A안·B안 두 줄이 필요합니다.")
    missing = [c for c in REPORT_AB_REQUIRED if c not in rows[0]]
    if missing:
        raise ValueError(f"빠진 열: {', '.join(missing)}")
    def num(v, cast=int):
        v = (v or "").strip().replace(",", "")
        return cast(float(v)) if v else None
    variants = []
    for r in rows:
        v = {"name": r["name"].strip(), "desc": (r.get("desc") or "").strip()}
        for c in ("impressions", "clicks", "sessions", "units", "orders"):
            v[c] = num(r.get(c))
        if not v["impressions"] or not v["sessions"]:
            raise ValueError(f"{v['name']}안의 노출·세션이 0입니다.")
        if not v["orders"]:
            v.pop("orders")
        variants.append(v)
    first = rows[0]
    ab = {"source": "직접 올린 파일", "period": (first.get("period") or "").strip(), "query": (first.get("query") or "").strip(),
          "market_ctr": num(first.get("market_ctr"), float), "variants": variants}
    spend = [num(r.get("spend"), float) for r in rows]
    ntb = [num(r.get("new_to_brand_orders")) for r in rows]
    if all(spend) and all(ntb):   # 안별 광고비·신규 고객 주문이 있으면 CAC 비교 (A = 전, B = 후)
        ab["cac"] = {"before": {"label": "A안", "spend": spend[0], "new_to_brand_orders": ntb[0]},
                     "after": {"label": "B안", "spend": spend[1], "new_to_brand_orders": ntb[1]}}
    return ab


def report_ab_day(now=None):
    """분석 기준일: 08:00 전이면 전날로 봅니다."""
    now = now or datetime.now(REPORT_AB_TZ)
    day = now.date() if now.hour >= REPORT_AB_MORNING_HOUR else now.date() - timedelta(days=1)
    return day.isoformat()


def report_ab_rate(hit, n, hit2, n2):
    """두 비율 z-검정 → (A 비율, B 비율, 양측 유의확률)."""
    ra, rb = hit / n, hit2 / n2
    pooled = (hit + hit2) / (n + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n + 1 / n2))
    z = (rb - ra) / se if se else 0.0
    return ra, rb, math.erfc(abs(z) / math.sqrt(2))


def report_ab_need(p1, p2):
    """지금 차이를 유의수준 0.05, 검정력 80%로 확인하려면 안별로 필요한 노출 수."""
    if p1 == p2:
        return None
    return math.ceil((1.96 + 0.84) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2)) / (p1 - p2) ** 2)


def report_ab_analyze(ab):
    """A/B 결과 판정: 클릭률(CTR)이 유의하게 높고 구매 전환율(CVR)이 기준 이상 떨어지지 않으면 B 승리."""
    a, b = ab["variants"]
    ctr_a, ctr_b, p_ctr = report_ab_rate(a["clicks"], a["impressions"], b["clicks"], b["impressions"])
    conv = "orders" if a.get("orders") and b.get("orders") else "units"   # 주문 수가 있으면 주문 기준 (한 주문 여러 개 구매 보정)
    cvr_a, cvr_b, p_cvr = report_ab_rate(a[conv], a["sessions"], b[conv], b["sessions"])
    cvr_ok = (cvr_b - cvr_a) * 100 >= -REPORT_AB_CVR_TOLERANCE
    b_wins = ctr_b > ctr_a and p_ctr < 0.05 and cvr_ok
    need = report_ab_need(ctr_a, ctr_b)
    out = {
        "source": ab.get("source", ""), "period": ab.get("period", ""), "query": ab.get("query", ""),
        "ctr_a": round(ctr_a * 100, 2), "ctr_b": round(ctr_b * 100, 2),
        "ctr_lift": round((ctr_b / ctr_a - 1) * 100, 1) if ctr_a else None, "p_ctr": round(p_ctr, 4),
        "cvr_basis": "주문 ÷ 세션" if conv == "orders" else "판매 수량 ÷ 세션 (Unit Session %)",
        "cvr_a": round(cvr_a * 100, 2), "cvr_b": round(cvr_b * 100, 2), "p_cvr": round(p_cvr, 4), "cvr_ok": cvr_ok,
        "winner": b["name"] if b_wins else a["name"], "b_wins": b_wins,
        "need_per_arm": need, "have_per_arm": min(a["impressions"], b["impressions"]),
        "variants": [{"name": v["name"], "desc": v.get("desc", "")} for v in (a, b)],
    }
    mkt = ab.get("market_ctr")
    if mkt:
        out["ratio_a"], out["ratio_b"] = round(ctr_a / mkt, 2), round(ctr_b / mkt, 2)
    cac = ab.get("cac") or {}
    if cac.get("before") and cac.get("after"):
        cb, ca = cac["before"], cac["after"]
        out["cac_before"] = round(cb["spend"] / cb["new_to_brand_orders"], 2) if cb.get("new_to_brand_orders") else None
        out["cac_after"] = round(ca["spend"] / ca["new_to_brand_orders"], 2) if ca.get("new_to_brand_orders") else None
    return out


def report_ab_p(p):
    return "<0.0001" if p < 0.0001 else f"{p:.4f}"


def report_ab_verdict(r, prev):
    """결과 문장 + 다음 행동 + 전날 대비 변화."""
    if r["b_wins"]:
        msg = f"B 승리: 클릭률 {r['ctr_a']}% → {r['ctr_b']}% ({r['ctr_lift']:+.1f}%, p={report_ab_p(r['p_ctr'])}), 구매 전환율 기준 통과 → B 적용"
    elif r["ctr_b"] > r["ctr_a"] and not r["cvr_ok"]:
        msg = f"클릭은 늘었지만 구매 전환율이 {r['cvr_a']}% → {r['cvr_b']}%로 기준({REPORT_AB_CVR_TOLERANCE}%p) 넘게 하락 → A 유지, 상세페이지 점검"
    elif r["ctr_b"] > r["ctr_a"]:
        left = (r["need_per_arm"] or 0) - r["have_per_arm"]
        msg = (f"B가 앞서지만 아직 유의하지 않음 (p={report_ab_p(r['p_ctr'])}) → 테스트 계속"
               + (f", 안별 노출 약 {left:,}회 더 필요" if left > 0 else ""))
    else:
        msg = f"B가 A보다 낮음 (클릭률 {r['ctr_a']}% → {r['ctr_b']}%) → A 유지, ② 가설 재검토"
    change = ""
    if prev:
        change = (f"전날 대비: B 클릭률 {prev['ctr_b']}% → {r['ctr_b']}%, 유의확률 {report_ab_p(prev['p_ctr'])} → {report_ab_p(r['p_ctr'])}"
                  + (", 판정 바뀜" if prev.get("winner") != r["winner"] else ""))
    return msg, change


def report_ab_daily(saved_report, utm_rows_fn):
    """오늘 아침 분석이 이미 있으면 그대로, 없으면 ③ 탭 최신 결과로 새로 분석합니다."""
    day = report_ab_day()
    old = (saved_report or {}).get("ab_daily") if isinstance(saved_report, dict) else None
    old = old if isinstance(old, dict) else {}
    media = store_get("media")
    media = media if isinstance(media, dict) else {}
    ab, utm = media.get("ab_result"), media.get("utm") or []
    if old.get("day") == day and (old.get("result") or not ab):
        return old   # 오늘 분석이 있으면 그대로 (아침에 결과가 없었는데 나중에 ③ 탭이 저장했으면 그때 한 번 분석)
    result = report_ab_analyze(ab) if isinstance(ab, dict) and len(ab.get("variants", [])) == 2 else None
    prev = old.get("result") if old.get("day") != day else None
    msg, change = report_ab_verdict(result, prev) if result else ("", "")
    rows, worst = utm_rows_fn(utm) if utm else ([], None)
    history = old.get("history", [])
    if old.get("day") and old.get("day") != day and prev:
        history = ([{"day": old["day"], "winner": prev["winner"], "ctr_b": prev["ctr_b"], "p_ctr": prev["p_ctr"]}]
                   + history)[:REPORT_AB_HISTORY]
    return {
        "day": day,
        "analyzed_at": datetime.now(REPORT_AB_TZ).strftime("%Y-%m-%d %H:%M"),
        "media_updated_at": media.get("updated_at", ""),
        "result": result, "verdict": msg, "change": change,
        "utm": rows, "utm_worst": worst["channel"] if worst else "",
        "history": history,
    }
