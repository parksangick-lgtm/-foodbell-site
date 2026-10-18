// js/docs/handoff.js 시험 (3단계 서류 잇기) — 실행: node --test "tools/sije_web/js-tests/*.test.mjs"
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  parseWhen, parseAmount, monthDay, wonText, pickTemplate,
  quoteToEvent, quoteToStatement, eventToStatement, putBundle, takeBundle,
} from '../../../js/docs/handoff.js';

const NO_DATE = '날짜를 읽지 못했습니다 — 직접 넣어 주세요';
const NO_AMOUNT = '금액을 읽지 못했습니다 — 직접 넣어 주세요';

test('parseWhen — 견적서 꼴', () => {
  assert.deepEqual(parseWhen('2026년 11월 21일 (토) 오전 10시'), { date: '2026-11-21', time: '오전 10시' });
});

test('parseWhen — 시간 없음 · 붙여 쓴 꼴', () => {
  assert.deepEqual(parseWhen('2026년 3월 1일'), { date: '2026-03-01', time: '' });
  assert.deepEqual(parseWhen('2026년11월1일(일)10시'), { date: '2026-11-01', time: '10시' });
});

test('parseWhen — 음력 날짜는 양력 칸에 넣지 않는다 (3단계 검토 M3)', () => {
  assert.equal(parseWhen('음력 2026년 10월 3일 (양력 11월 11일)'), null);
  assert.equal(parseWhen('음력2026년 10월 3일'), null);
  // 양력 날짜 뒤에 음력을 괄호로 적은 꼴은 그대로 읽는다
  assert.deepEqual(parseWhen('2026년 11월 21일 (음력 10월 3일) 오전 10시'), { date: '2026-11-21', time: '오전 10시' });
});

test('parseWhen — 괄호 없는 요일은 시간에서 뺀다', () => {
  assert.deepEqual(parseWhen('2026년 11월 21일 토요일 오전 10시'), { date: '2026-11-21', time: '오전 10시' });
  assert.deepEqual(parseWhen('2026년 11월 21일 토 10시'), { date: '2026-11-21', time: '10시' });
});

test('parseWhen — 못 읽으면 null', () => {
  for (const t of ['11월 21일', '2026년 13월 1일', '2026년 2월 30일', '', undefined]) assert.equal(parseWhen(t), null, String(t));
});

test('parseAmount — 받는 꼴', () => {
  for (const t of ['600,000원', '600000', '₩600,000', ' 600,000 원 ']) assert.equal(parseAmount(t), 600000, t);
});

test('parseAmount — 만 단위 · 메모 · 점 (실제 내역서 금액 칸에 적힌 모양, 2026-10-18)', () => {
  const cases = {
    '90만원': 900000, '180만': 1800000, '360만 VAT별도': 3600000, '385만 VAT별도': 3850000,
    '132만원(입금가)': 1320000, '1,200,000원 (1자상)': 1200000,       // 괄호 메모는 빼고 앞 숫자
    '2.145.000': 2145000, '1.585.000': 1585000, '2.400,000원': 2400000,  // 점도 자리 나눔으로
    '170': 1700000,                                                     // 단위 없는 1만 미만 숫자는 만 원 (사장님 결정)
  };
  for (const [t, n] of Object.entries(cases)) assert.equal(parseAmount(t), n, t);
});

test('parseAmount — 못 읽으면 null', () => {
  for (const t of ['', '육십만원', '600,00원', '0', '0만원', '1.5만', '360만 VAT포함', '60만원 정도', undefined]) {
    assert.equal(parseAmount(t), null, String(t));
  }
});

test('monthDay · wonText', () => {
  assert.equal(monthDay('2026-11-21'), '11/21');
  assert.equal(monthDay('2026-03-01'), '3/1');
  assert.equal(monthDay(''), '');
  assert.equal(wonText(600000), '600,000원');
  assert.equal(wonText(1000000), '1,000,000원');
});

test('pickTemplate — 빈 양식에 있는 이름만', () => {
  const names = ['60만원상', '7치 고임상', '1자 고임상'];
  assert.equal(pickTemplate('7치 고임상', names), '7치 고임상');
  assert.equal(pickTemplate('40만원상', names), null);
  assert.equal(pickTemplate('', names), null);
});

const QUOTE = {
  customer: '○○ 김씨 문중 종친회', when: '2026년 11월 21일 (토) 오전 10시', place: '충남 ○○군 ○○면 선산 묘역 (야외)',
  setting: '5열 진설 제수상 1상 + 종친 음복 식사', supply: 1000000, tier: '7치 고임상',
};

test('quoteToEvent — 칸 옮기기', () => {
  assert.deepEqual(quoteToEvent(QUOTE), {
    fields: {
      customer: '○○ 김씨 문중 종친회', date: '2026-11-21', time: '오전 10시',
      place: '충남 ○○군 ○○면 선산 묘역 (야외)', titlePlace: '충남 ○○군 ○○면 선산 묘역 (야외)',
      setting: '5열 진설 제수상 1상 + 종친 음복 식사', amount: '1,000,000원', template: '7치 고임상',
    },
    notes: [],
  });
});

test('quoteToEvent — 못 읽은 날짜 · 금액은 비우고 알림', () => {
  const r = quoteToEvent({ ...QUOTE, when: '11월 말', supply: 0 });
  assert.equal(r.fields.date, '');
  assert.equal(r.fields.time, '');
  assert.equal(r.fields.amount, '');
  assert.deepEqual(r.notes, [NO_DATE, NO_AMOUNT]);
});

test('quoteToStatement — 시제 견적서는 상차림, 행사 견적서는 행사 구분', () => {
  assert.deepEqual(quoteToStatement(QUOTE), {
    fields: { cust: '○○ 김씨 문중 종친회', md: '11/21', item: '5열 진설 제수상 1상 + 종친 음복 식사', price: 1000000 },
    notes: [],
  });
  const ev = { customer: '○○ 단체', when: '2026년 11월 21일 (토) 오전 11시', item: '단체 · 모임 행사 상차림', supply: 500000 };
  assert.deepEqual(quoteToStatement(ev).fields, { cust: '○○ 단체', md: '11/21', item: '단체 · 모임 행사 상차림', price: 500000 });
});

test('quoteToStatement — 공급가액이 없으면 단가 비우고 알림', () => {
  const r = quoteToStatement({ ...QUOTE, supply: 0 });
  assert.equal(r.fields.price, null);
  assert.deepEqual(r.notes, [NO_AMOUNT]);
});

test('eventToStatement — 내역서 금액 글자에서 단가', () => {
  const ev = { customer: '가짜 문중', date: '2026-11-13', setting: '7치 1상', amount: '600,000원' };
  assert.deepEqual(eventToStatement(ev), { fields: { cust: '가짜 문중', md: '11/13', item: '7치 1상', price: 600000 }, notes: [] });
  assert.equal(eventToStatement({ ...ev, amount: '360만 VAT별도' }).fields.price, 3600000);
  const bad = eventToStatement({ ...ev, date: '', amount: '육십만원' });
  assert.equal(bad.fields.md, '');
  assert.equal(bad.fields.price, null);
  assert.deepEqual(bad.notes, [NO_DATE, NO_AMOUNT]);
});

function fakeStorage() {
  const m = new Map();
  return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), removeItem: (k) => m.delete(k) };
}

test('꾸러미 — 한 번만 · 1분 안 · make 있을 때 · 받는 곳이 맞을 때만, 읽으면 늘 지움', () => {
  const s = fakeStorage();
  const built = { fields: { cust: '가짜' }, notes: [] };
  putBundle(s, 'statement', built, 1000);
  assert.deepEqual(takeBundle(s, 'statement', true, 1000 + 59_000), built);
  assert.equal(takeBundle(s, 'statement', true, 1000 + 59_000), null);      // 두 번째는 없음 (뒤로 가기 · 새로고침)
  putBundle(s, 'statement', built, 1000);
  assert.equal(takeBundle(s, 'statement', true, 1000 + 61_000), null);      // 1분 넘음
  assert.equal(s.getItem('foodbell-handoff'), null);
  putBundle(s, 'statement', built, 1000);
  assert.equal(takeBundle(s, 'statement', false, 2000), null);              // ?make=1 없이 연 목록
  assert.equal(s.getItem('foodbell-handoff'), null);
  putBundle(s, 'event', built, 1000);
  assert.equal(takeBundle(s, 'statement', true, 2000), null);               // 받는 곳이 다름
  s.setItem('foodbell-handoff', '{깨진');
  assert.equal(takeBundle(s, 'statement', true, 2000), null);               // 깨진 꾸러미
});
