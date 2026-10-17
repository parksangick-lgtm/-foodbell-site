// js/docs/doc-model.js 시험 — 실행: node --test "tools/sije_web/js-tests/*.test.mjs"
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { KINDS, sortDocs, editedText, rowCells } from '../../../js/docs/doc-model.js';

test('서류 다섯 종류의 목록 제목과 이름', () => {
  assert.deepEqual(KINDS, {
    'sije-quote': { title: '시제 견적서', noun: '견적서' },
    'event-quote': { title: '행사 견적서', noun: '견적서' },
    'sije-worksheet': { title: '시제 작업지시서', noun: '작업지시서' },
    'statement': { title: '거래명세서', noun: '거래명세서' },
    'staff-pay': { title: '알바비 지급내역서', noun: '지급내역서' },
  });
});

test('목록은 최근에 고친 순, 방금 이 기기에서 만든 것(시각 아직 없음)은 맨 위', () => {
  const rows = [
    { id: 'a', doc: { updatedAt: new Date('2026-10-15T05:00:00Z') } },
    { id: 'b', doc: { updatedAt: { toDate: () => new Date('2026-10-17T11:40:00Z') } } },   // 저장소 Timestamp 모양
    { id: 'c', doc: {} },
  ];
  assert.deepEqual(sortDocs(rows).map((r) => r.id), ['c', 'b', 'a']);
});

test('고친 시각 글자 — 오늘은 시:분, 같은 해는 월 일, 다른 해는 연도까지', () => {
  const now = new Date(2026, 9, 17, 21, 0);
  assert.equal(editedText(new Date(2026, 9, 17, 20, 40), now), '오늘 20:40 고침');
  assert.equal(editedText(new Date(2026, 9, 17, 9, 5), now), '오늘 09:05 고침');
  assert.equal(editedText(new Date(2026, 9, 15, 14, 2), now), '10월 15일 고침');
  assert.equal(editedText(new Date(2025, 9, 15, 9, 0), now), '2025년 10월 15일 고침');
});

test('고친 시각이 아직 없으면 방금 고침', () => {
  assert.equal(editedText(null, new Date(2026, 9, 17, 21, 0)), '방금 고침');
});

test('견적서 줄 = 구분값 · 발행일 · 합계(원)', () => {
  const doc = { label: '○○ 김씨 문중 종친회', issue: '2026년 10월 17일', total: '2,420,000' };
  assert.deepEqual(rowCells('sije-quote', doc), ['○○ 김씨 문중 종친회', '2026년 10월 17일', '2,420,000원']);
});

test('합계가 비면 -, 구분값이 비면 (이름 없음)', () => {
  assert.deepEqual(rowCells('statement', { label: '', issue: '', total: '' }), ['(이름 없음)', '', '-']);
});

test('알바비 줄 = 작성일 · 인원 · 총 지급액', () => {
  const doc = { label: '2026년 10월 3일', issue: '2026년 10월 3일', total: '450,000', count: '3명' };
  assert.deepEqual(rowCells('staff-pay', doc), ['2026년 10월 3일', '3명', '450,000원']);
  assert.deepEqual(rowCells('staff-pay', { issue: '2026년 10월 3일', total: '', count: '' }), ['2026년 10월 3일', '0명', '-']);
});
