# 3. 매체 제작 + 솔루션 제안 (`media`)

- 매체 제작: 가설 2개 → 프롬프트 2개 → 결과물 2개 (프롬프트 다듬기)
- 솔루션 제안: 매체 외에 실행할 수 있는 솔루션 제안 (이전 `solution` 모듈을 이 모듈로 합쳤습니다)

| 파일 | 내용 |
|---|---|
| `media_page.py` | 화면 + 기능 (`media_render()` 함수 하나) |
| `media_solution.py` | 솔루션 제안 영역 (`media_solution_section()`, `media_render()` 안에서 부름) |
| `media_ab.py` | 메인 이미지 A/B (루트 `문제 시나리오.md`): `report["sqp"]`·저장된 가설로 A(현재)/B(제안) 안, 메인 이미지 규칙, 촬영 브리프 다운로드, Manage Your Experiments 안내, 판정(CTR 승자 + CVR 안전장치), 적용 전후 CAC (`media_ab_section()`, `media_render()` 안에서 부름) |
| `data/media_ab_result_dummy_202610.json` | A/B 결과 더미 (가상, 실제 테스트 결과가 나오면 교체) |
| `media_style.css` | 디자인 (class는 `media-`로 시작) |
| `images/` | media에서만 쓰는 이미지 |
| `data/` | media에서만 쓰는 데이터 |

- 위젯 `key`, `st.session_state` 키는 `media-`로 시작합니다. (예: `key="media-btn-search"`, 솔루션 영역은 `key="media-solution-..."`)
- 다른 탭과 데이터 주고받기: `store_set("media", ...)` / `store_get("다른모듈")`
  - 매체 결과와 솔루션은 `media` 키 하나에 같이 저장합니다. (예: `{"results": [...], "solutions": [...]}`)
- Supabase 표 이름은 `media_`로 시작합니다. (예: `media_result`, `media_solution`)
