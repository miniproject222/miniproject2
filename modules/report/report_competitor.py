# 1. 분석 리포트 - 경쟁사 비교와 내부/외부 요인 (실제 데이터만)
# 근거: 공통 경쟁사 DB·독일 DB(루트 data/, 읽기만), Keepa 마지막 조회값, Open-Meteo 현재 기온(ui_theme 공통 함수)
# 문구마다 근거(시트 이름, 독일 DB ID, Keepa 조회 시각)를 함께 적습니다.
import csv
from datetime import date
from pathlib import Path
from statistics import median

import ui_theme as ui

REPORT_ROOT_DATA = Path(__file__).resolve().parents[2] / "data"
REPORT_COMPETITOR_DB = REPORT_ROOT_DATA / "common_competitor_seori_202610.csv"
REPORT_KNOWLEDGE_DB = REPORT_ROOT_DATA / "common_germany_knowledge_seori_202610.csv"
REPORT_PRICE_ALERT = 0.10         # Keepa 90일 평균 대비 이만큼 오르내리면 외부 요인으로 표시
REPORT_SEASON_MONTHS = (6, 7, 8)  # 냉감패드 성수기 (독일 DB CAL-002, 추론)
REPORT_SCORE_COLS = ["Novilla", "RIBECO", "Traumnacht", "Paradies", "potow", "웰크론(세사)", "GlacialPad", "SEORI (목표)"]
REPORT_LEVEL_ORDER = {"높음": 0, "중간": 1, "낮음": 2}


def report_num(value):
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def report_db_rows(path):
    return list(csv.DictReader(path.open(encoding="utf-8-sig"))) if path.exists() else []


def report_score_col(brand):
    key = brand.split()[0].split("(")[0].lower()
    return next((c for c in REPORT_SCORE_COLS if c.lower().startswith(key[:4])), None)


def report_competitor_load():
    """경쟁사 DB에서 브랜드별 행(서리 포함)과 경쟁우위 가중 점수를 읽습니다."""
    rows = report_db_rows(REPORT_COMPETITOR_DB)
    score_row = next((r for r in rows if r["원본시트"] == "경쟁우위 비교"
                      and r["평가 항목"].startswith("가중 합계 점수")), {})
    out = []
    for r in rows:
        if r["원본시트"] != "경쟁사DB" or r["섹션"] or not r["No"]:
            continue
        col = report_score_col(r["기업/브랜드"])
        out.append({
            "brand": r["기업/브랜드"], "kind": r["구분"], "product": r["제품명"], "type": r["유형"],
            "db_price": report_num(r["판매가"]), "currency": r["통화"], "price_basis": r["가격 기준"],
            "sqm_price": report_num(r["㎡당 가격"]), "channels": r["판매 채널"], "qmax": r["Q-max (공개값)"],
            "certs": r["인증"], "strength": r["강점"], "weakness": r["약점"], "trust": r["신뢰도"],
            "score": report_num(score_row.get(col, "")) if col else None,
        })
    return out


def report_competitor_criteria():
    """경쟁우위 비교 시트: 항목별 가중치, 서리(목표) 점수, 경쟁사 최고점."""
    out = []
    for r in report_db_rows(REPORT_COMPETITOR_DB):
        if r["원본시트"] != "경쟁우위 비교" or r["섹션"] or not report_num(r["가중치"]) or r["가중치"] == "1.0":
            continue
        rivals = {c: report_num(r[c]) for c in REPORT_SCORE_COLS[:-1] if report_num(r[c]) is not None}
        best = max(rivals, key=rivals.get)
        out.append({"item": r["평가 항목"], "weight": report_num(r["가중치"]), "seori": report_num(r["SEORI (목표)"]),
                    "best_brand": best, "best": rivals[best], "memo": r["평가 메모"]})
    return out


def report_competitor_checklist():
    """서리 제품 기획 D: 독일 판매 인증·규제 체크리스트 (해당 없음 제외)."""
    return [{"group": r["구분"], "item": r["인증·규제"], "status": r["상태"]}
            for r in report_db_rows(REPORT_COMPETITOR_DB)
            if r["원본시트"] == "SEORI 제품 기획" and r["섹션"].startswith("D.") and not r["구분"].startswith("해당 없음")]


def report_competitor_tests():
    """서리 시험·표시 F: 출시 전 완제품 시험 계획과 결과 입력 여부."""
    return [{"item": r["시험 항목"], "result": r["결과 입력"].strip(" -")}
            for r in report_db_rows(REPORT_COMPETITOR_DB)
            if r["원본시트"] == "SEORI 시험·표시" and r["섹션"].startswith("F.") and r["시험 항목"]]


def report_knowledge(ids):
    """독일 DB 지식 행 (ID → 내용)."""
    return {r["ID"]: r for r in report_db_rows(REPORT_KNOWLEDGE_DB) if r["원본시트"] == "지식DB" and r["ID"] in ids}


def report_competitor_merge(rows, keepa_products, keepa_items):
    """경쟁사 행에 Keepa 값(현재가, 90일 평균 대비, 평점, 리뷰, 재고, ㎡당 가격)을 붙입니다."""
    by_brand = {p["db_brand"]: p for p in keepa_products}
    for r in rows:
        p = by_brand.get(r["brand"])
        k = (keepa_items or {}).get(p["asin"]) if p else None
        r["asin"] = p["asin"] if p else ""
        r["keepa"] = k
        r["keepa_sqm"] = (k["price"] / (p["width_cm"] * p["length_cm"] / 10000)
                          if k and k["price"] and p.get("width_cm") else None)
    return rows


def report_sqm(r):
    """㎡당 가격 (EUR): Keepa 현재가가 있으면 그 값, 없으면 경쟁사 DB 값."""
    return r.get("keepa_sqm") or (r["sqm_price"] if r["currency"] == "EUR" else None)


def report_channel_count(r):
    return len([c for c in r["channels"].split(",") if c.strip()])


def report_position_kpis(rows, checklist):
    """KPI 4개 (GA4 연결 전): 서리의 경쟁 포지션. 모두 경쟁사 DB·Keepa 실제 값."""
    seori = next((r for r in rows if r["kind"] == "자사"), None)
    rivals = [r for r in rows if r["kind"] != "자사"]
    if not seori:
        return []
    priced = [report_sqm(r) for r in rivals if report_sqm(r)]
    reviews = [(r["keepa"]["reviews"], r["brand"]) for r in rivals if r.get("keepa") and r["keepa"].get("reviews") is not None]
    wide = max(rivals, key=report_channel_count)
    must = [c for c in checklist if c["group"].startswith("필수")]
    done = [c for c in must if c["status"] not in ("미착수", "")]
    kpis = [{"label": "㎡당 가격 (서리)", "value": f"€{seori['sqm_price']:.1f}",
             "badge": f"경쟁사 중앙값 €{median(priced):.1f}의 {seori['sqm_price'] / median(priced):.1f}배" if priced else "", "good": False}]
    if reviews:
        top = max(reviews)
        kpis.append({"label": "리뷰 수 (서리)", "value": "0건", "badge": f"{top[1]} {top[0]:,}건", "good": False})
    kpis.append({"label": "판매 채널 (서리)", "value": f"{report_channel_count(seori)}개",
                 "badge": f"{wide['brand']} {report_channel_count(wide)}개", "good": False})
    kpis.append({"label": "출시 필수 인증·규제", "value": f"{len(done)}/{len(must)} 완료",
                 "badge": f"미착수 {len(must) - len(done)}건", "good": len(done) == len(must)})
    return kpis


def report_internal_factors(rows, criteria, checklist, tests, keepa_time):
    """내부 요인: 서리가 경쟁사 대비 부족한 점 (경쟁사 DB + Keepa)."""
    seori = next((r for r in rows if r["kind"] == "자사"), None)
    rivals = [r for r in rows if r["kind"] != "자사"]
    out = []
    if not seori:
        return out

    reviews = sorted([(r["keepa"]["reviews"], r["brand"]) for r in rivals
                      if r.get("keepa") and r["keepa"].get("reviews")], reverse=True)
    if reviews:
        tops = ", ".join(f"{b} {n:,}건" for n, b in reviews[:2])
        out.append({"title": "리뷰 0건 (신규 브랜드)", "level": "높음", "group": "신뢰",
                    "detail": f"경쟁사 {tops} (Keepa {keepa_time}) · 온라인 쇼핑객 54%가 구매 전 리뷰 확인 (독일 DB SHP-006)"})

    must = [c for c in checklist if c["group"].startswith("필수") and c["status"] in ("미착수", "")]
    if must:
        names = ", ".join(c["item"].split(" (")[0] for c in must)
        out.append({"title": f"출시 필수 인증·규제 {len(must)}건 미착수", "level": "높음", "group": "인증·규제",
                    "detail": f"{names} (경쟁사 DB 'SEORI 제품 기획' D)"})

    pending = [t for t in tests if not t["result"]]
    if pending:
        out.append({"title": f"완제품 시험 {len(pending)}건 결과 없음", "level": "높음", "group": "시험",
                    "detail": f"{', '.join(t['item'] for t in pending[:4])} 등 · 수치 공개 우위는 시험값이 있어야 성립 "
                              f"(경쟁사 DB 'SEORI 시험·표시' F)"})

    priced = [r for r in rivals if report_sqm(r)]
    if priced and seori["sqm_price"]:
        low = min(priced, key=report_sqm)
        src = f"Keepa {keepa_time}" if low.get("keepa_sqm") else "경쟁사 DB"
        out.append({"title": f"㎡당 가격이 최저가 경쟁사의 {seori['sqm_price'] / report_sqm(low):.1f}배", "level": "중간",
                    "group": "가격", "detail": f"서리 €{seori['sqm_price']:.1f} vs {low['brand']} €{report_sqm(low):.1f} ({src})"})

    wide = max(rivals, key=report_channel_count, default=None)
    if wide and report_channel_count(wide) > report_channel_count(seori):
        out.append({"title": f"판매 채널 {report_channel_count(seori)}개 (경쟁사 최다 {report_channel_count(wide)}개)",
                    "level": "중간", "group": "채널",
                    "detail": f"서리: {seori['channels']} / {wide['brand']}: {wide['channels']} (경쟁사 DB)"})

    gaps = sorted([c for c in criteria if c["seori"] is not None and c["seori"] < c["best"]],
                  key=lambda c: (c["best"] - c["seori"]) * c["weight"], reverse=True)
    if gaps:
        out.append({"title": f"경쟁우위 {len(criteria)}개 항목 중 {len(gaps)}개가 목표치로도 경쟁사 최고점 미만",
                    "level": "중간", "group": "경쟁력",
                    "detail": " · ".join(f"{c['item'].split(' (')[0]} {c['seori']:.0f} vs {c['best_brand']} {c['best']:.0f}" for c in gaps[:4])
                              + " (경쟁사 DB '경쟁우위 비교', 서리는 목표 점수)"})

    out.append({"title": "여름 전용 제품, 독일 물류 거점 없음", "level": "중간", "group": "제품·물류",
                "detail": f"{seori['weakness']} (경쟁사 DB 서리 약점)"})
    return sorted(out, key=lambda f: REPORT_LEVEL_ORDER[f["level"]])


def report_external_factors(rows, keepa_time, today=None):
    """외부 요인: 위협(문제)과 기회. (경쟁사 DB, Keepa, 독일 DB, Open-Meteo 현재 기온)"""
    today = today or date.today()
    rivals = [r for r in rows if r["kind"] != "자사"]
    kb = report_knowledge({"SHP-002", "TRN-101", "TRN-105", "LAW-101", "CLI-001", "CAL-002"})
    out = []

    # Keepa: 경쟁사 가격 변화, 품절
    for r in rivals:
        k = r.get("keepa")
        if not k:
            continue
        if not k["in_stock"]:
            out.append({"kind": "기회", "title": f"{r['brand']} Amazon.de 재고 없음", "level": "중간", "group": "경쟁사",
                        "detail": f"Keepa {keepa_time} 기준 판매 중인 오퍼 없음"})
        elif k.get("change") is not None and abs(k["change"]) >= REPORT_PRICE_ALERT:
            down = k["change"] < 0
            base = f"90일 평균 €{k['avg90']:.2f} → 현재 €{k['price']:.2f}" if k.get("avg90") else f"현재 €{k['price']:.2f}"
            out.append({"kind": "위협" if down else "기회", "level": "높음" if down else "낮음", "group": "경쟁사",
                        "title": f"{r['brand']} 가격 {abs(k['change']) * 100:.0f}% {'인하' if down else '인상'}",
                        "detail": f"{base} (Keepa {keepa_time}, Amazon.de)"})

    # 날씨·시즌: Open-Meteo 현재 기온 + 독일 DB
    temps = ui.fetch_state_temperatures()
    if today.month not in REPORT_SEASON_MONTHS:
        avg = f"독일 16개 주 현재 평균 {sum(t['temp'] for t in temps) / len(temps):.1f}°C (Open-Meteo) · " if temps else ""
        out.append({"kind": "위협", "title": f"{today.month}월 비시즌 (여름 전용 제품)", "level": "중간", "group": "날씨",
                    "detail": f"{avg}수요는 열대야가 많은 6~8월에 집중 (독일 DB CAL-002, 추론)"})

    if "SHP-002" in kb:
        out.append({"kind": "위협", "title": "Amazon.de 일반 PayPal 결제 불가", "level": "중간", "group": "플랫폼",
                    "detail": f"{kb['SHP-002']['내용 (한국어)']} (독일 DB SHP-002)"})
    if "TRN-101" in kb:
        out.append({"kind": "위협", "title": "독일 소비심리 위축", "level": "중간", "group": "시장",
                    "detail": f"{kb['TRN-101']['내용 (한국어)']} (독일 DB TRN-101)"})
    if "TRN-105" in kb:
        out.append({"kind": "위협", "title": "중국 초저가 플랫폼 급성장", "level": "낮음", "group": "시장",
                    "detail": f"{kb['TRN-105']['내용 (한국어)']} (독일 DB TRN-105)"})
    if "LAW-101" in kb:
        out.append({"kind": "위협", "title": "친환경 표현 규제 시행 (EmpCo)", "level": "낮음", "group": "규제",
                    "detail": f"{kb['LAW-101']['내용 (한국어)'][:80]}… (독일 DB LAW-101)"})

    # 기회
    hidden = [r["brand"] for r in rivals if r["currency"] == "EUR" and "미공개" in r["qmax"]]
    if hidden:
        out.append({"kind": "기회", "title": "독일 경쟁사 Q-max 미공개", "level": "중간", "group": "경쟁사",
                    "detail": f"{', '.join(hidden)} 미공개 → 완제품 시험값을 공개하면 단독 우위 (경쟁사 DB)"})
    if "CLI-001" in kb:
        out.append({"kind": "기회", "title": "에어컨 없는 가구가 70% 이상", "level": "중간", "group": "시장",
                    "detail": f"{kb['CLI-001']['내용 (한국어)'][:90]}… (독일 DB CLI-001)"})
    return sorted(out, key=lambda f: (f["kind"] != "위협", REPORT_LEVEL_ORDER[f["level"]]))


def report_competitor_slim(rows):
    """홈·가설 탭이 쓰는 간단한 경쟁사 표 (열 6개)."""
    out = []
    for r in rows:
        k = r.get("keepa") or {}
        price = f"€{k['price']:.2f}" if k.get("price") else (
            f"{'€' if r['currency'] == 'EUR' else r['currency'] + ' '}{r['db_price']:.2f}" if r["db_price"] else "-")
        out.append({
            "브랜드": r["brand"], "가격": price,
            "평점": f"{k['rating']:.1f}" if k.get("rating") else "-",
            "리뷰 수": f"{k['reviews']:,}" if k.get("reviews") is not None else "-",
            "판매 채널": r["channels"],
            "재고": ("있음" if k["in_stock"] else "없음") if k else "-",
        })
    return out


# ─────────────────────────────────────────────
# 문제 도출 + 다른 탭에 넘길 데이터
# ─────────────────────────────────────────────
# 가설 탭이 바로 받을 수 있게 문제를 '어떻게 하면 ~할까?' 질문으로 바꿉니다 (문제 분류별)
REPORT_HMW = {
    "신뢰": "리뷰가 없는 신규 브랜드가 독일 소비자의 신뢰를 어떻게 얻을까?",
    "인증·규제": "출시 필수 인증·규제를 언제까지, 어떤 순서로 갖출까?",
    "시험": "완제품 시험값을 어떻게 확보하고 상세페이지·광고에 보여 줄까?",
    "가격": "㎡당 가격 차이를 어떤 근거로 납득시킬까?",
    "채널": "Amazon.de 외 판매 채널을 어떻게 넓힐까?",
    "경쟁력": "경쟁우위 점수가 낮은 항목 중 무엇부터 끌어올릴까?",
    "제품·물류": "여름 전용 제품의 재고·배송 부담을 어떻게 줄일까?",
    "경쟁사": "경쟁사 가격 인하에 가격 말고 무엇으로 대응할까?",
    "날씨": "비시즌 동안 다음 여름 판매를 위해 무엇을 준비할까?",
    "플랫폼": "PayPal을 선호하는 고객을 자사몰로 어떻게 유도할까?",
    "시장": "지출을 줄이는 독일 소비자에게 무엇을 강조할까?",
    "규제": "규제를 지키면서 어떤 표현으로 홍보할까?",
}
# 광고 소재·상세페이지에서 지켜야 할 독일 표현 규칙 (독일 DB ID)
REPORT_RULE_IDS = ["LNG-001", "LNG-002", "LNG-003", "LNG-004", "LNG-005", "LNG-006", "LAW-102", "LAW-104"]


def report_key_problems(internal, external, limit=3):
    """핵심 문제 Top N: 내부 1순위, 외부 위협 1순위, 그다음 순위 순으로 고르고 질문(HMW)을 붙입니다."""
    threats = [f for f in external if f["kind"] == "위협"]
    picked = [x for x in (internal[:1] + threats[:1])]
    rest = sorted(internal[1:] + threats[1:], key=lambda f: REPORT_LEVEL_ORDER[f["level"]])
    for f in rest:
        if len(picked) >= limit:
            break
        picked.append(f)
    out = []
    for i, f in enumerate(picked[:limit], 1):
        out.append({"rank": i, "type": "내부" if f in internal else "외부", "level": f["level"], "group": f["group"],
                    "title": f["title"], "detail": f["detail"],
                    "question": REPORT_HMW.get(f["group"], f"'{f['title']}' 문제를 어떻게 풀까?")})
    return out


def report_marketing_rules():
    """독일 DB에서 광고·상세페이지 표현 규칙만 골라 돌려줍니다."""
    kb = report_knowledge(set(REPORT_RULE_IDS))
    return [{"id": i, "topic": kb[i]["소분류"], "rule": kb[i]["SEORI 시사점"]} for i in REPORT_RULE_IDS if i in kb]


def report_team_handoff(rows, keepa_time):
    """다른 탭용: 서리 프로필, 경쟁사 프로필(강점·약점·Keepa), 경쟁사 신호(품절·가격 변화)."""
    def profile(r):
        k = r.get("keepa") or {}
        return {"brand": r["brand"], "kind": r["kind"], "product": r["product"], "type": r["type"],
                "price": r["db_price"], "currency": r["currency"], "sqm_price": report_sqm(r),
                "channels": r["channels"], "qmax": r["qmax"], "certs": r["certs"],
                "strength": r["strength"], "weakness": r["weakness"],
                "amazon_price": k.get("price"), "price_change_90d": k.get("change"),
                "rating": k.get("rating"), "reviews": k.get("reviews"), "in_stock": k.get("in_stock")}

    seori = next((r for r in rows if r["kind"] == "자사"), None)
    rivals = [r for r in rows if r["kind"] != "자사"]
    signals = [{"brand": r["brand"], "in_stock": r["keepa"]["in_stock"], "price": r["keepa"]["price"],
                "price_change_90d": r["keepa"].get("change"), "fetched_at": keepa_time}
               for r in rivals if r.get("keepa")]
    return {"seori_profile": profile(seori) if seori else {},
            "competitor_profiles": [profile(r) for r in rivals],
            "competitor_signals": signals}


# 가설 탭(hypothesis.md) 데이터 계약: problems[0]으로 가설 1개를 만들고, 선택 필드 target·metric·local_context·competitor_review를 반영
REPORT_PROBLEM_METRIC = {
    "신뢰": "전환율", "인증·규제": "출시 준비", "시험": "전환율", "가격": "전환율", "채널": "매출",
    "경쟁력": "매출", "제품·물류": "매출", "경쟁사": "전환율", "날씨": "매출", "플랫폼": "전환율",
    "시장": "매출", "규제": "광고 집행",
}
REPORT_PROBLEM_CONTEXT = {   # 문제 분류 → 독일 DB 근거 ID (local_context)
    "신뢰": "SHP-006", "인증·규제": "REV-110", "시험": "VAL-004", "가격": "VAL-003", "채널": "TRN-104",
    "경쟁력": "CUL-106", "제품·물류": "DLV-101", "경쟁사": "SHP-210", "날씨": "CAL-002", "플랫폼": "SHP-002",
    "시장": "TRN-101", "규제": "LAW-101",
}


def report_hypothesis_problems(key_problems, internal, external, rows):
    """홈·가설 탭용 problems: 핵심 문제 Top 3를 맨 앞에, 그다음 나머지 (낮음 제외).
    각 문제에 가설 탭 선택 필드(target, metric, local_context, competitor_review)를 실제 데이터로 채웁니다."""
    seori = next((r for r in rows if r["kind"] == "자사"), None)
    rivals = [r for r in rows if r["kind"] != "자사" and r["currency"] == "EUR"]
    kb = report_knowledge(set(REPORT_PROBLEM_CONTEXT.values()))
    target = f"{seori['channels'].split(' (')[0]}에서 냉감 매트리스 패드를 비교하는 독일 구매자" if seori else "독일 구매자"
    # 가설 탭은 앞부분만 잘라 쓰므로 핵심(경쟁사 약점)을 앞에, 출처는 뒤에 둡니다. 실제 리뷰 원문이 아니라 DB 약점·Keepa 평점입니다.
    weak = [f"{r['brand'].split()[0]} {r['weakness'].split(',')[0].strip()}" for r in rivals[:3] if r["weakness"]]
    rated = [f"{r['brand'].split()[0]} {r['keepa']['rating']:.1f}" for r in rivals if r.get("keepa") and r["keepa"].get("rating")]
    review = (" / ".join(weak) + (f" · Amazon 평점 {', '.join(rated[:3])}" if rated else "")
              + " (경쟁사 DB 약점, Keepa 평점)") if weak else ""

    def make(f, kind):
        ctx = kb.get(REPORT_PROBLEM_CONTEXT.get(f["group"], ""))
        return {"title": f["title"], "type": kind, "level": f["level"], "group": f["group"], "detail": f["detail"],
                "target": target, "metric": REPORT_PROBLEM_METRIC.get(f["group"], "매출"),
                "local_context": f"{ctx['내용 (한국어)']} (독일 DB {ctx['ID']})" if ctx else "",
                "competitor_review": review}

    out, seen = [], set()
    for p in key_problems:
        out.append(make(p, p["type"]))
        seen.add(p["title"])
    for f in internal:
        if f["title"] not in seen and f["level"] != "낮음":
            out.append(make(f, "내부"))
    for f in external:
        if f["kind"] == "위협" and f["title"] not in seen and f["level"] != "낮음":
            out.append(make(f, "외부"))
    return out
