# 2. 가설 수립 (`hypothesis`)

문제 해결 가설 제안 (현지 특성 반영)

| 파일 | 내용 |
|---|---|
| `hypothesis_page.py` | 화면 + 기능 (`hypothesis_render()` 함수 하나) |
| `hypothesis_style.css` | 디자인 (class는 `hypothesis-`로 시작) |
| `hypothesis_test.py` | 자체 테스트 (200개). `python modules/hypothesis/hypothesis_test.py`로 실행 |
| `images/` | hypothesis에서만 쓰는 이미지 |
| `data/` | hypothesis에서만 쓰는 데이터 |

- 위젯 `key`, `st.session_state` 키는 `hypothesis-`로 시작합니다. (예: `key="hypothesis-btn-search"`)
- 다른 탭과 데이터 주고받기: `store_set("hypothesis", ...)` / `store_get("다른모듈")`
- Supabase 표 이름은 `hypothesis_`로 시작합니다. (예: `hypothesis_result`)

## 사용자가 직접 입력하지 않고, 1번 리포트 결과로 가설 1개를 자동 생성합니다

가설을 여러 개 만들지 않는 이유: 1번 분석 결과와 가설이 1:1로 연결돼야 다음 탭(매체 제작 등)까지 흐름이 어긋나지 않기 때문입니다.

### `report` → `hypothesis` 데이터 모양 (report 탭 담당자 확인 필요)

**기본 키(`title`/`type`/`detail`)는 `modules/home/home_data.py`의 `HOME_DEMO["report"]["problems"]`가 이미 쓰고 있는 모양과 똑같이 맞췄습니다.** 홈 탭과 가설 탭이 같은 `report` 값을 읽으니, report 탭은 이 모양 하나만 만들면 두 탭에서 다 씁니다. `target`/`metric`/`local_context`/`competitor_review`는 가설 탭이 쓰려고 추가로 받는 **선택 필드**라 없어도 홈 탭 동작에는 영향이 없습니다.

```python
store_set("report", {
    "summary": "경쟁사가 가격을 낮췄어요...",   # 선택, 리포트 요약 한 줄
    "problems": [                              # 리스트! (2번 탭은 맨 앞 problems[0]로 가설 1개를 만듭니다)
        {
            "title": "경쟁사 가격 인하",
            "type": "외부",                     # "내부" | "외부" (home과 같은 한글 키/값)
            "detail": "경쟁사 B가 냉감패드 가격을 €39 → €29로 내렸습니다 (3일 전).",   # home과 같은 키
            "target": "Amazon.de에서 가격을 비교하는 독일 20~30대 구매자",   # 선택
            "metric": "전환율",                 # 선택, 없으면 "매출"로 대체됨
            "local_context": "독일 소비자는 가격 비교 사이트와 리뷰를 꼼꼼히 확인하는 시장",   # 선택, 현지(독일) 특성
            "competitor_review": "독일에 진출한 경쟁 냉감패드 브랜드 리뷰에 '냉감이 금방 사라진다'는 부정 리뷰 다수",   # 선택
        },
        # ... 문제가 더 있으면 이어서 추가. 가장 중요한 문제를 맨 앞(0번)에 놔 주세요.
    ],
})
```

- 우리 제품은 **독일 시장의 냉감패드(MODO)**이므로, `target`은 독일 고객/도시/채널(Amazon.de 등) 기준으로, `competitor_review`는 **독일에 진출한 유사 제품(냉감패드) 경쟁사**의 부정 리뷰 기준으로 채워 주세요. "강남점", "국내 배달앱" 같은 한국 매장형 예시는 이 프로젝트와 안 맞습니다.
- `local_context`(현지 특성), `competitor_review`(경쟁사 부정 리뷰)는 **값이 있으면 가설 문장에 항상 반영됩니다** (기획서의 "현지 특성 반영", "경쟁사 부정 리뷰를 홍보 포인트로 활용" 요구사항). 값이 없으면 `detail`에 "리뷰" 같은 단어가 있을 때만 규칙 기반으로 추측하니, 되도록 두 값을 채워서 넘겨주세요.

이 모양이 아직 안 정해졌다면, 2번 탭의 "예시 데이터로 먼저 테스트하기" 버튼으로 먼저 동작을 확인할 수 있습니다 (`hypothesis_page.py`의 `SAMPLE_REPORT`, home_data.py의 실제 샘플 문제를 독일 시장 기준으로 보강한 내용입니다).

### 가설 자동 생성 방식

1. `report["problems"]`의 **맨 앞(0번) 문제**를 읽어 `hypothesis_build_sentence()`가 규칙 기반으로 가설 문장을 바로 만듭니다. (AI 사용 도구/키가 아직 정해지지 않아서, 지금은 AI 호출 없이도 항상 동작하도록 규칙 기반으로만 구현했습니다. AI가 정해지면 `hypothesis_build_sentence()` 위쪽의 TODO 주석 자리에 연결하면 됩니다.)
2. 생성된 문장은 화면에서 바로 수정할 수 있고, "가설 저장"을 누르면 `store_set("hypothesis", {...})`로 **가설 1개(dict)만** 저장되어 media, solution, home 탭이 읽을 수 있습니다. 저장되는 dict에는 `home_data.py`가 기대하는 `"hypothesis"` 키와, 더 구체적인 `"text"`/`"target"`/`"metric"`/`"type"`/`"local_context"`/`"competitor_review"` 키가 함께 들어갑니다.
3. 리포트의 맨 앞 문제(`report["problems"][0]`)가 바뀌면 자동으로 새 가설을 다시 만듭니다. 같은 문제가 유지되는 동안에는 이미 만든 가설(수정한 내용 포함)을 그대로 보여줍니다.
4. `problems`가 리스트가 아니거나, 원소가 dict가 아니거나, `title`이 없는 등 모양이 예상과 달라도 화면이 깨지지 않습니다 (`hypothesis_pick_problem()`이 안전하게 걸러냅니다).
5. `hypothesis_build_sentence()`는 **같은 문제면 항상 같은 문장**을 돌려줍니다 (무작위 요소 없음). "1번 분석 결과 → 최적 가설 1개"라는 전제상, 같은 문제에 여러 후보가 있는 게 아니라 정해진 답 1개가 있어야 하기 때문입니다. "↺ 자동 생성 문장으로 되돌리기" 버튼도 "다른 안을 보여주는" 게 아니라, textarea에서 손으로 고친 내용을 원래 자동 생성 문장으로 되돌리는 용도입니다.

### 코드 고칠 때마다 꼭 돌려볼 것

```
python modules/hypothesis/hypothesis_test.py
```
pytest 같은 추가 설치 없이 Streamlit 내장 테스트 도구만 씁니다. 핵심 흐름, 방어적 처리, home_data.py 호환, 문법/키워드 회귀, 결정성(같은 입력 → 같은 결과), MODO 독일 사업 실전 시나리오 20개까지 총 200개를 확인합니다. 전부 통과해야 안전합니다.
