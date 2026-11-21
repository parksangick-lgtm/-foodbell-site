// 시제행사 목록의 순수 계산 — 정렬(오늘 이후 먼저 · 지난 행사는 아래) · 검색. 저장소 · 화면에 안 붙는다.

// 날짜 오름차순(날짜 없음은 맨 끝), 같은 날은 시간 순 — 전부터 쓰던 규칙
function byDateAsc(a, b) {
  return (a.ev.date || '9999').localeCompare(b.ev.date || '9999')
    || (a.ev.time || '').localeCompare(b.ev.time || '');
}

// 지난 행사: 최근 날짜 먼저, 같은 날은 시간 순
function byDateDesc(a, b) {
  return b.ev.date.localeCompare(a.ev.date)
    || (a.ev.time || '').localeCompare(b.ev.time || '');
}

// 상 종류 고르기 창의 단추 순서 — 큰 상부터 (사장님 2026-11-21). 저장소는 이름순(1자 · 45만 · 60만 · 7치)으로 준다.
// 여기 없는 새 양식은 그 뒤에 이름순, 수량 없는 빈 양식(type '')은 맨 끝.
const TEMPLATE_ORDER = ['1자 고임상', '7치 고임상', '60만원상', '45만원 고급상', '기본상'];
export function sortTemplates(tpls) {
  const rank = (t) => {
    if (t.type === '') return TEMPLATE_ORDER.length + 1;
    const i = TEMPLATE_ORDER.indexOf(t.name);
    return i === -1 ? TEMPLATE_ORDER.length : i;
  };
  return [...tpls].sort((a, b) => rank(a) - rank(b) || a.name.localeCompare(b.name, 'ko'));
}

// 기기 시각(로컬)의 'YYYY-MM-DD'
export function todayISO(now = new Date()) {
  const p = (n) => String(n).padStart(2, '0');
  return `${now.getFullYear()}-${p(now.getMonth() + 1)}-${p(now.getDate())}`;
}

// rows: [{ id, ev }] → { upcoming: 오늘(포함) 이후 + 날짜 없음, past: 오늘 전 }
export function splitRows(rows, today) {
  const isPast = (r) => Boolean(r.ev.date) && r.ev.date < today;
  return {
    upcoming: rows.filter((r) => !isPast(r)).sort(byDateAsc),
    past: rows.filter(isPast).sort(byDateDesc),
  };
}

// 공백 · 하이픈 · 대소문자를 무시하고 견준다 (전화 '010-0000-0000' 을 '01000000000' 으로 찾게)
const norm = (s) => String(s ?? '').toLowerCase().replace(/[\s-]/g, '');

// 이름(customer) · 장소(place · titlePlace) · 전화(contacts) 에 query 글자가 들어 있으면 true. 빈 검색은 전부.
export function matchRow(ev, query) {
  const q = norm(query);
  if (!q) return true;
  const fields = [ev.customer, ev.place, ev.titlePlace, ...(Array.isArray(ev.contacts) ? ev.contacts : [])];
  return fields.some((f) => norm(f).includes(q));
}
