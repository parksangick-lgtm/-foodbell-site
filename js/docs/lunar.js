// 음력 날짜 글자 — 일일 일정표의 큰 날짜 옆 · 복사 글 · 옵시디언 사본에 쓴다.
// 브라우저의 한국 음력(단기력 ko-KR-u-ca-dangi)만 쓴다. 중국식(chinese)은 하루 어긋나는 날이 있어 대신 쓰지 않는다 —
// 단기력을 모르는 브라우저면 비운다 (설계서 2026-10-20: 2024~2035년 4,383일을 천문연구원 기준과 맞대 틀림 0).
let fmt;
try {
  fmt = new Intl.DateTimeFormat('ko-KR-u-ca-dangi', { month: 'numeric', day: 'numeric' });
  if (fmt.resolvedOptions().calendar !== 'dangi') fmt = null;
} catch {
  fmt = null;
}

// Date → '음력 9월 11일' · 윤달은 '음력 윤6월 1일' · 못 읽으면 ''
export function lunarText(date) {
  if (!fmt || !(date instanceof Date) || Number.isNaN(date.getTime())) return '';
  const parts = fmt.formatToParts(date);
  const month = parts.find((p) => p.type === 'month')?.value;
  const day = parts.find((p) => p.type === 'day')?.value;
  return month && day ? `음력 ${month}월 ${day}일` : '';
}
