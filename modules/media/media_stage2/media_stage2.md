# 3. 매체 제작 > 2단계: 결과·판정 (`media_stage2`)

- 담당 브랜치: `JY`
- 3번 탭(`media`)의 2단계 하위 탭(지금 이름 '결과·판정', 아래 "하위 탭 이름" 참고)을 만듭니다.
- 1단계가 정한 A/B 테스트 설계를 받아 A/B 결과로 승자를 판정하고, 판정 결과를 3단계(솔루션 제안)에 넘깁니다.
- 개발이 끝나면 1단계(`min` 브랜치) 기준으로 합칩니다.

## 작업 범위

- **이 폴더(`modules/media/media_stage2/`) 안에서만** 작업합니다.
- `modules/media/` 바로 아래 파일(`media_page.py`, `media_handoff.py`, `media_style.css`, 문서 등)과 `media_stage3/`은 고치지 않습니다.
  바꿔야 하면 1단계 담당자에게 무엇을 왜 바꿔야 하는지 알립니다.

| 파일 | 내용 |
|---|---|
| `media_stage2.py` | 화면 + 기능. 진입 함수 `media_stage2_render()` 하나를 1단계의 `media_page.py`가 하위 탭 안에서 부릅니다 (이 함수 이름은 바꾸지 않음) |
| `media_stage2_style.css` | 디자인 (class는 `media-s2-`로 시작). `media_page.py`가 3번 탭을 열 때 읽어 넣습니다 |
| `media_stage2_prompt.md` | 프롬프트 기록 |
| `data/media_ab_result_dummy_202610.json` | A/B 결과 더미 (가상, 실제 테스트 결과가 나오면 교체) |
| `images/` | 2단계에서만 쓰는 이미지 |

## 하위 탭 이름

- 탭 이름은 `media_stage2.py`의 `MEDIA_S2_TAB_LABEL`에서 정합니다. 바꾸면 하위 탭과 이전/다음 버튼 글자가 함께 바뀝니다.
- 폴더·파일·함수·key 이름은 탭 이름이 아니라 단계 번호(`media_stage2`, `media_s2_`, `media-s2-`)라서 탭 이름이 바뀌어도 그대로 둡니다.
- 화면 안에 탭 이름을 문자열로 다시 쓰지 않습니다. 필요하면 `MEDIA_S2_TAB_LABEL`을 씁니다.

## 이름 규칙 (같은 media 안에서 겹치지 않게)

- 함수: `media_s2_...` (진입 함수만 `media_stage2_render`)
- 위젯 `key`, `st.session_state` 키, CSS class: `media-s2-...` (예: `key="media-s2-btn-judge"`)

## 받는 값 / 넘기는 값 (`modules/media/media_handoff.py`)

- 받는 값: `media_handoff_plan()` → 1단계 A/B 설계
  - `query` 검색어, `variable` 독립 변수, `a` 대조군, `b` 실험군, `kpi` KPI 이름(노출 대비 클릭률),
    `kpi_now` 지금 값(0.63배), `kpi_goal` 목표(0.8배), `cvr_tolerance` 안전장치(0.5%p)
- 넘기는 값: 판정이 끝나면 `media_handoff_set_result({...})`
  - 모양은 `MEDIA_HANDOFF_RESULT_SAMPLE`과 같게: `source`, `winner`, `b_wins`, `kpi` [A, B], `cvr` [A, B], `cvr_ok`, `p_ctr`
  - 키를 더하거나 바꾸려면 3단계 담당자, 1단계 담당자와 먼저 정합니다.

## 지금 상태 (나눌 때 1단계에서 옮겨 온 것)

- 가상 결과로 CTR 승자 판정(두 비율 z-검정, p < 0.05) + CVR 안전장치 + 적용 전후 CAC·ACoS 표시
- 판정 결과를 `media_handoff_set_result()`로 3단계에 넘김
