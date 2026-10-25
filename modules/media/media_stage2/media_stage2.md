# 3. 매체 제작 > 2단계: 프롬프트 만들기 + AI 다듬기 (`media_stage2`)

- 담당 브랜치: `JY`
- 3번 탭(`media`)의 **하위 탭 ② 'A/B 소재 준비'** 전체를 만듭니다 (2026-10-25 PM 결정: 옛 1단계 `media_ab.py`와 '프롬프트 만들기' 탭을 이 폴더로 합침, 담당 PM·`JH` 브랜치). 탭 이름은 `MEDIA_S2_TAB_LABEL` = "A/B 소재 준비", 진입 함수는 `media_stage2_render()`.
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
| `media_stage2_ai.py` | 2-4 AI 다듬기: 재료 모으기, 지시문, AI 호출, 받은 답 확인, 금지 단어 검사 (화면 코드 없음) |
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
- **'④로 넘기기' 버튼을 눌렀을 때만** Supabase(`store("media")`의 `handoff.prompt`)에 저장되고, 3단계는 다른 컴퓨터에서도 바로 받습니다. 탭을 열기만 해서는 저장되지 않습니다. 넘긴 뒤 프롬프트를 고치면 '다시 넘기기 필요'가 보입니다.

## 지금 상태

- **A·B 프롬프트 만들기 (2026-10-25 밤, PM)**: ①에서 확정한 A/B(`media_variable_confirmed_plan()`)로 OpenAI가 **수업 형식 6줄**(Subject·Composition·Lighting·Background·Style·Negative, `MEDIA_S2_FIELDS`)의 A 프롬프트를 먼저 만들고, **독립 변수가 들어간 줄 하나만 바꿔 B**를 만듦 (`media_s2_generate()`, 지시문 `MEDIA_S2_GEN_SYSTEM`). 그 줄 = `{slot}`이라 3단계 약속(`base`·`slot_a`·`slot_b`·`fixed`) 그대로 넘어감
  - A를 '지금 메인 이미지 그대로'(keep) 쓸지 '새로 설계'(new)할지는 자동 판단 (`media_s2_mode()`: 확정한 A = 리포트의 지금 메인 이미지면 keep). 실제 A 사진은 쓰지 않음 (PM 결정)
  - 처음 열 때 한 번 만들고 session_state(`media-s2-gen`)에 보관 → 3단계로 갔다 와도 그대로. ①에서 다시 확정하면 새로 만듦, 'A·B 다시 만들기' 버튼으로 다시 만들 수 있음. 키가 없거나 실패하면 예시 프롬프트 + 경고
  - 한 칸을 고치면 다른 칸의 같은 부분도 같이 바뀜 (`_media_s2_sync`), 독립 변수 부분을 고치면 맞추지 않고 경고. '되돌리기'는 두 칸을 처음 만든 프롬프트로 함께 되돌림
  - AI로 다듬기: 6줄 형식 유지 규칙 추가, 독일 디자인 DB(`data/` CSV의 DSN-103·104·109·110, REG-105)를 재료·근거로 씀
  - '다음: 사진·영상 초안 제작 →': AI로 다듬기를 한 번도 안 했으면 이동하지 않고 가운데 경고창('AI 다듬기가 필요해요'), 했으면 넘기고 이동 (`media_s2_handoff_now()`가 False를 돌려주면 `media_page.py`가 이동을 멈춤)

- **화면 정리 2 (2026-10-25 밤)**: A·B 카드는 HTML 격자(`.media-s2-ab-grid`, 두 칸 같은 높이·작은 글씨), 독립 변수는 카드 아래·구분선 위 강조 줄(`.media-s2-ab-var`). '① 으로 가서 확정하기'·'AI로 다듬기'는 글 바로 옆 작은 버튼. 프롬프트 A·B 칸 제목은 '프롬프트 A · 대조군 / B · 실험군' 한 줄(빈칸 문구는 칸 안 문장에 있음). 확인 통과 문구·금지 단어 통과 문구는 뺌(문제 있을 때만 경고). 리포트 규칙은 버튼 → 큰 팝업(`st.dialog`, 금지 표현 | 광고 표현 규칙 두 칸, ✕로 닫기). **'프롬프트 넘기기' 버튼 줄은 없애고, 맨 아래 '다음: 사진·영상 초안 제작 →'을 누르면 `media_s2_handoff_now()`가 확인을 통과한 A·B를 넘김** (`media_page.py`의 `MEDIA_STEP_ON_NEXT`). 위쪽 탭 이름을 직접 눌러 옮기면 넘기지 않음

- **화면 정리 (2026-10-25 저녁)**: A·B 카드는 한 줄에 같은 높이·작은 글씨(`media-s2-ab-cards`, CSS로 높이 맞춤). 아래쪽 제목은 "📝 A안·B안 프롬프트 만들기" + 옆 설명("정확한 성과 측정을 위해 AI가 선정한 핵심 변수(변수명) 외 세부 요소는 고정됩니다…")이고, 같은 줄 오른쪽 끝에 'AI로 다듬기' 버튼. '2-1 ~ 2-3 기본 프롬프트와 빈칸' 상자와 'AI로 다듬기 + 확인' 제목은 화면에서 뺌 (기본 프롬프트·빈칸은 `media_s2_draft()`로 A·B 칸을 채우는 데만 씀)

- **화면 (2026-10-25)**: `media_stage2_render()` = 위쪽 `media_s2_ab_section()`(①에서 확정한 A·B 카드, 1단계 함수 `media_variable_confirmed_plan()`·`media_variable_go_step()` 사용. 확정 전이면 점선 빈 카드 `media-s2-ab-empty`와 '① 으로 가서 확정하기'만 보이고 아래는 그리지 않음, ①에서 새로 고르고 확정 안 했으면 주황 '확정 안 됨') → 구분선 → 아래쪽 `media_s2_prompt_section()`(제목 "📝 프롬프트 만들기"). 넘기기 버튼은 '프롬프트 넘기기'(넘긴 뒤 바뀌면 '다시 넘기기'). 아마존 메인 이미지 규칙은 `media_stage2_ai.py`의 `MEDIA_S2_AMAZON_RULES`로 옮김 (옛 `MEDIA_AB_RULES`)

- `media_stage2.py`: 2-1~2-3은 예시 값(`media_s2_draft()`)으로 자리만 있음 (2단계 담당이 만들 곳). 단 **빈칸 B는 1단계에서 확정한 B안의 영어 문장(`plan["b_ref"]`)에서 기본 프롬프트 앞뒤를 잘라 씀** (`media_s2_slot_from_ref()`, 앞뒤가 다르거나 없으면 예시 빈칸). 1단계에서 다른 B를 확정하면 프롬프트 칸도 새 문장으로 바뀜, 2-4는 A·B 나란히 비교·되돌리기·확인·리포트 규칙 보기·3단계로 넘기기까지 있음.
- **AI로 다듬기 동작함** (화면 제목 "AI로 다듬기 + 확인", 번호 2-4는 화면에서 뺌) (`media_stage2_ai.py` + 화면은 `media_stage2.py`)
  - 제목 줄 오른쪽 끝에 `AI로 다듬기` 버튼(`media-s2-btn-refine`). **AI는 OpenAI만 씀** (Gemini 선택 삭제, PM 결정 2026-10-25). `OPENAI_API_KEY`가 없으면 버튼이 꺼지고 "secrets.toml에 OPENAI_API_KEY를 넣어 주세요"가 보임
  - 재료(`media_s2_ai_material()`, 여기서만 리포트를 읽음): `media_s2_draft()` 값 + 리포트 `ad_claims.forbidden`(BAN-n), `marketing_rules`의 LNG-002·004·006, `seori_profile.strength`(SEORI-1), `competitor_profiles[*].weakness`(RIVAL-n), `sqp.listing.main_image_issue`(LISTING-1) + 1단계 `MEDIA_AB_RULES`(AMZ-n). 리포트가 없으면 아마존 규칙만 쓰고 "리포트 규칙 없이 다듬었어요"를 보여 줌
  - 지시문 `MEDIA_S2_AI_SYSTEM`, 보내는 글 `media_s2_ai_message()`, 호출 `media_s2_ai_call()` (requests로 직접 호출, 새 라이브러리 없음, 모델은 `MEDIA_S2_OPENAI_MODEL`, 키 이름은 `MEDIA_S2_AI_KEY`)
  - 받은 답 확인 `media_s2_ai_validate()`: JSON이 깨지면 한 번만 다시 요청, `{slot}` 정확히 1개·고정 요소·`media_handoff_check()`를 통과해야 칸을 바꿈, 금지 단어가 남으면 경고, 근거 ID가 보낸 목록에 없으면 "근거 확인 필요"
  - 통과하면 프롬프트 A·B 칸을 다듬은 문장으로 바꾸고 "바꾼 곳" 표·찍지 말 것·넣을 것을 보여 줌. 결과는 `st.session_state["media-s2-ai-result"]`에 보관하고, 칸이 그 결과 그대로일 때만 `changes`·`avoid`·`include`를 3단계로 넘김 (되돌리거나 직접 고치면 빈 목록)
  - 키가 없어도 리포트 금지 표현 검사는 프롬프트 A·B에 항상 돌아감 (괄호 안 한국어 설명과 한국어 설명 문장은 검사 단어에서 뺌)
  - 호출 실패(키 오류, 사용량 초과, 시간 초과)는 경고만 띄우고 프롬프트는 그대로 둠
  - 2026-10-25 실제 OpenAI(`gpt-6.1-sol`) 호출 확인: 리포트 규칙을 써서 약 25초에 답, 바꾼 곳 4개 모두 근거 ID 확인 통과
- `media_stage2_judge.py`: 이전에 만든 A/B 결과·판정 코드 보관 (흐름에서 빠져 화면에 연결하지 않음, 다시 필요하면 `media_s2_judge_render()`를 연결)
- `data/media_ab_result_dummy_202610.json`: 판정 코드가 쓰는 A/B 결과 더미 (보관)
