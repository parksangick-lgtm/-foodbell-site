// js/docs/paging.js 시험 — 일정표 사진 · 인쇄를 장마다 나눌 때 줄을 묶는 계산
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { pageGroups } from '../../../js/docs/paging.js';

test('한 장에 다 들어가면 한 묶음', () => {
  assert.deepEqual(pageGroups([10, 10, 10], 100, 100), [[0, 1, 2]]);
});

test('첫 장은 자리가 적고 다음 장은 많다 — 15줄이면 6줄 + 9줄', () => {
  const range = (a, b) => Array.from({ length: b - a + 1 }, (_, i) => a + i);
  assert.deepEqual(pageGroups(Array(15).fill(30), 200, 300), [range(0, 5), range(6, 14)]);
});

test('한 줄이 한 장보다 커도 그 줄 혼자 한 장 (줄을 가르지 않는다)', () => {
  assert.deepEqual(pageGroups([500], 200, 300), [[0]]);
  assert.deepEqual(pageGroups([50, 500, 50], 200, 300), [[0], [1], [2]]);
});

test('줄이 없으면 묶음도 없다', () => {
  assert.deepEqual(pageGroups([], 200, 300), []);
});
