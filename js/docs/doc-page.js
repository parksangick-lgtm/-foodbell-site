// 웹 서류 5종 공통 부품 (2단계) — 로그인 · 목록 · 저장(모아서 올리기) · 다른 기기 고침 반영 · 지우기.
// 화면은 window.FoodbellDoc(연결 고리)만 내주고, 저장소는 ../sije/store.js 로만 부른다.
// 주소에 ?id= 가 없으면 그 종류의 목록, 있으면 그 서류.
import { KINDS, sortDocs, editedText, rowCells } from './doc-model.js';
import { putBundle, takeBundle, quoteToEvent, quoteToStatement, NOTES_KEY as NOTES } from './handoff.js';
import {
  initStore, onUser, signIn, signInForTest, signOutUser, watchDocs, watchDoc, createDoc, saveDoc, removeDoc, atMost, myRole, publishShare,
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
// 일일 일정표 주소를 직원이 열었을 때 — 직원 화면은 단톡방 공지의 '푸드벨 일정' 링크다 (사장님 2026-10-21 밤)
if (D.kind === 'daily-schedule') {
  for (const card of gate.querySelectorAll('[data-show="login"], [data-show="denied"]')) {
    const p = document.createElement('p');
    p.className = 'doc-staff-hint';
    p.textContent = "직원이시면 단톡방 공지의 '푸드벨 일정' 링크를 누르세요";
    card.querySelector('p').after(p);
  }
}
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

// 3단계 서류 잇기 — '이 견적서로 …만들기' 줄 (지우기 위). 누르면 겹치는 칸을 꾸러미로 넘기고 받는 화면을 ?make=1 로 연다.
const MAKES = { 'sije-quote': ['event', 'statement'], 'event-quote': ['statement'] };
const MAKE = {
  event: { label: '내역서 만들기', ask: `이 ${noun} 내용으로 새 내역서를 만들까요?`, url: 'sije-list.html?make=1', build: quoteToEvent },
  statement: { label: '거래명세서 만들기', ask: `이 ${noun} 내용으로 새 거래명세서를 만들까요?`, url: 'statement.html?make=1', build: quoteToStatement },
};
if (MAKES[D.kind]) {
  const row = document.createElement('div');
  row.className = 'doc-make';
  row.innerHTML = `<b>이 ${noun}로</b>`;
  for (const to of MAKES[D.kind]) {
    const b = document.createElement('button');
    b.type = 'button';
    b.id = `doc-make-${to}`;
    b.textContent = MAKE[to].label;
    b.addEventListener('click', async () => {
      if (!confirm(MAKE[to].ask)) return;
      const saving = flush();                               // 고치던 것을 먼저 올린다
      if (saving && navigator.onLine) await atMost(saving);
      putBundle(sessionStorage, to, MAKE[to].build(D.handoff()), Date.now());
      location.href = MAKE[to].url;
    });
    row.append(b);
  }
  delWrap.before(row);
}
// 받는 쪽(거래명세서 목록) — ?make=1 로 열렸고 1분 안의 꾸러미가 있으면 한 번만 쓴다 (읽으면 늘 지움)
const incoming = D.kind === 'statement' && !docId
  ? takeBundle(sessionStorage, 'statement', params.get('make') === '1', Date.now()) : null;

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
// '새 서류' 로 만들고 한 글자도 안 고친 채 떠나면 지운다 — 열었다 닫기만 해도 빈 서류가 목록에 남았다 (사장님 2026-10-26)
const FRESH = 'foodbell-doc-fresh:';   // 이 탭에서 '새 서류' 로 만든 서류 id 표시 (sessionStorage)
const DROP = 'foodbell-doc-drop:';     // 창을 닫아 끝나지 못한 지우기 — 서류 id → 그때 저장소 글자 (localStorage, 다음에 열 때 마저 지움)
let untouched = null;                  // 그런 서류면 처음 그린 직후의 serialize() — 이것과 같으면 안 고친 것
let current = null;     // 마지막으로 받은 서류 (저장 표시용)
let pending = false;
let failed = false;
let role = null;        // 'owner' | 'viewer' | 'none' — viewer(직원 보기 명단)는 읽기만: 편집 · 저장 · 새로 만들기 · 지우기 없음
let who = null;         // 지금 로그인한 메일 — 늦게 온 역할 확인이 다른 사람 것이면 버린다
let lastRows = [];      // 목록에서 받은 서류들 — 새 서류가 가장 최근 것에서 이어받을 때 (일일 일정표의 순번 · 전달 메모)
const viewerOnly = () => role === 'viewer';
// 역할 확인은 저장소 읽기라 신호가 약하면 10초쯤 걸린다 — 이 기기가 지난번에 확인한 것을 먼저 쓴다 (일일 일정표 최종 검토 I3)
const ROLE_KEY = 'foodbell-doc-role:';
const lastRole = (email) => { try { return localStorage.getItem(ROLE_KEY + email); } catch { return null; } };
const keepRole = (email, r) => { try { localStorage.setItem(ROLE_KEY + email, r); } catch { /* 저장 못 해도 이번 화면은 된다 */ } };

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
  // 치는 중에 다른 기기 고침이 왔다 — 이 기기 것이 올라가 남는다는 것을 알린다
  else if (waiting !== null) state.textContent = '다른 기기에서 같은 서류를 고쳤습니다 — 지금 고치는 내용으로 저장합니다';
  else if (pending || timer) state.textContent = '저장 중…';
  else if (current?.updatedAt) state.textContent = `저장됨 · 마지막으로 고친 시각 ${hhmm(current.updatedAt.toDate())}`;
  else state.textContent = '';
}

D.onSave = () => {
  if (drawing || gone || !docId || shownFrom === null || viewerOnly()) return;
  clearTimeout(timer);
  timer = null;
  if (!D.editing()) return flush();   // 편집 완료 · 칸 밖에서 바뀜 — 모으지 않고 바로 (그 사이 다른 기기 고침이 덮지 않게)
  timer = setTimeout(flush, SAVE_WAIT);
  showState();
};

function flush() {
  clearTimeout(timer);
  timer = null;
  if (drawing || gone || !docId || shownFrom === null || viewerOnly()) return;
  const html = D.serialize();
  if (html === lastHtml) {                       // 이 기기에서 바뀐 것 없음
    if (waiting !== null) apply(waiting);
    showState();
    return;
  }
  shownFrom = html;
  lastHtml = html;
  if (untouched !== null) {                      // 고쳤다 — 이제 남길 서류 (새로 고침해도 다시 '안 고친 것' 이 되지 않게 표시도 지운다)
    untouched = null;
    try { sessionStorage.removeItem(FRESH + docId); } catch { /* 못 지워도 이번 화면은 된다 */ }
  }
  waiting = null;                                // 내 것이 나중 — 들고 있던 다른 기기 것은 버린다
  failed = false;
  pending = true;
  showState();
  const saving = saveDoc(docId, html, D.summary()).catch((e) => {
    failed = true;
    showState();
    toast(`저장하지 못했습니다 (${why(e)})`);
  });
  publish(false);
  return saving;
}

// 직원 게시판(today.html) — 화면이 share() 를 내줄 때만(일일 일정표), 주인만. 서류 저장과 따로 돌아 실패해도 저장은 그대로.
// 끊김은 알리지 않는다(연결되면 다음 저장 때 올라간다). 그 밖의 실패는 화면당 한 번만 알린다.
let shareWarned = false;
function publish(removed) {
  if (!D.share || role !== 'owner' || !docId) return;
  publishShare(docId, removed ? null : D.share()).catch((e) => {
    if (e.code === 'unavailable' || shareWarned) return;
    shareWarned = true;
    toast(`직원 링크 화면에 올리지 못했습니다 (${why(e)})`);
  });
}
// 안 고친 새 서류 지우기 — 지우기는 기기 저장소에 먼저 들어가므로 창을 닫아 끊겨도 다음에 열 때 올라간다.
// 앱만 바꾸는 것(visibilitychange)으로는 지우지 않는다 — 카톡을 보고 돌아와 마저 쓸 수 있다.
function dropUntouched() {
  if (untouched === null || gone || !docId || viewerOnly() || D.serialize() !== untouched) return null;
  gone = true;
  deleting = true;
  clearTimeout(timer);
  timer = null;
  try { sessionStorage.removeItem(FRESH + docId); } catch { /* 못 지워도 이번 화면은 된다 */ }
  // 창을 닫으면 지우기가 끝나기 전에 화면이 사라진다(10-26 시험) — 바로 남는 기기 칸에 적어 두고, 끝나면 지운다
  const id = docId;
  try { localStorage.setItem(DROP + id, shownFrom); } catch { /* 못 적으면 이번 지우기만 믿는다 */ }
  publish(true);
  return removeDoc(id).then(() => { try { localStorage.removeItem(DROP + id); } catch { /* 다음에 열 때 정리된다 */ } });
}
// 지난번에 창을 닫아 끝나지 못한 지우기를 마저 한다 (주인만). 서버에서 받은 서류가 그때 글자 그대로일 때만 지운다 —
// 그사이 다른 기기에서 고쳤으면 남긴다. 끊긴 곳에서는 서버 것을 못 받으니 다음 기회로 미룬다.
function sweepDrops() {
  let keys = [];
  try { keys = Object.keys(localStorage).filter((k) => k.startsWith(DROP)); } catch { return; }
  for (const key of keys) {
    const id = key.slice(DROP.length);
    const stop = watchDoc(id, (doc, meta) => {
      if (meta.fromCache) return;
      stop();
      let html = null;
      try { html = localStorage.getItem(key); localStorage.removeItem(key); } catch { return; }
      if (doc && doc.html === html) removeDoc(id).catch(() => {});
    }, () => {});
  }
}
// 화면을 끄거나 앱을 바꾸면 모으던 것을 바로 올린다 (창을 닫을 때 안 고친 새 서류면 지운다)
addEventListener('pagehide', () => { if (!dropUntouched()) flush(); });
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
    try { if (sessionStorage.getItem(FRESH + docId)) untouched = lastHtml; } catch { /* 표시를 못 읽으면 지우지 않는다 */ }
    view('doc');
    publish(false);                               // 열기만 해도 직원 게시판에 올라간다
    const notes = sessionStorage.getItem(NOTES);  // 다른 서류에서 옮겨 만들며 못 읽은 칸이 있었다
    if (notes) {
      sessionStorage.removeItem(NOTES);
      toast(JSON.parse(notes).join(' · '));
    }
  } else if (!meta.pending && doc.html !== shownFrom) {   // 다른 기기에서 고침
    // 이 기기에 아직 안 올린 글자가 없으면 편집 중이어도 바로 보여 준다 (사장님 결정 2026-10-17).
    // 한창 치는 중(모아 올리기 전)이면 치던 글자를 지우지 않게 들고 있다가 — 이 기기 것이 올라가 나중 것으로 남는다
    if (timer === null && D.serialize() === lastHtml) apply(doc.html);
    else waiting = doc.html;
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
  lastRows = rows;
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
  const saving = dropUntouched() ?? flush();   // 안 고친 새 서류면 지우고, 아니면 고친 것을 올린다
  if (saving && navigator.onLine) await atMost(saving);
  location.href = listUrl;
});

// 새 서류 — bundle 이 있으면(3단계) 빈 첫 화면에 받은 칸을 채워서 만든다
async function makeNew(bundle) {
  if (viewerOnly()) return;
  const b = $('doc-new');
  b.disabled = true;
  try {
    draw(() => {
      D.fresh();
      if (D.inherit) D.inherit(sortDocs(lastRows)[0]?.doc ?? null);   // 가장 최근에 고친 같은 종류 서류에서 이어받기
      if (bundle) D.prefill(bundle.fields);
    });
    // 같은 날짜 서류가 이미 있으면 묻는다 — sameDoc 은 일일 일정표만 내준다. 취소하면 있는 것을 연다 (사장님 10-24 저녁)
    const same = !bundle && D.sameDoc ? D.sameDoc(sortDocs(lastRows)) : null;
    if (same && !window.confirm(`${same.label} ${noun}가 이미 있습니다.\n\n[확인] 그래도 새로 만들기\n[취소] 있는 ${noun} 열기`)) {
      location.href = `${listUrl}?id=${encodeURIComponent(same.id)}`;
      return;
    }
    const id = await createDoc(D.kind, D.serialize(), D.summary());
    if (!bundle) {                        // 다른 서류에서 옮겨 만든 것(bundle)은 내용이 있으니 안 고쳐도 남긴다
      try { sessionStorage.setItem(FRESH + id, '1'); } catch { /* 못 적으면 지우지 않을 뿐 */ }
    }
    if (bundle?.notes.length) sessionStorage.setItem(NOTES, JSON.stringify(bundle.notes));
    const url = `${listUrl}?id=${encodeURIComponent(id)}`;
    if (bundle) location.replace(url);   // 뒤로 가면 ?make=1 이 아니라 원래 서류로
    else location.href = url;
  } catch (e) {
    b.disabled = false;
    toast(`새 ${noun}를 만들지 못했습니다 (${why(e)})`);
  }
}
$('doc-new').addEventListener('click', () => makeNew(null));

// 보기 전용이면 편집 버튼이 숨어 있어도 눌리지 않게 (서류 화면의 편집 전환보다 먼저 가로챈다)
document.addEventListener('click', (e) => {
  if (viewerOnly() && e.target.closest?.('#btn-edit')) {
    e.preventDefault();
    e.stopPropagation();
  }
}, true);

$('doc-del').addEventListener('click', async () => {
  if (viewerOnly()) return;
  if (!confirm(`정말 지울까요? 지운 ${noun}는 되살릴 수 없습니다.`)) return;
  gone = true;
  deleting = true;
  clearTimeout(timer);
  timer = null;
  publish(true);
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
onUser(async (user) => {
  stop?.();
  stop = null;
  if (!user) {
    role = who = null;
    delete document.body.dataset.role;
    return view('login');
  }
  $('doc-who').textContent = user.email || '';
  const email = who = (user.email || '').toLowerCase();
  // 3초 안에 확인되면 그것, 아니면 지난번 것(처음이면 'none' — 저장소 규칙이 어차피 막는다). 늦게 확인되면 그때 바꾼다
  const asked = myRole(email).then((r) => {
    keepRole(email, r);
    if (who === email && role !== r) { role = r; document.body.dataset.role = r; }
    return r;
  }, () => null);
  role = (await atMost(asked)) ?? lastRole(email) ?? 'none';
  if (who !== email) return;            // 기다리는 동안 로그아웃 · 다른 사람 로그인
  document.body.dataset.role = role;
  if (role === 'owner') sweepDrops();   // 지난번 창을 닫아 남은 빈 새 서류
  if (docId) {
    stop = watchDoc(docId, onDoc, onError);
  } else if (incoming && !incoming.used) {
    incoming.used = true;                 // 로그인 알림이 두 번 와도 한 장만
    makeNew(incoming);
  } else {
    view('list');
    stop = watchDocs(D.kind, onRows, onError);
  }
});
