// js/docs/doc-model.js 시험 — 실행: node --test "tools/sije_web/js-tests/*.test.mjs"
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { KINDS, sortDocs, listOrder, editedText, rowCells, filterDocs } from '../../../js/docs/doc-model.js';

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

// 일정표 목록만 일정 날짜 순 (2026-11-18 보완 6번) — 지난주 일정표를 고쳐도 맨 위로 오지 않게.
// 날짜는 목록 줄의 label('2026년 11월 19일 (목)')에서 4자리 연도 · 월 · 일로 읽는다. 못 읽으면 맨 위, 같은 날짜면 최근에 고친 것이 위.
const at = (iso) => ({ toDate: () => new Date(iso) });   // 저장소 Timestamp 모양
const DAYS = [
  { id: 'nov10', doc: { label: '2026년 11월 10일 (화)', updatedAt: at('2026-11-17T09:00:00Z') } },   // 지난 날짜를 가장 늦게 고침
  { id: 'nov19a', doc: { label: '2026년 11월 19일 (목)', updatedAt: at('2026-11-15T09:00:00Z') } },
  { id: 'nodate', doc: { label: '날짜 미정', updatedAt: at('2026-11-01T09:00:00Z') } },
  { id: 'nov19b', doc: { label: '2026년 11월 19일 (목)', updatedAt: at('2026-11-16T09:00:00Z') } },
  { id: 'dec1', doc: { label: '2026년 12월 1일 (화)', updatedAt: at('2026-11-02T09:00:00Z') } },        // 월이 한 자리 · 두 자리 섞여도
  { id: 'y2025', doc: { label: '2025년 12월 31일 (수)', updatedAt: at('2026-11-18T09:00:00Z') } },
];

test('일정표 목록은 일정 날짜 순 — 늦은 날짜가 위, 못 읽는 날짜는 맨 위, 같은 날짜면 최근에 고친 것이 위', () => {
  assert.deepEqual(listOrder('daily-schedule', DAYS).map((r) => r.id), ['nodate', 'dec1', 'nov19b', 'nov19a', 'nov10', 'y2025']);
});

test('일정표 목록 — 방금 만든 것(고친 시각 없음)은 같은 날짜 안에서 맨 위, 받은 줄 묶음은 그대로 둔다', () => {
  const rows = [
    { id: 'old', doc: { label: '2026년 11월 19일 (목)', updatedAt: at('2026-11-16T09:00:00Z') } },
    { id: 'fresh', doc: { label: '2026년 11월 19일 (목)' } },
  ];
  assert.deepEqual(listOrder('daily-schedule', rows).map((r) => r.id), ['fresh', 'old']);
  assert.deepEqual(rows.map((r) => r.id), ['old', 'fresh']);
});

test('다른 서류 목록은 지금처럼 최근에 고친 순 (대조)', () => {
  for (const kind of ['sije-quote', 'event-quote', 'sije-worksheet', 'statement', 'staff-pay']) {
    assert.deepEqual(listOrder(kind, DAYS).map((r) => r.id), sortDocs(DAYS).map((r) => r.id), kind);
  }
  assert.deepEqual(sortDocs(DAYS).map((r) => r.id), ['y2025', 'nov10', 'nov19b', 'nov19a', 'dec1', 'nodate']);
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
