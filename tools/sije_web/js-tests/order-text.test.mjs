// 일일 일정표 '문자 붙여넣기' — 실제 카톡 주문 표본(이름 · 번호는 가짜)에서 시간 · 연락처 · 단가를 뽑는다
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { parseOrder } from '../../../js/docs/order-text.js';

const { samples, rejects, time_edge: timeEdge, funeral_edge: funeralEdge, price_edge: priceEdge } = JSON.parse(readFileSync(new URL('./fixtures/order-samples.json', import.meta.url), 'utf8'));

test('표본마다 사장님이 정한 칸 값', () => {
  for (const s of samples) {
    const got = parseOrder(s.text);
    console.log(`${s.name}\n  → 시간 '${got.time}' · 발인 '${got.depart}' · 화장 '${got.cremate}' · 연락처 ${JSON.stringify(got.tel)} · 단가 ${got.price}`);   // 눈으로 본다
    assert.deepEqual({ tel: got.tel, time: got.time, depart: got.depart, cremate: got.cremate, price: got.price },
      { tel: s.tel, time: s.time, depart: s.depart, cremate: s.cremate, price: s.price }, s.name);
  }
});

test('발인 · 화장 — 그 말이 붙은 시간만, 화장 회차는 화장 (2026-10-21)', () => {
  for (const c of funeralEdge) {
    const got = parseOrder(c.text);
    assert.deepEqual({ depart: got.depart, cremate: got.cremate }, { depart: c.depart, cremate: c.cremate }, c.text);
  }
});

test('메모는 원문 그대로 (뽑은 것도 지우지 않음)', () => {
  for (const s of samples) assert.equal(parseOrder(s.text).memo, s.text, s.name);
  assert.equal(parseOrder('  가짜\r\n주문  ').memo, '가짜\n주문');
});

test('시간 — 화장 · 발인 · 회차 시간은 줄 어디에 있어도 안 넣고, 시제 · 시간 · 보낸 시각은 시간이 아님 (3b 검토)', () => {
  for (const c of timeEdge) assert.equal(parseOrder(c.text).time, c.time, c.text);
});

test('단가 — 줄을 넘거나 번호 끝자리를 값으로 읽지 않음 (3b 검토)', () => {
  for (const c of priceEdge) assert.equal(parseOrder(c.text).price, c.price, c.text);
});

test('번호로 보면 안 되는 숫자', () => {
  for (const r of rejects) assert.deepEqual(parseOrder(r.text).tel, r.tel, r.name);
});

test('빈 글자', () => {
  assert.deepEqual(parseOrder(''), { tel: [], time: '', depart: '', cremate: '', price: null, memo: '' });
});
