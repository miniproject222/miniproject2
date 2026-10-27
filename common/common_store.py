# 탭끼리 데이터 주고받기 (PM)
# 내 모듈 이름의 키에만 저장하고, 다른 키는 읽기만 합니다.
#
# 사용 예:
#   from common.common_store import store_get, store_set
#   store_set("report", {"summary": "...", "problems": []})   # 리포트 탭이 저장
#   report = store_get("report")                               # 가설 탭이 읽기 (없으면 None)
#
# 값은 지금 접속(st.session_state)에 바로 반영되고, Supabase의 common_store 표에도 저장되어
# 새로고침하거나 다른 사람이 접속해도 같은 값을 볼 수 있습니다.
# 같은 접속 안에서는 처음 읽은 값을 다시 씁니다. 다른 사람이 방금 저장한 값이 필요하면 store_get(key, fresh=True).
# 값은 JSON으로 바꿀 수 있는 것(dict, list, 문자열, 숫자)만 넣습니다.
# DataFrame은 df.to_dict("records")로 바꿔서 넣습니다.
import streamlit as st

from common.common_db import db_read, db_upsert

STORE_TABLE = "common_store"
STORE_PREFIX = "store-"


def store_get(key, fresh=False):
    """fresh=True면 이번 접속에 기억해 둔 값 대신 Supabase에서 다시 읽습니다 (다른 사람이 방금 저장한 값 받기).
    Supabase에 연결할 수 없으면 이번 접속에 기억해 둔 값을 그대로 돌려줍니다."""
    ss_key = STORE_PREFIX + key
    if fresh or ss_key not in st.session_state:
        try:
            rows = db_read(STORE_TABLE, ttl=0, key=key)
            st.session_state[ss_key] = rows[0]["value"] if rows else None
        except Exception as err:   # Supabase 연결 전이어도 화면은 깨지지 않게
            print(f"[Store] '{key}' 불러오기 실패: {err}")
            st.session_state.setdefault(ss_key, None)
    return st.session_state[ss_key]


def store_set(key, value):
    st.session_state[STORE_PREFIX + key] = value
    try:
        db_upsert(STORE_TABLE, {"key": key, "value": value})
    except Exception as err:
        st.warning(f"'{key}' 데이터를 Supabase에 저장하지 못했습니다. 이번 접속 동안만 유지됩니다. ({err})")
