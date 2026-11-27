// 전자명함(card.html · foodbell.vcf) 시험 — 실행: node --test "tools/sije_web/js-tests/*.test.mjs"
// 설계 docs/superpowers/specs/2026-11-27-ecard-design.md
// 명함과 사이트의 전화 · 문자 · 카카오톡 주소가 서로 달라지면 실패다. 그래서 주소를 여기 손으로 적지 않고
// index.html 에서 뽑아 card.html 것과 견준다 — 사이트 주소를 바꾸고 명함을 잊으면 이 시험이 잡는다.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const ROOT = new URL('../../../', import.meta.url);
const read = (f) => readFileSync(new URL(f, ROOT), 'utf8');

// 쪽 안의 href 가운데 start 로 시작하는 것 — 겹치는 것은 하나로, 글자 그대로(&amp; 도 풀지 않는다)
const hrefs = (html, start) => [...new Set([...html.matchAll(/href="([^"]*)"/g)].map((m) => m[1]).filter((h) => h.startsWith(start)))].sort();

for (const [name, start] of [['전화', 'tel:'], ['문자', 'sms:'], ['카카오톡', 'https://pf.kakao.com/']]) {
  test(`명함의 ${name} 주소는 index.html 과 글자 그대로 같다`, () => {
    const site = hrefs(read('index.html'), start);
    assert.equal(site.length, 1, `index.html 의 ${name} 주소가 하나가 아니다 — 찾는 방법이 고장이거나 사이트가 바뀜: ${site.join(' | ')}`);
    assert.deepEqual(hrefs(read('card.html'), start), site);
  });
}

test('foodbell.vcf 는 줄 끝이 CRLF 이고 BOM 이 없다', () => {
  const buf = readFileSync(new URL('foodbell.vcf', ROOT));
  assert.notDeepEqual([...buf.subarray(0, 3)], [0xEF, 0xBB, 0xBF], '맨 앞에 BOM 이 있다');
  const text = buf.toString('utf8');
  const count = (re) => (text.match(re) || []).length;
  assert.ok(count(/\r\n/g) >= 6, `줄 끝 CRLF 가 ${count(/\r\n/g)}개뿐 — 필수 칸 여섯 줄도 안 된다`);
  assert.equal(count(/(?<!\r)\n/g), 0, '맨 \\n(CR 없는 줄 끝)이 있다 — 편집 도구로 고치면 이렇게 된다');
  assert.equal(count(/\r(?!\n)/g), 0, '맨 \\r 이 있다');
  assert.ok(text.endsWith('\r\n'), '마지막 줄이 CRLF 로 끝나지 않는다');
});

// 위 시험은 작업 폴더의 파일만 본다. 이 저장소는 core.autocrlf 가 켜진 PC 에서 CRLF 를 LF 로 바꿔 저장하므로,
// 깃이 이 파일을 그대로 두게 하는 줄이 .gitattributes 에 있어야 서버에도 CRLF 로 올라간다 (2026-11-27)
test('.gitattributes 가 vcf 를 바꾸지 않고 그대로 저장하게 한다', () => {
  assert.match(read('.gitattributes'), /^\*\.vcf\s+-text\s*$/m);
});

test('foodbell.vcf 는 필수 칸을 갖췄고 EMAIL · ADR 은 없다', () => {
  const lines = read('foodbell.vcf').split('\r\n').filter((l) => l !== '');
  const has = (key) => lines.some((l) => new RegExp(`^${key}[;:]`, 'i').test(l));
  assert.equal(lines[0], 'BEGIN:VCARD');
  assert.equal(lines.at(-1), 'END:VCARD');
  assert.ok(lines.includes('VERSION:3.0'), 'VERSION:3.0 줄이 없다');
  for (const key of ['N', 'FN', 'TEL']) assert.ok(has(key), `${key} 칸이 없다`);
  for (const key of ['EMAIL', 'ADR']) assert.ok(!has(key), `${key} 칸이 있다 — 넣지 않기로 했다(설계서 4절)`);
});

// 가격 = '원' 이 붙은 숫자 (150,000원 · 15만원 · 5만 원)
const PRICE = /\d[\d,.]*\s*(?:천|만|억)?\s*원/;

test('가격 찾는 식은 가격만 잡는다 (대조)', () => {
  for (const s of ['150,000원', '15만원', '5만 원', '3천원']) assert.match(s, PRICE);
  for (const s of ['010-5353-3477', '원본 그대로', 'width 1200 height 630', '2026-11-27']) assert.doesNotMatch(s, PRICE);
});

test('card.html 에 가격(원 붙은 숫자)이 없다', () => {
  const hit = PRICE.exec(read('card.html'));
  assert.equal(hit, null, `가격처럼 보이는 글자: ${hit && hit[0]}`);
});

test('card.html 이 부르는 사진 · 미리보기 그림 파일이 있다', () => {
  const html = read('card.html');
  const files = [...html.matchAll(/<img\s[^>]*src="([^"?]+)/g)].map((m) => m[1]);
  const og = /property="og:image"\s+content="https:\/\/foodbell\.kr\/([^"]+)"/.exec(html);
  assert.ok(files.length >= 1, '명함에 사진(img)이 없다 — 사장님이 사진을 넣기로 했다(2026-11-27)');
  assert.ok(og, 'og:image 가 없다');
  for (const f of [...files, og[1]]) assert.ok(readFileSync(new URL(f, ROOT)).length > 10000, `${f} 가 없거나 너무 작다`);
});

test('card.html 은 검색에 안 잡히게 noindex 다', () => {
  assert.match(read('card.html'), /<meta\s+name="robots"\s+content="[^"]*\bnoindex\b[^"]*"\s*\/?>/i);
});
