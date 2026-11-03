// doc-page.js 가 store.js 를 판 번호(?v=)를 붙여 부르는지 — 실행: node --test "tools/sije_web/js-tests/*.test.mjs"
// 붙이지 않으면 배포 직후 신호가 약한 곳에서 새 doc-page.js 와 휴대폰에 남은 옛 store.js 가 섞여,
// 새로 더한 이름(idToken · recentDocs)을 못 찾고 서류 6종이 통째로 안 뜬다 (2026-11-03 사진으로 채우기 최종 검토)
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const SRC = readFileSync(new URL('../../../js/docs/doc-page.js', import.meta.url), 'utf8');

test('doc_page_imports_store_with_version', () => {
  assert.match(SRC, /from '\.\.\/sije\/store\.js\?v=\d+'/);
});
