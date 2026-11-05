// 직원 '확인' 단추 — 담당 칸 이름 나누기 · 확인 판단 · 사장님 한 줄 (설계 2026-11-04 3-1 · 3-4). 이름은 모두 가짜
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { staffNames, confirmState, confirmLine } from '../../../js/docs/confirm.js';

const A = '가나다', B = '라마바', C = '사아자', D = '차카타';
const at = (h, m) => Date.UTC(2026, 10, 5, h, m);                    // 시험용 시각(ms)
const hhmm = (ms) => new Date(ms).toISOString().slice(11, 16);         // 시험용 'HH:MM' (UTC 로 고정)

test('나누는 글자 — 점 · 빗금 · 빈칸 · nbsp · 가운뎃점 · 、 · + · 쉼표', () => {
  for (const s of [`${A}.${B}`, `${A}/${B}`, `${A} ${B}`, `${A} ${B}`, `${A}·${B}`, `${A}、${B}`, `${A}+${B}`, `${A},${B}`]) {
    assert.deepEqual(staffNames(s), [A, B], s);
  }
});

test('나누는 글자가 여럿 붙거나 앞뒤에 있어도 빈 조각은 버린다', () => {
  assert.deepEqual(staffNames(` ${A} , ${B} ·· ${C}. `), [A, B, C]);
  assert.deepEqual(staffNames(` ${A}  / ${B}`), [A, B]);
});

test('괄호 안은 뺀다 — 반각 · 전각 · 닫지 않은 괄호(끝까지)', () => {
  assert.deepEqual(staffNames(`${A}(보조) ${B}`), [A, B]);
  assert.deepEqual(staffNames(`${A}(보조)${B}`), [A, B], '괄호 자리에서도 나뉜다');
  assert.deepEqual(staffNames(`${A}（보조）${B}`), [A, B]);
  assert.deepEqual(staffNames(`${A} ${B}(${C}. ${D}`), [A, B], '닫는 괄호가 없으면 끝까지 뺀다');
  assert.deepEqual(staffNames(`${A}(1차) ${B}(2차) ${C}`), [A, B, C], '괄호가 여럿');
});

test('같은 이름은 처음 하나만, 나온 순서대로', () => {
  assert.deepEqual(staffNames(`${A}.${B}.${A}`), [A, B]);
  assert.deepEqual(staffNames(`${D} ${A} ${D}/${B}`), [D, A, B]);
});

test('비었거나 이름이 없으면 빈 목록', () => {
  for (const s of ['', '   ', ' ', '(보조)', ' . / ', null, undefined]) {
    assert.deepEqual(staffNames(s), [], String(s));
  }
});

test('확인 판단 — 확인함 · 아직 · 고친 뒤 안 봄 · 아직 안 올라감, 목록에 없는 이름은 무시', () => {
  const entry = { at: at(7, 0), names: [A, B, C, D] };
  const marks = [
    { name: C, at: null },                // 눌렀는데 아직 서버에 안 감
    { name: B, at: at(6, 30) },           // 사장님이 고치기(7:00) 전에 봄
    { name: '파하가', at: at(7, 40) },     // 사장님이 담당에서 뺀 사람
    { name: A, at: at(7, 12) },
  ];
  assert.deepEqual(confirmState(entry, marks), {
    done: [{ name: A, at: at(7, 12) }],
    waiting: [D],
    stale: [B],
    pending: [C],
  });
});

test('확인함은 기록 순서가 아니라 이름 목록 순서', () => {
  const entry = { at: at(7, 0), names: [A, B] };
  const s = confirmState(entry, [{ name: B, at: at(7, 30) }, { name: A, at: at(7, 12) }]);
  assert.deepEqual(s.done, [{ name: A, at: at(7, 12) }, { name: B, at: at(7, 30) }]);
});

test('고친 시각과 같은 때 본 것은 확인함', () => {
  const s = confirmState({ at: at(7, 0), names: [A] }, [{ name: A, at: at(7, 0) }]);
  assert.deepEqual(s, { done: [{ name: A, at: at(7, 0) }], waiting: [], stale: [], pending: [] });
});

test('일정표 시각(entry.at)이 없으면 고친 뒤 안 봄은 없다', () => {
  const s = confirmState({ at: null, names: [A, B] }, [{ name: A, at: at(1, 0) }]);
  assert.deepEqual(s, { done: [{ name: A, at: at(1, 0) }], waiting: [B], stale: [], pending: [] });
});

test('이름 목록이 비었거나 일정표가 없으면 모두 빈 목록', () => {
  const empty = { done: [], waiting: [], stale: [], pending: [] };
  assert.deepEqual(confirmState({ at: at(7, 0), names: [] }, [{ name: A, at: at(7, 12) }]), empty);
  assert.deepEqual(confirmState({ at: at(7, 0) }, []), empty);
  assert.deepEqual(confirmState(null, null), empty);
});

test('사장님 한 줄 — 설계 3-4 의 글자 모양 그대로', () => {
  const entry = { at: at(7, 0), names: [A, B, C, D] };
  const marks = [{ name: A, at: at(7, 12) }, { name: B, at: at(7, 30) }, { name: D, at: at(6, 50) }];
  assert.equal(confirmLine(confirmState(entry, marks), hhmm),
    `직원 확인 2/4 · ${A} 07:12 · ${B} 07:30 · 아직: ${C} · ${D}(고친 뒤 안 봄)`);
});

test('사장님 한 줄 — 아직 안 올라간 사람도 아직에 들어간다', () => {
  const state = { done: [], waiting: [A], stale: [C], pending: [B] };
  assert.equal(confirmLine(state, hhmm), `직원 확인 0/3 · 아직: ${A} · ${B} · ${C}(고친 뒤 안 봄)`);
});

test('사장님 한 줄 — 모두 확인했으면 아직을 뺀다', () => {
  const entry = { at: at(7, 0), names: [A, B] };
  const marks = [{ name: A, at: at(7, 12) }, { name: B, at: at(7, 30) }];
  assert.equal(confirmLine(confirmState(entry, marks), hhmm), `직원 확인 2/2 · ${A} 07:12 · ${B} 07:30`);
});

test('사장님 한 줄 — 이름이 없으면 빈 글자', () => {
  assert.equal(confirmLine(confirmState({ at: at(7, 0), names: [] }, []), hhmm), '');
  assert.equal(confirmLine(confirmState(null, []), hhmm), '');
});
