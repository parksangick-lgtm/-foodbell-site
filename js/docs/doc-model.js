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

// 목록 검색 (사장님 2026-11-01) — 이미 읽어 온 줄 안에서만 거른다(서버에 다시 묻지 않음). 공백 · 하이픈 · 대소문자 무시, 빈 검색은 전부.
// 비교 대상 = 목록 줄 글자 셋 + 그 서류 summary 의 글자 칸(label · issue · total · count 등). 서류 본문(html) · 종류(kind)는 안 본다.
const squash = (s) => String(s).replace(/[\s-]/g, '').toLowerCase();
export function filterDocs(rows, kind, query) {
  const q = squash(query || '');
  if (!q) return rows;
  return rows.filter(({ doc }) => {
    const texts = [...rowCells(kind, doc), ...Object.entries(doc).filter(([k, v]) => k !== 'html' && k !== 'kind' && typeof v === 'string').map(([, v]) => v)];
    return texts.some((t) => squash(t).includes(q));
  });
}
