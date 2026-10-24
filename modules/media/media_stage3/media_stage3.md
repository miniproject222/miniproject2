# 3. 매체 제작 > 3단계: 매체 제작·외주 준비 (`media_stage3`)

- 담당 브랜치: `DH`
- 3번 탭(`media`)의 3단계 하위 탭(지금 이름 '매체 제작·외주 준비', 아래 "하위 탭 이름" 참고)을 만듭니다.
- 2단계가 만든 프롬프트 재료를 받아 **AI로 다듬고 확인 → 매체(사진·영상 초안) 제작 → 외주용 파일 준비**까지 합니다.
- 개발이 끝나면 1단계(`min` 브랜치) 기준으로 합칩니다.

## 전체 흐름에서 3단계 위치

| 단계 | 담당 | 하는 일 |
|---|---|---|
| 1단계 | min | 가설에서 단일 변수 추출 → A,B 테스트 소재 선정 |
| 2단계 | JY | 기본 프롬프트 1개 쓰기 → 단일 변수 칸 비워 두기 → 빈칸 채워 A, B 만들기 |
| **3단계** | **DH** | **AI로 다듬기 + 확인 → 매체 제작 → 외주 레퍼런스 취합·외주용 파일 준비** |

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
- Supabase 표를 만들면 `media_` 로 시작 (예: `media_reference`)

## 받는 값 (2단계 → 3단계)

`media_s3_input()`이 `media_handoff_prompt()`(`modules/media/media_handoff.py`)로 아래 모양을 받아 옵니다.
**2단계가 아직 `media_handoff_set_prompt()`로 넘기지 않았으면 예시 값(`MEDIA_HANDOFF_PROMPT_SAMPLE`)에 `sample: True`가 붙어 옵니다.**
2단계 값은 `media_stage2/data/media_stage2_prompt.json` 파일이라, 2단계 담당이 푸시한 뒤 풀 받으면 자동으로 들어옵니다.

| 키 | 내용 | 예 |
|---|---|---|
| `variable` | 단일 변수 이름 | 메인 이미지 촬영 구도 |
| `base` | 기본 프롬프트 (빈칸 자리는 `{slot}`) | `..., a cooling mattress pad 90x200 cm {slot}, ...` |
| `slot_a` | A 빈칸 문구 | `folded, seen from above` |
| `slot_b` | B 빈칸 문구 | `laid flat, ... one corner gently lifted ...` |
| `fixed` | 고정 요소 (다듬은 뒤에도 프롬프트 안에 그대로 있어야 하는 문구) | `["white seamless background", "90x200 cm", ...]` |

- 완성된 A, B 두 줄만 받으면 어디가 빈칸이었는지 알 수 없어 확인을 못 합니다. 그래서 **기본 프롬프트와 빈칸을 따로** 받습니다.

## 화면 구성

1. **① 프롬프트 다듬기 + 확인**
   - `AI로 다듬기` 버튼 (AI 도구가 정해지기 전이라 꺼져 있음, 지금은 칸에서 직접 고침)
   - 프롬프트 A, B를 나란히 두 칸에 보여 주고, 칸마다 `되돌리기`(빈칸만 채운 원래 문장으로) 버튼
   - 확인 규칙 (`media_s3_check()`):
     - 빈칸 문구(`slot_a`, `slot_b`)가 그대로 남아 있는가
     - 빈칸 문구를 빼면 A와 B가 글자까지 똑같은가
     - 고정 요소(`fixed`)가 A, B 모두에 남아 있는가
   - 하나라도 어기면 경고를 띄우고, 외주 파일 다운로드를 막음
2. **② 매체 제작 (사진·영상 초안)**
   - `A/B 매체 생성` 버튼 (생성 도구가 정해지기 전이라 꺼져 있음)
   - 지금은 만든 사진·영상 파일을 직접 올림 (png, jpg, webp, mp4, mov / 파일 이름에 A 또는 B)
   - AI로 만든 사진·영상은 아마존 메인 이미지로 쓰지 않음 (외주 촬영 레퍼런스, 서브 이미지, 광고 초안 용도)
3. **③ 외주 레퍼런스 정리**
   - zip 하나로 묶어 내려받기 (`media_s3_package()`): `README.txt`(안내문), `prompt_A.txt`, `prompt_B.txt`, `prompts.json`, `reference/`(올린 매체)

## 넘기는 값

- 3번 탭의 마지막 단계라 다른 단계에 넘기는 값은 없습니다. 결과는 외주 전달용 zip 파일입니다.

## 정해야 할 것

- AI 다듬기 도구와 이미지·영상 생성 도구 (정해지면 `requirements.txt`·`secrets.toml.example`에 넣을 줄을 PM에게 알림)
- 1단계의 '촬영 브리프 (외주용)'(`media_ab.py`)와 외주 자료를 한 곳으로 합칠지 (1단계 담당과 협의)
