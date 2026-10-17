// sw.js 시험 — 실제 sw.js 를 가짜 캐시 · 가짜 인터넷 속에서 돌린다. 실행: node --test "tools/sije_web/js-tests/*.test.mjs"
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const SRC = readFileSync(new URL('../../../sw.js', import.meta.url), 'utf8');
const CACHE = /const CACHE = '([^']+)'/.exec(SRC)[1];
const SITE = 'https://foodbell.kr/';
const strip = (u) => { const x = new URL(u); x.search = ''; return x.href; };

function loadSW(fetchImpl) {
  const store = new Map();          // 캐시 이름 → Map(주소 → 글자)
  const open = (name) => {
    if (!store.has(name)) store.set(name, new Map());
    const m = store.get(name);
    const key = (r) => new URL(typeof r === 'string' ? r : r.url, SITE).href;
    return {
      async put(r, res) { m.set(key(r), await res.text()); },
      async match(r, o = {}) {
        const k = key(r);
        for (const [u, body] of m) if (u === k || (o.ignoreSearch && strip(u) === strip(k))) return new Response(body);
        return undefined;
      },
      async keys() { return [...m.keys()].map((u) => ({ url: u })); },
      async addAll() {},
    };
  };
  const caches = {
    open: async (n) => open(n),
    keys: async () => [...store.keys()],
    delete: async (n) => store.delete(n),
    async match(r, o) {
      for (const n of store.keys()) { const hit = await open(n).match(r, o); if (hit) return hit; }
      return undefined;
    },
  };
  const handlers = {};
  const self = {
    addEventListener: (t, f) => { handlers[t] = f; },
    registration: { scope: SITE }, location: new URL('sw.js', SITE),
    skipWaiting() {}, clients: { claim() {} },
  };
  vm.runInNewContext(SRC, { self, caches, fetch: fetchImpl, URL, Response, Promise, setTimeout, clearTimeout, console });
  return { handlers, store, open };
}

function fire(handlers, req) {
  let p;
  handlers.fetch({ request: { method: 'GET', mode: 'cors', ...req }, respondWith: (x) => { p = x; } });
  return p;
}

const never = () => new Promise(() => {});        // 신호가 약해 답이 안 오는 인터넷
const within = (p, ms) => Promise.race([p, new Promise((_, no) => setTimeout(() => no(new Error(`${ms}ms 안에 안 옴`)), ms))]);

test('신호가 약하면 시제 화면은 몇 초 뒤 저장본으로 열린다', async () => {
  const sw = loadSW(never);
  await sw.open(CACHE).put('./sije-sheet.html', new Response('저장본 내역서'));
  const res = await within(fire(sw.handlers, { url: SITE + 'sije-sheet.html?id=x', mode: 'navigate' }), 5000);
  assert.equal(await res.text(), '저장본 내역서');
});

test('신호가 약하면 시제 화면 모듈도 몇 초 뒤 저장본', async () => {
  const sw = loadSW(never);
  await sw.open(CACHE).put(SITE + 'js/sije/store.js', new Response('// 저장본 모듈'));
  const res = await within(fire(sw.handlers, { url: SITE + 'js/sije/store.js' }), 5000);
  assert.equal(await res.text(), '// 저장본 모듈');
});

test('캐시 번호를 올려도(새 서비스 워커) 시제 화면 사본 · 파이어베이스 파일은 남는다', async () => {
  const sw = loadSW(never);
  const old = sw.open('foodbell-v1');
  for (const u of ['sije-list.html', 'sije-sheet.html', 'js/sije/store.js', 'css/sije-sheet.css?v=1']) {
    await old.put(SITE + u, new Response('옛 ' + u));
  }
  await old.put('https://www.gstatic.com/firebasejs/12.19.0/firebase-app.js', new Response('sdk'));
  await old.put(SITE + 'images/hero.jpg', new Response('사진'));
  let done;
  sw.handlers.activate({ waitUntil: (p) => { done = p; } });
  await done;
  assert.deepEqual([...sw.store.keys()], [CACHE]);
  const now = sw.open(CACHE);
  assert.equal(await (await now.match(SITE + 'sije-sheet.html')).text(), '옛 sije-sheet.html');
  assert.ok(await now.match('https://www.gstatic.com/firebasejs/12.19.0/firebase-app.js'));
  assert.ok(await now.match(SITE + 'js/sije/store.js'));
  assert.equal(await now.match(SITE + 'images/hero.jpg'), undefined, '사이트 사진까지 옮기지는 않는다');
});

test('신호가 약하면 서류 화면(2단계)도 몇 초 뒤 저장본으로 열린다', async () => {
  const sw = loadSW(never);
  await sw.open(CACHE).put('./statement.html', new Response('저장본 거래명세서'));
  const res = await within(fire(sw.handlers, { url: SITE + 'statement.html?id=x', mode: 'navigate' }), 5000);
  assert.equal(await res.text(), '저장본 거래명세서');
});

test('인터넷이 되면 서류 공통 부품은 늘 최신 (저장본 먼저가 아님)', async () => {
  const sw = loadSW(async () => new Response('// 최신 부품', { status: 200 }));
  await sw.open(CACHE).put(SITE + 'js/docs/doc-page.js', new Response('// 옛 부품'));
  const res = await within(fire(sw.handlers, { url: SITE + 'js/docs/doc-page.js' }), 5000);
  assert.equal(await res.text(), '// 최신 부품');
});

test('캐시 번호를 올려도 서류 화면 · js/docs · docs.css 사본은 남는다', async () => {
  const sw = loadSW(never);
  const old = sw.open('foodbell-v1');
  for (const u of ['sije-quote.html', 'staff-pay.html', 'js/docs/doc-page.js', 'css/docs.css?v=1']) {
    await old.put(SITE + u, new Response('옛 ' + u));
  }
  let done;
  sw.handlers.activate({ waitUntil: (p) => { done = p; } });
  await done;
  const now = sw.open(CACHE);
  for (const u of ['sije-quote.html', 'staff-pay.html', 'js/docs/doc-page.js', 'css/docs.css?v=1']) {
    assert.ok(await now.match(SITE + u), u);
  }
});

test('인터넷이 되면 시제 화면은 늘 최신', async () => {
  const sw = loadSW(async () => new Response('최신 목록', { status: 200 }));
  await sw.open(CACHE).put('./sije-list.html', new Response('옛 목록'));
  const res = await within(fire(sw.handlers, { url: SITE + 'sije-list.html', mode: 'navigate' }), 5000);
  assert.equal(await res.text(), '최신 목록');
});
