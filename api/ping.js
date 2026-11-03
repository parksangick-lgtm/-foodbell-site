// 버셀 서버 기능 확인용 (2026-11-03, 일정표 '사진으로 채우기' 계획 과제 1) — 확인이 끝나면 지운다(과제 5).
// GET  /api/ping?wait=N  → N초(0~55) 기다렸다가 답한다 — 서버 기능 시간 한도 확인
// POST /api/ping         → 받은 몸통 글자 수 — 몸통 크기 한도 확인
export const maxDuration = 60;

export async function GET(request) {
  const n = Math.min(55, Math.max(0, Number(new URL(request.url).searchParams.get('wait')) || 0));
  await new Promise((ok) => setTimeout(ok, n * 1000));
  const sdk = typeof (await import('@anthropic-ai/sdk')).default === 'function';
  return Response.json({ ok: true, sdk, waited: n });
}

export async function POST(request) {
  return Response.json({ bytes: (await request.text()).length });
}
