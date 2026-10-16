// 시제행사 목록 화면 (sije-list.html) — 로그인 · 상태 버튼 · 새 행사
import { formatDateText } from './model.js';
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

$('new-event').addEventListener('click', async () => {
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
          location.href = `sije-sheet.html?id=${encodeURIComponent(await createFromTemplate(t.name))}`;
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
});
$('tpl-cancel').addEventListener('click', () => $('tpl-dialog').close());

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
  stop = watchEvents((r) => { rows = r; render(); }, (e) => {
    rows = [];
    render();
    if (e.code === 'permission-denied') show('denied');
    else toast(`목록을 불러오지 못했습니다 (${e.code || e.message})`);
  });
});
