# 3. 매체 제작 + 솔루션 제안 (`media`)

- 매체 제작: 하위 탭 5단계 ① 가설 확인 → ② 가설에서 변수 도출 → ③ A/B 소재 준비 → ④ 결과·판정 → ⑤ 솔루션 제안 (각 단계 아래 이전/다음 버튼으로 이동)
- 솔루션 제안: 매체 외에 실행할 수 있는 솔루션 제안 (이전 `solution` 모듈을 이 모듈로 합쳤습니다)

| 파일 | 내용 |
|---|---|
| `media_page.py` | 화면 + 기능 (`media_render()` 함수 하나). `MEDIA_STEPS`로 하위 탭(`st.tabs(key="media-step", on_change="rerun")`)을 만들고 선택된 단계만 그림, 이전/다음 버튼은 `st.session_state["media-step"]`을 바꿔 단계 이동 |
| `media_solution.py` | 하위 탭 ⑤ 솔루션 제안 (`media_solution_section()`) |
| `media_variable.py` | 하위 탭 ① 가설 확인(`media_variable_hypothesis_step()`): ② 탭이 저장한 가설(`store_get("hypothesis")`)을 콜아웃에 If/Because/Then 배지로 표시 (없으면 기준 가설, 다르면 경고) · 하위 탭 ② 가설에서 변수 도출(`media_variable_derive_step()`): 후보 변수를 가설 연결·아마존 메인 이미지 규칙·테스트 도구 기준으로 걸러 독립 변수 1개(메인 이미지 촬영 구도)와 통제·종속 변수를 정함 |
| `media_ab.py` | 메인 이미지 A/B (루트 `문제 시나리오.md`): 하위 탭 ③ A/B 소재 준비(`media_ab_plan_step()`: `report["sqp"]`로 A(현재)/B(제안) 안, 메인 이미지 규칙, 촬영 브리프 다운로드, Manage Your Experiments 안내) · 하위 탭 ④ 결과·판정(`media_ab_result_step()`: CTR 승자 + CVR 안전장치, 적용 전후 CAC) |
| `data/media_ab_result_dummy_202610.json` | A/B 결과 더미 (가상, 실제 테스트 결과가 나오면 교체) |
| `media_style.css` | 디자인 (class는 `media-`로 시작). 3번 탭이 열린 동안만 페이지 위·양옆 여백 축소, 이 탭 버튼 글자색 |
| `images/` | media에서만 쓰는 이미지 |
| `data/` | media에서만 쓰는 데이터 |

- 위젯 `key`, `st.session_state` 키는 `media-`로 시작합니다. (예: `key="media-btn-search"`, 솔루션 영역은 `key="media-solution-..."`)
- 다른 탭과 데이터 주고받기: `store_set("media", ...)` / `store_get("다른모듈")`
  - 매체 결과와 솔루션은 `media` 키 하나에 같이 저장합니다. (예: `{"results": [...], "solutions": [...]}`)
- Supabase 표 이름은 `media_`로 시작합니다. (예: `media_result`, `media_solution`)
