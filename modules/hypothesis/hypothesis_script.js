// 2. 가설 수립
const Hypothesis = {
  STORE_KEY: 'hypothesis',

  // 1. 분석 리포트 탭이 아래 모양으로 'report'를 저장해 준다고 가정합니다.
  // report: {
  //   summary: '문제 요약 텍스트',
  //   problem: {               // 분석에서 찾은 핵심 문제 1개
  //     title, description,
  //     factor: 'internal' | 'external',
  //     target, metric,
  //   }
  // }
  // (report 탭 담당자와 이 모양을 맞춰 주세요. modules/hypothesis/README.md 참고)

  // 리포트 탭이 아직 없을 때 미리 확인해 볼 수 있는 예시 데이터
  SAMPLE_REPORT: {
    summary:
      '10월 매출이 전월 대비 12% 감소했고, 쿠폰을 사용한 고객의 재방문율이 8%p 떨어졌어요.',
    problem: {
      title: '쿠폰 고객 재방문율 하락',
      description: '쿠폰을 사용한 고객의 재방문율이 지난달보다 8%p 하락했다',
      factor: 'internal',
      target: '강남점 20대 여성 고객',
      metric: '재방문율',
    },
  },

  init() {
    // index.html이 탭을 처음 열 때 한 번 호출합니다
    this.reportSummaryEl = document.getElementById('hypothesis-report-summary');
    this.emptyEl = document.getElementById('hypothesis-empty');
    this.sampleBtn = document.getElementById('hypothesis-btn-sample');
    this.problemCardEl = document.getElementById('hypothesis-problem-card');
    this.factorBadgeEl = document.getElementById('hypothesis-factor-badge');
    this.problemTitleEl = document.getElementById('hypothesis-problem-title');
    this.problemDescEl = document.getElementById('hypothesis-problem-desc');
    this.textareaEl = document.getElementById('hypothesis-generated-text');
    this.statusEl = document.getElementById('hypothesis-generated-status');
    this.regenerateBtn = document.getElementById('hypothesis-btn-regenerate');
    this.saveBtn = document.getElementById('hypothesis-btn-save');
    this.savedNoteEl = document.getElementById('hypothesis-saved-note');

    this.problem = null; // 현재 리포트의 문제
    this.draft = null; // { status: 'loading' | 'ready', text, source: 'ai' | 'rule' }
    this.saved = Store.get(this.STORE_KEY) || null; // 저장된 가설 (단 하나만 존재)
    this.requestId = 0; // 응답이 늦게 와도 그 사이 문제가 바뀌었으면 결과를 버리기 위한 토큰

    this.bindEvents();
    this.loadReport();
  },

  bindEvents() {
    this.sampleBtn.addEventListener('click', () => {
      Store.set('report', this.SAMPLE_REPORT);
    });

    this.regenerateBtn.addEventListener('click', () => {
      if (this.problem) this.generate(this.problem, { force: true });
    });

    this.saveBtn.addEventListener('click', () => this.saveHypothesis());

    // 가설 문장을 직접 다듬을 수 있게, 수정 내용은 바로 draft에 반영
    this.textareaEl.addEventListener('input', () => {
      if (!this.draft) return;
      this.draft.text = this.textareaEl.value;
      this.syncSaveButton();
    });

    // 리포트 탭이 분석을 끝내고 저장하면(또는 다시 분석하면) 바로 반영
    Store.onChange('report', () => this.loadReport());
  },

  // 1. 분석 리포트 탭에서 저장한 핵심 문제를 읽어서, 가설 자동 생성을 시작합니다
  loadReport() {
    const report = Store.get('report');
    const problem = report && report.problem ? report.problem : null;

    this.reportSummaryEl.textContent =
      report && report.summary ? report.summary : '분석 리포트 탭에서 먼저 문제를 분석해 주세요.';

    const hasProblem = Boolean(problem && problem.title);
    this.emptyEl.hidden = hasProblem;
    this.problemCardEl.hidden = !hasProblem;

    if (!hasProblem) {
      this.problem = null;
      this.draft = null;
      return;
    }

    const sameAsBefore = Boolean(this.problem) && this.isSameProblem(this.problem, problem);
    this.problem = problem;
    this.renderProblem();

    // 리포트 문제가 그대로면 이미 만든 가설을 유지하고, 문제가 바뀌었을 때만 새로 생성
    if (sameAsBefore && this.draft) {
      this.renderDraft();
    } else {
      this.generate(problem);
    }
  },

  isSameProblem(a, b) {
    return a.title === b.title && a.description === b.description;
  },

  renderProblem() {
    const isExternal = this.problem.factor === 'external';
    this.factorBadgeEl.textContent = isExternal ? '외부 요인 · 경쟁사' : '내부 요인';
    this.factorBadgeEl.className = `hypothesis-factor-badge ${
      isExternal ? 'hypothesis-factor-external' : 'hypothesis-factor-internal'
    }`;
    this.problemTitleEl.textContent = this.problem.title;
    this.problemDescEl.textContent = this.problem.description || '';
  },

  // 리포트 문제 하나로 AI에게 가설 생성을 요청합니다. AI가 준비되지 않았거나 실패하면
  // buildFallbackSentence()로 바로 채워서, 1번 분석 결과와 맞는 가설을 항상 볼 수 있습니다.
  async generate(problem, { force = false } = {}) {
    if (!force && this.draft && this.draft.status === 'ready') return;

    const myRequestId = ++this.requestId;
    this.draft = { status: 'loading', text: '', source: null };
    this.renderDraft();

    let text = '';
    let source = 'rule';
    try {
      const res = await Api.post('/hypothesis/generate', { problem });
      if (res && res.ok && res.text) {
        text = res.text;
        source = 'ai';
      } else {
        text = this.buildFallbackSentence(problem);
      }
    } catch (err) {
      text = this.buildFallbackSentence(problem);
    }

    // 생성되는 동안 리포트의 문제가 바뀌었으면(= 더 최신 요청이 있으면) 이 결과는 버립니다
    if (myRequestId !== this.requestId) return;

    this.draft = { status: 'ready', text, source };
    this.renderDraft();
  },

  // AI 없이도 바로 쓸 수 있게, 1번 분석 결과(문제)로 규칙 기반 가설 문장을 만듭니다.
  // 만약 [타깃/지점]에 [구체적인 액션]을 적용한다면,
  // [이유/고객 심리] 때문에 [측정 가능한 지표/KPI]가 [얼마나] 개선될 것이다
  buildFallbackSentence(problem) {
    const target = problem.target || '전체 고객';
    const kpi = problem.metric || '매출';
    const desc = problem.description || problem.title || '';
    const isExternal = problem.factor === 'external';

    let action = '타깃 맞춤 프로모션을 집중적으로 노출한다';
    let amount = isExternal ? '8%' : '10%';

    if (/리뷰|후기/.test(desc)) {
      action = '경쟁사의 부정 리뷰 내용을 우리 서비스의 강점과 비교하는 홍보 콘텐츠를 노출한다';
      amount = '8%';
    } else if (/재방문|재구매/.test(desc)) {
      action = '재방문 고객 전용 할인 쿠폰을 발송한다';
      amount = '12%';
    } else if (/품절|재고/.test(desc)) {
      action = '품절 임박 상품을 묶음 할인으로 우선 노출한다';
      amount = '10%';
    } else if (/날씨|폭염|한파|우천/.test(desc)) {
      action = '날씨 상황에 맞춰 광고 노출 빈도를 자동으로 늘린다';
      amount = '15%';
    } else if (/신규|유입/.test(desc)) {
      action = '신규 고객 대상 첫 구매 할인 쿠폰을 노출한다';
      amount = '10%';
    }

    const reason = `${desc || '분석 결과'}로 미루어 볼 때 고객이 ${
      isExternal ? '경쟁사 대비 우리 혜택' : '해당 요인'
    }에 민감하게 반응할 가능성이 크기`;

    return `만약 ${target}에 ${action}을 적용한다면, ${reason} 때문에 ${kpi}가 ${amount} 개선될 것이다.`;
  },

  renderDraft() {
    const isLoading = this.draft.status === 'loading';

    this.textareaEl.value = this.draft.text;
    this.textareaEl.disabled = isLoading;
    this.textareaEl.classList.toggle('is-loading', isLoading);

    this.regenerateBtn.disabled = isLoading;

    if (isLoading) {
      this.statusEl.textContent = '가설을 만드는 중...';
    } else if (this.draft.source === 'ai') {
      this.statusEl.textContent = 'AI가 분석 결과를 바탕으로 만든 가설이에요. 필요하면 고쳐서 저장하세요.';
    } else {
      this.statusEl.textContent = '분석 결과를 바탕으로 규칙에 따라 만든 가설이에요. 필요하면 고쳐서 저장하세요.';
    }

    this.syncSaveButton();
  },

  syncSaveButton() {
    const text = this.draft ? this.draft.text.trim() : '';
    const isLoading = Boolean(this.draft) && this.draft.status === 'loading';
    const isSaved = Boolean(this.saved) && Boolean(this.draft) && this.saved.text === this.draft.text && !isLoading;

    this.saveBtn.disabled = isLoading || !text;
    this.saveBtn.textContent = isSaved ? '✓ 저장됨' : '가설 저장';
    this.saveBtn.classList.toggle('is-saved', isSaved);
    this.savedNoteEl.hidden = !isSaved;
  },

  // media, solution 탭이 읽을 수 있게 'hypothesis' 키에 가설 1개만 저장
  saveHypothesis() {
    if (!this.draft || !this.draft.text.trim() || !this.problem) return;

    this.saved = {
      problemTitle: this.problem.title,
      text: this.draft.text.trim(),
      target: this.problem.target || null,
      metric: this.problem.metric || null,
      factor: this.problem.factor || null,
      source: this.draft.source,
      updatedAt: new Date().toISOString(),
    };

    Store.set(this.STORE_KEY, this.saved);
    this.syncSaveButton();
  },
};
