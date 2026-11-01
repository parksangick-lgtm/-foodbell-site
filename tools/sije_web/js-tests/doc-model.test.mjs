// js/docs/doc-model.js 시험 — 실행: node --test "tools/sije_web/js-tests/*.test.mjs"
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { KINDS, sortDocs, editedText, rowCells, filterDocs } from '../../../js/docs/doc-model.js';

test('서류 여섯 종류의 목록 제목과 이름', () => {
  assert.deepEqual(KINDS, {
    'sije-quote': { title: '시제 견적서', noun: '견적서' },
    'event-quote': { title: '행사 견적서', noun: '견적서' },
    'sije-worksheet': { title: '시제 작업지시서', noun: '작업지시서' },
    'statement': { title: '거래명세서', noun: '거래명세서' },
    'staff-pay': { title: '알바비 지급내역서', noun: '지급내역서' },
    'daily-schedule': { title: '일일 일정표', noun: '일정표' },
  });
});

test('일정표 줄 = 날짜(요일) · 건수 · 빈칸', () => {
  assert.deepEqual(rowCells('daily-schedule', { label: '2026년 10월 21일 (수)', count: '3건' }),
    ['2026년 10월 21일 (수)', '3건', '']);
  assert.deepEqual(rowCells('daily-schedule', {}), ['(날짜 없음)', '0건', '']);
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

// 목록 검색 (사장님 2026-11-01 공통 11) — 읽어 온 줄 안에서만, 공백 · 하이픈 · 대소문자 무시
const ROWS = [
  { id: 'a', doc: { kind: 'statement', html: '<p>본문 글</p>', label: '가짜동 매화 문중', issue: '2026년 10월 15일', total: '1,000' } },
  { id: 'b', doc: { kind: 'statement', html: '<p>본문 글</p>', label: '가짜동 소나무 문중', issue: '2026년 10월 16일', total: '2,000' } },
  { id: 'c', doc: { kind: 'staff-pay', html: '', issue: '2026년 10월 3일', total: '450,000', count: '3명' } },
];

test('filterDocs — 손님 이름 · 날짜 글자로 거른다', () => {
  assert.deepEqual(filterDocs(ROWS, 'statement', '매화').map((r) => r.id), ['a']);
  assert.deepEqual(filterDocs(ROWS, 'statement', '10월 16일').map((r) => r.id), ['b']);
  assert.deepEqual(filterDocs(ROWS, 'staff-pay', '3명').map((r) => r.id), ['c']);
});

test('filterDocs — 공백 · 하이픈 · 대소문자는 무시, 빈 검색은 전부', () => {
  assert.deepEqual(filterDocs(ROWS, 'statement', '2026년10월15일').map((r) => r.id), ['a']);
  assert.deepEqual(filterDocs(ROWS, 'statement', '10월-15-일').map((r) => r.id), ['a']);
  assert.deepEqual(filterDocs([{ id: 'x', doc: { label: 'ABC 문중' } }], 'statement', 'abc').map((r) => r.id), ['x']);
  assert.equal(filterDocs(ROWS, 'statement', ''), ROWS);
  assert.equal(filterDocs(ROWS, 'statement', '  '), ROWS);
  assert.equal(filterDocs(ROWS, 'statement', undefined), ROWS);
});

test('filterDocs — 서류 본문(html) · 종류(kind) 글자로는 안 걸린다', () => {
  assert.deepEqual(filterDocs(ROWS, 'statement', '본문'), []);
  assert.deepEqual(filterDocs(ROWS, 'statement', 'statement'), []);
});
