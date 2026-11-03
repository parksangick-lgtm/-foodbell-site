// 버셀 서버 기능 — 일일 일정표 '사진으로 채우기' (2026-11-03, 설계 docs/superpowers/specs/2026-11-03-daily-schedule-photo-fill-design.md 3-1 · 3-2)
// GET  /api/read-note → { ready } — 버셀에 ANTHROPIC_API_KEY 가 들어 있는지만(값은 안 알려 줌), 로그인 없이
// POST /api/read-note → 머리 Authorization: Bearer <파이어베이스 ID 토큰>, 몸통 { image: base64 JPEG, hints: { staff, places }, day }
//   → 200 { day, rows, note } · 오류 { error }: 401 login · 413 too-big · 400 bad-request · 403 denied · 503 not-ready
//     · 402 limit · 504 timeout · 429 busy · 502 refusal · 502 failed
// 서버 기록에는 숫자(상태 · 걸린 시간 · 토큰 수)만 — 사진 · 결과 · 메일 · 토큰 글자는 찍지 않는다.
// 시험: tools/sije_web/js-tests/read-note.test.mjs (바깥은 makeHandlers 에 가짜로 끼운다)
export const maxDuration = 60;

const FIELDS = ['staff', 'car', 'leave', 'time', 'place', 'tel', 'work', 'people', 'price', 'lead', 'lead_tel', 'hall', 'depart', 'cremate', 'memo'];
const MAX_BODY = 4_000_000;
const ALLOW_URL = 'https://firestore.googleapis.com/v1/projects/foodbell-sije/databases/(default)/documents/allow/';

// 구조화 출력 — 모든 칸 필수, 스키마 밖 칸 없음
export const NOTE_SCHEMA = {
  type: 'object',
  properties: {
    day: { type: 'string' },
    rows: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          ...Object.fromEntries(FIELDS.map((f) => [f, { type: 'string' }])),
          unsure: { type: 'array', items: { type: 'string', enum: FIELDS } },
        },
        required: [...FIELDS, 'unsure'],
        additionalProperties: false,
      },
    },
    note: { type: 'string' },
  },
  required: ['day', 'rows', 'note'],
  additionalProperties: false,
};

const SYSTEM = [
  '출장음식 업체 사장님이 다음 날 일을 적은 손글씨 노트 사진을 읽어, 일정표 칸에 나눠 담는다.',
  '- 일 하나 = rows 한 줄, 노트에 적힌 차례대로. 노트에 없는 칸은 "".',
  '- 칸: staff 담당 직원 · car 차량 · leave 출발 · time 시간 · place 장소 · tel 연락처 · work 행사 내용 · people 인원 · price 단가'
    + ' · lead 상조팀장 · lead_tel 팀장 전화 · hall 장례식장 · 화장장 · depart 발인 시간 · cremate 화장 시간 · memo 메모.',
  '- 시간은 HH:MM (14시 → 14:00, 9시40 → 09:40).',
  '- 전화는 010-1234-5678 모양. 여럿이면 " / " 로 잇고, 누구 번호인지 앞에 적는다(상주 010-…).',
  '- 단가는 적힌 그대로("35만", "15,000"). "60명×15,000" 은 people 60 · price 15,000.',
  '- 담당(staff)은 줄 오른쪽 끝 이름과 위쪽 담당자 번호표로 정한다.',
  '- 상조팀장(lead)은 "회사 + 이름"(○○상조 ○○○). 장례식장 · 화장장은 hall, 화장 시각은 cremate, 발인 시각은 depart.',
  '- 나머지(고인 이름, 밥 1개, 위치 메모 등)는 work 또는 memo.',
  '- 이름 목록: 장소 · 담당이 목록에 있는 이름과 비슷하면 목록 글자로 쓴다. 목록에 없으면 읽은 그대로 적고 그 칸을 unsure 에 넣는다.',
  '- 읽기 애매한 글자 · 숫자가 있는 칸은 반드시 unsure 에 칸 이름으로 넣는다. 지어내지 않는다 — 모르면 빈칸이 낫다.',
  '- day: 노트에 적힌 날짜를 YYYY-MM-DD 로(연도가 없으면 일정표 날짜의 연도). 노트에 날짜가 없으면 "".',
  '- note: 어느 칸에도 넣지 못한 글.',
].join('\n');

const str = (v) => (typeof v === 'string' ? v : '');
const names = (a) => (Array.isArray(a) ? a.filter((s) => typeof s === 'string').slice(0, 60).map((s) => s.slice(0, 40)) : []);

// 토큰 가운데 조각(base64url JSON)의 email — 서명 확인은 Firestore 가 한다. 못 읽으면 ''
function readEmail(token) {
  try {
    const email = JSON.parse(Buffer.from(token.split('.')[1], 'base64url').toString('utf8')).email;
    return typeof email === 'string' ? email : '';
  } catch {
    return '';
  }
}

// Row 칸만, 글자만 — 스키마 밖 칸은 버리고 글자가 아닌 값은 ''
function cleanRows(rows) {
  if (!Array.isArray(rows)) return [];
  return rows.filter((r) => r && typeof r === 'object').map((r) => ({
    ...Object.fromEntries(FIELDS.map((f) => [f, str(r[f])])),
    unsure: Array.isArray(r.unsure) ? r.unsure.filter((f) => FIELDS.includes(f)) : [],
  }));
}

// 클로드 오류 → [상태 번호, 오류 이름]. SDK 오류는 name 이 'Error' 그대로라 클래스 이름도 본다
function mapError(e) {
  if (e?.name === 'APIConnectionTimeoutError' || e?.constructor?.name === 'APIConnectionTimeoutError') return [504, 'timeout'];
  if (e?.status === 429) return [429, 'busy'];
  if (e?.status === 402 || (e?.status === 400 && /credit balance|usage limit/i.test(String(e.message)))) return [402, 'limit'];
  if (e?.status === 401) return [503, 'not-ready'];
  return [502, 'failed'];
}

export function makeHandlers({ env, fetch, anthropic, log }) {
  async function GET() {
    return Response.json({ ready: Boolean(env.ANTHROPIC_API_KEY) });
  }

  async function POST(request) {
    const t0 = Date.now();
    let usage = {};
    const done = (status, body) => {
      log({ status, ms: Date.now() - t0, in: Number(usage.input_tokens) || 0, out: Number(usage.output_tokens) || 0 });
      return Response.json(body, { status });
    };
    const fail = (status, error) => done(status, { error });
    try {
      // 1. 로그인 표
      const token = /^Bearer (\S+)$/.exec(request.headers.get('authorization') || '')?.[1] || '';
      const email = token ? readEmail(token) : '';
      if (!email) return fail(401, 'login');

      // 2. 몸통 크기 · 모양 — 허락 목록을 읽기 전에
      const text = await request.text();
      if (text.length > MAX_BODY) return fail(413, 'too-big');
      let body = null;
      try { body = JSON.parse(text); } catch { /* 아래에서 400 */ }
      if (!body || typeof body.image !== 'string' || !body.image) return fail(400, 'bad-request');

      // 3. 주인 확인 — 사장님 토큰 그대로 allow/{메일} 을 읽는다(규칙: 자기 메일 문서만 get). 200 만 통과
      const r = await fetch(ALLOW_URL + encodeURIComponent(email), { headers: { Authorization: 'Bearer ' + token } });
      if (r.status === 401) return fail(401, 'login');
      if (r.status === 403 || r.status === 404) return fail(403, 'denied');
      if (r.status !== 200) return fail(502, 'failed');

      // 4. 열쇠
      if (!env.ANTHROPIC_API_KEY) return fail(503, 'not-ready');

      // 5. 클로드 — 사진 + 지시 + 일정표 날짜 · 이름 목록
      const hints = body.hints && typeof body.hints === 'object' ? body.hints : {};
      const client = await anthropic(env.ANTHROPIC_API_KEY);
      const res = await client.beta.messages.create({
        model: 'claude-opus-5-5',
        max_tokens: 16000,
        betas: ['server-side-fallback-2026-07-01'],
        fallbacks: 'default',
        output_config: { effort: 'medium', format: { type: 'json_schema', schema: NOTE_SCHEMA } },
        system: SYSTEM,
        messages: [{
          role: 'user',
          content: [
            { type: 'image', source: { type: 'base64', media_type: 'image/jpeg', data: body.image } },
            {
              type: 'text',
              text: [
                `일정표 날짜: ${str(body.day) || '(없음)'}`,
                `이름 목록 — 담당: ${names(hints.staff).join(', ') || '(없음)'}`,
                `이름 목록 — 장소: ${names(hints.places).join(', ') || '(없음)'}`,
                '이 노트 사진을 읽어 칸에 나눠 주세요.',
              ].join('\n'),
            },
          ],
        }],
      }, { timeout: 55_000, maxRetries: 0 });
      usage = res.usage || {};
      if (res.stop_reason === 'refusal') return fail(502, 'refusal');
      const out = JSON.parse(res.content.find((b) => b.type === 'text').text);
      return done(200, { day: str(out.day), rows: cleanRows(out.rows), note: str(out.note) });
    } catch (e) {
      return fail(...mapError(e));
    }
  }

  return { GET, POST };
}

// 실제 의존 — SDK 는 실제로 부를 때만 불러온다(시험은 SDK 없이 돈다)
export const { GET, POST } = makeHandlers({
  env: process.env,
  fetch: (...a) => globalThis.fetch(...a),
  anthropic: async (apiKey) => new (await import('@anthropic-ai/sdk')).default({ apiKey }),
  log: console.log,
});
