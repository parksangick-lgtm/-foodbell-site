// 일일 일정표 직원 사진(휴대폰 카드) — 직원 화면(today.html)과 같은 줄 순서 (설계 2026-10-24 2절).
// 순수 함수만 둔다 — 화면(DOM)은 daily-schedule.html 이 이 줄 목록으로 그린다.
// 사진에 찍히는 글자라 ::before 이름표 · tabular-nums 를 쓰지 않는다(html2canvas 가 사본에 박거나 숫자 사이에 틈을 낸다).
export const STAFF_NOTE = "전화 · 지도는 홈 화면의 '푸드벨 일정' 아이콘을 누르세요";
export const STAFF_LIKE = '확인했으면 사진을 길게 눌러 👍 해 주세요';
export const SHOT_W = 540;   // 카드 묶음 폭(CSS px) — 휴대폰 폭, 2배로 찍어 사진은 1080px
export const SHOT_H = 960;   // 한 장 = 휴대폰 화면 비율 9:16

const clean = (s) => (s == null ? '' : String(s)).trim();
const join = (parts, sep) => parts.map(clean).filter(Boolean).join(sep);

/* 게시판 한 장의 줄(no · staff · car · leave · time · place · tel · work · amt · lead · leadTel · guideTel · hall · depart · cremate · memo · state)
   → [{ lab, text }]. 첫 줄은 머리(번호 · 시간 · 담당 · 차량), 빈 칸은 이름표까지 뺀다. 메모는 줄바꿈 그대로. 지도 링크(map)는 사진에 안 나온다.
   연기 · 취소(state)는 머리 줄의 state 로 — 화면이 머리 맨 앞에 표시를 그린다 (사장님 10-24 저녁) */
export function cardLines(row) {
  const r = row || {};
  const head = { lab: '', text: join([`${r.no}번`, r.time, join([r.staff, r.car], ' · ')], ' · ') };
  if (clean(r.state)) head.state = clean(r.state);
  const lines = [head];
  const push = (lab, text) => { if (clean(text)) lines.push({ lab, text: clean(text) }); };
  push('출발', r.leave);
  push('장소', r.place);
  push('연락처', r.tel);
  push('행사', r.work);
  push('금액', r.amt);
  push('팀장', join([r.lead, r.leadTel], ' '));
  push('안내', r.guideTel);
  push('장례', join([r.hall, r.depart ? `발인 ${clean(r.depart)}` : '', r.cremate ? `화장 ${clean(r.cremate)}` : ''], ' · '));
  push('메모', r.memo);
  return lines;
}

/* 사진 첫 장의 작은 글자 — '10-24 19:32 보냄 · 2차', 한 번도 안 보냈으면 '10-24 19:32 만듦' */
export function stampText(sent, when) {
  const p = (n) => String(n).padStart(2, '0');
  const t = `${p(when.getMonth() + 1)}-${p(when.getDate())} ${p(when.getHours())}:${p(when.getMinutes())}`;
  return sent > 0 ? `${t} 보냄 · ${sent}차` : `${t} 만듦`;
}
