# 2. 가설 수립 (`hypothesis`)

문제 해결 가설 제안 (현지 특성 반영)

| 파일 | 내용 |
|---|---|
| `hypothesis_page.py` | 화면 + 기능 (`hypothesis_render()` 함수 하나, 가설 후보 탭 1개당 `_hypothesis_render_candidate()`) |
| `hypothesis_scenario.py` | 검색어 클릭 문제(루트 `문제 시나리오.md` 2단계)의 "소재 개선"/"노출 확대" 가설 근거(타깃·액션·이유·KPI·테스트 방법 표)를 해당 가설 후보 탭 안에 펼치지 않아도 바로 보이는 형태로 넣는 함수들 (`hypothesis_scenario_evidence_section()`, `hypothesis_scenario_problem2_evidence_section()`). "KPI 표·판단 기준"만 보조 참고 자료라 `st.expander`로 접어 둠. 문장 자체는 `hypothesis_page.py`의 `hypothesis_resolve_sentence()`가 가져다 쓰고 화면에는 직접 노출하지 않음(저장용으로만 씀) |
| `hypothesis_style.css` | 디자인 (class는 `hypothesis-`로 시작) |
| `hypothesis_test.py` | 자체 테스트 (282개). `python modules/hypothesis/hypothesis_test.py`로 실행 |
| `images/` | hypothesis에서만 쓰는 이미지 |
| `data/` | hypothesis에서만 쓰는 데이터 |

- 위젯 `key`, `st.session_state` 키는 `hypothesis-`로 시작합니다. (예: `key="hypothesis-btn-search"`)
- 다른 탭과 데이터 주고받기: `store_set("hypothesis", ...)` / `store_get("다른모듈")`
- Supabase 표 이름은 `hypothesis_`로 시작합니다. (예: `hypothesis_result`)

## 1번 리포트의 상위 문제로 가설 후보를 자동 생성하고, 그중 1개를 사용자가 선택·저장합니다

화면 구성:
1. **맨 위 2단**: 왼쪽 "📋 분석 리포트 문제 요약" / 오른쪽 "✅ 지금 선택된 가설"(아직 없으면 안내 문구)이 나란히, 같은 강조 박스(`.hypothesis-callout-box`) 모양으로 보입니다.
2. **"🧪 가설 후보"**: `report["problems"]`의 상위 문제로 만든 가설 후보가 **"가설 1" / "가설 2" / "가설 3"** 하부 탭으로 뜹니다 (문제가 1~2개뿐이면 그만큼만 뜹니다). 탭마다 제목 → 📍 현지 특성 → 💬 경쟁사 부정 리뷰 → **📋 가설 근거 · 실행 방법**(타깃·액션·이유·KPI·테스트 방법 표, 펼치지 않아도 바로 보임) 순서로 쭉 읽어본 뒤, 맨 아래 **"이 가설 선택하기"** 버튼 1개만 누르면 됩니다. 가설 문장 자체는 화면에 따로 수정 가능한 칸으로 보여주지 않고(근거 표가 같은 내용을 구조화해서 보여주므로), 선택 시 저장할 값으로만 내부적으로 씁니다. sqp(검색어 클릭 분석)와 연결된 후보는 그 원본 수치로, 나머지는 가설 문장과 같은 조각(`hypothesis_build_components()`)으로 표를 채우므로 문장과 표 내용이 항상 서로 일치합니다.
3. "이 가설 선택하기"를 누르면 `store_set("hypothesis", {...})`로 **그 후보 1개만** 최종 저장됩니다(media, home 탭이 읽는 값). 다른 후보를 선택하면 이전 선택은 풀리고 새 후보로 바뀝니다 — **최종적으로 저장되는 가설은 항상 1개**입니다. (탭으로 여러 후보를 보여주는 건 "후보 중에 고르는" 단계일 뿐이고, 고르고 나면 다음 탭들이 읽는 값은 여전히 1개입니다.)

### `report` → `hypothesis` 데이터 모양 (report 탭 담당자 확인 필요)

**기본 키(`title`/`type`/`detail`)는 `modules/home/home_data.py`의 `HOME_DEMO["report"]["problems"]`가 이미 쓰고 있는 모양과 똑같이 맞췄습니다.** 홈 탭과 가설 탭이 같은 `report` 값을 읽으니, report 탭은 이 모양 하나만 만들면 두 탭에서 다 씁니다. `target`/`metric`/`local_context`/`competitor_review`는 가설 탭이 쓰려고 추가로 받는 **선택 필드**라 없어도 홈 탭 동작에는 영향이 없습니다.

```python
store_set("report", {
    "summary": "경쟁사가 가격을 낮췄어요...",   # 선택, 리포트 요약 한 줄
    "problems": [                              # 리스트! (2번 탭은 상위 최대 3개로 가설 후보를 만듭니다)
        {
            "title": "경쟁사 가격 인하",
            "type": "외부",                     # "내부" | "외부" (home과 같은 한글 키/값)
            "detail": "경쟁사 B가 냉감패드 가격을 €39 → €29로 내렸습니다 (3일 전).",   # home과 같은 키
            "target": "Amazon.de에서 가격을 비교하는 독일 20~30대 구매자",   # 선택
            "metric": "전환율",                 # 선택, 없으면 "매출"로 대체됨
            "local_context": "독일 소비자는 가격 비교 사이트와 리뷰를 꼼꼼히 확인하는 시장",   # 선택, 현지(독일) 특성
            "competitor_review": "독일에 진출한 경쟁 냉감패드 브랜드 리뷰에 '냉감이 금방 사라진다'는 부정 리뷰 다수",   # 선택
            "group": "경쟁사",                  # 선택, 문제 분류 (아래 "group과 competitor_review" 참고)
        },
        # ... 문제가 더 있으면 이어서 추가. 가장 중요한 문제를 맨 앞(0번)에 놔 주세요.
    ],
})
```

- 우리 제품은 **독일 시장의 냉감패드(MODO)**이므로, `target`은 독일 고객/도시/채널(Amazon.de 등) 기준으로, `competitor_review`는 **독일에 진출한 유사 제품(냉감패드) 경쟁사**의 부정 리뷰 기준으로 채워 주세요. "강남점", "국내 배달앱" 같은 한국 매장형 예시는 이 프로젝트와 안 맞습니다.
- `local_context`(현지 특성)는 **값이 있으면 가설 문장에 항상 반영됩니다** (기획서의 "현지 특성 반영" 요구사항).
- **`group`과 `competitor_review`**: 실제 report 데이터는 `competitor_review`를 **문제 12개 전부에 같은 값**으로 채워 보냅니다(경쟁사 DB 공통 요약이라 문제별로 다르지 않음). 그래서 가설 탭은 "`competitor_review` 값이 있으면 무조건 경쟁사 리뷰 대응 액션"으로 쓰지 않고, **`group`이 `"경쟁사"`일 때만** `competitor_review`를 액션에 반영합니다. `group`이 없으면(샘플 데이터 등) `type == "외부"`로 대신 판단합니다. `group`이 `"경쟁사"`가 아닌 문제(예: `"플랫폼"`, `"가격"`, `"채널"`)는 `competitor_review`가 채워져 있어도 무시하고, `title`/`detail` 키워드로 더 적합한 액션을 고릅니다.
- **`group: "검색 클릭"` (report_sqp.py가 만듦) · `sqp_type`/`query`**: report_sqp.py(검색어 클릭 분석)가 만든 문제는 `problems` 맨 앞에 추가되고 `group="검색 클릭"`, `sqp_type`("소재 개선"/"노출 확대"/"제외 검토")·`query`(검색어)를 같이 보냅니다. report가 `store_set("report", {..., "sqp": {...}})`로 원본 sqp 데이터도 같이 주면(`hypothesis_scenario.py`가 읽는 값과 동일), 그 문제의 `sqp_type`/`query`가 `sqp`(또는 `sqp["problem2"]`)와 일치할 때 **그 sqp로 만든 더 구체적인 문장(`hypothesis_scenario_sentence()`/`hypothesis_scenario_problem2_sentence()`)을 그대로 그 후보의 유일한 가설로 씁니다** — `title`/`detail` 키워드만 보고 또 만들면, 같은 문제에 서로 다른 문장 2개가 동시에 보이는("후보 1개당 가설 1개" 원칙 위반) 버그가 났었기 때문입니다 (아래 참고).
- `detail`에 **"가설 없이"**라는 문구가 있으면(예: 검색 의도가 전혀 다른 검색어), 그 문제는 1번 쪽이 이미 "가설 대상 아님"으로 판단한 것이므로 가설 후보 목록 자체에서 제외됩니다 (`hypothesis_pick_candidates()`).

이 모양이 아직 안 정해졌다면, 2번 탭의 "예시 데이터로 먼저 테스트하기" 버튼으로 먼저 동작을 확인할 수 있습니다 (`hypothesis_page.py`의 `SAMPLE_REPORT`, home_data.py의 실제 샘플 문제를 독일 시장 기준으로 보강한 내용입니다).

### 가설 자동 생성 방식

1. `hypothesis_pick_candidates(report)`가 `report["problems"]`의 **상위 최대 3개**(중복 제목·"가설 없이" 문제는 건너뜀)를 가설 후보로 고릅니다.
2. 후보마다 `hypothesis_resolve_sentence(problem, sqp)`가 문장을 만듭니다: `sqp`(검색어 클릭 분석 원본)와 `sqp_type`/`query`가 일치하면 그 구체적인 문장을 그대로 쓰고, 아니면 `hypothesis_build_sentence()`가 규칙 기반으로 만듭니다. (AI 사용 도구/키가 아직 정해지지 않아서, 지금은 AI 호출 없이도 항상 동작하도록 규칙 기반으로만 구현했습니다. AI가 정해지면 `hypothesis_build_sentence()` 위쪽의 TODO 주석 자리에 연결하면 됩니다.) 규칙 기반 액션은 `title`+`detail`을 합쳐 키워드로 고르며, 검색 클릭/경쟁사/배송·물류/품절·재고/비수기/날씨/신뢰·리뷰0/신규유입/재구매/품질/인증·규제/시험·검증/채널/결제/인지도/환율/고객센터/반품/가격 순으로 더 구체적인 카테고리를 먼저 확인합니다.
3. 각 후보의 문장은 화면에 직접 보이지 않고, "이 가설 선택하기"를 누르는 순간 계산돼 `store_set("hypothesis", {...})`로 **그 후보 1개(dict)만** 저장되어 media, solution, home 탭이 읽을 수 있습니다. 저장되는 dict에는 `home_data.py`가 기대하는 `"hypothesis"` 키와, 더 구체적인 `"text"`/`"target"`/`"metric"`/`"type"`/`"local_context"`/`"competitor_review"` 키가 함께 들어갑니다. 다른 후보를 선택하면 이전 선택은 자동으로 풀립니다.
4. `problems`가 리스트가 아니거나, 원소가 dict가 아니거나, `title`이 없는 등 모양이 예상과 달라도 화면이 깨지지 않습니다 (`hypothesis_pick_candidates()`가 안전하게 걸러냅니다).
5. `hypothesis_resolve_sentence()`는 **같은 문제면 항상 같은 문장**을 돌려줍니다 (무작위 요소 없음). 같은 후보에 여러 버전이 있는 게 아니라 정해진 답 1개가 있어야 하기 때문입니다. 사용자가 직접 문장을 수정하는 기능은 없습니다 — 근거 표를 보고 "이 가설 선택하기"만 누르는 구조라, 문장을 고치고 싶으면 report(1번) 쪽 데이터를 바꿔야 합니다.

### 코드 고칠 때마다 꼭 돌려볼 것

```
python modules/hypothesis/hypothesis_test.py
```
pytest 같은 추가 설치 없이 Streamlit 내장 테스트 도구만 씁니다. 핵심 흐름(가설 1/2/3 탭 생성·선택·재선택), 방어적 처리, home_data.py 호환, 문법/키워드 회귀, `group` 기준 competitor_review 게이팅 회귀, 결정성(같은 입력 → 같은 결과), 신규 카테고리(인증/시험/채널/신뢰/비수기/가격), 검색어 클릭 문제(소재 개선/노출 확대) 근거 통합 회귀, 모든 가설 후보에 근거 표가 펼치지 않아도 바로 뜨는지(제너릭/시나리오 둘 다) 회귀, MODO 독일 사업 실전 시나리오 20개까지 총 282개를 확인합니다. 전부 통과해야 안전합니다.
