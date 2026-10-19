// js/docs/lunar.js 시험 — 실행: node --test "tools/sije_web/js-tests/*.test.mjs"
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { lunarText } from '../../../js/docs/lunar.js';

test('음력 날짜 글자 (한국 음력 · 단기력)', () => {
  assert.equal(lunarText(new Date(2026, 9, 21)), '음력 9월 11일');
  assert.equal(lunarText(new Date(2025, 7, 23)), '음력 7월 1일');
  assert.equal(lunarText(new Date(2027, 1, 7)), '음력 1월 1일');     // 설
});

test('윤달은 윤 을 붙인다', () => {
  assert.equal(lunarText(new Date(2025, 6, 25)), '음력 윤6월 1일');
});

test('못 읽는 날짜면 빈 글자', () => {
  assert.equal(lunarText(new Date(NaN)), '');
  assert.equal(lunarText(null), '');
});
