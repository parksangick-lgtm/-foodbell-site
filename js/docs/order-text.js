/* 일일 일정표 '문자 붙여넣기' — 카톡 주문 글에서 모양이 분명한 것만 뽑는다 (사장님 결정 2026-10-20, 실제 표본 9개 + 3b 검토).
   시간 = 상차림 · 도착 시간만. 시각마다 바로 뒤에 붙은 말('08시20분 화장', '09시50분/4회차', '11시20분경 도착'), 없으면
          앞쪽에서 가장 가까운 말('발인 05시30분', '도착 약 11시', '일시 : … 15시'), 그래도 없으면 바로 앞 줄의 '도착'(…도착시간 / 약 11시)로
          무슨 시각인지 가린다. 화장 · 발인 · 회차는 빼고, 상차림 > 도착 > 일시 > 아무 말 없음 차례로 고른다.
          적힌 그대로('3시', '11시반', '오후 3:30') — 오전 · 오후를 짐작하지 않는다. '시제 · 시사 · 시간' 은 시각이 아니다.
   발인 · 화장 = 같은 방법으로 '발인' · '화장' 이 붙은 첫 시각 (화장 회차 '09시50분/4회차' 는 화장) — 2026-10-21 부터 그 칸에 따로.
   연락처 = 휴대폰 번호(010 …, 하이픈 없어도 010-0000-0000 꼴로). 계좌 · 묘역번호 · 번지는 모양이 달라 안 걸린다.
   단가 = '35만(원)' · '15,000원' 같은 값이 하나일 때만 — 줄을 넘어 읽지 않고, 번호 끝자리('…-5678 원하시는')는 값이 아니다.
          띄어 쓴 숫자 뒤의 '천안' · '만나서' · '원래' 처럼 단위 글자로 시작하는 낱말도 값이 아니다.
   인원은 안 뽑는다(식사 100인분 × 평토상 35만 같은 틀린 곱셈). 메모 = 원문 그대로.
   옛 아이폰(사파리 16.4 전)에서도 열리게 뒤보기(lookbehind) 대신 앞 글자를 잡는 묶음 (^|…) 을 쓴다 */
import { readNumber } from './amount.js?v=1';

const TIME = /(^|[^\d/.:-])((?:(?:오전|오후)\s*)?(?:\d{1,2}\s*시(?![간제사작])(?:\s*(?:\d{1,2}\s*분|반))?|\d{1,2}:\d{2}))/g;
const STAMP = /\[(?:오전|오후)\s*\d{1,2}:\d{2}\]/g;          // 여러 말을 함께 복사하면 붙는 '[오후 3:21]' (보낸 시각)
const NEAR_AFTER = /^\s*(?:경\s*)?(?:\/\s*)?(?:\d+\s*)?(화장|발인|회차|도착|상차림)/;
const WORD = /화장|발인|회차|도착|상차림|일시/g;
const RANK = { 상차림: 4, 도착: 3, 일시: 2, '': 1 };          // 화장 · 발인 · 회차 = 상차림 시간이 아님
const TEL = /(^|\D)(01[016789])[-.\s]?(\d{3,4})[-.\s]?(\d{4})(?!\d)/g;
const MONEY = /(^|[^\d.,-])(\d[\d,.]*[ \t]*만(?:[ \t]*\d+[ \t]*천)?[ \t]*원?|\d+[ \t]*천[ \t]*원?|\d{1,3}(?:,\d{3})+[ \t]*원|\d+[ \t]*원)/g;

function timesIn(line) {
  return [...line.matchAll(TIME)].map((m) => ({ text: m[2].trim(), start: m.index + m[1].length, end: m.index + m[0].length }));
}

/* 글 속 시각마다 무슨 시각인지(붙은 말) — { text, word } */
function timesWithWords(text) {
  const lines = text.replace(STAMP, ' ').split('\n');
  const out = [];
  lines.forEach((line, i) => {
    const toks = timesIn(line);
    toks.forEach((t, k) => {
      const after = line.slice(t.end, k + 1 < toks.length ? toks[k + 1].start : line.length);
      const before = line.slice(k ? toks[k - 1].end : 0, t.start);
      const prev = lines[i - 1] || '';
      const word = (after.match(NEAR_AFTER) || [])[1]
        || (before.match(WORD) || []).pop()
        || (/도착/.test(prev) && !timesIn(prev).length ? '도착' : '');
      out.push({ text: t.text, word });
    });
  });
  return out;
}

function findTime(times) {
  let best = null;
  for (const t of times) {
    const rank = RANK[t.word];
    if (rank && (!best || rank > best.rank)) best = { text: t.text, rank };
  }
  return best ? best.text : '';
}

const firstWith = (times, words) => (times.find((t) => words.includes(t.word)) || { text: '' }).text;

function findTels(text) {
  const out = [];
  for (const m of text.matchAll(TEL)) {
    const n = `${m[2]}-${m[3]}-${m[4]}`;
    if (!out.includes(n)) out.push(n);
  }
  return out;
}

const SPACED = /\d[ \t]+[만천원]/;                            // 숫자와 단위 사이가 띄어져 있다

/* 띄어 쓴 숫자 + 단위 바로 뒤에 한글이 붙으면 값이 아니다 — '3 천안', '2 만나서', '12 원래', '12 천주교' (2026-10-28).
   '35만에' 처럼 붙여 쓴 것과 '35 만원 부탁' 처럼 단위 뒤가 띄어진 것은 그대로 읽는다 */
const wordAfterSpacedUnit = (text, m) => SPACED.test(m[2]) && /[가-힣]/.test(text[m.index + m[0].length] || '');

function findPrice(text) {
  const vals = [...new Set([...text.matchAll(MONEY)].filter((m) => !wordAfterSpacedUnit(text, m)).map((m) => readNumber(m[2])).filter(Boolean))];
  return vals.length === 1 ? vals[0] : null;
}

export function parseOrder(text) {
  const t = String(text || '').replace(/\r\n?/g, '\n').trim();
  const times = timesWithWords(t);
  return { tel: findTels(t), time: findTime(times), depart: firstWith(times, ['발인']), cremate: firstWith(times, ['화장', '회차']),
    price: findPrice(t), memo: t };
}
