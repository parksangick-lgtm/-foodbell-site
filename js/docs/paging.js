// 장 나누기 — 일일 일정표의 사진 · 인쇄를 A4 장마다 나눌 때, 줄(일 하나)을 장마다 묶는다.
// 첫 장은 표제 · 날짜 · 순번 · 전달 메모 때문에 자리가 적다(firstCap), 다음 장부터는 nextCap.
// 줄 하나가 두 장에 갈리지 않는다 — 한 장보다 큰 줄은 그 줄 혼자 한 장.
export function pageGroups(rowHeights, firstCap, nextCap) {
  const groups = [];
  let cur = [];
  let used = 0;
  let cap = firstCap;
  rowHeights.forEach((h, i) => {
    if (cur.length && used + h > cap) {
      groups.push(cur);
      cur = [];
      used = 0;
      cap = nextCap;
    }
    cur.push(i);
    used += h;
  });
  if (cur.length) groups.push(cur);
  return groups;
}
