// 시제행사 내역서 화면 (sije-sheet.html?id=…) — PC 편집 · 휴대폰 빠른 고치기 · 인쇄 · 그림 붙이기
// 저장 버튼 없음: 칸을 떠나면 그 칸만 저장된다. 인터넷이 끊겨도 기기에 들고 있다가 연결되면 올라간다.
import { itemsBySide, newViewKey, viewLinkText } from './model.js';
import { NOTES_KEY, putBundle, eventToStatement, eventToQuote } from '../docs/handoff.js?v=2';   // 새 export — 옛 사본이 오면 화면이 멈춘다 (기록장 #78)
import { renderSheet, fitToA4 } from './sheet-render.js';
import {
  initStore, onUser, signIn, signInForTest, watchEvent, updateField, ensureViewKey, addImage, watchImages, atMost,
} from './store.js';

const $ = (id) => document.getElementById(id);
const id = new URLSearchParams(location.search).get('id');
const sheet = $('sheet');
const LIMIT = 900_000;   // 그림 한 장 바이트 상한 (저장소 문서 하나에 한 장)
let ev = null;
let images = [];
let pending = false;
let deferred = false;
let stops = [];

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}

function toast(msg) {
  const t = $('toast');
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { t.hidden = true; }, 4000);
}

function show(which) {
  for (const s of ['loading', 'login', 'message', 'doc']) $(s).hidden = s !== which;
}

// 끊김 = navigator.onLine 이 끊김이라고 하거나, 저장소가 기기 저장본만 보여 주는 상태가 2초 넘게 이어질 때
// (신호가 약한 산속이나 끊긴 채 연 화면은 navigator.onLine 이 '연결됨'으로 나오기도 한다)
let cacheOnlySince = null;
function saveState() {
  const off = !navigator.onLine || (cacheOnlySince && Date.now() - cacheOnlySince > 2000);
  $('save-state').textContent = off ? '연결 안 됨 — 연결되면 올라갑니다' : pending ? '저장 중…' : '저장됨';
  $('save-state').classList.toggle('off', Boolean(off));
}
function trackCache(fromCache) {
  cacheOnlySince = fromCache ? (cacheOnlySince ?? Date.now()) : null;
  saveState();
  if (fromCache) setTimeout(saveState, 2100);
}

let saving = null;   // 마지막으로 보낸 저장 — '거래명세서 만들기' 가 다른 화면으로 넘어가기 전에 기다린다
function save(path, value) {
  const m = /^contacts\.(\d+)$/.exec(path);
  if (m) {   // 연락처는 목록 통째로 (저장소는 목록의 한 칸만 고칠 수 없다)
    const list = [...(ev.contacts || [])];
    list[Number(m[1])] = value;
    path = 'contacts';
    value = list;
  }
  // 화면이 들고 있는 행사 값도 바로 고친다 — 저장소 알림은 따로 늦게 와서, 고치자마자 '거래명세서 만들기' 를 누르면 옛 값이 넘어갔다 (3단계 검토 I2)
  if (!path.includes('.')) ev = { ...ev, [path]: value };
  saving = updateField(id, path, value);
  saving.catch((e) => toast(`저장하지 못했습니다 (${e.code || e.message})`));
}

// 인쇄 배율은 미리 재 두고, 화면은 원래 크기로 둔다 (인쇄 때만 @media print 가 이 배율을 쓴다)
function measurePrint() {
  const z = fitToA4(sheet);
  sheet.style.zoom = '';
  sheet.style.setProperty('--print-zoom', String(z));
  $('overflow-note').hidden = !sheet.dataset.overflow;   // 가장 작게 줄여도 넘치면 바로 알린다 (PDF 도 안 만들어진다)
}

// 내역서 칸을 고치는 중인가 (빠른 고치기 칸은 paintQuick 이 그 칸만 건너뛰므로 여기서 막지 않는다)
function editing() {
  const a = document.activeElement;
  return a && a.dataset?.path && sheet.contains(a);
}

async function paint() {
  if (!ev) return;
  if (editing()) { deferred = true; return; }   // 고치는 중인 칸을 지우지 않게, 칸을 떠난 뒤에 다시 그린다
  renderSheet(sheet, ev, images, { editable: true, onEdit: save });
  paintQuick();
  for (const b of document.querySelectorAll('[data-set-status]')) {
    b.setAttribute('aria-pressed', String(b.dataset.setStatus === ev.status));
  }
  await Promise.all([...sheet.querySelectorAll('img')].map((img) => img.decode().catch(() => {})));
  measurePrint();
}

function quickInput(path, value, label, type = 'text') {
  const wrap = el('label', 'q-field');
  wrap.append(el('span', 'q-label', label));
  const input = wrap.appendChild(el('input', 'q-input'));
  input.type = type;
  input.value = value ?? '';
  input.dataset.path = path;
  input.addEventListener('change', () => save(path, input.value));
  return wrap;
}

// 휴대폰 맨 위 빠른 고치기: 날짜 · 시간, 품목별 수량 (PC 에서는 날짜 · 시간만 보인다)
function paintQuick() {
  const items = ev.items || {};
  const sig = Object.keys(items).sort().join(',');
  const q = $('quick');
  if (q.dataset.sig !== sig) {
    q.dataset.sig = sig;
    const when = el('div', 'q-when');
    when.append(quickInput('date', ev.date, '날짜', 'date'), quickInput('time', ev.time, '시간'));
    const list = el('div', 'q-items');
    const { L, R } = itemsBySide(items);
    const keys = Object.keys(items).sort();
    [...L, ...R].forEach((it, i) => list.append(quickInput(`items.${keys[i]}.qty`, it.qty, it.name || it.group)));
    q.replaceChildren(when, el('p', 'q-head', '품목 수량'), list);
  }
  for (const input of q.querySelectorAll('input[data-path]')) {   // 고치는 중이 아닌 칸만 새 값으로
    if (input === document.activeElement) continue;
    const p = input.dataset.path.split('.');
    const v = p[0] === 'items' ? items[p[1]]?.[p[2]] : ev[p[0]];
    if (input.value !== (v ?? '')) input.value = v ?? '';
  }
}

async function shrink(file) {
  const bmp = await createImageBitmap(file);
  const k = Math.min(1, 1600 / Math.max(bmp.width, bmp.height));
  const canvas = Object.assign(document.createElement('canvas'),
    { width: Math.round(bmp.width * k), height: Math.round(bmp.height * k) });
  canvas.getContext('2d').drawImage(bmp, 0, 0, canvas.width, canvas.height);
  for (let q = 0.85; q > 0.04; q -= 0.1) {
    const blob = await new Promise((ok) => canvas.toBlob(ok, 'image/jpeg', q));
    if (blob.size <= LIMIT) return blob;
  }
  throw new Error('그림이 너무 큽니다');
}

document.addEventListener('focusout', () => setTimeout(() => {
  if (deferred && !editing()) { deferred = false; paint(); }
}, 0));
addEventListener('online', saveState);
addEventListener('offline', saveState);
// 칸에 쓰다가 화면을 끄거나 다른 앱으로 가면 그 칸을 떠난 것으로 쳐서 저장한다 (안 하면 쓴 글이 사라질 수 있다)
const flush = () => {
  const a = document.activeElement;
  if (a?.dataset?.path) a.blur();
};
addEventListener('pagehide', flush);
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') flush(); });

for (const b of document.querySelectorAll('[data-set-status]')) {
  b.addEventListener('click', () => save('status', b.dataset.setStatus));
}
$('print').addEventListener('click', () => { measurePrint(); print(); });
// 3단계 — 이 내역서의 고객 · 행사일 · 상차림 · 금액으로 새 거래명세서 · 시제 견적서(2026-10-28) (꾸러미는 같은 탭 sessionStorage, 주소엔 안 실음)
for (const [btn, to, noun, build] of [['make-statement', 'statement', '거래명세서', eventToStatement],
  ['make-quote', 'sije-quote', '견적서', eventToQuote]]) {
  $(btn).addEventListener('click', async () => {
    if (!ev || !confirm(`이 내역서 내용으로 새 ${noun}를 만들까요?`)) return;
    flush();
    // 저장을 기다리지 않고 넘어가면 휴대폰이 바쁠 때 고친 칸이 내역서에서 사라졌다 (2026-10-28) — 서류 화면처럼 3초까지만 기다린다
    if (saving && navigator.onLine) await atMost(saving.catch(() => {}));   // 저장이 실패해도(알림은 이미 뜸) 버튼은 막히지 않게
    putBundle(sessionStorage, to, build(ev), Date.now());
    location.href = `${to}.html?make=1`;
  });
}
$('attach').addEventListener('click', () => $('image-file').click());
$('image-file').addEventListener('change', async () => {
  const file = $('image-file').files[0];
  $('image-file').value = '';
  if (!file) return;
  try {
    addImage(id, await shrink(file)).catch((e) => toast(`그림을 저장하지 못했습니다 (${e.code || e.message})`));
  } catch (e) {
    toast(e.message);
  }
});
$('view-link').addEventListener('click', async () => {
  if (!ev) return;
  let key = ev.viewKey;
  if (!key) {
    try { key = await ensureViewKey(id, newViewKey); } catch (e) { return toast(`링크를 만들지 못했습니다 (${e.code || e.message})`); }
    ev.viewKey = key;   // 화면 값에도 넣어 두 번째 누를 때 같은 링크
  }
  const text = viewLinkText(ev, `${location.origin}/sije-view.html#${key}`);
  const warn = ev.status === '확정' ? '' : ' · 확정이 되어야 담당자에게 보여요';
  if (matchMedia('(pointer: coarse)').matches && navigator.share) {
    try { await navigator.share({ text }); } catch (e) { if (e.name === 'AbortError') return;
      // 크롬은 누른 뒤 약 5초 안에만 공유를 허락한다 - 링크 저장을 기다리다 지났으면 키는 이미 저장됐으니 한 번 더 누르면 된다
      toast(e.name === 'NotAllowedError' ? '링크를 만들었어요 — 한 번 더 눌러 주세요' : `공유하지 못했습니다 (${e.name})`); return; }
    if (warn) toast('확정이 되어야 담당자에게 보여요');
    return;
  }
  try { await navigator.clipboard.writeText(text); toast('링크를 복사했어요 — 카톡 대화창에 붙여 넣으세요' + warn); }
  catch (e) { toast(`복사하지 못했습니다 (${e.name})`); }
});

$('sign-in').addEventListener('click', () => signIn().catch((e) => toast(`로그인하지 못했습니다 (${e.code || e.message})`)));

function fail(e) {
  $('message').textContent = e.code === 'permission-denied' ? '권한이 없습니다 — 사장님께 문의하세요.'
    : `불러오지 못했습니다 (${e.code || e.message})`;
  show('message');
}

show('loading');
saveState();
await initStore();
const testToken = new URLSearchParams(location.search).get('testToken');
if (testToken) await signInForTest(testToken).catch((e) => toast(`시험 로그인 실패 (${e.code || e.message})`));

onUser((user) => {
  stops.forEach((s) => s());
  stops = [];
  if (!user) return show('login');
  if (!id) { $('message').textContent = '행사가 지정되지 않았습니다 — 목록에서 골라 주세요.'; return show('message'); }
  stops.push(watchEvent(id, (data, meta) => {
    if (!data) { $('message').textContent = '행사를 찾을 수 없습니다.'; return show('message'); }
    ev = data;
    pending = meta.pending;
    trackCache(meta.fromCache);
    show('doc');
    paint();
    const notes = sessionStorage.getItem(NOTES_KEY);   // 3단계 — 견적서에서 옮겨 만들며 못 읽은 칸이 있었다 (한 번만)
    if (notes) {
      sessionStorage.removeItem(NOTES_KEY);
      toast(JSON.parse(notes).join(' · '));
    }
  }, fail));
  stops.push(watchImages(id, (urls) => { images = urls; paint(); }));
});
