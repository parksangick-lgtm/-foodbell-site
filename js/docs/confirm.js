/* 직원 '확인' 단추 — 담당 칸 이름 나누기 · 확인 판단 · 사장님 한 줄 (설계 2026-11-04 3-1 · 3-4).
   사장님 화면(daily-schedule.html) · 직원 화면(today.html) · 시험이 같이 쓴다. 화면 · 저장소는 건드리지 않는다.
   n8n 밤 9시 알림은 이 파일을 못 불러와 같은 규칙을 옮겨 적는다(설계 3-5) — 규칙을 바꾸면 그쪽도 같이.
   옛 아이폰(사파리 16.4 전)에서도 열리게 뒤보기(lookbehind)는 쓰지 않는다 */
const PAREN = /[(（][^)）]*(?:[)）]|$)/g;     // 괄호 안('(보조)' · '（1차）'), 닫지 않았으면 끝까지
const SPLIT = /[.,·/、+\s]+/;                // \s 는 nbsp(&nbsp;)도 포함

/* 담당 칸 글 → 이름 목록. 빈 조각은 버리고 같은 이름은 처음 하나만, 나온 순서대로 */
export function staffNames(text) {
  const parts = String(text || '').replace(PAREN, ' ').split(SPLIT);
  return [...new Set(parts.filter(Boolean))];
}

/* 게시판 한 장 { at, names } + 확인 기록 [{ name, at }] → 이름 목록 순서대로 네 묶음.
   기록 없음 = waiting · 기록 시각 없음(눌렀는데 아직 서버에 안 감) = pending ·
   일정표를 고친 시각(entry.at)보다 앞 = stale(고친 뒤 안 봄) · 그 밖 = done. 목록에 없는 이름의 기록은 무시(담당을 바꾼 경우) */
export function confirmState(entry, marks) {
  const byName = new Map((marks || []).map((m) => [m.name, m]));
  const edited = entry && entry.at != null ? entry.at : null;
  const out = { done: [], waiting: [], stale: [], pending: [] };
  for (const name of (entry && entry.names) || []) {
    const m = byName.get(name);
    if (!m) out.waiting.push(name);
    else if (m.at == null) out.pending.push(name);
    else if (edited != null && m.at < edited) out.stale.push(name);
    else out.done.push({ name, at: m.at });
  }
  return out;
}

/* 사장님 한 줄 — '직원 확인 2/4 · 박○○ 07:12 · 최○○ 07:30 · 아직: 김○○ · 이○○(고친 뒤 안 봄)'.
   hhmm 은 (ms) → 'HH:MM'. 아직 = waiting → pending → stale 차례. 모두 확인했으면 '아직' 을 빼고, 이름이 없으면 빈 글자 */
export function confirmLine(state, hhmm) {
  if (!state) return '';
  const total = state.done.length + state.waiting.length + state.stale.length + state.pending.length;
  if (!total) return '';
  const parts = [`직원 확인 ${state.done.length}/${total}`, ...state.done.map((d) => `${d.name} ${hhmm(d.at)}`)];
  const rest = [...state.waiting, ...state.pending, ...state.stale.map((n) => `${n}(고친 뒤 안 봄)`)];
  if (rest.length) parts.push(`아직: ${rest.join(' · ')}`);
  return parts.join(' · ');
}
