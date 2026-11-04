// doc-page.js 가 store.js 를 판 번호(?v=)를 붙여 부르는지 — 실행: node --test "tools/sije_web/js-tests/*.test.mjs"
// 붙이지 않으면 배포 직후 신호가 약한 곳에서 새 doc-page.js 와 휴대폰에 남은 옛 store.js 가 섞여,
// 새로 더한 이름(idToken · recentDocs)을 못 찾고 서류 6종이 통째로 안 뜬다 (2026-11-03 사진으로 채우기 최종 검토)
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';

const SRC = readFileSync(new URL('../../../js/docs/doc-page.js', import.meta.url), 'utf8');

test('doc_page_imports_store_with_version', () => {
  assert.match(SRC, /from '\.\.\/sije\/store\.js\?v=\d+'/);
});

// 같은 모듈을 서로 다른 주소(번호 있음 · 없음 · 다른 번호)로 부르면 한 화면에 두 번 실려 상태(로그인 · 저장소 연결)가 갈라지고,
// 번호 없는 쪽은 휴대폰에 남은 옛 사본이 나갈 수 있다 (기록장 #78 · #82-7). 그래서 아래 모듈은 부르는 곳 모두가 한 주소다.
// 모듈을 고치면 이 주소의 번호를 부르는 곳 전부에서 같이 올린다.
const ROOT = new URL('../../../', import.meta.url);
const SHARED = ['js/sije/model.js', 'js/sije/store.js', 'js/sije/share-store.js'];
const SPEC = /(?:\bfrom\s*|\bimport\s*\(\s*)['"](\.[^'"]+)['"]/g;

function importers() {
  const files = [
    ...readdirSync(ROOT).filter((f) => f.endsWith('.html')),
    ...['js/sije/', 'js/docs/'].flatMap((d) => readdirSync(new URL(d, ROOT)).filter((f) => f.endsWith('.js')).map((f) => d + f)),
  ];
  const seen = Object.fromEntries(SHARED.map((m) => [m, []]));
  for (const f of files) {
    const at = new URL(f, ROOT);
    for (const [, spec] of readFileSync(at, 'utf8').matchAll(SPEC)) {
      const u = new URL(spec, at);
      const path = u.pathname.slice(ROOT.pathname.length);
      if (path in seen) seen[path].push(`${f} → ${spec}`);
    }
  }
  return seen;
}

test('shared_modules_have_one_versioned_address', () => {
  const seen = importers();
  assert.ok(seen['js/sije/model.js'].length >= 5, `model.js 를 부르는 곳을 못 찾음 — 찾는 방법이 고장: ${seen['js/sije/model.js']}`);
  for (const [mod, where] of Object.entries(seen)) {
    assert.ok(where.length > 0, `${mod} 를 부르는 곳이 없다`);
    const addrs = new Set(where.map((w) => new URL(w.split(' → ')[1], 'http://x/').search));
    assert.equal(addrs.size, 1, `${mod} 를 서로 다른 주소로 부른다:\n${where.join('\n')}`);
    assert.match([...addrs][0], /^\?v=\d+$/, `${mod} 에 판 번호(?v=)가 없다:\n${where.join('\n')}`);
  }
});
