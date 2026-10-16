"""확정 · 미확정 목록 읽기 · 짝짓기 시험 — 날짜 + 장소로 내역서와 짝짓는다."""
from conftest import FAKE_DATE_TEXT, FAKE_PLACE, make_fake_list, make_fake_sheet
from tools.sije_web.lists_parse import attach_list_rows, parse_list
from tools.sije_web.sheet_parse import parse_sheet


def test_attach_list_rows_matches_by_date_and_place(tmp_path):
    ev = parse_sheet(make_fake_sheet(tmp_path))
    rows = parse_list(make_fake_list(tmp_path / '확정 목록.xlsx', [
        (FAKE_DATE_TEXT, FAKE_PLACE, '010-0000-0000', '2026년 11월 13일 (금)', '작년 음력 날짜', '2026년 11월 13일 (금) 10시'),
    ]))
    assert attach_list_rows([ev], rows) == []
    assert ev['expectedDate'] == '2026년 11월 13일 (금)'
    assert ev['basis'] == '작년 음력 날짜'
    assert ev['confirmedText'] == '2026년 11월 13일 (금) 10시'


def test_unmatched_list_row_reported(tmp_path):
    ev = parse_sheet(make_fake_sheet(tmp_path))
    rows = parse_list(make_fake_list(tmp_path / '확정 목록.xlsx', [
        (FAKE_DATE_TEXT, FAKE_PLACE, '', '', '', ''),
        ('2026년 11월 20일 (금) 10시', '가짜동 없는 곳', '', '', '', ''),
    ]))
    problems = attach_list_rows([ev], rows)
    assert problems == ['3번째 줄']   # 머리줄이 1번째 — 손님 값은 알리지 않고 줄 번호만
