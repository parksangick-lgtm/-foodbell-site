// js/docs/cards.js 시험 — 일일 일정표 직원 사진(휴대폰 카드)의 줄 만들기 · 보냄 표시 (설계 2026-10-24 2절)
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cardLines, stampText, STAFF_NOTE, STAFF_LIKE, SHOT_W, SHOT_H } from '../../../js/docs/cards.js';

test('카드 줄 — 머리 · 출발 · 장소 · 연락처 · 행사 · 금액 · 팀장 · 안내 · 장례 · 메모 순, 빈 칸은 뺌', () => {
  const lines = cardLines({ no: 2, staff: '박○○', car: '스타렉스', leave: '06:30 가게', time: '11시20분', place: '가짜추모공원',
    tel: '상주 010-0000-0003', work: '평토상', amt: '350,000원', lead: '가짜팀장', leadTel: '010-0000-0005', guideTel: '',
    hall: '가짜장례식장 3호실', depart: '오전 7시', cremate: '9시 30분', memo: '첫 줄\n둘째 줄', map: 'https://naver.me/x' });
  assert.deepEqual(lines, [
    { lab: '', text: '2번 · 11시20분 · 박○○ · 스타렉스' }, { lab: '출발', text: '06:30 가게' }, { lab: '장소', text: '가짜추모공원' },
    { lab: '연락처', text: '상주 010-0000-0003' }, { lab: '행사', text: '평토상' }, { lab: '금액', text: '350,000원' },
    { lab: '팀장', text: '가짜팀장 010-0000-0005' }, { lab: '장례', text: '가짜장례식장 3호실 · 발인 오전 7시 · 화장 9시 30분' },
    { lab: '메모', text: '첫 줄\n둘째 줄' }]);
});

test('안내 전화만 있으면 안내 줄, 팀장 전화만 있으면 팀장 줄', () => {
  assert.deepEqual(cardLines({ no: 1, guideTel: '010-0000-0002' }), [{ lab: '', text: '1번' }, { lab: '안내', text: '010-0000-0002' }]);
  assert.deepEqual(cardLines({ no: 1, leadTel: '010-0000-0005' }), [{ lab: '', text: '1번' }, { lab: '팀장', text: '010-0000-0005' }]);
});

test('빈 줄은 머리(번호)만', () => {
  assert.deepEqual(cardLines({ no: 4 }), [{ lab: '', text: '4번' }]);
});

test('보냄 표시', () => {
  const d = new Date(2026, 9, 24, 19, 32);
  assert.equal(stampText(0, d), '10-24 19:32 만듦');
  assert.equal(stampText(2, d), '10-24 19:32 보냄 · 2차');
  assert.equal(stampText(1, new Date(2026, 0, 3, 7, 5)), '01-03 07:05 보냄 · 1차');
});

test('상수 — 아래 문구 두 줄, 사진 폭 540 · 한 장 960', () => {
  assert.equal(STAFF_NOTE, "전화 · 지도는 홈 화면의 '푸드벨 일정' 아이콘을 누르세요");
  assert.equal(STAFF_LIKE, '확인했으면 사진을 길게 눌러 👍 해 주세요');
  assert.deepEqual([SHOT_W, SHOT_H], [540, 960]);
});
