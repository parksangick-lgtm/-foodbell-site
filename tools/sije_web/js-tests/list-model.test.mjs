// 시제행사 목록 정렬 · 검색 — 오늘 이후는 가까운 순으로 먼저, 지난 행사는 최근 순으로 아래 / 이름 · 장소 · 전화로 거르기
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { splitRows, matchRow, todayISO } from '../../../js/sije/list-model.js';

const row = (id, date, time = '') => ({ id, ev: { date, time } });
const ids = (rows) => rows.map((r) => r.id);

test('splitRows — 오늘 포함 이후는 가까운 날짜 순, 지난 것은 최근 순', () => {
  const rows = [
    row('past-old', '2026-09-01'), row('next', '2026-11-20'), row('today', '2026-11-01'),
    row('past-new', '2026-10-25'), row('soon', '2026-11-05'),
  ];
  const { upcoming, past } = splitRows(rows, '2026-11-01');
  assert.deepEqual(ids(upcoming), ['today', 'soon', 'next']);
  assert.deepEqual(ids(past), ['past-new', 'past-old']);
});

test('splitRows — 날짜 없는 행사는 다가오는 쪽 맨 끝, 같은 날은 시간 순', () => {
  const rows = [
    row('none', ''), row('b', '2026-11-05', '14시'), row('a', '2026-11-05', '10시'),
    row('p2', '2026-10-20', '13시'), row('p1', '2026-10-20', '09시'),
  ];
  const { upcoming, past } = splitRows(rows, '2026-11-01');
  assert.deepEqual(ids(upcoming), ['a', 'b', 'none']);
  assert.deepEqual(ids(past), ['p1', 'p2']);
});

test('splitRows — 지난 행사가 없으면 past 는 빈 배열, 원본은 안 바뀐다', () => {
  const rows = [row('b', '2026-11-20'), row('a', '2026-11-05')];
  const { upcoming, past } = splitRows(rows, '2026-11-01');
  assert.deepEqual(ids(upcoming), ['a', 'b']);
  assert.deepEqual(past, []);
  assert.deepEqual(ids(rows), ['b', 'a']);
});

test('matchRow — 이름 · 장소 · 제목 장소 · 전화에 글자가 들어 있으면 보인다', () => {
  const ev = { customer: '가짜 문중', place: '가짜동 1-1 놀이터 위', titlePlace: '가짜동 1-1', contacts: ['010-0000-0000'] };
  assert.equal(matchRow(ev, '문중'), true);
  assert.equal(matchRow(ev, '놀이터'), true);
  assert.equal(matchRow(ev, '가짜동 1-1'), true);
  assert.equal(matchRow(ev, '없는글자'), false);
});

test('matchRow — 전화는 하이픈 · 공백을 무시하고, 대소문자도 무시한다', () => {
  const ev = { customer: 'Abc 문중', place: '', titlePlace: '', contacts: ['010-0000-0000'] };
  assert.equal(matchRow(ev, '01000000000'), true);
  assert.equal(matchRow(ev, '0000 0000'), true);
  assert.equal(matchRow(ev, '010-0000'), true);
  assert.equal(matchRow(ev, 'abc'), true);
  assert.equal(matchRow(ev, 'ABC문중'), true);
});

test('matchRow — 빈 검색(공백만)은 전부, 칸이 비어 있어도 죽지 않는다', () => {
  assert.equal(matchRow({ customer: '가짜 문중' }, ''), true);
  assert.equal(matchRow({ customer: '가짜 문중' }, '   '), true);
  assert.equal(matchRow({}, '문중'), false);
  assert.equal(matchRow({ contacts: null }, '010'), false);
});

test('todayISO — 기기 시각(로컬)의 YYYY-MM-DD', () => {
  assert.equal(todayISO(new Date(2026, 10, 1, 23, 59)), '2026-11-01');
  assert.equal(todayISO(new Date(2026, 0, 5)), '2026-01-05');
});
