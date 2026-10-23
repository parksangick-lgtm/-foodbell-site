// 일일 일정표 시간 칸 — 오전 · 오후가 없으면 편집 중에만 "오전? 오후?" 를 붙인다 (설계 2026-10-24 4절).
// 1~12시(또는 1~12:분)만 묻는다. 13시 이상, 오전 · 오후 · 새벽 · 아침 · 낮 · 저녁 · 밤 · 정오 · AM · PM 이 있으면 분명하니 안 묻는다.
const MARK = /오전|오후|새벽|아침|낮|저녁|밤|정오|am|pm/i;
const HOUR = /(?:^|[^\d])(?:1[0-2]|[1-9])\s*(?:시|:\d{2})/;

export function needsAmPm(text) {
  const t = (text || '').trim();
  if (!t || MARK.test(t)) return false;
  return HOUR.test(t);
}
