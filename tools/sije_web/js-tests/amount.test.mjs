// 일일 일정표 인원 · 단가 읽기 — 손으로 친 글자에서 숫자 하나만, 애매하면 null (틀린 금액을 직원에게 보내지 않게)
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readNumber } from '../../../js/docs/amount.js';

test('흔히 치는 모양은 그 숫자', () => {
  for (const [s, want] of [['60명', 60], ['15,000원', 15000], ['15000', 15000], ['약 60명', 60], ['1,500,000원', 1500000]]) {
    assert.equal(readNumber(s), want, s);
  }
});

test('만 · 천 단위를 읽는다', () => {
  for (const [s, want] of [['2만', 20000], ['2만원', 20000], ['1만5천원', 15000], ['1만 5천', 15000],
    ['1.5만', 15000], ['5천원', 5000], ['1만5천500원', 15500]]) {
    assert.equal(readNumber(s), want, s);
  }
});

test('1인 · 1인당 은 단가 앞뒤 꾸밈말로 본다', () => {
  for (const [s, want] of [['1인 15,000원', 15000], ['15,000원(1인)', 15000], ['1인당 2만', 20000], ['11인', 11]]) {
    assert.equal(readNumber(s), want, s);
  }
});

test('숫자가 둘 이상이거나 범위면 모른다 (null)', () => {
  for (const s of ['60~70명', '60-70명', '3명+2명', '2만원 3명', '', '없음', null, undefined]) {
    assert.equal(readNumber(s), null, String(s));
  }
});
