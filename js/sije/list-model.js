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
