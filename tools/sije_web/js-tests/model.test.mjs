// js/sije/model.js 시험 — 실행: node --test tools/sije_web/js-tests/
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  STATUSES, formatDateText, titleLine, itemKey, itemsBySide, newEventFromTemplate, newViewKey, viewLinkText,
} from '../../../js/sije/model.js';

test('상태 글자는 세 가지', () => {
  assert.deepEqual(STATUSES, ['확정', '미확정', '주문없음']);
});

test('날짜 글자에 요일과 시간이 붙는다', () => {
  assert.equal(formatDateText('2026-11-13', '10시'), '2026년 11월 13일 (금) 10시');
});

test('시간이 없으면 요일까지만', () => {
  assert.equal(formatDateText('2026-03-01', ''), '2026년 3월 1일 (일)');
});

test('맨 위 줄 = 주소 + 날짜 글자', () => {
  assert.equal(titleLine({ titlePlace: '가짜동 1-1', date: '2026-11-13', time: '10시' }),
    '가짜동 1-1 2026년 11월 13일 (금) 10시');
});

test('맨 위 줄은 앞뒤 공백을 정리한다', () => {
  assert.equal(titleLine({ titlePlace: '  가짜동 1-1 ', date: '2026-03-01', time: '' }),
    '가짜동 1-1 2026년 3월 1일 (일)');
});

test('품목 줄 이름은 쪽 + 두 자리 번호', () => {
  assert.equal(itemKey('L', 3), 'L03');
  assert.equal(itemKey('R', 12), 'R12');
});

test('품목은 왼쪽 · 오른쪽으로 나뉘고 줄 이름 순서', () => {
  const a = { name: 'a' }, b = { name: 'b' }, c = { name: 'c' };
  assert.deepEqual(itemsBySide({ R02: b, L01: a, R01: c }), { L: [a], R: [c, b] });
});

test('새 행사는 빈 양식에서 시작해 미확정', () => {
  const x = { group: '과일', no: '1', name: '배', qty: '5개', note: '' };
  const tpl = { name: '60만원상', items: { L01: x } };
  const ev = newEventFromTemplate(tpl);
  assert.equal(ev.status, '미확정');
  assert.equal(ev.templateType, '60만원상');
  assert.deepEqual(ev.items, { L01: x });
  assert.deepEqual(ev.contacts, []);
  assert.equal(ev.fileLabel, '');
  assert.equal(ev.memo, '');
  ev.items.L01.qty = '7개';
  assert.equal(tpl.items.L01.qty, '5개', '새 행사를 고쳐도 빈 양식은 그대로');
});

test('빈 양식에 type 이 있으면 머리글 상 종류는 그것 — 수량 없는 빈 양식은 빈 글자 (사장님 2026-10-26)', () => {
  assert.equal(newEventFromTemplate({ name: '빈 양식 (수량 없음)', type: '', items: {} }).templateType, '');
  assert.equal(newEventFromTemplate({ name: '60만원상', items: {} }).templateType, '60만원상');
});

test('새 행사는 빈 양식의 품목표 줄 수를 이어받는다', () => {
  assert.equal(newEventFromTemplate({ name: '60만원상', items: {}, itemRows: 17 }).itemRows, 17);
  assert.equal(newEventFromTemplate({ name: '60만원상', items: {} }).itemRows, 0);
});

test('담당자 링크 암호는 32글자 base64url 이고 매번 다르다', () => {
  const a = newViewKey(), b = newViewKey();
  assert.match(a, /^[A-Za-z0-9_-]{32}$/);
  assert.notEqual(a, b);
});

test('담당자 링크 공유 글은 세 줄', () => {
  const link = 'https://foodbell.kr/sije-view.html#' + 'a'.repeat(32);
  const ev = { date: '2026-10-31', time: '10시', titlePlace: '가짜동 1-1', place: '가짜동 1-1 뒷산' };
  assert.equal(viewLinkText(ev, link),
    `[푸드벨] 10월 31일 (토) 10시 가짜동 1-1 시제 내역서 (보기만)\n${link}\n행사 전날부터 당일까지 열려요.`);
  assert.equal(viewLinkText({ ...ev, titlePlace: '' }, link).split('\n')[0],
    '[푸드벨] 10월 31일 (토) 10시 가짜동 1-1 뒷산 시제 내역서 (보기만)');
  assert.equal(viewLinkText({ ...ev, date: '', time: '' }, link).split('\n')[0],
    '[푸드벨] 가짜동 1-1 시제 내역서 (보기만)');
});
