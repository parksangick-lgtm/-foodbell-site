// 시제행사 내역서 — 행사 하나를 A4 한 장 모양으로 그린다.
// 웹 화면(편집) · 웹 인쇄 · 사무실 PC 의 PDF 가 모두 이 그리기를 쓴다 — 그래서 셋이 똑같이 나온다.
// 칸 배치 · 너비 · 글자 크기는 지금 엑셀 내역서(_만들기 프로그램\jobsheet.py)와 같다.
import { formatDateText } from './model.js';

// 엑셀 열 너비(pt): 구분 · 번호 · 품목 · 수량 · 비고 · 준비 | 가운데 틈 | 오른쪽 같은 6칸
const COLS = [57, 28.5, 78, 47, 112, 28.5, 4.5, 57, 28.5, 78, 47, 112, 28.5];
const SIDE = ['grp', 'no', 'name', 'qty', 'note', 'chk'];

// A4 에서 여백(왼쪽·오른쪽 0.25in, 위·아래 0.3in)을 뺀 자리, px
const PAGE_W = (210 / 25.4 - 0.5) * 96;
const PAGE_H = (297 / 25.4 - 0.6) * 96;
const MIN_ZOOM = 0.7;

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}

export function renderSheet(root, ev, images, opts = {}) {
  const { editable = false, onEdit } = opts;
  root.replaceChildren();
  root.classList.add('sije-sheet');
  delete root.dataset.overflow;

  const table = el('table', 'sheet-top');
  const colgroup = el('colgroup');
  for (const w of COLS) {
    const col = el('col');
    col.style.width = `${w}pt`;
    colgroup.append(col);
  }
  const body = el('tbody');
  table.append(colgroup, body);

  const row = (cls) => body.appendChild(el('tr', cls));
  const cell = (tr, cls, text, { span = 1, rows = 1, path = null } = {}) => {
    const td = tr.appendChild(el('td', cls, text ?? ''));
    if (span > 1) td.colSpan = span;
    if (rows > 1) td.rowSpan = rows;
    if (path && editable) {
      td.contentEditable = 'plaintext-only';
      td.dataset.path = path;
      td.dataset.orig = td.textContent;
    }
    return td;
  };
  const gap = () => cell(row('gap-row'), '', '', { span: 13 });
  const section = (title) => cell(row('sec'), '', title, { span: 13 });
  const value = (path) => {
    const m = /^contacts\.(\d+)$/.exec(path || '');
    return (m ? (ev.contacts || [])[Number(m[1])] : ev[path]) ?? '';
  };

  // 맨 위 큰 줄: 주소(첫 줄) + 행사일(둘째 줄)
  const dateText = ev.date ? formatDateText(ev.date, ev.time) : '';
  const title = cell(row('title'), '', null, { span: 13 });
  const place = title.appendChild(el('div', 'title-place', ev.titlePlace || ''));
  if (editable) {
    place.contentEditable = 'plaintext-only';
    place.dataset.path = 'titlePlace';
    place.dataset.orig = place.textContent;
  }
  title.append(el('div', 'title-date', dateText));
  gap();

  // ■ 행사 정보
  section('■ 행사 정보');
  let tr = row();
  cell(tr, 'lab', '행사일', { span: 2 });
  cell(tr, 'val' + (dateText ? '' : ' blank'), dateText, { span: 11 });
  const contacts = ev.contacts?.length ? ev.contacts : [''];
  const pairs = [['장소', 'place', '시제일', 'sijeil'], ['상차림', 'setting', '산신제', 'sansinje'],
    ['고객', 'customer', '연락처', 'contacts.0']];
  for (let i = 1; i < contacts.length; i += 2) {
    pairs.push([`연락처 ${i + 1}`, `contacts.${i}`,
      ...(i + 1 < contacts.length ? [`연락처 ${i + 2}`, `contacts.${i + 1}`] : ['', null])]);
  }
  pairs.push(['담당·차량', 'staffCar', '식사', 'meal'], ['금액', 'amount', '금액 내역', 'amountDetail'],
    ['출발 시간', 'departTime', '도착 시간', 'arriveTime']);
  for (const [la, pa, lb, pb] of pairs) {
    tr = row();
    for (const [label, path, ls, vs] of [[la, pa, 2, 4], [lb, pb, 3, 4]]) {
      cell(tr, 'lab', label, { span: ls });
      const v = path ? value(path) : '';
      cell(tr, 'val' + (v || !path ? '' : ' blank'), v, { span: vs, path });
    }
  }
  gap();

  // ■ 꼭 지킬 것 (줄마다 한 칸 — 인쇄에서 비어 있으면 구역째 뺀다, 엑셀과 같게)
  if (ev.mustDo || editable) {
    section('■ 꼭 지킬 것');
    for (const line of (ev.mustDo || '').split('\n')) cell(row('must'), '', line, { span: 13, path: 'mustDo' });
    gap();
  }

  // ■ 준비 품목 — 왼쪽 L01… · 오른쪽 R01…, 같은 구분은 한 칸으로 합친다
  const t = ev.templateType || '';
  section('■ 준비 품목' + (t ? (t.startsWith('(') ? ` ${t}` : ` — ${t}`) : ''));
  tr = row('ihead');
  for (const side of [0, 1]) {
    if (side) cell(tr, 'gap', '');
    for (const h of ['구분', '번호', '품목', '수량', '비고', '준비']) cell(tr, '', h);
  }
  const items = ev.items || {};
  const keys = { L: [], R: [] };
  for (const k of Object.keys(items).sort()) keys[k[0]]?.push(k);
  let n = Math.max(keys.L.length, keys.R.length, 1);
  const extraSide = keys.R.length < n ? 'R' : keys.L.length < n ? 'L' : null;
  if (!extraSide && (ev.extraItems || editable)) n += 1;   // 추가 기입 칸이 남지 않으면 한 줄 더
  const extraAt = extraSide || 'R';
  for (let r = 0; r < n; r++) {
    tr = row('item');
    for (const side of ['L', 'R']) {
      if (side === 'R') cell(tr, 'gap', '');
      const ks = keys[side];
      if (r < ks.length) {
        const k = ks[r], it = items[k];
        const end = r === ks.length - 1 || items[ks[r + 1]].group !== it.group;
        if (r === 0 || items[ks[r - 1]].group !== it.group) {
          let len = 1;
          while (r + len < ks.length && items[ks[r + len]].group === it.group) len++;
          cell(tr, 'grp end', it.group, { rows: len });
        }
        const e = end ? ' end' : '';
        cell(tr, 'no' + e, it.no);
        for (const f of ['name', 'qty', 'note']) cell(tr, f + e, it[f], { path: `items.${k}.${f}` });
        cell(tr, 'chk' + e, '').append(el('span', 'box'));
      } else {
        const left = n - ks.length;
        if (r === ks.length) {
          cell(tr, 'grp end', left === 1 ? '추가 기입' : '추가\n기입', { rows: left });
          if (side === extraAt) {
            cell(tr, 'extra end', ev.extraItems || '', { span: 4, rows: left, path: 'extraItems' });
          }
        }
        if (side !== extraAt) for (const f of SIDE.slice(1, 5)) cell(tr, f + (r === n - 1 ? ' end' : ''), '');
        cell(tr, 'chk' + (r === n - 1 ? ' end' : ''), '').append(el('span', 'box'));
      }
    }
  }

  // ■ 메모 — 남는 높이를 채운다. 그림은 메모 빈자리에
  const memo = el('div', 'memo');
  memo.append(el('div', 'memo-sec', '■ 메모'));
  const box = memo.appendChild(el('div', 'memo-box'));
  const lines = box.appendChild(el('div', 'memo-lines'));
  const text = lines.appendChild(el('div', 'memo-text', ev.memo || ''));
  if (editable) {
    text.contentEditable = 'plaintext-only';
    text.dataset.path = 'memo';
    text.dataset.orig = text.textContent;
  }
  // 글 아래 빈자리는 손으로 적는 줄 — 남는 높이만큼만 보인다 (엑셀의 메모 줄처럼)
  const rule = lines.appendChild(el('div', 'memo-rule'));
  for (let i = 0; i < 40; i++) rule.append(el('div', 'memo-line'));
  if (images?.length) {
    const imgs = box.appendChild(el('div', 'memo-imgs'));
    for (const src of images) {
      const img = imgs.appendChild(el('img'));
      img.src = src;
      img.alt = '';
    }
  }

  root.append(table, memo);

  if (editable && onEdit) {
    root.addEventListener('focusout', (e) => {
      const td = e.target.closest?.('[data-path]');
      if (!td || !root.contains(td)) return;
      const path = td.dataset.path;
      const read = (x) => x.innerText.replace(/\n+$/, '');
      const v = path === 'mustDo'
        ? [...root.querySelectorAll('[data-path="mustDo"]')].map(read).join('\n')
        : read(td);
      if (read(td) === td.dataset.orig) return;
      td.dataset.orig = read(td);
      onEdit(path, v);
    });
  }
}

// A4 한 장에 맞추는 배율(0.7~1.0). 가장 작게 줄여도 넘치면 0.7 을 돌려주고 data-overflow="1".
export function fitToA4(root) {
  root.style.zoom = '';
  delete root.dataset.overflow;
  const z = Math.min(1, PAGE_W / root.offsetWidth, PAGE_H / root.scrollHeight) * 0.995;
  if (z < MIN_ZOOM) root.dataset.overflow = '1';
  const zoom = Math.max(MIN_ZOOM, z);
  root.style.zoom = String(zoom);
  return zoom;
}
