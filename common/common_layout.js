// 사이드바 메뉴, 탭 전환 (PM)
const Layout = {
  // 탭 목록: 순서대로 사이드바에 표시됩니다
  TABS: [
    { code: 'home', label: '홈', module: () => Home },
    { code: 'report', label: '1. 분석 리포트', module: () => Report },
    { code: 'hypothesis', label: '2. 가설 수립', module: () => Hypothesis },
    { code: 'media', label: '3. 매체 제작', module: () => Media },
    { code: 'solution', label: '3-1. 솔루션 제안', module: () => Solution },
    { code: 'weather', label: '4. 날씨 광고 타이밍', module: () => Weather },
  ],

  loaded: {},

  async init() {
    this.renderMenu();
    await this.loadAll();
    this.show(location.hash.slice(1) || 'home');
    window.addEventListener('hashchange', () => this.show(location.hash.slice(1)));
  },

  renderMenu() {
    const menu = document.getElementById('common-menu');
    menu.innerHTML = this.TABS.map(
      (tab) => `<li><button class="common-menu-item" data-tab="${tab.code}">${tab.label}</button></li>`
    ).join('');
    menu.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-tab]');
      if (btn) location.hash = btn.dataset.tab;
    });
  },

  // 각 모듈의 모듈코드_main.html을 해당 탭 칸에 넣습니다
  async loadAll() {
    await Promise.all(
      this.TABS.map(async (tab) => {
        const box = document.getElementById(`common-tab-${tab.code}`);
        try {
          const res = await fetch(`modules/${tab.code}/${tab.code}_main.html`);
          box.innerHTML = await res.text();
        } catch (err) {
          box.innerHTML = `<p>${tab.label} 화면을 불러오지 못했습니다.</p>`;
          console.error(`[Layout] ${tab.code} 로드 실패`, err);
        }
      })
    );
  },

  show(code) {
    const tab = this.TABS.find((t) => t.code === code) || this.TABS[0];
    document.querySelectorAll('.common-tab').forEach((el) => {
      el.classList.toggle('is-active', el.id === `common-tab-${tab.code}`);
    });
    document.querySelectorAll('.common-menu-item').forEach((el) => {
      el.classList.toggle('is-active', el.dataset.tab === tab.code);
    });

    // 탭을 처음 열 때 한 번만 init() 호출
    if (!this.loaded[tab.code]) {
      this.loaded[tab.code] = true;
      try {
        tab.module().init();
      } catch (err) {
        console.error(`[Layout] ${tab.code} init 실패`, err);
      }
    }
  },
};

document.addEventListener('DOMContentLoaded', () => Layout.init());
