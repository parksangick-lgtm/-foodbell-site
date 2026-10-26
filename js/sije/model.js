// 시제행사 내역서 — 화면 · 인쇄 · 시험이 같이 쓰는 순수 계산 (저장소에 붙지 않는다).

export const STATUSES = ['확정', '미확정', '주문없음'];

const DAYS = ['일', '월', '화', '수', '목', '금', '토'];

// '2026-11-13', '10시' → '2026년 11월 13일 (금) 10시'. 요일은 UTC 로 계산해 기기 시간대와 상관없게 한다.
export function formatDateText(date, time) {
  const [y, m, d] = date.split('-').map(Number);
  const day = DAYS[new Date(Date.UTC(y, m - 1, d)).getUTCDay()];
  return `${y}년 ${m}월 ${d}일 (${day})` + (time ? ` ${time}` : '');
}

// 맨 위 큰 줄 = 주소 + 행사일 — 날짜를 고치면 이 줄도 따라 바뀐다.
export function titleLine(ev) {
  return `${(ev.titlePlace || '').trim()} ${formatDateText(ev.date, ev.time)}`.trim();
}

// 품목 줄 이름: 왼쪽 L01 · L02 …, 오른쪽 R01 … (줄마다 이름이 있어 서로 다른 줄을 동시에 고쳐도 안 덮어쓴다)
export function itemKey(side, index) {
  return side + String(index).padStart(2, '0');
}

export function itemsBySide(items) {
  const out = { L: [], R: [] };
  for (const key of Object.keys(items).sort()) out[key[0]].push(items[key]);
  return out;
}

// 빈 양식 → 새 행사 (상태 미확정, 나머지 글자 칸은 비움)
export function newEventFromTemplate(tpl) {
  const text = [
    'date', 'time', 'sijeil', 'expectedDate', 'basis', 'confirmedText', 'place', 'titlePlace',
    'setting', 'sansinje', 'customer', 'staffCar', 'meal', 'amount', 'amountDetail',
    'departTime', 'arriveTime', 'mustDo', 'fileLabel', 'extraItems', 'memo', 'sourceFile',
  ];
  const ev = Object.fromEntries(text.map((k) => [k, '']));
  return {
    ...ev,
    status: '미확정',
    templateType: tpl.type ?? tpl.name,   // 머리글 상 종류 — 수량 없는 빈 양식은 type '' 라 안 붙는다
    contacts: [],
    items: structuredClone(tpl.items),
    itemRows: tpl.itemRows ?? 0,   // 품목표 줄 수 — 엑셀처럼 남는 줄에 '추가 기입' 칸을 그린다
  };
}
