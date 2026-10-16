r"""전체 행사 → 엑셀 한 파일 (하루 한 번, '…\시제행사 내역서\백업\YYYY-MM-DD 시제행사 백업.xlsx').
시트 '행사' 한 줄 = 행사 하나, 시트 '품목' 한 줄 = 품목 하나. 그림은 넣지 않는다 (PDF 에 있다)."""
import datetime
from pathlib import Path

import openpyxl

# 설계서 4절 순서
EVENT_COLS = [
    ('status', '상태'), ('date', '행사일'), ('time', '시간'), ('sijeil', '시제일'), ('expectedDate', '예상 날짜'),
    ('basis', '근거'), ('confirmedText', '확정 날짜·시간'), ('place', '장소'), ('titlePlace', '맨 위 주소'),
    ('setting', '상차림'), ('sansinje', '산신제'), ('customer', '고객'), ('contacts', '연락처'),
    ('staffCar', '담당·차량'), ('meal', '식사'), ('amount', '금액'), ('amountDetail', '금액 내역'),
    ('departTime', '출발 시간'), ('arriveTime', '도착 시간'), ('mustDo', '꼭 지킬 것'), ('templateType', '상 종류'),
    ('fileLabel', '파일 이름 글자'), ('extraItems', '추가 기입'), ('memo', '메모'), ('sourceFile', '옮겨 온 엑셀'),
    ('updatedAt', '고친 시각'),
]
ITEM_COLS = ['group', 'no', 'name', 'qty', 'note']


def _cell(v):
    if isinstance(v, list):
        return '\n'.join(str(x) for x in v)
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.isoformat()
    return v if v not in ('',) else None


def write_backup(events: list[tuple[str, dict]], out: Path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '행사'
    ws.append(['행사 id', *(h for _, h in EVENT_COLS)])
    items = wb.create_sheet('품목')
    items.append(['행사 id', '줄 이름', '구분', '번호', '품목', '수량', '비고'])
    for id, ev in events:
        ws.append([id, *(_cell(ev.get(k)) for k, _ in EVENT_COLS)])
        for key in sorted(ev.get('items') or {}):
            it = ev['items'][key]
            items.append([id, key, *(_cell(it.get(k)) for k in ITEM_COLS)])
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.stem + '.만드는중.xlsx')
    wb.save(tmp)
    tmp.replace(out)
