/* 일일 일정표 — 손으로 친 인원 · 단가 글자에서 숫자 하나를 읽는다.
   '60명' · '15,000원' · '2만' · '1만5천원' · '1인 15,000원' 은 읽고, 숫자가 둘 이상이거나 범위('60~70명' · '3명+2명')면
   모르는 것(null) — 틀린 금액을 사진 · 복사 글로 직원 모두에게 보내지 않게 (최종 검토 I2) */
const SCALE = { 만: 10000, 천: 1000 };

export function readNumber(text) {
  const t = String(text || '')
    .replace(/(^|\D)1\s*인\s*당?/g, '$1 ')        // '1인' · '1인당' 은 단가의 꾸밈말 ('11인' 은 그대로)
    .replace(/(\d),(?=\d{3})/g, '$1');             // 천 단위 쉼표
  const parts = [...t.matchAll(/(\d+(?:\.\d+)?)\s*(만|천)?/g)];
  if (!parts.length) return null;
  let total = 0;
  let prev = Infinity;
  let end = -1;
  for (const m of parts) {
    const scale = SCALE[m[2]] || 1;
    // 둘째 숫자부터는 바로 붙어 있고(사이에 빈칸만) 단위가 앞보다 작을 때만 이어 읽는다: 1만5천 · 1만5천500
    if (end >= 0 && (t.slice(end, m.index).trim() !== '' || scale >= prev || prev === 1)) return null;
    total += Number(m[1]) * scale;
    prev = scale;
    end = m.index + m[0].length;
  }
  return total;
}
