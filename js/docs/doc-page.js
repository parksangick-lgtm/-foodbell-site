// 웹 서류 5종 공통 부품 (2단계) — 로그인 · 목록 · 저장(모아서 올리기) · 다른 기기 고침 반영 · 지우기.
// 화면은 window.FoodbellDoc(연결 고리)만 내주고, 저장소는 ../sije/store.js 로만 부른다.
// 주소에 ?id= 가 없으면 그 종류의 목록, 있으면 그 서류.
import { KINDS, sortDocs, editedText, rowCells } from './doc-model.js';
import {
  initStore, onUser, signIn, signInForTest, signOutUser, watchDocs, watchDoc, createDoc, saveDoc, removeDoc, atMost,
} from '../sije/store.js';

const D = window.FoodbellDoc;
const { title, noun } = KINDS[D.kind];
const params = new URLSearchParams(location.search);
const docId = params.get('id');
const listUrl = location.pathname;
const $ = (id) => document.getElementById(id);
const SAVE_WAIT = 800;   // 글자를 칠 때마다 올리지 않고 이만큼(ms) 모아서 한 번에

// ---------- 화면에 끼워 넣기 ----------
const gate = document.createElement('div');
gate.className = 'doc-gate';
gate.innerHTML = `
  <p class="doc-wait" data-show="loading">불러오는 중…</p>
  <section class="doc-card" data-show="login">
    <p>허락된 구글 계정으로 로그인하세요.</p>
    <button type="button" id="doc-sign-in" class="doc-primary">구글로 로그인</button>
  </section>
  <section class="doc-card" data-show="denied">
    <p><b>권한이 없습니다</b> — 사장님께 문의하세요.</p>
    <button type="button" id="doc-sign-out">다른 계정으로 로그인</button>
  </section>
  <section id="doc-list" data-show="list">
    <header class="doc-head"><h1></h1><p class="doc-who" id="doc-who"></p></header>
    <div class="doc-bar"><button type="button" id="doc-new" class="doc-primary"></button></div>
    <div id="doc-rows"></div>
    <p class="doc-empty" id="doc-empty" hidden>아직 서류가 없습니다</p>
  </section>
  <section class="doc-card" id="doc-missing" data-show="missing">
    <p>서류를 찾을 수 없습니다</p>
    <button type="button" id="doc-back">목록</button>
  </section>
  <p class="doc-net" id="doc-net" role="status" hidden>연결 안 됨 — 연결되면 올라갑니다</p>`;
document.body.prepend(gate);
gate.querySelector('h1').textContent = `${title} 목록`;
$('doc-new').textContent = `새 ${noun}`;

const state = document.createElement('p');
state.id = 'doc-state';
state.className = 'doc-state';
state.setAttribute('role', 'status');
document.querySelector('.toolbar').after(state);

const delWrap = document.createElement('p');
delWrap.className = 'doc-del-wrap';
delWrap.innerHTML = '<button type="button" id="doc-del"></button>';
document.querySelector('.sheet').after(delWrap);
$('doc-del').textContent = `이 ${noun} 지우기`;

const toastEl = document.createElement('div');
toastEl.className = 'doc-toast';
toastEl.setAttribute('role', 'status');
toastEl.hidden = true;
document.body.append(toastEl);

function view(name) { document.body.dataset.docView = name; }
function toast(msg) {
  toastEl.textContent = msg;
  toastEl.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { toastEl.hidden = true; }, 4000);
}
const why = (e) => e.code || e.message;

// ---------- 연결 상태 (1단계 목록 화면과 같은 방식) ----------
// 끊긴 채 연 화면은 navigator.onLine 이 '연결됨'으로 나오기도 해서, 저장소가 기기 저장본만 보여 주는 상태가 2초 넘어도 '연결 안 됨'.
let cacheOnlySince = null;
const offline = () => !navigator.onLine || (cacheOnlySince !== null && Date.now() - cacheOnlySince > 2000);
function trackCache(fromCache) {
  cacheOnlySince = fromCache ? (cacheOnlySince ?? Date.now()) : null;
  refreshNet();
  if (fromCache) setTimeout(refreshNet, 2100);
}
function refreshNet() {
  $('doc-net').hidden = !offline();
  showState();
}
addEventListener('online', refreshNet);
addEventListener('offline', refreshNet);

// ---------- 서류 한 장 ----------
let shownFrom = null;   // 지금 화면이 바탕으로 삼은 저장소 글자 (그렸거나 올린 것)
let lastHtml = null;    // 그린 직후 · 올린 직후의 serialize() — 이것과 다르면 이 기기에서 고친 것
let waiting = null;     // 편집 중에 들어온 다른 기기 고침 (편집을 끝낼 때까지 들고 있음)
let drawing = false;    // 그리는 동안 화면이 부르는 save 는 무시 (그리기 → 합계 계산 → save 되돌이 막기)
let gone = false;       // 서류가 지워짐 — 더는 올리지 않는다
let deleting = false;   // 이 기기에서 지우는 중 — '찾을 수 없음' 을 띄우지 않고 목록으로 간다
let timer = null;
let current = null;     // 마지막으로 받은 서류 (저장 표시용)
let pending = false;
let failed = false;

function draw(fn) {
  drawing = true;
  try { fn(); } finally { drawing = false; }
}

function apply(html) {
  draw(() => D.load(html));
  shownFrom = html;
  lastHtml = D.serialize();
  waiting = null;
}

const hhmm = (d) => `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
function showState() {
  if (!docId) return;
  if (failed) state.textContent = '저장하지 못했습니다';
  else if (offline()) state.textContent = '연결 안 됨 — 연결되면 올라갑니다';
  // 편집을 켜 둔 채 다른 기기 고침이 왔다 — 모르고 글자를 치면 그것을 덮어쓰므로 알린다
  else if (waiting !== null) state.textContent = '다른 기기에서 고친 내용이 있습니다 — 편집 완료를 누르면 보입니다';
  else if (pending || timer) state.textContent = '저장 중…';
  else if (current?.updatedAt) state.textContent = `저장됨 · 마지막으로 고친 시각 ${hhmm(current.updatedAt.toDate())}`;
  else state.textContent = '';
}

D.onSave = () => {
  if (drawing || gone || !docId || shownFrom === null) return;
  clearTimeout(timer);
  timer = null;
  if (!D.editing()) return flush();   // 편집 완료 · 칸 밖에서 바뀜 — 모으지 않고 바로 (그 사이 다른 기기 고침이 덮지 않게)
  timer = setTimeout(flush, SAVE_WAIT);
  showState();
};

function flush() {
  clearTimeout(timer);
  timer = null;
  if (drawing || gone || !docId || shownFrom === null) return;
  const html = D.serialize();
  if (html === lastHtml) {                       // 이 기기에서 바뀐 것 없음
    if (waiting !== null && !D.editing()) apply(waiting);
    showState();
    return;
  }
  shownFrom = html;
  lastHtml = html;
  waiting = null;                                // 내 것이 나중 — 들고 있던 다른 기기 것은 버린다
  failed = false;
  pending = true;
  showState();
  return saveDoc(docId, html, D.summary()).catch((e) => {
    failed = true;
    showState();
    toast(`저장하지 못했습니다 (${why(e)})`);
  });
}
// 화면을 끄거나 앱을 바꾸면 모으던 것을 바로 올린다
addEventListener('pagehide', flush);
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') flush(); });

function onDoc(doc, meta) {
  if (!doc && deleting) return;   // 이 기기에서 지운 것 — 목록으로 가는 중
  if (!doc) {
    gone = true;
    clearTimeout(timer);
    timer = null;
    return view('missing');
  }
  gone = false;
  current = doc;
  pending = meta.pending;
  trackCache(meta.fromCache);
  if (shownFrom === null) {                       // 처음 (방금 이 기기에서 만들어 아직 안 올라간 것도)
    apply(doc.html);
    view('doc');
  } else if (!meta.pending && doc.html !== shownFrom) {   // 다른 기기에서 고침
    if (D.editing()) waiting = doc.html;
    else apply(doc.html);
  }
  showState();
}

// ---------- 목록 ----------
function rowEl({ id, doc }) {
  const a = document.createElement('a');
  a.className = 'doc-row';
  a.href = `${listUrl}?id=${encodeURIComponent(id)}`;
  a.dataset.id = id;
  const cells = [...rowCells(D.kind, doc), editedText(doc.updatedAt ? doc.updatedAt.toDate() : null, new Date())];
  ['d-name', 'd-issue', 'd-total', 'd-time'].forEach((cls, i) => {
    const s = document.createElement('span');
    s.className = cls;
    s.textContent = cells[i];
    a.append(s);
  });
  return a;
}

function onRows(rows, meta) {
  $('doc-rows').replaceChildren(...sortDocs(rows).map(rowEl));
  $('doc-empty').hidden = rows.length > 0;
  trackCache(meta.fromCache);
}

// ---------- 버튼 ----------
$('doc-sign-in').addEventListener('click', () => signIn().catch((e) => toast(`로그인하지 못했습니다 (${why(e)})`)));
$('doc-sign-out').addEventListener('click', () => signOutUser());
$('doc-back').addEventListener('click', () => { location.href = listUrl; });
// 목록으로 넘어가기 전에 고친 것을 올린다 — 페이지가 넘어가면 보내던 것이 끊긴다 (끊긴 곳에서는 3초까지만 기다림)
document.getElementById('btn-list')?.addEventListener('click', async () => {
  const saving = flush();
  if (saving && navigator.onLine) await atMost(saving);
  location.href = listUrl;
});

$('doc-new').addEventListener('click', async () => {
  const b = $('doc-new');
  b.disabled = true;
  try {
    draw(() => D.fresh());
    const id = await createDoc(D.kind, D.serialize(), D.summary());
    location.href = `${listUrl}?id=${encodeURIComponent(id)}`;
  } catch (e) {
    b.disabled = false;
    toast(`새 ${noun}를 만들지 못했습니다 (${why(e)})`);
  }
});

$('doc-del').addEventListener('click', async () => {
  if (!confirm(`정말 지울까요? 지운 ${noun}는 되살릴 수 없습니다.`)) return;
  gone = true;
  deleting = true;
  clearTimeout(timer);
  timer = null;
  const removing = removeDoc(docId);
  try {
    if (navigator.onLine) await atMost(removing);   // 끊긴 곳에서는 3초까지만 — 연결되면 지워진다
    location.href = listUrl;
  } catch (e) {
    gone = false;
    deleting = false;
    view('doc');
    toast(`지우지 못했습니다 (${why(e)})`);
  }
});

// ---------- 시작 ----------
view('loading');
await initStore();
const testToken = params.get('testToken');
if (testToken) await signInForTest(testToken).catch((e) => toast(`시험 로그인 실패 (${why(e)})`));

let stop = null;
const onError = (e) => {
  if (e.code === 'permission-denied') view('denied');
  else toast(`불러오지 못했습니다 (${why(e)})`);
};
onUser((user) => {
  stop?.();
  stop = null;
  if (!user) return view('login');
  $('doc-who').textContent = user.email || '';
  if (docId) {
    stop = watchDoc(docId, onDoc, onError);
  } else {
    view('list');
    stop = watchDocs(D.kind, onRows, onError);
  }
});
