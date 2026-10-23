// 탭끼리 데이터 주고받기 (PM)
// 내 모듈 이름의 키에만 저장하고, 다른 키는 읽기만 합니다.
const Store = {
  PREFIX: 'dashboard-',

  set(key, value) {
    try {
      localStorage.setItem(this.PREFIX + key, JSON.stringify(value));
    } catch (err) {
      console.error('[Store] 저장 실패', key, err);
    }
    document.dispatchEvent(new CustomEvent('store-change', { detail: { key, value } }));
  },

  get(key) {
    try {
      const raw = localStorage.getItem(this.PREFIX + key);
      return raw ? JSON.parse(raw) : null;
    } catch (err) {
      return null;
    }
  },

  // 다른 탭이 값을 바꿨을 때 알림 받기
  // 예: Store.onChange('report', (value) => { ... });
  onChange(key, callback) {
    document.addEventListener('store-change', (e) => {
      if (e.detail.key === key) callback(e.detail.value);
    });
  },
};
