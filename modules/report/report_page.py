# 1. 문제 분석 (검색어 클릭 분석은 가상 SQP + 실제 Keepa·DWD, 경쟁 포지션 분석은 실제 데이터만)
import time
from datetime import date, datetime
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

import ui_theme as ui

from common.common_store import store_get, store_set
from modules.report.report_ab import REPORT_AB_TEMPLATE, report_ab_analyze, report_ab_p, report_ab_parse_csv, report_ab_verdict
from modules.report.report_competitor import REPORT_SEORI_PROXY, report_shop_review_count
from modules.report.report_data import report_load_data, report_utm_rows
from modules.report.report_review import report_shop_reviews
from modules.report.report_download import report_download_pdf
from modules.report.report_keepa import (
    report_keepa_can_fetch, report_keepa_detail, report_keepa_estimate, report_keepa_fetch_and_save, report_keepa_usage,
)
from modules.report.report_sqp import report_sqp_kpis
from modules.report.report_sqp_view import report_sqp_show

REPORT_DIR = Path(__file__).resolve().parent   # 내 폴더 (images/, data/ 경로 만들 때 사용)

REPORT_LEVEL_DOTS = {"높음": "●●●", "중간": "●●○", "낮음": "●○○"}
REPORT_LEVEL_CLASS = {"높음": "high", "중간": "mid", "낮음": "low"}
REPORT_TOP_HEIGHT = 560   # 본문 50:50 두 카드 높이(px): 왼쪽 1순위·오른쪽 2순위 자세히 카드를 같게 (넘치면 카드 안 스크롤)


REPORT_HELP_RULE = ("**순위 기준**: ② 가설로 만들어 ③ 탭에서 바로 제작할 수 있는 문제(지금 ③은 메인 이미지)를 먼저, "
                    "그다음 이미지(서브·광고 배너 문구)로 고칠 수 있는 문제, 같은 조건 안에서는 위험도 → 심각도 순. 3순위부터는 다른 문제여도 됨")
REPORT_LOAD_MIN_SEC = 1.0   # 불러오기 로딩 표시 최소 시간 (초): 너무 빨리 끝나도 '불러오는 느낌'이 나게
REPORT_LOADED_KEY = "report-loaded"   # 이번 접속에서 '불러오기'를 눌렀는지 (누르기 전에는 화면을 비워 둠)


def report_render():
    """'1. 분석 리포트' 탭을 열 때마다 실행됩니다. 화면은 전부 이 함수 안에서 그립니다.
    처음에는 비어 있고, 오른쪽 위 '불러오기'를 누르면 분석해서 화면을 채우고, '저장하기'를 누르면 ② 탭이 읽을 리포트로 저장."""
    loaded = st.session_state.get(REPORT_LOADED_KEY, False)
    with st.container(horizontal=True, vertical_alignment="center", key="report-head"):
        with st.container(key="report-head-title"):
            ui.page_header("1. 문제 분석", "Keepa·경쟁사 DB·검색어 분석으로 서리의 내부·외부 문제를 찾아 위험도 순으로 정리해요.")
        with st.container(key="report-help"):   # 안내 문구는 화면에 늘어놓지 않고 이 물음표 하나에 모음 (내용은 아래에서 채움)
            help_box = st.popover("", icon=":material/help:", type="tertiary", help="순위 기준 · 저장 상태 안내")
        st.button("불러오기", icon=":material/download:", key="report-btn-load", on_click=report_click_load,
                  help="Keepa·경쟁사 DB·검색어 분석으로 문제 분석 결과를 만듭니다")
        st.button("다음으로", icon=":material/arrow_forward:", key="report-btn-save", type="primary", disabled=not loaded,
                  on_click=report_click_save, help="지금 결과를 리포트로 저장하고 ② 가설 탭으로 넘어갑니다")
    if st.session_state.pop("report-redirect-toast", False):   # ② 탭 '불러오기'에서 ① 리포트가 없어 넘어온 경우
        st.toast("저장된 ① 리포트가 없어 ① 탭으로 왔어요. 결과를 확인하고 '다음으로'를 눌러 주세요", icon=":material/info:")
    if st.session_state.pop("report-saved-toast", False):
        st.toast("리포트를 저장하고 ② 가설 탭으로 넘어왔어요", icon=":material/check_circle:")
    if not loaded:
        report_show_empty(help_box)
        return

    just = st.session_state.pop("report-just-loaded", False)
    if just:   # 불러오기 직후: 데이터를 실제로 불러오는 동안 로딩 표시 (최소 1초)
        started = time.time()
        with st.spinner("Keepa·경쟁사 DB·검색어 분석 데이터를 불러오는 중…"):
            data = report_load_data()
            time.sleep(max(0.0, REPORT_LOAD_MIN_SEC - (time.time() - started)))
    else:
        data = report_load_data()
    data["reveal"] = just   # 불러오기 직후 한 번만 글자가 차례로 나타남 (report_style.css .report-reveal)
    ga4, sqp = data["ga4"], data["sqp"]
    steps = report_funnel_steps(ga4["funnel"]) if ga4 else []
    worst = min(steps, key=lambda s: s["diff"]) if steps else None
    utm_rows, utm_worst = report_utm_rows(ga4["utm"]) if ga4 else ([], None)
    summary = report_build_summary(data, worst)
    payload = report_build_payload(data, summary, worst, utm_rows, utm_worst)
    st.session_state["report-current-payload"] = payload   # '저장하기'가 이 값을 저장
    data["saved"] = store_get("report") == payload        # 지금 화면 결과가 저장된 리포트와 같은지

    if data["source_error"]:
        st.caption(f"GA4 연결 실패: {data['source_error']}")

    position_kpis = report_ga4_kpis(ga4) if ga4 else data["position_kpis"]
    kpis = report_sqp_kpis(sqp) if sqp else position_kpis

    # 본문 50:50: 왼쪽 문제 분석 결과(1·2순위), 오른쪽 이미지로 고칠 수 있는 문제(② 가설·③ 광고 소재용).
    # 내부·외부 요인과 세부 내용은 오른쪽 끝 아이콘을 누르면 지금 화면 위에 창으로 열림
    left, right = st.columns(2, gap="medium")
    keys = data["key_problems"]
    for col, rank in ((left, 1), (right, 2)):
        with col:
            report_show_rank_card(data, keys[rank - 1] if len(keys) >= rank else None, rank)
    report_fill_help(help_box, data)

    # 오른쪽 끝 아이콘 (① 탭 안에서만 보이고 화면에 고정: report_style.css .st-key-report-side)
    # 아이콘: 테마 색 한 가지로 보이는 Material 아이콘 (마우스를 올리면 이름)
    # 마우스를 올렸을 때 이름은 report_style.css의 말풍선 (.st-key-report-btn-side-이름)
    buttons = [("internal", ":material/domain:", report_dialog_internal, (data,)),
               ("external", ":material/public:", report_dialog_external, (data,)),
               ("image", ":material/image:", report_dialog_image_fixes, (data,)),
               ("pdf", ":material/picture_as_pdf:", report_dialog_problems, (data, summary, kpis, steps, utm_rows)),
               ("sqp", ":material/manage_search:", report_dialog_sqp, (sqp, kpis)),
               ("comp", ":material/leaderboard:", report_dialog_competitors, (data, position_kpis, sqp)),
               ("ab", ":material/science:", report_dialog_ab, (data,))]
    if worst:
        buttons.insert(2, ("funnel", ":material/filter_alt:", report_dialog_funnel, (ga4["funnel"], worst)))
    with st.container(key="report-side"):
        for name, icon, dialog, args in buttons:
            if st.button("", icon=icon, key=f"report-btn-side-{name}", type="tertiary"):
                dialog(*args)


def report_show_empty(help_box):
    """'불러오기' 전 기본 틀: 결과 박스(1·2순위)와 내부·외부 요인 카드를 같은 모양으로 그리고 내용만 비워 둠.
    분석·Keepa 조회는 하지 않고, 결과 박스 아래에 안내와 마지막 저장 리포트만 보여 줍니다."""
    blank = "&nbsp;"
    saved = store_get("report")
    saved = saved if isinstance(saved, dict) and saved.get("problems") else None
    last = (f'마지막 저장 리포트: {saved.get("analyzed_on", "-")} 분석 · '
            + " / ".join(p["title"] for p in (saved.get("key_problems") or [])[:2]) if saved else "저장된 리포트 없음")
    left, right = st.columns(2, gap="medium")
    for col, rank in ((left, 1), (right, 2)):
        # 결과를 모르니 내부·외부·위험도는 쓰지 않고, 색도 기본색(report-skeleton) - 불러오면 실제 값과 색으로 바뀜
        with col, st.container(border=True, height=REPORT_TOP_HEIGHT, key=f"report-card-rank{rank}"):
            st.markdown(f':material/flag: **{rank}순위 문제**<span class="report-skeleton"></span>', unsafe_allow_html=True)
            st.markdown(report_row_html(f'<span class="report-level">{rank}순위</span>', "", blank, blank,
                                        f'<div class="report-row-q">{blank}</div>'), unsafe_allow_html=True)
    with help_box:
        st.markdown(f"**아직 불러오지 않음** → 오른쪽 위 '불러오기'를 누르면 분석 결과가 채워져요\n\n{last}\n\n" + REPORT_HELP_RULE)


@st.dialog("핵심 문제 전체 · 리포트 다운로드", width="large", icon=":material/picture_as_pdf:")
def report_dialog_problems(data, summary, kpis, steps, utm_rows):
    with st.container(key="report-dialog-body-pdf"):
        report_show_problem_rest(data, summary, kpis, steps, utm_rows)


@st.dialog("검색어 클릭 분석 (노출·클릭: 가상 SQP)", width="large", icon=":material/manage_search:")
def report_dialog_sqp(sqp, kpis):
    with st.container(key="report-dialog-body-sqp"):
        with st.container(key="report-dialog-kpis-sqp"):   # 창 안에서 스크롤해도 KPI 줄은 위에 고정
            report_show_kpis(kpis)
        if sqp:
            report_sqp_show(sqp)
        else:
            st.info("검색어 성과 더미(data/report_sqp_weekly_dummy_202608.json)가 없습니다. "
                    "python -m modules.report.report_sqp_make 로 만들어 주세요.")


@st.dialog("구매 퍼널 (GA4)", width="large", icon=":material/filter_alt:")
def report_dialog_funnel(funnel, worst):
    with st.container(key="report-dialog-body-funnel"):
        report_show_funnel(funnel, worst)


@st.dialog("경쟁 포지션 · 경쟁사 비교", width="large", icon=":material/leaderboard:")
def report_dialog_competitors(data, position_kpis, sqp):
    with st.container(key="report-dialog-body-comp"):
        if sqp:
            with st.container(key="report-dialog-kpis-comp"):   # 창 안에서 스크롤해도 KPI 줄은 위에 고정
                report_show_kpis(position_kpis)
        report_show_competitors(data)


@st.dialog("해결안 A/B 테스트", width="large", icon=":material/science:")
def report_dialog_ab(data):
    with st.container(key="report-dialog-body-ab"):
        report_show_ab(data["ab_tests"], data["ab_daily"], data["ab_upload"])


def report_pct(part, whole):
    """비율(%) 계산. 분모가 0이면 0 (GA4를 막 연결해 지난 기간 데이터가 없을 때)."""
    return part / whole * 100 if whole else 0.0


def report_funnel_steps(funnel):
    """퍼널 단계 사이(이전 → 다음)마다 이번 기간/지난 기간 전환율과 차이를 계산합니다."""
    steps = []
    for a, b in zip(funnel, funnel[1:]):
        now = report_pct(b["now"], a["now"])
        prev = report_pct(b["prev"], a["prev"])
        steps.append({"name": f"{a['stage']} → {b['stage']}", "to": b["stage"],
                      "now": now, "prev": prev, "diff": now - prev})
    return steps


def report_build_summary(data, worst):
    """핵심 문제 요약: 핵심 문제 Top 3와 같은 순서 (위험도 → 심각도) + GA4 퍼널이 있으면 가장 떨어진 단계."""
    parts = [f"{p['rank']}순위 {'검색 클릭' if p['group'] in ('소재 개선', '노출 확대', '제외 검토') else p['type']}: {p['title']}"
             for p in data["key_problems"][:2]]   # 화면 결과 박스와 같은 1·2순위
    if worst:
        parts.append(f"퍼널: '{worst['name']}' 전환율 {worst['prev']:.1f}% → {worst['now']:.1f}%")
    return " / ".join(parts) or "표시할 데이터가 없습니다."


REPORT_STORE_VERSION = "report-v2 (2026-10-25)"   # 다른 탭과 맞춘 데이터 모양. 키를 바꾸면 report_handoff.md와 함께 고침
REPORT_PROFILE_KEYS = ("brand", "product", "type", "price", "currency", "sqm_price", "channels", "qmax", "certs", "tests",
                       "strength", "weakness", "amazon_price", "price_change_90d", "rating", "reviews", "in_stock", "amazon_fees")


def report_store_profile(profile, ad_claims=None):
    """서리 프로필 중 다른 탭이 쓸 칸만 (분석용 세부 표는 ① 화면에만, 광고 문구는 ad_claims에 따로)."""
    out = {k: profile[k] for k in REPORT_PROFILE_KEYS if k in profile}
    # qmax는 분석용(원단·원사 값 포함). 광고에는 원사 0.4가 금지 표현이라, 광고에 써도 되는 문구를 따로 줌
    q = next((c for c in (ad_claims or {}).get("claims", []) if "Q-max" in c.get("topic", "")), None)
    if q:
        out["qmax_ad"] = q["ko"]
        out["qmax_note"] = "광고에는 qmax_ad만 사용 (qmax의 원단·원사 수치는 광고 금지 표현)"
    bt = profile.get("body_temp") or {}
    out["body_temp_rule"] = bt.get("rule", "")   # 광고 표현 규칙 한 줄 (자세한 연구는 경쟁사 DB '체감 vs 실제 체온')
    return out


def report_store_ranking(cs):
    """냉감패드 실적 순위 (냉감 전용 + 1년 판매 신호) - 상품 특징 문구·쿠폰 같은 세부값은 빼고 순위에 필요한 칸만."""
    if not cs:
        return []
    order = [r["brand"] for r in cs["rows"] if r.get("type") == "냉감 전용"]   # rows는 판매 신호 많은 순
    return [{"rank": order.index(r["brand"]) + 1 if r["brand"] in order else None,   # 냉감 전용끼리 순위 (제외 상품은 None)
             "brand": r["brand"], "type": r.get("type", ""), "sales_signal_365": (r.get("rank_drops") or {}).get("365"),
             "summer_rank_median": r.get("rank_root_summer_median"), "reviews": r.get("reviews_now"),
             "monthly_sold": r.get("badge", "-")} for r in cs["rows"]]


def report_store_home_ab(upload):
    """홈 탭이 읽는 ab_test 모양: 직접 올린 A/B 결과가 있을 때만."""
    if not upload:
        return None
    r = upload["result"]
    return {"name": f"메인 이미지 A/B ({upload['file']})", "a": {"ctr": r["ctr_a"], "cvr": r["cvr_a"]},
            "b": {"ctr": r["ctr_b"], "cvr": r["cvr_b"]}, "summary": upload["verdict"]}


def report_compare_text(previous, payload):
    """이전 분석 대비 한 줄: 1·2순위가 바뀌었는지, 안 바뀌었다면 왜인지 (데이터가 같은지)."""
    if not previous:
        return "이전 분석 결과 없음 (오늘이 첫 분석) · 같은 데이터면 같은 결과가 나오도록 계산"
    now = [p["title"] for p in payload["key_problems"][:2]]
    when = f"이전 분석({previous['analyzed_on']})"
    if now != previous["top"]:
        changed = [f"{i}순위 '{t[:24]}'" for i, t in enumerate(now, 1) if i > len(previous["top"]) or previous["top"][i - 1] != t]
        return f"{when}과 달라짐: " + ", ".join(changed) + " 새로 올라옴"
    if previous["as_of"] == payload["as_of"]:
        return f"{when}과 1·2순위 같음 · Keepa 데이터가 같아서 (새 데이터가 들어오면 다시 계산)"
    return f"{when}과 1·2순위 같음 · 새 Keepa 데이터({payload['as_of'].split(': ')[-1]})로 다시 계산해도 같은 문제가 가장 큼"


def report_build_payload(data, summary, worst, utm_rows, utm_worst):
    """홈·가설·광고 소재·광고 타이밍 탭이 읽을 리포트(store "report" = Supabase common_store)를 만듭니다. 저장은 하지 않음
    ('저장하기' 버튼 → report_save_store). 지금 다른 탭이 읽는 키: 가설 problems·sqp·summary / 광고 소재 sqp / 홈 problems·ab_test.
    매출 값(yesterday_sales·sales_delta·sales_7d·kpi)은 실제 매출 데이터(GA4)가 없어 넣지 않습니다."""
    ra = data["review_analysis"] or {}
    payload = {
        "version": REPORT_STORE_VERSION,
        "as_of": data["keepa_status"].split(" · ")[0],   # 데이터 기준 (Keepa 마지막 조회)
        # ── 지금 읽히는 키 (모양 바꾸지 않음) ──
        "summary": summary,                            # 홈·가설: 핵심 문제 한 줄
        "problems": data["problems"],                  # 홈·가설: 문제 목록 (맨 앞이 가장 중요, 가설 탭 계약 필드 포함)
        "sqp": data["sqp_store"],                      # 가설·광고 소재: 검색어 클릭 분석 (가상 SQP) / 없으면 None
        "ab_test": report_store_home_ab(data["ab_upload"]),   # 홈: A/B 결과 (직접 올린 파일이 있을 때만)
        # ── 다른 탭에서 쓰도록 준비한 키 ──
        "key_problems": data["key_problems"],          # 가설: 핵심 문제 Top 3 + 가설 질문(question)
        "image_fixes": data.get("image_fixes") or [],  # 가설·광고 소재: 이미지로 고칠 수 있는 문제 (title, detail, action, use, rank_label)
        "opportunities": [{"title": f["title"], "level": f["level"], "detail": f["detail"]}
                          for f in data["external"] if f["kind"] == "기회"],
        "seori_profile": report_store_profile(data["seori_profile"], data["ad_claims"]),   # 광고 소재: 서리 제품·가격·인증·시험
        "ad_claims": data["ad_claims"],                # 광고 소재: 광고 문구(독일어·한국어·필수 표기)·금지 표현
        "marketing_rules": data["marketing_rules"],    # 광고 소재: 독일 광고 표현 규칙
        "competitor_profiles": data["competitor_profiles"],   # 가설·광고 소재: 경쟁사 강점·약점·Keepa 값·상세페이지 문구
        "competitor_signals": data["competitor_signals"],     # 광고 타이밍: 품절·현재가·가격 변화·쿠폰·구매 배지
        "competitor_ranking": report_store_ranking(data["cooling_sales"]),   # 냉감패드 실적 순위 (냉감 전용 + 1년 판매 신호)
        "review_analysis": {k: ra[k] for k in ("seori", "leader", "five_star_needed", "findings", "metric", "target", "rule", "shop")
                            if k in ra} or None,      # 가설: 리뷰 문제 근거·목표
        "data_rules": data["data_rules"],              # 공통: 지표별 비교 기준·출처·기준일·구분(실제/가정/가상)
        "ab_upload": data["ab_upload"],                # ① 탭 자체 보관용: 올린 A/B 결과 파일 (새로고침 후에도 유지, 다른 탭은 ab_test 사용)
        # GA4 연결 후 추가할 키: funnel_worst, utm, utm_worst, kpi, yesterday_sales, sales_delta, sales_7d
        # [보류] ③ 탭 결과 아침 A/B 분석(ab_daily)은 ③ 탭 저장 기능이 생기면 추가
    }
    if utm_rows:   # GA4가 연결됐을 때만
        payload.update({"funnel_worst": worst["name"] if worst else "", "utm": utm_rows,
                        "utm_worst": utm_worst["channel"] if utm_worst else ""})
    # 이전 분석과 비교: 오늘 첫 분석이면 저장돼 있던 결과가 '이전', 같은 날 다시 열면 그 이전 값을 유지
    saved = store_get("report")
    saved = saved if isinstance(saved, dict) else {}
    today = date.today().isoformat()
    if saved.get("analyzed_on") and saved["analyzed_on"] != today:
        previous = {"analyzed_on": saved["analyzed_on"], "as_of": saved.get("as_of", ""),
                    "top": [p["title"] for p in (saved.get("key_problems") or [])[:2]]}
    else:
        previous = saved.get("previous")
    payload.update({"analyzed_on": today, "previous": previous})
    # ② 가설 탭이 리포트 맨 아래에 붙인 선택 가설은 ①이 다시 저장해도 지우지 않음 (③은 ①+② 리포트 하나만 읽음)
    hyp = saved.get("hypothesis")
    if isinstance(hyp, dict):
        hyp = dict(hyp)
        # 같은 문제인지는 제목이 아니라 '분류 + 지표'로 판단 (제목에 숫자가 있어 값이 바뀌면 제목도 바뀜: 리뷰 31건 → 93건)
        def ident(p):
            return (p.get("sqp_type") or p.get("group"), (p.get("plan") or {}).get("kpi") or p.get("title"))
        prob = hyp.get("problem") or {}
        hyp["stale"] = bool(prob) and ident(prob) not in [ident(p) for p in payload["problems"]]
        hyp["stale_reason"] = "① 분석이 바뀌어 이 가설의 문제가 지금 문제 목록에 없음 → ②에서 다시 선택 필요" if hyp["stale"] else ""
        # 같은 문제지만 지금 값·목표 값이 바뀜 (예: 리뷰 31건 → 93건) → 가설 숫자가 옛 값이라 ②에서 다시 선택하면 새 값
        cur = next((p for p in payload["problems"] if ident(p) == ident(prob)), None) if not hyp["stale"] else None
        old_plan, new_plan = prob.get("plan") or {}, (cur or {}).get("plan") or {}
        hyp["values_changed"] = bool(cur) and any(old_plan.get(k) != new_plan.get(k) for k in ("now", "goal"))
        hyp["values_changed_reason"] = (f"같은 문제지만 값이 바뀜 ({old_plan.get('kpi')} 지금 {old_plan.get('now')} → {new_plan.get('now')}, "
                                        f"목표 {old_plan.get('goal')} → {new_plan.get('goal')}) → ②에서 다시 선택하면 새 값으로 가설"
                                        if hyp["values_changed"] else "")
        payload["hypothesis"] = hyp
    data["compare"] = report_compare_text(previous, payload)
    return payload


def report_save_store(payload):
    """'저장하기' 버튼: 리포트를 store("report")에 저장 → ② 가설 탭(그리고 홈·③)에서 읽음."""
    store_set("report", payload)
    st.session_state["report-saved-at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    st.session_state["report-saved-toast"] = True


def report_click_load():
    """'불러오기' 버튼: 이번 접속에서 분석을 실행해 화면을 채움 (다시 누르면 최신 값으로 다시 계산)."""
    st.session_state[REPORT_LOADED_KEY] = True
    st.session_state["report-just-loaded"] = True   # 이번 한 번만: 로딩 표시 + 글자가 차례로 나타나는 효과
    st.session_state["report-load-count"] = st.session_state.get("report-load-count", 0) + 1


def report_click_save():
    """'다음으로': 리포트를 저장하고 ② 가설 탭으로 넘어감."""
    payload = st.session_state.get("report-current-payload")
    if payload:
        report_save_store(payload)
        # ② 탭은 넘어가자마자 이 리포트로 가설 후보를 만들도록 '불러오기'를 누른 상태로 (로딩·나타나는 효과 포함)
        st.session_state["hypothesis-loaded"] = True
        st.session_state["hypothesis-just-loaded"] = True
        report_goto_tab("hypothesis")


def report_goto_tab(code: str) -> None:
    """왼쪽 탭 줄에서 code 탭을 선택 (app.py st.tabs key="main_tabs"의 탭 이름과 같은 모양: 아이콘 + 띄어쓰기를 줄바꿈 없는 공백으로)."""
    from common.common_layout import LAYOUT_TABS   # 순환 import를 피하려고 함수 안에서
    tab = next((t for t in LAYOUT_TABS if t["code"] == code), None)
    if tab:
        st.session_state["main_tabs"] = f"{tab['icon']} {tab['label'].replace(' ', chr(160))}"


def report_problem_html(p):
    return (f'<div class="report-factor">'
            f'<span class="report-level report-level-{REPORT_LEVEL_CLASS[p["level"]]}">{p["rank"]}순위 · {p["type"]}</span>'
            f'<span class="report-tag">{p["group"]}</span><b>{p["title"]}</b>'
            f'<div class="report-desc">근거: {p["detail"]}</div>'
            + (f'<div class="report-desc">심각도 {p["severity"]["score"]:.2f} = {p["severity"]["basis"]} (같은 위험도 안의 순서)</div>'
               if p.get("severity") else "")
            + f'<div class="report-desc">→ 가설 탭 질문: <b>{p["question"]}</b></div></div>')


def report_row_html(badge, tag, title, detail, extra=""):
    """읽기 쉬운 한 줄: 왼쪽 배지, 오른쪽 [분류] 제목 / 근거 2줄 (마우스를 올리면 전체) / 덧붙임."""
    full = str(detail).replace('"', "&quot;")
    return (f'<div class="report-row"><div class="report-row-badge">{badge}</div><div>'
            f'<div class="report-row-title"><span class="report-tag">{tag}</span>{title}</div>'
            f'<div class="report-desc report-clamp" title="{full}">{detail}</div>{extra}</div></div>')


def report_show_rank_card(data, k, rank):
    """N순위 문제 1개를 자세히: 근거 전체 · 심각도 · ③ 이미지로 고치기 · ② 가설 재료(행동·KPI·테스트) · 가설 탭 질문."""
    with st.container(border=True, height=REPORT_TOP_HEIGHT, key=f"report-card-rank{rank}"):
        st.markdown(f':material/flag: **{rank}순위 문제**<span class="report-loaded-mark"></span>' + report_reveal_mark(data),
                    unsafe_allow_html=True)
        if not k:
            st.markdown('<div class="report-desc">이 순위에 들어갈 문제가 없어요</div>', unsafe_allow_html=True)
            return
        sev = k.get("severity") or {}
        st.markdown(
            f'<div class="report-detail-head"><span class="report-level report-level-{REPORT_LEVEL_CLASS[k["level"]]}">{rank}순위 · {k["type"]}</span>'
            f'<span class="report-tag">{k["group"]}</span></div>'
            f'<div class="report-detail-title">{k["title"]}</div>'
            f'<div class="report-desc"><b>근거</b> {k["detail"]}</div>'
            + (f'<div class="report-desc">심각도 {sev["score"]:.2f} = {sev["basis"]}</div>' if sev else ""),
            unsafe_allow_html=True)
        fix = k.get("image_fix")
        if fix:
            st.markdown(
                f'<div class="report-detail-box report-detail-img"><div class="report-detail-label">'
                + (f'③ 이미지로 고치기 · {fix["kind"]} · ③ 탭에서 바로 제작' if fix.get("stage3") else f'이미지로 고치기 · {fix["kind"]}')
                + f'<span class="report-use">{" · ".join(fix["use"])}</span></div>'
                f'<b>{fix["title"]}</b><div class="report-desc">{fix["action"]}</div></div>', unsafe_allow_html=True)
        else:   # 이미지로 고칠 수 있는 문제가 2개보다 적으면 다음 순서 문제로 채움 (③ 이미지 제작과는 바로 이어지지 않음)
            st.markdown('<div class="report-detail-box"><div class="report-detail-label">이미지로 고치기</div>'
                        '<div class="report-desc">지금 데이터로는 이미지로 고칠 문제가 이것보다 적어, 위험도 다음 순서 문제를 보여 줘요 '
                        '(③ 이미지 제작과는 바로 이어지지 않음)</div></div>', unsafe_allow_html=True)
        plan = next((p.get("plan") for p in data["problems"] if p["title"] == k["title"] and p.get("plan")), None)
        if plan:
            unit = plan.get("unit") or ""
            rows = [("행동", plan.get("action")), ("KPI", f'{plan.get("kpi")} {plan.get("now")}{unit} → {plan.get("goal")}{unit}'),
                    ("테스트", plan.get("test")), ("기간·표본", plan.get("period"))]
            st.markdown('<div class="report-detail-box"><div class="report-detail-label">② 가설 재료</div>'
                        + "".join(f'<div class="report-detail-row"><span>{a}</span><div>{b}</div></div>' for a, b in rows if b)
                        + "</div>", unsafe_allow_html=True)
        st.markdown(f'<div class="report-row-q">→ 가설 탭 질문: <b>{k["question"]}</b></div>', unsafe_allow_html=True)


def report_fill_help(help_box, data):
    """제목 줄 물음표 안: 저장 상태 · 이전 분석 비교 · 3순위 위치 · 순위 기준."""
    saved_text = (f"**저장됨**{' (' + st.session_state['report-saved-at'] + ')' if st.session_state.get('report-saved-at') else ''} · ② 가설 탭에서 확인 가능"
                  if data.get("saved") else "**아직 저장 안 됨** → 오른쪽 위 '다음으로'를 누르면 저장하고 ② 가설 탭으로 넘어가요")
    rest = len(data["key_problems"]) - 2
    lines = [saved_text] + ([data["compare"]] if data.get("compare") else []) \
        + ([f"3순위부터 {rest}개는 오른쪽 PDF 아이콘"] if rest > 0 else []) + [REPORT_HELP_RULE]
    with help_box:
        st.markdown("\n\n".join(lines))


def report_show_stage3_table(data):
    """모든 문제의 ① → ② → ③ 연결 분석 (report_stage3_check)."""
    rows = [{"③": "✅" if (p.get("stage3") or {}).get("ok") else "—", "문제": p["title"],
             "② 가설": "가능" if p.get("plan") else "불가", "이유": (p.get("stage3") or {}).get("why", "")} for p in data["problems"]]
    ok = sum(r["③"] == "✅" for r in rows)
    st.markdown(f"**① → ② → ③ 연결 분석** · 전체 {len(rows)}개 중 ② 가설 {sum(r['② 가설'] == '가능' for r in rows)}개, ③까지 {ok}개")
    st.dataframe(rows, hide_index=True, width="stretch", key="report-table-stage3")


@st.dialog("이미지로 고칠 수 있는 문제 전체", width="large", icon=":material/image:")
def report_dialog_image_fixes(data):
    """메인 이미지·광고 이미지 문구·상세 이미지 (② 가설·③ 광고 소재에서 사용). N순위 = 화면 1·2순위 카드와 같은 문제."""
    fixes = data.get("image_fixes") or []
    st.caption(f"사진·배너·상세 이미지로 고칠 수 있는 것 {len(fixes)}개 · ③ 탭에서 바로 쓸 수 있는 메인 이미지가 맨 위")
    with st.container(key="report-card-image"):
        st.markdown("".join(
            report_row_html('<span class="report-level report-level-img">'
                            + (f'{f["rank_label"]}' if f["rank_label"] else "이미지") + "</span>",
                            " · ".join(f["use"]), f["title"], f'근거: {f["detail"]} ({f["source"]})',
                            f'<div class="report-row-q">→ 이렇게: <b>{f["action"]}</b></div>')
            for f in fixes) or '<div class="report-desc">지금 데이터로는 이미지로 고칠 문제가 없어요</div>', unsafe_allow_html=True)
    report_show_stage3_table(data)


@st.dialog("내부 요인 전체", width="large", icon=":material/domain:")
def report_dialog_internal(data):
    st.caption(f'서리 = {data["seori_proxy"] or "-"} 실적 가정 · {report_keepa_age_text(data)}' + (" · 검색어 분석(가상)" if data.get("sqp") else "")
               + " · N순위 = 문제 분석 결과 순위 대상")
    items = data["internal"]
    st.markdown("".join(report_factor_row(f, f["group"]) for f in items) or '<div class="report-desc">표시할 내부 요인이 없습니다.</div>',
                unsafe_allow_html=True)


@st.dialog("외부 요인 전체", width="large", icon=":material/public:")
def report_dialog_external(data):
    items = data["external"]
    st.caption(f'위협 {sum(f["kind"] == "위협" for f in items)}개 · 기회 {sum(f["kind"] == "기회" for f in items)}개 · Keepa·Open-Meteo·독일 DB'
               " · N순위 = 문제 분석 결과 순위 대상")
    for kind in ("위협", "기회"):
        sub = [f for f in items if f["kind"] == kind]
        if sub:
            st.markdown(f"**{'⚠️ 위협' if kind == '위협' else '✨ 기회'}** ({len(sub)})")
            st.markdown("".join(report_factor_row(f, f"{f['kind']} · {f['group']}") for f in sub), unsafe_allow_html=True)


def report_show_problem_rest(data, summary, kpis, steps, utm_rows):
    """토글 안: 핵심 문제 전체, 경쟁 포지션 핵심 문제, PDF 리포트 다운로드."""
    with st.container(border=True):
        st.markdown("".join(report_problem_html(p) for p in data["key_problems"]), unsafe_allow_html=True)
        st.caption("이 결과는 다른 탭(홈, 가설, 광고 소재, 광고 타이밍)에서 store_get(\"report\")로 읽을 수 있습니다.")
        with st.expander(":material/rule: 데이터 기준·신뢰도 (같은 지표는 항상 같은 기준으로 계산)", expanded=False):
            st.dataframe(data["data_rules"], hide_index=True, width="stretch", key="report-table-data-rules")
        report_download_pdf(data, kpis, summary, steps, utm_rows)


def report_ga4_kpis(ga4):
    """GA4 연결 시 KPI 4개: 방문, 주문, 전환율(이전 기간 대비), 매출."""
    funnel, utm = ga4["funnel"], ga4["utm"]
    visits, orders = funnel[0], funnel[-1]
    conv_now, conv_prev = report_pct(orders["now"], visits["now"]), report_pct(orders["prev"], visits["prev"])

    def delta(now, prev):
        return f"{report_pct(now, prev) - 100:+.0f}%" if prev else "이전 기간 없음"

    return [
        {"label": "방문 (30일)", "value": f"{visits['now']:,}", "badge": delta(visits["now"], visits["prev"]),
         "good": visits["now"] >= visits["prev"]},
        {"label": "주문 (30일)", "value": f"{orders['now']:,}", "badge": delta(orders["now"], orders["prev"]),
         "good": orders["now"] >= orders["prev"]},
        {"label": "전환율", "value": f"{conv_now:.2f}%", "badge": f"{conv_now - conv_prev:+.2f}%p",
         "good": conv_now >= conv_prev},
        {"label": "매출 (30일)", "value": f"€{sum(r['revenue'] for r in utm):,}", "badge": "GA4", "good": True},
    ]


def report_show_kpis(kpis):
    """한 줄 높이의 작은 KPI 카드 (아래 분석 내용이 첫 화면에 보이도록)."""
    for col, k in zip(st.columns(len(kpis) or 1), kpis):
        with col:
            tip = str(k.get("tip") or k["badge"]).replace('"', "&quot;")
            badge = (f'<span class="ui-delta {"up" if k["good"] else "down"}" title="{tip}">{k["badge"]}</span>'
                     if k["badge"] else "")
            st.markdown(f'<div class="report-kpi" title="{tip}"><span class="report-kpi-label">{k["label"]}</span>'
                        f'<span class="report-kpi-value">{k["value"]}</span>{badge}</div>', unsafe_allow_html=True)


def report_factor_row(f, tag):
    # 결과 박스 순위 대상(4개)이면 제목 앞에 'N순위' 표시 → 결과 박스와 카드의 같은 문제를 바로 연결
    rank = f'<span class="report-rank-chip">{f["rank_label"]}</span>' if f.get("rank_label") else ""
    return report_row_html(f'<span class="report-level report-level-{REPORT_LEVEL_CLASS[f["level"]]}">'
                           f'{REPORT_LEVEL_DOTS[f["level"]]} {f["level"]}</span>', tag, rank + f["title"], f["detail"])


def report_reveal_mark(data):
    """불러오기 직후 한 번만: 카드 안 글자가 차례로 나타나게 하는 표시 (report_style.css .report-reveal)."""
    return '<span class="report-reveal"></span>' if data.get("reveal") else ""


def report_show_funnel(funnel, worst):
    # 오렌지(accent)는 화면당 1곳: 가장 크게 떨어진 단계에만 사용 (design.md 2-3)
    colors = [ui.THEME["accent"] if f["stage"] == worst["to"] else ui.THEME["primary_soft"] for f in funnel]
    colors[0] = ui.THEME["primary"]
    fig = go.Figure(go.Funnel(y=[f["stage"] for f in funnel], x=[f["now"] for f in funnel],
                              textinfo="value+percent previous", marker=dict(color=colors),
                              connector=dict(fillcolor=ui.THEME["line"])))
    fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=ui.THEME["text"]))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key="report-chart-funnel")
    st.markdown(f'<div class="report-desc">이전 기간보다 가장 크게 떨어진 단계: <b>{worst["name"]}</b> '
                f'({worst["prev"]:.1f}% → {worst["now"]:.1f}%, {worst["diff"]:+.1f}%p, GA4)</div>',
                unsafe_allow_html=True)


def report_keepa_age_text(data):
    """'Keepa 마지막 조회: 날짜 (N일 전 · 자동 갱신 꺼짐)' - 데이터가 오래됐는지, 아침 자동 갱신이 도는지 한눈에."""
    last = data["keepa_status"].split(" · ")[0]
    try:
        age = (date.today() - date.fromisoformat(str(data.get("keepa_time", ""))[:10])).days
    except ValueError:
        return last
    extra = ["오늘" if age == 0 else f"{age}일 전"]
    if str(data.get("keepa_auto", "")).startswith("아침 자동 갱신 꺼짐"):
        extra.append("자동 갱신 꺼짐")
    return f"{last} ({' · '.join(extra)})"


def report_show_competitors(data):
    """냉감패드 경쟁사 비교: 판매 순위 상위 2개사 + 서리(가정 3위). 냉감패드 제품 정보만 (경쟁사 DB + Keepa)."""
    rows = data["competitors_full"]
    month = f"{int(data['keepa_time'][5:7])}월" if str(data.get("keepa_time", ""))[5:7].isdigit() else "현재"
    now_col = f"현재 순위 ({month})"   # Keepa 마지막 조회 달 (아침 자동 갱신으로 달이 바뀌어도 맞게)
    off_season = month == "현재" or int(month[:-1]) not in (6, 7, 8)
    own_price = data["seori_profile"].get("amazon_price")
    with st.container(border=True):
        st.markdown(f":material/leaderboard: **냉감패드 경쟁사 비교** · 판매 순위 상위 2개사 + 서리(가정 3위)  \n"
                    f'<span class="report-desc">{data["keepa_status"]} · {data["keepa_auto"]}</span>',
                    unsafe_allow_html=True)
        report_show_keepa_fetch()
        if not rows:
            st.info("공통 경쟁사 DB(data/common_competitor_seori_202610.csv)가 없습니다.")
            return
        detail = report_keepa_detail().get("items", {})
        summer = {a: d.get("rank_root_summer_median") for a, d in detail.items()}   # 보조: 2026년 6~8월 순위 중앙값
        sig = {a: (d.get("rank_drops") or {}).get("365") for a, d in detail.items()}   # 순위 기준: 1년 판매 신호
        yago = {a: (d.get("price") or {}).get("year_ago") for a, d in detail.items()}   # 작년 같은 날 가격
        table = []
        shop_n = report_shop_review_count()   # 서리 리뷰 수 = Amazon + 자사몰 (경쟁사는 Amazon만)
        for r in rows:
            k = r.get("keepa") or {}
            seori = r["kind"] == "자사"
            shop_total = (k.get("reviews") or 0) + shop_n
            table.append({
                "순위": "3위 (가정)" if seori else (f"{r['rank']}위" if r.get("rank") else r["label"]),
                "브랜드": r["brand"], "냉감패드 제품": r["product"],
                "1년 판매 신호": f"{sig[r.get('asin')]}회" if sig.get(r.get("asin")) is not None else "-",
                "여름 순위 (6~8월)": f"{summer[r.get('asin')]:,}" if summer.get(r.get("asin")) else "-",
                now_col: f"{k['rank']:,}" if k.get("rank") else "-",
                "현재가": f"€{k['price']:.2f}" if k.get("price") else (f"€{r['db_price']:.2f} (권장가)" if seori and r["db_price"] else "-"),
                # 가격 변화는 계절이 섞이지 않게 작년 같은 날과 비교 (데이터 기준: 가격 변화)
                "작년 대비": (f"{(k['price'] / yago[r.get('asin')] - 1) * 100:+.0f}%"
                              if k.get("price") and yago.get(r.get("asin")) and not seori else "-"),   # 서리는 가정 가격이라 작년 비교 없음
                "평점": f"{k['rating']:.1f}" if k.get("rating") else "-",
                "리뷰 수": (f"{shop_total:,} (Amazon {k.get('reviews') or 0} + 자사몰 {shop_n:,})" if seori and shop_n
                           else f"{k['reviews']:,}" if k.get("reviews") is not None else ("0건" if seori else "-")),
                "㎡당 가격": (f"€{r['keepa_sqm']:.1f}" if r.get("keepa_sqm") else f"€{r['sqm_price']:.1f}" if r["sqm_price"] else "-"),
                "Q-max": (r["qmax"] or "-").split(" · ")[0].split(" (")[0],
            })
        st.dataframe(table, hide_index=True, width="stretch", key="report-table-competitors",
                     column_config={"냉감패드 제품": st.column_config.TextColumn(width="medium")})
        st.markdown('<div class="report-desc">순위 기준: 냉감 전용 상품의 1년 판매 신호(Keepa 순위가 좋아진 횟수 = 판매 횟수 추정), 양면(2-in-1)·비냉감 혼재 상품 제외 · '
                    + (f'현재 순위는 비수기({month}) 값이라 순서가 다를 수 있음 · ' if off_season else '')
                    + f'서리 = 독일 냉감패드 실적 3위 {REPORT_SEORI_PROXY}라고 가정해 판매 순위·평점은 {REPORT_SEORI_PROXY}의 Keepa 실적, '
                    + '리뷰 수는 Amazon + 자사몰 합산(경쟁사는 Amazon만), '
                    + (f'가격은 서리 판매가 €{own_price:.2f} (가정, 검색어 분석과 같은 값) · ' if own_price else '')
                    + '제품명·냉감 방식·Q-max·강점·약점은 서리 기획 · ㎡당 가격: 현재가 기준</div>',
                    unsafe_allow_html=True)
        with st.expander("냉감패드 항목별 비교 (서리 목표 vs 상위 2개사 최고)", expanded=False):
            st.dataframe([{"항목": c["item"], "가중치": f"{c['weight']:.0%}", "서리 (목표)": c["seori"],
                           "상위 2개사 최고": f"{c['best_brand']} {c['best']:.0f}",
                           "차이": f"{c['seori'] - c['best']:+.0f}" if c["seori"] is not None else "-", "메모": c["memo"]}
                          for c in data["criteria"]], hide_index=True, width="stretch", key="report-table-criteria")
        report_show_seori_status(data)
        report_show_review(data["review_analysis"])
        report_show_cooling_sales(data.get("cooling_sales"))
        with st.expander("냉감패드 강점·약점 (경쟁사 DB)", expanded=False):
            for r in rows:
                st.markdown(f"**{r['brand']}** · {r['product']} · 소재: {r['material'] or '-'}  \n"
                            f'<span class="report-desc">강점: {r["strength"]}<br>약점: {r["weakness"]}</span>',
                            unsafe_allow_html=True)


def report_show_seori_status(data):
    """서리 인증·시험 현황 (가정: 국내 기업 자료 기반 완제품 판매 중). 보완이 남은 항목은 내부/외부 요인으로 분석에 반영."""
    profile = data["seori_profile"]
    with st.expander("서리 인증·시험 현황 (가정: 국내 기업 자료 기반 완제품)", expanded=False):
        st.dataframe([{"인증·규제": c["item"], "구분": c["group"], "상태": c["status"], "근거": c.get("basis", "")}
                      for c in profile.get("certs", [])], hide_index=True, width="stretch", key="report-table-seori-certs")
        st.dataframe([{"시험 항목": t["item"], "결과": t["result"] or "미실시", "완료": "O" if t["done"] else "보완 필요"}
                      for t in profile.get("tests", [])], hide_index=True, width="stretch", key="report-table-seori-tests")
        if profile.get("data_check"):
            st.markdown("**국내 기업 데이터로 채울 수 있는지**")
            st.dataframe([{"항목": d["item"], "국내 데이터": d["domestic"], "국내 내용": d["detail"],
                           "다른 기업·해외": d.get("other", "-"), "적용": d["use"]}
                          for d in profile["data_check"]], hide_index=True, width="stretch", key="report-table-seori-check")
        ref = profile.get("finished_qmax_ref")
        if ref:
            st.markdown("**국내 다른 기업 Q-max 광고 수치 vs 완제품 실측 등급**")
            st.dataframe([{"브랜드": r["brand"], "광고 Q-max": r["value"], "조건": r["cond"], "완제품 실측(10℃) 등급": r["grade"]}
                          for r in ref["rows"]], hide_index=True, width="stretch", key="report-table-seori-qmaxref")
            st.markdown(f'<div class="report-desc">{ref["finding"]}<br>서리: {ref["seori_estimate"]}<br>'
                        f'광고 시정 사례: {ref["ad_cases"]}<br>사용 범위: {ref.get("usage", "")}<br>출처: {ref["source"]}</div>', unsafe_allow_html=True)
        ad = profile.get("ad_check")
        if ad:
            st.markdown("**완제품 Q-max 0.207 광고 사용 가능 여부**")
            st.markdown(f'<div class="report-desc">가상 광고(AI 시안): {ad["mock_ad"]}<br>실제 광고: {ad["real_ad"]}<br>'
                        f'쓰면 안 되는 것: {ad.get("not_ok", "-")}<br>독일어 표기 형식: {ad["claim_de"]}<br>근거: {ad["rules"]}</div>',
                        unsafe_allow_html=True)
        claims = data.get("ad_claims") or {}
        if claims.get("claims"):
            st.markdown("**나중에 광고에 넣을 서리 문구** (③ 광고 소재로 전달: `ad_claims`)")
            st.dataframe([{"주제": c["topic"], "독일어": c["de"], "한국어": c["ko"], "필수 표기": c["must"]} for c in claims["claims"]],
                         hide_index=True, width="stretch", key="report-table-ad-claims")
            st.markdown(f'<div class="report-desc">금지: {" · ".join(claims["forbidden"])}<br>장면: {claims["allowed_scenes"]}</div>',
                        unsafe_allow_html=True)
        bt = profile.get("body_temp")
        if bt:
            st.markdown("**체감(피부 표면) 온도 vs 실제 체온**")
            st.dataframe([{"구분": r["type"], "대상": r["target"], "하강 값": r["value"], "방법": r["method"],
                           "측정 주체": r["by"], "출처": r["source"]} for r in bt["rows"]],
                         hide_index=True, width="stretch", key="report-table-seori-bodytemp")
            st.markdown(f'<div class="report-desc">{bt["summary"]}<br>{bt["rule"]}</div>', unsafe_allow_html=True)
            if bt.get("health"):
                st.markdown("**실제 체온 변화가 몸에 주는 영향**")
                st.dataframe([{"연구": h["study"], "체온 변화": h["core"], "영향": h["effect"]} for h in bt["health"]],
                             hide_index=True, width="stretch", key="report-table-seori-health")
                st.markdown(f'<div class="report-desc">{bt["health_summary"]}</div>', unsafe_allow_html=True)
            if bt.get("steps"):
                st.markdown("**실제 체온 0.5℃ 단위 영향**")
                st.dataframe([{"체온 변화": x["change"], "의미": x["meaning"], "근거": x["basis"]} for x in bt["steps"]],
                             hide_index=True, width="stretch", key="report-table-seori-steps")
                st.markdown(f'<div class="report-desc">{bt.get("expert_note", "")}<br>{bt.get("apply", "")}<br>{bt.get("skin_note", "")}</div>', unsafe_allow_html=True)
        st.caption("가정 파일: modules/report/data/report_seori_assumption_202610.json · 상태가 '일부·미착수·보완 필요'인 항목은 "
                   "내부 요인(서리가 고칠 것)과 외부 위협(규제·시장이 요구하는 것)으로 나눠 위 분석에 반영했습니다.")


def report_show_keepa_fetch():
    """Keepa 최신값 조회: 예상 토큰·남은 한도 안내 → PIN + 동의 → 1회 조회. (토큰 한도 보호)"""
    usage = report_keepa_usage()
    left = usage["budget"] - usage["used"]
    with st.expander(f":material/refresh: Keepa 최신값 조회 (남은 한도 {left}/{usage['budget']}토큰)", expanded=False):
        ok, reason = report_keepa_can_fetch()
        st.caption(f"이번 조회 예상 사용량: 약 {report_keepa_estimate()}토큰 · 꼭 필요할 때만 조회하세요.")
        if not ok:
            st.caption(f"조회 불가: {reason}")
        else:
            pin = st.text_input("확인 PIN", type="password", key="report-keepa-pin")
            agree = st.checkbox(f"약 {report_keepa_estimate()}토큰을 사용해 조회하는 데 동의합니다", key="report-keepa-agree")
            if st.button("Keepa 조회 실행", key="report-btn-keepa-fetch", disabled=not (pin and agree)):
                try:
                    used = report_keepa_fetch_and_save(pin)
                    st.success(f"조회했습니다. 사용 토큰 {used}")
                    st.rerun()
                except Exception as err:   # RuntimeError만 문구를 보여 주고, 그 밖의 오류는 종류만 (키 노출 방지)
                    st.error(str(err) if isinstance(err, RuntimeError) else f"조회 실패 ({type(err).__name__})")
        st.caption("사용 기록: " + " / ".join(f"{x['date']} {x['tokens']}토큰 ({x['what']})" for x in usage["log"]))


def report_show_ab(ab_tests, daily, upload=None):
    """해결안 A/B: ③ 광고 소재 탭 결과를 매일 아침 분석한 값 + data/report_ab_tests.json의 실제 결과."""
    with st.container(border=True):
        if daily:
            st.markdown(":material/science: **③ 탭 실행 결과 분석** · 매일 아침(한국 08:00 이후 첫 접속)  \n"
                        f'<span class="report-desc">분석 기준일 {daily["day"]} · 분석 {daily["analyzed_at"]}'
                        + (f' · ③ 탭 저장 {daily["media_updated_at"]}' if daily.get("media_updated_at") else "")
                        + "</span>", unsafe_allow_html=True)
        else:
            # [보류] ③ 탭 결과 아침 자동 분석은 꺼져 있음 (report_data.py의 [보류] 주석 참고)
            st.markdown(":material/science: **해결안 A/B 분석** · 결과 파일(CSV)을 올려 바로 분석  \n"
                        '<span class="report-desc">③ 탭 실행 결과(UTM·GA4·A/B)의 매일 아침 자동 분석은 ③ 탭 연동 후 사용 예정 (지금은 꺼짐)</span>',
                        unsafe_allow_html=True)
        report_show_ab_upload(upload)
        daily = daily or {}
        r = daily.get("result")
        if r:
            st.markdown(f'<div class="report-desc">검색어 {r["query"]} · 기간 {r["period"]} · 출처 {r["source"]}</div>',
                        unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                ui.kpi_card("클릭률 A → B", f"{r['ctr_a']}% → {r['ctr_b']}%",
                            f"{r['ctr_lift']:+.1f}%" if r["ctr_lift"] is not None else None, sub=f"유의확률 p={report_ab_p(r['p_ctr'])}")
            with c2:
                ui.kpi_card("구매 전환율 (안전장치)", f"{r['cvr_a']}% → {r['cvr_b']}%",
                            sub="기준 통과" if r["cvr_ok"] else "기준 미달")
            with c3:
                cac = (f"CAC €{r['cac_before']} → €{r['cac_after']}" if r.get("cac_before") and r.get("cac_after") else "")
                ui.kpi_card("판정", f"{r['winner']} 안", sub=cac or " ")
            st.markdown(f"**결과** · {daily['verdict']}")
            if daily.get("change"):
                st.caption(daily["change"])
            if daily.get("history"):
                with st.expander(f"지난 분석 ({len(daily['history'])}일)", expanded=False):
                    st.dataframe([{"기준일": h["day"], "판정": h["winner"], "B 클릭률(%)": h["ctr_b"], "유의확률": h["p_ctr"]}
                                  for h in daily["history"]], hide_index=True, width="stretch", key="report-table-ab-history")
        elif daily:
            st.caption("아직 ③ 광고 소재 탭이 저장한 A/B 결과가 없습니다. ③ 탭에서 store_set(\"media\", {\"ab_result\": ..., "
                       "\"utm\": ..., \"updated_at\": ...})로 저장하면 다음 날 아침부터 여기서 분석합니다 (형식: report.md).")
        if daily.get("utm"):
            st.markdown("**유입 채널(UTM) 성과** · ③ 탭 저장값" + (f" · 전환율 최저: {daily['utm_worst']}" if daily["utm_worst"] else ""))
            st.dataframe([{"채널": u["channel"], "캠페인": u["campaign"], "방문": u["sessions"], "주문": u["orders"],
                           "전환율(%)": round(u["cvr"], 2), "방문 비중(%)": round(u["share"], 1)} for u in daily["utm"]],
                         hide_index=True, width="stretch", key="report-table-ab-utm")
        for t in ab_tests:
            a, b = t["variants"]
            r = t["result"]
            st.markdown(f'<div class="report-desc"><b>{t["name"]}</b> · 문제: {t["problem"]} · 가설: {t["hypothesis"]} · '
                        f'지표: {t["metric"]} · 기간: {t["period"]}</div>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                ui.kpi_card(a["name"], f"{r['rate_a']:.1f}%", sub=f"{a['desc']} · {a['conversions']:,}/{a['users']:,}")
            with c2:
                ui.kpi_card(b["name"], f"{r['rate_b']:.1f}%", f"{r['lift']:+.1f}%",
                            sub=f"{b['desc']} · {b['conversions']:,}/{b['users']:,}")
            with c3:
                ui.kpi_card("유의확률 (p)", f"{r['p']:.4f}",
                            sub="유의수준 0.05 기준 " + ("유의함" if r["significant"] else "유의하지 않음"))


def report_show_cooling_sales(cs):
    """냉감패드 실적만 보기: 하위 카테고리 순위·여름 순위·판매 신호 (Keepa 상세 조회)."""
    if not cs:
        return
    with st.expander(":material/trending_up: 냉감패드 실적만 보기 (하위 카테고리·여름 순위, Keepa 상세)", expanded=False):
        st.dataframe([{"브랜드": c["brand"], "하위 카테고리": c["sub_category"],
                       "하위 순위 (지금 / 여름 중앙값)": f"{c['rank_sub_now'] or '-'} / {c['rank_sub_summer_median'] or '-'}",
                       "전체 순위 여름 중앙값": f"{c['rank_root_summer_median']:,}" if c["rank_root_summer_median"] else "-",
                       "1년 판매 신호": c["rank_drops"]["365"], "월 구매 배지": c["badge"],
                       "냉감 변형 / 전체": f"{c['cooling_variations']} / {c['variations']}", "출시": c["listed_since"]}
                      for c in cs["rows"]], hide_index=True, width="stretch", key="report-table-cooling-sales")
        st.markdown("\n".join(f"- {f}" for f in cs["findings"]))
        st.caption(cs["note"])


def report_show_ab_upload(upload):
    """A/B 결과 CSV를 올리면 바로 분석합니다 (Amazon 실험 도구·광고·판매 리포트 값을 양식에 옮겨 적은 파일)."""
    with st.expander(":material/upload_file: 결과 파일 올려서 바로 분석 (CSV)", expanded=bool(upload)):
        st.download_button("양식 내려받기 (.csv)", REPORT_AB_TEMPLATE.encode("utf-8-sig"), file_name="report_ab_template.csv",
                           key="report-btn-ab-template")
        f = st.file_uploader("A/B 결과 CSV", type=["csv"], key="report-upload-ab")
        if f is not None and (not upload or upload.get("file") != f.name):
            try:
                ab = report_ab_parse_csv(f.getvalue().decode("utf-8-sig"))
                r = report_ab_analyze(ab)
                upload = {"file": f.name, "result": r, "verdict": report_ab_verdict(r, None)[0]}
                st.session_state["report-ab-upload"] = upload   # 다음 실행부터 store에도 저장
            except (ValueError, KeyError) as err:
                st.error(f"파일을 읽지 못했습니다: {err}")
        if upload:
            r = upload["result"]
            st.markdown(f"**{upload['file']}** · 클릭률 {r['ctr_a']}% → {r['ctr_b']}% (p={report_ab_p(r['p_ctr'])}) · "
                        f"구매 전환율 {r['cvr_a']}% → {r['cvr_b']}% ({r['cvr_basis']})  \n**결과** · {upload['verdict']}")


def report_show_review(ra):
    """리뷰 분석: 서리 리뷰 수·평점을 냉감패드 상품과 비교 (Keepa 마지막 조회값)."""
    with st.expander(":material/star: 리뷰 분석 (내부 요인 '리뷰' 근거)", expanded=False):
        if not ra:
            st.caption("Keepa 조회값이 없어 리뷰 분석을 할 수 없습니다.")
            return
        st.markdown("\n".join(f"- {f}" for f in ra["findings"]))
        st.dataframe([{"브랜드": x["brand"], "구분": x["kind"], "리뷰 수": x["reviews"],
                       "1년 증가": f"{x['reviews_1y']:+d}" if x.get("reviews_1y") is not None else "-", "평점": x["rating"],
                       "Amazon 판매 순위": f"{x['rank']:,}" if x["rank"] else "-"}
                      for x in sorted(ra["rows"], key=lambda x: x["rank"] or 10**9)],
                     hide_index=True, width="stretch", key="report-table-review")
        st.markdown(f'<div class="report-desc">지표: {ra["metric"]} · 목표: {ra["target"]}<br>규칙: {ra["rule"]}<br>한계: {ra["limits"]}</div>',
                    unsafe_allow_html=True)
        shop = report_shop_reviews()
        if shop:   # 자사몰 리뷰 (가정: SleepCOOL 공식몰) - Amazon 리뷰 수에는 더하지 않고 근거로만
            sh = shop["shop"]
            st.markdown(f"**자사몰 리뷰** (가정: {REPORT_SEORI_PROXY} 공식몰 · [Trusted Shops]({shop['url']}) · {shop['fetched_at']} 조회) · "
                        f"평점 {sh['rating']}/{sh['scale']} · {sh['reviews']:,}건 (별 5개 {sh['distribution_pct']['5']}%)")
            st.dataframe([{"주제": t["theme"], "건수": t["count"], "긍정·중립·부정": " · ".join(f"{k} {v}" for k, v in t["tones"].items()),
                           "예시": t["example"]} for t in shop["themes"]], hide_index=True, width="stretch", key="report-table-shop-themes")
            with st.expander("자사몰 리뷰 원문 (발췌)", expanded=False):
                st.dataframe([{"날짜": i["date"], "제품": i["product"], "분류": i["tone"], "원문": i["quote"], "한국어": i["ko"]}
                              for i in shop["items"]], hide_index=True, width="stretch", key="report-table-shop-items")
            st.markdown(f'<div class="report-desc">{shop["note"]}<br>한계: {shop["limits"]}</div>', unsafe_allow_html=True)


def report_factor_html(item, group=""):
    level = item["level"]
    tag = f'<span class="report-tag">{group}</span>' if group else ""
    return (
        f'<div class="report-factor">'
        f'<span class="report-level report-level-{REPORT_LEVEL_CLASS[level]}">{REPORT_LEVEL_DOTS[level]} {level}</span>'
        f'{tag}<b>{item["title"]}</b>'
        f'<div class="report-desc">{item["detail"]}</div>'
        f'</div>'
    )
