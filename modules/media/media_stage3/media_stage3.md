# 3. 매체 제작 > 3단계: 솔루션 제안 (`media_stage3`)

- 담당 브랜치: `DH`
- 3번 탭(`media`)의 3단계 하위 탭(지금 이름 '솔루션 제안', 아래 "하위 탭 이름" 참고)을 만듭니다.
- 2단계의 A/B 판정 결과를 받아 매체(광고 소재) 외에 실행할 수 있는 솔루션을 제안합니다.
- 개발이 끝나면 1단계(`min` 브랜치) 기준으로 합칩니다.

## 작업 범위

- **이 폴더(`modules/media/media_stage3/`) 안에서만** 작업합니다.
- `modules/media/` 바로 아래 파일(`media_page.py`, `media_handoff.py`, `media_style.css`, 문서 등)과 `media_stage2/`는 고치지 않습니다.
  바꿔야 하면 1단계 담당자에게 무엇을 왜 바꿔야 하는지 알립니다.

| 파일 | 내용 |
|---|---|
| `media_stage3.py` | 화면 + 기능. 진입 함수 `media_stage3_render()` 하나를 1단계의 `media_page.py`가 하위 탭 안에서 부릅니다 (이 함수 이름은 바꾸지 않음) |
| `media_stage3_style.css` | 디자인 (class는 `media-s3-`로 시작). `media_page.py`가 3번 탭을 열 때 읽어 넣습니다 |
| `media_stage3_prompt.md` | 프롬프트 기록 |
| `data/` | 3단계에서만 쓰는 데이터 |
| `images/` | 3단계에서만 쓰는 이미지 |

## 하위 탭 이름

- 탭 이름은 `media_stage3.py`의 `MEDIA_S3_TAB_LABEL`에서 정합니다. 바꾸면 하위 탭과 이전/다음 버튼 글자가 함께 바뀝니다.
- 폴더·파일·함수·key 이름은 탭 이름이 아니라 단계 번호(`media_stage3`, `media_s3_`, `media-s3-`)라서 탭 이름이 바뀌어도 그대로 둡니다.
- 화면 안에 탭 이름을 문자열로 다시 쓰지 않습니다. 필요하면 `MEDIA_S3_TAB_LABEL`을 씁니다.

## 이름 규칙 (같은 media 안에서 겹치지 않게)

- 함수: `media_s3_...` (진입 함수만 `media_stage3_render`)
- 위젯 `key`, `st.session_state` 키, CSS class: `media-s3-...` (예: `key="media-s3-btn-export"`)
- Supabase 표를 만들면 `media_` 로 시작 (예: `media_solution`)

## 받는 값 (`modules/media/media_handoff.py`)

- `media_handoff_result()` → 2단계 판정 결과
  - `source` 출처("가상"/"실제"), `winner` 승자, `b_wins` B 승리 여부, `kpi` 노출 대비 클릭률 [A, B],
    `cvr` CVR [A, B], `cvr_ok` 안전장치 통과, `p_ctr` 유의확률
  - 2단계가 아직 결과를 넣지 않았으면 예시 값이 오고 `sample`이 `True`입니다. 예시 값으로 먼저 개발할 수 있습니다.
- 필요하면 `media_handoff_plan()`(1단계 A/B 설계)도 읽을 수 있습니다.

## 지금 상태 (나눌 때 옮겨 온 것)

- 솔루션 우선순위 샘플 (`ui.progress_list`) 하나만 있음
