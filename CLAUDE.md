# Claude Code 공통 작업 지침

이 파일은 모든 팀원이 함께 사용하는 프로젝트 지침이다. (PM 관리)
특정 작업자의 이름이나 담당 모듈을 고정하지 않는다.

## 참조 문서

작업 전에 다음 문서를 읽고 적용한다.
세부 규칙은 각 문서에서 관리하며 이 파일에 중복 작성하지 않는다.

- `README.md`: 프로젝트 개요, 기술 구조, 파일 구조, 실행/배포 방법
- `RULES.md`: 팀 작업 규칙 (수정 범위, 이름 짓기, 충돌 방지, 비밀값, AI 도구 사용, Git, 커밋 메시지)
- `modules/[모듈코드]/[모듈코드].md`: 담당 모듈 설명 (기능 명세)
- `modules/[모듈코드]/CLAUDE.md`: 담당 모듈의 AI 작업 안내
- `modules/[모듈코드]/[모듈코드]_prompt.md`: 담당 모듈의 프롬프트 기록 (2026-10-26부터 자동 기록 중단, 요청할 때만 추가)

참조 문서가 없거나 내용이 서로 충돌하면 해당 사항을 알리고,
영향받는 작업을 진행하기 전에 기준을 확인한다.

## 작업 시작

1. 첫 작업 전에 `README.md`와 `RULES.md`를 확인한다.
2. 담당 모듈 코드(`home`, `report`, `hypothesis`, `media`, `weather` 중 하나)를 확인한다.
   - 이전 `solution` 모듈은 삭제됐다. (`media` 흐름은 외주 레퍼런스 준비까지이며 솔루션 제안은 빠짐)
   - `media` 모듈은 3단계로 나눠 개발한다. 2·3단계 담당은 `modules/media/media_stageN/` 폴더만 작업하고
     그 폴더의 `CLAUDE.md`, `media_stageN.md`, `media_stageN_prompt.md`를 따른다.
     `modules/media/` 바로 아래 파일(공용 파일 포함)은 1단계 담당만 고친다.
   - 현재 대화에서 이미 확인된 정보는 다시 묻지 않는다.
   - 요청에 모듈 폴더나 파일이 분명히 나오면 그 모듈로 본다.
   - 새 대화에서 모듈을 알 수 없으면 확인한다.
   - 브랜치 이름이나 기존 기록만으로 작업자나 모듈을 추측하지 않는다.
3. 담당 모듈의 `[모듈코드].md`, `CLAUDE.md`, `[모듈코드]_prompt.md`와 관련 코드를 읽는다.
   - 모듈 설명에 없는 요구사항은 임의로 확정하지 않고 확인한다.
4. Git 상태를 읽기 전용으로 확인한다.
   - 현재 브랜치와 미커밋 변경 사항을 확인한다.
   - `main`, `develop`(또는 `dev`)이면 코드 수정 전에 알리고
     작업 브랜치(`feature/모듈코드-기능명`) 준비를 요청한다.
   - Git 저장소가 아니라면 그 사실을 알리고,
     명시적으로 요청된 로컬 작업 범위에 따른다.

## 작업 진행

- `modules/[모듈코드]/` 폴더 안에서만 작업한다.
- 폴더 밖 파일(`app.py`, `common/`, `.streamlit/`, `data/`, 다른 모듈 폴더, `README.md`, `RULES.md`)은
  수정하지 않고, 필요하면 무엇을 왜 바꿔야 하는지 먼저 알린다.
- `requirements.txt`, `.streamlit/secrets.toml.example`에 추가할 줄이 생기면
  직접 추가하지 않고 추가할 한 줄을 알려 준다.
- 기존 작업과 다른 팀원의 변경 사항을 임의로 되돌리지 않는다.
- 이름, 화면 함수, 디자인, 데이터, 비밀값 규칙은 `RULES.md`를 따른다.
- `CLAUDE.md`는 도구가 인식하는 표준 파일명이므로
  "파일명은 모듈 코드로 시작" 규칙의 예외로 유지한다.
- Git 변경 작업(`add`, `commit`, `push`, `merge`)과 배포는 실행하지 않는다.
- 파일 수정이 권한 설정(`.claude/settings.local.json`)으로 막히면 터미널 명령 등 다른 방법으로
  우회하지 않고, 어떤 파일을 왜 고쳐야 하는지 담당자에게 알린다.

## 수정 잠금 파일 (`.claude/settings.local.json`)

**`.claude/settings.local.json` = 내 Claude가 다른 사람 폴더를 못 고치게 잠그는 파일**

**왜 하냐면**
- Claude한테 작업을 시키면 편하다는 이유로 **공용 파일이나 다른 사람 폴더까지 고치는 경우가 많아요.**
- 그러면 GitHub에서 합칠 때 **충돌이 나거나 남의 화면이 깨져요.**
- 매번 "home만 고쳐"라고 말해도 **까먹거나 무시할 수 있어요.**
- 이 파일이 있으면 **실수해도 자동으로 막혀서** 처음부터 문제가 안 생겨요.

**어떻게 작동하냐면**
- 내 모듈 폴더만 수정할 수 있어요.
- 다른 폴더는 보기만 되고 수정은 막혀요.
- 한 번 만들면 계속 적용돼요.
- 내 컴퓨터에만 있고 GitHub에는 안 올라가요. (`.gitignore`에 `.claude/settings.local.json`이 있어야 함)

**만드는 법**
1. 프로젝트 맨 위에 `.claude` 폴더 만들기
2. 그 안에 `settings.local.json` 만들기
3. 아래 예시 내용 붙여넣고, 모듈 이름만 내 것으로 바꾸기
   - 예시는 `home` 담당자용이에요. 내 모듈 줄(`"Edit(/modules/내모듈/**)"`)을 목록에서 **지우고**,
     대신 `home` 줄을 넣으면 돼요.
   - 경로 맨 앞의 `/`는 컴퓨터 맨 위가 아니라 **프로젝트 맨 위 폴더**를 뜻해요.

```json
{
  "permissions": {
    "deny": [
      "Edit(/app.py)",
      "Edit(/README.md)",
      "Edit(/RULES.md)",
      "Edit(/CLAUDE.md)",
      "Edit(/requirements.txt)",
      "Edit(/.gitignore)",
      "Edit(/.editorconfig)",
      "Edit(/.streamlit/**)",
      "Edit(/common/**)",
      "Edit(/data/**)",
      "Edit(/docs/**)",
      "Edit(/modules/report/**)",
      "Edit(/modules/hypothesis/**)",
      "Edit(/modules/media/**)",
      "Edit(/modules/weather/**)"
    ]
  }
}
```

**`media` 2·3단계 담당자는** 위 예시에서 `media` 줄(`"Edit(/modules/media/**)"`)을 넣지 말고,
대신 아래 줄을 넣어요.

- 2단계: `"Edit(/modules/media/*.*)"`, `"Edit(/modules/media/data/**)"`, `"Edit(/modules/media/images/**)"`, `"Edit(/modules/media/media_stage3/**)"`
- 3단계: 위 2단계 줄과 같고, 마지막 줄만 `"Edit(/modules/media/media_stage2/**)"`로 바꿔요.

**`media` 1단계 담당자는** `media` 줄을 넣지 않고, 2·3단계 폴더만 잠가요.

- 1단계: `"Edit(/modules/media/media_stage2/**)"`, `"Edit(/modules/media/media_stage3/**)"`

> 주의: 이 파일은 Claude의 **파일 수정 기능**을 막아요. 터미널 명령으로 파일을 바꾸는 것까지
> 완벽히 막지는 못하니, 작업 후 GitHub Desktop의 변경 파일 목록은 계속 확인해요.

**한 줄 요약:** `RULES.md`는 "고치지 마세요"라는 **부탁**이고, 이 파일은 실제로 **잠그는 자물쇠**예요. 합칠 때 충돌을 미리 막으려고 해요.

## 검증 및 기록

- 변경 범위에 필요한 검증을 수행한다. (예: 문법 확인, `streamlit run app.py`로 탭 확인,
  `RULES.md`의 "PR 올리기 전 체크리스트")
- 실제 실행한 검증, 실패한 검증, 미검증 항목을 구분한다.
- 실제 실행하지 않은 검증이나 결과를 만들어 기록하지 않는다.
- 프롬프트 기록은 자동으로 갱신하지 않는다 (2026-10-26 PM 결정). 사용자가 직접 요청할 때만
  담당 모듈의 `[모듈코드]_prompt.md` 규칙에 따라 추가한다.
- 모듈이 불명확하면 아무 모듈의 기록 파일에나 기록하지 않는다.

## 완료 보고

작업이 끝나면 다음 내용을 정리한다.

1. 변경한 파일과 변경 이유
2. 실제 검증 결과
3. 미검증 항목과 남은 문제
4. (사용자가 요청해서 프롬프트 기록을 추가했을 때만) 추가한 기록 (예: "home_prompt.md에 P-03 추가")
5. 사람이 사용할 커밋 메시지 제안 (`RULES.md` 6-6 형식: Summary + Description)

커밋·푸시·병합·배포는 실행하지 않고 담당자에게 맡긴다.
