/* 푸드벨 서비스 워커 — 오프라인 기본 지원 + 홈 화면 앱 실행
   내용을 크게 바꿨을 때는 아래 CACHE 버전 숫자를 올리세요. */
const CACHE = 'foodbell-v1';

/* 처음 설치할 때 미리 받아두는 최소한의 파일 (앱 껍데기) */
const PRECACHE = [
  '/',
  '/index.html',
  '/manifest.webmanifest',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  /* 페이지 이동: 온라인이면 최신을 보여주고 오프라인용 사본도 갱신,
     오프라인이면 저장해 둔 첫 화면 */
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((cache) => cache.put('/index.html', copy));
          return res;
        })
        .catch(() => caches.match('/index.html', { ignoreSearch: true }))
    );
    return;
  }

  /* 다른 사이트(폰트 CDN 등)는 그냥 통과 */
  if (url.origin !== self.location.origin) return;

  /* 같은 사이트의 CSS·JS·이미지: 저장된 것 먼저 보여주고 뒤에서 갱신 */
  event.respondWith(
    caches.match(req).then((cached) => {
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
    })
  );
});
