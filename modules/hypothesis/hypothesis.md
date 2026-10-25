# 2. 가설 수립 (`hypothesis`)

문제 해결 가설 제안 (현지 특성 반영)

| 파일 | 내용 |
|---|---|
| `hypothesis_page.py` | 화면 + 기능 (`hypothesis_render()` 함수 하나, 가설 후보 탭 1개당 `_hypothesis_render_candidate()`) |
| `hypothesis_scenario.py` | 검색어 클릭 문제(루트 `문제 시나리오.md` 2단계)의 "소재 개선"/"노출 확대" 가설을 If·Because·Then 3조각(dict)으로 만드는 `hypothesis_scenario_ibt()`/`hypothesis_scenario_problem2_ibt()`, 그 조각을 색 배지 카드로 그리는 `hypothesis_if_then_card()`, "실행 세부사항"/"KPI 표"만 보조 참고 자료로 `st.expander`에 넣는 `hypothesis_scenario_detail_section()`/`hypothesis_scenario_problem2_detail_section()`이 있습니다. |
| `hypothesis_style.css` | 디자인 (class는 `hypothesis-`로 시작) |
| `hypothesis_test.py` | 자체 테스트 (282개). `python modules/hypothesis/hypothesis_test.py`로 실행 |
| `images/` | hypothesis에서만 쓰는 이미지 |
| `data/` | hypothesis에서만 쓰는 데이터 |

- 위젯 `key`, `st.session_state` 키는 `hypothesis-`로 시작합니다. (예: `key="hypothesis-btn-search"`)
- 다른 탭과 데이터 주고받기: `store_set("hypothesis", ...)` / `store_get("다른모듈")`
- Supabase 표 이름은 `hypothesis_`로 시작합니다. (예: `hypothesis_result`)

## 1번 리포트의 상위 문제로 가설 후보를 자동 생성하고, 그중 1개를 사용자가 선택·저장합니다

화면 구성:
1. **맨 위**: "✅ 지금 선택된 가설" 박스 1개(전체 너비). 아직 선택 전엔 안내 문구, 선택하고 나면 **그 가설도 가설 후보 탭과 똑같은 If·Because·Then 색 배지 카드**로 보여줍니다 ("선택된 가설도 카드로 보고 싶다"는 요청 반영). "📋 분석 리포트 문제 요약" 칸은 뺐습니다 — 가설 후보 탭마다 그 문제의 내부/외부 요인을 이미 보여주고 있어서 중복이었습니다.
2. **"🧪 가설 후보"**: `report["problems"]`의 상위 문제 중 **A/B 테스트용 사진·영상 결과물로 바로 이어지는 문제를 우선** 고른 가설 후보가 **"가설 1" / "가설 2" / "가설 3"** 하부 탭으로 뜹니다 (문제가 1~2개뿐이면 그만큼만 뜹니다). 탭마다 **내부/외부 요인 배지+제목 줄(오른쪽 끝에 작은 "선택하기"/"✓ 선택됨" 버튼)** → **"🧪 실행 방법"**(타깃·목표 KPI·준비할 소재·고정 요소·테스트 방법을 표 하나로, **토글 없이 항상 보임** — 사용자가 이 표만 보고 가설 1/2/3을 비교·선택할 수 있도록, 세 유형 전부 같은 구성. sqp 소재 개선 가설은 CAC/CTR 판단법만 "📏 판단 기준 자세히 보기" 토글에 따로 둠) → "📚 근거 · 출처 보기" 토글(문제 설명·현지 특성·경쟁사 부정 리뷰 **원문을 출처까지 그대로** 모음) 순서입니다. **If · Because · Then 카드는 가설 후보 탭 안에서는 그리지 않습니다** — 선택하면 어차피 맨 위 "지금 선택된 가설" 칸에서 그 카드로 보이므로, 탭 안에서 또 보여주면 중복이라는 지적을 반영했습니다(`hypothesis_if_then_card()`는 이제 그 맨 위 칸에서만 쓰입니다). 가설 문장 자체도 화면에 따로 수정 가능한 칸으로 보여주지 않고, 선택 시 저장할 값으로만 내부적으로 계산합니다(`hypothesis_resolve_ibt()`). sqp(검색어 클릭 분석)와 연결된 후보는 그 원본 수치로, 나머지는 가설 문장과 같은 조각(`hypothesis_build_ibt()`/`hypothesis_build_components()`)으로 저장값을 채우므로 "실행 방법" 표의 내용과 선택 후 맨 위 칸의 카드 내용이 항상 서로 일치합니다.
3. 제목 줄 오른쪽의 **"선택하기"**를 누르면 `store_set("hypothesis", {...})`로 **그 후보 1개만** 최종 저장됩니다(media, home 탭이 읽는 값). 저장되는 dict에는 합쳐진 문장(`text`/`hypothesis`)뿐 아니라 `if_text`/`because_text`/`then_text`도 따로 들어가서, 맨 위 "선택된 가설" 칸이 같은 카드 모양으로 다시 그릴 수 있습니다. 다른 후보를 선택하면 이전 선택은 풀리고 새 후보로 바뀝니다 — **최종적으로 저장되는 가설은 항상 1개**입니다. (예전에는 맨 아래에 가로로 꽉 찬 버튼 + "선택됨" 안내 박스가 있었는데, "박스는 지우고 조그맣게 버튼만 제목 줄 오른쪽에 넣어 달라"는 요청으로 지금 모양이 됐습니다.)
4. **긴 텍스트를 줄여서 자르지 않습니다.** 예전에는 현지 특성/경쟁사 부정 리뷰/액션 인용을 글자 수로 잘라 "…"로 끝냈는데, 중간에 끊겨 어색해 보인다는 피드백을 받고 전부 원문 그대로 쓰도록 바꿨습니다. 대신 글자 크기를 조금 줄이고(`hypothesis_style.css`), 긴 글은 카드/표 안에서 자연스럽게 줄바꿈되게 했습니다.

### If·Because·Then은 항상 짧게, 데이터 원문·출처는 "📚 근거·출처 보기" 토글 하나로 모음

report(1번)가 주는 `local_context`/`competitor_review`/`detail`은 실제로는 "경쟁사 Novilla 310건, RIBECO Germany 173건 (Keepa 2026-10-24 19:41) · 온라인 쇼핑객 54%가 구매 전 리뷰 확인 (독일 DB SHP-006)"처럼, 괄호 출처가 문장 **중간에도 여러 번** 섞인 긴 통계 인용문일 때가 많습니다. 끝 괄호 하나만 떼어내는 정도로는 부족해서("Because에 여전히 Keepa 시각·건수 같은 통계가 보인다"는 재피드백), 이 필드들의 원문은 Because 절에 **아예 쓰지 않도록** 바꿨습니다.

- **If·Because·Then의 이유(Because)는 항상 `title`(문제 제목)만 바탕으로** 짧게 만듭니다 — `hypothesis_build_components()`가 `detail`/`local_context` 원문 대신 `title`(report가 항상 짧고 깔끔한 명사구로 줌, 예: "리뷰 0건 (신규 브랜드)")로 reason_fragment를 만듭니다. sqp 기반 가설(`hypothesis_scenario_ibt()`)의 Because도 경쟁사 근거를 가리키는 포인터 문구조차 넣지 않고, sqp 수치(장바구니 전환율·가격차)로만 이유를 설명합니다.
- **문제 설명(`detail`)·현지 특성(`local_context`)·경쟁사 부정 리뷰(`competitor_review`) 원문(출처 포함, 안 자름)은 전부 `hypothesis_evidence_section()`이 "🔧 실행 세부사항" 바로 아래 "📚 근거 · 출처 보기" 토글 하나에 모아서** 보여줍니다 — 세 가설 유형(소재 개선/노출 확대/규칙 기반) 전부 공통으로 이 함수를 씁니다. 📍/💬 캡션은 없앴습니다(원문이 토글 안에 전부 있으므로 중복).

### 가설 후보를 고르는 우선순위: A/B 테스트 결과물(사진·영상)이 나오는 문제부터

"A/B 테스트 결과물이 좋은 사진·영상으로 나와야 한다"는 요구에 맞춰, `hypothesis_pick_candidates()`가 후보를 고를 때 `hypothesis_is_visual_candidate()`로 각 문제를 분류합니다:
- **report_sqp.py의 "소재 개선"**(메인 이미지 각도 변경)은 사진 자체가 핵심이라 항상 `True`.
- **"노출 확대"**(입찰가 조정)는 소재 없이도 되는 운영성 액션이라 항상 `False`.
- 그 외 문제는 `hypothesis_pick_action()`이 고른 액션 기준으로 판단합니다 (메인 이미지 교체, 배너·인포그래픽, 체험 영상 콘텐츠 등은 `True` / 입찰가·결제수단·채널 확대·고객센터처럼 소재가 필요 없는 운영성 액션은 `False`).

유효한 문제들을 이 분류로 나눈 뒤 **사진·영상으로 이어지는 문제를 먼저**, 그다음 운영성 문제로 채워서 상위 `limit`(기본 3)개를 고릅니다 — 각 그룹 안에서는 report가 원래 매긴 중요도 순서를 그대로 유지합니다. 즉 운영성 문제라도 사진·영상 후보가 `limit`개보다 적으면 후보에 들어옵니다.

### 테스트 방법도 가설(카테고리)마다 다르게

예전에는 "테스트 방법" 줄이 sqp 근거가 없는 가설은 전부 `A/B 테스트로 적용 전/후 {kpi} 비교`라는 똑같은 문장이었습니다 (체험단 영상이든 배너 이미지든 쿠폰 발송이든 전부 동일). `hypothesis_pick_action()`이 액션(`action`)·변화량(`amount`)·사진·영상 여부(`is_visual`)와 함께 **그 액션에 맞는 `test_method`**(무엇과 무엇을 비교하는지 + 기간·표본 기준)도 카테고리마다 따로 골라 돌려주도록 확장했습니다 — 예: 체험단 콘텐츠는 "체험단 모집 2주 + 콘텐츠 게시 후 4주 관찰", 쿠폰 발송류는 "발송군 vs 미발송군 ○일 재구매율/반품률 비교", 배너·인포그래픽류는 "노출군 vs 비노출군 전환율 비교 (2주 또는 전환 N건)". sqp 기반 두 가설(소재 개선·노출 확대)의 테스트 방법도 각각 "Manage Your Experiments 50:50 분할"/"폭염 주 평소 입찰 대비 비교"처럼 그 가설 고유의 방식을 그대로 씁니다.

### "🧪 실행 방법" 표는 세 가설 유형 전부 토글 없이, 같은 구성으로

"가설 2,3도 가설 1(sqp 기반)처럼 자세하게 나오게 해달라"는 요구에 맞춰, 규칙 기반 가설(`hypothesis_generic_detail_section()`)도 sqp 가설과 같은 **타깃 · 목표 KPI · 준비할 소재 · 고정 요소 · 테스트 방법** 표를 씁니다. `hypothesis_build_components()`가 `prep_material`(준비할 소재)·`fixed_factor`(고정 요소)도 같이 돌려주는데, 사진·영상이 필요한 액션(`is_visual=True`)이면 `action` 자체가 곧 준비할 소재이고(예: "장바구니 단계에서 배송비를 미리 안내하는 배너 이미지 노출"), 소재가 필요 없는 운영성 액션(`is_visual=False`)이면 "별도 소재 불필요 (운영성 액션)"으로 고정 문구를 씁니다. **목표 KPI도 이 표 안에 같이** 넣었습니다(실행 방법과 목표를 같이 봐야 비교하기 편하다고 판단 — "실행 방법 표에 목표 KPI도 같이 들어 있으면 좋겠냐"는 질문에 그렇다고 답하고 반영). 이 표는 **토글 없이 바로 보여서** 가설 1/2/3을 실행 방법 기준으로 바로 비교할 수 있고, sqp 소재 개선 가설만 CAC/CTR 판단법 같은 더 깊은 설명을 "📏 판단 기준 자세히 보기" 토글에 남겨둡니다.

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

### 화면에 나오는 수치가 진짜 DB에서 온 건지 (2026-10-24 확인)

가설 탭에 보이는 수치는 전부 report가 넘겨준 값을 그대로 쓰므로, 진위는 report 쪽 데이터 소스에 달려 있습니다. 직접 소스 파일까지 추적해 확인한 결과:
- **독일 지식 DB 인용**(예: "온라인 쇼핑객의 54%가 구매 전 리뷰를 확인한다", SHP-006)과 **경쟁사 DB**(Novilla/RIBECO/Traumnacht Q-max 미공개 등)는 루트 `data/common_germany_knowledge_seori_202610.csv`, `data/common_competitor_seori_202610.csv`에 **그대로 들어 있는 실제 값**입니다.
- **경쟁 제품 가격·평점**은 `modules/report/data/report_keepa_snapshot.json`(실제 Keepa 스냅샷, "개발 테스트 조회" 기준)에서 옵니다.
- **검색어 클릭 분석(노출 점유율·클릭 점유율·놓친 클릭 등, "가상 SQP" 배지가 붙어 있는 값들)은 report_sqp.py가 스스로 "더미(가상)"라고 명시**합니다 — 실제 Amazon 검색어 성과 데이터가 아직 연결되지 않아서, `report_sqp_make.py`로 만든 더미 JSON(`report_sqp_weekly_dummy_202608.json`)을 씁니다. 기온(DWD)과 경쟁 제품 가격(Keepa)만 실제고, 우리 상품의 노출·클릭·장바구니·구매 수치는 가상입니다.
이 구분은 화면에도 "(가상 SQP)" 같은 배지/문구로 이미 표시돼 있습니다. 검색어 클릭 분석을 실제 데이터로 바꾸는 건 report(1번) 탭 담당자가 결정할 일이라 제가 임의로 바꾸지 않았습니다.

### 가설 자동 생성 방식

1. `hypothesis_pick_candidates(report)`가 `report["problems"]`의 **상위 최대 3개**(중복 제목·"가설 없이" 문제는 건너뜀, A/B 테스트 결과물 우선순위 적용)를 가설 후보로 고릅니다.
2. 후보마다 `hypothesis_resolve_ibt(problem, sqp)`가 If·Because·Then 3조각(dict)을 만듭니다: `sqp`(검색어 클릭 분석 원본)와 `sqp_type`/`query`가 일치하면 `hypothesis_scenario_ibt()`/`hypothesis_scenario_problem2_ibt()`의 구체적인 조각을 그대로 쓰고, 아니면 `hypothesis_build_ibt()`가 규칙 기반으로 만듭니다. `hypothesis_resolve_sentence()`(저장용 한 문장)는 이 조각 3개를 `"만약 {if}, {because} {then}."` 형태로 이어붙인 것뿐이라, 카드와 저장되는 문장이 항상 같습니다. (AI 사용 도구/키가 아직 정해지지 않아서, 지금은 AI 호출 없이도 항상 동작하도록 규칙 기반으로만 구현했습니다. AI가 정해지면 `hypothesis_build_ibt()` 자리에 연결하면 됩니다.) 규칙 기반 액션은 `title`+`detail`을 합쳐 키워드로 고르며, 검색 클릭/경쟁사/배송·물류/품절·재고/비수기/날씨/신뢰·리뷰0/신규유입/재구매/품질/인증·규제/시험·검증/채널/결제/인지도/환율/고객센터/반품/가격 순으로 더 구체적인 카테고리를 먼저 확인합니다.
3. 각 후보의 If·Because·Then은 가설 후보 탭 안에서 카드로 바로 보이고, "이 가설 선택하기"를 누르면 `store_set("hypothesis", {...})`로 **그 후보 1개(dict)만** 저장되어 media, solution, home 탭이 읽을 수 있습니다. 저장되는 dict에는 `home_data.py`가 기대하는 `"hypothesis"` 키, 합쳐진 `"text"`, 카드 재구성용 `"if_text"`/`"because_text"`/`"then_text"`, 그리고 `"target"`/`"metric"`/`"type"`/`"local_context"`/`"competitor_review"` 키가 함께 들어갑니다. 다른 후보를 선택하면 이전 선택은 자동으로 풀립니다.
4. `problems`가 리스트가 아니거나, 원소가 dict가 아니거나, `title`이 없는 등 모양이 예상과 달라도 화면이 깨지지 않습니다 (`hypothesis_pick_candidates()`가 안전하게 걸러냅니다).
5. `hypothesis_resolve_ibt()`/`hypothesis_resolve_sentence()`는 **같은 문제면 항상 같은 내용**을 돌려줍니다 (무작위 요소 없음). 같은 후보에 여러 버전이 있는 게 아니라 정해진 답 1개가 있어야 하기 때문입니다. 사용자가 직접 문장을 수정하는 기능은 없습니다 — 근거 카드를 보고 "이 가설 선택하기"만 누르는 구조라, 문장을 고치고 싶으면 report(1번) 쪽 데이터를 바꿔야 합니다.

### 코드 고칠 때마다 꼭 돌려볼 것

```
python modules/hypothesis/hypothesis_test.py
```
pytest 같은 추가 설치 없이 Streamlit 내장 테스트 도구만 씁니다. 핵심 흐름(가설 1/2/3 탭 생성·선택·재선택), 방어적 처리, home_data.py 호환, 문법/키워드 회귀, `group` 기준 competitor_review 게이팅 회귀, 결정성(같은 입력 → 같은 결과), 신규 카테고리(인증/시험/채널/신뢰/비수기/가격), 검색어 클릭 문제(소재 개선/노출 확대) 근거 통합 회귀, 모든 가설 후보에 근거 표가 펼치지 않아도 바로 뜨는지(제너릭/시나리오 둘 다) 회귀, MODO 독일 사업 실전 시나리오 20개까지 총 282개를 확인합니다. 전부 통과해야 안전합니다.
