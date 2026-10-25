# 3. 매체 제작 > 2단계: 프롬프트 만들기 + AI 다듬기 (`media_stage2`)

- 담당 브랜치: `JY`
- 3번 탭(`media`)의 하위 탭 ③(지금 이름 '프롬프트 만들기', 아래 "하위 탭 이름" 참고)을 만듭니다.
- 1단계가 정한 단일 변수와 A/B 소재를 받아 **2-1 기본 프롬프트 쓰기 → 2-2 단일 변수 칸 비워 두기 → 2-3 빈칸 채워 A, B 만들기 → 2-4 리포트 값으로 AI 다듬기 + 확인**을 하고, 결과를 3단계(④ 사진·영상 초안, ⑤ 외주 정리)에 넘깁니다.
- 개발이 끝나면 1단계(`min` 브랜치) 기준으로 합칩니다.

## 할 일

| 순서 | 하는 일 | 예 |
|---|---|---|
| 2-1 | A와 B에 똑같이 들어갈 기본 프롬프트 1개 쓰기 | 흰 배경, 글자 없음, 냉감패드 90×200cm, 부드러운 조명 |
| 2-2 | 기본 프롬프트 안에 단일 변수 자리만 빈칸 `{slot}`으로 남기기 | "패드를 `{slot}` 상태로 찍은 사진" |
| 2-3 | 빈칸 채워 A, B 만들기 (두 프롬프트는 빈칸 단어만 다르고 나머지는 똑같음) | A "접힌", B "펼쳐서 모서리를 살짝 든" |
| 2-4 | 리포트 값(금지 표현, 광고 표현 규칙, 서리 강점)으로 **공통 부분만** AI로 다듬고, A·B를 나란히 비교해 빈칸 밖이 바뀌었으면 되돌리기 | 🚫 얼음 연출 빼기, ✅ 면 뒷면 보이게 |

## 작업 범위

- **이 폴더(`modules/media/media_stage2/`) 안에서만** 작업합니다.
- `modules/media/` 바로 아래 파일(`media_page.py`, `media_handoff.py`, `media_style.css`, 문서 등)과 `media_stage3/`은 고치지 않습니다.
  바꿔야 하면 1단계 담당자에게 무엇을 왜 바꿔야 하는지 알립니다.

| 파일 | 내용 |
|---|---|
| `media_stage2.py` | 화면 + 기능. 진입 함수 `media_stage2_render()` 하나를 1단계의 `media_page.py`가 하위 탭 안에서 부릅니다 (이 함수 이름은 바꾸지 않음) |
| `media_stage2_style.css` | 디자인 (class는 `media-s2-`로 시작). `media_page.py`가 3번 탭을 열 때 읽어 넣습니다 |
| `media_stage2_prompt.md` | 프롬프트 기록 |
| `media_stage2_judge.py` | (보관) 이전 A/B 결과·판정 코드, 지금 화면에는 연결하지 않음 |
| `data/media_ab_result_dummy_202610.json` | (보관) 판정 코드가 쓰는 A/B 결과 더미 |
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
  - `query` 검색어, `variable` 단일 변수, `a` A 소재, `b` B 소재, `kpi` KPI 이름 등
- 넘기는 값: 다 만들면 `media_handoff_set_prompt({...})`
  - 모양은 `MEDIA_HANDOFF_PROMPT_SAMPLE`과 같게: `variable` 단일 변수, `base` 기본 프롬프트(빈칸 `{slot}` 1개),
    `slot_a` A 빈칸, `slot_b` B 빈칸, `fixed` 고정 요소 목록(기본 프롬프트 안의 문구 그대로)
  - 완성된 A, B 두 줄이 아니라 **기본 프롬프트와 빈칸을 따로** 넘깁니다. 3단계가 "빈칸 밖이 바뀌었나"를 확인해야 하기 때문입니다.
  - 키를 더하거나 바꾸려면 3단계 담당자, 1단계 담당자와 먼저 정합니다.
- 2-4 AI 다듬기 결과도 같이 넘깁니다: `prompt_a`, `prompt_b`(다듬은 프롬프트), `changes`(바꾼 곳 / 뺌·더함 / 이유 / 근거 DB ID), `avoid`·`include`(찍지 말 것 / 넣을 것 → ⑤ 촬영 브리프로 감)
- 확인은 `media_handoff_check()`(빈칸만 다른가, 고정 요소가 남았나)로 하고, 통과했을 때만 넘깁니다.
- 2-4에서 쓰는 리포트 값: `store_get("report")`의 `ad_claims.forbidden`(금지 표현), `marketing_rules`(독일 광고 표현 규칙 8개), `seori_profile`, `competitor_profiles` (`media_s2_report_rules()`). ① 탭을 한 번 열어야 들어옵니다.
- 넘긴 값은 `data/media_stage2_prompt.json`에 저장됩니다. **이 파일을 커밋·푸시해야** 3단계 담당이 풀 받아 이어서 작업할 수 있습니다.

## 지금 상태

- `media_stage2.py`: 2-1~2-3은 예시 값(`media_s2_draft()`)으로 자리만 있음 (2단계 담당이 만들 곳), 2-4는 A·B 나란히 비교·되돌리기·확인·리포트 규칙 보기·3단계로 넘기기까지 있음. `AI로 다듬기` 버튼은 AI 키 연결 전이라 꺼져 있음
- `media_stage2_judge.py`: 이전에 만든 A/B 결과·판정 코드 보관 (흐름에서 빠져 화면에 연결하지 않음, 다시 필요하면 `media_s2_judge_render()`를 연결)
- `data/media_ab_result_dummy_202610.json`: 판정 코드가 쓰는 A/B 결과 더미 (보관)
