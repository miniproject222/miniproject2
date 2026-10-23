// 서버 호출 함수 (PM)
// 예: const result = await Api.post('/report/analyze', { month: '2026-10' });
const Api = {
  // uvicorn(8000)에서 열면 같은 주소, Live Server 등으로 열면 8000번 서버로 요청
  BASE_URL: location.port === '8000' ? '' : 'http://localhost:8000',

  async request(method, path, body) {
    const options = { method, headers: {} };
    if (body !== undefined) {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(body);
    }
    const res = await fetch(this.BASE_URL + path, options);
    if (!res.ok) {
      throw new Error(`[Api] ${method} ${path} 실패 (${res.status})`);
    }
    return res.json();
  },

  get(path) {
    return this.request('GET', path);
  },

  post(path, body = {}) {
    return this.request('POST', path, body);
  },
};
