// 서류 잇기 (3단계) — 칸 글자 읽기 · 넘길 꾸러미 만들기 · 꾸러미 주고받기. 저장소에 붙지 않는다.
// 꾸러미는 같은 탭의 sessionStorage 에 잠깐 둔다 — 손님 이름 · 금액을 주소(URL)에 싣지 않으려고(주소는 방문 · 서버 기록에 남는다).

const KEY = 'foodbell-handoff';
export const NOTES_KEY = 'foodbell-handoff-notes';   // 새 서류 화면에 한 번 보여 줄 알림 (못 읽은 날짜 · 금액)
const FRESH_MS = 60_000;   // 이보다 오래된 꾸러미는 쓰지 않는다 (나중에 목록을 열 때 엉뚱한 서류가 생기지 않게)
const NO_DATE = '날짜를 읽지 못했습니다 — 직접 넣어 주세요';
const NO_AMOUNT = '금액을 읽지 못했습니다 — 직접 넣어 주세요';
const pad2 = (n) => String(n).padStart(2, '0');

// '2026년 11월 21일 (토) 오전 10시' → { date: '2026-11-21', time: '오전 10시' }. 연 · 월 · 일이 없거나 없는 날짜면 null.
export function parseWhen(text) {
  const m = /(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일/.exec(text || '');
  if (!m) return null;
  if (/음력\s*$/.test(text.slice(0, m.index))) return null;   // 음력 날짜를 양력 칸에 넣지 않는다 (시제는 음력으로 적는 일이 많다)
  const [y, mo, d] = [Number(m[1]), Number(m[2]), Number(m[3])];
  const dt = new Date(Date.UTC(y, mo - 1, d));
  if (dt.getUTCFullYear() !== y || dt.getUTCMonth() !== mo - 1 || dt.getUTCDate() !== d) return null;
  const time = text.slice(m.index + m[0].length)
    .replace(/^\s*\([^)]*\)/, '')                        // (토) · (음력 10월 3일)
    .replace(/^\s*[월화수목금토일](요일)?(?=\s|$)/, '')    // 괄호 없는 요일
    .trim();
  return { date: `${y}-${pad2(mo)}-${pad2(d)}`, time };
}

// '600,000원' · '600000' · '₩600,000' → 600000. 내역서 금액 칸은 손으로 적어 모양이 여러 가지다(실제 85장, 2026-10-18):
// '360만 VAT별도' · '90만원' · '132만원(입금가)' · '1,200,000원 (1자상)' · '2.145.000' · '170'.
// 점은 쉼표처럼 자리 나눔, 뒤에는 (메모) 나 'VAT별도' 만 허락한다 — 'VAT포함' 은 공급가액이 아니라서 null.
// 단위 없이 1만 미만 숫자만 있으면 만 원으로 본다('170' → 1,700,000 — 사장님 결정). 숫자가 아니거나 자리가 틀리면 null.
export function parseAmount(text) {
  const m = /^\s*₩?\s*(\d{1,3}(?:[.,]\d{3})+|\d+)\s*(만)?\s*(원)?\s*(?:\([^)]*\)|(?:VAT|부가세)\s*별도)?\s*$/i.exec(text || '');
  if (!m) return null;
  let n = Number(m[1].replace(/[.,]/g, ''));
  if (m[2] || (!m[3] && n < 10000)) n *= 10000;
  return n > 0 ? n : null;
}

// '2026-11-21' → '11/21' (거래명세서의 월/일 꼴)
export function monthDay(date) {
  if (!date) return '';
  const [, m, d] = date.split('-').map(Number);
  return `${m}/${d}`;
}

export const wonText = (n) => `${n.toLocaleString('ko-KR')}원`;

export const pickTemplate = (tier, names) => (tier && names.includes(tier) ? tier : null);

// 시제 견적서 → 내역서. src = 견적서 화면의 handoff() 값 { customer, when, place, setting, supply, tier }
export function quoteToEvent(src) {
  const when = parseWhen(src.when);
  const notes = [];
  if (!when) notes.push(NO_DATE);
  if (!(src.supply > 0)) notes.push(NO_AMOUNT);
  return {
    fields: {
      customer: src.customer || '', date: when ? when.date : '', time: when ? when.time : '',
      place: src.place || '', titlePlace: src.place || '', setting: src.setting || '',
      amount: src.supply > 0 ? wonText(src.supply) : '', template: src.tier || '',
    },
    notes,
  };
}

// 시제 · 행사 견적서 → 거래명세서 한 줄. 품목 = 시제는 상차림, 행사는 행사 구분(item)
export function quoteToStatement(src) {
  const when = parseWhen(src.when);
  const notes = [];
  if (!when) notes.push(NO_DATE);
  if (!(src.supply > 0)) notes.push(NO_AMOUNT);
  return {
    fields: { cust: src.customer || '', md: when ? monthDay(when.date) : '', item: src.setting ?? src.item ?? '', price: src.supply > 0 ? src.supply : null },
    notes,
  };
}

// 내역서(1단계 행사 문서) → 거래명세서 한 줄. 단가 = 금액 글자에서 읽은 숫자
export function eventToStatement(ev) {
  const price = parseAmount(ev.amount);
  const notes = [];
  if (!ev.date) notes.push(NO_DATE);
  if (price === null) notes.push(NO_AMOUNT);
  return { fields: { cust: ev.customer || '', md: monthDay(ev.date), item: ev.setting || '', price }, notes };
}

export function putBundle(storage, to, built, now) {
  storage.setItem(KEY, JSON.stringify({ to, at: now, fields: built.fields, notes: built.notes }));
}

// 받는 화면이 한 번 읽는다 — 읽으면 늘 지운다. 받는 곳이 다르거나 1분 넘었거나 ?make=1 이 아니면 null.
export function takeBundle(storage, to, makeFlag, now) {
  const raw = storage.getItem(KEY);
  storage.removeItem(KEY);
  if (!raw || !makeFlag) return null;
  try {
    const b = JSON.parse(raw);
    if (b.to !== to || !(now - b.at <= FRESH_MS)) return null;
    return { fields: b.fields, notes: b.notes || [] };
  } catch {
    return null;
  }
}
