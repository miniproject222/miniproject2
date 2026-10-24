# 1. 분석 리포트 - GA4 연결 (UTM 유입 채널 + 구매 퍼널)
# secrets.toml의 report 칸에 아래 두 값이 있으면 GA4 실제 데이터를 쓰고, 없으면 샘플 데이터를 씁니다.
#   REPORT_GA4_PROPERTY_ID = "123456789"
#   REPORT_GA4_CREDENTIALS = '''{ 서비스 계정 JSON }'''
# 필요한 라이브러리: google-analytics-data (requirements.txt)
import json
from urllib.parse import urlencode

import streamlit as st

# 서리 자사몰(랜딩 페이지) 주소. UTM 링크 만들기의 기본값입니다.
REPORT_SHOP_URL = "https://seori-site.vercel.app/"

# GA4 전자상거래 이벤트 → 화면 퍼널 단계 (방문은 세션 수)
REPORT_GA4_FUNNEL_EVENTS = [
    ("view_item", "상세 조회"),
    ("add_to_cart", "장바구니"),
    ("begin_checkout", "결제 시작"),
    ("purchase", "구매"),
]
# 이번 기간 / 비교 기간 (GA4 날짜 표현)
REPORT_GA4_RANGES = {"now": ("30daysAgo", "yesterday"), "prev": ("60daysAgo", "31daysAgo")}


def report_ga4_ready():
    """GA4 연결 정보가 secrets에 있는지 확인합니다."""
    try:
        return bool(st.secrets.get("REPORT_GA4_PROPERTY_ID")) and bool(st.secrets.get("REPORT_GA4_CREDENTIALS"))
    except Exception:   # secrets.toml이 없을 때
        return False


def report_utm_link(base_url, source, medium, campaign, content="", term=""):
    """광고 링크 끝에 UTM 값을 붙입니다. GA4가 이 값으로 유입 채널을 자동 분류합니다."""
    params = {"utm_source": source, "utm_medium": medium, "utm_campaign": campaign,
              "utm_content": content, "utm_term": term}
    query = urlencode({k: v.strip() for k, v in params.items() if v and v.strip()})
    if not base_url or not query:
        return ""
    return f"{base_url}{'&' if '?' in base_url else '?'}{query}"


@st.cache_data(ttl=3600, show_spinner="GA4 데이터를 불러오는 중...")
def report_ga4_fetch():
    """GA4에서 UTM 채널별 성과와 퍼널 단계 수를 가져옵니다. (1시간 캐시)"""
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Filter, FilterExpression, Metric, RunReportRequest,
    )
    from google.oauth2 import service_account

    creds = service_account.Credentials.from_service_account_info(json.loads(st.secrets["REPORT_GA4_CREDENTIALS"]))
    client = BetaAnalyticsDataClient(credentials=creds)
    prop = f"properties/{st.secrets['REPORT_GA4_PROPERTY_ID']}"

    def run(dimensions, metrics, period, dim_filter=None):
        start, end = REPORT_GA4_RANGES[period]
        resp = client.run_report(RunReportRequest(
            property=prop, date_ranges=[DateRange(start_date=start, end_date=end)],
            dimensions=[Dimension(name=d) for d in dimensions], metrics=[Metric(name=m) for m in metrics],
            dimension_filter=dim_filter,
        ))
        return [([v.value for v in r.dimension_values], [float(v.value) for v in r.metric_values]) for r in resp.rows]

    events = FilterExpression(filter=Filter(field_name="eventName", in_list_filter=Filter.InListFilter(
        values=[e for e, _ in REPORT_GA4_FUNNEL_EVENTS])))
    raw = {
        "utm": run(["sessionSource", "sessionMedium", "sessionCampaignName"],
                   ["sessions", "ecommercePurchases", "purchaseRevenue"], "now"),
        "sessions": {p: run([], ["sessions"], p) for p in REPORT_GA4_RANGES},
        "events": {p: run(["eventName"], ["eventCount"], p, events) for p in REPORT_GA4_RANGES},
    }
    return report_ga4_parse(raw)


def report_ga4_parse(raw):
    """GA4 응답 행을 화면 데이터 모양(utm, funnel)으로 바꿉니다."""
    utm = [{"source": d[0], "medium": d[1], "campaign": d[2],
            "sessions": int(m[0]), "orders": int(m[1]), "revenue": round(m[2])}
           for d, m in raw["utm"]]
    utm.sort(key=lambda r: r["sessions"], reverse=True)

    def count(period, event):
        return int(next((m[0] for d, m in raw["events"][period] if d[0] == event), 0))

    def sessions(period):
        rows = raw["sessions"][period]
        return int(rows[0][1][0]) if rows else 0

    funnel = [{"stage": "방문", "now": sessions("now"), "prev": sessions("prev")}]
    funnel += [{"stage": stage, "now": count("now", e), "prev": count("prev", e)} for e, stage in REPORT_GA4_FUNNEL_EVENTS]
    return {"utm": utm, "funnel": funnel}
