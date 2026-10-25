# 3. 매체 제작 > 2단계: 프롬프트 만들기 (`media_stage2`) 프롬프트 기록

`modules/media/media_stage2/`를 AI로 만들면서 **잘 쓴 프롬프트**와 **AI 실수를 고친 과정**을 모아 둡니다.
쌓인 기록은 프롬프트 엔지니어링 기록(보고서)의 `media` 파트에 합칩니다. (1단계 기록: `modules/media/media_prompt.md`)

- 담당:
- 브랜치: `JY`
- 사용한 AI 도구:

---

## AI에게: 기록 규칙

이 파일을 읽은 AI는 `modules/media/media_stage2/` 작업이 끝날 때마다 아래 규칙대로 기록해 주세요.

**기록하는 것**
- 결과가 잘 나와서 담당자가 받아들인 프롬프트
- 처음엔 실패했지만 프롬프트를 고쳐서 해결한 경우 (실패한 프롬프트와 고친 프롬프트 모두)
- AI가 틀린 정보를 지어내거나(환각), 시키지 않은 파일을 고치는 등 실수를 막은 프롬프트
- 앱 안에서 쓰는 AI 프롬프트(시스템 프롬프트 등)를 새로 만들거나 고친 경우

**기록하지 않는 것**
- "안녕", "응", "맞아", "고마워", "ㅇㅋ", "다시 해 줘", "계속" 같은 짧은 말
- 오타 수정, 파일 위치 묻기처럼 결과가 남지 않는 단순 요청
- 이미 기록한 것과 거의 같은 프롬프트

**쓰는 방법**
- 프롬프트는 담당자가 쓴 **원문 그대로** 넣습니다. 다듬거나 요약하지 않습니다.
- API 키, 비밀번호, Supabase 주소, 개인정보는 `***`로 가립니다.
- 새 기록은 `## 기록` 맨 아래에 번호를 이어서(P-01, P-02 …) 추가합니다. 이전 기록은 고치거나 지우지 않습니다.
- 기록을 추가했다면 `## 요약`의 표도 한 줄 갱신합니다.
- 앱 안 AI 프롬프트를 고쳤다면 `## 앱 안 AI 프롬프트 버전`에도 한 줄 추가합니다.
- 기록했다면 작업 끝에 "프롬프트 기록에 P-00을 추가했습니다"라고 알려 줍니다.

**기록 형식** (이 형식만 사용)

````
### P-00 · YYYY-MM-DD · 작업 제목

- 분류: 기능 구현 / 버그 수정 / 디자인 / 데이터 / 앱 안 AI 프롬프트 / 기타 중 하나
- 문제 유형: 환각(없는 정보 지어냄) / 다른 파일 수정 / 기존 코드 삭제 / 형식 깨짐 / API 버전 오류 / 없음 등

**잘 쓴 프롬프트 (원문)**
```text
담당자가 쓴 프롬프트 그대로
```

**처음 시도와 문제** (처음부터 잘 됐으면 "없음")
- 처음 프롬프트: "..."
- AI가 한 실수: ...

**해결 전략**: 프롬프트에서 무엇을 바꿨더니 해결됐는지 한두 줄
**결과**: 무엇이 만들어졌는지, 바뀐 파일
**다음에 쓸 팁**: 다른 작업에도 쓸 수 있는 요령 한 줄
````

---

## 요약

보고서의 "전략 개요"와 "문제 해결 표"가 되는 부분입니다. 기록이 쌓일 때마다 갱신합니다.

**프롬프트 전략 개요**: (기록이 3개 이상 쌓이면 이 단계에서 어떤 방식으로 프롬프트를 썼는지 2~3문장으로 정리)

| 문제 유형 | AI가 한 실수 | 해결한 프롬프트 전략 | 기록 |
|---|---|---|---|
| 없음 | - | 확인할 것(브랜치·함수)부터 지정하고, AI 지시문과 코드 확인 규칙을 같은 목록으로 지정 | P-01 |

---

## 앱 안 AI 프롬프트 버전

화면에서 AI를 부르는 기능(요약, 추천, 문구 생성 등)의 프롬프트가 바뀔 때마다 기록합니다.

| 버전 | 날짜 | 프롬프트 전략 (무엇을 바꿨나) | 결과 | 기록 |
|---|---|---|---|---|
| v1 | 2026-10-25 | `MEDIA_S2_AI_SYSTEM`: 사진 프롬프트 편집자 역할, {slot}·고정 요소 유지, 근거 ID 필수, JSON만 답하기 / 리포트 금지 표현·LNG-002·004·006·아마존 규칙·사실 목록을 칸으로 나눠 전달 | 가짜 답 7종으로 확인 함수 시험 통과, 실제 AI 호출은 키가 없어 미검증 | P-01 |

---

## 기록

### P-01 · 2026-10-25 · 2-4 AI로 다듬기 연결 (리포트 규칙으로 기본 프롬프트 공통 부분만 다듬기)

- 분류: 앱 안 AI 프롬프트
- 문제 유형: 없음 (작업 전 dev 최신이 빠진 브랜치를 발견해 멈춤 → dev를 받은 뒤 진행)

**잘 쓴 프롬프트 (원문)**
```text
나는 miniproject2의 3번 탭(media, "광고 소재·솔루션")에서 하위 탭 ③ "프롬프트 만들기"의 AI 다듬기 기능을 맡았어.
폴더는 modules/media/media_stage2/ 하나만 고쳐. (원래 2단계 담당은 JY이고, PM이 이 기능을 나에게 맡겼어)

[먼저 확인할 것]
- git 상태를 읽기 전용으로 확인하고, dev 최신을 받은 상태인지 알려 줘. 아니면 멈추고 알려 줘.
- 아래 함수들이 실제로 있는지 확인해. 없거나 이름이 다르면 코드를 고치지 말고 먼저 알려 줘.
  - modules/media/media_stage2/media_stage2.py: media_s2_draft(), media_s2_report_rules(), media_s2_refine_section(), media_stage2_render()
  - modules/media/media_handoff.py: media_handoff_check(), media_handoff_fill(), media_handoff_set_prompt(), MEDIA_HANDOFF_SLOT
  - modules/media/media_ab.py: MEDIA_AB_RULES (아마존 메인 이미지 규칙)

[먼저 읽을 파일]
1. modules/media/media_stage2/CLAUDE.md, media_stage2.md, media_stage2_prompt.md
2. modules/media/media_stage2/media_stage2.py (지금 코드)
3. modules/media/media_handoff.py (읽기만)
4. modules/report/report_handoff.md (리포트가 ③ 탭에 넘기는 값 설명, 읽기만)
5. README.md, RULES.md

[만들 것]
③ 탭의 2-4 "AI로 다듬기"를 실제로 동작하게 만들어. 리포트 데이터를 AI에게 주고, 기본 프롬프트의 공통 부분만 다듬게 해.

1. 버튼 위치
   - 지금 꺼져 있는 "AI로 다듬기" 버튼(key="media-s2-btn-refine")을 프롬프트 A·B 칸 바로 위, 오른쪽 끝에 둬.
     ("2-4 AI로 다듬기 + 확인" 제목과 같은 줄 오른쪽)
   - 버튼 옆에 쓸 AI를 고르는 작은 선택(Gemini / OpenAI)을 둬. key는 media-s2-ai-pick.
   - 키가 하나도 없으면 버튼을 끄고, 마우스를 올리면 "secrets.toml에 GEMINI_API_KEY 또는 OPENAI_API_KEY를 넣어 주세요"가 보이게 해.

2. AI에게 보낼 재료 (전부 리포트에서, 새로 지어내지 않음)
   - 기본 프롬프트·빈칸·A/B 문구·고정 요소·단일 변수: media_s2_draft()
   - store_get("report")에서:
     · ad_claims.forbidden (금지 표현 목록)
     · marketing_rules 중 LNG-002, LNG-004, LNG-006 (사진에 해당하는 규칙. 나머지는 광고 문구용)
     · seori_profile.strength (서리 강점)
     · competitor_profiles[*].weakness (경쟁사 약점)
     · sqp.listing.main_image_issue (지금 메인 이미지 문제)
   - 아마존 메인 이미지 규칙: media_ab.py의 MEDIA_AB_RULES를 import해서 읽기만 해. ID는 AMZ-1, AMZ-2 … 순서대로 붙여.
   - 리포트 값이 없으면(① 탭을 안 열었으면) 아마존 규칙만으로 다듬고, 화면에 "리포트 규칙 없이 다듬었어요"를 보여 줘.
   - 재료를 모으는 함수는 media_s2_ai_material() 하나로 만들어 (다른 곳에서 읽지 않게).

3. AI에게 보내는 지시문 (그대로 상수로 넣어: MEDIA_S2_AI_SYSTEM)
   ---
   너는 amazon.de(독일)에서 파는 냉감패드의 "사진 프롬프트 편집자"야.
   아마존 메인 이미지 A/B 테스트용 레퍼런스 사진을 만들 기본 프롬프트 하나를 다듬어.
   이 사진은 촬영팀에게 주는 견본이고, 광고에 바로 쓰는 사진이 아니야.

   반드시 지킬 것
   1. 기본 프롬프트에는 {slot}이 딱 한 번 있어. {slot}은 글자 그대로, 한 번만 남겨. 빈칸 안에 들어갈 내용은 건드리지 마.
   2. 고정 요소는 글자 하나 바꾸지 말고 그대로 남겨.
   3. {slot} 밖의 공통 부분만 고쳐.
   4. 피할 것 규칙과 아마존 메인 이미지 규칙에 걸리는 표현은 빼.
   5. 넣을 것은 "사실" 목록에 있는 것만 넣어. 수치·인증·효과를 지어내지 마.
      더한 내용도 흰 배경, 글자 없음, 소품 없음 조건을 지켜야 해.
   6. 바꾼 곳마다 근거 ID를 붙여. 근거가 없으면 바꾸지 마.
   7. A 문구·B 문구가 규칙에 걸려도 고치지 말고 slot_warnings에 알려만 줘.
   8. 다듬은 프롬프트는 영어로, 이유는 한국어로 써.
   9. JSON만 답해. 형식:
      {"base": "...", "changes": [{"where": "...", "kind": "뺌 또는 더함", "reason": "...", "basis": "ID"}],
       "avoid": ["..."], "include": ["..."], "slot_warnings": ["..."]}
   ---
   보내는 내용은 [기본 프롬프트] [단일 변수] [A 문구] [B 문구] [고정 요소] [피할 것 - 리포트 금지 표현]
   [피할 것 - 독일 광고 규칙] [아마존 메인 이미지 규칙] [넣을 것 - 사실] 칸으로 나눠서 글로 만들어 (media_s2_ai_message()).

4. AI 호출
   - 함수 하나로 감싸: media_s2_ai_call(provider, system, message) → 답 문자열
   - 키는 st.secrets["GEMINI_API_KEY"] / st.secrets["OPENAI_API_KEY"]에서 함수 안에서 읽어. 코드에 키를 쓰지 마.
   - 모델 이름은 파일 맨 위 상수(MEDIA_S2_GEMINI_MODEL, MEDIA_S2_OPENAI_MODEL)로 두고, 공식 문서에서 지금 쓸 수 있는 이름인지 확인해.
   - 호출이 실패하면(키 오류, 사용량 초과, 시간 초과) 화면이 깨지지 않게 경고만 띄우고 원래 프롬프트를 그대로 둬.
   - 새 라이브러리가 필요하면 requirements.txt를 고치지 말고 추가할 한 줄을 나한테 알려 줘.

5. 받은 답 확인 (AI를 믿지 않고 코드로 다시 확인) → media_s2_ai_validate()
   - JSON이 깨졌으면 한 번만 다시 요청하고, 또 깨지면 취소
   - base에 {slot}이 정확히 1개인가, 고정 요소가 전부 그대로 있나 → 아니면 버리고 경고
   - A = base에 slot_a, B = base에 slot_b를 끼워서 만들고 media_handoff_check()로 확인
   - ad_claims.forbidden의 단어가 남아 있으면 경고 (괄호 안 한국어 설명은 빼고 단어 부분으로 검사)
   - changes의 basis가 보낸 ID 목록에 없으면 그 줄에 "근거 확인 필요" 표시

6. 화면
   - 통과하면 프롬프트 A·B 칸(media-s2-prompt-A/B)을 다듬은 문장으로 바꿔. (위젯이 그려지기 전에 바꿔야 하니 버튼 on_click 콜백에서 처리)
   - 아래에 "바꾼 곳" 표(바꾼 곳 / 뺌·더함 / 이유 / 근거), "찍지 말 것", "넣을 것", slot_warnings가 있으면 경고로 보여 줘.
   - 되돌리기 버튼은 지금처럼 원래 문장으로 돌아가게 둬.
   - 지금 있는 media_handoff_set_prompt() 호출에 changes, avoid, include를 AI 결과로 채워서 넘겨. (지금은 빈 목록)
     AI 결과는 st.session_state["media-s2-ai-result"]에 보관해서 다시 그려도 유지되게 해.

7. 키가 없을 때도 시연이 되게
   - 버튼은 꺼져 있어도, ad_claims.forbidden 단어 검사는 프롬프트 A·B에 항상 돌려서 경고를 보여 줘.

[지킬 것]
- modules/media/media_stage2/ 폴더 안만 수정해. media_handoff.py, media_page.py, media_ab.py, media_stage3/, report, common/, app.py는 고치지 마.
  바꿔야 하면 무엇을 왜 바꿔야 하는지 먼저 알려 줘.
- 함수는 media_s2_, 위젯 key·session_state 키·CSS class는 media-s2-로 시작해.
- 진입 함수 media_stage2_render() 이름과 MEDIA_S2_TAB_LABEL은 바꾸지 마.
- 넘기는 값의 키 이름(base, slot_a, slot_b, fixed, prompt_a, prompt_b, changes, avoid, include)은 바꾸지 마.
- git add/commit/push/merge는 하지 마. 커밋 메시지만 제안해 줘.
- 끝나면 media_stage2_prompt.md에 기록하고, media_stage2.md의 "지금 상태"를 고쳐 줘.

[검증]
- 키 없이: 앱이 오류 없이 뜨고, 버튼이 꺼져 있고, 금지 단어 검사가 돌아가는지
- 가짜 AI 답(정상 JSON, {slot} 없는 답, 고정 요소 빠진 답, 깨진 JSON)으로 media_s2_ai_validate()를 시험해서 각각 맞게 처리하는지
- 키가 있으면 실제로 한 번 눌러서 결과 표가 나오는지
- 실제로 한 검증과 못 한 검증을 나눠서 알려 줘.
```

**처음 시도와 문제**: 없음 (지시문의 "먼저 확인할 것"대로 git 상태를 보니 브랜치에 dev 최신 커밋 1개("커밋 오류 수정")가 빠져 있어 코드를 고치지 않고 멈췄고, dev를 받은 뒤 시작함)

**해결 전략**: 확인할 것(브랜치·함수 존재) → 읽을 파일 → 만들 것(함수 이름·재료·지시문 원문·답 확인 규칙) → 지킬 것 → 검증 순서로 한 번에 지정. AI 답을 믿지 않고 코드로 다시 확인하는 규칙({slot} 1개, 고정 요소, A/B 확인, 금지 단어, 근거 ID)을 미리 적어 둠.
**결과**: `media_stage2_ai.py`(새 파일: 재료·지시문·호출·답 확인·금지 단어 검사), `media_stage2.py`(제목 줄 AI 고르기·버튼, 결과 표·찍지 말 것·넣을 것, 넘기는 값에 changes·avoid·include), `media_stage2.md`
**다음에 쓸 팁**: 앱 안 AI 기능은 "AI가 지켜야 할 규칙"과 "코드가 다시 확인할 규칙"을 같은 목록으로 써 두면, AI가 어겨도 화면이 망가지지 않는다.
