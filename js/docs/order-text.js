/* 일일 일정표 '문자 붙여넣기' — 카톡 주문 글에서 모양이 분명한 것만 뽑는다 (사장님 결정 2026-10-20, 실제 표본 9개).
   시간 = 상차림 · 도착 시간만: 그 줄(또는 바로 앞 줄)에 '도착' 이 있는 시각 → 없으면 '일시' 줄의 시각 → 없으면 화장 · 발인 · 회차가
          아닌 첫 시각. 적힌 그대로('3시', '11시20분') — 오전 · 오후를 짐작하지 않는다.
   연락처 = 휴대폰 번호(010 …, 하이픈 없어도 010-0000-0000 꼴로). 계좌 · 묘역번호 · 번지는 모양이 달라 안 걸린다.
   단가 = '35만(원)' · '15,000원' 같은 값이 하나일 때만. 인원은 안 뽑는다(식사 100인분 × 평토상 35만 같은 틀린 곱셈).
   메모 = 원문 그대로 (뽑은 것도 지우지 않는다) */
import { readNumber } from './amount.js?v=1';

const TIME = /(?:(?:오전|오후)\s*)?\d{1,2}\s*시(?:\s*\d{1,2}\s*분)?|\d{1,2}:\d{2}/g;
const NOT_SETUP = /화장|발인|회차/;
const TEL = /(^|\D)(01[016789])[-.\s]?(\d{3,4})[-.\s]?(\d{4})(?!\d)/g;
const MONEY = /\d[\d,.]*\s*만(?:\s*\d+\s*천)?\s*원?|\d+\s*천\s*원?|\d{1,3}(?:,\d{3})+\s*원|\d+\s*원/g;

function findTime(text) {
  const lines = text.split('\n');
  const found = [];
  lines.forEach((line, i) => {
    for (const m of line.matchAll(TIME)) found.push({ text: m[0].trim(), line, prev: lines[i - 1] || '' });
  });
  const hasTime = (s) => s.search(TIME) >= 0;
  const pick = found.find((f) => /도착/.test(f.line) || (/도착/.test(f.prev) && !hasTime(f.prev)))   // '선산 도착시간 / 약 11시'
    || found.find((f) => /일시/.test(f.line))
    || found.find((f) => !NOT_SETUP.test(f.line));
  return pick ? pick.text : '';
}

function findTels(text) {
  const out = [];
  for (const m of text.matchAll(TEL)) {
    const n = `${m[2]}-${m[3]}-${m[4]}`;
    if (!out.includes(n)) out.push(n);
  }
  return out;
}

function findPrice(text) {
  const vals = [...new Set([...text.matchAll(MONEY)].map((m) => readNumber(m[0])).filter(Boolean))];
  return vals.length === 1 ? vals[0] : null;
}

export function parseOrder(text) {
  const t = String(text || '').replace(/\r\n?/g, '\n').trim();
  return { tel: findTels(t), time: findTime(t), price: findPrice(t), memo: t };
}
