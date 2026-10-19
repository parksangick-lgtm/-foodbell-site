// 웹 서류 5종 — 목록 화면이 쓰는 순수 계산 (저장소에 붙지 않는다).

// 종류 = 화면 파일 이름. title 은 목록 제목, noun 은 버튼 글자(새 견적서 · 이 견적서 지우기).
export const KINDS = {
  'sije-quote': { title: '시제 견적서', noun: '견적서' },
  'event-quote': { title: '행사 견적서', noun: '견적서' },
  'sije-worksheet': { title: '시제 작업지시서', noun: '작업지시서' },
  'statement': { title: '거래명세서', noun: '거래명세서' },
  'staff-pay': { title: '알바비 지급내역서', noun: '지급내역서' },
  'daily-schedule': { title: '일일 일정표', noun: '일정표' },
};

const toDate = (t) => (t && typeof t.toDate === 'function' ? t.toDate() : t) || null;

// 최근에 고친 순. 이 기기에서 방금 만든 서류는 서버 시각이 아직 없어서 맨 위에 둔다.
export function sortDocs(rows) {
  const time = (r) => { const d = toDate(r.doc.updatedAt); return d ? d.getTime() : Infinity; };
  return [...rows].sort((a, b) => time(b) - time(a));
}

const pad2 = (n) => String(n).padStart(2, '0');

export function editedText(updated, now) {
  if (!updated) return '방금 고침';
  const sameYear = updated.getFullYear() === now.getFullYear();
  if (sameYear && updated.getMonth() === now.getMonth() && updated.getDate() === now.getDate()) {
    return `오늘 ${pad2(updated.getHours())}:${pad2(updated.getMinutes())} 고침`;
  }
  const md = `${updated.getMonth() + 1}월 ${updated.getDate()}일`;
  return sameYear ? `${md} 고침` : `${updated.getFullYear()}년 ${md} 고침`;
}

// 목록 한 줄의 글자 셋 (고친 시각은 따로)
export function rowCells(kind, doc) {
  const total = doc.total ? `${doc.total}원` : '-';
  if (kind === 'staff-pay') return [doc.issue || '', doc.count || '0명', total];
  if (kind === 'daily-schedule') return [doc.label || '(날짜 없음)', doc.count || '0건', ''];
  return [doc.label || '(이름 없음)', doc.issue || '', total];
}
