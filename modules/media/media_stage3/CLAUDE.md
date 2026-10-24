# media 3단계(매체 제작·외주 준비) AI 작업 안내

이 파일은 Claude Code가 `modules/media/media_stage3/`에서 작업할 때 자동으로 읽습니다.

## 작업 범위 (필수)

- 담당 폴더는 `modules/media/media_stage3/` 하나입니다. 이 폴더 밖 파일은 수정하지 않습니다.
  (`modules/media/` 바로 아래 파일과 `media_stage2/`도 수정 금지 · 바꿔야 하면 무엇을 왜 바꿔야 하는지 먼저 알림)
- 기능 명세는 `media_stage3.md`를 읽고 따릅니다.
- 함수는 `media_s3_`, 위젯 key·session_state 키·CSS class는 `media-s3-`로 시작합니다.
- 진입 함수 `media_stage3_render()`의 이름은 바꾸지 않습니다.
- 하위 탭 이름은 `media_stage3.py`의 `MEDIA_S3_TAB_LABEL`에서 바꿉니다. 폴더·함수·key 이름은 탭 이름이 바뀌어도 그대로 둡니다.
- 2단계 프롬프트 재료는 `media_s3_input()`(안에서 `media_handoff_prompt()`)으로 읽습니다. 2단계가 아직 넘기지 않았으면 예시 값(`sample: True`)이 옵니다.

## 프롬프트 기록 (필수)

- 작업을 시작하면 `media_stage3_prompt.md`를 먼저 읽어 주세요.
- 작업이 끝날 때마다, 이번 대화에서 보고서에 쓸 만한 프롬프트가 있었으면 그 파일의 "AI에게: 기록 규칙"과 "기록 형식"대로 `## 기록` 맨 아래에 추가해 주세요.
- 1단계 기록 파일(`modules/media/media_prompt.md`)에는 쓰지 않습니다.
- "안녕", "응", "맞아", "고마워", "다시 해 줘" 같은 짧은 말과 단순 요청은 기록하지 않습니다.
