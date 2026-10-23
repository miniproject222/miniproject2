# Supabase 읽기 / 저장 (PM)
# 주소와 키는 .streamlit/secrets.toml의 [connections.supabase]에서 자동으로 읽습니다.
#
# 사용 예:
#   from common.common_db import db_read, db_insert, db_update
#   rows = db_read("report_sales", month="2026-10")           # 읽기 (10분 캐시)
#   db_insert("report_sales", {"month": "2026-10", "amount": 100})
#   db_update("report_sales", {"amount": 120}, id=3)          # id=3인 행 수정
import streamlit as st
from st_supabase_connection import SupabaseConnection, execute_query


def db_conn():
    """Supabase 연결 (st.connection이 한 번만 만들고 재사용합니다)."""
    return st.connection("supabase", type=SupabaseConnection)


def db_read(table, columns="*", ttl=600, **filters):
    """table에서 filters와 일치하는 행을 리스트로 돌려줍니다.

    ttl: 결과를 몇 초 동안 캐시할지 (0이면 매번 새로 읽기)
    """
    query = db_conn().table(table).select(columns)
    for col, val in filters.items():
        query = query.eq(col, val)
    return execute_query(query, ttl=ttl).data


def db_insert(table, rows):
    """행 추가. rows는 dict 하나 또는 dict 리스트."""
    result = db_conn().table(table).insert(rows).execute()
    st.cache_data.clear()   # 저장 후에는 캐시를 비워 새 값이 바로 보이게 합니다
    return result.data


def db_upsert(table, rows):
    """기본 키가 같은 행이 있으면 수정, 없으면 추가."""
    result = db_conn().table(table).upsert(rows).execute()
    st.cache_data.clear()
    return result.data


def db_update(table, values, **filters):
    """filters와 일치하는 행의 값을 values로 바꿉니다. 조건 없는 전체 수정은 막아 둡니다."""
    if not filters:
        raise ValueError("db_update에는 수정할 행 조건(예: id=3)이 꼭 필요합니다.")
    query = db_conn().table(table).update(values)
    for col, val in filters.items():
        query = query.eq(col, val)
    result = query.execute()
    st.cache_data.clear()
    return result.data


def db_delete(table, **filters):
    """filters와 일치하는 행 삭제. 조건 없는 전체 삭제는 막아 둡니다."""
    if not filters:
        raise ValueError("db_delete에는 삭제할 행 조건(예: id=3)이 꼭 필요합니다.")
    query = db_conn().table(table).delete()
    for col, val in filters.items():
        query = query.eq(col, val)
    result = query.execute()
    st.cache_data.clear()
    return result.data
