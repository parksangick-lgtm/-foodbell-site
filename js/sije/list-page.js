// 시제행사 목록 화면 (sije-list.html) — 로그인 · 상태 버튼 · 새 행사
import { formatDateText } from './model.js';
import { takeBundle, pickTemplate, NOTES_KEY } from '../docs/handoff.js';
import {
  initStore, onUser, signIn, signInForTest, signOutUser, watchEvents, listTemplates, createFromTemplate,
} from './store.js';

const $ = (id) => document.getElementById(id);
let filter = '확정';
let rows = [];
let stop = null;

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}

function show(id) {
  for (const s of ['loading', 'login', 'denied', 'list']) $(s).hidden = s !== id;
}

function toast(msg) {
  const t = $('toast');
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { t.hidden = true; }, 4000);
}

function rowEl({ id, ev }) {
  const a = el('a', 'row');
  a.href = `sije-sheet.html?id=${encodeURIComponent(id)}`;
  a.dataset.id = id;
  a.append(
    el('span', 'r-date', ev.date ? formatDateText(ev.date, ev.time) : '날짜 미정'),
    el('span', 'r-place', ev.place || ev.titlePlace || ''),
    el('span', 'r-setting', ev.setting || ''),
    el('span', 'r-phone', (ev.contacts || []).join(', ')),
    el('span', 'r-status', ev.status),
  );
  if (ev.status === '미확정' && (ev.expectedDate || ev.basis)) {
    a.append(el('span', 'r-expect', [ev.expectedDate && `예상 ${ev.expectedDate}`, ev.basis].filter(Boolean).join(' · ')));
  }
  return a;
}

function render() {
  const shown = rows
    .filter((r) => filter === '전체' || r.ev.status === filter)
    .sort((a, b) => (a.ev.date || '9999').localeCompare(b.ev.date || '9999')
      || (a.ev.time || '').localeCompare(b.ev.time || ''));
  $('rows').replaceChildren(...shown.map(rowEl));
  $('empty').hidden = shown.length > 0;
  for (const b of document.querySelectorAll('[data-status]')) {
    b.setAttribute('aria-pressed', String(b.dataset.status === filter));
  }
}

for (const b of document.querySelectorAll('[data-status]')) {
  b.addEventListener('click', () => { filter = b.dataset.status; render(); });
}

$('sign-in').addEventListener('click', () => signIn().catch((e) => toast(`로그인하지 못했습니다 (${e.code || e.message})`)));
$('sign-out').addEventListener('click', () => signOutUser());

// 새 행사 만들기 — bundle(3단계: 견적서에서 옮겨 온 칸 · 알림)이 있으면 함께 넣고, 뒤로 가면 견적서로 돌아가게 한다
async function makeEvent(name, bundle) {
  const { template, ...extra } = bundle ? bundle.fields : {};
  const id = await createFromTemplate(name, extra);
  if (bundle?.notes.length) sessionStorage.setItem(NOTES_KEY, JSON.stringify(bundle.notes));
  const url = `sije-sheet.html?id=${encodeURIComponent(id)}`;
  if (bundle) location.replace(url);
  else location.href = url;
}

// 상 종류 고르기 창
async function chooseTemplate(bundle) {
  const dlg = $('tpl-dialog');
  $('tpl-list').replaceChildren(el('p', 'tpl-wait', '불러오는 중…'));
  dlg.showModal();
  try {
    const tpls = await listTemplates();
    $('tpl-list').replaceChildren(...tpls.map((t) => {
      const b = el('button', 'tpl-choice', t.name);
      b.type = 'button';
      b.addEventListener('click', async () => {
        b.disabled = true;
        try {
          await makeEvent(t.name, bundle);
        } catch (e) {
          b.disabled = false;
          toast(`새 행사를 만들지 못했습니다 (${e.code || e.message})`);
        }
      });
      return b;
    }));
  } catch (e) {
    $('tpl-list').replaceChildren(el('p', 'tpl-wait', `빈 양식을 불러오지 못했습니다 (${e.code || e.message})`));
  }
}
$('new-event').addEventListener('click', () => chooseTemplate(null));

// 3단계 — 시제 견적서의 '내역서 만들기' 로 ?make=1 열림: 1분 안의 꾸러미만 한 번 쓴다 (읽으면 늘 지움).
// 눌린 수량 버튼과 같은 빈 양식이 있으면 바로, 없으면(45만원상 · 안 누름) 고르기 창.
const incoming = takeBundle(sessionStorage, 'event', new URLSearchParams(location.search).get('make') === '1', Date.now());
async function receive(bundle) {
  toast('견적서 내용으로 내역서를 만드는 중…');   // 신호가 약하면 몇 초 걸린다 — 안 된 줄 알고 또 누르지 않게 (내역서는 지울 수 없다)
  try {
    const name = pickTemplate(bundle.fields.template, (await listTemplates()).map((t) => t.name));
    if (name) await makeEvent(name, bundle);
    else await chooseTemplate(bundle);
  } catch (e) {
    toast(`새 행사를 만들지 못했습니다 (${e.code || e.message})`);
  }
}
$('tpl-cancel').addEventListener('click', () => $('tpl-dialog').close());

// 인터넷이 끊기면 알린다 (목록은 기기에 저장해 둔 것을 보여 준다).
// 신호가 약한 산속이나 끊긴 채 연 화면은 navigator.onLine 이 '연결됨'으로 나오기도 해서,
// 저장소가 서버에 못 붙고 기기 저장본만 보여 주는 상태가 2초 넘게 이어져도 '연결 안 됨'으로 본다.
let cacheOnlySince = null;
const netState = () => {
  $('net-state').hidden = navigator.onLine && !(cacheOnlySince && Date.now() - cacheOnlySince > 2000);
};
const trackCache = (fromCache) => {
  cacheOnlySince = fromCache ? (cacheOnlySince ?? Date.now()) : null;
  netState();
  if (fromCache) setTimeout(netState, 2100);
};
addEventListener('online', netState);
addEventListener('offline', netState);
netState();

show('loading');
await initStore();
const testToken = new URLSearchParams(location.search).get('testToken');
if (testToken) await signInForTest(testToken).catch((e) => toast(`시험 로그인 실패 (${e.code || e.message})`));

onUser((user) => {
  stop?.();
  stop = null;
  rows = [];
  render();
  if (!user) return show('login');
  $('who').textContent = user.email || '';
  show('list');
  stop = watchEvents((r, meta) => { rows = r; render(); trackCache(meta.fromCache); }, (e) => {
    rows = [];
    render();
    if (e.code === 'permission-denied') show('denied');
    else toast(`목록을 불러오지 못했습니다 (${e.code || e.message})`);
  });
  if (incoming && !incoming.used) {
    incoming.used = true;   // 로그인 알림이 두 번 와도 한 장만
    receive(incoming);
  }
});
