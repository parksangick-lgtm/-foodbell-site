// js/docs/time-hint.js 시험 — 시간 칸에 오전 · 오후가 없을 때만 묻는다 (설계 2026-10-24 4절)
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { needsAmPm } from '../../../js/docs/time-hint.js';

for (const t of ['11시20분', '12시', '3시 도착', '11:20']) {
  test(`묻는다: ${t}`, () => assert.equal(needsAmPm(t), true));
}
for (const t of ['13:30', '오후 1시', '정오', '새벽 5시', '11시 am', '오전 11시', '', '15시 도착', '2026년 10월 25일']) {
  test(`안 묻는다: ${JSON.stringify(t)}`, () => assert.equal(needsAmPm(t), false));
}
