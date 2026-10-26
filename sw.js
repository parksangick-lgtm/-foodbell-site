/* 푸드벨 서비스 워커 — 오프라인 기본 지원 + 홈 화면 앱 실행
   내용을 크게 바꿨을 때는 아래 CACHE 버전 숫자를 올리세요. */
const CACHE = 'foodbell-v38';

/* 처음 설치할 때 미리 받아두는 최소한의 파일 (앱 껍데기) */
const PRECACHE = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icons/icon-192.png',
  './icons/icon-512.png',
];

/* 인터넷이 없어도 열려야 하는 화면 (페이지마다 자기 사본) — 시제행사 화면 + 2단계 서류 5종 + 일일 일정표 + 직원 화면(today.html) + 담당자 내역서(sije-view.html) */
const OFFLINE_PAGES = ['sije-list.html', 'sije-sheet.html',
  'sije-quote.html', 'event-quote.html', 'sije-worksheet.html', 'statement.html', 'staff-pay.html', 'daily-schedule.html', 'today.html', 'sije-view.html'];
/* 그 화면들이 부르는 모듈 · 스타일 — 인터넷 먼저(모듈끼리 부르는 주소에 ?v= 가 없어서), 끊기면 저장본 */
const isOfflineAsset = (rel) => rel.startsWith('js/sije/') || rel.startsWith('js/docs/')
  || rel === 'css/sije-sheet.css' || rel === 'css/docs.css';
/* 신호가 약한 산속: 이만큼(ms) 기다려도 답이 없으면 저장본을 보여 준다 */
const SLOW_MS = 3000;

/* 시제행사 화면이 인터넷 없이 열리는 데 필요한 것 — 캐시 이름을 올려도 옛 캐시에서 새 캐시로 옮겨 둔다 */
function keepOffline(u) {
  const url = new URL(u);
  if (url.origin === 'https://www.gstatic.com') return url.pathname.startsWith('/firebasejs/');
  if (url.origin !== self.location.origin) return false;
  const rel = url.pathname.slice(new URL('./', self.registration.scope).pathname.length);
  return OFFLINE_PAGES.includes(rel) || isOfflineAsset(rel);
}

/* 인터넷 먼저 — 그런데 SLOW_MS 안에 답이 없거나 끊기면 저장본. 늦게 온 답은 사본만 새로 바꾼다 */
function networkFirst(req, key, fallback) {
  const net = fetch(req).then((res) => {
    if (res && res.status === 200) {
      const copy = res.clone();
      caches.open(CACHE).then((cache) => cache.put(key, copy));
    }
    return res;
  });
  return new Promise((resolve, reject) => {
    let settled = false;
    const finish = (res) => { if (res && !settled) { settled = true; resolve(res); } return res; };
    const timer = setTimeout(() => fallback().then(finish), SLOW_MS);   // 저장본이 없으면 계속 기다린다
    net.then((res) => { clearTimeout(timer); finish(res); }, () => {
      clearTimeout(timer);
      fallback().then((hit) => { if (!finish(hit) && !settled) reject(new Error('연결 안 됨')); });
    });
  });
}

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const now = await caches.open(CACHE);
    for (const k of (await caches.keys()).filter((name) => name !== CACHE)) {
      const old = await caches.open(k);
      for (const req of await old.keys()) {   // 시제행사 오프라인 사본은 새 캐시로 옮긴 뒤 옛 캐시를 지운다
        if (keepOffline(req.url) && !(await now.match(req))) await now.put(req, await old.match(req));
      }
      await caches.delete(k);
    }
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  /* 페이지 이동: 온라인이면 최신을 보여주고 오프라인용 사본도 갱신,
     오프라인이면 저장해 둔 첫 화면.
     사본은 첫 화면을 열었을 때만 갱신한다 — 전에는 처리방침·견적서를 열어도 그 페이지가
     "첫 화면" 사본 자리에 저장돼, 인터넷이 끊기면 엉뚱한 페이지가 나왔다(2026-10-08). */
  if (req.mode === 'navigate') {
    const home = new URL('./', self.registration.scope).pathname;
    const isHome = url.pathname === home || url.pathname === home + 'index.html';
    /* 시제행사 목록 · 내역서는 산속(인터넷 없음)에서도 떠야 해서 그 페이지 자기 자리에 사본을 둔다
       (첫 화면 사본 자리는 건드리지 않는다 — 위 2026-10-08 주석) */
    const page = url.pathname.slice(home.length);
    const own = OFFLINE_PAGES.includes(page) ? './' + page : null;
    if (own) {
      event.respondWith(networkFirst(req, own, () => caches.match(own, { ignoreSearch: true })
        .then((hit) => hit || caches.match('./index.html', { ignoreSearch: true }))));
      return;
    }
    event.respondWith(
      fetch(req)
        .then((res) => {
          if ((isHome || own) && res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((cache) => cache.put(own || './index.html', copy));
          }
          return res;
        })
        .catch(() => (own ? caches.match(own, { ignoreSearch: true }) : Promise.resolve(null))
          .then((hit) => hit || caches.match('./index.html', { ignoreSearch: true })))
    );
    return;
  }

  /* 파이어베이스 프로그램 파일(판이 주소에 박혀 있어 안 바뀐다): 저장된 것 먼저, 뒤에서 갱신 */
  if (url.origin === 'https://www.gstatic.com' && url.pathname.startsWith('/firebasejs/')) {
    event.respondWith(cacheFirst(req));
    return;
  }

  /* 다른 사이트(폰트 CDN 등)는 그냥 통과 */
  if (url.origin !== self.location.origin) return;

  /* 시제행사 화면 · 서류 5종의 스크립트·스타일: 인터넷이 되면 늘 최신, 끊기면 저장본.
     모듈끼리 부르는 주소에는 ?v= 가 없어서, 저장본 먼저로 두면 고친 뒤 한 번은 옛 모듈이 섞인다 */
  const rel = url.pathname.slice(new URL('./', self.registration.scope).pathname.length);
  if (isOfflineAsset(rel)) {
    event.respondWith(networkFirst(req, req, () => caches.match(req)));
    return;
  }

  /* 버셀 측정 파일은 저장하지 않는다 — 옛 사본이 남으면 측정이 어긋난다 */
  if (url.pathname.startsWith('/_vercel/')) return;

  /* 영상은 저장하지 않고 그대로 통과 — 브라우저는 영상을 조각(Range)으로 나눠 받는데,
     통째로 저장된 사본을 돌려주면 아이폰 사파리가 재생을 못 한다 */
  if (url.pathname.endsWith('.mp4')) return;

  /* 같은 사이트의 CSS·JS·이미지: 저장된 것 먼저 보여주고 뒤에서 갱신 */
  event.respondWith(cacheFirst(req));
});

function cacheFirst(req) {
  return caches.match(req).then((cached) => {
    const network = fetch(req)
      .then((res) => {
        if (res && res.status === 200) {
          const copy = res.clone();
          caches.open(CACHE).then((cache) => cache.put(req, copy));
        }
        return res;
      })
      .catch(() => cached);
    return cached || network;
  });
}
