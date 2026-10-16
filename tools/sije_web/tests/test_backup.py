"""하루 한 번 백업 엑셀 시험 — 시트 '행사'(한 줄 = 행사) · '품목'(한 줄 = 품목)."""
import datetime

import openpyxl

from conftest import fake_event
from tools.sije_web.backup import write_backup


def test_backup_has_event_and_item_sheets(tmp_path):
    a = fake_event(updatedAt=datetime.datetime(2026, 10, 16, 1, tzinfo=datetime.timezone.utc))
    b = fake_event(place='가짜동 2-2', contacts=['010-0000-0001', '010-0000-0002'])
    out = tmp_path / '백업' / '2026-10-16 시제행사 백업.xlsx'
    write_backup([('a', a), ('b', b)], out)
    wb = openpyxl.load_workbook(out)
    events, items = wb['행사'], wb['품목']
    assert events.max_row == 3                                     # 머리줄 + 2
    head = [c.value for c in events[1]]
    assert head[:3] == ['행사 id', '상태', '행사일']
    row_b = {h: c.value for h, c in zip(head, events[3])}
    assert row_b['장소'] == '가짜동 2-2' and row_b['연락처'] == '010-0000-0001\n010-0000-0002'
    assert items.max_row == 1 + len(a['items']) + len(b['items'])
    assert [c.value for c in items[1]] == ['행사 id', '줄 이름', '구분', '번호', '품목', '수량', '비고']
    assert [c.value for c in items[2]] == ['a', 'L01', '과일', '1', '배', '5개', None]
