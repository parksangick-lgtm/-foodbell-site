// api/read-note.js 시험 — 바깥(Firestore · 클로드)은 가짜로 끼운다. 실행: node --test "tools/sije_web/js-tests/*.test.mjs"
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { makeHandlers } from '../../../api/read-note.js';

const FIELDS = ['staff', 'car', 'leave', 'time', 'place', 'tel', 'work', 'people', 'price', 'lead', 'lead_tel', 'hall', 'depart', 'cremate', 'memo'];
const EMAIL = 'fake@example.com';
const MIDDLE = Buffer.from(JSON.stringify({ email: EMAIL })).toString('base64url');
const TOKEN = '가짜헤더.' + MIDDLE + '.서명';
const IMAGE = Buffer.from('가짜사진 글자').toString('base64');
const KEY = '가짜열쇠';
const DAY = '2026-11-04';
const FS_URL = 'https://firestore.googleapis.com/v1/projects/foodbell-sije/databases/(default)/documents/allow/fake%40example.com';

const row = (o = {}) => ({ ...Object.fromEntries(FIELDS.map((f) => [f, ''])), unsure: [], ...o });
const ANSWER = {
  day: DAY,
  rows: [row({ staff: '가짜담당', time: '09:40', place: '가짜장소', tel: '상주 010-0000-1234', price: '35만', unsure: ['tel'] })],
  note: '가짜 메모',
};
const BODY = JSON.stringify({ image: IMAGE, hints: { staff: ['가짜담당'], places: ['가짜장소'] }, day: DAY });

// 진짜 Request 머리에는 한글 토큰을 못 넣는다(ByteString 오류) — 기능이 쓰는 것(머리 읽기 · 몸통 글)만 흉내 낸다
function req({ auth = 'Bearer ' + TOKEN, body = BODY } = {}) {
  return {
    method: 'POST',
    url: 'https://foodbell.kr/api/read-note',
    headers: { get: (k) => (k.toLowerCase() === 'authorization' && auth !== null ? auth : null) },
    text: async () => body,
  };
}

// 가짜 바깥: fsStatus = Firestore 답 번호('throw' 면 연결 끊김), reply = 클로드 답, fail = 클로드가 던질 오류
function setup({ key = KEY, fsStatus = 200, answer = ANSWER, reply, fail, logs = [] } = {}) {
  const calls = { fetch: [], keys: [], claude: [], logs };
  const h = makeHandlers({
    env: key ? { ANTHROPIC_API_KEY: key } : {},
    fetch: async (url, init) => {
      calls.fetch.push({ url, init });
      if (fsStatus === 'throw') throw new TypeError('fetch failed');
      return new Response('{}', { status: fsStatus });
    },
    anthropic: async (apiKey) => {
      calls.keys.push(apiKey);
      return { beta: { messages: { create: async (params, options) => {
        calls.claude.push({ params, options });
        if (fail) throw fail;
        return reply ?? { stop_reason: 'end_turn', content: [{ type: 'text', text: JSON.stringify(answer) }], usage: { input_tokens: 1500, output_tokens: 300 } };
      } } } };
    },
    log: (...a) => calls.logs.push(a),
  });
  return { h, calls };
}

async function post(opts = {}, r = {}) {
  const { h, calls } = setup(opts);
  const res = await h.POST(req(r));
  return { res, body: await res.json(), calls };
}

// 정확히 n 글자인 올바른 몸통
function bodyOfLength(n) {
  const base = JSON.stringify({ image: '', hints: {}, day: DAY });
  return JSON.stringify({ image: 'A'.repeat(n - base.length), hints: {}, day: DAY });
}

// SDK 1.4.0 의 시간 초과 오류처럼 — name 은 'Error' 그대로이고 클래스 이름만 다르다(2026-11-03 실제 부품으로 확인)
class APIConnectionTimeoutError extends Error {}
const apiError = (status, message) => Object.assign(new Error(`${status} ${message}`), { status });

test('get_ready_follows_key — 열쇠가 없으면 ready:false, 있으면 ready:true', async () => {
  for (const [key, ready] of [[null, false], ['', false], [KEY, true]]) {
    const { h } = setup({ key });
    const res = await h.GET({ method: 'GET', url: 'https://foodbell.kr/api/read-note', headers: { get: () => null } });
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { ready });
  }
});

test('post_without_token_is_401 — 로그인 표가 없으면 401 login, Firestore · 클로드 안 부름', async () => {
  for (const auth of [null, '', 'Bearer ', 'Basic ' + TOKEN, 'Bearer 메일없는토큰']) {
    const { res, body, calls } = await post({}, { auth });
    assert.equal(res.status, 401, String(auth));
    assert.deepEqual(body, { error: 'login' });
    assert.equal(calls.fetch.length, 0);
    assert.equal(calls.claude.length, 0);
  }
  // 토큰이 풀렸으면(Firestore 401) 거절이 아니라 다시 로그인
  const { res, body, calls } = await post({ fsStatus: 401 });
  assert.equal(res.status, 401);
  assert.deepEqual(body, { error: 'login' });
  assert.equal(calls.claude.length, 0);
});

test('post_non_owner_is_403 — 허락 목록에 없으면(Firestore 404 · 403) 403 denied', async () => {
  for (const fsStatus of [404, 403]) {
    const { res, body, calls } = await post({ fsStatus });
    assert.equal(res.status, 403, String(fsStatus));
    assert.deepEqual(body, { error: 'denied' });
    assert.equal(calls.keys.length + calls.claude.length, 0);
  }
  // Firestore 가 고장이거나 연결이 끊기면 '쓸 수 없는 계정' 이 아니라 failed
  for (const fsStatus of [500, 'throw']) {
    const { res, body, calls } = await post({ fsStatus });
    assert.equal(res.status, 502, String(fsStatus));
    assert.deepEqual(body, { error: 'failed' });
    assert.equal(calls.claude.length, 0);
  }
});

test('post_too_big_is_413 — 4,000,001자 몸통은 413, Firestore 안 부름', async () => {
  const big = await post({}, { body: bodyOfLength(4_000_001) });
  assert.equal(big.res.status, 413);
  assert.deepEqual(big.body, { error: 'too-big' });
  assert.equal(big.calls.fetch.length, 0);
  assert.equal(big.calls.claude.length, 0);
  const edge = await post({}, { body: bodyOfLength(4_000_000) });   // 딱 4,000,000자는 통과
  assert.equal(edge.res.status, 200);
});

test('post_without_key_is_503 — 주인이지만 열쇠가 없으면 503 not-ready', async () => {
  const { res, body, calls } = await post({ key: null });
  assert.equal(res.status, 503);
  assert.deepEqual(body, { error: 'not-ready' });
  assert.equal(calls.fetch.length, 1);                 // 주인 확인은 했다
  assert.equal(calls.keys.length + calls.claude.length, 0);
});

test('post_owner_returns_rows — 주인이면 클로드에 사진 · 지시 · 이름 목록을 보내고 답을 돌려준다', async () => {
  const { res, body, calls } = await post();
  assert.equal(res.status, 200);
  assert.deepEqual(body, ANSWER);

  assert.equal(calls.fetch.length, 1);
  assert.equal(calls.fetch[0].url, FS_URL);
  assert.equal(calls.fetch[0].init.headers.Authorization, 'Bearer ' + TOKEN);
  assert.deepEqual(calls.keys, [KEY]);

  assert.equal(calls.claude.length, 1);
  const { params, options } = calls.claude[0];
  assert.equal(params.model, 'claude-opus-5-5');
  assert.equal(params.max_tokens, 16000);
  assert.deepEqual(params.betas, ['server-side-fallback-2026-07-01']);
  assert.equal(params.fallbacks, 'default');
  assert.equal(params.output_config.effort, 'medium');
  assert.equal(params.output_config.format.type, 'json_schema');
  const schema = params.output_config.format.schema;
  assert.equal(schema.additionalProperties, false);
  assert.deepEqual(schema.required, ['day', 'rows', 'note']);
  assert.equal(schema.properties.rows.items.additionalProperties, false);
  assert.deepEqual([...schema.properties.rows.items.required].sort(), [...FIELDS, 'unsure'].sort());
  assert.ok(typeof params.system === 'string' && params.system.includes('unsure'));

  const [image, text] = params.messages[0].content;
  assert.equal(params.messages[0].role, 'user');
  assert.deepEqual(image, { type: 'image', source: { type: 'base64', media_type: 'image/jpeg', data: IMAGE } });
  assert.equal(text.type, 'text');
  assert.ok(text.text.includes('가짜담당'), '담당 이름 목록');
  assert.ok(text.text.includes('가짜장소'), '장소 이름 목록');
  assert.ok(text.text.includes(DAY), '일정표 날짜');
  assert.deepEqual(options, { timeout: 55000, maxRetries: 0 });
});

test('rejects_unknown_fields — 스키마 밖 칸은 빼고, 글자가 아닌 값은 빈 글자로', async () => {
  const answer = {
    day: 5, extra: 'y', note: null,
    rows: [{ ...row({ staff: '가짜담당' }), secret: 'x', price: 35, tel: null, unsure: ['tel', 'secret', 3] }, '줄 아님'],
  };
  const { res, body } = await post({ answer });
  assert.equal(res.status, 200);
  assert.deepEqual(Object.keys(body).sort(), ['day', 'note', 'rows']);
  assert.equal(body.day, '');
  assert.equal(body.note, '');
  assert.equal(body.rows.length, 1);
  const [r] = body.rows;
  assert.deepEqual(Object.keys(r).sort(), [...FIELDS, 'unsure'].sort());
  assert.equal(r.staff, '가짜담당');
  assert.equal(r.price, '');
  assert.equal(r.tel, '');
  assert.deepEqual(r.unsure, ['tel']);
});

test('refusal_is_502 — 클로드가 거절하면 502 refusal', async () => {
  const refused = await post({ reply: { stop_reason: 'refusal', content: [], usage: { input_tokens: 10, output_tokens: 0 } } });
  assert.equal(refused.res.status, 502);
  assert.deepEqual(refused.body, { error: 'refusal' });
  // 답이 JSON 이 아니면 failed
  const garbled = await post({ reply: { stop_reason: 'end_turn', content: [{ type: 'text', text: '가짜 글' }], usage: {} } });
  assert.equal(garbled.res.status, 502);
  assert.deepEqual(garbled.body, { error: 'failed' });
});

test('anthropic_errors_map — 클로드 오류마다 알맞은 번호', async () => {
  const cases = [
    [new APIConnectionTimeoutError('Request timed out.'), 504, 'timeout'],
    [Object.assign(new Error('Request timed out.'), { name: 'APIConnectionTimeoutError' }), 504, 'timeout'],
    [apiError(429, 'rate_limit_error'), 429, 'busy'],
    [apiError(400, '{"type":"error","error":{"type":"invalid_request_error","message":"Your credit balance is too low to access the Anthropic API."}}'), 402, 'limit'],
    [apiError(400, '{"type":"error","error":{"type":"invalid_request_error","message":"You have reached your specified API usage limits."}}'), 402, 'limit'],
    [apiError(402, 'billing_error'), 402, 'limit'],
    [apiError(401, 'authentication_error'), 503, 'not-ready'],
    [apiError(400, 'invalid_request_error'), 502, 'failed'],
    [apiError(500, 'api_error'), 502, 'failed'],
    [new Error('가짜 오류'), 502, 'failed'],
  ];
  for (const [fail, status, error] of cases) {
    const { res, body } = await post({ fail });
    assert.equal(res.status, status, fail.message);
    assert.deepEqual(body, { error }, fail.message);
  }
});

test('logs_hold_no_content — 기록에는 숫자(status · ms · in · out)만, 사진 · 메일 · 토큰 · 결과 없음', async () => {
  const logs = [];
  const runs = [
    [{}, { auth: null }],
    [{ fsStatus: 404 }, {}],
    [{ fsStatus: 'throw' }, {}],
    [{}, { body: bodyOfLength(4_000_001) }],
    [{}, { body: '{"image":' }],
    [{ key: null }, {}],
    [{}, {}],
    [{ reply: { stop_reason: 'refusal', content: [], usage: {} } }, {}],
    [{ fail: new APIConnectionTimeoutError('Request timed out.') }, {}],
    [{ fail: apiError(400, `credit balance — ${EMAIL} ${IMAGE}`) }, {}],
  ];
  const statuses = [];
  for (const [opts, r] of runs) {
    const { h } = setup({ ...opts, logs });
    statuses.push((await h.POST(req(r))).status);
  }
  assert.deepEqual(statuses, [401, 403, 502, 413, 400, 503, 200, 502, 504, 402]);
  assert.equal(logs.length, runs.length, '요청마다 한 줄');
  logs.forEach((args, i) => {
    assert.equal(args.length, 1);
    const [entry] = args;
    assert.deepEqual(Object.keys(entry).sort(), ['in', 'ms', 'out', 'status']);
    for (const v of Object.values(entry)) assert.equal(typeof v, 'number');
    assert.equal(entry.status, statuses[i]);
    const s = JSON.stringify(args);
    for (const secret of [IMAGE, EMAIL, TOKEN, MIDDLE, KEY, '가짜담당', '가짜장소', '가짜 메모', 'credit']) {
      assert.ok(!s.includes(secret), `${i}번 기록에 ${secret.slice(0, 12)}…`);
    }
  });
  assert.deepEqual({ in: logs[6][0].in, out: logs[6][0].out }, { in: 1500, out: 300 }, '정상 답의 토큰 수');
});
