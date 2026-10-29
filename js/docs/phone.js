// 전화번호에 작대기 — 숫자만 친 번호를 010-1234-5678 모양으로 (칸을 떠날 때). 2026-10-29 사장님 "전체 다".
// 규칙은 일일 일정표가 2026-10-21 부터 쓰던 것과 같다(daily-schedule.html telShape · dashTels):
// 02-xxx(x)-xxxx · 0xx-xxx(x)-xxxx · 15xx-xxxx 만. 날짜 같은 숫자 · 이미 작대기가 있는 번호 · 번호 앞뒤 글자는 그대로.

export function telShape(d) {
  const m = d.match(/^(02|0\d{2})(\d{3,4})(\d{4})$/) || d.match(/^(1[5-9]\d{2})(\d{4})$/);
  return m ? m.slice(1).join('-') : null;
}

export const dashTels = (s) => s.replace(/(^|[^\d-])(\d{8,11})(?![\d-])/g, (all, pre, d) => (telShape(d) ? pre + telShape(d) : all));

// 편집 칸 안의 글자 조각마다 작대기 — 줄바꿈 · 안쪽 태그는 그대로 두려고 글자 조각(text node)만 바꾼다. 바뀐 게 있으면 true.
export function dashTelsIn(el) {
  let changed = false;
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const v = dashTels(n.data);
    if (v !== n.data) { n.data = v; changed = true; }
  }
  return changed;
}
