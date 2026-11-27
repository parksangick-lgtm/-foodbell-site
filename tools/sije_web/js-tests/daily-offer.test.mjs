// 일일 일정표 '새 일정표를 만들 때 확정 행사를 불러올지 묻기' (2026-11-28) — 실행: node --test "tools/sije_web/js-tests/*.test.mjs"
// 일정표 화면은 공통 부품(js/docs/doc-page.js)이 이 탭에 적어 두는 '새 서류' 표시를 읽어 '방금 새로 만든 일정표'인지 안다.
// 공통 부품을 안 고치려고 표시 이름을 일정표 쪽에 한 번 더 적었다 — 한쪽만 바뀌면 묻는 창이 조용히 안 뜬다. 그래서 둘을 견준다.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const read = (name) => readFileSync(fileURLToPath(new URL(`../../../${name}`, import.meta.url)), 'utf8');
const literal = (src, name) => new RegExp(`const ${name} = '([^']+)'`).exec(src)?.[1];

test("일정표가 읽는 '새 서류' 표시 이름이 공통 부품이 적는 이름과 같다", () => {
  const made = literal(read('js/docs/doc-page.js'), 'FRESH');
  const seen = literal(read('daily-schedule.html'), 'FRESH_KEY');
  assert.ok(made && made.endsWith(':'), `공통 부품의 FRESH 를 못 찾음: ${made}`);
  assert.equal(seen, made);
});

test('대조 — 다른 이름표를 넣으면 못 찾는다(찾기가 아무거나 통과시키지 않는다)', () => {
  assert.equal(literal(read('daily-schedule.html'), 'NO_SUCH_KEY_ZZ9'), undefined);
});
