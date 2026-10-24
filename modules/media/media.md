# 3. 매체 제작 (`media`)

- 매체 제작: 하위 탭 4개 가설에서 변수 도출 → A/B 소재 준비 → 프롬프트 만들기 → 매체 제작·외주 준비 (둥근 알약형 탭) (각 단계 아래 이전/다음 버튼으로 이동)
- 끝은 외주업체에 넘길 레퍼런스 파일(프롬프트, 사진·영상 초안, 고정 요소) 준비까지입니다. A/B 결과 판정, UTM, 매체 외 솔루션 제안은 지금 흐름에서 빠졌습니다 (판정 코드는 `media_stage2/media_stage2_judge.py`에 보관)

## 3단계 나눠 개발 (동시 개발 후 1단계 기준으로 합침)

| 단계 | 하위 탭 | 브랜치 | 담당 폴더·파일 | 이름 접두어 |
|---|---|---|---|---|
| 1단계 | 단일 변수 추출 ~ A/B 소재 선정 (가설에서 변수 도출, A/B 소재 준비) | `min` | `modules/media/` 바로 아래 파일 전부 (공용 파일 포함) | `media_` / `media-` |
| 2단계 | 프롬프트 만들기: 기본 프롬프트 → 빈칸 → A, B 채우기 | `JY` | `media_stage2/`만 | `media_s2_` / `media-s2-` |
| 3단계 | 매체 제작·외주 준비: AI 다듬기·확인 → 사진·영상 초안 → 외주 레퍼런스 파일 | `DH` | `media_stage3/`만 | `media_s3_` / `media-s3-` |

- 공용 파일(`media_page.py`, `media_handoff.py`, `media_style.css`, `media.md`, `media_prompt.md`, `CLAUDE.md`)은 1단계 담당자만 고칩니다.
- 연결 지점: `media_page.py`가 하위 탭에서 `media_stage2_render()`, `media_stage3_render()`만 부릅니다.
- 2·3단계 하위 탭 이름은 각 단계 파일의 `MEDIA_S2_TAB_LABEL`, `MEDIA_S3_TAB_LABEL`에서 정하고 `media_page.py`가 가져다 씁니다. 단계 담당자가 직접 바꿉니다.
- 단계 사이 데이터: `media_handoff.py` (1→2 `media_handoff_set_plan()` / `media_handoff_plan()`, 2→3 `media_handoff_set_prompt()` / `media_handoff_prompt()`).
  - 값은 각 단계 폴더의 JSON 파일로 저장됩니다. **그 파일을 커밋·푸시하면, 다른 컴퓨터에서 풀 받은 사람에게 자동으로 이어집니다.**
    - 1단계: `modules/media/data/media_handoff_plan.json` (min이 올림)
    - 2단계: `modules/media/media_stage2/data/media_stage2_prompt.json` (JY가 올림)
  - 단계마다 자기 폴더의 파일만 쓰므로 합칠 때 충돌이 나지 않습니다. 읽을 때마다 파일을 새로 읽어서, 풀 받은 뒤 새로고침하면 바로 반영됩니다. 앞 단계 값이 없으면 예시 값이 와서 각자 먼저 개발할 수 있습니다.
  - 2→3 모양(`MEDIA_HANDOFF_PROMPT_SAMPLE`): `variable` 단일 변수, `base` 기본 프롬프트(빈칸 `{slot}`), `slot_a`, `slot_b` 빈칸 문구, `fixed` 고정 요소 목록
- 단계 폴더의 CSS(`media_stage2_style.css`, `media_stage3_style.css`)는 공통 로더가 읽지 않아 `media_page.py`의 `media_load_stage_css()`가 넣습니다.
- 각 단계의 기능 명세·AI 안내·프롬프트 기록은 단계 폴더의 `media_stageN.md`, `CLAUDE.md`, `media_stageN_prompt.md`에 있습니다.

## 1단계 파일

| 파일 | 내용 |
|---|---|
| `media_page.py` | 화면 + 기능 (`media_render()` 함수 하나). `MEDIA_STEPS`로 하위 탭(`st.tabs(key="media-step", on_change="rerun")`)을 만들고 선택된 단계만 그림, 이전/다음 버튼은 `st.session_state["media-step"]`을 바꿔 단계 이동 |
| `media_handoff.py` | 단계 사이 데이터 모양과 주고받는 함수 (1단계 A/B 설계, 2단계 프롬프트 재료 예시) |
| `media_variable.py` | 하위 탭 ① 가설에서 변수 도출(`media_variable_step()`): '가설 불러오기' 버튼은 페이지 제목 줄 오른쪽 끝, 가설 콜아웃·빈 카드는 하위 탭 바와 같은 줄 오른쪽 자리 폭으로 표시, 탭 바 아래 왼쪽에는 핵심 요약 카드(독립 변수·KPI). KPI '클릭 점유율 ÷ 노출 점유율'은 화면에서만 '노출 대비 클릭률'로 보여 주고 가설 원문은 그대로 둠(2번 탭이 어느 쪽으로 저장해도 같은 가설로 봄)(넓은 화면만, 좁은 화면은 전체 폭). 버튼을 누르기 전에는 점선 빈 카드만 보이고, 누르면 스피너(1.2초)·토스트 뒤 아래 내용이 떠오르며 나타남 (버튼은 '다시 불러오기'로 바뀜). 위에 2번 가설 탭이 저장한 가설(`store_get("hypothesis")`)을 콜아웃에 If/Because/Then 배지로 표시 (없으면 기준 가설, 다르면 경고, `media_variable_hypothesis_step()`), 아래에 후보 변수를 가설 연결·아마존 메인 이미지 규칙·테스트 도구 기준으로 걸러 독립 변수 1개(메인 이미지 촬영 구도)와 통제·종속 변수를 정함 (`media_variable_derive_step()`) |
| `media_ab.py` | 메인 이미지 A/B (루트 `문제 시나리오.md`): 하위 탭 ② A/B 소재 준비(`media_ab_plan_step()`: `report["sqp"]`로 A(현재)/B(제안) 안, 메인 이미지 규칙, 촬영 브리프 다운로드, Manage Your Experiments 안내). 결과·판정은 `media_stage2/media_stage2_judge.py`에 보관 (지금 흐름에서는 안 씀) |
| `media_style.css` | 디자인 (class는 `media-`로 시작). 3번 탭이 열린 동안만 페이지 위·양옆 여백 축소, 이 탭 버튼 글자색, 하위 탭 알약형 스타일 |
| `images/` | media에서만 쓰는 이미지 |
| `data/` | media에서만 쓰는 데이터 |

- 위젯 `key`, `st.session_state` 키는 `media-`로 시작합니다. (예: `key="media-btn-search"`)
- 다른 탭과 데이터 주고받기: `store_set("media", ...)` / `store_get("다른모듈")`
  - 매체 결과는 `media` 키 하나에 저장합니다. (예: `{"results": [...]}`)
- Supabase 표 이름은 `media_`로 시작합니다. (예: `media_result`)
