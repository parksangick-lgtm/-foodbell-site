// 일일 일정표 '문자 붙여넣기' — 실제 카톡 주문 표본(이름 · 번호는 가짜)에서 시간 · 연락처 · 단가를 뽑는다
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { parseOrder } from '../../../js/docs/order-text.js';

const { samples, rejects } = JSON.parse(readFileSync(new URL('./fixtures/order-samples.json', import.meta.url), 'utf8'));

test('표본마다 사장님이 정한 칸 값', () => {
  for (const s of samples) {
    const got = parseOrder(s.text);
    console.log(`${s.name}\n  → 시간 '${got.time}' · 연락처 ${JSON.stringify(got.tel)} · 단가 ${got.price}`);   // 눈으로 본다
    assert.deepEqual({ tel: got.tel, time: got.time, price: got.price }, { tel: s.tel, time: s.time, price: s.price }, s.name);
  }
});

test('메모는 원문 그대로 (뽑은 것도 지우지 않음)', () => {
  for (const s of samples) assert.equal(parseOrder(s.text).memo, s.text, s.name);
  assert.equal(parseOrder('  가짜\r\n주문  ').memo, '가짜\n주문');
});

test('번호로 보면 안 되는 숫자', () => {
  for (const r of rejects) assert.deepEqual(parseOrder(r.text).tel, r.tel, r.name);
});

test('빈 글자', () => {
  assert.deepEqual(parseOrder(''), { tel: [], time: '', price: null, memo: '' });
});
