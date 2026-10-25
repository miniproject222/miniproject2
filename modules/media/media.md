# 3. 매체 제작 (`media`)

- 매체 제작: 하위 탭 5개 가설에서 변수 도출 → A/B 소재 준비 → 프롬프트 만들기(AI 다듬기) → 사진·영상 초안 제작 → 외주 정리 (둥근 알약형 탭) (각 단계 아래 이전/다음 버튼으로 이동)
- 끝은 외주업체에 넘길 레퍼런스 파일(프롬프트, 사진·영상 초안, 고정 요소) 준비까지입니다. A/B 결과 판정, UTM, 매체 외 솔루션 제안은 지금 흐름에서 빠졌습니다 (판정 코드는 `media_stage2/media_stage2_judge.py`에 보관)

## 3단계 나눠 개발 (동시 개발 후 1단계 기준으로 합침)

| 단계 | 하위 탭 | 브랜치 | 담당 폴더·파일 | 이름 접두어 |
|---|---|---|---|---|
| 1단계 | 단일 변수 추출 ~ A/B 소재 선정 (가설에서 변수 도출, A/B 소재 준비) | `min` | `modules/media/` 바로 아래 파일 전부 (공용 파일 포함) | `media_` / `media-` |
| 2단계 | ③ 프롬프트 만들기: 기본 프롬프트 → 빈칸 → A, B 채우기 → 리포트 값으로 AI 다듬기 + 확인 | `JY` | `media_stage2/`만 | `media_s2_` / `media-s2-` |
| 3단계 | ④ 사진·영상 초안 제작(프롬프트로 사진 초안, 스토리보드 → 영상 초안) → ⑤ 외주 정리(브리프 + zip) | `DH` | `media_stage3/`만 | `media_s3_` / `media-s3-` |

- 공용 파일(`media_page.py`, `media_handoff.py`, `media_style.css`, `media.md`, `media_prompt.md`, `CLAUDE.md`)은 1단계 담당자만 고칩니다.
- 연결 지점: `media_page.py`가 하위 탭에서 `media_stage2_render()`(③), `media_stage3_render()`(④), `media_stage3_export_render()`(⑤)만 부릅니다.
- 2·3단계 하위 탭 이름은 각 단계 파일의 `MEDIA_S2_TAB_LABEL`, `MEDIA_S3_TAB_LABEL`, `MEDIA_S3_EXPORT_TAB_LABEL`에서 정하고 `media_page.py`가 가져다 씁니다. 단계 담당자가 직접 바꿉니다.
- 단계 사이 데이터: `media_handoff.py` (1→2 `media_handoff_set_plan()` / `media_handoff_plan()`, 2→3 `media_handoff_set_prompt()` / `media_handoff_prompt()`, ④→⑤ `media_handoff_set_assets()` / `media_handoff_assets()`).
  - 값은 **Supabase 공용 저장소**(`store("media")`의 `handoff` 칸: `plan`, `prompt`, `assets`)에 저장됩니다. 프로젝트 파일은 바뀌지 않아 커밋·충돌이 생기지 않고, 다른 컴퓨터에서도 바로 이어집니다. (읽을 때 3초마다 Supabase에서 새로 읽음)
  - **각 단계의 넘기기 버튼을 눌렀을 때만** 저장됩니다. 화면을 열기만 해서는 저장되지 않습니다. 앞 단계가 아직 안 넘겼으면 예시 값(`sample: True`)이 와서 각자 먼저 개발할 수 있습니다.
    - ①: 선정 표 아래 '이 변수로 확정' 버튼 (`media_variable_confirm_step()`). 확정한 뒤 리포트 값 등이 바뀌면 '다시 확정 필요'와 '다시 확정' 버튼이 보입니다.
      확정할 때 고른 B안의 영어 레퍼런스 프롬프트(후보 파일의 `ref_prompt`)도 `b_ref`로 같이 넘기고, 2단계는 여기서 빈칸 B를 잘라 씁니다.
      하위 탭 ② A/B 소재 준비부터는 모두 이 확정 값을 씁니다. ①에서 고르기만 하고 확정하지 않았으면 ②는 이전 확정 값을 보여 주며
      '확정 안 됨' 안내와 '① 으로 가서 확정하기' 버튼을 띄우고, 한 번도 확정하지 않았으면 A/B 대신 빈 카드와 같은 버튼만 보여 줍니다.
      `MEDIA_HANDOFF_PLAN` 기본값에 1번 리포트 값(`sqp.query`, `sqp.listing.main_image` → `a`, `sqp.ratio` → `kpi_now`, `sqp.kpi_goal`)을 덮어쓴 값입니다. 2번 탭 가설이 메인 이미지 A/B 가설이 아니어도 기준 가설로 진행하므로 확정 버튼은 꺼지지 않습니다.
    - ③: '④로 넘기기' 버튼 (`media_s2_handoff_step()`, 확인을 통과해야 눌림)
    - ④: '⑤로 넘기기' 버튼 (`media_s3_handoff_step()`, 스토리보드를 확정해야 눌림). 사진·영상 파일 자체는 크기 때문에 Supabase에 넣지 않고 같은 브라우저 접속 안에만 둡니다.
  - Supabase는 팀 전체가 같은 값을 보므로, 누군가 다시 넘기면 모두의 다음 단계 화면이 그 값으로 바뀝니다.
  - Supabase에 연결할 수 없으면(`.streamlit/secrets.toml` 없음) 같은 브라우저 접속 안에서만 이어집니다.
  - 2→3 모양(`MEDIA_HANDOFF_PROMPT_SAMPLE`): `variable` 단일 변수, `base` 기본 프롬프트(빈칸 `{slot}`), `slot_a`, `slot_b` 빈칸 문구, `fixed` 고정 요소, `prompt_a`, `prompt_b`, `changes`, `avoid`, `include`
- 단계 폴더의 CSS(`media_stage2_style.css`, `media_stage3_style.css`)는 공통 로더가 읽지 않아 `media_page.py`의 `media_load_stage_css()`가 넣습니다.
- 각 단계의 기능 명세·AI 안내·프롬프트 기록은 단계 폴더의 `media_stageN.md`, `CLAUDE.md`, `media_stageN_prompt.md`에 있습니다.

## 1단계 파일

| 파일 | 내용 |
|---|---|
| `media_page.py` | 화면 + 기능 (`media_render()` 함수 하나). `MEDIA_STEPS`로 하위 탭(`st.tabs(key="media-step", on_change="rerun")`)을 만들고 선택된 단계만 그림, 하위 탭 ②~④(2·3단계 포함)에는 맨 위에 목표 KPI 칩(`media_variable_kpi_chip()`)을 먼저 그림, 이전/다음 버튼은 `st.session_state["media-step"]`을 바꿔 단계 이동 |
| `media_handoff.py` | 단계 사이 데이터 모양과 주고받는 함수 (1단계 A/B 설계, 2단계 프롬프트 재료 예시) |
| `media_variable.py` | 하위 탭 ① 가설에서 변수 도출(`media_variable_step()`): '가설 불러오기' 버튼은 페이지 제목 줄 오른쪽 끝, 가설 콜아웃·빈 카드는 하위 탭 바와 같은 줄 오른쪽 자리 폭으로 표시, 탭 바 아래 왼쪽에는 핵심 요약 카드(독립 변수·KPI). KPI '클릭 점유율 ÷ 노출 점유율'은 화면에서만 '노출 대비 클릭률'로 보여 주고 가설 원문은 그대로 둠(2번 탭이 어느 쪽으로 저장해도 같은 가설로 봄)(넓은 화면만, 좁은 화면은 전체 폭). 버튼을 누르기 전에는 점선 빈 카드만 보이고, 누르면 스피너(1.2초)·토스트 뒤 아래 내용이 떠오르며 나타남 (버튼은 '다시 불러오기'로 바뀜). 위에 2번 가설 탭이 저장한 가설(`store_get("hypothesis")`)을 콜아웃에 If/Because/Then 배지로 표시 (없으면 기준 가설, `media_variable_hypothesis_step()`), 아래 왼쪽 '후보 변수 걸러내기' 표에서 A/B로 실험할 변수를 고르고, 오른쪽 '선정한 단일 변수'에서 그 변수를 A/B로 나눔 (`media_variable_derive_step()`). 표의 한 줄 = 변수 하나 (예: 메인 이미지 촬영 구도 / 제목 앞 문구 / 가격·쿠폰). 후보는 가설별 묶음으로 `data/media_variable_candidates.json`의 `variables`에 두고(변수마다 B안 목록 `b_options`, 가설이 바뀌면 그 가설의 묶음만 추가, 읽는 곳은 `media_variable_candidate_set()`), 판정은 파일에 쓰지 않고 규칙으로 계산함 (`media_variable_judge()`: 가설의 If → 2·3단계가 이어받을 수 있는 메인 이미지 변수 → 메인 이미지 규칙 안에서 만들 B안이 있는지). 변수 표는 `st.dataframe` 한 줄 선택으로, 통과한 줄을 누르면 그 변수로 바뀌고 제외된 줄을 누르면 이유를 토스트로 알린 뒤 선택을 되돌림. 오른쪽에서는 고른 변수의 B안을 버튼(`st.segmented_control`, key `media-variable-pick-<변수 번호>`)으로 고르고, 고른 변수·B가 plan에 들어감 (안 골랐으면 확정해 둔 값 → 첫 통과 변수·첫 B안). 고른 B안은 `st.session_state["media-variable-b"]`(`MEDIA_VARIABLE_B_KEY`, 변수 이름 → B안)에도 남겨, 다른 하위 탭에 다녀와도 확정 전 선택이 사라지지 않게 함 (Streamlit은 그려지지 않은 위젯의 값을 지움). A는 지금 아마존에 올라간 메인 이미지라 고정이고(표에 '현재 사진 · 고정', ⓘ에 이유), B만 고름. 규칙을 어겨 B로 못 쓰는 안(손·텍스트 등)은 오른쪽 제목 옆 ⓘ에 대신 쓸 곳과 함께 보여 줌. 변수 표는 통과 → 제외 순으로 3줄만 보여 주고(`MEDIA_VARIABLE_SHOW`, 목록 순서 = 우선순위), 표에 안 보이는 제외 변수는 왼쪽 제목 옆 ⓘ에 적음. 줄 높이(`MEDIA_VARIABLE_ROW_PX` 47px)로 왼쪽 표와 오른쪽 'B안 버튼 + A·B 표'의 높이를 맞춤. 2번 탭 가설은 아직 문장 형식이 자주 바뀌므로 문장이 똑같지 않아도 '메인 이미지'와 KPI('클릭 점유율 ÷ 노출 점유율' 또는 '노출 대비 클릭률')가 함께 들어 있으면 같은 가설로 보고 그 문장을 보여 줌(`media_variable_hypo_match()`). 그렇지 않은 가설(예: 리뷰 수, 광고 표현 준수율)이면 막지 않고 기준 가설로 진행하며 '기준 가설로 진행' 안내 한 줄과 ⓘ에 2번 탭 원문을 보여 줌 (2번 탭 원문 읽기는 `media_variable_saved_hypothesis()`). '선정한 단일 변수' 표는 스크롤 없이 한 화면에 보이도록 A·B 두 줄만 보여 주고, 통제 변수·KPI 식·안전장치·B로 못 쓰는 안·가설에 딸린 참고 설명(후보 묶음의 note)은 제목 옆 ⓘ 툴팁에 둠 (변수 걸러내기 기준도 제목 옆 ⓘ). 요약 카드와 선정 표는 A/B 설계(plan, `media_variable_plan()`)로 그리고, 사용자가 '이 변수로 확정'을 누르면 같은 값을 하위 탭 ②와 2단계로 넘김 (확정 값은 `media_variable_confirmed_plan()`, 확정 상태 none/same/changed는 `media_variable_confirm_state()`). 리포트 값이 없으면 기본값을 쓰고 표 아래에 어떤 항목이 기본값인지 표시. 목표 KPI 칩 `media_variable_kpi_chip()`: 하위 탭 ②~④에서 탭 바와 같은 줄 오른쪽 끝에 '[🎯 A/B 목표 KPI] 노출 대비 클릭률 0.63배 → 0.8배 이상 · 가상 데이터'를 띄워 단계를 옮겨도 목표값이 보이게 함 (앞 배지로 칩이 무엇인지 알림, 짧은 출처 표시는 `MEDIA_VARIABLE_SQP_LABEL`, 목표의 뜻·검색어·노출·클릭 점유율·리포트의 긴 출처 문장 `sqp.source`·기간은 칩의 ⓘ 툴팁, 화면 폭 1280px 미만이면 탭 바 아래 줄 오른쪽. 칩을 감싼 칸이 탭 바를 덮어 클릭을 막지 않도록 칸 폭을 칩에 맞춤). 바깥 값을 읽는 곳은 `media_variable_hypothesis()`(가설), `media_variable_report_sqp()`(리포트) 두 함수뿐 (출처가 DB 등으로 바뀌면 여기만 고침) |
| `media_ab.py` | 메인 이미지 A/B (루트 `문제 시나리오.md`): 하위 탭 ② A/B 소재 준비(`media_ab_plan_step()`: 하위 탭 ①에서 확정한 plan(`media_variable_confirmed_plan()`)으로 A(현재)/B(제안) 안, 메인 이미지 규칙, 촬영 브리프 다운로드, Manage Your Experiments 안내. plan에 없는 지금 이미지 문제점만 `media_variable_report_sqp()`로 읽고 (검색어·목표 KPI·점유율·출처는 탭 바 오른쪽 목표 KPI 칩에 있음), AI 각도 레퍼런스 프롬프트는 확정한 B안의 ref_prompt를 씀(`media_variable_ref_prompt()`), 리포트 값이 없어도 기본값으로 그림. 확정 전이면 빈 카드, ①에서 고른 값이 확정과 다르면 '확정 안 됨' 안내와 ①로 가는 버튼(`media_variable_go_step()`)을 보여 줌). 결과·판정은 `media_stage2/media_stage2_judge.py`에 보관 (지금 흐름에서는 안 씀) |
| `media_style.css` | 디자인 (class는 `media-`로 시작). 3번 탭이 열린 동안만 페이지 위·양옆 여백 축소, 이 탭 버튼 글자색, 하위 탭 알약형 스타일, 목표 KPI 칩 위치, 하위 탭 ① 가설 줄을 끌어올려도 하위 탭 바 클릭이 막히지 않게 함 |
| `images/` | media에서만 쓰는 이미지 |
| `data/` | media에서만 쓰는 데이터 |

- 위젯 `key`, `st.session_state` 키는 `media-`로 시작합니다. (예: `key="media-btn-search"`)
- 다른 탭과 데이터 주고받기: `store_set("media", ...)` / `store_get("다른모듈")`
  - 매체 결과는 `media` 키 하나에 저장합니다. (예: `{"results": [...]}`)
- Supabase 표 이름은 `media_`로 시작합니다. (예: `media_result`)
