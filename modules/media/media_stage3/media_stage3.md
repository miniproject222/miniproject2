# 3. 매체 제작 > 3단계: 사진·영상 초안 → 외주 정리 (`media_stage3`)

- 담당 브랜치: `DH`
- 3번 탭(`media`)의 하위 탭 **④ 사진·영상 초안 제작**과 **⑤ 외주 정리**를 만듭니다. (탭 이름은 아래 "하위 탭 이름" 참고)
- 2단계가 AI로 다듬어 넘긴 프롬프트 A·B를 받아 **사진 레퍼런스 → 영상 스토리보드 → 영상 초안**을 만들고,
  **외주 촬영 업체 또는 사내 촬영팀에 보낼 자료를 zip 하나로** 묶습니다. 사진 초안은 프롬프트 A·B로, 영상 초안은 스토리보드로 만든 영상 프롬프트로 만듭니다.
- 개발이 끝나면 1단계(`min` 브랜치) 기준으로 합칩니다.

## 전체 흐름에서 3단계 위치

| 하위 탭 | 담당 | 하는 일 |
|---|---|---|
| ① 가설에서 변수 도출 · ② A/B 소재 준비 | min | 가설에서 단일 변수 추출 → A,B 테스트 소재 선정 |
| ③ 프롬프트 만들기 | JY | 기본 프롬프트 → 빈칸 → A, B 채우기 → **리포트 값으로 AI 다듬기 + 확인** |
| **④ 사진·영상 초안 제작** | **DH** | **프롬프트 A·B로 사진 초안, 스토리보드 → 영상 프롬프트로 영상 초안** |
| **⑤ 외주 정리** | **DH** | **촬영 브리프 + 찍지 말 것/넣을 것 + 만든 자료를 zip으로** |

## 작업 범위

- **이 폴더(`modules/media/media_stage3/`) 안에서만** 작업합니다.
- `modules/media/` 바로 아래 파일(`media_page.py`, `media_handoff.py`, `media_style.css`, 문서 등)과 `media_stage2/`는 고치지 않습니다.
  바꿔야 하면 1단계 담당자에게 무엇을 왜 바꿔야 하는지 알립니다.

| 파일 | 내용 |
|---|---|
| `media_stage3.py` | 하위 탭 ④ 사진·영상 초안 제작. 진입 함수 `media_stage3_render()` (이름은 바꾸지 않음) |
| `media_stage3_ai.py` | ④의 AI 호출: 사진 초안 `media_s3_make_image()`·스토리보드 `media_s3_make_storyboard()`(OpenAI), 영상 초안 `media_s3_make_video()`(Higgsfield Seedance 2.5). 모델·화질·영상 길이는 파일 맨 위 상수 |
| `media_stage3_hf_login.py` | Higgsfield 계정 로그인 (처음 한 번, 터미널: `python -m modules.media.media_stage3.media_stage3_hf_login`). 로그인 열쇠를 `.streamlit/hf_mcp_token.json`에 저장 (`.gitignore`에 등록됨) |
| `media_stage3_hf_mcp.py` | Higgsfield MCP(`https://mcp.higgsfield.ai/mcp`)로 영상 만들기: `generate_video` → `jobs_wait`. 구독 크레딧 사용, 열쇠 자동 갱신 |
| `media_stage3_store.py` | 작업물 보관: 사진·영상·스토리보드·만드는 중인 영상 작업 번호를 `data/workspace/`에 저장하고, 화면을 그릴 때 다시 읽음 (탭을 옮기거나 새로고침해도 유지, `.gitignore`에 등록) |
| `media_stage3_export.py` | 하위 탭 ⑤ 외주 정리. 진입 함수 `media_stage3_export_render()` (이름은 바꾸지 않음) |
| `media_stage3_style.css` | 디자인 (class는 `media-s3-`로 시작). `media_page.py`가 3번 탭을 열 때 읽어 넣습니다 |
| `media_stage3_prompt.md` | 프롬프트 기록 |
| `data/` | 3단계에서만 쓰는 데이터 |
| `images/` | 3단계에서만 쓰는 이미지 |

## 하위 탭 이름

- ④ 이름은 `media_stage3.py`의 `MEDIA_S3_TAB_LABEL`(지금 '사진·영상 초안 제작'), ⑤ 이름은 `media_stage3_export.py`의 `MEDIA_S3_EXPORT_TAB_LABEL`(지금 '외주 정리')에서 정합니다. 바꾸면 하위 탭과 이전/다음 버튼 글자가 함께 바뀝니다.
- 폴더·파일·함수·key 이름은 탭 이름이 아니라 단계 번호(`media_stage3`, `media_s3_`, `media-s3-`)라서 탭 이름이 바뀌어도 그대로 둡니다.
- 화면 안에 탭 이름을 문자열로 다시 쓰지 않습니다. 필요하면 위 상수를 씁니다.

## 이름 규칙 (같은 media 안에서 겹치지 않게)

- 함수: `media_s3_...` (진입 함수만 `media_stage3_render`, `media_stage3_export_render`)
- 위젯 `key`, `st.session_state` 키, CSS class: `media-s3-...` (예: `key="media-s3-btn-export"`)
- Supabase 표를 만들면 `media_` 로 시작 (예: `media_reference`)

## 받는 값 (2단계 → 3단계)

`media_handoff_prompt()`(`modules/media/media_handoff.py`)로 받습니다. 2단계가 아직 넘기지 않았으면 예시 값(`MEDIA_HANDOFF_PROMPT_SAMPLE`)에 `sample: True`가 붙어 옵니다.

| 키 | 내용 |
|---|---|
| `variable` | 단일 변수 이름 |
| `base`, `slot_a`, `slot_b` | 기본 프롬프트(빈칸 `{slot}`)와 A·B 빈칸 문구 |
| `fixed` | 고정 요소 (다듬은 뒤에도 그대로 있어야 하는 문구) |
| `prompt_a`, `prompt_b` | **2단계에서 다듬은 프롬프트 A·B** (비어 있으면 빈칸만 채운 문장) |
| `changes` | 바꾼 곳 표 (바꾼 곳 / 뺌·더함 / 이유 / 근거 DB ID) |
| `avoid`, `include` | **찍지 말 것 / 넣을 것** → ⑤ 촬영 브리프에 그대로 들어감 |

- 받은 A·B는 `media_handoff_check()`로 한 번 더 확인합니다 (빈칸만 다른가, 고정 요소가 남았나).
- 리포트 값(`store_get("report")`)은 ④ 스토리보드에서 `ad_claims.allowed_scenes`(허용 장면)를 씁니다.

## 화면 구성

### ④ 사진·영상 초안 제작 (`media_stage3.py`, AI는 `media_stage3_ai.py`)
- AI 버튼은 `.streamlit/secrets.toml`에 키가 있으면 켜지고 (사진·스토리보드는 `OPENAI_API_KEY`, 영상은 `HF_KEY` = "키ID:키시크릿"), 없으면 꺼진 채 "키를 넣어 주세요" 안내가 보입니다. 키가 없어도 파일을 직접 올려서 끝까지 진행할 수 있습니다.
- 화면 맨 위에서 받은 프롬프트 A·B를 확인하고, 안쪽 하위 탭 2개(`st.tabs(key="media-s3-sub")`)로 나눕니다.
- **사진 초안 제작**: 사진 A·B 칸마다 다듬은 프롬프트와 `사진 A 만들기`·`사진 B 만들기` 버튼
  - 누르면 그 프롬프트로 사진을 만들어(`gpt-image-1-mini`, 화질 low, 10~30초) 칸 안에 보여 주고 `photo_A_ai.png`·`photo_B_ai.png`로 보관 (다시 누르면 바꿔 끼움)
  - 직접 만든 사진도 올릴 수 있음 (AI 사진과 같이 보관)
- **영상 초안 제작**: 순서대로 진행
  1. **스토리보드 만들기**: `스토리보드 만들기` 버튼을 누르면 리포트 값(허용 장면 `ad_claims.allowed_scenes`, 쓸 수 있는 문구 `ad_claims.claims`, 금지 표현 `ad_claims.forbidden`, 서리 강점)과 프롬프트 A·B로 문제 → 해결 → 증거 → 신뢰 → 마무리 장면 표를 채움 (`gpt-4.1-mini`). 표는 직접 고칠 수 있고, 금지 표현이 남아 있으면 경고 → **`스토리보드 확정`**
  2. **영상 초안 만들기**: 스토리보드를 확정해야 열림. 확정한 장면을 이어 붙인 영상 프롬프트(`media_s3_video_prompt()`)로 `영상 초안 만들기`를 누르면 **Higgsfield 계정 로그인(MCP)이 되어 있으면 구독 크레딧으로**(Seedance 2.5, 5초 약 35크레딧), 아니면 **Higgsfield API 잔액(HF_KEY)으로** 영상을 만들어(`bytedance/seedance-2.5/text-to-video`, 5초, 720p, 16:9, 소리 없음, 1~5분) 화면에 보여 주고 `video_draft_ai.mp4`로 보관. **Higgsfield API는 선불 잔액에서 차감**(사이트 구독 크레딧과 별개, 최소 충전 $5). 잔액 부족·실패·검열이면 경고만 띄움. 직접 만든 영상도 올릴 수 있음
- 화면 맨 아래 **'⑤로 넘기기'** 버튼(`media_s3_handoff_step()`, 스토리보드를 확정해야 눌림)을 눌렀을 때만 확정한 스토리보드와 파일 이름이 Supabase(`handoff.assets`)로 넘어갑니다. 넘긴 뒤 바뀌면 '다시 넘기기 필요'가 보입니다.
- **작업 공간** (`media_s3_workspace()`): 사진 초안 제작 탭과 영상 초안 제작 탭 아래에 각각 하나씩. AI로 만든 파일(🤖)과 직접 올린 파일(📁)을 한곳에 미리 보기로 모으고, 파일마다 `내려받기`·`지우기`. **작업 공간에 있는 파일이 ⑤ 외주 정리로 갑니다.** 사진은 OpenAI 키(`OPENAI_API_KEY`), 영상은 Higgsfield 키(`HF_KEY`)로 만듭니다.
- 버튼은 모두 `type="primary"`로 둡니다. media 탭 공용 CSS(`media_style.css`)가 탭 안 버튼 글자를 흰색으로 바꿔서, 흰 바탕 버튼은 글자가 안 보이기 때문입니다.
- Higgsfield가 영상 대신 **비슷한 프리셋 추천**(`notice.type == "preset_recommendation"`)을 돌려주면, 추천을 거절(`declined_preset_id`)하고 프롬프트 그대로 다시 요청합니다. 작업 번호는 `results[].id`에서만 받고, 없는 작업(404)이면 기다리지 않고 다시 누르라고 안내합니다.
- **방금 만든 영상** (`media_s3_latest_video()`): 영상 만들기 바로 아래에 가장 최근 AI 영상을 크게 보여 주고, 막 완성된 경우에는 자동 재생(브라우저 규칙상 소리 없이)합니다. 저작권 확인 대기(`ip_detected`)면 Higgsfield 사이트에서 확인해야 한다고 안내합니다.
- **유지:** 만든 사진·영상, 스토리보드, 확정본은 `data/workspace/`에도 저장돼서 다른 탭에 다녀오거나 새로고침해도 그대로 있습니다 (`media_s3_store_load()`).
- **영상(계정 로그인)은 요청만 보내고 작업 번호를 저장**합니다. 화면이 10초마다 상태를 확인하고(`media_s3_video_job_step()`, `st.fragment(run_every=10)`), 완성되면 작업 공간에 `video_<작업번호 앞 8자리>_ai.mp4`로 자동으로 넣습니다. 만드는 중에는 버튼이 잠기고, 다른 탭에 다녀와도 이어서 확인합니다. 결과 주소는 `job_status`의 `generation.results.rawUrl`에서 받습니다.
- 사진·영상 파일, 스토리보드는 session_state(`media-s3-assets-photos`, `media-s3-assets-videos`, `media-s3-storyboard`, 확정본 `media-s3-storyboard-done`)에 보관해 ⑤에서 씁니다. (하위 탭을 옮기면 위젯 값이 지워져서 따로 보관)
- AI로 만든 사진·영상은 아마존 메인 이미지로 쓰지 않습니다. 외주 촬영 레퍼런스, 서브 이미지, 광고 초안 용도입니다.

### ⑤ 외주 정리 (`media_stage3_export.py`)
- 촬영 브리프 미리 보기 (`media_s3_brief()`): 맨 위에 단일 변수 "A와 B는 이것만 다르게", 조명·배경·보정은 똑같이, 고정 요소, 찍지 말 것 / 넣을 것, 받을 것, "법률 자문 아님" 안내
- zip 내려받기 (`media_s3_package()`, 스토리보드는 확정본이 있으면 확정본): `README_촬영브리프.txt`, `prompt_A.txt`, `prompt_B.txt`, `prompts.json`, `video_storyboard.csv`, `photo_reference/`, `video_draft/`
- ④에서 넘긴 값(`media_handoff_assets()`)만 씁니다. 안 넘겼으면 안내를 보여 주고 내려받기를 막습니다. 사진·영상 파일은 같은 브라우저 접속에서 ④에 올린 것 중 넘긴 이름만 zip에 넣습니다.
- 받은 프롬프트 A·B가 확인을 통과하지 못해도 내려받기를 막습니다.

## 넘기는 값

- 3번 탭의 마지막 단계라 다른 단계에 넘기는 값은 없습니다. 결과는 외주 전달용 zip 파일입니다.

## 정해야 할 것

- 이미지 생성 AI, 영상 생성 도구 (정해지면 `requirements.txt`·`secrets.toml`에 넣을 줄을 PM에게 알림)
- 1단계의 '촬영 브리프 (외주용)'(`media_ab.py`)와 ⑤ 외주 정리를 한 곳으로 합칠지 (1단계 담당과 협의)
