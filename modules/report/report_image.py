"""이미지로 고칠 수 있는 문제 (① 화면 오른쪽 카드, ② 가설·③ 광고 소재에서 사용).
지금 있는 데이터(상품 정보·Keepa 상세·검색어 분석·광고 문구 점검)에서만 만들고, 고정 문장·고정 값은 쓰지 않습니다.
데이터가 없으면 그 항목은 빠집니다."""
import json
import re
from statistics import median

from modules.report.report_competitor import REPORT_SEORI_PROXY, report_rank_list, report_severity_key
from modules.report.report_keepa import report_keepa_detail
from modules.report.report_sqp import REPORT_SQP_LISTING_FILE

# ③ 광고 소재 탭이 지금 이어받아 제작할 수 있는 이미지 종류 (modules/media/media_variable.py: 메인 이미지만 확정 가능).
# ③이 서브 이미지·배너·영상도 받게 되면 여기에 종류를 추가하면 1순위 후보가 넓어집니다.
REPORT_IMAGE_STAGE3_KINDS = {"메인 이미지"}

# 상세페이지 불릿에서 '구체 정보'로 보는 항목 (독일어 상세페이지 표현 기준)
REPORT_IMAGE_INFO = {
    "세탁": r"wasch|°\s*c|waschbar|maschine",
    "고정 밴드": r"eckgummi|eckband|eckbänd|gummi|rutsch|elastisch",
    "인증": r"oeko|öko",
    "두께·사이즈": r"\d+\s*x\s*\d+|\d+\s*(mm|cm)",
}


def report_image_listing():
    """우리 상품 정보 (가상). 없으면 None."""
    if not REPORT_SQP_LISTING_FILE.exists():
        return None
    return json.loads(REPORT_SQP_LISTING_FILE.read_text(encoding="utf-8"))


def report_image_info_found(features):
    text = " ".join(str(f) for f in features or []).lower()
    return {name for name, pat in REPORT_IMAGE_INFO.items() if re.search(pat, text)}


def report_image_fixes(data):
    """[{title, detail, action, use, rank_label, source}] - 위험도 순위와 연결되는 항목이 앞."""
    fixes = []
    key_titles = [k["title"] for k in data.get("key_problems") or []]

    def rank_of(title):
        return f"{key_titles.index(title) + 1}순위" if title in key_titles else ""

    # 1) 메인 이미지: 검색 결과 첫인상 (② 가설 재료가 '사진'인 문제)
    listing = report_image_listing()
    for p in data.get("problems") or []:
        plan = p.get("plan") or {}
        if plan.get("visual") and listing and listing.get("main_image_issue"):
            fixes.append({
                "title": f"메인 이미지: {listing['main_image_issue']}",
                "detail": f"{p['title']} · 지금 사진 '{listing['main_image']}' (상품 정보 가상)",
                "action": f"'{listing['main_image_issue']}'를 고친 메인 이미지 B안 → ② A/B 가설, ③ B안 사진 제작",
                "use": ["② 가설", "③ 소재"], "rank_label": rank_of(p["title"]), "source": "검색어 분석(가상)·상품 정보",
                "kind": "메인 이미지", "problem_title": p["title"],
            })
            break

    # 2) 광고 이미지 속 문구: 규제(UWG) 필수 표기
    for f in data.get("external") or []:
        if f.get("group") == "규제" and f.get("kind") == "위협":
            fixes.append({
                "title": "광고 이미지 문구: 시험기관·성적서 번호 같이 넣기",
                "detail": f["title"],
                "action": "이미지·배너의 냉감 수치 옆에 시험 조건·시험기관·성적서 번호를 함께 표기 (광고·상세페이지 문구)",
                "use": ["② 가설"], "rank_label": rank_of(f["title"]), "source": "광고 문구 점검·독일 DB",
                "kind": "광고 이미지 문구", "problem_title": f["title"],
            })
            break

    # 3) 상세 이미지 수 · 4) 불릿에 없는 구체 정보 (Keepa 상세: 서리 = 실적 가정 브랜드)
    items = list((report_keepa_detail().get("items") or {}).values())
    own = next((it for it in items if it.get("brand") == REPORT_SEORI_PROXY), None)
    rivals = [it for it in items if it is not own and it.get("type") != "비냉감 혼재"]
    if own and rivals:
        counts = [it["images"] for it in rivals if it.get("images")]
        if own.get("images") and counts and own["images"] < median(counts):
            need = round(median(counts) - own["images"]) or 1
            fixes.append({
                "title": f"상세 이미지 {own['images']}장, 경쟁사 중앙값 {median(counts):g}장",
                "detail": f"냉감 경쟁사 {len(counts)}곳 이미지 수 {min(counts)}~{max(counts)}장 ({REPORT_SEORI_PROXY} 실적 가정)",
                "action": f"부족한 {need}장을 사용 장면·크기 비교 이미지로 상세페이지에 추가",
                "use": ["상세페이지"], "rank_label": "", "source": "Keepa 상세", "kind": "상세 이미지", "problem_title": None,
            })
        found = report_image_info_found(own.get("features"))
        rival_found = [report_image_info_found(it.get("features")) for it in rivals]
        missing = [name for name in REPORT_IMAGE_INFO
                   if name not in found and sum(name in r for r in rival_found) * 2 >= len(rivals)]
        if missing:
            have = ", ".join(f"{name} {sum(name in r for r in rival_found)}곳" for name in missing)
            fixes.append({
                "title": f"상세페이지에 {'·'.join(missing)} 정보 없음",
                "detail": f"우리 불릿 {len(own.get('features') or [])}개에 없음 · 냉감 경쟁사 {len(rivals)}곳 중 {have} 표기",
                "action": f"{'·'.join(missing)}를 한 장에 모은 정보 이미지(인포그래픽)를 상세페이지에 추가",
                "use": ["상세페이지"], "rank_label": "", "source": "Keepa 상세", "kind": "상세 이미지", "problem_title": None,
            })
    return sorted(fixes, key=report_image_order)


def report_image_order(fix):
    """③ 탭에서 바로 쓸 수 있는 종류(메인 이미지)를 먼저, 그다음 위험도 순위와 연결된 것, 나머지."""
    return fix["kind"] not in REPORT_IMAGE_STAGE3_KINDS, fix["rank_label"] == "", fix["rank_label"]


def report_image_rank(data):
    """1·2순위 = ② 가설 재료(plan)가 있고 이미지(메인·서브·광고 배너 문구)로 고칠 수 있는 문제 2개.
    1순위는 ③ 탭이 지금 바로 제작할 수 있는 종류(REPORT_IMAGE_STAGE3_KINDS)를 먼저 (② 가설 1 → ③ 제작이 끊기지 않게),
    같은 조건 안에서는 위험도 → 심각도 순. 3순위부터는 기존 핵심 문제 순서 (이미지 문제가 아니어도 됨).
    data의 key_problems·problems 순서·요인 rank_label·image_fixes rank_label을 함께 고칩니다."""
    plans = {p["title"] for p in data["problems"] if p.get("plan")}
    linked = {f["problem_title"]: f for f in data["image_fixes"] if f.get("problem_title") in plans}
    factors = data["internal"] + data["external"]
    # 1순위: ③ 탭이 지금 제작할 수 있는 종류(메인 이미지)를 먼저, 그다음 이미지 문제 중 위험도 → 심각도 순
    top = sorted([f for f in factors if f["title"] in linked],
                 key=lambda f: (linked[f["title"]]["kind"] not in REPORT_IMAGE_STAGE3_KINDS, report_severity_key(f)))[:2]
    top_titles = {f["title"] for f in top}
    rest = []
    for k in data["key_problems"]:
        f = next((x for x in factors if x["title"] == k["title"]), None)
        if f and f["title"] not in top_titles and f not in rest:
            rest.append(f)
    data["key_problems"] = report_rank_list(top + rest[:max(0, 4 - len(top))], data["internal"])
    for k in data["key_problems"]:
        fix = linked.get(k["title"]) if k["title"] in top_titles else None
        k["image_fix"] = ({**{x: fix[x] for x in ("kind", "title", "action", "use")}, "stage3": fix["kind"] in REPORT_IMAGE_STAGE3_KINDS}
                          if fix else None)
    order = [k["title"] for k in data["key_problems"]]
    first = [p for t in order for p in data["problems"] if p["title"] == t]
    data["problems"] = first + [p for p in data["problems"] if p not in first]
    for f in data["image_fixes"]:
        t = f.get("problem_title")
        f["rank_label"] = f"{order.index(t) + 1}순위" if t in order else ""
    data["image_fixes"].sort(key=report_image_order)


def report_stage3_check(data):
    """문제마다 ① → ② → ③ 연결 판정 p["stage3"] = {"ok", "why"} (② 가설 후보 순서·배지, ① 창에서 사용).
    ok = ② 가설 재료(plan)가 있고, 그 해결이 ③ 탭이 지금 만드는 이미지 종류(메인 이미지)인 문제. 이유는 데이터(plan_none·plan 소재·이미지 종류)로."""
    linked = {f["problem_title"]: f for f in data.get("image_fixes") or [] if f.get("problem_title")}
    for p in data["problems"]:
        plan, fix = p.get("plan") or {}, linked.get(p["title"])
        if not plan:
            p["stage3"] = {"ok": False, "why": f"② 가설 재료 없음 ({p.get('plan_none') or '데이터 없음'})"}
        elif fix and fix["kind"] in REPORT_IMAGE_STAGE3_KINDS:
            p["stage3"] = {"ok": True, "why": f"{fix['kind']} B안으로 ③에서 제작 ({plan.get('material', '')})"}
        elif fix:
            p["stage3"] = {"ok": False, "why": f"해결이 {fix['kind']}라 ③(메인 이미지 제작)이 아닌 문구 수정으로 개선"}
        else:
            p["stage3"] = {"ok": False, "why": f"해결에 이미지가 필요 없음 (준비할 것: {plan.get('material') or '-'})"}

