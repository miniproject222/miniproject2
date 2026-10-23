# 2. 가설 수립 (`hypothesis`)

문제 해결 가설 제안 (현지 특성 반영). 사용자가 직접 입력하지 않고, **분석 리포트(`report`)의 핵심 문제 1개를 읽어 가설 1개를 자동으로 생성**합니다. (가설을 여러 개 만들지 않는 이유: 1번 분석 결과와 가설이 1:1로 연결돼야 다음 탭(매체 제작 등)까지 흐름이 어긋나지 않기 때문)

| 파일 | 내용 |
|---|---|
| `hypothesis_main.html` | 화면 (`<section id="hypothesis-section">` 하나) |
| `hypothesis_style.css` | 디자인 (class는 `hypothesis-`로 시작) |
| `hypothesis_script.js` | 화면 기능 (`Hypothesis` 객체, `Hypothesis.init()`) |
| `hypothesis_server.py` | 서버 기능 (주소는 `/hypothesis/...`) |
| `images/` | hypothesis에서만 쓰는 이미지 |
| `data/` | hypothesis에서만 쓰는 데이터 |

## `report` → `hypothesis` 데이터 모양 (report 탭 담당자 확인 필요)

`report` 탭이 아래 모양으로 `Store.set('report', ...)` 해 주셔야 이 탭에서 가설을 자동 생성합니다. `problem`은 **배열이 아니라 객체 1개**입니다 (리포트에서 찾은 문제가 여러 개여도, 여기서는 가장 핵심이 되는 문제 1개만 전달해 주세요).

```js
Store.set('report', {
  summary: '10월 매출이 전월 대비 12% 감소...',   // 리포트 요약 한 줄
  problem: {                  // 핵심 문제 1개 (객체, 배열 아님)
    title: '쿠폰 고객 재방문율 하락',
    description: '쿠폰을 사용한 고객의 재방문율이 지난달보다 8%p 하락했다',
    factor: 'internal',       // 'internal' | 'external' (경쟁사 등 외부 요인이면 'external')
    target: '강남점 20대 여성 고객',   // 선택
    metric: '재방문율',               // 선택, 없으면 '매출'로 대체됨
  },
});
```

이 모양이 아직 안 정해졌다면, 2번 탭의 "예시 데이터로 먼저 테스트하기" 버튼으로 먼저 동작을 확인할 수 있습니다 (`hypothesis_script.js`의 `Hypothesis.SAMPLE_REPORT`).

## 가설 자동 생성 방식

1. `report.problem`을 읽어 카드 1개를 만들고, `POST /hypothesis/generate`로 AI에게 가설 문장을 요청합니다.
2. AI(`server/shared/shared_ai.py`)가 아직 연결되지 않았거나 요청이 실패하면, `Hypothesis.buildFallbackSentence()`가 규칙 기반으로 바로 채워 줍니다. 그래서 AI 연동 전에도 화면은 항상 동작하고, 1번 분석 결과와 맞는 가설이 나옵니다.
3. 생성된 문장은 바로 수정할 수 있고, "가설 저장"을 누르면 `Store.set('hypothesis', { text, problemTitle, target, metric, factor, source, updatedAt })`로 **객체 1개만** 저장되어 media, solution 탭이 읽을 수 있습니다. (예전에는 배열로 여러 개 저장했지만, 가설을 1개만 쓰기로 하면서 배열이 아닌 객체로 바뀌었습니다 — media, solution 탭 담당자에게 공유해 주세요.)
4. 리포트의 문제(`report.problem`)가 바뀌면 자동으로 새 가설을 다시 만듭니다. 같은 문제가 유지되는 동안에는 이미 만든 가설을 그대로 보여줍니다.
